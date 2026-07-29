#!/usr/bin/env python3
"""Render G-S04 source-to-candidate visual validation as SVG."""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RAW_PATH = RESULTS_DIR / "g_s02_raw_reader.json"
TRACK_PATH = RESULTS_DIR / "g_s03_track_definition_candidate.json"
CONVERSION_PATH = RESULTS_DIR / "g_s03_track_definition_conversion.json"
G_S04_PATH = RESULTS_DIR / "g_s04_visual_validation.json"
SVG_PATH = RESULTS_DIR / "G_S04_VISUAL_VALIDATION.svg"
SAMPLES_PER_VECTOR_SEGMENT = 10


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_by_id(raw: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    return next(fixture for fixture in raw["rawFixtures"] if fixture["fixture"] == fixture_id)


def convert_raw_point(point: dict[str, float], origin: dict[str, float], scale: float) -> dict[str, float]:
    return {
        "x": (float(point["x"]) - origin["x"]) / scale,
        "y": -(float(point["y"]) - origin["y"]) / scale,
    }


def vector2(angle_deg: float, length: float) -> dict[str, float]:
    radians = math.radians(angle_deg)
    return {"x": math.cos(radians) * length, "y": math.sin(radians) * length}


def handle_vector2(angle_deg: float, length: float) -> dict[str, float]:
    vector = vector2(angle_deg, length)
    return {"x": vector["x"], "y": -vector["y"]}


def raw_handle_endpoint(key: dict[str, Any], handle: str) -> dict[str, float]:
    angle_key = "angleADeg" if handle == "A" else "angleBDeg"
    weight_key = "weightA" if handle == "A" else "weightB"
    vector = handle_vector2(float(key[angle_key]), float(key[weight_key]))
    return {"x": float(key["x"]) + vector["x"], "y": float(key["y"]) + vector["y"]}


def raw_incoming_handle_endpoint(source_key: dict[str, Any], target_point: dict[str, float]) -> dict[str, float]:
    vector_b = handle_vector2(float(source_key["angleBDeg"]), float(source_key["weightB"]))
    return {"x": target_point["x"] + vector_b["x"], "y": target_point["y"] + vector_b["y"]}


def bezier(p0: dict[str, float], c0: dict[str, float], c1: dict[str, float], p1: dict[str, float], t: float) -> dict[str, float]:
    u = 1.0 - t
    return {
        "x": u**3 * p0["x"] + 3 * u * u * t * c0["x"] + 3 * u * t * t * c1["x"] + t**3 * p1["x"],
        "y": u**3 * p0["y"] + 3 * u * u * t * c0["y"] + 3 * u * t * t * c1["y"] + t**3 * p1["y"],
    }


def is_duplicate_point(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return math.isclose(float(a["x"]), float(b["x"])) and math.isclose(float(a["y"]), float(b["y"]))


def vector_handles(keys: list[dict[str, Any]], origin: dict[str, float], scale: float) -> list[dict[str, Any]]:
    unique_keys = keys[:-1] if len(keys) > 1 and is_duplicate_point(keys[0], keys[-1]) else keys
    closed = len(keys) > 1 and is_duplicate_point(keys[0], keys[-1])
    segment_count = len(unique_keys) if closed else max(0, len(unique_keys) - 1)
    handles = []
    for index in range(segment_count):
        key = unique_keys[index]
        next_key = unique_keys[(index + 1) % len(unique_keys)]
        p0 = {"x": float(key["x"]), "y": float(key["y"])}
        p1 = {"x": float(next_key["x"]), "y": float(next_key["y"])}
        out_handle = handle_vector2(float(key["angleADeg"]), float(key["weightA"]))
        c0 = {"x": p0["x"] + out_handle["x"], "y": p0["y"] + out_handle["y"]}
        c1 = raw_incoming_handle_endpoint(key, p1)
        handles.append(
            {
                "from": convert_raw_point(p0, origin, scale),
                "out": convert_raw_point(c0, origin, scale),
                "to": convert_raw_point(p1, origin, scale),
                "in": convert_raw_point(c1, origin, scale),
            }
        )
    return handles


def sample_vector_trace(keys: list[dict[str, Any]], origin: dict[str, float], scale: float) -> list[dict[str, float]]:
    unique_keys = keys[:-1] if len(keys) > 1 and is_duplicate_point(keys[0], keys[-1]) else keys
    closed = len(keys) > 1 and is_duplicate_point(keys[0], keys[-1])
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
        for step in range(SAMPLES_PER_VECTOR_SEGMENT):
            raw_point = bezier(p0, c0, c1, p1, step / SAMPLES_PER_VECTOR_SEGMENT)
            sampled.append(convert_raw_point(raw_point, origin, scale))
    if closed and sampled:
        sampled.append(sampled[0])
    elif unique_keys:
        sampled.append(convert_raw_point(unique_keys[-1], origin, scale))
    return sampled


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
    seen = set()
    for offset in token_offsets:
        for block in fixture.get("lineLikeBlocks", []):
            distance = block["offset"] - offset
            if 0 <= distance <= max_distance and block["offset"] not in seen:
                seen.add(block["offset"])
                blocks.append(block)
    return sorted(blocks, key=lambda block: block["offset"])


def sampled_block(block: dict[str, Any] | None, origin: dict[str, float], scale: float) -> list[dict[str, float]]:
    if block is None:
        return []
    vector = block.get("vectorTraceCandidate")
    if vector:
        return sample_vector_trace(vector["keys"], origin, scale)
    return [convert_raw_point(point, origin, scale) for point in block.get("points", [])]


def path_d(points: list[dict[str, float]], mapper, close: bool = False) -> str:
    if not points:
        return ""
    coords = [mapper(point) for point in points]
    if close and len(coords) > 2:
        coords.append(coords[0])
    commands = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    commands.extend(f"L {x:.1f} {y:.1f}" for x, y in coords[1:])
    if close:
        commands.append("Z")
    return " ".join(commands)


def bounds(points: list[dict[str, float]]) -> tuple[float, float, float, float]:
    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def make_mapper(points: list[dict[str, float]], width: int, height: int, pad: int):
    min_x, max_x, min_y, max_y = bounds(points)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)

    def mapper(point: dict[str, float]) -> tuple[float, float]:
        return pad + (point["x"] - min_x) * scale, height - pad - (point["y"] - min_y) * scale

    return mapper


def road_ribbon(centerline: list[dict[str, Any]]) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    def unit_segment(from_point: dict[str, Any], to_point: dict[str, Any]) -> dict[str, float]:
        dx = to_point["x"] - from_point["x"]
        dy = to_point["y"] - from_point["y"]
        length = math.hypot(dx, dy) or 1.0
        return {"x": dx / length, "y": dy / length}

    def line_intersection(
        p0: dict[str, float],
        d0: dict[str, float],
        p1: dict[str, float],
        d1: dict[str, float],
    ) -> dict[str, float] | None:
        cross = d0["x"] * d1["y"] - d0["y"] * d1["x"]
        if abs(cross) < 1e-9:
            return None
        dx = p1["x"] - p0["x"]
        dy = p1["y"] - p0["y"]
        t = (dx * d1["y"] - dy * d1["x"]) / cross
        return {"x": p0["x"] + d0["x"] * t, "y": p0["y"] + d0["y"] * t}

    def offset_point(index: int, side: float) -> dict[str, float]:
        point = centerline[index]
        prev_point = centerline[(index - 1) % count]
        next_point = centerline[(index + 1) % count]
        prev_dir = unit_segment(prev_point, point)
        next_dir = unit_segment(point, next_point)
        width_key = "leftWidth" if side > 0 else "rightWidth"
        width = point[width_key]
        prev_normal = {"x": -prev_dir["y"] * side, "y": prev_dir["x"] * side}
        next_normal = {"x": -next_dir["y"] * side, "y": next_dir["x"] * side}
        prev_offset = {"x": point["x"] + prev_normal["x"] * width, "y": point["y"] + prev_normal["y"] * width}
        next_offset = {"x": point["x"] + next_normal["x"] * width, "y": point["y"] + next_normal["y"] * width}
        intersection = line_intersection(prev_offset, prev_dir, next_offset, next_dir)
        if intersection is not None:
            return intersection
        normal = {
            "x": (prev_normal["x"] + next_normal["x"]) / 2.0,
            "y": (prev_normal["y"] + next_normal["y"]) / 2.0,
        }
        normal_length = math.hypot(normal["x"], normal["y"]) or 1.0
        return {
            "x": point["x"] + normal["x"] / normal_length * width,
            "y": point["y"] + normal["y"] / normal_length * width,
        }

    count = len(centerline)
    return [offset_point(index, 1.0) for index in range(count)], [offset_point(index, -1.0) for index in range(count)]


def render_svg() -> str:
    raw = load_json(RAW_PATH)
    track = load_json(TRACK_PATH)
    conversion = load_json(CONVERSION_PATH)
    g_s04 = load_json(G_S04_PATH) if G_S04_PATH.exists() else {"status": "not-run", "checks": {}}
    origin = conversion["conversionNotes"]["rawOriginEditorUnits"]
    scale = conversion["conversionNotes"]["scalePolicy"]["editorUnitsPerMetre"]
    t03 = fixture_by_id(raw, "T03_ai_line")
    t04 = fixture_by_id(raw, "T04_limits_or_walls")
    t05 = fixture_by_id(raw, "T05_start_and_checkpoints")
    t06 = fixture_by_id(raw, "T06_pit_lane")
    t07 = fixture_by_id(raw, "T07_surfaces")

    road_keys = t05["vectorTraceCandidates"]["primaryRoad"]["keys"]
    road_key_points = [convert_raw_point(key, origin, scale) for key in road_keys[:-1]]
    road_handles = vector_handles(road_keys, origin, scale)

    ai_item = next((item for item in raw["elementInventory"]["items"] if item["id"] == "ai_lines"), {})
    ai_lines = [sampled_block(line_block_by_offset(t03, item["hexOffset"]), origin, scale) for item in ai_item.get("blocks", [])]
    wall = sampled_block(nearest_line_block_after_token(t04, "wall1", 128), origin, scale)
    pit_blocks = line_blocks_after_token(t06, "spr_pit_building_to_right", 768)[:2]
    pit_lines = [sampled_block(block, origin, scale) for block in pit_blocks]
    pitlane = [pit_lines[0][0], pit_lines[1][0]] if len(pit_lines) >= 2 and pit_lines[0] and pit_lines[1] else []
    tree = sampled_block(nearest_line_block_after_token(t07, "forrest2", 128), origin, scale)
    sand = sampled_block(nearest_line_block_after_token(t07, "spr_sand", 128), origin, scale)
    checkpoints = [
        {
            "id": checkpoint.get("label") or "Checkpoint",
            "point": convert_raw_point(checkpoint, origin, scale),
        }
        for checkpoint in t05.get("checkpointCandidates", [])
    ]

    centerline = track["centerline"]
    left_edge, right_edge = road_ribbon(centerline)
    all_points: list[dict[str, float]] = []
    for group in [
        centerline,
        left_edge,
        right_edge,
        road_key_points,
        sand,
        tree,
        wall,
        *ai_lines,
        *pit_lines,
        pitlane,
        [checkpoint["point"] for checkpoint in checkpoints],
    ]:
        all_points.extend(group)
    for handle in road_handles:
        all_points.extend([handle["from"], handle["out"], handle["to"], handle["in"]])

    width = 1280
    height = 860
    plot_x = 48
    plot_y = 142
    plot_w = 820
    plot_h = 650
    mapper = make_mapper(all_points, plot_w, plot_h, 56)

    def mp(point: dict[str, float]) -> tuple[float, float]:
        x, y = mapper(point)
        return x + plot_x, y + plot_y

    def local_path(points: list[dict[str, float]], close: bool = False) -> str:
        return path_d(points, mp, close)

    road_width_m = max(point["leftWidth"] + point["rightWidth"] for point in centerline)
    road_width_px = abs(mp({"x": road_width_m, "y": 0.0})[0] - mp({"x": 0.0, "y": 0.0})[0])
    pitlane_width_px = abs(mp({"x": 5.0, "y": 0.0})[0] - mp({"x": 0.0, "y": 0.0})[0])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Segoe UI,Arial,sans-serif;fill:#25313f}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6b7a}",
        ".label{font-size:14px;font-weight:600}",
        ".small{font-size:12px;fill:#627282}",
        ".tiny{font-size:11px;fill:#627282}",
        "</style>",
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#2f5f9f"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="#f7f9fc"/>',
        '<rect x="32" y="32" width="1216" height="86" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="56" y="70" class="title">G-S04 - Validation visuelle UR2D2</text>',
        f'<text x="56" y="98" class="subtitle">Statut: {escape(g_s04.get("status", "unknown"))} · repère converti en mètres · source .sav éditeur</text>',
        f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        f'<path d="{local_path(tree, True)}" fill="#7fb069" fill-opacity="0.18" stroke="#5c8d55" stroke-width="2"/>',
        f'<path d="{local_path(sand, True)}" fill="#e3b55d" fill-opacity="0.28" stroke="#c58a1f" stroke-width="2"/>',
        f'<path d="{local_path(centerline, True)}" fill="none" stroke="#d9e1ea" stroke-width="{road_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.72"/>',
    ]
    for line in ai_lines:
        parts.append(f'<path d="{local_path(line)}" fill="none" stroke="#e9a23b" stroke-width="2.2" stroke-dasharray="7 6"/>')
    if pitlane:
        parts.append(f'<path d="{local_path(pitlane)}" fill="none" stroke="#8b5fbf" stroke-width="{pitlane_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.32"/>')
    for index, line in enumerate(pit_lines, start=1):
        parts.append(f'<path d="{local_path(line)}" fill="none" stroke="#8b5fbf" stroke-width="{pitlane_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.22"/>')
        parts.append(f'<path d="{local_path(line)}" fill="none" stroke="#8b5fbf" stroke-width="2.2" stroke-dasharray="9 5"/>')
        if line:
            x, y = mp(line[0])
            label = "pit1 entrée" if index == 1 else "pit2 sortie"
            parts.append(f'<text x="{x + 8:.1f}" y="{y - 8:.1f}" class="tiny">{label}</text>')
    parts.extend(
        [
            f'<path d="{local_path(wall)}" fill="none" stroke="#4d4f53" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
            f'<path d="{local_path(centerline, True)}" fill="none" stroke="#2f5f9f" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" marker-mid="url(#arrow)"/>',
        ]
    )
    for handle in road_handles:
        fx, fy = mp(handle["from"])
        ox, oy = mp(handle["out"])
        tx, ty = mp(handle["to"])
        ix, iy = mp(handle["in"])
        parts.append(f'<line x1="{fx:.1f}" y1="{fy:.1f}" x2="{ox:.1f}" y2="{oy:.1f}" stroke="#2f5f9f" stroke-width="1.5" stroke-dasharray="4 4"/>')
        parts.append(f'<line x1="{tx:.1f}" y1="{ty:.1f}" x2="{ix:.1f}" y2="{iy:.1f}" stroke="#2f5f9f" stroke-width="1.5" stroke-dasharray="4 4"/>')
        parts.append(f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="3" fill="#ffffff" stroke="#2f5f9f" stroke-width="1.5"/>')
        parts.append(f'<circle cx="{ix:.1f}" cy="{iy:.1f}" r="3" fill="#ffffff" stroke="#2f5f9f" stroke-width="1.5"/>')
    for index, point in enumerate(centerline):
        x, y = mp(point)
        fill = "#2f5f9f" if index % 4 == 0 else "#7aa6d8"
        radius = 6 if index % 4 == 0 else 3.5
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{fill}"/>')
        if index % 4 == 0:
            parts.append(f'<text x="{x + 8:.1f}" y="{y - 8:.1f}" class="small">P{index:02d}</text>')
    for index, point in enumerate(road_key_points):
        x, y = mp(point)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="none" stroke="#d1495b" stroke-width="2"/>')
        parts.append(f'<text x="{x - 10:.1f}" y="{y + 22:.1f}" class="small">K{index}</text>')
    for checkpoint in checkpoints:
        x, y = mp(checkpoint["point"])
        color = "#d1495b" if checkpoint["id"] == "Finish" else "#f29f05"
        parts.append(f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="{color}" transform="rotate(45 {x:.1f} {y:.1f})"/>')
        parts.append(f'<text x="{x + 10:.1f}" y="{y + 4:.1f}" class="small">{escape(checkpoint["id"])}</text>')

    legend_x = 910
    layers = g_s04.get("checks", {}).get("requiredVisualLayers", {}).get("layers", {})
    preprocessed = conversion.get("validation", {}).get("preprocessed", {})
    total_width = preprocessed.get("minTotalWidthM", 0)
    parts.extend(
        [
            f'<rect x="{legend_x}" y="142" width="318" height="510" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            f'<text x="{legend_x + 22}" y="178" class="label">Couches superposées</text>',
            f'<path d="M{legend_x + 22},212 L{legend_x + 52},212" stroke="#2f5f9f" stroke-width="4"/><text x="{legend_x + 64}" y="217" class="small">centerline TrackDefinition</text>',
            f'<rect x="{legend_x + 22}" y="236" width="30" height="14" fill="#d9e1ea" stroke="#b4c2d0"/><text x="{legend_x + 64}" y="248" class="small">largeur de piste {total_width:.1f} m</text>',
            f'<path d="M{legend_x + 22},274 L{legend_x + 52},274" stroke="#e9a23b" stroke-width="2.2" stroke-dasharray="7 6"/><text x="{legend_x + 64}" y="279" class="small">lignes IA ({layers.get("aiLines", 0)})</text>',
            f'<path d="M{legend_x + 22},306 L{legend_x + 52},306" stroke="#4d4f53" stroke-width="4"/><text x="{legend_x + 64}" y="311" class="small">mur multi-segments</text>',
            f'<path d="M{legend_x + 22},338 L{legend_x + 52},338" stroke="#8b5fbf" stroke-width="8" stroke-opacity="0.28"/><path d="M{legend_x + 22},338 L{legend_x + 52},338" stroke="#8b5fbf" stroke-width="2.2" stroke-dasharray="9 5"/><text x="{legend_x + 64}" y="343" class="small">pit1 entrée / pit2 sortie, 5 m</text>',
            f'<path d="M{legend_x + 22},370 L{legend_x + 52},370" stroke="#8b5fbf" stroke-width="8" stroke-opacity="0.32"/><text x="{legend_x + 64}" y="375" class="small">pitlane droite ({layers.get("pitlaneSegments", 0)})</text>',
            f'<rect x="{legend_x + 22}" y="394" width="30" height="16" fill="#e3b55d" fill-opacity="0.45" stroke="#c58a1f"/><text x="{legend_x + 64}" y="407" class="small">sable</text>',
            f'<rect x="{legend_x + 22}" y="426" width="30" height="16" fill="#7fb069" fill-opacity="0.28" stroke="#5c8d55"/><text x="{legend_x + 64}" y="439" class="small">arbres</text>',
            f'<circle cx="{legend_x + 37}" cy="468" r="9" fill="none" stroke="#d1495b" stroke-width="2"/><text x="{legend_x + 64}" y="473" class="small">clés vectorielles route</text>',
            f'<rect x="{legend_x + 30}" y="492" width="14" height="14" fill="#d1495b" transform="rotate(45 {legend_x + 37} 499)"/><text x="{legend_x + 64}" y="504" class="small">départ/checkpoints ({layers.get("checkpoints", 0)})</text>',
            f'<text x="{legend_x + 22}" y="522" class="label">Validation</text>',
            f'<text x="{legend_x + 22}" y="552" class="small">C-S01: {escape(g_s04.get("checks", {}).get("cS01Validation", {}).get("status", "?"))}</text>',
            f'<text x="{legend_x + 22}" y="578" class="small">Longueur: {preprocessed.get("totalLengthM", 0):.3f} m</text>',
            f'<text x="{legend_x + 22}" y="604" class="small">Largeur min: {preprocessed.get("minTotalWidthM", 0):.3f} m</text>',
            f'<text x="{legend_x + 22}" y="630" class="small">Statut couches: {escape(g_s04.get("checks", {}).get("requiredVisualLayers", {}).get("status", "?"))}</text>',
            f'<rect x="{legend_x}" y="676" width="318" height="116" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            f'<text x="{legend_x + 22}" y="710" class="label">Réserves</text>',
            f'<text x="{legend_x + 22}" y="738" class="small">Pas de capture éditeur de référence.</text>',
            f'<text x="{legend_x + 22}" y="764" class="small">Poignées hors route non confirmées.</text>',
            '<text x="48" y="828" class="small">La vue superpose les données brutes converties dans le repère G-S03. Les surfaces hors contrat C sont affichées pour contrôle visuel, mais ne sont pas encore sérialisées dans TrackDefinition v0.1.</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(render_svg(), encoding="utf-8")
    print(f"Wrote: {SVG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
