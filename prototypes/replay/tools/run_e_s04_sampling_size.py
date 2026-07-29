#!/usr/bin/env python3
"""Run E-S04: measure replay size across sampling frequencies."""

from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

SUPPORTED_SCHEMA_VERSIONS = {"0.1.0"}


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


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def lerp(left: float, right: float, ratio: float) -> float:
    return left + (right - left) * ratio


def lerp_optional(left: float | None, right: float | None, ratio: float) -> float | None:
    if left is None or right is None:
        return left if ratio < 0.5 else right
    return lerp(float(left), float(right), ratio)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def seek_replay(replay: dict[str, Any], requested_time_s: float) -> dict[str, Any]:
    frames = replay["frames"]
    times = [frame["timeS"] for frame in frames]
    clamped_time_s = clamp(requested_time_s, times[0], times[-1])
    right_index = bisect.bisect_left(times, clamped_time_s)
    if right_index < len(times) and abs(times[right_index] - clamped_time_s) < 1e-9:
        frame = frames[right_index]
        return {
            "mode": "exact",
            "timeS": clamped_time_s,
            "vehicles": frame["vehicles"],
            "signals": frame["signals"],
        }

    left_index = max(0, right_index - 1)
    right_index = min(len(frames) - 1, right_index)
    left_time = times[left_index]
    right_time = times[right_index]
    ratio = (clamped_time_s - left_time) / max(right_time - left_time, 1e-9)

    vehicles: dict[str, dict[str, Any]] = {}
    for vehicle_id in replay["timeline"]["vehicleIds"]:
        left_vehicle = frames[left_index]["vehicles"][vehicle_id]
        right_vehicle = frames[right_index]["vehicles"][vehicle_id]
        vehicles[vehicle_id] = {
            "xM": rounded(lerp(left_vehicle["xM"], right_vehicle["xM"], ratio)),
            "yM": rounded(lerp(left_vehicle["yM"], right_vehicle["yM"], ratio)),
            "headingRad": rounded(lerp(left_vehicle["headingRad"], right_vehicle["headingRad"], ratio)),
            "progressM": rounded(lerp(left_vehicle["progressM"], right_vehicle["progressM"], ratio)),
            "wrappedProgressM": rounded(lerp(left_vehicle["wrappedProgressM"], right_vehicle["wrappedProgressM"], ratio)),
            "lateralOffsetM": rounded(lerp(left_vehicle["lateralOffsetM"], right_vehicle["lateralOffsetM"], ratio)),
            "speedMps": rounded(lerp(left_vehicle["speedMps"], right_vehicle["speedMps"], ratio)),
            "offTrack": bool(left_vehicle["offTrack"] or right_vehicle["offTrack"]),
        }

    left_signals = frames[left_index]["signals"]
    right_signals = frames[right_index]["signals"]
    front_gap = lerp_optional(left_signals["frontGapM"], right_signals["frontGapM"], ratio)
    rear_gap = lerp_optional(left_signals["rearGapM"], right_signals["rearGapM"], ratio)
    return {
        "mode": "interpolated",
        "timeS": clamped_time_s,
        "vehicles": vehicles,
        "signals": {
            "frontGapM": rounded(front_gap) if front_gap is not None else None,
            "rearGapM": rounded(rear_gap) if rear_gap is not None else None,
            "gapSafe": bool(left_signals["gapSafe"] and right_signals["gapSafe"]),
            "contact": bool(left_signals["contact"] or right_signals["contact"]),
        },
    }


def sample_times(duration_s: float, sample_interval_s: float) -> list[float]:
    times = []
    index = 0
    while True:
        time_s = rounded(index * sample_interval_s)
        if time_s > duration_s + 1e-9:
            break
        times.append(time_s)
        index += 1
    if not times or abs(times[-1] - duration_s) > 1e-9:
        times.append(rounded(duration_s))
    return times


def build_frame(replay: dict[str, Any], time_s: float) -> dict[str, Any]:
    state = seek_replay(replay, time_s)
    return {
        "timeS": rounded(state["timeS"]),
        "vehicles": deepcopy(state["vehicles"]),
        "signals": deepcopy(state["signals"]),
    }


def build_keyframes(frames: list[dict[str, Any]], sample_interval_s: float) -> list[dict[str, Any]]:
    frames_per_keyframe = max(1, int(round(1.0 / sample_interval_s)))
    keyframes = [
        {"timeS": frame["timeS"], "frameIndex": index}
        for index, frame in enumerate(frames)
        if index % frames_per_keyframe == 0 or index == len(frames) - 1
    ]
    if keyframes[-1]["frameIndex"] != len(frames) - 1:
        keyframes.append({"timeS": frames[-1]["timeS"], "frameIndex": len(frames) - 1})
    return keyframes


def resample_replay(replay: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    sample_interval_s = float(profile["sampleIntervalS"])
    duration_s = float(replay["timeline"]["durationS"])
    frames = [build_frame(replay, time_s) for time_s in sample_times(duration_s, sample_interval_s)]
    variant = deepcopy(replay)
    variant["replayId"] = f"e-s04-{profile['id']}"
    variant["createdAtUtc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    variant["timeline"]["sampleIntervalS"] = rounded(sample_interval_s)
    variant["timeline"]["frameCount"] = len(frames)
    variant["index"] = {
        "kind": "fixed-keyframe",
        "keyframeIntervalS": 1.0,
        "keyframes": build_keyframes(frames, sample_interval_s),
    }
    variant["resampling"] = {
        "scenario": "E-S04",
        "profileId": profile["id"],
        "label": profile["label"],
        "sourceReplayId": replay["replayId"],
        "sourceSampleIntervalS": replay["timeline"]["sampleIntervalS"],
        "method": "linear interpolation between E-S01 frames",
    }
    variant["frames"] = frames
    return variant


def validate_variant(replay: dict[str, Any], expected_interval_s: float) -> list[str]:
    errors: list[str] = []
    if replay.get("kind") != "AutomationLapReplay":
        errors.append("invalid replay kind")
    if replay.get("schemaVersion") not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"unsupported schema version: {replay.get('schemaVersion')}")
    frames = replay.get("frames", [])
    if not frames:
        errors.append("variant has no frames")
        return errors
    if replay["timeline"]["frameCount"] != len(frames):
        errors.append("timeline frameCount does not match frames length")
    if abs(float(replay["timeline"]["sampleIntervalS"]) - expected_interval_s) > 1e-9:
        errors.append("timeline sample interval mismatch")
    for index, frame in enumerate(frames):
        if index > 0 and frame["timeS"] <= frames[index - 1]["timeS"]:
            errors.append(f"non-monotonic frame time at index {index}")
        for vehicle in frame["vehicles"].values():
            for field in ("xM", "yM", "headingRad", "progressM", "wrappedProgressM", "lateralOffsetM", "speedMps"):
                if not math.isfinite(float(vehicle[field])):
                    errors.append(f"non-finite vehicle field {field} at frame {index}")
    if abs(frames[0]["timeS"]) > 1e-9:
        errors.append("first frame is not t=0")
    duration_s = float(replay["timeline"]["durationS"])
    if abs(frames[-1]["timeS"] - duration_s) > min(expected_interval_s, 1e-6):
        errors.append("last frame does not cover duration")
    if not replay["index"]["keyframes"] or replay["index"]["keyframes"][0]["frameIndex"] != 0:
        errors.append("index does not start at frame 0")
    if replay["index"]["keyframes"][-1]["frameIndex"] != len(frames) - 1:
        errors.append("index does not include final frame")
    return errors


def nearest_frame_delta_s(replay: dict[str, Any], event_time_s: float) -> float:
    times = [frame["timeS"] for frame in replay["frames"]]
    right_index = bisect.bisect_left(times, event_time_s)
    candidates = []
    if right_index < len(times):
        candidates.append(abs(times[right_index] - event_time_s))
    if right_index > 0:
        candidates.append(abs(times[right_index - 1] - event_time_s))
    return min(candidates)


def write_replay(path: Path, replay: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(replay, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")


def build_profile_results(
    source_replay: dict[str, Any],
    profiles: list[dict[str, Any]],
    variants_dir: Path,
    repo_root: Path,
) -> list[dict[str, Any]]:
    results = []
    for profile in profiles:
        interval_s = float(profile["sampleIntervalS"])
        variant = resample_replay(source_replay, profile)
        output_path = variants_dir / f"e_s04_{profile['id']}.replay.json"
        write_replay(output_path, variant)
        validation_errors = validate_variant(variant, interval_s)
        event_deltas = [nearest_frame_delta_s(variant, event["timeS"]) for event in variant["events"]]
        file_bytes = output_path.stat().st_size
        duration_s = float(variant["timeline"]["durationS"])
        frame_count = int(variant["timeline"]["frameCount"])
        results.append(
            {
                "profileId": profile["id"],
                "label": profile["label"],
                "sampleIntervalS": rounded(interval_s),
                "sampleHz": rounded(1.0 / interval_s, 3),
                "frameCount": frame_count,
                "fileBytes": file_bytes,
                "bytesPerSecond": rounded(file_bytes / duration_s, 3),
                "bytesPerFrame": rounded(file_bytes / frame_count, 3),
                "keyframeCount": len(variant["index"]["keyframes"]),
                "eventNearestFrameMaxDeltaS": rounded(max(event_deltas) if event_deltas else 0.0),
                "eventNearestFrameMeanDeltaS": rounded(sum(event_deltas) / max(len(event_deltas), 1)),
                "validationErrorCount": len(validation_errors),
                "validationErrors": validation_errors,
                "outputPath": output_path.relative_to(repo_root).as_posix(),
            }
        )
    return results


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# E-S04 - Taille et frequence d'echantillonnage",
        "",
        "- **Experience :** E - Replay minimal",
        "- **Scenario :** E-S04",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** mesurer la taille brute du replay JSON selon plusieurs frequences de frames.",
        "- **Reserve :** mesure hors compression, hors format binaire et sur un scenario court a trois voitures.",
        "",
        "## Entrees",
        "",
        f"- Replay source : `{summary['sourceReplayPath']}`",
        f"- Profils : `{summary['profilesPath']}`",
        "",
        "## Metriques globales",
        "",
        f"- Profils testes : {metrics['profileCount']}",
        f"- Duree replay : {fmt_number(metrics['durationS'])} s",
        f"- Vehicules : {metrics['vehicleCount']}",
        f"- Evenements : {metrics['eventCount']}",
        f"- Taille min/max : {metrics['minFileBytes']} / {metrics['maxFileBytes']} octets",
        f"- Debit min/max : {fmt_number(metrics['minBytesPerSecond'], 1)} / {fmt_number(metrics['maxBytesPerSecond'], 1)} octets/s",
        f"- Erreurs de validation : {metrics['validationErrorCount']}",
        "",
        "## Profils",
        "",
        "| Profil | Hz | Intervalle | Frames | Taille | Octets/s | Octets/frame | Ecart evenement max |",
        "| --- | ---:| ---:| ---:| ---:| ---:| ---:| ---:|",
    ]
    for result in summary["profiles"]:
        lines.append(
            "| "
            f"{result['profileId']} | "
            f"{fmt_number(result['sampleHz'], 2)} | "
            f"{fmt_number(result['sampleIntervalS'], 3)} s | "
            f"{result['frameCount']} | "
            f"{result['fileBytes']} | "
            f"{fmt_number(result['bytesPerSecond'], 1)} | "
            f"{fmt_number(result['bytesPerFrame'], 1)} | "
            f"{fmt_number(result['eventNearestFrameMaxDeltaS'], 3)} s |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "E-S04 est valide avec reserves. Les donnees permettent de choisir une frequence candidate avant de tester la compatibilite E-S05."
                if summary["success"]
                else "E-S04 est a corriger avant de poursuivre vers E-S05."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run E-S04 replay sampling size scenario.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="Replay JSON produced by E-S01.",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "fixtures" / "e_s04_sampling_profiles.json",
        help="Sampling profiles JSON.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results",
        help="Directory where E-S04 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    source_replay = load_json(arguments.replay)
    profiles_config = load_json(arguments.profiles)
    variants_dir = arguments.results_dir / "e_s04_variants"
    profile_results = build_profile_results(source_replay, profiles_config["profiles"], variants_dir, repo_root)

    file_sizes = [result["fileBytes"] for result in profile_results]
    bytes_per_second = [result["bytesPerSecond"] for result in profile_results]
    validation_error_count = sum(result["validationErrorCount"] for result in profile_results)
    size_is_monotonic = all(
        profile_results[index]["fileBytes"] < profile_results[index + 1]["fileBytes"]
        for index in range(max(0, len(profile_results) - 1))
    )
    event_coverage_ok = all(
        result["eventNearestFrameMaxDeltaS"] <= result["sampleIntervalS"] * 0.5 + 1e-9
        for result in profile_results
    )
    metrics = {
        "profileCount": len(profile_results),
        "durationS": source_replay["timeline"]["durationS"],
        "vehicleCount": len(source_replay["vehicles"]),
        "eventCount": len(source_replay["events"]),
        "sourceFileBytes": arguments.replay.stat().st_size,
        "minFileBytes": min(file_sizes),
        "maxFileBytes": max(file_sizes),
        "minBytesPerSecond": min(bytes_per_second),
        "maxBytesPerSecond": max(bytes_per_second),
        "validationErrorCount": validation_error_count,
        "sizeIsMonotonicWithFrequency": size_is_monotonic,
        "eventCoverageOk": event_coverage_ok,
        "referenceProfileId": "4hz_reference",
        "referenceProfileFileBytes": next(result["fileBytes"] for result in profile_results if result["profileId"] == "4hz_reference"),
    }
    success = (
        metrics["profileCount"] >= 5
        and metrics["validationErrorCount"] == 0
        and metrics["sizeIsMonotonicWithFrequency"]
        and metrics["eventCoverageOk"]
        and metrics["minFileBytes"] > 0
        and metrics["maxFileBytes"] > metrics["minFileBytes"]
    )
    summary = {
        "scenario": "E-S04",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sourceReplayPath": arguments.replay.relative_to(repo_root).as_posix(),
        "profilesPath": arguments.profiles.relative_to(repo_root).as_posix(),
        "variantsDir": variants_dir.relative_to(repo_root).as_posix(),
        "profiles": profile_results,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "e_s04_sampling_size_summary.json"
    report_path = arguments.results_dir / "E_S04_SAMPLING_SIZE_RESULT.md"
    with summary_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with report_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_markdown(summary))
    print(f"Wrote {summary_path.relative_to(repo_root)}")
    print(f"Wrote {report_path.relative_to(repo_root)}")
    print(f"Wrote {variants_dir.relative_to(repo_root)}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
