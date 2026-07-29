#!/usr/bin/env python3
"""Render vector handles as currently interpreted by the G-S04 prototype."""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path
from typing import Any

import render_g_s04_visual_validation as g04


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RAW_PATH = RESULTS_DIR / "g_s02_raw_reader.json"
CONVERSION_PATH = RESULTS_DIR / "g_s03_track_definition_conversion.json"
SVG_PATH = RESULTS_DIR / "G_S04_HANDLE_INTERPRETATION.svg"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def raw_handle_point(key: dict[str, Any], handle: str) -> dict[str, float]:
    return g04.raw_handle_endpoint(key, handle)


def strip_duplicate_key(keys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(keys) > 1 and g04.is_duplicate_point(keys[0], keys[-1]):
        return keys[:-1]
    return keys


def vector_trace_from_block(block: dict[str, Any] | None) -> dict[str, Any] | None:
    if block is None:
        return None
    return block.get("vectorTraceCandidate")


def collect_layers(raw: dict[str, Any]) -> list[dict[str, Any]]:
    t03 = g04.fixture_by_id(raw, "T03_ai_line")
    t04 = g04.fixture_by_id(raw, "T04_limits_or_walls")
    t05 = g04.fixture_by_id(raw, "T05_start_and_checkpoints")
    t06 = g04.fixture_by_id(raw, "T06_pit_lane")
    t07 = g04.fixture_by_id(raw, "T07_surfaces")

    ai_item = next((item for item in raw["elementInventory"]["items"] if item["id"] == "ai_lines"), {})
    ai_blocks = [
        g04.line_block_by_offset(t03, item["hexOffset"])
        for item in ai_item.get("blocks", [])
    ]
    pit_blocks = g04.line_blocks_after_token(t06, "spr_pit_building_to_right", 768)[:2]
    layers = [
        {
            "name": "Route principale",
            "status": "référence actuelle",
            "color": "#2f5f9f",
            "traces": [t05["vectorTraceCandidates"]["primaryRoad"]],
        },
        {
            "name": "Lignes IA",
            "status": "à confirmer",
            "color": "#e9a23b",
            "traces": [vector_trace_from_block(block) for block in ai_blocks],
        },
        {
            "name": "Mur",
            "status": "à confirmer",
            "color": "#4d4f53",
            "traces": [vector_trace_from_block(g04.nearest_line_block_after_token(t04, "wall1", 128))],
        },
        {
            "name": "Pit 1 / Pit 2",
            "status": "à confirmer",
            "color": "#8b5fbf",
            "traces": [vector_trace_from_block(block) for block in pit_blocks],
        },
        {
            "name": "Sable",
            "status": "à confirmer",
            "color": "#c58a1f",
            "traces": [vector_trace_from_block(g04.nearest_line_block_after_token(t07, "spr_sand", 128))],
        },
        {
            "name": "Arbres",
            "status": "à confirmer",
            "color": "#5c8d55",
            "traces": [vector_trace_from_block(g04.nearest_line_block_after_token(t07, "forrest2", 128))],
        },
    ]
    for layer in layers:
        layer["traces"] = [trace for trace in layer["traces"] if trace is not None]
    return layers


def converted_trace_points(trace: dict[str, Any], origin: dict[str, float], scale: float) -> list[dict[str, float]]:
    return [g04.convert_raw_point(key, origin, scale) for key in strip_duplicate_key(trace["keys"])]


def converted_handle_triplets(trace: dict[str, Any], origin: dict[str, float], scale: float) -> list[dict[str, Any]]:
    keys = strip_duplicate_key(trace["keys"])
    closed = len(trace["keys"]) > 1 and g04.is_duplicate_point(trace["keys"][0], trace["keys"][-1])
    triplets = []
    for index, key in enumerate(keys):
        source_b = keys[index - 1] if closed or index > 0 else None
        key_point = g04.convert_raw_point(key, origin, scale)
        handle_a = g04.convert_raw_point(raw_handle_point(key, "A"), origin, scale)
        handle_b = None
        if source_b is not None:
            handle_b = g04.convert_raw_point(g04.raw_incoming_handle_endpoint(source_b, {"x": float(key["x"]), "y": float(key["y"])}), origin, scale)
        triplets.append(
            {
                "index": int(key["index"]),
                "key": key_point,
                "a": handle_a,
                "b": handle_b,
                "bSourceIndex": int(source_b["index"]) if source_b is not None else None,
                "angleA": float(key["angleADeg"]),
                "angleB": float(source_b["angleBDeg"]) if source_b is not None else None,
                "weightA": float(key["weightA"]),
                "weightB": float(source_b["weightB"]) if source_b is not None else None,
            }
        )
    return triplets


def panel_mapper(points: list[dict[str, float]], x: int, y: int, width: int, height: int, pad: int):
    mapper = g04.make_mapper(points, width, height, pad)

    def mapped(point: dict[str, float]) -> tuple[float, float]:
        px, py = mapper(point)
        return x + px, y + py

    return mapped


def path_d(points: list[dict[str, float]], mapper, close: bool = False) -> str:
    if not points:
        return ""
    coords = [mapper(point) for point in points]
    if close and len(coords) > 2:
        coords.append(coords[0])
    commands = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    commands.extend(f"L {px:.1f} {py:.1f}" for px, py in coords[1:])
    if close:
        commands.append("Z")
    return " ".join(commands)


def render_panel(layer: dict[str, Any], origin: dict[str, float], scale: float, x: int, y: int, width: int, height: int) -> list[str]:
    all_points: list[dict[str, float]] = []
    traces_points = []
    traces_handles = []
    for trace in layer["traces"]:
        points = converted_trace_points(trace, origin, scale)
        handles = converted_handle_triplets(trace, origin, scale)
        traces_points.append(points)
        traces_handles.append(handles)
        all_points.extend(points)
        for handle in handles:
            all_points.append(handle["a"])
            if handle["b"] is not None:
                all_points.append(handle["b"])
    if not all_points:
        all_points = [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}]
    mapper = panel_mapper(all_points, x, y, width, height, 34)
    color = layer["color"]
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        f'<text x="{x + 18}" y="{y + 26}" class="label">{escape(layer["name"])}</text>',
        f'<text x="{x + 18}" y="{y + 48}" class="tiny">{escape(layer["status"])}</text>',
    ]
    for points in traces_points:
        close = len(points) > 2 and layer["name"] not in {"Pit 1 / Pit 2"}
        parts.append(f'<path d="{path_d(points, mapper, close)}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
    for handles in traces_handles:
        for handle in handles:
            kx, ky = mapper(handle["key"])
            ax, ay = mapper(handle["a"])
            parts.append(f'<line x1="{kx:.1f}" y1="{ky:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="{color}" stroke-width="1.6"/>')
            parts.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="4" fill="{color}"/>')
            parts.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="3" fill="#ffffff" stroke="{color}" stroke-width="1.5"/>')
            parts.append(f'<text x="{kx + 5:.1f}" y="{ky - 5:.1f}" class="tiny">K{handle["index"]}</text>')
            parts.append(f'<text x="{ax + 4:.1f}" y="{ay + 4:.1f}" class="tiny">A</text>')
            if handle["b"] is not None:
                bx, by = mapper(handle["b"])
                parts.append(f'<line x1="{kx:.1f}" y1="{ky:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{color}" stroke-width="1.6" stroke-dasharray="4 4"/>')
                parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="3" fill="{color}" fill-opacity="0.32" stroke="{color}" stroke-width="1.5"/>')
                parts.append(f'<text x="{bx + 4:.1f}" y="{by + 4:.1f}" class="tiny">B←K{handle["bSourceIndex"]}</text>')
    return parts


def render_svg() -> str:
    raw = load_json(RAW_PATH)
    conversion = load_json(CONVERSION_PATH)
    origin = conversion["conversionNotes"]["rawOriginEditorUnits"]
    scale = conversion["conversionNotes"]["scalePolicy"]["editorUnitsPerMetre"]
    layers = collect_layers(raw)
    width = 1280
    height = 1220
    panels = [
        (48, 142, 570, 330),
        (662, 142, 570, 330),
        (48, 504, 360, 330),
        (460, 504, 360, 330),
        (872, 504, 360, 330),
        (48, 866, 570, 300),
        (662, 866, 570, 300),
        (48, 1190, 1184, 0),
    ]
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
        f'<rect width="{width}" height="{height}" fill="#f7f9fc"/>',
        '<rect x="32" y="32" width="1216" height="86" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="56" y="70" class="title">G-S04 - Poignées vectorielles interprétées</text>',
        '<text x="56" y="98" class="subtitle">A = trait plein ; B = pointillé depuis la ligne précédente ; vecteurs de poignées avec inversion verticale globale</text>',
    ]
    for layer, panel in zip(layers, panels[:6]):
        parts.extend(render_panel(layer, origin, scale, *panel))
    x, y, w, h = panels[6]
    parts.extend(
        [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            f'<text x="{x + 18}" y="{y + 28}" class="label">Lecture actuelle</text>',
            f'<text x="{x + 18}" y="{y + 54}" class="small">Pour un segment Ki vers Ki+1 : A vient de Ki, B vient aussi de la ligne Ki mais s’ancre sur Ki+1. Les vecteurs de poignées sont lus avec Y inversé par rapport aux coordonnées brutes des points.</text>',
        ]
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(render_svg(), encoding="utf-8")
    print(f"Wrote: {SVG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
