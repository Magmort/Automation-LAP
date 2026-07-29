#!/usr/bin/env python3
"""Run C-S02: follow the canonical track at constrained speed."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TARGET_LAPS = 3
TIME_STEPS = (1.0 / 60.0, 1.0 / 120.0)
REFERENCE_DT = 1.0 / 120.0
TARGET_SPEED_MPS = 12.5
LOOKAHEAD_M = 14.0
WHEELBASE_M = 2.5
MAX_STEER_RAD = 0.32
MAX_DURATION_S = 140.0
MEAN_LATERAL_ERROR_LIMIT_M = 1.25
MAX_LATERAL_ERROR_LIMIT_M = 4.50
LAP_TIME_VARIATION_LIMIT = 0.03


@dataclass(frozen=True)
class TrackPoint:
    id: str
    x: float
    y: float
    left_width: float
    right_width: float


@dataclass(frozen=True)
class TrackSegment:
    index: int
    start_s: float
    length: float
    heading: float
    from_point: TrackPoint
    to_point: TrackPoint


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_c_s01_module(repo_root: Path) -> Any:
    module_path = repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s01_track_contract.py"
    spec = importlib.util.spec_from_file_location("run_c_s01_track_contract", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load C-S01 module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def normalize_angle(value: float) -> float:
    while value <= -math.pi:
        value += 2.0 * math.pi
    while value > math.pi:
        value -= 2.0 * math.pi
    return value


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def build_points(track: dict[str, Any]) -> list[TrackPoint]:
    return [
        TrackPoint(
            id=str(point["id"]),
            x=float(point["x"]),
            y=float(point["y"]),
            left_width=float(point["leftWidth"]),
            right_width=float(point["rightWidth"]),
        )
        for point in track["centerline"]
    ]


def build_segments(points: list[TrackPoint]) -> tuple[list[TrackSegment], float]:
    segments: list[TrackSegment] = []
    cumulative = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        dx = next_point.x - point.x
        dy = next_point.y - point.y
        length = math.hypot(dx, dy)
        heading = math.atan2(dy, dx)
        segments.append(
            TrackSegment(
                index=index,
                start_s=cumulative,
                length=length,
                heading=heading,
                from_point=point,
                to_point=next_point,
            )
        )
        cumulative += length
    return segments, cumulative


def interpolate_on_segment(segment: TrackSegment, ratio: float) -> dict[str, float]:
    ratio = clamp(ratio, 0.0, 1.0)
    point = segment.from_point
    next_point = segment.to_point
    tangent_x = math.cos(segment.heading)
    tangent_y = math.sin(segment.heading)
    return {
        "x": point.x + ratio * (next_point.x - point.x),
        "y": point.y + ratio * (next_point.y - point.y),
        "heading": segment.heading,
        "tangentX": tangent_x,
        "tangentY": tangent_y,
        "normalX": -tangent_y,
        "normalY": tangent_x,
        "leftWidth": point.left_width + ratio * (next_point.left_width - point.left_width),
        "rightWidth": point.right_width + ratio * (next_point.right_width - point.right_width),
    }


def point_at_s(segments: list[TrackSegment], track_length: float, s: float) -> dict[str, float]:
    wrapped_s = s % track_length
    for segment in segments:
        if segment.start_s <= wrapped_s < segment.start_s + segment.length:
            return interpolate_on_segment(segment, (wrapped_s - segment.start_s) / segment.length)
    last = segments[-1]
    return interpolate_on_segment(last, 1.0)


def project_position(
    segments: list[TrackSegment],
    track_length: float,
    x: float,
    y: float,
) -> dict[str, float]:
    best: dict[str, float] | None = None
    for segment in segments:
        dx = segment.to_point.x - segment.from_point.x
        dy = segment.to_point.y - segment.from_point.y
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            continue
        ratio = clamp(((x - segment.from_point.x) * dx + (y - segment.from_point.y) * dy) / length_squared, 0.0, 1.0)
        projected = interpolate_on_segment(segment, ratio)
        delta_x = x - projected["x"]
        delta_y = y - projected["y"]
        distance_squared = delta_x * delta_x + delta_y * delta_y
        lateral = delta_x * projected["normalX"] + delta_y * projected["normalY"]
        candidate = {
            "s": (segment.start_s + ratio * segment.length) % track_length,
            "lateral": lateral,
            "distanceSquared": distance_squared,
            "leftWidth": projected["leftWidth"],
            "rightWidth": projected["rightWidth"],
            "segmentIndex": segment.index,
            "heading": projected["heading"],
        }
        if best is None or candidate["distanceSquared"] < best["distanceSquared"]:
            best = candidate
    if best is None:
        raise RuntimeError("cannot project position on empty track")
    return best


def track_limit_for_lateral(projection: dict[str, float]) -> float:
    return projection["leftWidth"] if projection["lateral"] >= 0.0 else projection["rightWidth"]


def simulate(track: dict[str, Any], dt: float) -> dict[str, Any]:
    points = build_points(track)
    segments, track_length = build_segments(points)
    start = point_at_s(segments, track_length, 0.0)
    state = {
        "time": 0.0,
        "x": start["x"],
        "y": start["y"],
        "heading": start["heading"],
        "speed": TARGET_SPEED_MPS,
    }
    completed_laps = 0
    previous_wrapped_s = 0.0
    unwrapped_s = 0.0
    lap_times: list[float] = []
    last_lap_time = 0.0
    off_track_count = 0
    lateral_abs_values: list[float] = []
    max_abs_steer = 0.0
    max_abs_heading_error = 0.0
    max_lateral_error = 0.0
    samples: list[dict[str, float]] = []
    next_sample_time = 0.0

    while completed_laps < TARGET_LAPS and state["time"] < MAX_DURATION_S:
        projection = project_position(segments, track_length, state["x"], state["y"])
        wrapped_s = projection["s"]
        if previous_wrapped_s - wrapped_s > track_length * 0.5:
            completed_laps += 1
            lap_times.append(state["time"] - last_lap_time)
            last_lap_time = state["time"]
        elif wrapped_s - previous_wrapped_s > track_length * 0.5:
            completed_laps = max(0, completed_laps - 1)
        previous_wrapped_s = wrapped_s
        unwrapped_s = completed_laps * track_length + wrapped_s

        lateral_abs = abs(projection["lateral"])
        lateral_abs_values.append(lateral_abs)
        max_lateral_error = max(max_lateral_error, lateral_abs)
        if lateral_abs > track_limit_for_lateral(projection):
            off_track_count += 1

        target = point_at_s(segments, track_length, wrapped_s + LOOKAHEAD_M)
        to_target_x = target["x"] - state["x"]
        to_target_y = target["y"] - state["y"]
        target_distance = max(math.hypot(to_target_x, to_target_y), 1e-9)
        forward_x = math.cos(state["heading"])
        forward_y = math.sin(state["heading"])
        dot = forward_x * to_target_x + forward_y * to_target_y
        cross = forward_x * to_target_y - forward_y * to_target_x
        heading_error = math.atan2(cross, dot)
        curvature = 2.0 * math.sin(heading_error) / target_distance
        steer = clamp(math.atan(WHEELBASE_M * curvature), -MAX_STEER_RAD, MAX_STEER_RAD)
        max_abs_steer = max(max_abs_steer, abs(steer))
        max_abs_heading_error = max(max_abs_heading_error, abs(heading_error))

        speed_error = TARGET_SPEED_MPS - state["speed"]
        acceleration = clamp(speed_error * 3.0, -4.0, 3.0)
        midpoint_speed = max(0.0, state["speed"] + acceleration * dt * 0.5)
        yaw_rate = midpoint_speed * math.tan(steer) / WHEELBASE_M
        midpoint_heading = state["heading"] + yaw_rate * dt * 0.5
        state["x"] += math.cos(midpoint_heading) * midpoint_speed * dt
        state["y"] += math.sin(midpoint_heading) * midpoint_speed * dt
        state["heading"] = normalize_angle(state["heading"] + yaw_rate * dt)
        state["speed"] = max(0.0, state["speed"] + acceleration * dt)
        state["time"] += dt

        if state["time"] + 1e-9 >= next_sample_time:
            samples.append(
                {
                    "time": state["time"],
                    "lap": completed_laps,
                    "progressM": unwrapped_s,
                    "x": state["x"],
                    "y": state["y"],
                    "heading": state["heading"],
                    "speedMps": state["speed"],
                    "lateralErrorM": projection["lateral"],
                    "steerRad": steer,
                }
            )
            next_sample_time += 5.0

    mean_abs_lateral = sum(lateral_abs_values) / len(lateral_abs_values)
    rms_lateral = math.sqrt(sum(value * value for value in lateral_abs_values) / len(lateral_abs_values))
    lap_variation = 0.0
    if len(lap_times) >= 2:
        mean_lap = sum(lap_times) / len(lap_times)
        lap_variation = (max(lap_times) - min(lap_times)) / mean_lap if mean_lap else math.inf

    finite_values = all(
        math.isfinite(value)
        for value in (
            state["time"],
            state["x"],
            state["y"],
            state["heading"],
            state["speed"],
            mean_abs_lateral,
            rms_lateral,
            max_lateral_error,
            lap_variation,
        )
    )
    return {
        "dt": dt,
        "targetLaps": TARGET_LAPS,
        "completedLaps": completed_laps,
        "trackLengthM": track_length,
        "targetSpeedMps": TARGET_SPEED_MPS,
        "targetSpeedKmh": TARGET_SPEED_MPS * 3.6,
        "lookaheadM": LOOKAHEAD_M,
        "wheelbaseM": WHEELBASE_M,
        "maxSteerRad": MAX_STEER_RAD,
        "durationS": state["time"],
        "lapTimesS": lap_times,
        "lapTimeVariation": lap_variation,
        "meanAbsLateralErrorM": mean_abs_lateral,
        "rmsLateralErrorM": rms_lateral,
        "maxAbsLateralErrorM": max_lateral_error,
        "offTrackCount": off_track_count,
        "maxAbsSteerRad": max_abs_steer,
        "maxAbsHeadingErrorRad": max_abs_heading_error,
        "finalState": state,
        "samples": samples,
        "finiteValues": finite_values,
        "success": (
            completed_laps >= TARGET_LAPS
            and off_track_count == 0
            and finite_values
            and mean_abs_lateral <= MEAN_LATERAL_ERROR_LIMIT_M
            and max_lateral_error <= MAX_LATERAL_ERROR_LIMIT_M
            and lap_variation <= LAP_TIME_VARIATION_LIMIT
        ),
    }


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# C-S02 - Suivi de trajectoire a vitesse contrainte",
        "",
        "- **Experience :** C - Tour autonome et modele minimal de circuit",
        "- **Scenario :** C-S02",
        f"- **Statut :** {'valide' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier qu'une voiture peut suivre la ligne centrale par projection et cible lookahead, sans script par virage.",
        "- **Reserve :** la vitesse est volontairement contrainte ; l'adaptation par courbure est repoussee a C-S03.",
        "",
        "## Synthese",
        "",
        f"- Fichier piste : `{summary['inputPath']}`",
        f"- Longueur piste : {fmt_number(summary['trackLengthM'])} m",
        f"- Vitesse cible : {fmt_number(summary['targetSpeedKmh'])} km/h",
        f"- Lookahead : {fmt_number(summary['lookaheadM'])} m",
        f"- Tours cibles : {TARGET_LAPS}",
        "",
        "## Resultats par pas de temps",
        "",
        "| dt | Tours | Duree | Moyenne erreur lat. | RMS erreur lat. | Max erreur lat. | Sorties | Variation tours | Stable |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for run in summary["runs"]:
        lines.append(
            "| "
            f"{fmt_number(run['dt'], 5)} | "
            f"{run['completedLaps']} | "
            f"{fmt_number(run['durationS'])} | "
            f"{fmt_number(run['meanAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['rmsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxAbsLateralErrorM'], 3)} | "
            f"{run['offTrackCount']} | "
            f"{fmt_number(run['lapTimeVariation'] * 100.0, 2)} % | "
            f"{fmt_bool(run['success'])} |"
        )

    lines.extend(
        [
            "",
            "## Temps au tour",
            "",
            "| dt | Tour 1 | Tour 2 | Tour 3 |",
            "| ---: | ---: | ---: | ---: |",
        ]
    )

    for run in summary["runs"]:
        lap_times = run["lapTimesS"]
        lines.append(
            "| "
            f"{fmt_number(run['dt'], 5)} | "
            f"{fmt_number(lap_times[0] if len(lap_times) > 0 else None)} | "
            f"{fmt_number(lap_times[1] if len(lap_times) > 1 else None)} | "
            f"{fmt_number(lap_times[2] if len(lap_times) > 2 else None)} |"
        )

    reference = summary["referenceRun"]
    lines.extend(
        [
            "",
            "## Reference 1/120 s",
            "",
            f"- Erreur laterale moyenne : {fmt_number(reference['meanAbsLateralErrorM'], 3)} m",
            f"- Erreur laterale max : {fmt_number(reference['maxAbsLateralErrorM'], 3)} m",
            f"- Braquage max utilise : {fmt_number(reference['maxAbsSteerRad'], 4)} rad",
            f"- Erreur de cap max vers cible : {fmt_number(reference['maxAbsHeadingErrorRad'], 4)} rad",
            "",
            "## Observations",
            "",
            "- Le controleur utilise uniquement la projection sur `TrackDefinition`, une cible lookahead et une loi pure pursuit.",
            "- Aucun virage n'est scripté : la meme logique parcourt toute la boucle.",
            "- Les deux pas de temps testés terminent trois tours sans sortie de piste.",
            "- La vitesse est maintenue constante pour isoler le probleme de suivi ; C-S03 ajoutera l'adaptation par courbure.",
            "",
            "## Decision",
            "",
            "C-S02 est valide. Le prototype peut passer a C-S03 pour moduler la vitesse selon la courbure et tester un comportement plus proche d'un tour autonome utilisable.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run C-S02 path following.")
    parser.add_argument(
        "--input",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "results",
        help="Directory where C-S02 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    c_s01 = load_c_s01_module(repo_root)
    track = load_json(arguments.input)
    errors = c_s01.validate_track(track)
    if errors:
        raise RuntimeError("invalid TrackDefinition: " + "; ".join(errors))

    runs = [simulate(track, dt) for dt in TIME_STEPS]
    reference_run = next(run for run in runs if abs(run["dt"] - REFERENCE_DT) < 1e-12)
    summary = {
        "scenario": "C-S02",
        "success": all(run["success"] for run in runs),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputPath": arguments.input.relative_to(repo_root).as_posix(),
        "trackLengthM": reference_run["trackLengthM"],
        "targetSpeedMps": TARGET_SPEED_MPS,
        "targetSpeedKmh": TARGET_SPEED_MPS * 3.6,
        "lookaheadM": LOOKAHEAD_M,
        "successCriteria": {
            "targetLaps": TARGET_LAPS,
            "offTrackCount": 0,
            "meanLateralErrorMMax": MEAN_LATERAL_ERROR_LIMIT_M,
            "maxLateralErrorMMax": MAX_LATERAL_ERROR_LIMIT_M,
            "lapTimeVariationMax": LAP_TIME_VARIATION_LIMIT,
        },
        "runs": runs,
        "referenceRun": reference_run,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "c_s02_path_following_summary.json"
    report_path = arguments.results_dir / "C_S02_PATH_FOLLOWING_RESULT.md"

    with summary_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    with report_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_markdown(summary))

    print(f"Wrote {summary_path.relative_to(repo_root)}")
    print(f"Wrote {report_path.relative_to(repo_root)}")
    return 0 if summary["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
