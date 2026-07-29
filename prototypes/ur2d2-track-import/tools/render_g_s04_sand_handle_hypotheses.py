#!/usr/bin/env python3
"""Render sand handle axis hypotheses for G-S04 visual validation."""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path
from typing import Any

import render_g_s04_handle_interpretation as handles
import render_g_s04_visual_validation as g04


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RAW_PATH = RESULTS_DIR / "g_s02_raw_reader.json"
CONVERSION_PATH = RESULTS_DIR / "g_s03_track_definition_conversion.json"
SVG_PATH = RESULTS_DIR / "G_S04_SAND_HANDLE_HYPOTHESES.svg"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sand_trace(raw: dict[str, Any]) -> dict[str, Any]:
    layer = next(item for item in handles.collect_layers(raw) if item["name"] == "Sable")
    return layer["traces"][0]


def transform_vector(vector: dict[str, float], mode: str) -> dict[str, float]:
    if mode == "identity":
        return vector
    if mode == "flip-y":
        return {"x": vector["x"], "y": -vector["y"]}
    if mode == "flip-x":
        return {"x": -vector["x"], "y": vector["y"]}
    if mode == "flip-xy":
        return {"x": -vector["x"], "y": -vector["y"]}
    raise ValueError(f"unknown vector transform {mode}")


def feedback_mode(index: int) -> str:
    if index in {0, 1}:
        return "flip-y"
    if index in {4, 5, 6}:
        return "flip-x"
    return "identity"


def key_points(trace: dict[str, Any], origin: dict[str, float], scale: float) -> list[dict[str, float]]:
    return [g04.convert_raw_point(key, origin, scale) for key in handles.strip_duplicate_key(trace["keys"])]


def handle_triplets(trace: dict[str, Any], origin: dict[str, float], scale: float, mode_name: str) -> list[dict[str, Any]]:
    keys = handles.strip_duplicate_key(trace["keys"])
    triplets = []
    for index, key in enumerate(keys):
        prev_key = keys[index - 1]
        mode = feedback_mode(index) if mode_name == "feedback" else mode_name
        key_point = g04.convert_raw_point(key, origin, scale)
        raw_a_vector = g04.vector2(float(key["angleADeg"]), float(key["weightA"]))
        raw_b_vector = g04.vector2(float(prev_key["angleBDeg"]), float(prev_key["weightB"]))
        a_vector = transform_vector(raw_a_vector, mode)
        b_vector = transform_vector(raw_b_vector, mode)
        raw_a = {"x": float(key["x"]) + a_vector["x"], "y": float(key["y"]) + a_vector["y"]}
        raw_b = {"x": float(key["x"]) + b_vector["x"], "y": float(key["y"]) + b_vector["y"]}
        triplets.append(
            {
                "index": index,
                "mode": mode,
                "key": key_point,
                "a": g04.convert_raw_point(raw_a, origin, scale),
                "b": g04.convert_raw_point(raw_b, origin, scale),
            }
        )
    return triplets


def path_d(points: list[dict[str, float]], mapper) -> str:
    coords = [mapper(point) for point in points]
    commands = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    commands.extend(f"L {x:.1f} {y:.1f}" for x, y in coords[1:])
    commands.append("Z")
    return " ".join(commands)


def panel(
    trace: dict[str, Any],
    origin: dict[str, float],
    scale: float,
    mode_name: str,
    title: str,
    x: int,
    y: int,
    width: int,
    height: int,
) -> list[str]:
    points = key_points(trace, origin, scale)
    triplets = handle_triplets(trace, origin, scale, mode_name)
    all_points = list(points)
    for triplet in triplets:
        all_points.extend([triplet["a"], triplet["b"]])
    mapper = handles.panel_mapper(all_points, x, y, width, height, 34)
    parts = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        f'<text x="{x + 18}" y="{y + 28}" class="label">{escape(title)}</text>',
        f'<path d="{path_d(points, mapper)}" fill="none" stroke="#c58a1f" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>',
    ]
    for triplet in triplets:
        kx, ky = mapper(triplet["key"])
        ax, ay = mapper(triplet["a"])
        bx, by = mapper(triplet["b"])
        parts.append(f'<line x1="{kx:.1f}" y1="{ky:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="#c58a1f" stroke-width="1.5"/>')
        parts.append(f'<line x1="{kx:.1f}" y1="{ky:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="#c58a1f" stroke-width="1.5" stroke-dasharray="4 4"/>')
        parts.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="4" fill="#c58a1f"/>')
        parts.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="3" fill="#ffffff" stroke="#c58a1f" stroke-width="1.5"/>')
        parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="3" fill="#c58a1f" fill-opacity="0.32" stroke="#c58a1f" stroke-width="1.5"/>')
        parts.append(f'<text x="{kx + 5:.1f}" y="{ky - 5:.1f}" class="tiny">K{triplet["index"]}</text>')
    return parts


def render_svg() -> str:
    raw = load_json(RAW_PATH)
    conversion = load_json(CONVERSION_PATH)
    origin = conversion["conversionNotes"]["rawOriginEditorUnits"]
    scale = conversion["conversionNotes"]["scalePolicy"]["editorUnitsPerMetre"]
    trace = sand_trace(raw)
    panels = [
        ("identity", "Sans inversion", 48, 142),
        ("flip-y", "Hypothèse retenue : inversion verticale globale", 662, 142),
        ("flip-x", "Inversion horizontale globale", 48, 514),
        ("feedback", "Selon ton retour : K0-K1 Y, K2-K3 ok, K4-K6 X", 662, 514),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="910" viewBox="0 0 1280 910">',
        "<style>",
        "text{font-family:Segoe UI,Arial,sans-serif;fill:#25313f}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6b7a}",
        ".label{font-size:14px;font-weight:600}",
        ".small{font-size:12px;fill:#627282}",
        ".tiny{font-size:11px;fill:#627282}",
        "</style>",
        '<rect width="1280" height="910" fill="#f7f9fc"/>',
        '<rect x="32" y="32" width="1216" height="86" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="56" y="70" class="title">G-S04 - Hypothèses de repère des poignées du sable</text>',
        '<text x="56" y="98" class="subtitle">A en trait plein, B en pointillé ; B reste ancrée sur la clé courante depuis la ligne précédente</text>',
    ]
    for mode, title, x, y in panels:
        parts.extend(panel(trace, origin, scale, mode, title, x, y, 570, 330))
    parts.extend(
        [
            '<rect x="48" y="854" width="1184" height="34" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            '<text x="66" y="876" class="small">But : identifier si les angles des zones utilisent un repère local ou une règle d’axe dépendante de la clé avant de généraliser la correction à l’importeur.</text>',
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
