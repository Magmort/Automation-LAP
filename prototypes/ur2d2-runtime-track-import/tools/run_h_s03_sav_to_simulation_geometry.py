#!/usr/bin/env python3
"""Run H-S03: convert H-S02 .sav features into simulation geometry."""

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

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
RESULTS_DIR = ROOT / "results"
H_S02_PATH = RESULTS_DIR / "h_s02_runtime_sav_reader.json"
SUMMARY_PATH = RESULTS_DIR / "h_s03_simulation_geometry.json"
TRACK_PATH = RESULTS_DIR / "h_s03_track_definition_candidate.json"
REPORT_PATH = RESULTS_DIR / "H_S03_SIMULATION_GEOMETRY_RESULT.md"
C_S01_VALIDATOR_PATH = REPO_ROOT / "prototypes" / "autonomous-lap" / "tools" / "run_c_s01_track_contract.py"

EDITOR_UNITS_PER_METRE = 12.8
SAMPLES_PER_VECTOR_SEGMENT = 16
MIN_CENTERLINE_POINTS = 8


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_c_s01_validator() -> Any:
    spec = importlib.util.spec_from_file_location("c_s01_track_contract", C_S01_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load C-S01 validator from {C_S01_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_duplicate_point(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return math.isclose(float(a["x"]), float(b["x"])) and math.isclose(float(a["y"]), float(b["y"]))


def unique_closed_keys(keys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(keys) > 1 and is_duplicate_point(keys[0], keys[-1]):
        return keys[:-1]
    return keys


def vector2(angle_deg: float, length: float) -> dict[str, float]:
    radians = math.radians(angle_deg)
    return {"x": math.cos(radians) * length, "y": math.sin(radians) * length}


def handle_vector2(angle_deg: float, length: float) -> dict[str, float]:
    vector = vector2(angle_deg, length)
    return {"x": vector["x"], "y": -vector["y"]}


def raw_incoming_handle_endpoint(source_key: dict[str, Any], target_point: dict[str, float]) -> dict[str, float]:
    vector_b = handle_vector2(float(source_key["angleBDeg"]), float(source_key["weightB"]))
    return {"x": target_point["x"] + vector_b["x"], "y": target_point["y"] + vector_b["y"]}


def bezier(
    p0: dict[str, float],
    c0: dict[str, float],
    c1: dict[str, float],
    p1: dict[str, float],
    t: float,
) -> dict[str, float]:
    u = 1.0 - t
    return {
        "x": u**3 * p0["x"] + 3 * u * u * t * c0["x"] + 3 * u * t * t * c1["x"] + t**3 * p1["x"],
        "y": u**3 * p0["y"] + 3 * u * u * t * c0["y"] + 3 * u * t * t * c1["y"] + t**3 * p1["y"],
    }


def sample_raw_vector_trace(block: dict[str, Any], samples_per_segment: int = SAMPLES_PER_VECTOR_SEGMENT) -> list[dict[str, float]]:
    vector = block.get("vectorTraceCandidate")
    if not vector:
        return [{"x": float(point["x"]), "y": float(point["y"])} for point in block.get("points", [])]
    keys = vector["keys"]
    if len(keys) < 2:
        return [{"x": float(key["x"]), "y": float(key["y"])} for key in keys]
    closed = len(keys) > 1 and is_duplicate_point(keys[0], keys[-1])
    unique_keys = unique_closed_keys(keys)
    segment_count = len(unique_keys) if closed else max(0, len(unique_keys) - 1)
    sampled = []
    for index in range(segment_count):
        key = unique_keys[index]
        next_key = unique_keys[(index + 1) % len(unique_keys)]
        p0 = {"x": float(key["x"]), "y": float(key["y"])}
        p1 = {"x": float(next_key["x"]), "y": float(next_key["y"])}
        out_handle = handle_vector2(float(key["angleADeg"]), float(key["weightA"]))
        c0 = {"x": p0["x"] + out_handle["x"], "y": p0["y"] + out_handle["y"]}
        c1 = raw_incoming_handle_endpoint(key, p1)
        for step in range(samples_per_segment):
            sampled.append(bezier(p0, c0, c1, p1, step / samples_per_segment))
    if not closed and unique_keys:
        sampled.append({"x": float(unique_keys[-1]["x"]), "y": float(unique_keys[-1]["y"])})
    return sampled


def centroid(points: list[dict[str, float]]) -> dict[str, float]:
    return {
        "x": sum(point["x"] for point in points) / len(points),
        "y": sum(point["y"] for point in points) / len(points),
    }


def convert_point(point: dict[str, Any], origin: dict[str, float], scale: float) -> dict[str, float]:
    return {
        "x": (float(point["x"]) - origin["x"]) / scale,
        "y": -(float(point["y"]) - origin["y"]) / scale,
    }


def signed_area(points: list[dict[str, float]]) -> float:
    if len(points) < 3:
        return 0.0
    total = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        total += point["x"] * next_point["y"] - next_point["x"] * point["y"]
    return total * 0.5


def distance(a: dict[str, float], b: dict[str, float]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def polyline_length(points: list[dict[str, float]], closed: bool = False) -> float:
    if len(points) < 2:
        return 0.0
    length = sum(distance(a, b) for a, b in zip(points, points[1:]))
    if closed:
        length += distance(points[-1], points[0])
    return length


def nearest_centerline_point_id(centerline: list[dict[str, Any]], point: dict[str, float]) -> str:
    nearest = min(centerline, key=lambda candidate: math.hypot(candidate["x"] - point["x"], candidate["y"] - point["y"]))
    return nearest["id"]


def checkpoint_id(label: str | None, index: int) -> str:
    normalized = (label or f"checkpoint-{index}").lower().replace(" ", "-")
    normalized = "".join(char for char in normalized if char.isalnum() or char == "-").strip("-")
    return normalized or f"checkpoint-{index}"


def convert_feature_polyline(
    feature: dict[str, Any],
    origin: dict[str, float],
    scale: float,
    closed: bool = False,
) -> dict[str, Any]:
    raw_points = sample_raw_vector_trace(feature)
    converted_points = [convert_point(point, origin, scale) for point in raw_points]
    return {
        "role": feature["role"],
        "sourceHexOffset": feature["hexOffset"],
        "confidence": feature["confidence"],
        "closed": closed,
        "pointCount": len(converted_points),
        "lengthM": polyline_length(converted_points, closed=closed),
        "points": [
            {"x": round(point["x"], 6), "y": round(point["y"], 6)}
            for point in converted_points
        ],
    }


def build_track_definition(h_s02: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    features = h_s02["simulationFeatures"]
    track_feature = features.get("track")
    if track_feature is None:
        raise RuntimeError("H-S02 did not provide a main track feature")
    vector = track_feature.get("vectorTraceCandidate")
    if not vector:
        raise RuntimeError("H-S03 requires a vectorTraceCandidate for the main track")

    raw_keys = unique_closed_keys(vector["keys"])
    raw_key_points = [{"x": float(key["x"]), "y": float(key["y"])} for key in raw_keys]
    raw_origin = centroid(raw_key_points)
    scale = EDITOR_UNITS_PER_METRE
    width_candidate = h_s02.get("editorSav", {}).get("globalCandidates", {}).get("float32At0")
    total_width_m = float(width_candidate) if isinstance(width_candidate, (int, float)) and width_candidate > 0 else 10.0
    half_width_m = total_width_m * 0.5

    sampled_raw = sample_raw_vector_trace(track_feature)
    if len(sampled_raw) < MIN_CENTERLINE_POINTS:
        raise RuntimeError("sampled main track does not have enough centerline points")
    converted_centerline = [convert_point(point, raw_origin, scale) for point in sampled_raw]
    area = signed_area(converted_centerline)
    direction = "counter-clockwise" if area > 0 else "clockwise"
    centerline = []
    for index, point in enumerate(converted_centerline):
        centerline.append(
            {
                "id": f"p{index:03d}",
                "x": round(point["x"], 6),
                "y": round(point["y"], 6),
                "leftWidth": round(half_width_m, 6),
                "rightWidth": round(half_width_m, 6),
            }
        )

    checkpoints = []
    finish_checkpoint = None
    for index, checkpoint in enumerate(features.get("checkpoints", [])):
        converted = convert_point(checkpoint, raw_origin, scale)
        centerline_point_id = nearest_centerline_point_id(centerline, converted)
        item = {
            "id": checkpoint_id(checkpoint.get("label"), index),
            "centerlinePointId": centerline_point_id,
        }
        checkpoints.append(item)
        if checkpoint.get("label") == "Finish":
            finish_checkpoint = item
    start_point_id = finish_checkpoint["centerlinePointId"] if finish_checkpoint else checkpoints[0]["centerlinePointId"]

    track = {
        "kind": "TrackDefinition",
        "schemaVersion": "0.1.0",
        "trackId": "ur2d2-runtime-r00-h03-candidate",
        "name": (h_s02.get("trackInfo", {}).get("strings") or ["UR2D2 Runtime Track"])[0],
        "coordinateSystem": {
            "units": {"distance": "m", "angle": "rad", "time": "s"},
            "axis": {"x": "right", "y": "forward"},
            "orientation": direction,
        },
        "closedLoop": True,
        "direction": direction,
        "surface": {"type": "asphalt", "grip": 1.0},
        "centerline": centerline,
        "startLine": {
            "centerlinePointId": start_point_id,
            "width": round(total_width_m, 6),
        },
        "checkpoints": checkpoints,
    }
    notes = {
        "sourceScenario": h_s02["scenario"],
        "sourceStatus": h_s02["status"],
        "sourceTrackDirectory": h_s02["trackDirectory"],
        "sourceTrackFeatureOffset": track_feature["hexOffset"],
        "rawOriginEditorUnits": raw_origin,
        "scalePolicy": {
            "editorUnitsPerMetre": scale,
            "status": "reused-from-g-grid-calibration",
            "reason": "H-S03 reuses the grid calibration validated during G: 12.8 editor units per metre.",
        },
        "axisPolicy": {
            "status": "simulation-coordinate-system",
            "x": "raw editor x increases to simulation x",
            "y": "raw editor y is inverted so screen-down editor coordinates become negative forward coordinates",
        },
        "widthPolicy": {
            "totalRoadWidthM": total_width_m,
            "leftWidthM": half_width_m,
            "rightWidthM": half_width_m,
            "status": "source-file",
            "reason": "Width comes from track_editor.sav global float32At0.",
        },
        "vectorPolicy": {
            "samplesPerVectorSegment": SAMPLES_PER_VECTOR_SEGMENT,
            "status": "vector-aware",
            "formula": "cubic Bezier per vector segment using angleA/weightA as outgoing handle and angleB/weightB as incoming handle on the same source row.",
        },
        "nonTrackFeatures": {
            "pitlaneLaneCount": len(features.get("pitlaneLanes", [])),
            "wallCount": len(features.get("walls", [])),
        },
    }
    return track, notes


def build_result(h_s02: dict[str, Any], results_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    track, notes = build_track_definition(h_s02)
    validator = load_c_s01_validator()
    errors = validator.validate_track(track)
    preprocessed = validator.preprocess_track(track) if not errors else {}
    success = (
        not errors
        and preprocessed["totalLengthM"] > validator.MIN_LOOP_LENGTH_M
        and preprocessed["minTotalWidthM"] >= validator.MIN_TOTAL_WIDTH_M
        and math.isfinite(preprocessed["maxAbsCurvature"])
    )

    origin = notes["rawOriginEditorUnits"]
    scale = notes["scalePolicy"]["editorUnitsPerMetre"]
    features = h_s02["simulationFeatures"]
    pitlane_lanes = [convert_feature_polyline(feature, origin, scale) for feature in features.get("pitlaneLanes", [])]
    walls = [convert_feature_polyline(feature, origin, scale) for feature in features.get("walls", [])]
    checkpoint_points = []
    for index, checkpoint in enumerate(features.get("checkpoints", [])):
        converted = convert_point(checkpoint, origin, scale)
        checkpoint_points.append(
            {
                "id": checkpoint_id(checkpoint.get("label"), index),
                "label": checkpoint.get("label"),
                "x": round(converted["x"], 6),
                "y": round(converted["y"], 6),
                "rotationDegEditor": checkpoint.get("rotationDeg"),
            }
        )

    result = {
        "kind": "UR2D2SimulationGeometry",
        "schemaVersion": "0.1.0",
        "scenario": "H-S03",
        "status": "validated-with-reserves" if success else "conversion-failed-validation",
        "success": success,
        "generatedAtUtc": utc_now(),
        "trackDefinitionPath": str((results_dir / TRACK_PATH.name).resolve()),
        "sourcePath": str((results_dir / H_S02_PATH.name).resolve()),
        "conversionNotes": notes,
        "trackDefinition": track,
        "pitlaneLanes": pitlane_lanes,
        "walls": walls,
        "checkpointPoints": checkpoint_points,
        "validation": {
            "success": success,
            "errors": errors,
            "preprocessed": preprocessed,
        },
        "nonGuarantees": [
            "H-S03 does not align coordinates to PNG pixels yet.",
            "H-S03 does not simulate a vehicle yet.",
            "H-S03 does not encode pitlane or walls into TrackDefinition v0.1 because C's contract does not include them.",
        ],
    }
    return track, result


def render_markdown(result: dict[str, Any]) -> str:
    validation = result["validation"]
    preprocessed = validation.get("preprocessed", {})
    notes = result["conversionNotes"]
    lines = [
        "# H-S03 - Géométrie de simulation depuis .sav",
        "",
        "- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2",
        "- **Scénario :** H-S03",
        f"- **Statut :** {result['status']}",
        f"- **Date :** {result['generatedAtUtc']}",
        f"- **TrackDefinition :** `{result['trackDefinitionPath']}`",
        f"- **Validation C-S01 :** {'succès' if validation['success'] else 'échec'}",
        "",
        "## Décision du jalon",
        "",
    ]
    if validation["success"]:
        lines.append("H-S03 produit une géométrie de simulation exploitable : la piste principale du `.sav` est convertie en `TrackDefinition` v0.1 et passe C-S01.")
    else:
        lines.append("H-S03 produit une géométrie candidate, mais la validation C-S01 échoue encore.")

    lines.extend(
        [
            "",
            "## Conversion",
            "",
            f"- Source piste : `{notes['sourceTrackFeatureOffset']}`.",
            f"- Échelle : `1 m = {notes['scalePolicy']['editorUnitsPerMetre']} unités éditeur` (`{notes['scalePolicy']['status']}`).",
            f"- Largeur piste : {notes['widthPolicy']['totalRoadWidthM']:.3f} m total.",
            f"- Axes : {notes['axisPolicy']['x']} ; {notes['axisPolicy']['y']}.",
            f"- Vectoriel : {notes['vectorPolicy']['samplesPerVectorSegment']} échantillons par segment ; {notes['vectorPolicy']['formula']}",
            f"- Pitlane : {notes['nonTrackFeatures']['pitlaneLaneCount']} voies converties hors contrat C.",
            f"- Murs : {notes['nonTrackFeatures']['wallCount']} polylignes converties hors contrat C.",
            "",
            "## Validation C-S01",
            "",
            f"- Erreurs : {len(validation['errors'])}",
        ]
    )
    if preprocessed:
        lines.extend(
            [
                f"- Points : {preprocessed['pointCount']}",
                f"- Segments : {preprocessed['segmentCount']}",
                f"- Longueur : {preprocessed['totalLengthM']:.3f} m",
                f"- Largeur totale min : {preprocessed['minTotalWidthM']:.3f} m",
                f"- Courbure max absolue : {preprocessed['maxAbsCurvature']:.6f} 1/m",
            ]
        )
    if validation["errors"]:
        lines.extend(["", "### Erreurs", ""])
        lines.extend(f"- {error}" for error in validation["errors"])

    lines.extend(
        [
            "",
            "## Éléments convertis",
            "",
            "| Élément | Count | Longueur |",
            "| --- | ---: | ---: |",
            f"| Centerline | {len(result['trackDefinition']['centerline'])} | {preprocessed.get('totalLengthM', 0.0):.3f} m |",
            f"| Pitlane | {len(result['pitlaneLanes'])} | {sum(item['lengthM'] for item in result['pitlaneLanes']):.3f} m |",
            f"| Murs | {len(result['walls'])} | {sum(item['lengthM'] for item in result['walls']):.3f} m |",
            f"| Checkpoints | {len(result['checkpointPoints'])} | - |",
            "",
            "## Réserves",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result["nonGuarantees"])
    lines.extend(
        [
            "",
            "## Prochaine étape",
            "",
            "H-S04 doit superposer cette géométrie convertie au fond PNG runtime afin de valider l'alignement image/coordonnées.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=H_S02_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    track, result = build_result(load_json(args.input), results_dir)
    write_json(results_dir / TRACK_PATH.name, track)
    write_json(results_dir / SUMMARY_PATH.name, result)
    (results_dir / REPORT_PATH.name).write_text(render_markdown(result), encoding="utf-8", newline="\n")
    print(f"H-S03 status: {result['status']}")
    print(f"C-S01 validation: {'success' if result['success'] else 'failure'}")
    print(f"Wrote: {results_dir / REPORT_PATH.name}")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
