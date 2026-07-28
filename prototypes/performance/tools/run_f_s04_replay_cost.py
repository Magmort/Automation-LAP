#!/usr/bin/env python3
"""Run F-S04: measure replay capture and serialization cost by sampling rate."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_f_s02_realtime_load import (  # noqa: E402
    compute_driver_decisions,
    compute_track_length,
    environment_info,
    expand_vehicle_states,
    find_repo_root,
    fmt_number,
    integrate_motion,
    load_json,
    perceive_neighbors,
    percentile,
    rounded,
    sample_replay_frame,
    seek_replay,
)


def run_replay_cost_repetition(replay: dict[str, Any], profile: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    vehicle_count = int(profile["vehicleCount"])
    sample_hz = float(profile["replaySampleHz"])
    tick_rate_hz = float(config["tickRateHz"])
    duration_s = float(config["durationS"])
    dt_s = 1.0 / tick_rate_hz
    tick_count = int(round(duration_s * tick_rate_hz))
    replay_interval_ticks = math.inf if sample_hz <= 0 else max(1, int(round(tick_rate_hz / sample_hz)))
    track_length_m = compute_track_length(replay["track"])
    timings: dict[str, list[float]] = {
        "input": [],
        "motion": [],
        "perception": [],
        "decision": [],
        "replay": [],
        "replaySampled": [],
        "tick": [],
    }
    serialized_bytes = 0
    replay_sample_count = 0
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
        should_sample = sample_hz > 0 and tick_index % int(replay_interval_ticks) == 0
        if should_sample:
            payload = sample_replay_frame(time_s, states, decisions)
            serialized_bytes += len(payload.encode("utf-8"))
            replay_sample_count += 1
        replay_ms = (time.perf_counter() - section_start) * 1000.0
        timings["replay"].append(replay_ms)
        if should_sample:
            timings["replaySampled"].append(replay_ms)

        checksum += sum(state["wrappedProgressM"] * 0.001 + state["speedMps"] for state in states)
        timings["tick"].append((time.perf_counter() - tick_start) * 1000.0)

    current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    wall_s = time.perf_counter() - wall_start
    cpu_s = time.process_time() - cpu_start
    system_summary = summarize_timings(timings)
    replay_mean_ms = system_summary["replay"]["meanMs"]
    tick_mean_ms = max(system_summary["tick"]["meanMs"], 1e-9)
    return {
        "profileId": profile["id"],
        "vehicleCount": vehicle_count,
        "replaySampleHz": sample_hz,
        "tickRateHz": tick_rate_hz,
        "tickCount": tick_count,
        "simulatedDurationS": duration_s,
        "wallTimeMs": wall_s * 1000.0,
        "cpuTimeMs": cpu_s * 1000.0,
        "realTimeFactor": duration_s / max(wall_s, 1e-9),
        "ticksPerSecond": tick_count / max(wall_s, 1e-9),
        "vehicleTicksPerSecond": vehicle_count * tick_count / max(wall_s, 1e-9),
        "tickMeanMs": system_summary["tick"]["meanMs"],
        "tickP95Ms": system_summary["tick"]["p95Ms"],
        "tickMaxMs": system_summary["tick"]["maxMs"],
        "replayMeanMs": replay_mean_ms,
        "replayP95Ms": system_summary["replay"]["p95Ms"],
        "replaySampledMeanMs": system_summary["replaySampled"]["meanMs"],
        "replaySampledP95Ms": system_summary["replaySampled"]["p95Ms"],
        "replayShare": replay_mean_ms / tick_mean_ms,
        "serializedBytes": serialized_bytes,
        "serializedBytesPerSecond": serialized_bytes / duration_s,
        "replaySampleCount": replay_sample_count,
        "bytesPerSample": serialized_bytes / replay_sample_count if replay_sample_count else 0.0,
        "peakTracedBytes": peak_bytes,
        "currentTracedBytes": current_bytes,
        "constrainedDecisionCount": constrained_decisions,
        "systemTimings": system_summary,
        "checksum": rounded(checksum, 3),
    }


def summarize_timings(timings: dict[str, list[float]]) -> dict[str, dict[str, float]]:
    summary = {}
    for name, values in timings.items():
        effective = values if values else [0.0]
        summary[name] = {
            "meanMs": rounded(statistics.mean(effective), 6),
            "p95Ms": rounded(percentile(effective, 0.95), 6),
            "maxMs": rounded(max(effective), 6),
        }
    return summary


def aggregate_repetitions(runs: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        "wallTimeMs",
        "cpuTimeMs",
        "realTimeFactor",
        "ticksPerSecond",
        "vehicleTicksPerSecond",
        "tickMeanMs",
        "tickP95Ms",
        "tickMaxMs",
        "replayMeanMs",
        "replayP95Ms",
        "replaySampledMeanMs",
        "replaySampledP95Ms",
        "replayShare",
        "serializedBytes",
        "serializedBytesPerSecond",
        "replaySampleCount",
        "bytesPerSample",
        "peakTracedBytes",
    ]
    aggregate = {
        "profileId": runs[0]["profileId"],
        "vehicleCount": runs[0]["vehicleCount"],
        "replaySampleHz": runs[0]["replaySampleHz"],
        "tickRateHz": runs[0]["tickRateHz"],
        "tickCount": runs[0]["tickCount"],
        "simulatedDurationS": runs[0]["simulatedDurationS"],
        "repetitionCount": len(runs),
        "checksumStable": len({run["checksum"] for run in runs}) == 1,
    }
    for field in fields:
        values = [float(run[field]) for run in runs]
        aggregate[f"{field}Mean"] = rounded(statistics.mean(values), 6)
        aggregate[f"{field}Min"] = rounded(min(values), 6)
        aggregate[f"{field}Max"] = rounded(max(values), 6)
        aggregate[f"{field}Stdev"] = rounded(statistics.pstdev(values), 6)
    return aggregate


def build_profiles(config: dict[str, Any]) -> list[dict[str, Any]]:
    profiles = []
    target_vehicle_count = int(config["targetVehicleCount"])
    reference_hz = float(config["referenceReplaySampleHz"])
    for profile_group in config["profiles"]:
        vehicle_count = int(profile_group["vehicleCount"])
        for sample_hz in profile_group["replaySampleHz"]:
            sample_label = "off" if float(sample_hz) <= 0 else f"{sample_hz:g}hz"
            profiles.append(
                {
                    "id": f"cars_{vehicle_count}_{sample_label}",
                    "vehicleCount": vehicle_count,
                    "replaySampleHz": float(sample_hz),
                    "required": int(vehicle_count) == target_vehicle_count and float(sample_hz) == reference_hz,
                }
            )
    return profiles


def run_profiles(replay: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    repetitions = int(config["repetitions"])
    for profile in build_profiles(config):
        runs = [run_replay_cost_repetition(replay, profile, config) for _ in range(repetitions)]
        results.append({"profileId": profile["id"], "required": profile["required"], "runs": runs, "aggregate": aggregate_repetitions(runs)})
    attach_overheads(results)
    return results


def attach_overheads(results: list[dict[str, Any]]) -> None:
    baselines = {
        result["aggregate"]["vehicleCount"]: result["aggregate"]
        for result in results
        if result["aggregate"]["replaySampleHz"] <= 0
    }
    for result in results:
        aggregate = result["aggregate"]
        baseline = baselines[aggregate["vehicleCount"]]
        wall_delta = aggregate["wallTimeMsMean"] - baseline["wallTimeMsMean"]
        tick_delta = aggregate["tickMeanMsMean"] - baseline["tickMeanMsMean"]
        aggregate["wallOverheadMs"] = rounded(wall_delta, 6)
        aggregate["wallOverheadRatio"] = rounded(wall_delta / max(baseline["wallTimeMsMean"], 1e-9), 6)
        aggregate["tickMeanOverheadMs"] = rounded(tick_delta, 6)
        aggregate["tickMeanOverheadRatio"] = rounded(tick_delta / max(baseline["tickMeanMsMean"], 1e-9), 6)


def validate_results(results: list[dict[str, Any]], config: dict[str, Any]) -> list[str]:
    thresholds = config["thresholds"]
    errors = []
    reference = next((result["aggregate"] for result in results if result["required"]), None)
    target_variants = [result for result in results if result["aggregate"]["vehicleCount"] == int(config["targetVehicleCount"])]
    if reference is None:
        errors.append("reference profile missing")
    else:
        if reference["replayShareMean"] > thresholds["requiredMaxReferenceReplayShare"]:
            errors.append("reference replay share too high")
        if not reference["checksumStable"]:
            errors.append("reference checksum unstable")
    if len(target_variants) < thresholds["requiredMinFrequencyVariants"]:
        errors.append("not enough replay frequency variants")
    return errors


def render_markdown(summary: dict[str, Any]) -> str:
    status = "valide avec reserves" if summary["success"] else "echec"
    target_count = summary["config"]["targetVehicleCount"]
    lines = [
        "# F-S04 - Cout replay detaille",
        "",
        "- **Experience :** F - Charge et acceleration",
        "- **Scenario :** F-S04",
        f"- **Statut :** {status}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** isoler le cout de capture et serialization replay selon la frequence d'echantillonnage.",
        "- **Reserve :** benchmark Python hors Unity, replay compact JSON en memoire, sans IO disque continu.",
        "",
        "## Seuils requis",
        "",
        f"- Profil reference : {target_count} voitures a {fmt_number(summary['config']['referenceReplaySampleHz'], 0)} Hz",
        f"- Part replay reference : <= {fmt_number(summary['thresholds']['requiredMaxReferenceReplayShare'] * 100.0, 1)} %",
        "- Overhead mural : indicateur informatif, sensible a l'ordre d'execution Python/Windows",
        "",
        "## Profils 20 voitures",
        "",
        "| Hz | Wall moyen | Overhead wall | Tick moyen | Replay moyen | Part replay | Octets/s | Octets/sample | Samples |",
        "| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:|",
    ]
    for result in filter_vehicle_count(summary["profiles"], target_count):
        aggregate = result["aggregate"]
        lines.append(render_profile_row(aggregate))
    lines.extend(
        [
            "",
            "## Stress 40 voitures",
            "",
            "| Hz | Wall moyen | Overhead wall | Tick moyen | Replay moyen | Part replay | Octets/s | Octets/sample | Samples |",
            "| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:|",
        ]
    )
    for result in filter_vehicle_count(summary["profiles"], 40):
        lines.append(render_profile_row(result["aggregate"]))
    lines.extend(["", "## Decision", ""])
    if summary["success"]:
        lines.append(
            "F-S04 est valide avec reserves. Le cout replay de reference reste faible dans ce prototype ; la frequence augmente surtout le volume serialise."
        )
    else:
        lines.append("F-S04 est a corriger ou a re-mesurer avant la synthese F-S05.")
    lines.append("")
    return "\n".join(lines)


def filter_vehicle_count(results: list[dict[str, Any]], vehicle_count: int) -> list[dict[str, Any]]:
    return sorted(
        [result for result in results if result["aggregate"]["vehicleCount"] == vehicle_count],
        key=lambda result: result["aggregate"]["replaySampleHz"],
    )


def render_profile_row(aggregate: dict[str, Any]) -> str:
    hz = "off" if aggregate["replaySampleHz"] <= 0 else fmt_number(aggregate["replaySampleHz"], 0)
    return (
        "| "
        f"{hz} | "
        f"{fmt_number(aggregate['wallTimeMsMean'], 2)} ms | "
        f"{fmt_number(aggregate['wallOverheadRatio'] * 100.0, 1)} % | "
        f"{fmt_number(aggregate['tickMeanMsMean'], 4)} ms | "
        f"{fmt_number(aggregate['replayMeanMsMean'], 4)} ms | "
        f"{fmt_number(aggregate['replayShareMean'] * 100.0, 1)} % | "
        f"{fmt_number(aggregate['serializedBytesPerSecondMean'], 0)} | "
        f"{fmt_number(aggregate['bytesPerSampleMean'], 0)} | "
        f"{fmt_number(aggregate['replaySampleCountMean'], 0)} |"
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run F-S04 replay cost benchmark.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="Replay JSON produced by E-S01.",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "fixtures" / "f_s04_replay_cost_profiles.json",
        help="F-S04 profile config.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results",
        help="Directory where F-S04 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    replay = load_json(arguments.replay)
    config = load_json(arguments.profiles)
    results = run_profiles(replay, config)
    errors = validate_results(results, config)
    success = len(errors) == 0
    reference = next(result["aggregate"] for result in results if result["required"])
    metrics = {
        "profileCount": len(results),
        "repetitionsPerProfile": int(config["repetitions"]),
        "profileGroups": config["profiles"],
        "referenceVehicleCount": int(config["targetVehicleCount"]),
        "referenceReplaySampleHz": float(config["referenceReplaySampleHz"]),
        "referenceReplayShareMean": reference["replayShareMean"],
        "referenceWallOverheadRatio": reference["wallOverheadRatio"],
        "referenceSerializedBytesPerSecond": reference["serializedBytesPerSecondMean"],
        "profileErrorCount": len(errors),
    }
    summary = {
        "scenario": "F-S04",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "replayPath": arguments.replay.relative_to(repo_root).as_posix(),
        "profilesPath": arguments.profiles.relative_to(repo_root).as_posix(),
        "environment": environment_info(),
        "config": config,
        "thresholds": config["thresholds"],
        "profileErrors": errors,
        "profiles": results,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "f_s04_replay_cost_summary.json"
    report_path = arguments.results_dir / "F_S04_REPLAY_COST_RESULT.md"
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
