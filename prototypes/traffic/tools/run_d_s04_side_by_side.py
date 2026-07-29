#!/usr/bin/env python3
"""Run D-S04: maintain two cars side by side without contact."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

KMH_TO_MPS = 1.0 / 3.6
MPS_TO_KMH = 3.6


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def signed_progress_delta(track_length: float, left_s: float, right_s: float) -> float:
    delta = (right_s - left_s + track_length * 0.5) % track_length - track_length * 0.5
    return delta


def build_initial_states(scene: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    for vehicle in scene["vehicles"]:
        states[vehicle["id"]] = {
            "id": vehicle["id"],
            "label": vehicle["label"],
            "progressM": float(vehicle["progressM"]),
            "unwrappedProgressM": float(vehicle["progressM"]),
            "lateralOffsetM": float(vehicle["lateralOffsetM"]),
            "targetLateralOffsetM": float(vehicle["targetLateralOffsetM"]),
            "speedMps": float(vehicle["initialSpeedKmh"]) * KMH_TO_MPS,
            "targetSpeedMps": float(vehicle["targetSpeedKmh"]) * KMH_TO_MPS,
            "lengthM": float(vehicle["lengthM"]),
            "widthM": float(vehicle["widthM"]),
        }
    return states


def project_state(c_s02: Any, segments: list[Any], track_length: float, state: dict[str, Any]) -> dict[str, float]:
    center = c_s02.point_at_s(segments, track_length, state["progressM"])
    x = center["x"] + center["normalX"] * state["lateralOffsetM"]
    y = center["y"] + center["normalY"] * state["lateralOffsetM"]
    projection = c_s02.project_position(segments, track_length, x, y)
    return {
        "x": x,
        "y": y,
        "heading": center["heading"],
        "leftLimitM": center["leftWidth"],
        "rightLimitM": center["rightWidth"],
        "offTrack": abs(projection["lateral"]) > c_s02.track_limit_for_lateral(projection),
    }


def edge_clearance(state: dict[str, Any], pose: dict[str, float]) -> float:
    half_width = state["widthM"] * 0.5
    if state["lateralOffsetM"] >= 0.0:
        return pose["leftLimitM"] - state["lateralOffsetM"] - half_width
    return pose["rightLimitM"] - abs(state["lateralOffsetM"]) - half_width


def simulate(scene: dict[str, Any], c_s02: Any, segments: list[Any], track_length: float) -> dict[str, Any]:
    dt = float(scene["simulation"]["dt"])
    duration_s = float(scene["simulation"]["durationS"])
    sample_interval_s = float(scene["simulation"]["sampleIntervalS"])
    controller = scene["controller"]
    adjacency = scene["adjacency"]
    states = build_initial_states(scene)
    inside = states["inside"]
    outside = states["outside"]

    samples: list[dict[str, Any]] = []
    side_clearance_values: list[float] = []
    abs_progress_delta_values: list[float] = []
    edge_clearance_values: list[float] = []
    side_by_side_ticks = 0
    contact_ticks = 0
    off_track_ticks = 0
    min_side_clearance = math.inf
    min_edge_clearance = math.inf
    max_lateral_speed = 0.0
    next_sample_time = 0.0
    time_s = 0.0

    while time_s <= duration_s + 1e-9:
        progress_delta = signed_progress_delta(track_length, inside["progressM"], outside["progressM"])
        abs_progress_delta = abs(progress_delta)
        lateral_separation = abs(outside["lateralOffsetM"] - inside["lateralOffsetM"])
        side_clearance = lateral_separation - (inside["widthM"] + outside["widthM"]) * 0.5
        side_by_side = abs_progress_delta <= float(adjacency["longitudinalOverlapM"])
        contact = side_by_side and side_clearance <= 0.0

        inside_pose = project_state(c_s02, segments, track_length, inside)
        outside_pose = project_state(c_s02, segments, track_length, outside)
        inside_edge = edge_clearance(inside, inside_pose)
        outside_edge = edge_clearance(outside, outside_pose)
        min_edge = min(inside_edge, outside_edge)

        if side_by_side:
            side_by_side_ticks += 1
        if contact:
            contact_ticks += 1
        if inside_pose["offTrack"] or outside_pose["offTrack"]:
            off_track_ticks += 1

        side_clearance_values.append(side_clearance)
        abs_progress_delta_values.append(abs_progress_delta)
        edge_clearance_values.append(min_edge)
        min_side_clearance = min(min_side_clearance, side_clearance)
        min_edge_clearance = min(min_edge_clearance, min_edge)

        if time_s + 1e-9 >= next_sample_time:
            samples.append(
                {
                    "timeS": time_s,
                    "progressDeltaM": progress_delta,
                    "absProgressDeltaM": abs_progress_delta,
                    "sideClearanceM": side_clearance,
                    "minEdgeClearanceM": min_edge,
                    "sideBySide": side_by_side,
                    "contact": contact,
                    "inside": {
                        "progressM": inside["unwrappedProgressM"],
                        "wrappedProgressM": inside["progressM"],
                        "lateralOffsetM": inside["lateralOffsetM"],
                        "speedKmh": inside["speedMps"] * MPS_TO_KMH,
                        **inside_pose,
                    },
                    "outside": {
                        "progressM": outside["unwrappedProgressM"],
                        "wrappedProgressM": outside["progressM"],
                        "lateralOffsetM": outside["lateralOffsetM"],
                        "speedKmh": outside["speedMps"] * MPS_TO_KMH,
                        **outside_pose,
                    },
                }
            )
            next_sample_time += sample_interval_s

        for state in (inside, outside):
            accel = clamp(
                (state["targetSpeedMps"] - state["speedMps"]) / float(controller["speedResponseTimeS"]),
                -float(controller["maxDecelMps2"]),
                float(controller["maxAccelMps2"]),
            )
            lateral_speed = clamp(
                (state["targetLateralOffsetM"] - state["lateralOffsetM"])
                / float(controller["lateralResponseTimeS"]),
                -float(controller["maxLateralSpeedMps"]),
                float(controller["maxLateralSpeedMps"]),
            )
            max_lateral_speed = max(max_lateral_speed, abs(lateral_speed))
            state["speedMps"] = max(0.0, state["speedMps"] + accel * dt)
            state["lateralOffsetM"] += lateral_speed * dt
            state["unwrappedProgressM"] += state["speedMps"] * dt
            state["progressM"] = state["unwrappedProgressM"] % track_length

        time_s += dt

    stable_samples = [sample for sample in samples if sample["timeS"] >= duration_s - 15.0]
    stable_side_clearance = [sample["sideClearanceM"] for sample in stable_samples]
    stable_progress_delta = [sample["absProgressDeltaM"] for sample in stable_samples]
    return {
        "durationS": duration_s,
        "dt": dt,
        "samples": samples,
        "metrics": {
            "contactTicks": contact_ticks,
            "offTrackTicks": off_track_ticks,
            "sideBySideTickPercent": 100.0 * side_by_side_ticks / len(side_clearance_values),
            "minSideClearanceM": min_side_clearance,
            "minEdgeClearanceM": min_edge_clearance,
            "meanSideClearanceLast15S": sum(stable_side_clearance) / len(stable_side_clearance),
            "meanAbsProgressDeltaLast15S": sum(stable_progress_delta) / len(stable_progress_delta),
            "maxLateralSpeedMps": max_lateral_speed,
            "finalSideClearanceM": side_clearance_values[-1],
            "finalAbsProgressDeltaM": abs_progress_delta_values[-1],
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["run"]["metrics"]
    lines = [
        "# D-S04 - Deux voitures cote a cote",
        "",
        "- **Experience :** D - Trafic et depassement",
        "- **Scenario :** D-S04",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier que deux voitures peuvent rester cote a cote avec separation laterale et limites de piste mesurables.",
        "- **Reserve :** pas encore de manoeuvre complete de depassement ; les offsets lateraux cibles sont imposes.",
        "",
        "## Scene",
        "",
        f"- Piste : `{summary['trackInputPath']}`",
        f"- Scene : `{summary['sceneInputPath']}`",
        f"- Duree : {fmt_number(summary['run']['durationS'])} s",
        f"- Pas : {fmt_number(summary['run']['dt'], 5)} s",
        f"- Separation laterale minimale attendue : {fmt_number(summary['adjacency']['minSideClearanceM'])} m",
        "",
        "## Metriques",
        "",
        f"- Contact ticks : {metrics['contactTicks']}",
        f"- Hors-piste ticks : {metrics['offTrackTicks']}",
        f"- Temps cote a cote : {fmt_number(metrics['sideBySideTickPercent'])} %",
        f"- Clearance laterale minimale : {fmt_number(metrics['minSideClearanceM'])} m",
        f"- Clearance bord de piste minimale : {fmt_number(metrics['minEdgeClearanceM'])} m",
        f"- Clearance laterale moyenne sur les 15 dernieres secondes : {fmt_number(metrics['meanSideClearanceLast15S'])} m",
        f"- Delta longitudinal moyen sur les 15 dernieres secondes : {fmt_number(metrics['meanAbsProgressDeltaLast15S'])} m",
        f"- Vitesse laterale max : {fmt_number(metrics['maxLateralSpeedMps'])} m/s",
        "",
        "## Decision",
        "",
        (
            "D-S04 est valide avec reserves. Le prototype peut passer a D-S05 pour tester la reinsertion apres ecart."
            if summary["success"]
            else "D-S04 est a corriger avant de tester la reinsertion apres ecart."
        ),
        "",
    ]
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run D-S04 side-by-side scenario.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "fixtures" / "d_s04_side_by_side_scene.json",
        help="TrafficSideBySideScene JSON fixture.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results",
        help="Directory where D-S04 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    c_s01 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s01_track_contract.py",
        "run_c_s01_track_contract",
    )
    c_s02 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s02_path_following.py",
        "run_c_s02_path_following",
    )
    track = load_json(arguments.track)
    scene = load_json(arguments.scene)
    track_errors = c_s01.validate_track(track)
    if track_errors:
        raise RuntimeError("invalid TrackDefinition: " + "; ".join(track_errors))
    points = c_s02.build_points(track)
    segments, track_length = c_s02.build_segments(points)
    run = simulate(scene, c_s02, segments, track_length)
    metrics = run["metrics"]
    summary = {
        "scenario": "D-S04",
        "success": (
            metrics["contactTicks"] == 0
            and metrics["offTrackTicks"] == 0
            and metrics["sideBySideTickPercent"] >= 95.0
            and metrics["minSideClearanceM"] >= 0.35
            and metrics["meanSideClearanceLast15S"] >= float(scene["adjacency"]["minSideClearanceM"])
            and metrics["minEdgeClearanceM"] >= float(scene["adjacency"]["trackEdgeClearanceM"])
            and metrics["meanAbsProgressDeltaLast15S"] <= float(scene["adjacency"]["longitudinalOverlapM"])
        ),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "sceneInputPath": arguments.scene.relative_to(repo_root).as_posix(),
        "trackLengthM": track_length,
        "adjacency": scene["adjacency"],
        "controller": scene["controller"],
        "run": run,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "d_s04_side_by_side_summary.json"
    report_path = arguments.results_dir / "D_S04_SIDE_BY_SIDE_RESULT.md"
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
