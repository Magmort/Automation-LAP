#!/usr/bin/env python3
"""Run F-S01: establish a no-render benchmark harness."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def fmt_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def rounded(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def compute_track_length(track: dict[str, Any]) -> float:
    points = track["centerline"]
    length = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        length += math.hypot(next_point["x"] - point["x"], next_point["y"] - point["y"])
    return length


def expand_vehicle_states(frame: dict[str, Any], vehicle_count: int, track_length_m: float) -> list[dict[str, Any]]:
    source_vehicles = list(frame["vehicles"].values())
    lateral_slots = [-1.8, 0.0, 1.8, -3.0, 3.0]
    states = []
    spacing = track_length_m / max(vehicle_count, 1)
    for index in range(vehicle_count):
        source = source_vehicles[index % len(source_vehicles)]
        progress = source["progressM"] + index * spacing
        wrapped = progress % track_length_m
        lateral_offset = lateral_slots[index % len(lateral_slots)]
        speed = max(0.0, source["speedMps"] * (0.94 + 0.02 * (index % 7)))
        states.append(
            {
                "id": f"car_{index:03d}",
                "progressM": progress,
                "wrappedProgressM": wrapped,
                "lateralOffsetM": lateral_offset,
                "speedMps": speed,
                "xM": source["xM"] + lateral_offset * 0.05,
                "yM": source["yM"] - lateral_offset * 0.05,
                "headingRad": source["headingRad"],
            }
        )
    return states


def perceive_neighbors(states: list[dict[str, Any]], track_length_m: float, lookahead_m: float) -> list[dict[str, Any]]:
    ordered = sorted(states, key=lambda state: state["wrappedProgressM"])
    count = len(ordered)
    if count == 1:
        return [
            {
                "id": ordered[0]["id"],
                "frontId": None,
                "rearId": None,
                "frontGapM": track_length_m,
                "rearGapM": track_length_m,
                "frontSpeedMps": ordered[0]["speedMps"],
            }
        ]
    neighbors = []
    for index, state in enumerate(ordered):
        front = ordered[(index + 1) % count]
        rear = ordered[(index - 1) % count]
        front_gap = (front["wrappedProgressM"] - state["wrappedProgressM"]) % track_length_m
        rear_gap = (state["wrappedProgressM"] - rear["wrappedProgressM"]) % track_length_m
        neighbors.append(
            {
                "id": state["id"],
                "frontId": front["id"] if front_gap <= lookahead_m else None,
                "rearId": rear["id"] if rear_gap <= lookahead_m else None,
                "frontGapM": front_gap,
                "rearGapM": rear_gap,
                "frontSpeedMps": front["speedMps"],
            }
        )
    return neighbors


def apply_light_decision(
    states: list[dict[str, Any]],
    neighbors: list[dict[str, Any]],
    minimum_gap_m: float,
    target_headway_s: float,
) -> list[dict[str, Any]]:
    neighbor_by_id = {neighbor["id"]: neighbor for neighbor in neighbors}
    decisions = []
    for state in states:
        neighbor = neighbor_by_id[state["id"]]
        dynamic_gap = minimum_gap_m + state["speedMps"] * target_headway_s
        constrained = neighbor["frontId"] is not None and neighbor["frontGapM"] < dynamic_gap
        target_speed = min(state["speedMps"], neighbor["frontSpeedMps"]) if constrained else state["speedMps"] + 0.25
        decisions.append(
            {
                "id": state["id"],
                "targetSpeedMps": rounded(target_speed),
                "constrained": constrained,
            }
        )
    return decisions


def serialize_replay_frame(time_s: float, states: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> str:
    decision_by_id = {decision["id"]: decision for decision in decisions}
    payload = {
        "timeS": time_s,
        "vehicles": [
            {
                "id": state["id"],
                "p": rounded(state["progressM"], 3),
                "w": rounded(state["wrappedProgressM"], 3),
                "l": rounded(state["lateralOffsetM"], 3),
                "v": rounded(state["speedMps"], 3),
                "tv": decision_by_id[state["id"]]["targetSpeedMps"],
            }
            for state in states
        ],
    }
    return json.dumps(payload, separators=(",", ":"))


def run_single_repetition(replay: dict[str, Any], profile: dict[str, Any], workload: dict[str, Any]) -> dict[str, Any]:
    vehicle_count = int(profile["vehicleCount"])
    track_length_m = compute_track_length(replay["track"])
    serialized_bytes = 0
    decision_count = 0
    constrained_count = 0
    checksum = 0.0
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    tracemalloc.start()
    for frame in replay["frames"]:
        states = expand_vehicle_states(frame, vehicle_count, track_length_m)
        neighbors = perceive_neighbors(states, track_length_m, float(workload["neighborLookaheadM"]))
        decisions = apply_light_decision(
            states,
            neighbors,
            float(workload["minimumGapM"]),
            float(workload["targetHeadwayS"]),
        )
        serialized = serialize_replay_frame(frame["timeS"], states, decisions)
        serialized_bytes += len(serialized.encode("utf-8"))
        decision_count += len(decisions)
        constrained_count += sum(1 for decision in decisions if decision["constrained"])
        checksum += sum(state["wrappedProgressM"] * 0.001 + state["speedMps"] for state in states)
    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    wall_s = time.perf_counter() - wall_start
    cpu_s = time.process_time() - cpu_start
    frames = len(replay["frames"])
    simulated_duration_s = float(replay["timeline"]["durationS"])
    vehicle_frames = frames * vehicle_count
    return {
        "vehicleCount": vehicle_count,
        "frames": frames,
        "vehicleFrames": vehicle_frames,
        "simulatedDurationS": simulated_duration_s,
        "wallTimeMs": wall_s * 1000.0,
        "cpuTimeMs": cpu_s * 1000.0,
        "realTimeFactor": simulated_duration_s / max(wall_s, 1e-9),
        "framesPerSecond": frames / max(wall_s, 1e-9),
        "vehicleFramesPerSecond": vehicle_frames / max(wall_s, 1e-9),
        "serializedBytes": serialized_bytes,
        "serializedBytesPerSecond": serialized_bytes / simulated_duration_s,
        "peakTracedBytes": peak_bytes,
        "currentTracedBytes": current_bytes,
        "decisionCount": decision_count,
        "constrainedDecisionCount": constrained_count,
        "checksum": rounded(checksum, 3),
    }


def aggregate_repetitions(repetitions: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        "wallTimeMs",
        "cpuTimeMs",
        "realTimeFactor",
        "framesPerSecond",
        "vehicleFramesPerSecond",
        "serializedBytes",
        "serializedBytesPerSecond",
        "peakTracedBytes",
    ]
    aggregate = {
        "vehicleCount": repetitions[0]["vehicleCount"],
        "frames": repetitions[0]["frames"],
        "vehicleFrames": repetitions[0]["vehicleFrames"],
        "simulatedDurationS": repetitions[0]["simulatedDurationS"],
        "repetitionCount": len(repetitions),
        "decisionCount": repetitions[0]["decisionCount"],
        "constrainedDecisionCount": repetitions[0]["constrainedDecisionCount"],
        "checksumStable": len({rep["checksum"] for rep in repetitions}) == 1,
    }
    for field in fields:
        values = [float(repetition[field]) for repetition in repetitions]
        aggregate[f"{field}Mean"] = rounded(statistics.mean(values), 3)
        aggregate[f"{field}Min"] = rounded(min(values), 3)
        aggregate[f"{field}Max"] = rounded(max(values), 3)
        aggregate[f"{field}Stdev"] = rounded(statistics.pstdev(values), 3)
    return aggregate


def run_benchmark(replay: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    repetitions = int(config["repetitions"])
    for vehicle_count in config["vehicleCounts"]:
        profile = {"vehicleCount": int(vehicle_count)}
        runs = [run_single_repetition(replay, profile, config["workload"]) for _ in range(repetitions)]
        results.append({"vehicleCount": int(vehicle_count), "runs": runs, "aggregate": aggregate_repetitions(runs)})
    return results


def environment_info() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "pythonVersion": platform.python_version(),
        "pythonExecutable": sys.executable,
        "processor": platform.processor(),
        "cpuCount": os.cpu_count(),
        "machine": platform.machine(),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# F-S01 - Harnais de benchmark sans rendu",
        "",
        "- **Experience :** F - Charge et acceleration",
        "- **Scenario :** F-S01",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** etablir un harnais reproductible pour mesurer la boucle representative hors rendu.",
        "- **Reserve :** benchmark Python, sans Unity, avec voitures dupliquees depuis le replay E-S01.",
        "",
        "## Environnement",
        "",
        f"- Plateforme : {summary['environment']['platform']}",
        f"- Python : {summary['environment']['pythonVersion']}",
        f"- CPU logiques : {summary['environment']['cpuCount']}",
        "",
        "## Metriques globales",
        "",
        f"- Profils : {metrics['profileCount']}",
        f"- Repetitions par profil : {metrics['repetitionsPerProfile']}",
        f"- Duree simulee : {fmt_number(metrics['simulatedDurationS'])} s",
        f"- Voitures min/max : {metrics['minVehicleCount']} / {metrics['maxVehicleCount']}",
        f"- Erreurs : {metrics['benchmarkErrorCount']}",
        "",
        "## Profils",
        "",
        "| Voitures | Wall moyen | Facteur temps reel | Vehicules-frames/s | Replay bytes/s | Pic memoire |",
        "| ---:| ---:| ---:| ---:| ---:| ---:|",
    ]
    for result in summary["profiles"]:
        aggregate = result["aggregate"]
        lines.append(
            "| "
            f"{result['vehicleCount']} | "
            f"{fmt_number(aggregate['wallTimeMsMean'], 2)} ms | "
            f"{fmt_number(aggregate['realTimeFactorMean'], 1)}x | "
            f"{fmt_number(aggregate['vehicleFramesPerSecondMean'], 0)} | "
            f"{fmt_number(aggregate['serializedBytesPerSecondMean'], 0)} | "
            f"{fmt_number(aggregate['peakTracedBytesMean'], 0)} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "F-S01 est valide avec reserves. Le harnais peut servir de base a F-S02 pour mesurer la charge cible temps reel."
                if summary["success"]
                else "F-S01 est a corriger avant de mesurer la charge cible."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run F-S01 no-render benchmark harness.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="Replay JSON produced by E-S01.",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "fixtures" / "f_s01_benchmark_profiles.json",
        help="Benchmark profile config.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results",
        help="Directory where F-S01 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    replay = load_json(arguments.replay)
    config = load_json(arguments.profiles)
    benchmark_profiles = run_benchmark(replay, config)
    benchmark_errors = [
        f"unstable checksum for {profile['vehicleCount']} vehicles"
        for profile in benchmark_profiles
        if not profile["aggregate"]["checksumStable"]
    ]
    metrics = {
        "profileCount": len(benchmark_profiles),
        "repetitionsPerProfile": int(config["repetitions"]),
        "simulatedDurationS": replay["timeline"]["durationS"],
        "minVehicleCount": min(profile["vehicleCount"] for profile in benchmark_profiles),
        "maxVehicleCount": max(profile["vehicleCount"] for profile in benchmark_profiles),
        "benchmarkErrorCount": len(benchmark_errors),
        "allRealTimeFactorsAboveOne": all(profile["aggregate"]["realTimeFactorMean"] > 1.0 for profile in benchmark_profiles),
    }
    success = (
        metrics["profileCount"] == 4
        and metrics["minVehicleCount"] == 1
        and metrics["maxVehicleCount"] == 40
        and metrics["repetitionsPerProfile"] >= 3
        and metrics["benchmarkErrorCount"] == 0
        and metrics["allRealTimeFactorsAboveOne"]
    )
    summary = {
        "scenario": "F-S01",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "replayPath": arguments.replay.relative_to(repo_root).as_posix(),
        "profilesPath": arguments.profiles.relative_to(repo_root).as_posix(),
        "environment": environment_info(),
        "benchmarkErrors": benchmark_errors,
        "profiles": benchmark_profiles,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "f_s01_benchmark_harness_summary.json"
    report_path = arguments.results_dir / "F_S01_BENCHMARK_HARNESS_RESULT.md"
    with summary_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with report_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_markdown(summary))
    print(f"Wrote {summary_path.relative_to(repo_root)}")
    print(f"Wrote {report_path.relative_to(repo_root)}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
