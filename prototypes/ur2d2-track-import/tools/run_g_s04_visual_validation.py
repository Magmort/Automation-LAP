#!/usr/bin/env python3
"""Validate the G-S03 conversion with source-to-candidate visual checks."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RAW_PATH = RESULTS_DIR / "g_s02_raw_reader.json"
TRACK_PATH = RESULTS_DIR / "g_s03_track_definition_candidate.json"
CONVERSION_PATH = RESULTS_DIR / "g_s03_track_definition_conversion.json"
SUMMARY_PATH = RESULTS_DIR / "g_s04_visual_validation.json"
REPORT_PATH = RESULTS_DIR / "G_S04_VISUAL_VALIDATION_RESULT.md"

STRAIGHT_ALIGNMENT_TOLERANCE_M = 0.001
CHECKPOINT_PROJECTION_WARNING_M = 6.0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fixture_by_id(raw: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    for fixture in raw["rawFixtures"]:
        if fixture["fixture"] == fixture_id:
            return fixture
    raise KeyError(f"Missing fixture {fixture_id}")


def convert_raw_point(point: dict[str, float], origin: dict[str, float], scale: float) -> dict[str, float]:
    return {
        "x": (float(point["x"]) - origin["x"]) / scale,
        "y": -(float(point["y"]) - origin["y"]) / scale,
    }


def find_nearest_centerline_point(centerline: list[dict[str, Any]], point: dict[str, float]) -> tuple[dict[str, Any], float]:
    nearest = min(centerline, key=lambda candidate: math.hypot(candidate["x"] - point["x"], candidate["y"] - point["y"]))
    distance = math.hypot(nearest["x"] - point["x"], nearest["y"] - point["y"])
    return nearest, distance


def line_block_by_offset(fixture: dict[str, Any], hex_offset: str) -> dict[str, Any] | None:
    return next((block for block in fixture.get("lineLikeBlocks", []) if block.get("hexOffset") == hex_offset), None)


def nearest_line_block_after_token(fixture: dict[str, Any], token: str, max_distance: int) -> dict[str, Any] | None:
    token_offsets = [
        item["tokenOffset"]
        for item in fixture.get("namedObjectCandidates", [])
        if item.get("token") == token and "tokenOffset" in item
    ]
    candidates = []
    for offset in token_offsets:
        for block in fixture.get("lineLikeBlocks", []):
            distance = block["offset"] - offset
            if 0 <= distance <= max_distance:
                candidates.append((distance, block))
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1] if candidates else None


def line_blocks_after_token(fixture: dict[str, Any], token: str, max_distance: int) -> list[dict[str, Any]]:
    token_offsets = [
        item["tokenOffset"]
        for item in fixture.get("namedObjectCandidates", [])
        if item.get("token") == token and "tokenOffset" in item
    ]
    blocks = []
    seen_offsets = set()
    for offset in token_offsets:
        for block in fixture.get("lineLikeBlocks", []):
            distance = block["offset"] - offset
            if 0 <= distance <= max_distance and block["offset"] not in seen_offsets:
                seen_offsets.add(block["offset"])
                blocks.append(block)
    blocks.sort(key=lambda block: block["offset"])
    return blocks


def collect_visual_layers(raw: dict[str, Any]) -> dict[str, Any]:
    t03 = fixture_by_id(raw, "T03_ai_line")
    t04 = fixture_by_id(raw, "T04_limits_or_walls")
    t05 = fixture_by_id(raw, "T05_start_and_checkpoints")
    t06 = fixture_by_id(raw, "T06_pit_lane")
    t07 = fixture_by_id(raw, "T07_surfaces")

    inventory = raw.get("elementInventory", {}).get("items", [])
    ai_item = next((item for item in inventory if item.get("id") == "ai_lines"), {})
    ai_blocks = [
        line_block_by_offset(t03, block["hexOffset"])
        for block in ai_item.get("blocks", [])
    ]
    ai_blocks = [block for block in ai_blocks if block is not None]

    pit_blocks = line_blocks_after_token(t06, "spr_pit_building_to_right", 768)
    return {
        "roadVectorKeys": len(t05["vectorTraceCandidates"]["primaryRoad"]["keys"]) - 1,
        "aiLines": len(ai_blocks),
        "checkpoints": len(t05.get("checkpointCandidates", [])),
        "wallBlocks": 1 if nearest_line_block_after_token(t04, "wall1", 128) else 0,
        "pitConnectors": min(2, len(pit_blocks)),
        "pitlaneSegments": 1 if len(pit_blocks) >= 2 else 0,
        "sandPolygons": 1 if nearest_line_block_after_token(t07, "spr_sand", 128) else 0,
        "treePolygons": 1 if nearest_line_block_after_token(t07, "forrest2", 128) else 0,
    }


def build_checkpoint_projection_checks(
    raw: dict[str, Any],
    track: dict[str, Any],
    conversion: dict[str, Any],
) -> list[dict[str, Any]]:
    origin = conversion["conversionNotes"]["rawOriginEditorUnits"]
    scale = conversion["conversionNotes"]["scalePolicy"]["editorUnitsPerMetre"]
    t05 = fixture_by_id(raw, "T05_start_and_checkpoints")
    by_label = {
        checkpoint["id"]: checkpoint["centerlinePointId"]
        for checkpoint in track.get("checkpoints", [])
    }
    checks = []
    for raw_checkpoint in t05.get("checkpointCandidates", []):
        label = (raw_checkpoint.get("label") or "checkpoint").lower().replace(" ", "-")
        if label == "finish":
            checkpoint_id = "finish"
        elif label == "checkpoint-1":
            checkpoint_id = "checkpoint-1"
        elif label == "checkpoint-2":
            checkpoint_id = "checkpoint-2"
        else:
            checkpoint_id = label
        converted = convert_raw_point(raw_checkpoint, origin, scale)
        nearest, distance = find_nearest_centerline_point(track["centerline"], converted)
        expected_point_id = by_label.get(checkpoint_id)
        checks.append(
            {
                "id": checkpoint_id,
                "rawLabel": raw_checkpoint.get("label"),
                "projectedPointId": expected_point_id,
                "nearestPointId": nearest["id"],
                "distanceM": distance,
                "status": "pass"
                if expected_point_id == nearest["id"] and distance <= CHECKPOINT_PROJECTION_WARNING_M
                else "reserve",
            }
        )
    return checks


def build_straight_alignment_checks(track: dict[str, Any]) -> list[dict[str, Any]]:
    centerline = track["centerline"]
    top_points = centerline[0:5]
    bottom_points = centerline[8:13]
    top_y_values = [point["y"] for point in top_points]
    bottom_y_values = [point["y"] for point in bottom_points]
    top_deviation = max(top_y_values) - min(top_y_values)
    bottom_deviation = max(bottom_y_values) - min(bottom_y_values)
    return [
        {
            "id": "top-straight",
            "expected": "samples p00..p04 remain aligned on the P00-P04 axis",
            "maxDeviationM": top_deviation,
            "status": "pass" if top_deviation <= STRAIGHT_ALIGNMENT_TOLERANCE_M else "fail",
        },
        {
            "id": "bottom-straight",
            "expected": "samples p08..p12 remain aligned on the P08-P12 axis",
            "maxDeviationM": bottom_deviation,
            "status": "pass" if bottom_deviation <= STRAIGHT_ALIGNMENT_TOLERANCE_M else "fail",
        },
    ]


def build_result() -> dict[str, Any]:
    raw = load_json(RAW_PATH)
    track = load_json(TRACK_PATH)
    conversion = load_json(CONVERSION_PATH)
    visual_layers = collect_visual_layers(raw)
    straight_checks = build_straight_alignment_checks(track)
    checkpoint_checks = build_checkpoint_projection_checks(raw, track, conversion)
    c_s01_success = bool(conversion.get("validation", {}).get("success"))
    required_layers_present = (
        visual_layers["roadVectorKeys"] == 4
        and visual_layers["aiLines"] == 3
        and visual_layers["checkpoints"] == 3
        and visual_layers["wallBlocks"] == 1
        and visual_layers["pitConnectors"] == 2
        and visual_layers["pitlaneSegments"] == 1
        and visual_layers["sandPolygons"] == 1
        and visual_layers["treePolygons"] == 1
    )
    hard_checks_pass = c_s01_success and all(check["status"] == "pass" for check in straight_checks)
    status = "validated-with-reserves" if hard_checks_pass and required_layers_present else "needs-rework"
    return {
        "scenario": "G-S04",
        "status": status,
        "generatedAt": utc_now(),
        "inputs": {
            "rawReader": str(RAW_PATH.resolve()),
            "trackDefinition": str(TRACK_PATH.resolve()),
            "conversionSummary": str(CONVERSION_PATH.resolve()),
        },
        "visualizationPath": str((RESULTS_DIR / "G_S04_VISUAL_VALIDATION.svg").resolve()),
        "checks": {
            "cS01Validation": {"status": "pass" if c_s01_success else "fail"},
            "requiredVisualLayers": {
                "status": "pass" if required_layers_present else "fail",
                "layers": visual_layers,
            },
            "straightAlignment": straight_checks,
            "checkpointProjection": checkpoint_checks,
        },
        "decisionNotes": [
            "La forme convertie de la route est cohérente pour préparer la validation fonctionnelle G-S05.",
            "Les deux segments droits valident la convention corrigée de la poignée B sur les deux axes faciles à contrôler.",
            "La largeur de route est visuellement recalibrée à 5 m au total après retour utilisateur : 10 m rendait la piste presque deux fois trop large.",
            "pit1 est confirmé comme voie d'entrée des stands, pit2 comme voie de sortie, et la pitlane manquante est représentée par le segment droit entre les deux.",
            "Les lignes IA, le mur, les connecteurs pitlane, le sable et les arbres sont visualisés depuis les blocs bruts, mais ne font pas encore partie de TrackDefinition v0.1.",
            "La poignée B est maintenant interprétée comme la poignée entrante de la clé suivante : B visible sur Ki provient de la ligne Ki-1.",
            "Les vecteurs de poignées utilisent une inversion verticale globale par rapport aux coordonnées brutes des points.",
            "La convention d'index et de repère des poignées rétablit l'alignement tangent, mais reste à confirmer visuellement sur toutes les familles de tracés.",
            "Aucune capture de l'éditeur n'est disponible ; G-S04 valide donc la cohérence interne source/candidat plutôt qu'une superposition pixel-perfect avec l'UI UR2D2.",
        ],
    }


def render_markdown(result: dict[str, Any]) -> str:
    layers = result["checks"]["requiredVisualLayers"]["layers"]
    lines = [
        "# G-S04 - Validation visuelle de la conversion UR2D2",
        "",
        "- **Expérience :** G - Import du modèle minimal depuis les sauvegardes UR2D2",
        "- **Scénario :** G-S04",
        f"- **Statut :** {result['status']}",
        f"- **Date :** {result['generatedAt']}",
        f"- **Visualisation :** `{result['visualizationPath']}`",
        "",
        "## Décision du jalon",
        "",
    ]
    if result["status"] == "validated-with-reserves":
        lines.append("G-S04 valide visuellement la cohérence interne de la conversion et autorise le passage à G-S05 avec réserves.")
    else:
        lines.append("G-S04 ne valide pas encore la conversion ; une reprise de la lecture ou de la transformation est nécessaire.")
    lines.extend(
        [
            "",
            "## Couches affichées",
            "",
            f"- Clés vectorielles de route : {layers['roadVectorKeys']}",
            f"- Lignes IA : {layers['aiLines']}",
            f"- Checkpoints : {layers['checkpoints']}",
            f"- Mur multi-segments : {layers['wallBlocks']}",
            f"- Connecteurs pitlane candidats : {layers['pitConnectors']}",
            f"- Segment pitlane droit : {layers['pitlaneSegments']}",
            f"- Polygone sable : {layers['sandPolygons']}",
            f"- Polygone arbres : {layers['treePolygons']}",
            "",
            "## Contrôles",
            "",
            f"- Validation C-S01 : {result['checks']['cS01Validation']['status']}",
            f"- Couches requises : {result['checks']['requiredVisualLayers']['status']}",
            "",
            "| Contrôle | Statut | Écart |",
            "| --- | --- | ---: |",
        ]
    )
    for check in result["checks"]["straightAlignment"]:
        lines.append(f"| {check['id']} | {check['status']} | {check['maxDeviationM']:.6f} m |")
    lines.extend(
        [
            "",
            "## Projection des checkpoints",
            "",
            "| Checkpoint | Point projeté | Point le plus proche | Distance | Statut |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for check in result["checks"]["checkpointProjection"]:
        lines.append(
            f"| {check['id']} | {check.get('projectedPointId') or '-'} | {check['nearestPointId']} | "
            f"{check['distanceM']:.3f} m | {check['status']} |"
        )
    lines.extend(["", "## Réserves", ""])
    for note in result["decisionNotes"][2:]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result = build_result()
    write_json(SUMMARY_PATH, result)
    REPORT_PATH.write_text(render_markdown(result), encoding="utf-8")
    print(f"G-S04 status: {result['status']}")
    print(f"Wrote: {REPORT_PATH}")
    return 0 if result["status"] == "validated-with-reserves" else 1


if __name__ == "__main__":
    raise SystemExit(main())
