#!/usr/bin/env python3
"""Run E-S02: validate forward/backward replay navigation."""

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


def validate_replay_for_navigation(replay: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if replay.get("kind") != "AutomationLapReplay":
        errors.append("invalid replay kind")
    if replay.get("schemaVersion") not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"unsupported schema version: {replay.get('schemaVersion')}")
    frames = replay.get("frames", [])
    if not frames:
        errors.append("replay has no frames")
        return errors
    for index, frame in enumerate(frames):
        if index > 0 and frame["timeS"] <= frames[index - 1]["timeS"]:
            errors.append(f"non-monotonic frame time at index {index}")
    if abs(frames[0]["timeS"]) > 1e-9:
        errors.append("first frame is not t=0")
    if abs(frames[-1]["timeS"] - replay["timeline"]["durationS"]) > replay["timeline"]["sampleIntervalS"] + 1e-9:
        errors.append("last frame does not cover duration")
    return errors


def append_navigation_sample(
    trace: list[dict[str, Any]],
    replay: dict[str, Any],
    cursor_time_s: float,
    playback_time_s: float,
    command_label: str,
    command_type: str,
    requested_time_s: float | None = None,
) -> dict[str, Any]:
    state = seek_replay(replay, cursor_time_s if requested_time_s is None else requested_time_s)
    ego = state["vehicles"]["ego"]
    sample = {
        "playbackTimeS": playback_time_s,
        "replayTimeS": state["timeS"],
        "requestedReplayTimeS": state["requestedTimeS"],
        "commandLabel": command_label,
        "commandType": command_type,
        "seekMode": state["mode"],
        "clamped": state["clamped"],
        "ego": {
            "xM": ego["xM"],
            "yM": ego["yM"],
            "progressM": ego["progressM"],
            "lateralOffsetM": ego["lateralOffsetM"],
            "speedMps": ego["speedMps"],
        },
        "signals": state["signals"],
    }
    trace.append(sample)
    return sample


def run_navigation(replay: dict[str, Any], script: dict[str, Any]) -> dict[str, Any]:
    duration_s = float(replay["timeline"]["durationS"])
    sample_step_s = float(script["sampleStepS"])
    cursor_time_s = 0.0
    playback_time_s = 0.0
    trace: list[dict[str, Any]] = []
    command_results: list[dict[str, Any]] = []
    monotonic_failures = 0

    append_navigation_sample(trace, replay, cursor_time_s, playback_time_s, "initial", "initial")
    for command_index, command in enumerate(script["commands"]):
        label = command["label"]
        command_type = command["type"]
        before_time = cursor_time_s
        samples_before = len(trace)
        if command_type == "seek":
            requested = float(command["targetTimeS"])
            cursor_time_s = clamp(requested, 0.0, duration_s)
            append_navigation_sample(trace, replay, cursor_time_s, playback_time_s, label, command_type, requested)
        elif command_type == "pause":
            playback_time_s += float(command["durationS"])
            append_navigation_sample(trace, replay, cursor_time_s, playback_time_s, label, command_type)
        elif command_type == "play":
            direction = 1.0 if command["direction"] == "forward" else -1.0
            speed = float(command["speed"])
            elapsed = 0.0
            previous_time = cursor_time_s
            while elapsed + 1e-9 < float(command["durationS"]):
                step = min(sample_step_s, float(command["durationS"]) - elapsed)
                elapsed += step
                playback_time_s += step
                requested_cursor_time_s = cursor_time_s + direction * speed * step
                cursor_time_s = clamp(requested_cursor_time_s, 0.0, duration_s)
                if direction > 0.0 and cursor_time_s + 1e-9 < previous_time:
                    monotonic_failures += 1
                if direction < 0.0 and cursor_time_s - 1e-9 > previous_time:
                    monotonic_failures += 1
                previous_time = cursor_time_s
                append_navigation_sample(
                    trace,
                    replay,
                    cursor_time_s,
                    playback_time_s,
                    label,
                    command_type,
                    requested_cursor_time_s,
                )
                if (direction > 0.0 and cursor_time_s >= duration_s) or (direction < 0.0 and cursor_time_s <= 0.0):
                    break
        else:
            raise ValueError(f"unsupported navigation command: {command_type}")
        command_results.append(
            {
                "index": command_index,
                "label": label,
                "type": command_type,
                "startReplayTimeS": before_time,
                "endReplayTimeS": cursor_time_s,
                "sampleCount": len(trace) - samples_before,
            }
        )
    return {
        "durationS": duration_s,
        "sampleStepS": sample_step_s,
        "trace": trace,
        "commandResults": command_results,
        "monotonicFailures": monotonic_failures,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# E-S02 - Navigation temporelle avant/arriere",
        "",
        "- **Experience :** E - Replay minimal",
        "- **Scenario :** E-S02",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** parcourir un replay autonome en avant, en arriere, en pause et par seek arbitraire.",
        "- **Reserve :** navigation hors UI Unity ; les sauts vers evenements restent dedies a E-S03.",
        "",
        "## Entrees",
        "",
        f"- Replay : `{summary['replayPath']}`",
        f"- Script : `{summary['scriptPath']}`",
        "",
        "## Metriques",
        "",
        f"- Commandes executees : {metrics['commandCount']}",
        f"- Samples navigation : {metrics['traceSampleCount']}",
        f"- Lectures avant : {metrics['forwardCommandCount']}",
        f"- Lectures arriere : {metrics['backwardCommandCount']}",
        f"- Seek arbitraires : {metrics['seekCommandCount']}",
        f"- Pauses : {metrics['pauseCommandCount']}",
        f"- Seek exacts : {metrics['exactSeekSamples']}",
        f"- Seek interpoles : {metrics['interpolatedSeekSamples']}",
        f"- Clamps aux bornes : {metrics['clampedSamples']}",
        f"- Echecs monotonicite : {metrics['monotonicFailures']}",
        f"- Replay time min/max : {fmt_number(metrics['minReplayTimeS'])} s / {fmt_number(metrics['maxReplayTimeS'])} s",
        "",
        "## Decision",
        "",
        (
            "E-S02 est valide avec reserves. Le prototype peut passer a E-S03 pour tester les evenements et le saut vers evenement."
            if summary["success"]
            else "E-S02 est a corriger avant de tester les evenements."
        ),
        "",
    ]
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run E-S02 replay navigation scenario.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="Replay JSON produced by E-S01.",
    )
    parser.add_argument(
        "--script",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "fixtures" / "e_s02_navigation_script.json",
        help="Navigation script JSON.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results",
        help="Directory where E-S02 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    replay = load_json(arguments.replay)
    script = load_json(arguments.script)
    validation_errors = validate_replay_for_navigation(replay)
    run = run_navigation(replay, script)
    trace = run["trace"]
    seek_commands = [command for command in script["commands"] if command["type"] == "seek"]
    play_commands = [command for command in script["commands"] if command["type"] == "play"]
    metrics = {
        "commandCount": len(script["commands"]),
        "traceSampleCount": len(trace),
        "forwardCommandCount": sum(1 for command in play_commands if command["direction"] == "forward"),
        "backwardCommandCount": sum(1 for command in play_commands if command["direction"] == "backward"),
        "seekCommandCount": len(seek_commands),
        "pauseCommandCount": sum(1 for command in script["commands"] if command["type"] == "pause"),
        "exactSeekSamples": sum(1 for sample in trace if sample["seekMode"] == "exact"),
        "interpolatedSeekSamples": sum(1 for sample in trace if sample["seekMode"] == "interpolated"),
        "clampedSamples": sum(1 for sample in trace if sample["clamped"]),
        "monotonicFailures": run["monotonicFailures"],
        "validationErrorCount": len(validation_errors),
        "minReplayTimeS": min(sample["replayTimeS"] for sample in trace),
        "maxReplayTimeS": max(sample["replayTimeS"] for sample in trace),
        "durationS": run["durationS"],
        "replayTimeRangeInsideBounds": all(0.0 <= sample["replayTimeS"] <= run["durationS"] for sample in trace),
        "finiteStateSamples": all(
            math.isfinite(sample["ego"]["xM"])
            and math.isfinite(sample["ego"]["yM"])
            and math.isfinite(sample["ego"]["speedMps"])
            for sample in trace
        ),
    }
    success = (
        metrics["validationErrorCount"] == 0
        and metrics["traceSampleCount"] > 0
        and metrics["forwardCommandCount"] >= 1
        and metrics["backwardCommandCount"] >= 1
        and metrics["seekCommandCount"] >= 3
        and metrics["pauseCommandCount"] >= 1
        and metrics["interpolatedSeekSamples"] >= 1
        and metrics["clampedSamples"] >= 2
        and metrics["monotonicFailures"] == 0
        and metrics["replayTimeRangeInsideBounds"]
        and metrics["finiteStateSamples"]
    )
    summary = {
        "scenario": "E-S02",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "replayPath": arguments.replay.relative_to(repo_root).as_posix(),
        "scriptPath": arguments.script.relative_to(repo_root).as_posix(),
        "validationErrors": validation_errors,
        "run": run,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "e_s02_navigation_summary.json"
    report_path = arguments.results_dir / "E_S02_NAVIGATION_RESULT.md"
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
