#!/usr/bin/env python3
"""Run E-S03: validate replay event index and event jumps."""

from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
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


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def lerp(left: float, right: float, ratio: float) -> float:
    return left + (right - left) * ratio


def seek_replay(replay: dict[str, Any], requested_time_s: float) -> dict[str, Any]:
    frames = replay["frames"]
    times = [frame["timeS"] for frame in frames]
    clamped_time_s = clamp(requested_time_s, times[0], times[-1])
    right_index = bisect.bisect_left(times, clamped_time_s)
    if right_index < len(times) and abs(times[right_index] - clamped_time_s) < 1e-9:
        frame = frames[right_index]
        return {
            "mode": "exact",
            "requestedTimeS": requested_time_s,
            "timeS": clamped_time_s,
            "clamped": abs(requested_time_s - clamped_time_s) > 1e-9,
            "leftFrameIndex": right_index,
            "rightFrameIndex": right_index,
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
            "xM": lerp(left_vehicle["xM"], right_vehicle["xM"], ratio),
            "yM": lerp(left_vehicle["yM"], right_vehicle["yM"], ratio),
            "headingRad": lerp(left_vehicle["headingRad"], right_vehicle["headingRad"], ratio),
            "progressM": lerp(left_vehicle["progressM"], right_vehicle["progressM"], ratio),
            "wrappedProgressM": lerp(left_vehicle["wrappedProgressM"], right_vehicle["wrappedProgressM"], ratio),
            "lateralOffsetM": lerp(left_vehicle["lateralOffsetM"], right_vehicle["lateralOffsetM"], ratio),
            "speedMps": lerp(left_vehicle["speedMps"], right_vehicle["speedMps"], ratio),
            "offTrack": bool(left_vehicle["offTrack"] or right_vehicle["offTrack"]),
        }
    left_signals = frames[left_index]["signals"]
    right_signals = frames[right_index]["signals"]
    return {
        "mode": "interpolated",
        "requestedTimeS": requested_time_s,
        "timeS": clamped_time_s,
        "clamped": abs(requested_time_s - clamped_time_s) > 1e-9,
        "leftFrameIndex": left_index,
        "rightFrameIndex": right_index,
        "ratio": ratio,
        "vehicles": vehicles,
        "signals": {
            "frontGapM": lerp(left_signals["frontGapM"], right_signals["frontGapM"], ratio),
            "rearGapM": lerp(left_signals["rearGapM"], right_signals["rearGapM"], ratio),
            "gapSafe": bool(left_signals["gapSafe"] and right_signals["gapSafe"]),
            "contact": bool(left_signals["contact"] or right_signals["contact"]),
        },
    }


def validate_event_index(replay: dict[str, Any], script: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if replay.get("kind") != "AutomationLapReplay":
        errors.append("invalid replay kind")
    if replay.get("schemaVersion") not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"unsupported schema version: {replay.get('schemaVersion')}")
    events = replay.get("events", [])
    event_ids = [event["id"] for event in events]
    if len(event_ids) != len(set(event_ids)):
        errors.append("event ids are not unique")
    duration_s = float(replay["timeline"]["durationS"])
    for event in events:
        if event["timeS"] < 0.0 or event["timeS"] > duration_s:
            errors.append(f"event outside replay duration: {event['id']}")
        if event.get("vehicleId") not in replay["timeline"]["vehicleIds"]:
            errors.append(f"event vehicle id is unknown: {event['id']}")
    if events != sorted(events, key=lambda event: event["timeS"]):
        errors.append("events are not sorted by time")
    for event_id in script["requiredEvents"]:
        if event_id not in event_ids:
            errors.append(f"missing required event: {event_id}")
    expected = script["expectedChronology"]
    actual = [event_id for event_id in event_ids if event_id in expected]
    if actual != expected:
        errors.append("required event chronology mismatch")
    return errors


def build_event_jumps(replay: dict[str, Any], script: dict[str, Any]) -> list[dict[str, Any]]:
    event_by_id = {event["id"]: event for event in replay["events"]}
    duration_s = float(replay["timeline"]["durationS"])
    pre_roll = float(script["preRollS"])
    post_roll = float(script["postRollS"])
    jumps = []
    for event_id in script["requiredEvents"]:
        event = event_by_id[event_id]
        before = seek_replay(replay, event["timeS"] - pre_roll)
        at_event = seek_replay(replay, event["timeS"])
        after = seek_replay(replay, event["timeS"] + post_roll)
        ego_at = at_event["vehicles"][event["vehicleId"]]
        jumps.append(
            {
                "eventId": event_id,
                "eventType": event["type"],
                "label": event["label"],
                "vehicleId": event["vehicleId"],
                "eventTimeS": event["timeS"],
                "preRollTimeS": before["timeS"],
                "postRollTimeS": after["timeS"],
                "preRollClamped": before["clamped"],
                "postRollClamped": after["clamped"],
                "eventSeekMode": at_event["mode"],
                "eventFrameLeft": at_event["leftFrameIndex"],
                "eventFrameRight": at_event["rightFrameIndex"],
                "egoProgressM": ego_at["progressM"],
                "egoLateralOffsetM": ego_at["lateralOffsetM"],
                "frontGapM": at_event["signals"]["frontGapM"],
                "rearGapM": at_event["signals"]["rearGapM"],
                "insideDuration": 0.0 <= before["timeS"] <= duration_s and 0.0 <= after["timeS"] <= duration_s,
                "finiteState": math.isfinite(ego_at["xM"]) and math.isfinite(ego_at["yM"]) and math.isfinite(ego_at["speedMps"]),
            }
        )
    return jumps


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# E-S03 - Evenements et saut vers evenement",
        "",
        "- **Experience :** E - Replay minimal",
        "- **Scenario :** E-S03",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** indexer les evenements du replay et sauter directement sur chaque evenement avec contexte pre/post-roll.",
        "- **Reserve :** test hors UI ; les evenements proviennent du scenario deterministe D-S05.",
        "",
        "## Entrees",
        "",
        f"- Replay : `{summary['replayPath']}`",
        f"- Script : `{summary['scriptPath']}`",
        "",
        "## Metriques",
        "",
        f"- Evenements replay : {metrics['eventCount']}",
        f"- Evenements requis trouves : {metrics['requiredEventFoundCount']} / {metrics['requiredEventCount']}",
        f"- Jumps executes : {metrics['jumpCount']}",
        f"- Jumps interpoles : {metrics['interpolatedJumpCount']}",
        f"- Contextes pre/post-roll valides : {metrics['validContextCount']}",
        f"- Clamps pre/post-roll : {metrics['contextClampCount']}",
        f"- Erreurs index evenement : {metrics['eventIndexErrorCount']}",
        "",
        "## Evenements",
        "",
        "| Evenement | Temps | Mode | Pre | Post | Offset ego |",
        "| --- | ---:| --- | ---:| ---:| ---:|",
    ]
    for jump in summary["jumps"]:
        lines.append(
            "| "
            f"{jump['eventId']} | "
            f"{fmt_number(jump['eventTimeS'], 3)} | "
            f"{jump['eventSeekMode']} | "
            f"{fmt_number(jump['preRollTimeS'])} | "
            f"{fmt_number(jump['postRollTimeS'])} | "
            f"{fmt_number(jump['egoLateralOffsetM'], 3)} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "E-S03 est valide avec reserves. Le prototype peut passer a E-S04 pour mesurer taille et frequence d'echantillonnage."
                if summary["success"]
                else "E-S03 est a corriger avant de mesurer taille et frequence d'echantillonnage."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run E-S03 event jump scenario.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="Replay JSON produced by E-S01.",
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "fixtures" / "e_s03_event_jump_script.json",
        help="Event jump script JSON.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results",
        help="Directory where E-S03 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    replay = load_json(arguments.replay)
    script = load_json(arguments.script)
    event_index_errors = validate_event_index(replay, script)
    jumps = build_event_jumps(replay, script) if not event_index_errors else []
    required_event_ids = set(script["requiredEvents"])
    replay_event_ids = {event["id"] for event in replay["events"]}
    metrics = {
        "eventCount": len(replay["events"]),
        "requiredEventCount": len(required_event_ids),
        "requiredEventFoundCount": len(required_event_ids & replay_event_ids),
        "jumpCount": len(jumps),
        "interpolatedJumpCount": sum(1 for jump in jumps if jump["eventSeekMode"] == "interpolated"),
        "validContextCount": sum(1 for jump in jumps if jump["insideDuration"] and jump["finiteState"]),
        "contextClampCount": sum(1 for jump in jumps if jump["preRollClamped"] or jump["postRollClamped"]),
        "eventIndexErrorCount": len(event_index_errors),
        "finiteJumpStates": all(jump["finiteState"] for jump in jumps),
        "eventTimesMonotonic": all(
            jumps[index]["eventTimeS"] <= jumps[index + 1]["eventTimeS"] for index in range(max(0, len(jumps) - 1))
        ),
    }
    success = (
        metrics["eventIndexErrorCount"] == 0
        and metrics["requiredEventFoundCount"] == metrics["requiredEventCount"]
        and metrics["jumpCount"] == metrics["requiredEventCount"]
        and metrics["interpolatedJumpCount"] >= 1
        and metrics["validContextCount"] == metrics["jumpCount"]
        and metrics["contextClampCount"] >= 1
        and metrics["finiteJumpStates"]
        and metrics["eventTimesMonotonic"]
    )
    summary = {
        "scenario": "E-S03",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "replayPath": arguments.replay.relative_to(repo_root).as_posix(),
        "scriptPath": arguments.script.relative_to(repo_root).as_posix(),
        "eventIndexErrors": event_index_errors,
        "jumps": jumps,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "e_s03_event_jump_summary.json"
    report_path = arguments.results_dir / "E_S03_EVENT_JUMP_RESULT.md"
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
