#!/usr/bin/env python3
"""Run E-S05: validate replay version and structural compatibility checks."""

from __future__ import annotations

import argparse
import json
import math
import sys
from copy import deepcopy
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

SUPPORTED_SCHEMA_VERSIONS = {"0.1.0"}
EXPECTED_UNITS = {"time": "s", "distance": "m", "speed": "m/s", "angle": "rad"}
REQUIRED_TOP_LEVEL_FIELDS = [
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


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def get_path(payload: Any, path: list[Any]) -> Any:
    current = payload
    for part in path:
        current = current[part]
    return current


def set_path(payload: Any, path: list[Any], value: Any) -> None:
    current = payload
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value


def remove_path(payload: Any, path: list[Any]) -> None:
    current = payload
    for part in path[:-1]:
        current = current[part]
    del current[path[-1]]


def apply_mutation(source_replay: dict[str, Any], mutation: dict[str, Any]) -> dict[str, Any] | str:
    mutation_type = mutation["type"]
    if mutation_type == "raw":
        return str(mutation["content"])

    replay = deepcopy(source_replay)
    replay["replayId"] = f"e-s05-{mutation_type}"
    replay["createdAtUtc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if mutation_type == "none":
        return replay
    if mutation_type == "set":
        set_path(replay, mutation["path"], mutation["value"])
        return replay
    if mutation_type == "remove":
        remove_path(replay, mutation["path"])
        return replay
    if mutation_type == "copy":
        set_path(replay, mutation["toPath"], get_path(replay, mutation["fromPath"]))
        return replay
    raise ValueError(f"unsupported mutation type: {mutation_type}")


def write_case_file(path: Path, payload: dict[str, Any] | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8", newline="\n")
        return
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")


def reject(error_code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "canLoad": False,
        "errorCode": error_code,
        "message": message,
        "details": details or [],
    }


def accept(details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "canLoad": True,
        "errorCode": "OK",
        "message": "Replay accepted by compatibility reader.",
        "details": details or [],
    }


def load_and_validate_replay(path: Path) -> dict[str, Any]:
    try:
        replay = load_json(path)
    except JSONDecodeError as exc:
        return reject("INVALID_JSON", f"Invalid JSON: {exc.msg}")

    if not isinstance(replay, dict):
        return reject("INVALID_ROOT", "Replay root must be an object.")

    missing_fields = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in replay]
    if missing_fields:
        return reject(
            "MISSING_FIELD",
            "Replay is missing required top-level fields.",
            [{"field": field} for field in missing_fields],
        )

    if replay["kind"] != "AutomationLapReplay":
        return reject("INVALID_KIND", f"Unsupported replay kind: {replay['kind']}")

    if replay["schemaVersion"] not in SUPPORTED_SCHEMA_VERSIONS:
        return reject("UNSUPPORTED_SCHEMA_VERSION", f"Unsupported schema version: {replay['schemaVersion']}")

    if replay["units"] != EXPECTED_UNITS:
        return reject("INVALID_UNITS", "Replay units do not match the expected SI contract.")

    timeline = replay["timeline"]
    frames = replay["frames"]
    if not isinstance(frames, list) or not frames:
        return reject("EMPTY_FRAMES", "Replay must contain at least one frame.")
    if timeline.get("frameCount") != len(frames):
        return reject(
            "FRAME_COUNT_MISMATCH",
            "Timeline frameCount does not match frames length.",
            [{"timelineFrameCount": timeline.get("frameCount"), "actualFrameCount": len(frames)}],
        )

    vehicle_ids = timeline.get("vehicleIds", [])
    if not vehicle_ids:
        return reject("MISSING_VEHICLE_IDS", "Timeline does not declare vehicle ids.")

    for index, frame in enumerate(frames):
        if index > 0 and frame["timeS"] <= frames[index - 1]["timeS"]:
            return reject(
                "NON_MONOTONIC_FRAME_TIME",
                "Frame times must be strictly increasing.",
                [{"frameIndex": index, "previousTimeS": frames[index - 1]["timeS"], "timeS": frame["timeS"]}],
            )
        if sorted(frame.get("vehicles", {}).keys()) != sorted(vehicle_ids):
            return reject("VEHICLE_SET_MISMATCH", f"Frame {index} vehicle set does not match timeline.")
        for vehicle_id, vehicle in frame["vehicles"].items():
            for field in ("xM", "yM", "headingRad", "progressM", "wrappedProgressM", "lateralOffsetM", "speedMps"):
                if field not in vehicle or not math.isfinite(float(vehicle[field])):
                    return reject("INVALID_VEHICLE_STATE", f"Invalid {field} for {vehicle_id} at frame {index}.")

    duration_s = float(timeline["durationS"])
    if abs(frames[0]["timeS"]) > 1e-9:
        return reject("INVALID_TIMELINE_START", "First frame must be at t=0.")
    if frames[-1]["timeS"] > duration_s + 1e-9:
        return reject("FRAME_OUTSIDE_DURATION", "Last frame is outside replay duration.")
    for event in replay["events"]:
        if event["timeS"] < 0.0 or event["timeS"] > duration_s:
            return reject("EVENT_OUTSIDE_DURATION", f"Event outside replay duration: {event['id']}")

    keyframes = replay["index"].get("keyframes", [])
    if not keyframes or keyframes[0].get("frameIndex") != 0:
        return reject("INVALID_INDEX", "Replay index must start at frame 0.")
    if keyframes[-1].get("frameIndex") != len(frames) - 1:
        return reject("INVALID_INDEX", "Replay index must include the final frame.")

    return accept(
        [
            {"field": "schemaVersion", "value": replay["schemaVersion"]},
            {"field": "frameCount", "value": len(frames)},
            {"field": "durationS", "value": duration_s},
        ]
    )


def run_case(
    source_replay: dict[str, Any],
    case: dict[str, Any],
    cases_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    output_path = cases_dir / f"e_s05_{case['id']}.replay.json"
    write_case_file(output_path, apply_mutation(source_replay, case["mutation"]))
    validation = load_and_validate_replay(output_path)
    expected_can_load = bool(case["expectedCanLoad"])
    expected_error_code = case["expectedErrorCode"]
    can_load_matches = validation["canLoad"] == expected_can_load
    error_code_matches = validation["errorCode"] == expected_error_code
    return {
        "caseId": case["id"],
        "label": case["label"],
        "expectedCanLoad": expected_can_load,
        "actualCanLoad": validation["canLoad"],
        "expectedErrorCode": expected_error_code,
        "actualErrorCode": validation["errorCode"],
        "message": validation["message"],
        "details": validation["details"],
        "canLoadMatches": can_load_matches,
        "errorCodeMatches": error_code_matches,
        "success": can_load_matches and error_code_matches,
        "outputPath": output_path.relative_to(repo_root).as_posix(),
        "fileBytes": output_path.stat().st_size,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# E-S05 - Compatibilite de version",
        "",
        "- **Experience :** E - Replay minimal",
        "- **Scenario :** E-S05",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier que le lecteur replay accepte la version supportee et refuse explicitement les versions ou structures incompatibles.",
        "- **Reserve :** politique stricte de prototype : seule la version `0.1.0` est acceptee, sans migration automatique.",
        "",
        "## Entrees",
        "",
        f"- Replay source : `{summary['sourceReplayPath']}`",
        f"- Cas : `{summary['casesPath']}`",
        "",
        "## Metriques",
        "",
        f"- Cas testes : {metrics['caseCount']}",
        f"- Cas acceptes attendus : {metrics['expectedAcceptCount']}",
        f"- Cas refuses attendus : {metrics['expectedRejectCount']}",
        f"- Attentes respectees : {metrics['successfulCaseCount']} / {metrics['caseCount']}",
        f"- Versions supportees : {', '.join(summary['supportedSchemaVersions'])}",
        f"- Mismatches : {metrics['mismatchCount']}",
        "",
        "## Cas",
        "",
        "| Cas | Attendu | Obtenu | Code attendu | Code obtenu | OK |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in summary["cases"]:
        lines.append(
            "| "
            f"{result['caseId']} | "
            f"{fmt_bool(result['expectedCanLoad'])} | "
            f"{fmt_bool(result['actualCanLoad'])} | "
            f"{result['expectedErrorCode']} | "
            f"{result['actualErrorCode']} | "
            f"{fmt_bool(result['success'])} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "E-S05 est valide avec reserves. La detection des versions et structures incompatibles est explicite ; le prototype peut passer a E-S06 pour la synthese."
                if summary["success"]
                else "E-S05 est a corriger avant la synthese E-S06."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run E-S05 replay compatibility scenario.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="Replay JSON produced by E-S01.",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "fixtures" / "e_s05_compatibility_cases.json",
        help="Compatibility cases JSON.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results",
        help="Directory where E-S05 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    source_replay = load_json(arguments.replay)
    cases_config = load_json(arguments.cases)
    cases_dir = arguments.results_dir / "e_s05_compatibility_cases"
    case_results = [run_case(source_replay, case, cases_dir, repo_root) for case in cases_config["cases"]]
    metrics = {
        "caseCount": len(case_results),
        "expectedAcceptCount": sum(1 for result in case_results if result["expectedCanLoad"]),
        "expectedRejectCount": sum(1 for result in case_results if not result["expectedCanLoad"]),
        "actualAcceptCount": sum(1 for result in case_results if result["actualCanLoad"]),
        "actualRejectCount": sum(1 for result in case_results if not result["actualCanLoad"]),
        "successfulCaseCount": sum(1 for result in case_results if result["success"]),
        "mismatchCount": sum(1 for result in case_results if not result["success"]),
    }
    success = (
        metrics["caseCount"] >= 8
        and metrics["expectedAcceptCount"] >= 1
        and metrics["expectedRejectCount"] >= 6
        and metrics["mismatchCount"] == 0
    )
    summary = {
        "scenario": "E-S05",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sourceReplayPath": arguments.replay.relative_to(repo_root).as_posix(),
        "casesPath": arguments.cases.relative_to(repo_root).as_posix(),
        "casesDir": cases_dir.relative_to(repo_root).as_posix(),
        "supportedSchemaVersions": sorted(SUPPORTED_SCHEMA_VERSIONS),
        "cases": case_results,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "e_s05_version_compatibility_summary.json"
    report_path = arguments.results_dir / "E_S05_VERSION_COMPATIBILITY_RESULT.md"
    with summary_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with report_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_markdown(summary))
    print(f"Wrote {summary_path.relative_to(repo_root)}")
    print(f"Wrote {report_path.relative_to(repo_root)}")
    print(f"Wrote {cases_dir.relative_to(repo_root)}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
