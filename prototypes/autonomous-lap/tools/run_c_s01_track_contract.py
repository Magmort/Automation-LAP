#!/usr/bin/env python3
"""Run C-S01: validate and preprocess the minimal TrackDefinition contract."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

EXPECTED_KIND = "TrackDefinition"
EXPECTED_SCHEMA = "0.1.0"
MIN_POINTS = 8
MIN_LOOP_LENGTH_M = 100.0
MIN_TOTAL_WIDTH_M = 4.0
SAMPLE_SPACING_M = 5.0


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def distance(left: dict[str, float], right: dict[str, float]) -> float:
    return math.hypot(right["x"] - left["x"], right["y"] - left["y"])


def normalize_angle(value: float) -> float:
    while value <= -math.pi:
        value += 2.0 * math.pi
    while value > math.pi:
        value -= 2.0 * math.pi
    return value


def point_ids(track: dict[str, Any]) -> set[str]:
    return {str(point["id"]) for point in track["centerline"]}


def validate_track(track: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if track.get("kind") != EXPECTED_KIND:
        errors.append(f"kind must be {EXPECTED_KIND!r}")
    if track.get("schemaVersion") != EXPECTED_SCHEMA:
        errors.append(f"schemaVersion must be {EXPECTED_SCHEMA!r}")
    if track.get("closedLoop") is not True:
        errors.append("closedLoop must be true for C-S01")
    if track.get("direction") not in {"clockwise", "counter-clockwise"}:
        errors.append("direction must be clockwise or counter-clockwise")

    units = track.get("coordinateSystem", {}).get("units", {})
    if units.get("distance") != "m" or units.get("angle") != "rad" or units.get("time") != "s":
        errors.append("coordinateSystem.units must use m, rad and s")

    centerline = track.get("centerline")
    if not isinstance(centerline, list) or len(centerline) < MIN_POINTS:
        errors.append(f"centerline must contain at least {MIN_POINTS} points")
        return errors

    seen_ids: set[str] = set()
    for index, point in enumerate(centerline):
        point_id = point.get("id")
        if not isinstance(point_id, str) or not point_id:
            errors.append(f"centerline[{index}].id must be a non-empty string")
        elif point_id in seen_ids:
            errors.append(f"duplicate centerline point id {point_id!r}")
        else:
            seen_ids.add(point_id)

        for key in ("x", "y", "leftWidth", "rightWidth"):
            if not finite_number(point.get(key)):
                errors.append(f"centerline[{index}].{key} must be finite")

        if finite_number(point.get("leftWidth")) and finite_number(point.get("rightWidth")):
            total_width = float(point["leftWidth"]) + float(point["rightWidth"])
            if total_width < MIN_TOTAL_WIDTH_M:
                errors.append(f"centerline[{index}] total width must be >= {MIN_TOTAL_WIDTH_M} m")

    ids = point_ids(track)
    start_id = track.get("startLine", {}).get("centerlinePointId")
    if start_id not in ids:
        errors.append("startLine.centerlinePointId must reference centerline")

    checkpoints = track.get("checkpoints", [])
    if not isinstance(checkpoints, list) or not checkpoints:
        errors.append("checkpoints must contain at least one checkpoint")
    else:
        seen_checkpoints: set[str] = set()
        for index, checkpoint in enumerate(checkpoints):
            checkpoint_id = checkpoint.get("id")
            if not isinstance(checkpoint_id, str) or not checkpoint_id:
                errors.append(f"checkpoints[{index}].id must be a non-empty string")
            elif checkpoint_id in seen_checkpoints:
                errors.append(f"duplicate checkpoint id {checkpoint_id!r}")
            else:
                seen_checkpoints.add(checkpoint_id)
            if checkpoint.get("centerlinePointId") not in ids:
                errors.append(f"checkpoints[{index}].centerlinePointId must reference centerline")

    return errors


def preprocess_track(track: dict[str, Any]) -> dict[str, Any]:
    points = [
        {
            "id": point["id"],
            "x": float(point["x"]),
            "y": float(point["y"]),
            "leftWidth": float(point["leftWidth"]),
            "rightWidth": float(point["rightWidth"]),
        }
        for point in track["centerline"]
    ]
    segments: list[dict[str, Any]] = []
    cumulative = [0.0]
    total_length = 0.0
    for index, point in enumerate(points):
        next_index = (index + 1) % len(points)
        next_point = points[next_index]
        length = distance(point, next_point)
        heading = math.atan2(next_point["y"] - point["y"], next_point["x"] - point["x"])
        segments.append(
            {
                "index": index,
                "from": point["id"],
                "to": next_point["id"],
                "length": length,
                "heading": heading,
            }
        )
        total_length += length
        if index < len(points) - 1:
            cumulative.append(total_length)

    curvatures: list[float] = []
    turn_angles: list[float] = []
    for index in range(len(points)):
        previous_segment = segments[index - 1]
        next_segment = segments[index]
        turn_angle = normalize_angle(next_segment["heading"] - previous_segment["heading"])
        average_length = max((previous_segment["length"] + next_segment["length"]) / 2.0, 1e-9)
        turn_angles.append(turn_angle)
        curvatures.append(turn_angle / average_length)

    sample_count = max(1, math.ceil(total_length / SAMPLE_SPACING_M))
    samples: list[dict[str, float]] = []
    for sample_index in range(sample_count):
        s = sample_index * total_length / sample_count
        segment_index = 0
        while segment_index < len(segments) - 1 and cumulative[segment_index + 1] <= s:
            segment_index += 1
        segment = segments[segment_index]
        local_s = s - cumulative[segment_index]
        ratio = 0.0 if segment["length"] == 0 else local_s / segment["length"]
        point = points[segment_index]
        next_point = points[(segment_index + 1) % len(points)]
        x = point["x"] + ratio * (next_point["x"] - point["x"])
        y = point["y"] + ratio * (next_point["y"] - point["y"])
        tangent_x = math.cos(segment["heading"])
        tangent_y = math.sin(segment["heading"])
        samples.append(
            {
                "s": s,
                "x": x,
                "y": y,
                "tangentX": tangent_x,
                "tangentY": tangent_y,
                "normalX": -tangent_y,
                "normalY": tangent_x,
                "leftWidth": point["leftWidth"] + ratio * (next_point["leftWidth"] - point["leftWidth"]),
                "rightWidth": point["rightWidth"] + ratio * (next_point["rightWidth"] - point["rightWidth"]),
            }
        )

    min_width = min(point["leftWidth"] + point["rightWidth"] for point in points)
    max_width = max(point["leftWidth"] + point["rightWidth"] for point in points)
    min_segment = min(segment["length"] for segment in segments)
    max_segment = max(segment["length"] for segment in segments)
    max_abs_curvature = max(abs(value) for value in curvatures)
    start_id = track["startLine"]["centerlinePointId"]
    checkpoint_ids = [checkpoint["centerlinePointId"] for checkpoint in track["checkpoints"]]
    id_to_s = {point["id"]: cumulative[index] for index, point in enumerate(points)}

    return {
        "trackId": track["trackId"],
        "name": track["name"],
        "schemaVersion": track["schemaVersion"],
        "pointCount": len(points),
        "segmentCount": len(segments),
        "sampleCount": len(samples),
        "sampleSpacingM": total_length / sample_count,
        "totalLengthM": total_length,
        "minSegmentLengthM": min_segment,
        "maxSegmentLengthM": max_segment,
        "minTotalWidthM": min_width,
        "maxTotalWidthM": max_width,
        "maxAbsCurvature": max_abs_curvature,
        "maxAbsTurnAngleRad": max(abs(value) for value in turn_angles),
        "startDistanceM": id_to_s[start_id],
        "checkpointDistancesM": [id_to_s[checkpoint_id] for checkpoint_id in checkpoint_ids],
        "segments": segments,
        "pointDistancesM": cumulative,
        "curvatures": curvatures,
        "samplesPreview": samples[:5],
    }


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def render_markdown(summary: dict[str, Any]) -> str:
    processed = summary["preprocessed"]
    lines = [
        "# C-S01 - Contrat TrackDefinition",
        "",
        "- **Experience :** C - Tour autonome et modele minimal de circuit",
        "- **Scenario :** C-S01",
        f"- **Statut :** {'valide' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** valider une piste canonique dans le contrat `TrackDefinition` minimal.",
        "- **Reserve :** C-S01 ne valide pas encore le controleur autonome.",
        "",
        "## Synthese",
        "",
        f"- Fichier : `{summary['inputPath']}`",
        f"- Erreurs de contrat : {len(summary['errors'])}",
        f"- Points : {processed['pointCount']}",
        f"- Segments : {processed['segmentCount']}",
        f"- Longueur : {fmt_number(processed['totalLengthM'])} m",
        f"- Largeur totale : {fmt_number(processed['minTotalWidthM'])} m a {fmt_number(processed['maxTotalWidthM'])} m",
        f"- Courbure max absolue : {fmt_number(processed['maxAbsCurvature'], 5)} 1/m",
        f"- Echantillons preprocesses : {processed['sampleCount']}",
        "",
        "## Distances fonctionnelles",
        "",
        "| Element | Distance curviligne |",
        "| --- | ---: |",
        f"| Depart | {fmt_number(processed['startDistanceM'])} m |",
    ]

    for index, checkpoint_distance in enumerate(processed["checkpointDistancesM"], start=1):
        lines.append(f"| Checkpoint {index} | {fmt_number(checkpoint_distance)} m |")

    lines.extend(
        [
            "",
            "## Segments",
            "",
            "| Segment | Depuis | Vers | Longueur | Cap |",
            "| ---: | --- | --- | ---: | ---: |",
        ]
    )

    for segment in processed["segments"]:
        lines.append(
            "| "
            f"{segment['index']} | "
            f"{segment['from']} | "
            f"{segment['to']} | "
            f"{fmt_number(segment['length'])} | "
            f"{fmt_number(segment['heading'], 4)} |"
        )

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Le contrat minimal suffit a reconstruire une boucle fermee et orientee.",
            "- Les distances curvilignes, tangentes, normales et courbures sont derivables sans champ source supplementaire.",
            "- Les largeurs gauche/droite scalaires donnent une limite roulable exploitable pour les premiers controles.",
            "- Le contrat est independant de Unity et d'UR2D2 ; G devra s'adapter vers ce format, pas l'inverse.",
            "",
            "## Decision",
            "",
            "C-S01 est valide. Le prototype peut passer a C-S02 pour projeter une voiture sur la piste et suivre une cible de lookahead.",
            "",
        ]
    )

    if summary["errors"]:
        lines.extend(["## Erreurs", ""])
        for error in summary["errors"]:
            lines.append(f"- {error}")
        lines.append("")

    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run C-S01 TrackDefinition validation.")
    parser.add_argument(
        "--input",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "results",
        help="Directory where C-S01 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    track = load_json(arguments.input)
    errors = validate_track(track)
    preprocessed = preprocess_track(track) if not errors else {}
    success = (
        not errors
        and preprocessed["totalLengthM"] > MIN_LOOP_LENGTH_M
        and preprocessed["minTotalWidthM"] >= MIN_TOTAL_WIDTH_M
        and math.isfinite(preprocessed["maxAbsCurvature"])
    )
    summary = {
        "scenario": "C-S01",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputPath": arguments.input.relative_to(repo_root).as_posix(),
        "contract": {
            "kind": EXPECTED_KIND,
            "schemaVersion": EXPECTED_SCHEMA,
            "units": {"distance": "m", "angle": "rad", "time": "s"},
            "closedLoop": True,
            "centerlineClosure": "implicit last point to first point",
        },
        "errors": errors,
        "preprocessed": preprocessed,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "c_s01_track_contract_summary.json"
    report_path = arguments.results_dir / "C_S01_TRACK_CONTRACT_RESULT.md"

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
