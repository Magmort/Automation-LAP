#!/usr/bin/env python3
"""Run H-S02: read simulation features from a runtime track editor .sav."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
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
SUMMARY_PATH = RESULTS_DIR / "h_s02_runtime_sav_reader.json"
REPORT_PATH = RESULTS_DIR / "H_S02_RUNTIME_SAV_READER_RESULT.md"

STRING_RE = re.compile(rb"[\x20-\x7e]{4,}")
RUNTIME_IMAGE_FILES = ("track.png", "track_preview.png", "grass.png", "gravel.png", "minimap.png")
RELEVANT_EDITOR_TOKENS = {
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
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_g_reader() -> Any:
    spec = importlib.util.spec_from_file_location("g_s02_raw_reader", G_READER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {G_READER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_track_dir_from_h_s00(path: Path) -> Path:
    h_s00 = load_json(path)
    if not h_s00.get("fixtures"):
        raise RuntimeError("H-S00 inventory does not contain any fixture")
    first = h_s00["fixtures"][0]
    return Path(first["sourcePath"])


def ascii_strings(data: bytes, limit: int = 64) -> list[dict[str, Any]]:
    strings = []
    for match in STRING_RE.finditer(data):
        value = match.group(0).decode("ascii", errors="ignore").strip("\x00")
        if not value:
            continue
        strings.append({"offset": match.start(), "hexOffset": f"0x{match.start():04x}", "value": value})
        if len(strings) >= limit:
            break
    return strings


def cleaned_track_info_strings(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    values: list[str] = []
    for item in ascii_strings(path.read_bytes(), 32):
        value = item["value"].strip("@? ")
        # Keep readable suffixes when binary float bytes bleed into the string.
        for marker in ("track:", "flag_", "Road Course", "medium", "soft", "clear"):
            if marker in value and value != marker:
                value = value[value.index(marker) :]
                break
        if "First_Track" in value:
            value = "First_Track"
        if value and value not in values:
            values.append(value)
    return values


def alpha_bbox(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        from PIL import Image
    except ImportError:
        return {"path": path.name, "status": "pillow-unavailable"}
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        bbox = alpha.getbbox()
        histogram = alpha.histogram()
        return {
            "path": path.name,
            "size": list(rgba.size),
            "mode": image.mode,
            "nonTransparentPixelCount": sum(histogram[1:]),
            "alphaBbox": list(bbox) if bbox is not None else None,
        }


def distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def is_closed(points: list[dict[str, Any]]) -> bool:
    return len(points) >= 3 and distance(points[0], points[-1]) <= 1e-4


def polyline_length(points: list[dict[str, Any]], close_if_closed: bool = False) -> float:
    if len(points) < 2:
        return 0.0
    length = sum(distance(a, b) for a, b in zip(points, points[1:]))
    if close_if_closed and not is_closed(points):
        length += distance(points[-1], points[0])
    return length


def signed_area(points: list[dict[str, Any]]) -> float:
    if len(points) < 3:
        return 0.0
    total = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        total += float(point["x"]) * float(next_point["y"]) - float(next_point["x"]) * float(point["y"])
    return total * 0.5


def point_bounds(points: list[dict[str, Any]]) -> dict[str, float] | None:
    if not points:
        return None
    xs = [float(point["x"]) for point in points]
    ys = [float(point["y"]) for point in points]
    return {
        "minX": min(xs),
        "maxX": max(xs),
        "minY": min(ys),
        "maxY": max(ys),
        "spanX": max(xs) - min(xs),
        "spanY": max(ys) - min(ys),
    }


def plausible_point_ratio(points: list[dict[str, Any]]) -> float:
    if not points:
        return 0.0
    plausible = 0
    for point in points:
        x = float(point["x"])
        y = float(point["y"])
        if math.isfinite(x) and math.isfinite(y) and 0.0 <= x <= 10000.0 and 0.0 <= y <= 10000.0:
            plausible += 1
    return plausible / len(points)


def normalized_token_value(value: str) -> str:
    return value.strip("@? \x00")


def relevant_editor_strings(strings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relevant = []
    for item in strings:
        value = normalized_token_value(item["value"])
        if value in RELEVANT_EDITOR_TOKENS:
            entry = dict(item)
            entry["value"] = value
            relevant.append(entry)
    return relevant


def previous_token(block: dict[str, Any], tokens: list[dict[str, Any]], max_distance: int = 320) -> dict[str, Any] | None:
    candidates = []
    for token in tokens:
        delta = int(block["offset"]) - int(token["offset"])
        if 0 <= delta <= max_distance:
            candidates.append((delta, token))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    token = dict(candidates[0][1])
    token["distanceToBlock"] = candidates[0][0]
    return token


def classify_block(block: dict[str, Any], token: dict[str, Any] | None) -> list[str]:
    tags = []
    points = block.get("points", [])
    closed = is_closed(points)
    plausible = plausible_point_ratio(points)
    area = abs(signed_area(points))
    length = polyline_length(points)
    token_value = token["value"] if token else None
    if closed:
        tags.append("closed-vector-trace")
    else:
        tags.append("open-vector-trace")
    if plausible >= 0.95:
        tags.append("coordinate-plausible")
    if block.get("vectorTraceCandidate") is not None:
        tags.append("handles-present")
    if token_value:
        tags.append(f"near-token:{token_value}")
    if closed and plausible >= 0.95 and area > 1000.0 and block.get("pointCount", 0) >= 4:
        tags.append("closed-shape-candidate")
    if not closed and plausible >= 0.95 and length > 100.0:
        tags.append("line-candidate")
    return tags


def summarize_blocks(parsed_sav: dict[str, Any]) -> list[dict[str, Any]]:
    tokens = relevant_editor_strings(parsed_sav.get("stringTokens", []))
    blocks = []
    for block in parsed_sav.get("lineLikeBlocks", []):
        points = block.get("points", [])
        token = previous_token(block, tokens)
        bounds = point_bounds(points)
        entry = {
            "offset": block["offset"],
            "hexOffset": block["hexOffset"],
            "endOffset": block["endOffset"],
            "endHexOffset": block["endHexOffset"],
            "pointCount": block["pointCount"],
            "arrayCount": block["arrayCount"],
            "closed": is_closed(points),
            "lengthEditorUnits": round(polyline_length(points), 6),
            "signedAreaEditorUnits2": round(signed_area(points), 6),
            "absAreaEditorUnits2": round(abs(signed_area(points)), 6),
            "plausiblePointRatio": round(plausible_point_ratio(points), 6),
            "bounds": bounds,
            "firstPoint": points[0] if points else None,
            "lastPoint": points[-1] if points else None,
            "nearbyToken": token,
            "tags": [],
            "points": points,
            "vectorTraceCandidate": block.get("vectorTraceCandidate"),
        }
        entry["tags"] = classify_block(entry, token)
        blocks.append(entry)
    return blocks


def token_counts(items: list[dict[str, Any]], key: str = "token") -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = item.get(key)
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def file_entry(path: Path | None, root: Path) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return {
        "path": path.relative_to(root).as_posix(),
        "sizeBytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def block_digest(block: dict[str, Any], role: str, confidence: str, reason: str) -> dict[str, Any]:
    return {
        "role": role,
        "confidence": confidence,
        "reason": reason,
        "offset": block["offset"],
        "hexOffset": block["hexOffset"],
        "pointCount": block["pointCount"],
        "closed": block["closed"],
        "lengthEditorUnits": block["lengthEditorUnits"],
        "absAreaEditorUnits2": block["absAreaEditorUnits2"],
        "bounds": block["bounds"],
        "firstPoint": block["firstPoint"],
        "lastPoint": block["lastPoint"],
        "nearbyToken": block.get("nearbyToken"),
        "tags": block["tags"],
        "points": block["points"],
        "vectorTraceCandidate": block.get("vectorTraceCandidate"),
    }


def block_by_offset(blocks: list[dict[str, Any]], offset: int) -> dict[str, Any] | None:
    return next((block for block in blocks if int(block["offset"]) == int(offset)), None)


def token_offsets(tokens: list[dict[str, Any]], value: str) -> list[int]:
    return [int(token["offset"]) for token in tokens if token.get("value") == value]


def blocks_after_offsets(
    blocks: list[dict[str, Any]],
    offsets: list[int],
    max_distance: int,
    *,
    require_open: bool | None = None,
) -> list[dict[str, Any]]:
    selected = []
    seen = set()
    for offset in offsets:
        for block in blocks:
            delta = int(block["offset"]) - offset
            if not (0 <= delta <= max_distance):
                continue
            if require_open is True and block["closed"]:
                continue
            if require_open is False and not block["closed"]:
                continue
            if block["offset"] in seen:
                continue
            if block["plausiblePointRatio"] < 0.95 or block["lengthEditorUnits"] <= 10.0:
                continue
            seen.add(block["offset"])
            selected.append(block)
    return sorted(selected, key=lambda block: block["offset"])


def select_track_block(parsed_sav: dict[str, Any], blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    primary = parsed_sav.get("vectorTraceCandidates", {}).get("primaryRoad")
    if primary is not None:
        block = block_by_offset(blocks, int(primary["offset"]))
        if block is not None:
            return block

    # Fallback for single-track saves where the counted-array region is not at
    # the minimal fixture offset: use the first large closed vector after the
    # road/grass header and before explicit object tokens.
    closed_blocks = [
        block
        for block in blocks
        if block["closed"]
        and block["plausiblePointRatio"] >= 0.95
        and block["pointCount"] >= 4
        and block["absAreaEditorUnits2"] > 1000.0
    ]
    if not closed_blocks:
        return None
    return sorted(closed_blocks, key=lambda block: block["offset"])[0]


def build_simulation_features(parsed_sav: dict[str, Any], blocks: list[dict[str, Any]], tokens: list[dict[str, Any]]) -> dict[str, Any]:
    track_block = select_track_block(parsed_sav, blocks)
    wall_blocks = blocks_after_offsets(blocks, token_offsets(tokens, "wall1"), 512)
    pitlane_blocks = blocks_after_offsets(
        blocks,
        token_offsets(tokens, "spr_pit_building_to_right"),
        768,
        require_open=True,
    )

    pitlane_lanes = []
    for index, block in enumerate(pitlane_blocks[:2]):
        role = "pitlane-entry" if index == 0 else "pitlane-exit"
        pitlane_lanes.append(
            block_digest(
                block,
                role,
                "medium",
                "Open vector block following spr_pit_building_to_right; role assigned by order in the .sav.",
            )
        )

    return {
        "track": block_digest(
            track_block,
            "main-track",
            "high" if parsed_sav.get("vectorTraceCandidates", {}).get("primaryRoad") else "medium",
            "Primary road vector trace from the .sav counted-array region."
            if parsed_sav.get("vectorTraceCandidates", {}).get("primaryRoad")
            else "Fallback: first large closed plausible vector trace in the .sav.",
        )
        if track_block
        else None,
        "pitlaneLanes": pitlane_lanes,
        "walls": [
            block_digest(
                block,
                "wall",
                "high",
                "Vector block located after a wall1 token.",
            )
            for block in wall_blocks
        ],
        "checkpoints": parsed_sav.get("checkpointCandidates", []),
        "status": {
            "trackFound": track_block is not None,
            "pitlaneLaneCount": len(pitlane_lanes),
            "wallCount": len(wall_blocks),
            "checkpointCount": len(parsed_sav.get("checkpointCandidates", [])),
        },
    }


def build_runtime_data(track_dir: Path) -> dict[str, Any]:
    track_dir = track_dir.resolve()
    if not track_dir.is_dir():
        raise RuntimeError(f"Track directory does not exist: {track_dir}")
    editor_path = track_dir / "track_editor.sav"
    if not editor_path.exists():
        raise RuntimeError(f"Missing track_editor.sav in {track_dir}")
    info_path = track_dir / "track_info.data"

    g_reader = load_g_reader()
    parsed_sav = g_reader.parse_fixture(
        {
            "fixture": track_dir.name,
            "path": editor_path,
            "data": editor_path.read_bytes(),
        }
    )
    vector_blocks = summarize_blocks(parsed_sav)
    relevant_tokens = relevant_editor_strings(parsed_sav.get("stringTokens", []))
    simulation_features = build_simulation_features(parsed_sav, vector_blocks, relevant_tokens)
    image_layers = {name: alpha_bbox(track_dir / name) for name in RUNTIME_IMAGE_FILES}

    object_candidates = parsed_sav.get("namedObjectCandidates", [])
    checkpoints = parsed_sav.get("checkpointCandidates", [])
    counts = {
        "vectorBlocks": len(vector_blocks),
        "closedVectorBlocks": sum(1 for block in vector_blocks if block["closed"]),
        "openVectorBlocks": sum(1 for block in vector_blocks if not block["closed"]),
        "checkpoints": len(checkpoints),
        "objectCandidates": len(object_candidates),
        "relevantEditorTokens": len(relevant_tokens),
        "imageLayersPresent": sum(1 for item in image_layers.values() if item is not None),
    }
    feature_status = simulation_features["status"]
    status = (
        "ready-for-h03-route-and-overlay"
        if feature_status["trackFound"]
        and feature_status["pitlaneLaneCount"] >= 2
        and feature_status["wallCount"] >= 1
        and feature_status["checkpointCount"] > 0
        else "parsed-with-missing-functional-data"
    )
    return {
        "kind": "UR2D2RuntimeTrackData",
        "schemaVersion": "0.1.0",
        "scenario": "H-S02",
        "status": status,
        "generatedAtUtc": utc_now(),
        "trackDirectory": str(track_dir),
        "sourceFiles": {
            "trackEditorSav": file_entry(editor_path, track_dir),
            "trackInfoData": file_entry(info_path if info_path.exists() else None, track_dir),
            "imageLayers": {name: file_entry(track_dir / name if (track_dir / name).exists() else None, track_dir) for name in RUNTIME_IMAGE_FILES},
        },
        "trackInfo": {
            "path": "track_info.data" if info_path.exists() else None,
            "strings": cleaned_track_info_strings(info_path if info_path.exists() else None),
            "status": "present" if info_path.exists() else "missing",
        },
        "imageLayers": image_layers,
        "editorSav": {
            "path": "track_editor.sav",
            "sourceSha256": parsed_sav["sourceSha256"],
            "sizeBytes": parsed_sav["sizeBytes"],
            "globalCandidates": parsed_sav["globalCandidates"],
            "countedFloatArrayRegion": parsed_sav["countedFloatArrayRegion"],
            "countedFloatArrayCount": len(parsed_sav.get("countedFloatArrays", [])),
            "stringTokens": relevant_tokens,
            "stringTokenCounts": token_counts(relevant_tokens, "value"),
            "checkpointCandidates": checkpoints,
            "namedObjectCandidates": object_candidates,
            "namedObjectTokenCounts": token_counts(object_candidates, "token"),
            "vectorBlocks": vector_blocks,
        },
        "simulationFeatures": simulation_features,
        "counts": counts,
        "guarantees": [
            "All offsets are byte offsets in the source track_editor.sav.",
            "Simulation features are read from track_editor.sav, not from track.data.",
            "The main track, pitlane lanes and walls are exposed as explicit feature candidates.",
            "track_info.data strings are cleaned as metadata hints only.",
            "PNG layers are treated as runtime background/raster evidence, not regenerated vector geometry.",
        ],
        "nonGuarantees": [
            "H-S02 does not convert editor units to metres.",
            "H-S02 does not align .sav coordinates to image pixels yet.",
            "Object payload schemas remain provisional.",
        ],
    }


def top_blocks(blocks: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    return sorted(
        blocks,
        key=lambda block: (
            block["plausiblePointRatio"],
            block["closed"],
            block["absAreaEditorUnits2"],
            block["lengthEditorUnits"],
        ),
        reverse=True,
    )[:limit]


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# H-S02 - Lecteur brut runtime .sav",
        "",
        "- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2",
        "- **Scénario :** H-S02",
        f"- **Statut :** {data['status']}",
        f"- **Date :** {data['generatedAtUtc']}",
        f"- **Dossier piste :** `{data['trackDirectory']}`",
        "- **Sortie brute :** `UR2D2RuntimeTrackData` v0.1.0",
        "",
        "## Décision du jalon",
        "",
    ]
    if data["status"] == "ready-for-h03-route-and-overlay":
        lines.append("H-S02 est exploitable : le `.sav` fournit explicitement les candidats de simulation utiles, à savoir la piste principale, les voies de pitlane, les murs et les checkpoints.")
    else:
        lines.append("H-S02 lit le `.sav`, mais au moins un élément fonctionnel minimal manque parmi piste, pitlane, murs ou checkpoints.")

    lines.extend(
        [
            "",
            "## Fichiers source",
            "",
            "| Fichier | Taille | SHA-256 court |",
            "| --- | ---: | --- |",
        ]
    )
    for key in ("trackEditorSav", "trackInfoData"):
        entry = data["sourceFiles"].get(key)
        if entry:
            lines.append(f"| `{entry['path']}` | {entry['sizeBytes']} | `{entry['sha256'][:12]}` |")
    for name, entry in data["sourceFiles"]["imageLayers"].items():
        if entry:
            lines.append(f"| `{entry['path']}` | {entry['sizeBytes']} | `{entry['sha256'][:12]}` |")

    lines.extend(
        [
            "",
            "## Synthèse",
            "",
            "| Mesure | Valeur |",
            "| --- | ---: |",
        ]
    )
    for key, value in data["counts"].items():
        lines.append(f"| `{key}` | {value} |")

    features = data["simulationFeatures"]
    lines.extend(
        [
            "",
            "## Éléments de simulation retenus",
            "",
            "| Élément | Statut | Offset | Points | Confiance | Raison |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    track = features.get("track")
    if track:
        lines.append(
            f"| Piste principale | trouvé | `{track['hexOffset']}` | {track['pointCount']} | {track['confidence']} | {track['reason']} |"
        )
    else:
        lines.append("| Piste principale | manquant | - | - | - | - |")
    for lane in features.get("pitlaneLanes", []):
        lines.append(
            f"| {lane['role']} | trouvé | `{lane['hexOffset']}` | {lane['pointCount']} | {lane['confidence']} | {lane['reason']} |"
        )
    for wall in features.get("walls", []):
        lines.append(
            f"| Mur | trouvé | `{wall['hexOffset']}` | {wall['pointCount']} | {wall['confidence']} | {wall['reason']} |"
        )

    lines.extend(["", "## Métadonnées track_info.data", ""])
    if data["trackInfo"]["strings"]:
        lines.extend(f"- `{value}`" for value in data["trackInfo"]["strings"])
    else:
        lines.append("- Aucune chaîne exploitable.")

    lines.extend(
        [
            "",
            "## Checkpoints",
            "",
            "| Label | X | Y | Rotation | Payload |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for checkpoint in data["editorSav"]["checkpointCandidates"]:
        lines.append(
            f"| {checkpoint.get('label') or '-'} | {checkpoint['x']:.3f} | {checkpoint['y']:.3f} | "
            f"{checkpoint['rotationDeg']:.3f} | `{checkpoint['payloadHexOffset']}` |"
        )

    lines.extend(
        [
            "",
            "## Tokens objets",
            "",
            "| Token | Count |",
            "| --- | ---: |",
        ]
    )
    for token, count in data["editorSav"]["namedObjectTokenCounts"].items():
        lines.append(f"| `{token}` | {count} |")

    lines.extend(
        [
            "",
            "## Blocs vectoriels bruts conservés",
            "",
            "| Offset | Points | Fermé | Longueur | Aire abs. | Token proche | Tags |",
            "| --- | ---: | --- | ---: | ---: | --- | --- |",
        ]
    )
    for block in top_blocks(data["editorSav"]["vectorBlocks"]):
        token = block.get("nearbyToken", {}).get("value") if block.get("nearbyToken") else "-"
        tags = ", ".join(block["tags"][:4])
        lines.append(
            f"| `{block['hexOffset']}` | {block['pointCount']} | {'oui' if block['closed'] else 'non'} | "
            f"{block['lengthEditorUnits']:.3f} | {block['absAreaEditorUnits2']:.3f} | {token} | {tags} |"
        )

    lines.extend(
        [
            "",
            "## Calques PNG",
            "",
            "| Fichier | Taille image | Pixels alpha | BBox alpha |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for name, layer in data["imageLayers"].items():
        if layer is None:
            lines.append(f"| `{name}` | - | - | - |")
        elif layer.get("status") == "pillow-unavailable":
            lines.append(f"| `{name}` | Pillow indisponible | - | - |")
        else:
            lines.append(f"| `{name}` | {layer['size']} | {layer['nonTransparentPixelCount']} | {layer['alphaBbox']} |")

    lines.extend(["", "## Garanties", ""])
    lines.extend(f"- {item}" for item in data["guarantees"])
    lines.extend(["", "Limites explicites :", ""])
    lines.extend(f"- {item}" for item in data["nonGuarantees"])
    lines.extend(
        [
            "",
            "## Prochaine étape",
            "",
            "H-S03 peut maintenant convertir la piste principale, les voies de pitlane et les murs vers le repère de simulation, puis H-S04 les superposera au fond PNG runtime.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track-dir", type=Path, default=None, help="Runtime track directory containing track_editor.sav.")
    parser.add_argument("--h-s00", type=Path, default=H_S00_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    track_dir = args.track_dir or default_track_dir_from_h_s00(args.h_s00)
    data = build_runtime_data(track_dir)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / SUMMARY_PATH.name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.results_dir / REPORT_PATH.name).write_text(render_markdown(data), encoding="utf-8", newline="\n")
    print(f"H-S02 status: {data['status']}")
    print(f"Wrote: {args.results_dir / REPORT_PATH.name}")
    return 0 if data["status"] == "ready-for-h03-route-and-overlay" else 1


if __name__ == "__main__":
    raise SystemExit(main())
