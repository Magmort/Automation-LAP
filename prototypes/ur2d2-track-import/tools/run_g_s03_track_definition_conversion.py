#!/usr/bin/env python3
"""Convert G-S02 UR2D2RawTrackData into a candidate TrackDefinition."""

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
DEFAULT_RAW_PATH = ROOT / "results" / "g_s02_raw_reader.json"
DEFAULT_RESULTS_DIR = ROOT / "results"
C_S01_VALIDATOR_PATH = REPO_ROOT / "prototypes" / "autonomous-lap" / "tools" / "run_c_s01_track_contract.py"

EDITOR_UNITS_PER_METRE = 12.8
MIN_CENTERLINE_POINTS = 8
SAMPLES_PER_VECTOR_SEGMENT = 4


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_c_s01_validator():
    spec = importlib.util.spec_from_file_location("c_s01_track_contract", C_S01_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load C-S01 validator from {C_S01_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_by_id(raw: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    for fixture in raw["rawFixtures"]:
        if fixture["fixture"] == fixture_id:
            return fixture
    raise KeyError(f"Missing fixture {fixture_id}")


def signed_area(points: list[dict[str, float]]) -> float:
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point["x"] * next_point["y"] - next_point["x"] * point["y"]
    return area / 2.0


def strip_duplicate_closure(points: list[dict[str, float]]) -> list[dict[str, float]]:
    if len(points) >= 2 and math.isclose(points[0]["x"], points[-1]["x"]) and math.isclose(points[0]["y"], points[-1]["y"]):
        return points[:-1]
    return points


def centroid(points: list[dict[str, float]]) -> dict[str, float]:
    return {
        "x": sum(point["x"] for point in points) / len(points),
        "y": sum(point["y"] for point in points) / len(points),
    }


def convert_point(point: dict[str, float], origin: dict[str, float]) -> dict[str, float]:
    return {
        "x": (point["x"] - origin["x"]) / EDITOR_UNITS_PER_METRE,
        "y": -(point["y"] - origin["y"]) / EDITOR_UNITS_PER_METRE,
    }


def arrays_by_name(fixture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {array["name"]: array for array in fixture["countedFloatArrays"]}


def road_half_width_m(route_fixture: dict[str, Any]) -> float:
    width_candidate = route_fixture.get("globalCandidates", {}).get("float32At0")
    if isinstance(width_candidate, (int, float)) and width_candidate > 0:
        return float(width_candidate) / 2.0
    raise ValueError("missing positive road width candidate in route fixture")


def vector2(angle_deg: float, length: float) -> dict[str, float]:
    radians = math.radians(angle_deg)
    return {"x": math.cos(radians) * length, "y": math.sin(radians) * length}


def handle_vector2(angle_deg: float, length: float) -> dict[str, float]:
    vector = vector2(angle_deg, length)
    return {"x": vector["x"], "y": -vector["y"]}


def incoming_handle_endpoint(source_key: dict[str, Any], target_point: dict[str, float]) -> dict[str, float]:
    incoming_handle = handle_vector2(float(source_key["angleBDeg"]), float(source_key["weightB"]))
    return {"x": target_point["x"] + incoming_handle["x"], "y": target_point["y"] + incoming_handle["y"]}


def bezier(p0: dict[str, float], c0: dict[str, float], c1: dict[str, float], p1: dict[str, float], t: float) -> dict[str, float]:
    u = 1.0 - t
    return {
        "x": u**3 * p0["x"] + 3 * u * u * t * c0["x"] + 3 * u * t * t * c1["x"] + t**3 * p1["x"],
        "y": u**3 * p0["y"] + 3 * u * u * t * c0["y"] + 3 * u * t * t * c1["y"] + t**3 * p1["y"],
    }


def strip_duplicate_vector_key(keys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(keys) >= 2 and math.isclose(keys[0]["x"], keys[-1]["x"]) and math.isclose(keys[0]["y"], keys[-1]["y"]):
        return keys[:-1]
    return keys


def sample_vector_trace(keys: list[dict[str, Any]], origin: dict[str, float], half_width_m: float) -> list[dict[str, Any]]:
    unique_keys = strip_duplicate_vector_key(keys)
    sampled = []
    for index, key in enumerate(unique_keys):
        next_key = unique_keys[(index + 1) % len(unique_keys)]
        p0 = {"x": key["x"], "y": key["y"]}
        p1 = {"x": next_key["x"], "y": next_key["y"]}
        out_handle = handle_vector2(float(key["angleADeg"]), float(key["weightA"]))
        c0 = {"x": p0["x"] + out_handle["x"], "y": p0["y"] + out_handle["y"]}
        c1 = incoming_handle_endpoint(key, p1)
        for step in range(SAMPLES_PER_VECTOR_SEGMENT):
            t = step / SAMPLES_PER_VECTOR_SEGMENT
            raw_point = bezier(p0, c0, c1, p1, t)
            converted = convert_point(raw_point, origin)
            sampled.append(
                {
                    "source": "vector-sample",
                    "sourceIndex": index,
                    "t": t,
                    "x": converted["x"],
                    "y": converted["y"],
                    "leftWidth": half_width_m,
                    "rightWidth": half_width_m,
                }
            )
    if len(sampled) < MIN_CENTERLINE_POINTS:
        raise RuntimeError("Vector-sampled centerline did not reach C-S01 minimum point count")
    for index, point in enumerate(sampled):
        point["id"] = f"p{index:02d}"
    return sampled


def nearest_centerline_point_id(centerline: list[dict[str, Any]], point: dict[str, float]) -> str:
    nearest = min(centerline, key=lambda candidate: math.hypot(candidate["x"] - point["x"], candidate["y"] - point["y"]))
    return nearest["id"]


def checkpoint_id(label: str | None, index: int) -> str:
    normalized = (label or f"checkpoint-{index}").lower().replace(" ", "-")
    normalized = "".join(char for char in normalized if char.isalnum() or char == "-").strip("-")
    return normalized or f"checkpoint-{index}"


def build_track_definition(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    route_fixture = fixture_by_id(raw, "T05_start_and_checkpoints")
    vector_trace = route_fixture.get("vectorTraceCandidates", {}).get("primaryRoad")
    if not vector_trace:
        raise RuntimeError("Missing primaryRoad vectorTraceCandidate from G-S02 raw data")
    raw_keys = strip_duplicate_vector_key(vector_trace["keys"])
    raw_points = [{"x": key["x"], "y": key["y"]} for key in raw_keys]
    half_width_m = road_half_width_m(route_fixture)
    raw_origin = centroid(raw_points)
    converted_points = [convert_point(point, raw_origin) for point in raw_points]
    converted_area = signed_area(converted_points)
    direction = "counter-clockwise" if converted_area > 0 else "clockwise"
    centerline = sample_vector_trace(raw_keys, raw_origin, half_width_m)
    total_road_width_m = half_width_m * 2.0

    checkpoints = []
    finish_checkpoint = None
    for index, checkpoint in enumerate(route_fixture["checkpointCandidates"]):
        converted = convert_point({"x": checkpoint["x"], "y": checkpoint["y"]}, raw_origin)
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
        "trackId": "ur2d2-editor-t05-candidate",
        "name": "UR2D2 Editor T05 Candidate",
        "coordinateSystem": {
            "units": {"distance": "m", "angle": "rad", "time": "s"},
            "axis": {"x": "right", "y": "forward"},
            "orientation": direction,
        },
        "closedLoop": True,
        "direction": direction,
        "surface": {"type": "asphalt", "grip": 1.0},
        "centerline": [
            {
                "id": point["id"],
                "x": round(point["x"], 6),
                "y": round(point["y"], 6),
                "leftWidth": round(point["leftWidth"], 6),
                "rightWidth": round(point["rightWidth"], 6),
            }
            for point in centerline
        ],
        "startLine": {
            "centerlinePointId": start_point_id,
            "width": round((centerline[0]["leftWidth"] + centerline[0]["rightWidth"]), 6),
        },
        "checkpoints": checkpoints,
    }

    conversion_notes = {
        "sourceFixture": route_fixture["fixture"],
        "sourceSha256": route_fixture["sourceSha256"],
        "rawOriginEditorUnits": raw_origin,
        "scalePolicy": {
            "editorUnitsPerMetre": EDITOR_UNITS_PER_METRE,
            "status": "grid-calibrated",
            "reason": "Les deux premières clés route sont séparées par 1056 unités éditeur et 33 carreaux de grille, soit 32 unités éditeur par carreau. Avec 1 carreau = 2,5 m, l'échelle retenue est 12,8 unités éditeur par mètre.",
        },
        "widthPolicy": {
            "totalRoadWidthM": total_road_width_m,
            "leftWidthM": half_width_m,
            "rightWidthM": half_width_m,
            "status": "source-file",
            "reason": "La largeur totale provient de `globalCandidates.float32At0`. Sa valeur 10,0 correspond visuellement à environ 4 carreaux, soit 2,5 m par carreau avec l'échelle grille.",
        },
        "axisPolicy": {
            "x": "raw x increases to TrackDefinition x",
            "y": "raw y is inverted so screen-down editor coordinates become negative forward coordinates",
            "status": "experimental",
        },
        "vectorInterpolationPolicy": {
            "status": "experimental-needs-g-s04-confirmation",
            "formula": "cubic bezier per segment; handle A is key[i] + angleA[i]/weightA[i], handle B is key[i+1] + angleB[i]/weightB[i]",
            "samplesPerSegment": SAMPLES_PER_VECTOR_SEGMENT,
            "warning": "UR2D2 stores the incoming B handle on the previous segment row. Handle vectors use a global vertical inversion relative to raw point coordinates.",
        },
        "centerlinePolicy": {
            "rawVectorKeys": len(raw_keys),
            "convertedCenterlinePoints": len(centerline),
            "method": "drop duplicated closure key, then sample each vector segment with a provisional cubic Bezier formula",
        },
        "checkpointPolicy": {
            "method": "map each raw checkpoint candidate to nearest converted centerline point; use Finish as start line when present",
            "rawCheckpointCount": len(route_fixture["checkpointCandidates"]),
        },
    }
    return track, conversion_notes


def render_markdown(result: dict[str, Any]) -> str:
    validation = result["validation"]
    preprocessed = validation.get("preprocessed", {})
    notes = result["conversionNotes"]
    lines = [
        "# G-S03 - Conversion candidate vers TrackDefinition",
        "",
        "- **Expérience :** G - Import du modèle minimal depuis les sauvegardes UR2D2",
        "- **Scénario :** G-S03",
        f"- **Statut :** {result['status']}",
        f"- **Date :** {result['generatedAt']}",
        f"- **TrackDefinition :** `{result['trackDefinitionPath']}`",
        f"- **Validation C-S01 :** {'succès' if validation['success'] else 'échec'}",
        "",
        "## Décision du jalon",
        "",
    ]
    if validation["success"]:
        lines.append("G-S03 produit un `TrackDefinition` candidat qui passe les invariants C-S01.")
    else:
        lines.append("G-S03 produit un `TrackDefinition` candidat, mais il ne passe pas encore les invariants C-S01.")

    lines.extend(
        [
            "",
            "## Politique de conversion",
            "",
            f"- Échelle : `1 m = {notes['scalePolicy']['editorUnitsPerMetre']} unités éditeur` (`{notes['scalePolicy']['status']}`).",
            f"- Raison échelle : {notes['scalePolicy']['reason']}",
            f"- Largeur route : {notes['widthPolicy']['totalRoadWidthM']:.3f} m total (`{notes['widthPolicy']['status']}`).",
            f"- Axes : {notes['axisPolicy']['x']} ; {notes['axisPolicy']['y']} (`{notes['axisPolicy']['status']}`).",
            f"- Interpolation vectorielle : {notes['vectorInterpolationPolicy']['formula']} (`{notes['vectorInterpolationPolicy']['status']}`).",
            f"- Convention poignées : {notes['vectorInterpolationPolicy']['warning']}",
            f"- Ligne centrale : {notes['centerlinePolicy']['rawVectorKeys']} clés vectorielles -> {notes['centerlinePolicy']['convertedCenterlinePoints']} points échantillonnés.",
            f"- Checkpoints : {notes['checkpointPolicy']['rawCheckpointCount']} candidats mappés au point central le plus proche.",
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
        for error in validation["errors"]:
            lines.append(f"- {error}")

    lines.extend(
        [
            "",
            "## Réserves",
            "",
            "- L'échelle est plausible mais pas calibrée avec une mesure connue en jeu.",
            "- L'échelle est recalibrée depuis la grille éditeur : 33 carreaux pour 1056 unités éditeur, 1 carreau = 2,5 m.",
            "- La largeur de route n'est plus forcée : elle provient du fichier source (`globalCandidates.float32At0`).",
            "- L'inversion de l'axe Y est une hypothèse de convention écran -> monde.",
            "- La ligne centrale est échantillonnée depuis des courbes de Bézier candidates ; la convention des poignées est cohérente avec le retour G-S04 mais reste à confirmer sur davantage de fixtures.",
            "- Les murs, surfaces, lignes IA et pitlane lus par G-S02 ne sont pas encore inclus comme champs source `TrackDefinition` v0.1.",
            "- G-S04 valide la cohérence visuelle interne, mais pas encore une superposition pixel-perfect avec une capture éditeur.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW_PATH)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    raw = load_json(args.raw)
    track, conversion_notes = build_track_definition(raw)

    validator = load_c_s01_validator()
    errors = validator.validate_track(track)
    preprocessed = validator.preprocess_track(track) if not errors else {}
    success = (
        not errors
        and preprocessed["totalLengthM"] > validator.MIN_LOOP_LENGTH_M
        and preprocessed["minTotalWidthM"] >= validator.MIN_TOTAL_WIDTH_M
        and math.isfinite(preprocessed["maxAbsCurvature"])
    )

    track_path = results_dir / "g_s03_track_definition_candidate.json"
    summary_path = results_dir / "g_s03_track_definition_conversion.json"
    report_path = results_dir / "G_S03_TRACK_DEFINITION_CONVERSION_RESULT.md"
    write_json(track_path, track)

    result = {
        "scenario": "G-S03",
        "status": "validated-with-reserves" if success else "conversion-failed-validation",
        "generatedAt": utc_now(),
        "rawInputPath": str(args.raw.resolve()),
        "trackDefinitionPath": str(track_path),
        "conversionNotes": conversion_notes,
        "validation": {
            "success": success,
            "errors": errors,
            "preprocessed": preprocessed,
        },
    }
    write_json(summary_path, result)
    report_path.write_text(render_markdown(result), encoding="utf-8")

    print(f"G-S03 status: {result['status']}")
    print(f"C-S01 validation: {'success' if success else 'failure'}")
    print(f"Wrote: {report_path}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
