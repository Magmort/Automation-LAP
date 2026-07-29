#!/usr/bin/env python3
"""Run D-S05: rejoin the target corridor after a lateral offset."""

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


def progress_delta_rear(track_length: float, origin_s: float, target_s: float) -> float:
    return (origin_s - target_s) % track_length


def bumper_gap(center_gap_m: float, left: dict[str, Any], right: dict[str, Any]) -> float:
    return center_gap_m - (float(left["lengthM"]) + float(right["lengthM"])) * 0.5


def build_initial_states(scene: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    for vehicle in scene["vehicles"]:
        states[vehicle["id"]] = {
            "id": vehicle["id"],
            "label": vehicle["label"],
            "role": vehicle["role"],
            "progressM": float(vehicle["progressM"]),
            "unwrappedProgressM": float(vehicle["progressM"]),
            "lateralOffsetM": float(vehicle["lateralOffsetM"]),
            "targetLateralOffsetM": float(vehicle["targetLateralOffsetM"]),
            "speedMps": float(vehicle["initialSpeedKmh"]) * KMH_TO_MPS,
            "targetSpeedMps": float(vehicle["targetSpeedKmh"]) * KMH_TO_MPS,
            "freeTargetSpeedMps": float(vehicle["targetSpeedKmh"]) * KMH_TO_MPS,
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


def pair_contact(track_length: float, left: dict[str, Any], right: dict[str, Any]) -> bool:
    forward = progress_delta_forward(track_length, left["progressM"], right["progressM"])
    center_gap = min(forward, track_length - forward)
    longitudinal_overlap = center_gap <= (left["lengthM"] + right["lengthM"]) * 0.5
    lateral_overlap = abs(left["lateralOffsetM"] - right["lateralOffsetM"]) <= (left["widthM"] + right["widthM"]) * 0.5
    return longitudinal_overlap and lateral_overlap


def target_lane_neighbors(
    states: dict[str, dict[str, Any]],
    ego: dict[str, Any],
    track_length: float,
    target_offset_m: float,
    lateral_limit_m: float,
) -> tuple[dict[str, Any] | None, float | None, dict[str, Any] | None, float | None]:
    front_candidates: list[tuple[float, dict[str, Any]]] = []
    rear_candidates: list[tuple[float, dict[str, Any]]] = []
    for other in states.values():
        if other["id"] == ego["id"]:
            continue
        if abs(other["lateralOffsetM"] - target_offset_m) > lateral_limit_m:
            continue
        front_gap = bumper_gap(progress_delta_forward(track_length, ego["progressM"], other["progressM"]), ego, other)
        rear_gap = bumper_gap(progress_delta_rear(track_length, ego["progressM"], other["progressM"]), ego, other)
        if front_gap > 0.0:
            front_candidates.append((front_gap, other))
        if rear_gap > 0.0:
            rear_candidates.append((rear_gap, other))
    front_candidates.sort(key=lambda item: item[0])
    rear_candidates.sort(key=lambda item: item[0])
    front = front_candidates[0] if front_candidates else None
    rear = rear_candidates[0] if rear_candidates else None
    return (
        front[1] if front else None,
        front[0] if front else None,
        rear[1] if rear else None,
        rear[0] if rear else None,
    )


def update_ego_speed_target(
    ego: dict[str, Any],
    front: dict[str, Any] | None,
    rear: dict[str, Any] | None,
    front_gap_m: float | None,
    rear_gap_m: float | None,
    rejoin: dict[str, Any],
) -> None:
    target = ego["freeTargetSpeedMps"]
    if front is not None and front_gap_m is not None and front_gap_m < float(rejoin["frontSafetyGapM"]) + 12.0:
        target = min(target, front["speedMps"])
    if rear is not None and rear_gap_m is not None and rear_gap_m < float(rejoin["rearSafetyGapM"]) + 8.0:
        target = max(target, min(ego["freeTargetSpeedMps"], rear["speedMps"] + 0.8))
    ego["targetSpeedMps"] = target


def simulate(scene: dict[str, Any], c_s02: Any, segments: list[Any], track_length: float) -> dict[str, Any]:
    dt = float(scene["simulation"]["dt"])
    duration_s = float(scene["simulation"]["durationS"])
    sample_interval_s = float(scene["simulation"]["sampleIntervalS"])
    controller = scene["controller"]
    rejoin = scene["rejoin"]
    target_offset = float(rejoin["targetOffsetM"])
    states = build_initial_states(scene)
    ego = states["ego"]

    samples: list[dict[str, Any]] = []
    gap_ok_time_s = 0.0
    rejoin_started_s: float | None = None
    rejoin_completed_s: float | None = None
    contact_ticks = 0
    off_track_ticks = 0
    stable_target_ticks = 0
    stable_target_total_ticks = 0
    min_front_gap_during_rejoin = math.inf
    min_rear_gap_during_rejoin = math.inf
    min_edge_clearance = math.inf
    max_lateral_speed = 0.0
    next_sample_time = 0.0
    time_s = 0.0

    while time_s <= duration_s + 1e-9:
        front, front_gap, rear, rear_gap = target_lane_neighbors(
            states,
            ego,
            track_length,
            target_offset,
            float(rejoin["sameCorridorLateralM"]),
        )
        gap_is_safe = (
            front_gap is not None
            and rear_gap is not None
            and front_gap >= float(rejoin["frontSafetyGapM"])
            and rear_gap >= float(rejoin["rearSafetyGapM"])
        )
        gap_ok_time_s = gap_ok_time_s + dt if gap_is_safe else 0.0
        if rejoin_started_s is None and gap_ok_time_s >= float(rejoin["gapDwellS"]):
            rejoin_started_s = time_s
            ego["targetLateralOffsetM"] = target_offset

        update_ego_speed_target(ego, front, rear, front_gap, rear_gap, rejoin)
        if rejoin_started_s is not None:
            min_front_gap_during_rejoin = min(min_front_gap_during_rejoin, front_gap if front_gap is not None else math.inf)
            min_rear_gap_during_rejoin = min(min_rear_gap_during_rejoin, rear_gap if rear_gap is not None else math.inf)
        if rejoin_started_s is not None and rejoin_completed_s is None:
            if abs(ego["lateralOffsetM"] - target_offset) <= float(rejoin["completeLateralToleranceM"]):
                rejoin_completed_s = time_s
        if rejoin_completed_s is not None:
            stable_target_total_ticks += 1
            if abs(ego["lateralOffsetM"] - target_offset) <= float(rejoin["completeLateralToleranceM"]) and gap_is_safe:
                stable_target_ticks += 1

        poses = {vehicle_id: project_state(c_s02, segments, track_length, state) for vehicle_id, state in states.items()}
        edge_clearances = [edge_clearance(states[vehicle_id], pose) for vehicle_id, pose in poses.items()]
        min_edge = min(edge_clearances)
        min_edge_clearance = min(min_edge_clearance, min_edge)
        if any(pose["offTrack"] for pose in poses.values()):
            off_track_ticks += 1
        state_values = list(states.values())
        contact = any(
            pair_contact(track_length, state_values[left_index], state_values[right_index])
            for left_index in range(len(state_values))
            for right_index in range(left_index + 1, len(state_values))
        )
        if contact:
            contact_ticks += 1

        if time_s + 1e-9 >= next_sample_time:
            samples.append(
                {
                    "timeS": time_s,
                    "frontGapM": front_gap,
                    "rearGapM": rear_gap,
                    "gapSafe": gap_is_safe,
                    "rejoinStarted": rejoin_started_s is not None,
                    "rejoinCompleted": rejoin_completed_s is not None,
                    "minEdgeClearanceM": min_edge,
                    "contact": contact,
                    "vehicles": {
                        vehicle_id: {
                            "progressM": state["unwrappedProgressM"],
                            "wrappedProgressM": state["progressM"],
                            "lateralOffsetM": state["lateralOffsetM"],
                            "speedKmh": state["speedMps"] * MPS_TO_KMH,
                            **poses[vehicle_id],
                        }
                        for vehicle_id, state in states.items()
                    },
                }
            )
            next_sample_time += sample_interval_s

        for state in states.values():
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
            if state["id"] == ego["id"]:
                max_lateral_speed = max(max_lateral_speed, abs(lateral_speed))
            state["speedMps"] = max(0.0, state["speedMps"] + accel * dt)
            state["lateralOffsetM"] += lateral_speed * dt
            state["unwrappedProgressM"] += state["speedMps"] * dt
            state["progressM"] = state["unwrappedProgressM"] % track_length

        time_s += dt

    stable_target_percent = (
        100.0 * stable_target_ticks / stable_target_total_ticks if stable_target_total_ticks > 0 else 0.0
    )
    final_ego = states["ego"]
    return {
        "durationS": duration_s,
        "dt": dt,
        "samples": samples,
        "metrics": {
            "contactTicks": contact_ticks,
            "offTrackTicks": off_track_ticks,
            "rejoinStartedS": rejoin_started_s,
            "rejoinCompletedS": rejoin_completed_s,
            "rejoinDurationS": (
                rejoin_completed_s - rejoin_started_s
                if rejoin_started_s is not None and rejoin_completed_s is not None
                else None
            ),
            "minFrontGapDuringRejoinM": min_front_gap_during_rejoin if math.isfinite(min_front_gap_during_rejoin) else None,
            "minRearGapDuringRejoinM": min_rear_gap_during_rejoin if math.isfinite(min_rear_gap_during_rejoin) else None,
            "stableTargetLaneTickPercent": stable_target_percent,
            "minEdgeClearanceM": min_edge_clearance,
            "maxLateralSpeedMps": max_lateral_speed,
            "finalLateralOffsetM": final_ego["lateralOffsetM"],
            "finalSpeedKmh": final_ego["speedMps"] * MPS_TO_KMH,
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["run"]["metrics"]
    lines = [
        "# D-S05 - Reinsertion apres ecart",
        "",
        "- **Experience :** D - Trafic et depassement",
        "- **Scenario :** D-S05",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier qu'une voiture decalee peut revenir dans le corridor cible quand les gaps avant et arriere sont suffisants.",
        "- **Reserve :** la decision reste deterministe et le trou est nominal ; D-S05 ne couvre pas encore les reinsertion contestees.",
        "",
        "## Scene",
        "",
        f"- Piste : `{summary['trackInputPath']}`",
        f"- Scene : `{summary['sceneInputPath']}`",
        f"- Duree : {fmt_number(summary['run']['durationS'])} s",
        f"- Pas : {fmt_number(summary['run']['dt'], 5)} s",
        f"- Offset cible : {fmt_number(summary['rejoin']['targetOffsetM'])} m",
        f"- Gap securite avant : {fmt_number(summary['rejoin']['frontSafetyGapM'])} m",
        f"- Gap securite arriere : {fmt_number(summary['rejoin']['rearSafetyGapM'])} m",
        "",
        "## Metriques",
        "",
        f"- Contact ticks : {metrics['contactTicks']}",
        f"- Hors-piste ticks : {metrics['offTrackTicks']}",
        f"- Debut reinsertion : {fmt_number(metrics['rejoinStartedS'])} s",
        f"- Fin reinsertion : {fmt_number(metrics['rejoinCompletedS'])} s",
        f"- Duree reinsertion : {fmt_number(metrics['rejoinDurationS'])} s",
        f"- Gap avant minimal pendant reinsertion : {fmt_number(metrics['minFrontGapDuringRejoinM'])} m",
        f"- Gap arriere minimal pendant reinsertion : {fmt_number(metrics['minRearGapDuringRejoinM'])} m",
        f"- Temps stable dans le corridor cible apres completion : {fmt_number(metrics['stableTargetLaneTickPercent'])} %",
        f"- Clearance bord de piste minimale : {fmt_number(metrics['minEdgeClearanceM'])} m",
        f"- Offset lateral final ego : {fmt_number(metrics['finalLateralOffsetM'])} m",
        f"- Vitesse finale ego : {fmt_number(metrics['finalSpeedKmh'])} km/h",
        "",
        "## Decision",
        "",
        (
            "D-S05 est valide avec reserves. Le prototype peut passer a D-S06 pour consolider statistiquement D."
            if summary["success"]
            else "D-S05 est a corriger avant la synthese D-S06."
        ),
        "",
    ]
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run D-S05 rejoin-after-offset scenario.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "fixtures" / "d_s05_rejoin_scene.json",
        help="TrafficRejoinScene JSON fixture.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results",
        help="Directory where D-S05 result files will be written.",
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
    rejoin = scene["rejoin"]
    summary = {
        "scenario": "D-S05",
        "success": (
            metrics["contactTicks"] == 0
            and metrics["offTrackTicks"] == 0
            and metrics["rejoinStartedS"] is not None
            and metrics["rejoinCompletedS"] is not None
            and metrics["minFrontGapDuringRejoinM"] is not None
            and metrics["minFrontGapDuringRejoinM"] >= float(rejoin["frontSafetyGapM"])
            and metrics["minRearGapDuringRejoinM"] is not None
            and metrics["minRearGapDuringRejoinM"] >= float(rejoin["rearSafetyGapM"])
            and metrics["stableTargetLaneTickPercent"] >= 95.0
            and abs(metrics["finalLateralOffsetM"] - float(rejoin["targetOffsetM"]))
            <= float(rejoin["completeLateralToleranceM"])
            and metrics["minEdgeClearanceM"] >= float(rejoin["trackEdgeClearanceM"])
        ),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "sceneInputPath": arguments.scene.relative_to(repo_root).as_posix(),
        "trackLengthM": track_length,
        "rejoin": rejoin,
        "controller": scene["controller"],
        "run": run,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "d_s05_rejoin_summary.json"
    report_path = arguments.results_dir / "D_S05_REJOIN_RESULT.md"
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
