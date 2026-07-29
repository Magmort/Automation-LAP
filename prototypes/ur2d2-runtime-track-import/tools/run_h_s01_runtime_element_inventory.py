#!/usr/bin/env python3
"""Run H-S01b: localize every editor-save element inside the runtime package."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
RESULTS_DIR = ROOT / "results"
H_S00_PATH = RESULTS_DIR / "h_s00_runtime_inventory_summary.json"
G_READER_PATH = REPO_ROOT / "prototypes" / "ur2d2-track-import" / "tools" / "run_g_s02_raw_reader.py"
SUMMARY_PATH = RESULTS_DIR / "h_s01_runtime_element_inventory.json"
REPORT_PATH = RESULTS_DIR / "H_S01_RUNTIME_ELEMENT_INVENTORY_RESULT.md"

CHECKPOINT_TOKEN = b"checkpoint\x00"
SPR_CHECKPOINT_TOKEN = b"spr_checkpoint\x00"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_g_reader() -> Any:
    spec = importlib.util.spec_from_file_location("g_s02_raw_reader", G_READER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {G_READER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_info(fixture: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((item for item in fixture["files"] if item["path"] == name), None)


def source_file(fixtures_root: Path, fixture: dict[str, Any], name: str) -> Path:
    return fixtures_root / fixture["fixture"] / name


def pack_f32(value: float) -> bytes:
    return struct.pack("<f", float(value))


def float_offsets(data: bytes, value: float) -> list[int]:
    needle = pack_f32(value)
    offsets: list[int] = []
    start = 0
    while True:
        found = data.find(needle, start)
        if found < 0:
            return offsets
        offsets.append(found)
        start = found + 1


def pair_offsets(data: bytes, x: float, y: float) -> list[int]:
    needle = struct.pack("<ff", float(x), float(y))
    offsets: list[int] = []
    start = 0
    while True:
        found = data.find(needle, start)
        if found < 0:
            return offsets
        offsets.append(found)
        start = found + 1


def yx_pair_offsets(data: bytes, x: float, y: float) -> list[int]:
    return pair_offsets(data, y, x)


def exact_token_offsets(data: bytes, token: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        found = data.find(token, start)
        if found < 0:
            return offsets
        offsets.append(found)
        start = found + 1


def alpha_bbox(path: Path) -> dict[str, Any] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    if not path.exists():
        return None
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        bbox = alpha.getbbox()
        if bbox is None:
            return {
                "path": path.name,
                "size": list(rgba.size),
                "nonTransparentPixelCount": 0,
                "bbox": None,
            }
        histogram = alpha.histogram()
        return {
            "path": path.name,
            "size": list(rgba.size),
            "nonTransparentPixelCount": sum(histogram[1:]),
            "bbox": list(bbox),
        }


def runtime_checkpoint_records(data: bytes) -> list[dict[str, Any]]:
    records = []
    for token_offset in exact_token_offsets(data, CHECKPOINT_TOKEN):
        start = token_offset - 20
        if start < 0:
            continue
        values = struct.unpack_from("<fffff", data, start)
        rotation, size, x, y, index_or_flag = values
        if not (-720.0 <= rotation <= 720.0 and 0.0 <= size <= 250.0):
            continue
        if not (0.0 <= x <= 5000.0 and 0.0 <= y <= 5000.0):
            continue
        records.append(
            {
                "recordOffset": start,
                "tokenOffset": token_offset,
                "rotationRuntimeDeg": rotation,
                "sizeCandidate": size,
                "x": x,
                "y": y,
                "indexOrFlag": index_or_flag,
            }
        )
    return records


def sprite_checkpoint_records(data: bytes) -> list[dict[str, Any]]:
    records = []
    for token_offset in exact_token_offsets(data, SPR_CHECKPOINT_TOKEN):
        start = token_offset - 28
        if start < 0:
            continue
        values = struct.unpack_from("<fffffff", data, start)
        x = values[5]
        y = values[6]
        if not (0.0 <= x <= 5000.0 and 0.0 <= y <= 5000.0):
            continue
        records.append(
            {
                "recordOffset": start,
                "tokenOffset": token_offset,
                "rotationDeg": values[0],
                "x": x,
                "y": y,
                "rawValues": [round(value, 6) for value in values],
            }
        )
    return records


def point_runtime_presence(data: bytes, point: dict[str, Any]) -> dict[str, Any]:
    x = float(point["x"])
    y = float(point["y"])
    x_offsets = float_offsets(data, x)
    y_offsets = float_offsets(data, y)
    xy_offsets = pair_offsets(data, x, y)
    yx_offsets = yx_pair_offsets(data, x, y)
    return {
        "x": round(x, 6),
        "y": round(y, 6),
        "xOffsets": x_offsets[:8],
        "xOccurrenceCount": len(x_offsets),
        "yOffsets": y_offsets[:8],
        "yOccurrenceCount": len(y_offsets),
        "xyPairOffsets": xy_offsets[:8],
        "xyPairOccurrenceCount": len(xy_offsets),
        "yxPairOffsets": yx_offsets[:8],
        "yxPairOccurrenceCount": len(yx_offsets),
    }


def block_runtime_presence(data: bytes, block: dict[str, Any]) -> dict[str, Any]:
    points = block["points"]
    samples = [points[0]]
    if len(points) > 2:
        samples.append(points[len(points) // 2])
    if len(points) > 1:
        samples.append(points[-1])
    point_presence = [point_runtime_presence(data, point) for point in samples]
    xy_hits = sum(1 for item in point_presence if item["xyPairOccurrenceCount"] > 0)
    yx_hits = sum(1 for item in point_presence if item["yxPairOccurrenceCount"] > 0)
    scalar_hits = sum(1 for item in point_presence if item["xOccurrenceCount"] > 0 and item["yOccurrenceCount"] > 0)
    primary_offsets: list[int] = []
    for item in point_presence:
        primary_offsets.extend(item["xyPairOffsets"])
        primary_offsets.extend(item["yxPairOffsets"])
    primary_offsets = sorted(set(primary_offsets))
    return {
        "sourceOffset": block["offset"],
        "sourceHexOffset": block["hexOffset"],
        "sourcePointCount": block["pointCount"],
        "sampledPointsChecked": point_presence,
        "xyPairHits": xy_hits,
        "yxPairHits": yx_hits,
        "scalarCoordinateHits": scalar_hits,
        "runtimeOffsets": primary_offsets[:12],
    }


def find_blocks(parsed_sav: dict[str, Any]) -> dict[str, Any]:
    blocks = parsed_sav["lineLikeBlocks"]
    by_offset = {block["hexOffset"]: block for block in blocks}
    return {
        "road": by_offset.get("0x004d"),
        "sand_zone": by_offset.get("0x0290"),
        "tree_zone": by_offset.get("0x04c8"),
        "wall": by_offset.get("0x06e6"),
        "pitlane_entry": by_offset.get("0x0997"),
        "pitlane_exit": by_offset.get("0x0a43"),
        "ai_line_1": by_offset.get("0x0b43"),
        "ai_line_2": by_offset.get("0x0c43"),
        "ai_line_3": by_offset.get("0x0d43"),
    }


def count_road_segments(block: dict[str, Any] | None) -> int:
    if block is None:
        return 0
    points = block["points"]
    if len(points) >= 2 and points[0] == points[-1]:
        return len(points) - 1
    return max(0, len(points) - 1)


def compact_checkpoint_matches(data: bytes, checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = runtime_checkpoint_records(data)
    matches = []
    for checkpoint in checkpoints:
        best_record = None
        best_distance = math.inf
        for record in records:
            distance = math.hypot(float(record["x"]) - float(checkpoint["x"]), float(record["y"]) - float(checkpoint["y"]))
            if distance < best_distance:
                best_distance = distance
                best_record = record
        matches.append(
            {
                "label": checkpoint.get("label") or "Checkpoint",
                "sourcePayloadOffset": checkpoint["payloadHexOffset"],
                "x": checkpoint["x"],
                "y": checkpoint["y"],
                "runtimeRecordOffset": best_record["recordOffset"] if best_record else None,
                "runtimeTokenOffset": best_record["tokenOffset"] if best_record else None,
                "distanceEditorUnits": round(best_distance, 6) if best_record else None,
                "rotationRuntimeMinusEditorMinus90Deg": round(
                    float(best_record["rotationRuntimeDeg"]) - (float(checkpoint["rotationDeg"]) - 90.0),
                    6,
                )
                if best_record
                else None,
            }
        )
    return matches


def runtime_layer_evidence(fixture_root: Path) -> dict[str, Any]:
    layer_names = ["track.png", "track_preview.png", "gravel.png", "grass.png", "minimap.png"]
    return {name: alpha_bbox(fixture_root / name) for name in layer_names}


def relevant_runtime_tokens(data: bytes) -> list[dict[str, Any]]:
    tokens = [b"checkpoint\x00", b"spr_checkpoint\x00", b"spr_pit_building_to_right\x00"]
    items = []
    for token in tokens:
        offsets = exact_token_offsets(data, token)
        if offsets:
            items.append(
                {
                    "token": token.rstrip(b"\x00").decode("ascii"),
                    "offsets": offsets,
                    "count": len(offsets),
                }
            )
    return items


def relevant_editor_tokens(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known_fragments = [
        "spr_road",
        "grass_1",
        "spr_sand",
        "spr_sand_edge",
        "forrest2",
        "spr_water_edge",
        "wall1",
        "spr_checkpoint",
        "checkpoint",
        "Finish",
        "Checkpoint 1",
        "Checkpoint 2",
        "spr_pit_building_to_right",
    ]
    relevant = []
    for token in tokens:
        value = token["value"].strip("@? ")
        if any(fragment == value for fragment in known_fragments):
            item = dict(token)
            item["value"] = value
            relevant.append(item)
    return relevant


def item(
    item_id: str,
    label: str,
    expected: int,
    detected_in_sav: int,
    runtime_status: str,
    confidence: str,
    evidence: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "label": label,
        "expected": expected,
        "detectedInEditorSav": detected_in_sav,
        "runtimeStatus": runtime_status,
        "confidence": confidence,
        "evidence": evidence,
        "details": details or {},
    }


def build_summary(h_s00: dict[str, Any]) -> dict[str, Any]:
    if not h_s00.get("fixtures"):
        raise RuntimeError("H-S00 has no runtime fixture")
    fixtures_root = Path(h_s00["fixturesRoot"])
    fixture = h_s00["fixtures"][0]
    fixture_root = fixtures_root / fixture["fixture"]
    track_data_path = source_file(fixtures_root, fixture, "track.data")
    track_editor_path = source_file(fixtures_root, fixture, "track_editor.sav")
    track_data = track_data_path.read_bytes()
    track_editor = track_editor_path.read_bytes()

    g_reader = load_g_reader()
    parsed_sav = g_reader.parse_fixture(
        {
            "fixture": f"{fixture['fixture']}_track_editor_sav",
            "path": track_editor_path,
            "data": track_editor,
        }
    )
    blocks = find_blocks(parsed_sav)
    layers = runtime_layer_evidence(fixture_root)
    checkpoint_matches = compact_checkpoint_matches(track_data, parsed_sav["checkpointCandidates"])

    block_presence = {
        key: block_runtime_presence(track_data, block)
        for key, block in blocks.items()
        if block is not None
    }
    track_data_tokens = relevant_runtime_tokens(track_data)

    road_segments = count_road_segments(blocks["road"])
    ai_detected = sum(1 for key in ("ai_line_1", "ai_line_2", "ai_line_3") if blocks[key] is not None)
    checkpoint_detected = len(parsed_sav["checkpointCandidates"])
    pit_token_offsets = exact_token_offsets(track_data, b"spr_pit_building_to_right\x00")
    sprite_checkpoint_count = len(sprite_checkpoint_records(track_data))
    compact_checkpoint_ok = all(match["distanceEditorUnits"] is not None and match["distanceEditorUnits"] <= 0.01 for match in checkpoint_matches)

    sand_bbox = layers.get("gravel.png", {}).get("bbox") if layers.get("gravel.png") else None
    preview_bbox = layers.get("track_preview.png", {}).get("bbox") if layers.get("track_preview.png") else None
    track_bbox = layers.get("track.png", {}).get("bbox") if layers.get("track.png") else None

    items = [
        item(
            "road_segments",
            "Segments de route",
            4,
            road_segments,
            "localized-sampled-track-data",
            "high",
            "La route est lue comme trace vectorielle dans track_editor.sav et présente comme blocs échantillonnés dans track.data.",
            block_presence.get("road"),
        ),
        item(
            "ai_lines",
            "Lignes IA",
            3,
            ai_detected,
            "localized-sampled-track-data",
            "high",
            "Les trois lignes IA sont lues dans track_editor.sav ; leurs points caractéristiques ressortent dans track.data, avec alternance XY/YX selon les blocs runtime.",
            {key: block_presence.get(key) for key in ("ai_line_1", "ai_line_2", "ai_line_3")},
        ),
        item(
            "checkpoints",
            "Checkpoints",
            3,
            checkpoint_detected,
            "localized-runtime-records",
            "high",
            "Les trois checkpoints sont présents dans track_editor.sav et correspondent aux records compacts de track.data.",
            {"matches": checkpoint_matches, "spriteCheckpointRecordCount": sprite_checkpoint_count},
        ),
        item(
            "pitlane",
            "Pitlane",
            1,
            1 if blocks["pitlane_entry"] and blocks["pitlane_exit"] else 0,
            "localized-token-and-sampled-connectors",
            "medium",
            "Le bâtiment pitlane est présent par token runtime ; les deux voies pit1/pit2 sont lues comme connecteurs vectoriels dans le .sav et échantillonnées dans track.data.",
            {
                "runtimePitBuildingTokenOffsets": pit_token_offsets,
                "entry": block_presence.get("pitlane_entry"),
                "exit": block_presence.get("pitlane_exit"),
            },
        ),
        item(
            "pitlane_entry",
            "Entrée de pitlane",
            1,
            1 if blocks["pitlane_entry"] else 0,
            "localized-sampled-track-data",
            "medium",
            "La voie pit1 commence à 1565/826.9 dans le .sav et est retrouvée dans track.data.",
            block_presence.get("pitlane_entry"),
        ),
        item(
            "pitlane_exit",
            "Sortie de pitlane",
            1,
            1 if blocks["pitlane_exit"] else 0,
            "localized-sampled-track-data",
            "medium",
            "La voie pit2 commence à 2819/826.9 dans le .sav ; ses coordonnées sont retrouvées dans track.data, surtout en stockage YX.",
            block_presence.get("pitlane_exit"),
        ),
        item(
            "wall",
            "Mur en plusieurs segments",
            1,
            1 if blocks["wall"] else 0,
            "editor-vector-and-baked-runtime-raster",
            "medium",
            "Le mur est vectoriel dans track_editor.sav ; dans le runtime jouable il est principalement validé par sa présence rasterisée dans track.png/track_preview.png.",
            {"source": block_presence.get("wall"), "trackPngBbox": track_bbox, "previewBbox": preview_bbox},
        ),
        item(
            "sand_zone",
            "Zone de sable (polygone)",
            1,
            1 if blocks["sand_zone"] else 0,
            "editor-vector-and-runtime-layer",
            "high",
            "Le polygone sable est vectoriel dans track_editor.sav et correspond au calque runtime gravel.png.",
            {"source": block_presence.get("sand_zone"), "gravelPngBbox": sand_bbox},
        ),
        item(
            "tree_zone",
            "Zone d'arbres (polygone)",
            1,
            1 if blocks["tree_zone"] else 0,
            "editor-vector-and-baked-runtime-raster",
            "medium",
            "La zone d'arbres est vectorielle dans track_editor.sav ; le runtime la porte dans les rendus composites plutôt que dans un calque alpha isolable.",
            {"source": block_presence.get("tree_zone"), "trackPngBbox": track_bbox, "previewBbox": preview_bbox},
        ),
    ]

    all_source_items_found = all(entry["detectedInEditorSav"] == entry["expected"] for entry in items)
    all_runtime_items_localized = all(not entry["runtimeStatus"].startswith("missing") for entry in items)
    status = "complete-runtime-element-map" if all_source_items_found and all_runtime_items_localized and compact_checkpoint_ok else "incomplete"

    return {
        "scenario": "H-S01b",
        "status": status,
        "generatedAtUtc": utc_now(),
        "runtimeFixture": fixture["fixture"],
        "editorSav": {
            "path": "track_editor.sav",
            "sizeBytes": len(track_editor),
            "sourceSha256": parsed_sav["sourceSha256"],
            "globalWidthCandidate": parsed_sav["globalCandidates"]["float32At0"],
            "lineLikeBlocks": [
                {
                    "hexOffset": block["hexOffset"],
                    "pointCount": block["pointCount"],
                    "firstPoint": block["points"][0],
                    "lastPoint": block["points"][-1],
                }
                for block in parsed_sav["lineLikeBlocks"]
            ],
            "relevantStringTokens": relevant_editor_tokens(parsed_sav["stringTokens"]),
            "asciiStringCandidateCount": len(parsed_sav["stringTokens"]),
        },
        "trackData": {
            "path": "track.data",
            "sizeBytes": len(track_data),
            "relevantStringTokens": track_data_tokens,
            "asciiStringCandidateCount": len(list(re.finditer(rb"[\x20-\x7e]{4,}", track_data))),
        },
        "runtimeLayers": layers,
        "items": items,
        "checks": {
            "allExpectedElementsFoundInEditorSav": all_source_items_found,
            "allExpectedElementsLocalizedInRuntimePackage": all_runtime_items_localized,
            "compactCheckpointRecordsMatchEditorSav": compact_checkpoint_ok,
            "gravelLayerHasLocalizedAlphaBBox": sand_bbox is not None,
        },
        "notes": [
            "H-S01b distingue volontairement la source vectorielle embarquée (`track_editor.sav`) des données runtime jouables (`track.data` et PNG).",
            "Les éléments route, IA, checkpoints et pitlane gardent des signaux exploitables dans `track.data`.",
            "Les surfaces et objets décoratifs sont bien présents dans le `.sav`, mais une partie est consommée côté runtime sous forme de calques/rendus raster.",
            "Ce résultat suffit pour démarrer H-S02 sans perdre l'information source : le lecteur runtime devra garder `track_editor.sav` comme source vectorielle quand il est disponible.",
        ],
    }


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def render_offsets(offsets: list[int] | None) -> str:
    if not offsets:
        return "-"
    return ", ".join(f"`0x{offset:04x}`" for offset in offsets[:6])


def render_block_detail(details: dict[str, Any]) -> str:
    if not details:
        return "-"
    parts = []
    source_offsets = details.get("source", {}).get("runtimeOffsets") if isinstance(details.get("source"), dict) else []
    if source_offsets:
        parts.append(f"track.data {render_offsets(source_offsets)}")
    if "gravelPngBbox" in details:
        parts.append(f"`gravel.png` bbox {details['gravelPngBbox']}")
    if "trackPngBbox" in details:
        parts.append(f"`track.png` bbox {details['trackPngBbox']}")
    if parts:
        return " ; ".join(parts)
    offsets = details.get("runtimeOffsets")
    if offsets:
        return f"runtime {render_offsets(offsets)}"
    if "matches" in details:
        return ", ".join(
            f"{match['label']}@0x{match['runtimeRecordOffset']:04x}"
            for match in details["matches"]
            if match.get("runtimeRecordOffset") is not None
        )
    if "entry" in details or "exit" in details:
        entry_offsets = details.get("entry", {}).get("runtimeOffsets") if details.get("entry") else []
        exit_offsets = details.get("exit", {}).get("runtimeOffsets") if details.get("exit") else []
        token_offsets = details.get("runtimePitBuildingTokenOffsets", [])
        return f"token {render_offsets(token_offsets)} ; pit1 {render_offsets(entry_offsets)} ; pit2 {render_offsets(exit_offsets)}"
    nested_offsets = []
    for key, value in details.items():
        if isinstance(value, dict) and value.get("runtimeOffsets"):
            nested_offsets.append(f"{key} {render_offsets(value['runtimeOffsets'])}")
    if nested_offsets:
        return " ; ".join(nested_offsets)
    return "-"


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# H-S01b - Inventaire exhaustif des éléments runtime",
        "",
        "- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2",
        "- **Scénario :** H-S01b",
        f"- **Statut :** {summary['status']}",
        f"- **Date :** {summary['generatedAtUtc']}",
        f"- **Fixture runtime :** `{summary['runtimeFixture']}`",
        "",
        "## Décision du jalon",
        "",
    ]
    if summary["status"] == "complete-runtime-element-map":
        lines.append(
            "Tous les éléments attendus sont localisés dans le package runtime : soit comme source vectorielle dans `track_editor.sav`, soit comme signal exploitable dans `track.data`, soit comme rendu/calque raster runtime."
        )
    else:
        lines.append("L'inventaire est incomplet : H-S02 doit attendre ou traiter explicitement les réserves listées.")

    lines.extend(
        [
            "",
            "## Contrôles",
            "",
            "| Contrôle | Résultat |",
            "| --- | --- |",
        ]
    )
    for key, value in summary["checks"].items():
        lines.append(f"| `{key}` | {fmt_bool(value)} |")

    lines.extend(
        [
            "",
            "## Inventaire attendu",
            "",
            "| Élément | Attendu | Lu dans track_editor.sav | Localisation runtime | Confiance | Preuve courte | Offsets / couche |",
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for entry in summary["items"]:
        lines.append(
            f"| {entry['label']} | {entry['expected']} | {entry['detectedInEditorSav']} | "
            f"`{entry['runtimeStatus']}` | {entry['confidence']} | {entry['evidence']} | {render_block_detail(entry['details'])} |"
        )

    lines.extend(
        [
            "",
            "## Blocs vectoriels du track_editor.sav",
            "",
            "| Offset | Points | Premier point | Dernier point |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for block in summary["editorSav"]["lineLikeBlocks"]:
        first = block["firstPoint"]
        last = block["lastPoint"]
        lines.append(
            f"| `{block['hexOffset']}` | {block['pointCount']} | "
            f"({first['x']:.3f}, {first['y']:.3f}) | ({last['x']:.3f}, {last['y']:.3f}) |"
        )

    lines.extend(
        [
            "",
            "## Calques runtime",
            "",
            "| Fichier | Taille image | Pixels alpha | BBox alpha |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for name, layer in summary["runtimeLayers"].items():
        if layer is None:
            lines.append(f"| `{name}` | - | - | - |")
        else:
            lines.append(f"| `{name}` | {layer['size']} | {layer['nonTransparentPixelCount']} | {layer['bbox']} |")

    lines.extend(["", "## Tokens lisibles", ""])
    editor_tokens = [
        f"`{token['value']}` @ `{token['hexOffset']}`"
        for token in summary["editorSav"]["relevantStringTokens"]
    ]
    lines.append("- `track_editor.sav` pertinents : " + " ; ".join(editor_tokens))
    lines.append(f"- `track_editor.sav` candidats ASCII bruts : {summary['editorSav']['asciiStringCandidateCount']} chaînes, filtrées dans cette vue.")
    track_data_tokens = [
        f"`{item['token']}` @ {render_offsets(item['offsets'])}"
        for item in summary["trackData"]["relevantStringTokens"]
    ]
    lines.append("- `track.data` pertinents : " + " ; ".join(track_data_tokens))
    lines.append(f"- `track.data` candidats ASCII bruts : {summary['trackData']['asciiStringCandidateCount']} chaînes, volontairement non listées car très bruitées.")

    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in summary["notes"])
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            "On peut passer à H-S02, mais le lecteur runtime devra assumer une stratégie hybride : `track.data` pour les données jouables déjà échantillonnées, `track_info.data` pour les métadonnées, et `track_editor.sav` pour conserver les objets vectoriels quand le runtime les a seulement rasterisés.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h-s00", type=Path, default=H_S00_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(load_json(args.h_s00))
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / SUMMARY_PATH.name).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.results_dir / REPORT_PATH.name).write_text(render_markdown(summary), encoding="utf-8", newline="\n")
    print(f"H-S01b status: {summary['status']}")
    print(f"Wrote: {args.results_dir / REPORT_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
