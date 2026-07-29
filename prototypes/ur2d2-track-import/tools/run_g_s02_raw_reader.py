#!/usr/bin/env python3
"""Build a provisional UR2D2RawTrackData payload from editor .sav fixtures."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES_ROOT = ROOT / "fixtures" / "source"
DEFAULT_RESULTS_DIR = ROOT / "results"

EXPECTED_FILES = [
    ("T00_empty_save", ["T00_empty_save.sav"]),
    ("T01_single_straight", ["T01_single_straight.sav"]),
    ("T02_simple_closed_loop", ["T02_simple_closed_loop.sav"]),
    ("T03_ai_line", ["T03_ai_line.sav"]),
    ("T04_limits_or_walls", ["T04_limits_or_walls.sav", "T04_limit_or_walls.sav"]),
    ("T05_start_and_checkpoints", ["T05_start_and_checkpoints.sav"]),
    ("T06_pit_lane", ["T06_pit_lane.sav"]),
    ("T07_surfaces", ["T07_surfaces.sav"]),
]

STRING_RE = re.compile(rb"[\x20-\x7e]{4,}")
COUNTED_ARRAY_START = 0x004D


ARRAY_HYPOTHESES = {
    0: ("road_control_x", "high", "Route control point X coordinates in editor units."),
    1: ("road_control_y", "high", "Route control point Y coordinates in editor units."),
    2: ("road_node_flags_or_types", "low", "Small per-node values; exact meaning unknown."),
    3: ("road_angle_a_deg", "medium", "Per-node angle-like values in degrees."),
    4: ("road_angle_b_deg", "medium", "Second per-node angle-like values in degrees."),
    5: ("road_handle_weight_a", "medium", "Values around 128-130; likely vector key handle weight A."),
    6: ("road_handle_weight_b", "medium", "Values around 128-130; likely vector key handle weight B."),
    7: ("generated_edge_or_mesh_x", "medium", "Generated X samples around the road envelope."),
    8: ("generated_edge_or_mesh_y", "medium", "Generated Y samples around the road envelope."),
    13: ("sampled_line_x", "medium", "Dense X samples; may be generated road/AI/reference line."),
    14: ("sampled_line_y", "medium", "Dense Y samples paired with sampled_line_x."),
    15: ("sampled_line_angle_deg", "low", "Dense angle-like values paired with sampled_line_x/y."),
    16: ("unknown_scalar_block", "low", "Trailing one-value counted block."),
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def is_plausible_count(value: float) -> bool:
    return math.isfinite(value) and abs(value - round(value)) < 1e-5 and 0 <= value <= 512


def load_fixture_files(root: Path) -> list[dict[str, Any]]:
    fixtures = []
    for fixture_id, aliases in EXPECTED_FILES:
        path = next((root / alias for alias in aliases if (root / alias).is_file()), None)
        if path is not None:
            data = path.read_bytes()
            fixtures.append({"fixture": fixture_id, "path": path, "data": data})
    return fixtures


def extract_strings(data: bytes) -> list[dict[str, Any]]:
    return [
        {"offset": match.start(), "hexOffset": f"0x{match.start():04x}", "value": match.group(0).decode("ascii", "ignore")}
        for match in STRING_RE.finditer(data)
    ]


def read_counted_float_arrays(data: bytes, start: int = COUNTED_ARRAY_START) -> tuple[list[dict[str, Any]], int]:
    arrays = []
    offset = start
    index = 0
    while offset + 4 <= len(data):
        count_value = read_f32(data, offset)
        if not is_plausible_count(count_value):
            break
        count = int(round(count_value))
        values_offset = offset + 4
        end = values_offset + count * 4
        if end > len(data):
            break
        values = [read_f32(data, values_offset + i * 4) for i in range(count)]
        if any(not math.isfinite(value) or abs(value) > 100000 for value in values):
            break
        name, confidence, reason = ARRAY_HYPOTHESES.get(
            index, (f"unknown_counted_float_array_{index:02d}", "low", "No stable semantic label yet.")
        )
        arrays.append(
            {
                "index": index,
                "name": name,
                "confidence": confidence,
                "reason": reason,
                "offset": offset,
                "hexOffset": f"0x{offset:04x}",
                "count": count,
                "values": [round(value, 6) for value in values],
            }
        )
        offset = end
        index += 1
    return arrays, offset


def pair_points(x_values: list[float], y_values: list[float]) -> list[dict[str, float]]:
    return [
        {"x": round(float(x), 6), "y": round(float(y), 6)}
        for x, y in zip(x_values, y_values)
    ]


def build_vector_trace_candidate(
    arrays: list[dict[str, Any]],
    label: str,
    confidence: str,
    reason: str,
) -> dict[str, Any] | None:
    if len(arrays) < 7:
        return None
    key_count = arrays[0]["count"]
    if key_count < 2:
        return None
    if any(array["count"] != key_count for array in arrays[:7]):
        return None

    keys = []
    for index in range(key_count):
        keys.append(
            {
                "index": index,
                "x": arrays[0]["values"][index],
                "y": arrays[1]["values"][index],
                "typeOrFlag": arrays[2]["values"][index],
                "angleADeg": arrays[3]["values"][index],
                "angleBDeg": arrays[4]["values"][index],
                "weightA": arrays[5]["values"][index],
                "weightB": arrays[6]["values"][index],
            }
        )

    return {
        "label": label,
        "offset": arrays[0]["offset"],
        "hexOffset": arrays[0]["hexOffset"],
        "keyCount": key_count,
        "confidence": confidence,
        "reason": reason,
        "keys": keys,
    }


def read_counted_arrays_at(data: bytes, start: int, max_arrays: int = 12) -> tuple[list[dict[str, Any]], int]:
    arrays = []
    offset = start
    for index in range(max_arrays):
        if offset + 4 > len(data):
            break
        count_value = read_f32(data, offset)
        if not is_plausible_count(count_value):
            break
        count = int(round(count_value))
        values_offset = offset + 4
        end = values_offset + count * 4
        if end > len(data):
            break
        values = [read_f32(data, values_offset + i * 4) for i in range(count)]
        if any(not math.isfinite(value) or abs(value) > 100000 for value in values):
            break
        arrays.append(
            {
                "index": index,
                "offset": offset,
                "hexOffset": f"0x{offset:04x}",
                "count": count,
                "values": [round(value, 6) for value in values],
            }
        )
        offset = end
    return arrays, offset


def extract_line_like_blocks(data: bytes) -> list[dict[str, Any]]:
    blocks = []
    for start in range(0, max(0, len(data) - 16)):
        arrays, end = read_counted_arrays_at(data, start, max_arrays=8)
        if len(arrays) < 2:
            continue
        if arrays[0]["count"] != arrays[1]["count"] or arrays[0]["count"] < 2:
            continue
        xs = arrays[0]["values"]
        ys = arrays[1]["values"]
        if not all(0 <= value <= 5000 for value in xs + ys):
            continue
        blocks.append(
            {
                "offset": start,
                "hexOffset": f"0x{start:04x}",
                "endOffset": end,
                "endHexOffset": f"0x{end:04x}",
                "pointCount": arrays[0]["count"],
                "arrayCount": len(arrays),
                "points": pair_points(xs, ys),
                "arrays": arrays,
                "vectorTraceCandidate": build_vector_trace_candidate(
                    arrays,
                    "line_like_vector_trace",
                    "medium",
                    "Line-like counted arrays expose x/y, flags, angle A/B and weight A/B candidates.",
                ),
            }
        )

    # Keep a non-overlapping readable list. Later classifications can still
    # search this list by token proximity.
    selected = []
    last_end = -1
    for block in sorted(blocks, key=lambda item: (item["offset"], -item["pointCount"])):
        if block["offset"] >= last_end:
            selected.append(block)
            last_end = block["endOffset"]
    return selected


def exact_string_offsets(data: bytes, token: bytes) -> list[int]:
    offsets = []
    start = 0
    while True:
        found = data.find(token, start)
        if found < 0:
            return offsets
        offsets.append(found)
        start = found + 1


def following_floats(data: bytes, offset: int, count: int) -> list[float] | None:
    if offset + count * 4 > len(data):
        return None
    values = [read_f32(data, offset + i * 4) for i in range(count)]
    if any(not math.isfinite(value) or abs(value) > 100000 for value in values):
        return None
    return values


def best_payload_after_token(data: bytes, token_offset: int, token_length: int) -> tuple[int, list[float]] | None:
    token_end = token_offset + token_length
    for candidate in range(token_end + 1, min(token_end + 9, len(data) - 24)):
        values = following_floats(data, candidate, 6)
        if values is None:
            continue
        x, y, layer_or_scale, rotation, width, height = values
        if 0 <= x <= 5000 and 0 <= y <= 5000 and -5 <= layer_or_scale <= 5 and -720 <= rotation <= 720:
            if 0 <= width <= 1000 and 0 <= height <= 1000:
                return candidate, values
    return None


def nearest_label_after(data: bytes, search_start: int, search_end: int) -> str | None:
    labels = []
    for match in STRING_RE.finditer(data, search_start, min(search_end, len(data))):
        value = match.group(0).decode("ascii", "ignore").strip("@? ")
        if value and not value.startswith("spr_"):
            labels.append(value)
    return labels[0] if labels else None


def extract_checkpoint_candidates(data: bytes) -> list[dict[str, Any]]:
    checkpoints = []
    token = b"spr_checkpoint"
    for token_offset in exact_string_offsets(data, token):
        payload = best_payload_after_token(data, token_offset, len(token))
        if payload is None:
            continue
        payload_offset, values = payload
        label = nearest_label_after(data, payload_offset + 24, payload_offset + 96)
        checkpoints.append(
            {
                "spriteOffset": token_offset,
                "spriteHexOffset": f"0x{token_offset:04x}",
                "payloadOffset": payload_offset,
                "payloadHexOffset": f"0x{payload_offset:04x}",
                "label": label,
                "x": round(values[0], 6),
                "y": round(values[1], 6),
                "layerOrScale": round(values[2], 6),
                "rotationDeg": round(values[3], 6),
                "widthCandidate": round(values[4], 6),
                "heightCandidate": round(values[5], 6),
                "confidence": "medium",
                "reason": "Exact spr_checkpoint token followed by plausible x/y/rotation/size payload and a nearby label.",
            }
        )
    return checkpoints


def extract_named_object_candidates(data: bytes) -> list[dict[str, Any]]:
    tokens = [b"wall1", b"spr_pit_building_to_right", b"forrest2", b"spr_water_edge", b"spr_sand", b"spr_sand_edge"]
    objects = []
    for token in tokens:
        for token_offset in exact_string_offsets(data, token):
            payload = best_payload_after_token(data, token_offset, len(token))
            item: dict[str, Any] = {
                "token": token.decode("ascii"),
                "tokenOffset": token_offset,
                "tokenHexOffset": f"0x{token_offset:04x}",
                "confidence": "low",
                "reason": "Known object/surface token; payload layout still uncertain.",
            }
            if payload is not None:
                payload_offset, values = payload
                item.update(
                    {
                        "payloadOffset": payload_offset,
                        "payloadHexOffset": f"0x{payload_offset:04x}",
                        "x": round(values[0], 6),
                        "y": round(values[1], 6),
                        "rotationDeg": round(values[3], 6),
                        "widthCandidate": round(values[4], 6),
                        "heightCandidate": round(values[5], 6),
                    }
                )
            objects.append(item)
    return objects


def find_nearest_line_block_after(blocks: list[dict[str, Any]], offset: int, max_distance: int) -> dict[str, Any] | None:
    candidates = [block for block in blocks if 0 <= block["offset"] - offset <= max_distance]
    return candidates[0] if candidates else None


def find_next_line_blocks_after(blocks: list[dict[str, Any]], offset: int, count: int, max_distance: int) -> list[dict[str, Any]]:
    candidates = [block for block in blocks if 0 <= block["offset"] - offset <= max_distance]
    return candidates[:count]


def token_offsets(data: bytes, token: str) -> list[int]:
    return exact_string_offsets(data, token.encode("ascii"))


def summarize_array_pairs(arrays: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {array["name"]: array for array in arrays}
    summary: dict[str, Any] = {}
    if "road_control_x" in by_name and "road_control_y" in by_name:
        summary["roadControlPoints"] = pair_points(by_name["road_control_x"]["values"], by_name["road_control_y"]["values"])
    if "generated_edge_or_mesh_x" in by_name and "generated_edge_or_mesh_y" in by_name:
        summary["generatedEdgeOrMeshPoints"] = pair_points(
            by_name["generated_edge_or_mesh_x"]["values"], by_name["generated_edge_or_mesh_y"]["values"]
        )
    if "sampled_line_x" in by_name and "sampled_line_y" in by_name:
        summary["sampledLinePoints"] = pair_points(by_name["sampled_line_x"]["values"], by_name["sampled_line_y"]["values"])
    return summary


def primary_vector_trace(arrays: list[dict[str, Any]]) -> dict[str, Any] | None:
    return build_vector_trace_candidate(
        arrays,
        "primary_road_vector_trace",
        "medium",
        "Primary route arrays expose x/y plus angle and weight candidates. The exact interpolation formula is not validated yet.",
    )


def parse_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    data = fixture["data"]
    arrays, arrays_end = read_counted_float_arrays(data)
    strings = extract_strings(data)
    line_blocks = extract_line_like_blocks(data)
    global_width_or_scale = read_f32(data, 0) if len(data) >= 4 else None
    return {
        "fixture": fixture["fixture"],
        "sourcePath": str(fixture["path"]),
        "sourceSha256": sha256_bytes(data),
        "sizeBytes": len(data),
        "format": {
            "kind": "UR2D2RawTrackData",
            "source": "Track Editor .sav",
            "readerVersion": "0.1.0",
            "endiannessHypothesis": "little-endian",
        },
        "globalCandidates": {
            "float32At0": round(global_width_or_scale, 6) if global_width_or_scale is not None else None,
            "float32At0Hypothesis": "global width, scale or editor parameter; value is 10.0 in all fixtures.",
        },
        "countedFloatArrays": arrays,
        "countedFloatArrayRegion": {
            "startOffset": COUNTED_ARRAY_START,
            "startHexOffset": f"0x{COUNTED_ARRAY_START:04x}",
            "endOffset": arrays_end,
            "endHexOffset": f"0x{arrays_end:04x}",
            "arrayCount": len(arrays),
        },
        "pairedGeometryCandidates": summarize_array_pairs(arrays),
        "vectorTraceCandidates": {
            "primaryRoad": primary_vector_trace(arrays),
            "lineLikeBlocks": [
                block["vectorTraceCandidate"]
                for block in line_blocks
                if block.get("vectorTraceCandidate") is not None and block["offset"] != COUNTED_ARRAY_START
            ],
        },
        "stringTokens": strings,
        "lineLikeBlocks": line_blocks,
        "checkpointCandidates": extract_checkpoint_candidates(data),
        "namedObjectCandidates": extract_named_object_candidates(data),
        "unknownRegions": [
            {
                "startOffset": arrays_end,
                "startHexOffset": f"0x{arrays_end:04x}",
                "endOffset": len(data),
                "endHexOffset": f"0x{len(data):04x}",
                "reason": "Bytes after the stable counted-float region contain object records, generated samples and unknown payloads.",
            }
        ],
    }


def fixture_by_id(parsed: list[dict[str, Any]], fixture_id: str) -> dict[str, Any] | None:
    return next((fixture for fixture in parsed if fixture["fixture"] == fixture_id), None)


def matching_ai_blocks(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    road = fixture.get("pairedGeometryCandidates", {}).get("roadControlPoints", [])
    road_xs = [point["x"] for point in road]
    region_end = fixture["countedFloatArrayRegion"]["endOffset"]
    blocks = []
    for block in fixture.get("lineLikeBlocks", []):
        if block["offset"] <= region_end:
            continue
        xs = [point["x"] for point in block["points"]]
        if len(xs) == len(road_xs) and all(abs(a - b) < 0.001 for a, b in zip(xs, road_xs)):
            item = dict(block)
            item["confidence"] = "medium"
            item["reason"] = "Vector-like line block added by T03 with the same X control points as the route and shifted Y values."
            blocks.append(item)
    return blocks[:3]


def build_element_inventory(parsed: list[dict[str, Any]]) -> dict[str, Any]:
    t03 = fixture_by_id(parsed, "T03_ai_line")
    t04 = fixture_by_id(parsed, "T04_limits_or_walls")
    t05 = fixture_by_id(parsed, "T05_start_and_checkpoints")
    t06 = fixture_by_id(parsed, "T06_pit_lane")
    t07 = fixture_by_id(parsed, "T07_surfaces")
    route_fixture = fixture_by_id(parsed, "T02_simple_closed_loop") or t05

    route_points = route_fixture.get("pairedGeometryCandidates", {}).get("roadControlPoints", []) if route_fixture else []
    route_segment_count = max(0, len(route_points) - 1) if route_points else 0
    ai_blocks = matching_ai_blocks(t03) if t03 else []
    checkpoint_count = len(t05.get("checkpointCandidates", [])) if t05 else 0

    wall_block = None
    if t04:
        offsets = token_offsets(Path(t04["sourcePath"]).read_bytes(), "wall1")
        if offsets:
            wall_block = find_nearest_line_block_after(t04["lineLikeBlocks"], offsets[0], 64)

    pit_blocks: list[dict[str, Any]] = []
    if t06:
        data = Path(t06["sourcePath"]).read_bytes()
        offsets = token_offsets(data, "spr_pit_building_to_right")
        if offsets:
            pit_blocks = find_next_line_blocks_after(t06["lineLikeBlocks"], offsets[0], 2, 768)

    tree_block = None
    sand_block = None
    if t07:
        data = Path(t07["sourcePath"]).read_bytes()
        tree_offsets = token_offsets(data, "forrest2")
        if tree_offsets:
            tree_block = find_nearest_line_block_after(t07["lineLikeBlocks"], tree_offsets[0], 128)
        sand_offsets = token_offsets(data, "spr_sand")
        if sand_offsets:
            sand_block = find_nearest_line_block_after(t07["lineLikeBlocks"], sand_offsets[0], 128)

    pit_entry = pit_blocks[0] if len(pit_blocks) >= 1 else None
    pit_exit = pit_blocks[1] if len(pit_blocks) >= 2 else None
    pitlane_detected = bool(t06 and token_offsets(Path(t06["sourcePath"]).read_bytes(), "spr_pit_building_to_right"))

    items = [
        {
            "id": "road_segments",
            "label": "Segments de route",
            "expected": 4,
            "detected": route_segment_count,
            "status": "read" if route_segment_count == 4 else "mismatch",
            "confidence": "high",
            "fixture": route_fixture["fixture"] if route_fixture else None,
            "evidence": f"{len(route_points)} control points, last point duplicates the first point." if route_points else "No route points read.",
        },
        {
            "id": "ai_lines",
            "label": "Lignes IA",
            "expected": 3,
            "detected": len(ai_blocks),
            "status": "read" if len(ai_blocks) == 3 else "mismatch",
            "confidence": "medium",
            "fixture": t03["fixture"] if t03 else None,
            "evidence": "Three line-like blocks added by T03 after the primary route block." if ai_blocks else "No AI line blocks classified.",
            "blocks": [{"hexOffset": block["hexOffset"], "pointCount": block["pointCount"]} for block in ai_blocks],
        },
        {
            "id": "checkpoints",
            "label": "Checkpoints",
            "expected": 3,
            "detected": checkpoint_count,
            "status": "read" if checkpoint_count == 3 else "mismatch",
            "confidence": "medium",
            "fixture": t05["fixture"] if t05 else None,
            "evidence": "spr_checkpoint payloads with labels Checkpoint 2, Checkpoint 1 and Finish." if checkpoint_count else "No checkpoint payloads read.",
        },
        {
            "id": "pitlane",
            "label": "Pitlane",
            "expected": 1,
            "detected": 1 if pitlane_detected else 0,
            "status": "detected" if pitlane_detected else "missing",
            "confidence": "low",
            "fixture": t06["fixture"] if t06 else None,
            "evidence": "spr_pit_building_to_right token plus pit connector line-like blocks; exact pitlane schema still provisional.",
        },
        {
            "id": "pitlane_entry",
            "label": "Entrée de pitlane",
            "expected": 1,
            "detected": 1 if pit_entry else 0,
            "status": "candidate" if pit_entry else "missing",
            "confidence": "low",
            "fixture": t06["fixture"] if t06 else None,
            "evidence": f"First pit connector line-like block at {pit_entry['hexOffset']} with {pit_entry['pointCount']} points." if pit_entry else "No pit entry candidate.",
        },
        {
            "id": "pitlane_exit",
            "label": "Sortie de pitlane",
            "expected": 1,
            "detected": 1 if pit_exit else 0,
            "status": "candidate" if pit_exit else "missing",
            "confidence": "low",
            "fixture": t06["fixture"] if t06 else None,
            "evidence": f"Second pit connector line-like block at {pit_exit['hexOffset']} with {pit_exit['pointCount']} points." if pit_exit else "No pit exit candidate.",
        },
        {
            "id": "wall",
            "label": "Mur en plusieurs segments",
            "expected": 1,
            "detected": 1 if wall_block else 0,
            "status": "read" if wall_block else "missing",
            "confidence": "medium",
            "fixture": t04["fixture"] if t04 else None,
            "evidence": f"wall1 token followed by a {wall_block['pointCount']}-point line-like block." if wall_block else "No wall geometry block classified.",
        },
        {
            "id": "sand_zone",
            "label": "Zone de sable (polygone)",
            "expected": 1,
            "detected": 1 if sand_block else 0,
            "status": "read" if sand_block else "missing",
            "confidence": "medium",
            "fixture": t07["fixture"] if t07 else None,
            "evidence": f"spr_sand token followed by a {sand_block['pointCount']}-point polygon-like block." if sand_block else "No sand polygon classified.",
        },
        {
            "id": "tree_zone",
            "label": "Zone d'arbres (polygone)",
            "expected": 1,
            "detected": 1 if tree_block else 0,
            "status": "read" if tree_block else "missing",
            "confidence": "medium",
            "fixture": t07["fixture"] if t07 else None,
            "evidence": f"forrest2 token followed by an {tree_block['pointCount']}-point polygon-like block." if tree_block else "No tree polygon classified.",
        },
    ]
    return {
        "status": "complete-with-low-confidence-pitlane-role-assignment"
        if all(item["detected"] == item["expected"] for item in items)
        else "incomplete",
        "items": items,
        "notes": [
            "read = geometry payload is extracted as counted float arrays.",
            "detected = element token is present but full schema is not yet understood.",
            "candidate = geometry exists, but role assignment still needs confirmation in the editor/game.",
            "Pitlane entry and exit are assigned by order of the two connector-like blocks after spr_pit_building_to_right; this is low confidence.",
            "All route/AI/wall/surface geometries are vector trace candidates; the exact handle interpolation formula remains to validate.",
        ],
    }


def build_result(fixtures_root: Path) -> dict[str, Any]:
    fixtures = load_fixture_files(fixtures_root)
    parsed = [parse_fixture(fixture) for fixture in fixtures]
    status = "raw-reader-ready-for-g-s03-candidate-conversion" if parsed else "awaiting-fixtures"
    return {
        "scenario": "G-S02",
        "status": status,
        "generatedAt": utc_now(),
        "fixturesRoot": str(fixtures_root),
        "fixtureCount": len(parsed),
        "rawFixtures": parsed,
        "elementInventory": build_element_inventory(parsed),
        "schema": {
            "name": "UR2D2RawTrackData",
            "version": "0.1.0",
            "guarantees": [
                "Offsets are source byte offsets in the .sav file.",
                "Values are decoded as little-endian float32 only where a stable counted-array or object-payload hypothesis exists.",
                "Unknown regions are retained explicitly and not silently discarded.",
            ],
            "nonGuarantees": [
                "No conversion to metres is performed.",
                "No axis, orientation or direction convention is finalized.",
                "Object payload layouts remain provisional.",
                "Vector handle interpolation formula remains provisional.",
            ],
        },
    }


def write_json(path: Path, result: dict[str, Any]) -> None:
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# G-S02 - Lecteur brut exploratoire UR2D2 .sav",
        "",
        "- **Expérience :** G - Import du modèle minimal depuis les sauvegardes UR2D2",
        "- **Scénario :** G-S02",
        f"- **Statut :** {result['status']}",
        f"- **Date :** {result['generatedAt']}",
        f"- **Fixtures analysées :** {result['fixtureCount']}",
        "- **Sortie brute :** `UR2D2RawTrackData` v0.1.0",
        "",
        "## Décision du jalon",
        "",
        "G-S02 est exploitable pour préparer une G-S03 vector-aware : le lecteur brut extrait une région stable de tableaux `float32` comptés, des clés vectorielles candidates, des objets/checkpoints candidats et conserve les régions inconnues.",
        "",
        "## Schéma brut",
        "",
    ]
    for guarantee in result["schema"]["guarantees"]:
        lines.append(f"- {guarantee}")
    lines.extend(["", "Limites explicites :", ""])
    for limitation in result["schema"]["nonGuarantees"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Synthèse par fixture",
            "",
            "| Fixture | Taille | Tableaux | Clés route | Points échantillonnés | Checkpoints candidats | Objets candidats | Région tableaux |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for fixture in result["rawFixtures"]:
        geometry = fixture["pairedGeometryCandidates"]
        road_count = len(geometry.get("roadControlPoints", []))
        sampled_count = len(geometry.get("sampledLinePoints", []))
        region = fixture["countedFloatArrayRegion"]
        lines.append(
            f"| {fixture['fixture']} | {fixture['sizeBytes']} | {region['arrayCount']} | {road_count} | "
            f"{sampled_count} | {len(fixture['checkpointCandidates'])} | {len(fixture['namedObjectCandidates'])} | "
            f"`{region['startHexOffset']}..{region['endHexOffset']}` |"
        )

    lines.extend(
        [
            "",
            "## Inventaire des éléments attendus",
            "",
            f"- **Statut inventaire :** {result['elementInventory']['status']}",
            "",
            "| Élément | Attendu | Détecté/lu | Statut | Confiance | Fixture | Preuve |",
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for item in result["elementInventory"]["items"]:
        lines.append(
            f"| {item['label']} | {item['expected']} | {item['detected']} | {item['status']} | "
            f"{item['confidence']} | {item.get('fixture') or '-'} | {item['evidence']} |"
        )
    lines.extend(["", "Notes :", ""])
    for note in result["elementInventory"]["notes"]:
        lines.append(f"- {note}")

    lines.extend(["", "## Tableaux identifiés", ""])
    representative = next((fixture for fixture in result["rawFixtures"] if fixture["fixture"] == "T05_start_and_checkpoints"), None)
    if representative is None and result["rawFixtures"]:
        representative = result["rawFixtures"][-1]
    if representative is not None:
        lines.extend(["| Index | Nom provisoire | Confiance | Count | Offset | Extrait |", "| ---: | --- | --- | ---: | --- | --- |"])
        for array in representative["countedFloatArrays"]:
            values = ", ".join(str(value) for value in array["values"][:8])
            if len(array["values"]) > 8:
                values += ", ..."
            lines.append(
                f"| {array['index']} | `{array['name']}` | {array['confidence']} | {array['count']} | "
                f"`{array['hexOffset']}` | {values} |"
            )

    lines.extend(["", "## Checkpoints candidats", ""])
    checkpoint_fixture = next((fixture for fixture in result["rawFixtures"] if fixture["checkpointCandidates"]), None)
    if checkpoint_fixture is None:
        lines.append("Aucun checkpoint candidat détecté.")
    else:
        lines.extend(["| Fixture | Label | X | Y | Rotation | Payload |", "| --- | --- | ---: | ---: | ---: | --- |"])
        for checkpoint in checkpoint_fixture["checkpointCandidates"]:
            lines.append(
                f"| {checkpoint_fixture['fixture']} | {checkpoint.get('label') or '-'} | {checkpoint['x']} | "
                f"{checkpoint['y']} | {checkpoint['rotationDeg']} | `{checkpoint['payloadHexOffset']}` |"
            )

    lines.extend(
        [
            "",
            "## Interprétation provisoire",
            "",
            "- Les tableaux 0 et 1 forment les positions de clés de route candidates en unités éditeur.",
            "- Les tableaux 3 et 4 ressemblent à des angles de poignées vectorielles ; les tableaux 5 et 6 ressemblent à des poids de poignées.",
            "- Le `float32` global initial `10.0` devient le meilleur candidat de largeur de route pour `TrackDefinition` v0.1.",
            "- Les checkpoints sont présents avec positions et rotations plausibles dans T05.",
            "- Les objets murs, stands et surfaces sont détectables par token, mais leur payload exact reste moins fiable que celui des checkpoints.",
            "- La conversion G-S03 doit échantillonner les courbes vectorielles, pas seulement relier les clés par segments droits.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures-root", type=Path, default=DEFAULT_FIXTURES_ROOT)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    result = build_result(args.fixtures_root.resolve())
    write_json(results_dir / "g_s02_raw_reader.json", result)
    write_markdown(results_dir / "G_S02_RAW_READER_RESULT.md", result)
    print(f"G-S02 status: {result['status']}")
    print(f"Parsed fixtures: {result['fixtureCount']}")
    print(f"Wrote: {results_dir / 'G_S02_RAW_READER_RESULT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
