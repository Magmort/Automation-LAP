#!/usr/bin/env python3
"""Run D-S03: trigger an overtake candidate when the adjacent corridor is clear."""

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


def project_vehicle(c_s02: Any, segments: list[Any], track_length: float, vehicle: dict[str, Any]) -> dict[str, Any]:
    progress = float(vehicle["progressM"]) % track_length
    lateral = float(vehicle["lateralOffsetM"])
    center = c_s02.point_at_s(segments, track_length, progress)
    x = center["x"] + center["normalX"] * lateral
    y = center["y"] + center["normalY"] * lateral
    projection = c_s02.project_position(segments, track_length, x, y)
    return {
        **vehicle,
        "progressM": progress,
        "lateralOffsetM": lateral,
        "speedMps": float(vehicle["speedKmh"]) * KMH_TO_MPS,
        "x": x,
        "y": y,
        "heading": center["heading"],
        "projectedLateralM": projection["lateral"],
        "offTrack": abs(projection["lateral"]) > c_s02.track_limit_for_lateral(projection),
    }


def candidate_lane_is_inside_track(
    c_s02: Any,
    segments: list[Any],
    track_length: float,
    progress_m: float,
    candidate_offset_m: float,
    vehicle_width_m: float,
    clearance_m: float,
) -> bool:
    point = c_s02.point_at_s(segments, track_length, progress_m)
    if candidate_offset_m >= 0.0:
        return candidate_offset_m + vehicle_width_m * 0.5 + clearance_m <= point["leftWidth"]
    return abs(candidate_offset_m) + vehicle_width_m * 0.5 + clearance_m <= point["rightWidth"]


def nearest_front(
    vehicles: list[dict[str, Any]],
    ego: dict[str, Any],
    track_length: float,
    lateral_center_m: float,
    lateral_limit_m: float,
    front_lookahead_m: float,
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for other in vehicles:
        if other["id"] == ego["id"]:
            continue
        lateral_separation = abs(float(other["lateralOffsetM"]) - lateral_center_m)
        if lateral_separation > lateral_limit_m:
            continue
        center_gap = progress_delta_forward(track_length, float(ego["progressM"]), float(other["progressM"]))
        gap = bumper_gap(center_gap, ego, other)
        if 0.0 < gap <= front_lookahead_m:
            closing_speed = float(ego["speedMps"]) - float(other["speedMps"])
            candidates.append(
                {
                    "id": other["id"],
                    "gapM": gap,
                    "centerGapM": center_gap,
                    "lateralSeparationM": lateral_separation,
                    "closingSpeedMps": closing_speed,
                    "timeToCatchS": gap / closing_speed if closing_speed > 1e-6 else None,
                    "speedDeltaKmh": (float(ego["speedMps"]) - float(other["speedMps"])) * 3.6,
                }
            )
    candidates.sort(key=lambda item: item["gapM"])
    return candidates[0] if candidates else None


def adjacent_blockers(
    vehicles: list[dict[str, Any]],
    ego: dict[str, Any],
    track_length: float,
    candidate_offset_m: float,
    lateral_limit_m: float,
    front_safety_gap_m: float,
    rear_safety_gap_m: float,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for other in vehicles:
        if other["id"] == ego["id"]:
            continue
        lateral_separation = abs(float(other["lateralOffsetM"]) - candidate_offset_m)
        if lateral_separation > lateral_limit_m:
            continue
        forward_gap = bumper_gap(
            progress_delta_forward(track_length, float(ego["progressM"]), float(other["progressM"])),
            ego,
            other,
        )
        rear_gap = bumper_gap(
            progress_delta_rear(track_length, float(ego["progressM"]), float(other["progressM"])),
            ego,
            other,
        )
        if 0.0 < forward_gap < front_safety_gap_m:
            blockers.append({"id": other["id"], "where": "front", "gapM": forward_gap})
        elif 0.0 < rear_gap < rear_safety_gap_m:
            blockers.append({"id": other["id"], "where": "rear", "gapM": rear_gap})
    blockers.sort(key=lambda item: item["gapM"])
    return blockers


def evaluate_case(
    case: dict[str, Any],
    decision: dict[str, Any],
    c_s02: Any,
    segments: list[Any],
    track_length: float,
) -> dict[str, Any]:
    vehicles = [project_vehicle(c_s02, segments, track_length, vehicle) for vehicle in case["vehicles"]]
    ego = next(vehicle for vehicle in vehicles if vehicle["role"] == "ego")
    current_front = nearest_front(
        vehicles,
        ego,
        track_length,
        float(ego["lateralOffsetM"]),
        float(decision["sameCorridorLateralM"]),
        float(decision["frontLookaheadM"]),
    )
    candidate_offset = float(decision["candidateOffsetM"])
    candidate_inside = candidate_lane_is_inside_track(
        c_s02,
        segments,
        track_length,
        float(ego["progressM"]),
        candidate_offset,
        float(ego["widthM"]),
        float(decision["trackEdgeClearanceM"]),
    )
    blockers = adjacent_blockers(
        vehicles,
        ego,
        track_length,
        candidate_offset,
        float(decision["sameCorridorLateralM"]),
        float(decision["frontSafetyGapM"]),
        float(decision["rearSafetyGapM"]),
    )
    blocked_by_slow_front = False
    if current_front is not None:
        blocked_by_slow_front = (
            current_front["speedDeltaKmh"] >= float(decision["minSpeedDeltaKmh"])
            and current_front["timeToCatchS"] is not None
            and current_front["timeToCatchS"] <= float(decision["triggerTimeToCatchS"])
        )
    should_overtake = blocked_by_slow_front and candidate_inside and not blockers
    reasons: list[str] = []
    if not blocked_by_slow_front:
        reasons.append("no_slow_front_trigger")
    if not candidate_inside:
        reasons.append("candidate_outside_track")
    for blocker in blockers:
        reasons.append(f"candidate_blocked_{blocker['where']}_{blocker['id']}")
    if should_overtake:
        reasons.append("candidate_clear")
    return {
        "id": case["id"],
        "label": case["label"],
        "expectedDecision": bool(case["expectedDecision"]),
        "actualDecision": should_overtake,
        "matchedExpectation": should_overtake == bool(case["expectedDecision"]),
        "vehicles": vehicles,
        "egoId": ego["id"],
        "candidateOffsetM": candidate_offset,
        "currentFront": current_front,
        "candidateInsideTrack": candidate_inside,
        "candidateBlockers": blockers,
        "reasons": reasons,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# D-S03 - Declenchement de depassement candidat",
        "",
        "- **Experience :** D - Trafic et depassement",
        "- **Scenario :** D-S03",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier qu'une intention de depassement est declenchee seulement si une voiture lente bloque l'ego et si le corridor candidat est libre.",
        "- **Reserve :** D-S03 ne deplace pas encore la voiture ; il choisit seulement une ligne candidate.",
        "",
        "## Reglages",
        "",
        f"- Offset candidat : {fmt_number(summary['decisionSettings']['candidateOffsetM'])} m",
        f"- TTC declencheur : {fmt_number(summary['decisionSettings']['triggerTimeToCatchS'])} s",
        f"- Delta vitesse min : {fmt_number(summary['decisionSettings']['minSpeedDeltaKmh'])} km/h",
        f"- Gap securite avant : {fmt_number(summary['decisionSettings']['frontSafetyGapM'])} m",
        f"- Gap securite arriere : {fmt_number(summary['decisionSettings']['rearSafetyGapM'])} m",
        "",
        "## Resultats",
        "",
        "| Cas | Attendu | Obtenu | Front | TTC | Blockers | Raisons |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for case in summary["caseResults"]:
        front = case["currentFront"]
        blockers = ", ".join(f"{item['where']}:{item['id']}@{fmt_number(item['gapM'])}m" for item in case["candidateBlockers"])
        lines.append(
            "| "
            f"{case['label']} | "
            f"{'oui' if case['expectedDecision'] else 'non'} | "
            f"{'oui' if case['actualDecision'] else 'non'} | "
            f"{front['id'] if front else 'n/a'} | "
            f"{fmt_number(front['timeToCatchS'] if front else None)} | "
            f"{blockers or 'n/a'} | "
            f"{', '.join(case['reasons'])} |"
        )
    lines.extend(
        [
            "",
            "## Metriques",
            "",
            f"- Cas conformes : {summary['metrics']['matchedCases']} / {summary['metrics']['caseCount']}",
            f"- Decisions positives : {summary['metrics']['positiveDecisions']}",
            f"- Decisions negatives : {summary['metrics']['negativeDecisions']}",
            f"- Cas avec blocker candidat : {summary['metrics']['blockedCandidateCases']}",
            "",
            "## Decision",
            "",
            (
                "D-S03 est valide avec reserves. Le prototype peut passer a D-S04 pour tester deux voitures cote a cote."
                if summary["success"]
                else "D-S03 est a corriger avant de tester deux voitures cote a cote."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run D-S03 overtake candidate decision scenario.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "fixtures" / "d_s03_overtake_candidate_scene.json",
        help="TrafficOvertakeDecisionSuite JSON fixture.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results",
        help="Directory where D-S03 result files will be written.",
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
    case_results = [
        evaluate_case(case, scene["decision"], c_s02, segments, track_length) for case in scene["cases"]
    ]
    metrics = {
        "caseCount": len(case_results),
        "matchedCases": sum(1 for case in case_results if case["matchedExpectation"]),
        "positiveDecisions": sum(1 for case in case_results if case["actualDecision"]),
        "negativeDecisions": sum(1 for case in case_results if not case["actualDecision"]),
        "blockedCandidateCases": sum(1 for case in case_results if case["candidateBlockers"]),
    }
    summary = {
        "scenario": "D-S03",
        "success": (
            metrics["matchedCases"] == metrics["caseCount"]
            and metrics["positiveDecisions"] >= 1
            and metrics["negativeDecisions"] >= 2
            and metrics["blockedCandidateCases"] >= 2
        ),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "sceneInputPath": arguments.scene.relative_to(repo_root).as_posix(),
        "trackLengthM": track_length,
        "decisionSettings": scene["decision"],
        "caseResults": case_results,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "d_s03_overtake_candidate_summary.json"
    report_path = arguments.results_dir / "D_S03_OVERTAKE_CANDIDATE_RESULT.md"
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
