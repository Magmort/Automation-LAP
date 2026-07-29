#!/usr/bin/env python3
"""Run D-S01: validate multi-car neighbor perception on TrackDefinition."""

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

REFERENCE_DT = 1.0 / 120.0
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


def build_vehicle_states(scene: dict[str, Any], c_s02: Any, segments: list[Any], track_length: float) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for vehicle in scene["vehicles"]:
        center = c_s02.point_at_s(segments, track_length, float(vehicle["progressM"]))
        lateral = float(vehicle["lateralOffsetM"])
        x = center["x"] + center["normalX"] * lateral
        y = center["y"] + center["normalY"] * lateral
        projection = c_s02.project_position(segments, track_length, x, y)
        states.append(
            {
                "id": vehicle["id"],
                "label": vehicle["label"],
                "sourceProgressM": float(vehicle["progressM"]) % track_length,
                "projectedProgressM": projection["s"],
                "projectionProgressErrorM": abs(
                    min(
                        progress_delta_forward(track_length, float(vehicle["progressM"]), projection["s"]),
                        progress_delta_rear(track_length, float(vehicle["progressM"]), projection["s"]),
                    )
                ),
                "lateralOffsetM": lateral,
                "projectedLateralM": projection["lateral"],
                "x": x,
                "y": y,
                "heading": center["heading"],
                "speedKmh": float(vehicle["speedKmh"]),
                "speedMps": float(vehicle["speedKmh"]) * KMH_TO_MPS,
                "lengthM": float(vehicle["lengthM"]),
                "widthM": float(vehicle["widthM"]),
                "offTrack": abs(projection["lateral"]) > c_s02.track_limit_for_lateral(projection),
            }
        )
    return states


def nearest_neighbors(scene: dict[str, Any], states: list[dict[str, Any]], track_length: float) -> dict[str, Any]:
    forward_limit = float(scene["perception"]["forwardLookaheadM"])
    rear_limit = float(scene["perception"]["rearLookaheadM"])
    same_corridor_lateral = float(scene["perception"]["sameCorridorLateralM"])
    perception: dict[str, Any] = {}
    for ego in states:
        front_candidates: list[dict[str, Any]] = []
        rear_candidates: list[dict[str, Any]] = []
        for other in states:
            if other["id"] == ego["id"]:
                continue
            lateral_separation = abs(float(other["projectedLateralM"]) - float(ego["projectedLateralM"]))
            same_corridor = lateral_separation <= same_corridor_lateral
            forward_gap = progress_delta_forward(track_length, ego["projectedProgressM"], other["projectedProgressM"])
            rear_gap = progress_delta_rear(track_length, ego["projectedProgressM"], other["projectedProgressM"])
            if same_corridor and 0.0 < forward_gap <= forward_limit:
                closing_speed = ego["speedMps"] - other["speedMps"]
                front_candidates.append(
                    {
                        "id": other["id"],
                        "gapM": forward_gap,
                        "lateralSeparationM": lateral_separation,
                        "closingSpeedMps": closing_speed,
                        "timeToCatchS": forward_gap / closing_speed if closing_speed > 1e-6 else None,
                    }
                )
            if same_corridor and 0.0 < rear_gap <= rear_limit:
                closing_speed = other["speedMps"] - ego["speedMps"]
                rear_candidates.append(
                    {
                        "id": other["id"],
                        "gapM": rear_gap,
                        "lateralSeparationM": lateral_separation,
                        "closingSpeedMps": closing_speed,
                        "timeToCatchS": rear_gap / closing_speed if closing_speed > 1e-6 else None,
                    }
                )
        front_candidates.sort(key=lambda item: item["gapM"])
        rear_candidates.sort(key=lambda item: item["gapM"])
        perception[ego["id"]] = {
            "front": front_candidates[0] if front_candidates else None,
            "rear": rear_candidates[0] if rear_candidates else None,
            "frontCandidates": front_candidates,
            "rearCandidates": rear_candidates,
        }
    return perception


def compare_expected(scene: dict[str, Any], perception: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for ego_id, expected_id in scene["expectedNearestFront"].items():
        actual = perception[ego_id]["front"]["id"] if perception[ego_id]["front"] else None
        if actual != expected_id:
            errors.append(f"{ego_id}: expected front {expected_id}, got {actual}")
    for ego_id, expected_id in scene["expectedNearestRear"].items():
        actual = perception[ego_id]["rear"]["id"] if perception[ego_id]["rear"] else None
        if actual != expected_id:
            errors.append(f"{ego_id}: expected rear {expected_id}, got {actual}")
    return errors


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# D-S01 - Perception des voisins sur piste",
        "",
        "- **Experience :** D - Trafic et depassement",
        "- **Scenario :** D-S01",
        f"- **Statut :** {'valide' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier qu'une scene multi-voitures peut etre projetee sur `TrackDefinition` et produire des voisins avant/arriere coherents.",
        "- **Reserve :** aucun changement de ligne, aucune decision de depassement et aucune collision dynamique ne sont encore simules.",
        "",
        "## Scene",
        "",
        f"- Piste : `{summary['trackInputPath']}`",
        f"- Scene : `{summary['sceneInputPath']}`",
        f"- Voitures : {summary['metrics']['vehicleCount']}",
        f"- Longueur piste : {fmt_number(summary['trackLengthM'])} m",
        f"- Lookahead avant : {fmt_number(summary['perceptionSettings']['forwardLookaheadM'])} m",
        f"- Lookahead arriere : {fmt_number(summary['perceptionSettings']['rearLookaheadM'])} m",
        f"- Corridor lateral : {fmt_number(summary['perceptionSettings']['sameCorridorLateralM'])} m",
        "",
        "## Resultats",
        "",
        "| Voiture | s | Offset lat. | Vitesse | Avant | Gap avant | TTC avant | Arriere | Gap arriere |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |",
    ]
    for state in summary["vehicleStates"]:
        perception = summary["perception"][state["id"]]
        front = perception["front"]
        rear = perception["rear"]
        lines.append(
            "| "
            f"{state['label']} | "
            f"{fmt_number(state['projectedProgressM'])} | "
            f"{fmt_number(state['projectedLateralM'])} | "
            f"{fmt_number(state['speedKmh'])} | "
            f"{front['id'] if front else 'n/a'} | "
            f"{fmt_number(front['gapM'] if front else None)} | "
            f"{fmt_number(front['timeToCatchS'] if front else None)} | "
            f"{rear['id'] if rear else 'n/a'} | "
            f"{fmt_number(rear['gapM'] if rear else None)} |"
        )
    lines.extend(
        [
            "",
            "## Metriques",
            "",
            f"- Erreurs attendues/reelles : {len(summary['expectationErrors'])}",
            f"- Voitures hors piste : {summary['metrics']['offTrackCount']}",
            f"- Erreur max de projection : {fmt_number(summary['metrics']['maxProjectionProgressErrorM'], 4)} m",
            f"- Liens voisins detectes : {summary['metrics']['neighborLinkCount']}",
            f"- Plus petit gap longitudinal detecte : {fmt_number(summary['metrics']['minDetectedGapM'])} m",
            "",
            "## Decision",
            "",
            (
                "D-S01 est valide. Le prototype peut passer a D-S02 pour simuler un suivi longitudinal derriere une voiture plus lente."
                if summary["success"]
                else "D-S01 est a corriger avant de simuler un suivi longitudinal."
            ),
            "",
        ]
    )
    if summary["expectationErrors"]:
        lines.extend(["## Erreurs", ""])
        for error in summary["expectationErrors"]:
            lines.append(f"- {error}")
        lines.append("")
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run D-S01 neighbor perception scenario.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "fixtures" / "d_s01_multicar_scene.json",
        help="TrafficScene JSON fixture.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results",
        help="Directory where D-S01 result files will be written.",
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
    states = build_vehicle_states(scene, c_s02, segments, track_length)
    perception = nearest_neighbors(scene, states, track_length)
    expectation_errors = compare_expected(scene, perception)
    neighbor_gaps = [
        link["gapM"]
        for links in perception.values()
        for link in (links["front"], links["rear"])
        if link is not None
    ]
    metrics = {
        "vehicleCount": len(states),
        "offTrackCount": sum(1 for state in states if state["offTrack"]),
        "maxProjectionProgressErrorM": max(state["projectionProgressErrorM"] for state in states),
        "neighborLinkCount": len(neighbor_gaps),
        "minDetectedGapM": min(neighbor_gaps) if neighbor_gaps else None,
    }
    summary = {
        "scenario": "D-S01",
        "success": (
            not expectation_errors
            and metrics["vehicleCount"] >= 2
            and metrics["offTrackCount"] == 0
            and metrics["maxProjectionProgressErrorM"] <= 1e-6
            and metrics["neighborLinkCount"] >= 4
        ),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "sceneInputPath": arguments.scene.relative_to(repo_root).as_posix(),
        "trackLengthM": track_length,
        "perceptionSettings": scene["perception"],
        "vehicleStates": states,
        "perception": perception,
        "expectationErrors": expectation_errors,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "d_s01_neighbor_perception_summary.json"
    report_path = arguments.results_dir / "D_S01_NEIGHBOR_PERCEPTION_RESULT.md"
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
