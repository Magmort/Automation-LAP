#!/usr/bin/env python3
"""Run E-S01: build and validate a standalone replay contract."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

REPLAY_SCHEMA_VERSION = "0.1.0"
SUPPORTED_SCHEMA_VERSIONS = {REPLAY_SCHEMA_VERSION}
MPS_PER_KMH = 1.0 / 3.6


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def rounded(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def vehicle_definitions(source_summary: dict[str, Any]) -> list[dict[str, Any]]:
    first_sample = source_summary["run"]["samples"][0]
    source_scene = source_summary.get("sceneInputPath", "")
    roles = {
        "ego": "ego",
        "target_front": "target_front",
        "target_rear": "target_rear",
    }
    labels = {
        "ego": "Ego",
        "target_front": "Target Front",
        "target_rear": "Target Rear",
    }
    vehicles = []
    for vehicle_id in first_sample["vehicles"]:
        vehicles.append(
            {
                "id": vehicle_id,
                "label": labels.get(vehicle_id, vehicle_id),
                "role": roles.get(vehicle_id, "traffic"),
                "lengthM": 4.4 if vehicle_id == "ego" else 4.5,
                "widthM": 1.9,
                "sourceScene": source_scene,
            }
        )
    return vehicles


def replay_frame_from_sample(sample: dict[str, Any]) -> dict[str, Any]:
    vehicles: dict[str, dict[str, Any]] = {}
    for vehicle_id, vehicle in sample["vehicles"].items():
        vehicles[vehicle_id] = {
            "xM": rounded(vehicle["x"]),
            "yM": rounded(vehicle["y"]),
            "headingRad": rounded(vehicle["heading"]),
            "progressM": rounded(vehicle["progressM"]),
            "wrappedProgressM": rounded(vehicle["wrappedProgressM"]),
            "lateralOffsetM": rounded(vehicle["lateralOffsetM"]),
            "speedMps": rounded(float(vehicle["speedKmh"]) * MPS_PER_KMH),
            "offTrack": bool(vehicle["offTrack"]),
        }
    return {
        "timeS": rounded(sample["timeS"]),
        "vehicles": vehicles,
        "signals": {
            "frontGapM": rounded(sample["frontGapM"]) if sample["frontGapM"] is not None else None,
            "rearGapM": rounded(sample["rearGapM"]) if sample["rearGapM"] is not None else None,
            "gapSafe": bool(sample["gapSafe"]),
            "contact": bool(sample["contact"]),
        },
    }


def build_events(source_summary: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = source_summary["run"]["metrics"]
    return [
        {
            "id": "gap_safe_start",
            "timeS": 0.0,
            "type": "state",
            "vehicleId": "ego",
            "label": "Target corridor gap is safe",
        },
        {
            "id": "rejoin_started",
            "timeS": rounded(metrics["rejoinStartedS"]),
            "type": "maneuver",
            "vehicleId": "ego",
            "label": "Ego starts rejoin",
        },
        {
            "id": "rejoin_completed",
            "timeS": rounded(metrics["rejoinCompletedS"]),
            "type": "maneuver",
            "vehicleId": "ego",
            "label": "Ego completes rejoin",
        },
    ]


def build_replay(
    source_summary: dict[str, Any],
    track: dict[str, Any],
    source_path: Path,
    track_path: Path,
) -> dict[str, Any]:
    frames = [replay_frame_from_sample(sample) for sample in source_summary["run"]["samples"]]
    duration_s = float(source_summary["run"]["durationS"])
    sample_interval_s = frames[1]["timeS"] - frames[0]["timeS"] if len(frames) > 1 else duration_s
    keyframes = [
        {"timeS": frame["timeS"], "frameIndex": index}
        for index, frame in enumerate(frames)
        if index % 4 == 0 or index == len(frames) - 1
    ]
    return {
        "kind": "AutomationLapReplay",
        "schemaVersion": REPLAY_SCHEMA_VERSION,
        "replayId": "e-s01-d-s05-rejoin",
        "createdAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "units": {
            "time": "s",
            "distance": "m",
            "speed": "m/s",
            "angle": "rad",
        },
        "source": {
            "experiment": "D-S05",
            "summaryPath": source_path.as_posix(),
            "summarySha256": sha256_file(source_path),
            "trackPath": track_path.as_posix(),
            "trackSha256": sha256_file(track_path),
        },
        "timeline": {
            "durationS": rounded(duration_s),
            "sampleIntervalS": rounded(sample_interval_s),
            "frameCount": len(frames),
            "vehicleIds": [vehicle["id"] for vehicle in vehicle_definitions(source_summary)],
        },
        "track": track,
        "vehicles": vehicle_definitions(source_summary),
        "events": build_events(source_summary),
        "index": {
            "kind": "fixed-keyframe",
            "keyframeIntervalS": 1.0,
            "keyframes": keyframes,
        },
        "frames": frames,
    }


def validate_replay(replay: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_top_level = [
        "kind",
        "schemaVersion",
        "replayId",
        "units",
        "source",
        "timeline",
        "track",
        "vehicles",
        "events",
        "index",
        "frames",
    ]
    for field in required_top_level:
        if field not in replay:
            errors.append(f"missing top-level field: {field}")
    if errors:
        return errors
    if replay["kind"] != "AutomationLapReplay":
        errors.append("invalid replay kind")
    if replay["schemaVersion"] not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"unsupported schema version: {replay['schemaVersion']}")
    if replay["units"] != {"time": "s", "distance": "m", "speed": "m/s", "angle": "rad"}:
        errors.append("invalid units")
    frames = replay["frames"]
    if replay["timeline"]["frameCount"] != len(frames):
        errors.append("timeline frameCount does not match frames length")
    if not frames:
        errors.append("replay has no frames")
        return errors
    vehicle_ids = replay["timeline"]["vehicleIds"]
    for index, frame in enumerate(frames):
        if index > 0 and frame["timeS"] <= frames[index - 1]["timeS"]:
            errors.append(f"frame time is not strictly increasing at index {index}")
        if sorted(frame["vehicles"].keys()) != sorted(vehicle_ids):
            errors.append(f"frame vehicle set mismatch at index {index}")
        for vehicle_id, vehicle in frame["vehicles"].items():
            for field in ("xM", "yM", "headingRad", "progressM", "wrappedProgressM", "lateralOffsetM", "speedMps"):
                if field not in vehicle:
                    errors.append(f"missing {field} for {vehicle_id} at frame {index}")
    if abs(frames[0]["timeS"]) > 1e-9:
        errors.append("first frame is not at t=0")
    if abs(frames[-1]["timeS"] - replay["timeline"]["durationS"]) > replay["timeline"]["sampleIntervalS"] + 1e-9:
        errors.append("last frame does not cover replay duration")
    for event in replay["events"]:
        if event["timeS"] < 0.0 or event["timeS"] > replay["timeline"]["durationS"]:
            errors.append(f"event outside timeline: {event['id']}")
    keyframes = replay["index"]["keyframes"]
    if not keyframes or keyframes[0]["frameIndex"] != 0:
        errors.append("index does not start at frame 0")
    if keyframes[-1]["frameIndex"] != len(frames) - 1:
        errors.append("index does not include final frame")
    return errors


def lerp(left: float, right: float, ratio: float) -> float:
    return left + (right - left) * ratio


def seek_replay(replay: dict[str, Any], time_s: float) -> dict[str, Any]:
    frames = replay["frames"]
    times = [frame["timeS"] for frame in frames]
    if time_s < times[0] or time_s > times[-1]:
        raise ValueError(f"seek time outside replay: {time_s}")
    right_index = bisect.bisect_left(times, time_s)
    if right_index < len(times) and abs(times[right_index] - time_s) < 1e-9:
        return {"mode": "exact", "timeS": time_s, "leftFrameIndex": right_index, "rightFrameIndex": right_index}
    left_index = max(0, right_index - 1)
    right_index = min(len(frames) - 1, right_index)
    left_time = times[left_index]
    right_time = times[right_index]
    ratio = (time_s - left_time) / max(right_time - left_time, 1e-9)
    vehicles: dict[str, dict[str, Any]] = {}
    for vehicle_id in replay["timeline"]["vehicleIds"]:
        left_vehicle = frames[left_index]["vehicles"][vehicle_id]
        right_vehicle = frames[right_index]["vehicles"][vehicle_id]
        vehicles[vehicle_id] = {
            "xM": lerp(left_vehicle["xM"], right_vehicle["xM"], ratio),
            "yM": lerp(left_vehicle["yM"], right_vehicle["yM"], ratio),
            "headingRad": lerp(left_vehicle["headingRad"], right_vehicle["headingRad"], ratio),
            "speedMps": lerp(left_vehicle["speedMps"], right_vehicle["speedMps"], ratio),
        }
    return {
        "mode": "interpolated",
        "timeS": time_s,
        "leftFrameIndex": left_index,
        "rightFrameIndex": right_index,
        "ratio": ratio,
        "vehicles": vehicles,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# E-S01 - Contrat replay autonome",
        "",
        "- **Expérience :** E - Replay minimal",
        "- **Scénario :** E-S01",
        f"- **Statut :** {'validé avec réserves' if summary['success'] else 'échec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** générer et charger un replay autonome sans recalculer la simulation source.",
        "- **Réserve :** format JSON lisible, non optimisé, issu d'un scénario déterministe D-S05.",
        "",
        "## Fichier replay",
        "",
        f"- Chemin : `{summary['replayPath']}`",
        f"- Taille : {metrics['replayFileBytes']} octets",
        f"- Durée : {fmt_number(metrics['durationS'])} s",
        f"- Frames : {metrics['frameCount']}",
        f"- Véhicules : {metrics['vehicleCount']}",
        f"- Événements : {metrics['eventCount']}",
        f"- Points de piste embarqués : {metrics['trackPointCount']}",
        "",
        "## Validation",
        "",
        f"- Erreurs de structure : {metrics['validationErrorCount']}",
        f"- Checks de seek : {metrics['seekCheckCount']}",
        f"- Modes de seek : {', '.join(metrics['seekModes'])}",
        f"- Version supportée : {'oui' if metrics['versionSupported'] else 'non'}",
        "",
        "## Décision",
        "",
        (
            "E-S01 est valide avec réserves. Le prototype peut passer à E-S02 pour tester la navigation temporelle avant/arrière."
            if summary["success"]
            else "E-S01 est à corriger avant de tester la navigation temporelle."
        ),
        "",
    ]
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run E-S01 replay contract scenario.")
    parser.add_argument(
        "--source",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "d_s05_rejoin_summary.json",
        help="Dynamic source summary used to build the replay.",
    )
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition snapshot to embed into the replay.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results",
        help="Directory where E-S01 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    source = load_json(arguments.source)
    track = load_json(arguments.track)
    replay = build_replay(
        source,
        track,
        arguments.source.relative_to(repo_root),
        arguments.track.relative_to(repo_root),
    )
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    replay_path = arguments.results_dir / "e_s01_minimal_replay.replay.json"
    with replay_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(replay, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")

    loaded_replay = load_json(replay_path)
    validation_errors = validate_replay(loaded_replay)
    seek_times = [
        0.0,
        0.375,
        3.13,
        float(loaded_replay["timeline"]["durationS"]) * 0.5 + 0.07,
        float(loaded_replay["timeline"]["durationS"]),
    ]
    seek_results = [seek_replay(loaded_replay, time_s) for time_s in seek_times]
    metrics = {
        "replayFileBytes": replay_path.stat().st_size,
        "durationS": loaded_replay["timeline"]["durationS"],
        "frameCount": loaded_replay["timeline"]["frameCount"],
        "vehicleCount": len(loaded_replay["vehicles"]),
        "eventCount": len(loaded_replay["events"]),
        "trackPointCount": len(loaded_replay["track"]["centerline"]),
        "validationErrorCount": len(validation_errors),
        "seekCheckCount": len(seek_results),
        "seekModes": sorted({result["mode"] for result in seek_results}),
        "versionSupported": loaded_replay["schemaVersion"] in SUPPORTED_SCHEMA_VERSIONS,
    }
    success = (
        metrics["validationErrorCount"] == 0
        and metrics["frameCount"] > 0
        and metrics["vehicleCount"] == 3
        and metrics["eventCount"] >= 3
        and metrics["trackPointCount"] >= 4
        and metrics["seekCheckCount"] == len(seek_times)
        and metrics["versionSupported"]
        and metrics["replayFileBytes"] > 0
    )
    summary = {
        "scenario": "E-S01",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sourcePath": arguments.source.relative_to(repo_root).as_posix(),
        "trackPath": arguments.track.relative_to(repo_root).as_posix(),
        "replayPath": replay_path.relative_to(repo_root).as_posix(),
        "validationErrors": validation_errors,
        "seekChecks": seek_results,
        "metrics": metrics,
    }
    summary_path = arguments.results_dir / "e_s01_replay_contract_summary.json"
    report_path = arguments.results_dir / "E_S01_REPLAY_CONTRACT_RESULT.md"
    with summary_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with report_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_markdown(summary))
    print(f"Wrote {replay_path.relative_to(repo_root)}")
    print(f"Wrote {summary_path.relative_to(repo_root)}")
    print(f"Wrote {report_path.relative_to(repo_root)}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
