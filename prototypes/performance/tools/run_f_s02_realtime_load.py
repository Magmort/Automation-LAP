#!/usr/bin/env python3
"""Run F-S02: measure target real-time load at a fixed simulation tick rate."""

from __future__ import annotations

import argparse
import bisect
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


def rounded(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def fmt_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * ratio) - 1))
    return ordered[index]


def environment_info() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "pythonVersion": platform.python_version(),
        "pythonExecutable": sys.executable,
        "processor": platform.processor(),
        "cpuCount": os.cpu_count(),
        "machine": platform.machine(),
    }


def compute_track_length(track: dict[str, Any]) -> float:
    points = track["centerline"]
    length = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        length += math.hypot(next_point["x"] - point["x"], next_point["y"] - point["y"])
    return length


def lerp(left: float, right: float, ratio: float) -> float:
    return left + (right - left) * ratio


def seek_replay(replay: dict[str, Any], requested_time_s: float) -> dict[str, Any]:
    frames = replay["frames"]
    times = [frame["timeS"] for frame in frames]
    clamped_time_s = min(max(requested_time_s, times[0]), times[-1])
    right_index = bisect.bisect_left(times, clamped_time_s)
    if right_index < len(times) and abs(times[right_index] - clamped_time_s) < 1e-9:
        return frames[right_index]
    left_index = max(0, right_index - 1)
    right_index = min(len(frames) - 1, right_index)
    left_frame = frames[left_index]
    right_frame = frames[right_index]
    left_time = left_frame["timeS"]
    right_time = right_frame["timeS"]
    ratio = (clamped_time_s - left_time) / max(right_time - left_time, 1e-9)
    vehicles: dict[str, dict[str, Any]] = {}
    for vehicle_id in replay["timeline"]["vehicleIds"]:
        left_vehicle = left_frame["vehicles"][vehicle_id]
        right_vehicle = right_frame["vehicles"][vehicle_id]
        vehicles[vehicle_id] = {
            "xM": lerp(left_vehicle["xM"], right_vehicle["xM"], ratio),
            "yM": lerp(left_vehicle["yM"], right_vehicle["yM"], ratio),
            "headingRad": lerp(left_vehicle["headingRad"], right_vehicle["headingRad"], ratio),
            "progressM": lerp(left_vehicle["progressM"], right_vehicle["progressM"], ratio),
            "wrappedProgressM": lerp(left_vehicle["wrappedProgressM"], right_vehicle["wrappedProgressM"], ratio),
            "lateralOffsetM": lerp(left_vehicle["lateralOffsetM"], right_vehicle["lateralOffsetM"], ratio),
            "speedMps": lerp(left_vehicle["speedMps"], right_vehicle["speedMps"], ratio),
            "offTrack": bool(left_vehicle["offTrack"] or right_vehicle["offTrack"]),
        }
    return {"timeS": clamped_time_s, "vehicles": vehicles, "signals": left_frame["signals"]}


def expand_vehicle_states(frame: dict[str, Any], vehicle_count: int, track_length_m: float) -> list[dict[str, Any]]:
    source_vehicles = list(frame["vehicles"].values())
    lateral_slots = [-2.4, -1.2, 0.0, 1.2, 2.4]
    spacing = track_length_m / max(vehicle_count, 1)
    states = []
    for index in range(vehicle_count):
        source = source_vehicles[index % len(source_vehicles)]
        progress = source["progressM"] + index * spacing
        speed_scale = 0.92 + 0.015 * (index % 9)
        states.append(
            {
                "id": f"car_{index:03d}",
                "progressM": progress,
                "wrappedProgressM": progress % track_length_m,
                "lateralOffsetM": lateral_slots[index % len(lateral_slots)],
                "speedMps": max(0.0, source["speedMps"] * speed_scale),
                "headingRad": source["headingRad"],
                "xM": source["xM"],
                "yM": source["yM"],
            }
        )
    return states


def integrate_motion(states: list[dict[str, Any]], dt_s: float, track_length_m: float, tick_index: int) -> None:
    for index, state in enumerate(states):
        speed_variation = math.sin((tick_index + index) * 0.017) * 0.06
        state["speedMps"] = max(0.0, state["speedMps"] + speed_variation * dt_s)
        state["progressM"] += state["speedMps"] * dt_s
        state["wrappedProgressM"] = state["progressM"] % track_length_m
        state["lateralOffsetM"] += math.sin((tick_index * 0.01) + index) * 0.0005


def perceive_neighbors(states: list[dict[str, Any]], track_length_m: float, lookahead_m: float) -> list[dict[str, Any]]:
    ordered = sorted(states, key=lambda state: state["wrappedProgressM"])
    if len(ordered) == 1:
        return [{"id": ordered[0]["id"], "frontId": None, "frontGapM": track_length_m, "frontSpeedMps": ordered[0]["speedMps"]}]
    neighbors = []
    for index, state in enumerate(ordered):
        front = ordered[(index + 1) % len(ordered)]
        front_gap = (front["wrappedProgressM"] - state["wrappedProgressM"]) % track_length_m
        neighbors.append(
            {
                "id": state["id"],
                "frontId": front["id"] if front_gap <= lookahead_m else None,
                "frontGapM": front_gap,
                "frontSpeedMps": front["speedMps"],
            }
        )
    return neighbors


def compute_driver_decisions(
    states: list[dict[str, Any]],
    neighbors: list[dict[str, Any]],
    minimum_gap_m: float,
    target_headway_s: float,
    lookahead_ticks: int,
) -> list[dict[str, Any]]:
    neighbors_by_id = {neighbor["id"]: neighbor for neighbor in neighbors}
    decisions = []
    for state in states:
        neighbor = neighbors_by_id[state["id"]]
        dynamic_gap = minimum_gap_m + state["speedMps"] * target_headway_s
        predicted_gap = neighbor["frontGapM"] - max(0.0, state["speedMps"] - neighbor["frontSpeedMps"]) * lookahead_ticks / 60.0
        constrained = neighbor["frontId"] is not None and predicted_gap < dynamic_gap
        target_speed = min(state["speedMps"], neighbor["frontSpeedMps"]) if constrained else state["speedMps"] + 0.12
        decisions.append(
            {
                "id": state["id"],
                "targetSpeedMps": rounded(target_speed),
                "constrained": constrained,
                "predictedGapM": rounded(predicted_gap),
            }
        )
    return decisions


def sample_replay_frame(time_s: float, states: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> str:
    decisions_by_id = {decision["id"]: decision for decision in decisions}
    payload = {
        "t": rounded(time_s, 3),
        "v": [
            {
                "i": state["id"],
                "p": rounded(state["wrappedProgressM"], 3),
                "l": rounded(state["lateralOffsetM"], 3),
                "s": rounded(state["speedMps"], 3),
                "ts": decisions_by_id[state["id"]]["targetSpeedMps"],
            }
            for state in states
        ],
    }
    return json.dumps(payload, separators=(",", ":"))


def run_realtime_repetition(replay: dict[str, Any], profile: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    vehicle_count = int(profile["vehicleCount"])
    tick_rate_hz = float(config["tickRateHz"])
    duration_s = float(config["durationS"])
    dt_s = 1.0 / tick_rate_hz
    tick_count = int(round(duration_s * tick_rate_hz))
    tick_budget_ms = 1000.0 / tick_rate_hz
    replay_interval_ticks = max(1, int(round(tick_rate_hz / float(config["workload"]["replaySampleHz"]))))
    track_length_m = compute_track_length(replay["track"])
    timings: dict[str, list[float]] = {"input": [], "motion": [], "perception": [], "decision": [], "replay": [], "tick": []}
    serialized_bytes = 0
    replay_sample_count = 0
    deadline_misses = 0
    constrained_decisions = 0
    checksum = 0.0

    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    tracemalloc.start()
    for tick_index in range(tick_count):
        tick_start = time.perf_counter()
        time_s = tick_index * dt_s

        section_start = time.perf_counter()
        base_frame = seek_replay(replay, time_s)
        states = expand_vehicle_states(base_frame, vehicle_count, track_length_m)
        timings["input"].append((time.perf_counter() - section_start) * 1000.0)

        section_start = time.perf_counter()
        integrate_motion(states, dt_s, track_length_m, tick_index)
        timings["motion"].append((time.perf_counter() - section_start) * 1000.0)

        section_start = time.perf_counter()
        neighbors = perceive_neighbors(states, track_length_m, float(config["workload"]["neighborLookaheadM"]))
        timings["perception"].append((time.perf_counter() - section_start) * 1000.0)

        section_start = time.perf_counter()
        decisions = compute_driver_decisions(
            states,
            neighbors,
            float(config["workload"]["minimumGapM"]),
            float(config["workload"]["targetHeadwayS"]),
            int(config["workload"]["driverLookaheadTicks"]),
        )
        constrained_decisions += sum(1 for decision in decisions if decision["constrained"])
        timings["decision"].append((time.perf_counter() - section_start) * 1000.0)

        section_start = time.perf_counter()
        if tick_index % replay_interval_ticks == 0:
            serialized_bytes += len(sample_replay_frame(time_s, states, decisions).encode("utf-8"))
            replay_sample_count += 1
        timings["replay"].append((time.perf_counter() - section_start) * 1000.0)

        checksum += sum(state["wrappedProgressM"] * 0.001 + state["speedMps"] for state in states)
        tick_ms = (time.perf_counter() - tick_start) * 1000.0
        timings["tick"].append(tick_ms)
        if tick_ms > tick_budget_ms:
            deadline_misses += 1

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    wall_s = time.perf_counter() - wall_start
    cpu_s = time.process_time() - cpu_start
    vehicle_ticks = vehicle_count * tick_count
    system_summary = {}
    for name, values in timings.items():
        system_summary[name] = {
            "meanMs": rounded(statistics.mean(values), 6),
            "p95Ms": rounded(percentile(values, 0.95), 6),
            "maxMs": rounded(max(values), 6),
        }
    return {
        "profileId": profile["id"],
        "vehicleCount": vehicle_count,
        "tickRateHz": tick_rate_hz,
        "tickCount": tick_count,
        "vehicleTicks": vehicle_ticks,
        "simulatedDurationS": duration_s,
        "tickBudgetMs": tick_budget_ms,
        "wallTimeMs": wall_s * 1000.0,
        "cpuTimeMs": cpu_s * 1000.0,
        "realTimeFactor": duration_s / max(wall_s, 1e-9),
        "ticksPerSecond": tick_count / max(wall_s, 1e-9),
        "vehicleTicksPerSecond": vehicle_ticks / max(wall_s, 1e-9),
        "deadlineMisses": deadline_misses,
        "deadlineMissRatio": deadline_misses / max(tick_count, 1),
        "tickMeanMs": system_summary["tick"]["meanMs"],
        "tickP95Ms": system_summary["tick"]["p95Ms"],
        "tickMaxMs": system_summary["tick"]["maxMs"],
        "p95BudgetRatio": system_summary["tick"]["p95Ms"] / tick_budget_ms,
        "serializedBytes": serialized_bytes,
        "serializedBytesPerSecond": serialized_bytes / duration_s,
        "replaySampleCount": replay_sample_count,
        "peakTracedBytes": peak_bytes,
        "currentTracedBytes": current_bytes,
        "constrainedDecisionCount": constrained_decisions,
        "systemTimings": system_summary,
        "checksum": rounded(checksum, 3),
    }


def aggregate_repetitions(runs: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        "wallTimeMs",
        "cpuTimeMs",
        "realTimeFactor",
        "ticksPerSecond",
        "vehicleTicksPerSecond",
        "deadlineMisses",
        "tickMeanMs",
        "tickP95Ms",
        "tickMaxMs",
        "p95BudgetRatio",
        "serializedBytes",
        "serializedBytesPerSecond",
        "peakTracedBytes",
    ]
    aggregate = {
        "profileId": runs[0]["profileId"],
        "vehicleCount": runs[0]["vehicleCount"],
        "tickRateHz": runs[0]["tickRateHz"],
        "tickCount": runs[0]["tickCount"],
        "vehicleTicks": runs[0]["vehicleTicks"],
        "simulatedDurationS": runs[0]["simulatedDurationS"],
        "tickBudgetMs": runs[0]["tickBudgetMs"],
        "repetitionCount": len(runs),
        "checksumStable": len({run["checksum"] for run in runs}) == 1,
    }
    for field in fields:
        values = [float(run[field]) for run in runs]
        aggregate[f"{field}Mean"] = rounded(statistics.mean(values), 6)
        aggregate[f"{field}Min"] = rounded(min(values), 6)
        aggregate[f"{field}Max"] = rounded(max(values), 6)
        aggregate[f"{field}Stdev"] = rounded(statistics.pstdev(values), 6)
    system_names = runs[0]["systemTimings"].keys()
    aggregate["systemTimingsMean"] = {}
    for system_name in system_names:
        aggregate["systemTimingsMean"][system_name] = {
            metric: rounded(statistics.mean(float(run["systemTimings"][system_name][metric]) for run in runs), 6)
            for metric in ("meanMs", "p95Ms", "maxMs")
        }
    return aggregate


def run_profiles(replay: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    profile_results = []
    repetitions = int(config["repetitions"])
    for profile in config["profiles"]:
        runs = [run_realtime_repetition(replay, profile, config) for _ in range(repetitions)]
        profile_results.append({"profileId": profile["id"], "label": profile["label"], "required": profile["required"], "runs": runs, "aggregate": aggregate_repetitions(runs)})
    return profile_results


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# F-S02 - Charge cible temps reel",
        "",
        "- **Experience :** F - Charge et acceleration",
        "- **Scenario :** F-S02",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** mesurer si la boucle representative tient les profils cible 12 et 20 voitures a 60 Hz.",
        "- **Reserve :** benchmark Python hors Unity, avec etats dupliques depuis le replay E-S01.",
        "",
        "## Seuils",
        "",
        f"- Budget par tick : {fmt_number(metrics['tickBudgetMs'], 3)} ms",
        f"- Deadline misses requis : <= {summary['thresholds']['requiredMaxDeadlineMisses']}",
        f"- Ratio p95/budget requis : <= {fmt_number(summary['thresholds']['requiredMaxP95BudgetRatio'], 2)}",
        f"- Facteur temps reel requis : >= {fmt_number(summary['thresholds']['requiredMinRealtimeFactor'], 1)}x",
        "",
        "## Profils",
        "",
        "| Profil | Voitures | Requis | Wall moyen | Facteur | Tick p95 | Ratio p95/budget | Misses | Veh-ticks/s | Replay bytes/s |",
        "| --- | ---:| --- | ---:| ---:| ---:| ---:| ---:| ---:| ---:|",
    ]
    for result in summary["profiles"]:
        aggregate = result["aggregate"]
        lines.append(
            "| "
            f"{result['profileId']} | "
            f"{aggregate['vehicleCount']} | "
            f"{'oui' if result['required'] else 'non'} | "
            f"{fmt_number(aggregate['wallTimeMsMean'], 2)} ms | "
            f"{fmt_number(aggregate['realTimeFactorMean'], 1)}x | "
            f"{fmt_number(aggregate['tickP95MsMean'], 4)} ms | "
            f"{fmt_number(aggregate['p95BudgetRatioMean'], 4)} | "
            f"{fmt_number(aggregate['deadlineMissesMean'], 0)} | "
            f"{fmt_number(aggregate['vehicleTicksPerSecondMean'], 0)} | "
            f"{fmt_number(aggregate['serializedBytesPerSecondMean'], 0)} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "F-S02 est valide avec reserves. Les profils cible 12 et 20 voitures gardent une marge temps reel confortable dans cette boucle hors rendu."
                if summary["success"]
                else "F-S02 est a corriger ou a re-mesurer avant de passer a l'acceleration F-S03."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run F-S02 real-time target load benchmark.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="Replay JSON produced by E-S01.",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "fixtures" / "f_s02_realtime_profiles.json",
        help="F-S02 profile config.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results",
        help="Directory where F-S02 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    replay = load_json(arguments.replay)
    config = load_json(arguments.profiles)
    profile_results = run_profiles(replay, config)
    thresholds = config["thresholds"]
    required_results = [result for result in profile_results if result["required"]]
    profile_errors = []
    for result in required_results:
        aggregate = result["aggregate"]
        if aggregate["deadlineMissesMax"] > thresholds["requiredMaxDeadlineMisses"]:
            profile_errors.append(f"{result['profileId']} has deadline misses")
        if aggregate["p95BudgetRatioMean"] > thresholds["requiredMaxP95BudgetRatio"]:
            profile_errors.append(f"{result['profileId']} p95 budget ratio too high")
        if aggregate["realTimeFactorMean"] < thresholds["requiredMinRealtimeFactor"]:
            profile_errors.append(f"{result['profileId']} real-time factor too low")
        if not aggregate["checksumStable"]:
            profile_errors.append(f"{result['profileId']} checksum unstable")
    tick_budget_ms = 1000.0 / float(config["tickRateHz"])
    metrics = {
        "profileCount": len(profile_results),
        "requiredProfileCount": len(required_results),
        "repetitionsPerProfile": int(config["repetitions"]),
        "tickRateHz": float(config["tickRateHz"]),
        "tickBudgetMs": tick_budget_ms,
        "simulatedDurationS": float(config["durationS"]),
        "profileErrorCount": len(profile_errors),
        "requiredProfilesPass": len(profile_errors) == 0,
        "minRequiredRealtimeFactorMean": min(result["aggregate"]["realTimeFactorMean"] for result in required_results),
        "maxRequiredP95BudgetRatioMean": max(result["aggregate"]["p95BudgetRatioMean"] for result in required_results),
    }
    success = (
        metrics["requiredProfileCount"] == 2
        and metrics["repetitionsPerProfile"] >= 3
        and metrics["profileErrorCount"] == 0
    )
    summary = {
        "scenario": "F-S02",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "replayPath": arguments.replay.relative_to(repo_root).as_posix(),
        "profilesPath": arguments.profiles.relative_to(repo_root).as_posix(),
        "environment": environment_info(),
        "thresholds": thresholds,
        "profileErrors": profile_errors,
        "profiles": profile_results,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "f_s02_realtime_load_summary.json"
    report_path = arguments.results_dir / "F_S02_REALTIME_LOAD_RESULT.md"
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
