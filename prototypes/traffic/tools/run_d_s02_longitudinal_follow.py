#!/usr/bin/env python3
"""Run D-S02: longitudinal following behind a slower car."""

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


def progress_delta_forward(track_length: float, origin_s: float, target_s: float) -> float:
    return (target_s - origin_s) % track_length


def build_initial_states(scene: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    for vehicle in scene["vehicles"]:
        speed_key = "targetSpeedKmh" if vehicle["role"] == "leader" else "initialSpeedKmh"
        states[vehicle["id"]] = {
            "id": vehicle["id"],
            "label": vehicle["label"],
            "role": vehicle["role"],
            "progressM": float(vehicle["progressM"]),
            "unwrappedProgressM": float(vehicle["progressM"]),
            "lateralOffsetM": float(vehicle["lateralOffsetM"]),
            "speedMps": float(vehicle[speed_key]) * KMH_TO_MPS,
            "lengthM": float(vehicle["lengthM"]),
            "widthM": float(vehicle["widthM"]),
            "freeSpeedMps": float(vehicle.get("freeSpeedKmh", vehicle.get("targetSpeedKmh", 0.0))) * KMH_TO_MPS,
            "targetSpeedMps": float(vehicle.get("targetSpeedKmh", vehicle.get("freeSpeedKmh", 0.0))) * KMH_TO_MPS,
            "lapCount": 0,
        }
    return states


def front_gap_m(track_length: float, follower: dict[str, Any], leader: dict[str, Any]) -> float:
    center_gap = progress_delta_forward(track_length, follower["progressM"], leader["progressM"])
    return center_gap - (follower["lengthM"] + leader["lengthM"]) * 0.5


def same_corridor(follower: dict[str, Any], leader: dict[str, Any], lateral_limit_m: float) -> bool:
    return abs(follower["lateralOffsetM"] - leader["lateralOffsetM"]) <= lateral_limit_m


def project_state(c_s02: Any, segments: list[Any], track_length: float, state: dict[str, Any]) -> dict[str, float]:
    center = c_s02.point_at_s(segments, track_length, state["progressM"])
    x = center["x"] + center["normalX"] * state["lateralOffsetM"]
    y = center["y"] + center["normalY"] * state["lateralOffsetM"]
    return {
        "x": x,
        "y": y,
        "heading": center["heading"],
    }


def simulate(scene: dict[str, Any], c_s02: Any, segments: list[Any], track_length: float) -> dict[str, Any]:
    dt = float(scene["simulation"]["dt"])
    duration_s = float(scene["simulation"]["durationS"])
    sample_interval_s = float(scene["simulation"]["sampleIntervalS"])
    forward_lookahead_m = float(scene["perception"]["forwardLookaheadM"])
    lateral_limit_m = float(scene["perception"]["sameCorridorLateralM"])
    controller = scene["controller"]
    states = build_initial_states(scene)
    leader = states["leader"]
    follower = states["follower"]

    samples: list[dict[str, Any]] = []
    gap_values: list[float] = []
    desired_gap_values: list[float] = []
    speed_error_values: list[float] = []
    front_detected_ticks = 0
    contact_ticks = 0
    stalled_ticks = 0
    max_decel = 0.0
    min_gap = math.inf
    next_sample_time = 0.0
    time_s = 0.0

    while time_s <= duration_s + 1e-9:
        gap = front_gap_m(track_length, follower, leader)
        visible_front = same_corridor(follower, leader, lateral_limit_m) and 0.0 < gap <= forward_lookahead_m
        desired_gap = float(controller["standstillGapM"]) + float(controller["timeHeadwayS"]) * follower["speedMps"]

        leader_speed_target = leader["targetSpeedMps"]
        leader_accel = clamp((leader_speed_target - leader["speedMps"]) / 0.8, -3.5, 2.0)

        if visible_front:
            front_detected_ticks += 1
            gap_error = gap - desired_gap
            follower_target_speed = min(
                follower["freeSpeedMps"],
                leader["speedMps"] + gap_error * float(controller["gapGain"]),
            )
        else:
            follower_target_speed = follower["freeSpeedMps"]

        follower_accel = clamp(
            (follower_target_speed - follower["speedMps"]) / float(controller["speedResponseTimeS"]),
            -float(controller["maxDecelMps2"]),
            float(controller["maxAccelMps2"]),
        )
        max_decel = max(max_decel, max(0.0, -follower_accel))

        gap_values.append(gap)
        desired_gap_values.append(desired_gap)
        speed_error_values.append(abs(follower["speedMps"] - leader["speedMps"]))
        min_gap = min(min_gap, gap)
        if gap <= 0.0:
            contact_ticks += 1
        if follower["speedMps"] < 1.0:
            stalled_ticks += 1

        if time_s + 1e-9 >= next_sample_time:
            leader_pose = project_state(c_s02, segments, track_length, leader)
            follower_pose = project_state(c_s02, segments, track_length, follower)
            samples.append(
                {
                    "timeS": time_s,
                    "gapM": gap,
                    "desiredGapM": desired_gap,
                    "frontDetected": visible_front,
                    "leader": {
                        "progressM": leader["unwrappedProgressM"],
                        "wrappedProgressM": leader["progressM"],
                        "speedKmh": leader["speedMps"] * MPS_TO_KMH,
                        **leader_pose,
                    },
                    "follower": {
                        "progressM": follower["unwrappedProgressM"],
                        "wrappedProgressM": follower["progressM"],
                        "speedKmh": follower["speedMps"] * MPS_TO_KMH,
                        "accelMps2": follower_accel,
                        **follower_pose,
                    },
                }
            )
            next_sample_time += sample_interval_s

        for state, accel in ((leader, leader_accel), (follower, follower_accel)):
            state["speedMps"] = max(0.0, state["speedMps"] + accel * dt)
            state["unwrappedProgressM"] += state["speedMps"] * dt
            state["progressM"] = state["unwrappedProgressM"] % track_length
            state["lapCount"] = math.floor(state["unwrappedProgressM"] / track_length)

        time_s += dt

    stable_window_start = duration_s - 20.0
    stable_samples = [sample for sample in samples if sample["timeS"] >= stable_window_start]
    stable_gap_values = [sample["gapM"] for sample in stable_samples]
    stable_desired_values = [sample["desiredGapM"] for sample in stable_samples]
    stable_speed_delta_values = [
        abs(sample["follower"]["speedKmh"] - sample["leader"]["speedKmh"]) for sample in stable_samples
    ]
    mean_gap_last20 = sum(stable_gap_values) / len(stable_gap_values)
    mean_desired_last20 = sum(stable_desired_values) / len(stable_desired_values)
    mean_speed_delta_last20 = sum(stable_speed_delta_values) / len(stable_speed_delta_values)
    return {
        "durationS": duration_s,
        "dt": dt,
        "samples": samples,
        "metrics": {
            "minGapM": min_gap,
            "contactTicks": contact_ticks,
            "stalledTicks": stalled_ticks,
            "frontDetectedTickPercent": 100.0 * front_detected_ticks / len(gap_values),
            "maxFollowerDecelMps2": max_decel,
            "meanGapLast20S": mean_gap_last20,
            "meanDesiredGapLast20S": mean_desired_last20,
            "meanGapErrorLast20S": mean_gap_last20 - mean_desired_last20,
            "meanSpeedDeltaLast20Kmh": mean_speed_delta_last20,
            "leaderLapCount": leader["lapCount"],
            "followerLapCount": follower["lapCount"],
            "finalGapM": gap_values[-1],
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["run"]["metrics"]
    lines = [
        "# D-S02 - Suivi longitudinal derriere voiture lente",
        "",
        "- **Experience :** D - Trafic et depassement",
        "- **Scenario :** D-S02",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier qu'une voiture plus rapide peut rattraper puis suivre une voiture lente sans contact constant.",
        "- **Reserve :** modele longitudinal simple, pas encore de decision de depassement ni de changement de ligne.",
        "",
        "## Scene",
        "",
        f"- Piste : `{summary['trackInputPath']}`",
        f"- Scene : `{summary['sceneInputPath']}`",
        f"- Duree : {fmt_number(summary['run']['durationS'])} s",
        f"- Pas : {fmt_number(summary['run']['dt'], 5)} s",
        f"- Gap cible : standstill {fmt_number(summary['controller']['standstillGapM'])} m + {fmt_number(summary['controller']['timeHeadwayS'])} s de headway",
        "",
        "## Metriques",
        "",
        f"- Gap minimal : {fmt_number(metrics['minGapM'])} m",
        f"- Contact ticks : {metrics['contactTicks']}",
        f"- Ticks immobilises : {metrics['stalledTicks']}",
        f"- Detection voiture avant : {fmt_number(metrics['frontDetectedTickPercent'])} %",
        f"- Deceleration max suiveur : {fmt_number(metrics['maxFollowerDecelMps2'])} m/s2",
        f"- Gap moyen sur les 20 dernieres secondes : {fmt_number(metrics['meanGapLast20S'])} m",
        f"- Gap cible moyen sur les 20 dernieres secondes : {fmt_number(metrics['meanDesiredGapLast20S'])} m",
        f"- Ecart gap moyen sur les 20 dernieres secondes : {fmt_number(metrics['meanGapErrorLast20S'])} m",
        f"- Delta vitesse moyen sur les 20 dernieres secondes : {fmt_number(metrics['meanSpeedDeltaLast20Kmh'])} km/h",
        "",
        "## Decision",
        "",
        (
            "D-S02 est valide avec reserves. Le prototype peut passer a D-S03 pour declencher un depassement candidat."
            if summary["success"]
            else "D-S02 est a corriger avant de tester un depassement candidat."
        ),
        "",
    ]
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run D-S02 longitudinal following scenario.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "fixtures" / "d_s02_longitudinal_follow_scene.json",
        help="TrafficFollowScene JSON fixture.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results",
        help="Directory where D-S02 result files will be written.",
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
        "scenario": "D-S02",
        "success": (
            metrics["contactTicks"] == 0
            and metrics["stalledTicks"] == 0
            and metrics["minGapM"] >= 2.0
            and metrics["frontDetectedTickPercent"] >= 70.0
            and abs(metrics["meanGapErrorLast20S"]) <= 4.0
            and metrics["meanSpeedDeltaLast20Kmh"] <= 2.5
        ),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "sceneInputPath": arguments.scene.relative_to(repo_root).as_posix(),
        "trackLengthM": track_length,
        "controller": scene["controller"],
        "perception": scene["perception"],
        "run": run,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "d_s02_longitudinal_follow_summary.json"
    report_path = arguments.results_dir / "D_S02_LONGITUDINAL_FOLLOW_RESULT.md"
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
