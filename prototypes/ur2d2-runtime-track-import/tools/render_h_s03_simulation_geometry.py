#!/usr/bin/env python3
"""Render H-S03 converted simulation geometry as SVG."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SUMMARY_PATH = RESULTS_DIR / "h_s03_simulation_geometry.json"
OUTPUT_PATH = RESULTS_DIR / "H_S03_SIMULATION_GEOMETRY_VISUALIZATION.svg"

WIDTH = 1280
HEIGHT = 880
PLOT_X = 48
PLOT_Y = 142
PLOT_W = 820
PLOT_H = 660


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text(x: float, y: float, value: str, size: int = 14, weight: int = 400, fill: str = "#1f2937") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'
    )


def collect_points(data: dict[str, Any]) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    points.extend(data["trackDefinition"]["centerline"])
    for lane in data["pitlaneLanes"]:
        points.extend(lane["points"])
    for wall in data["walls"]:
        points.extend(wall["points"])
    points.extend(data["checkpointPoints"])
    return points


def make_mapper(points: list[dict[str, float]]):
    min_x = min(float(point["x"]) for point in points)
    max_x = max(float(point["x"]) for point in points)
    min_y = min(float(point["y"]) for point in points)
    max_y = max(float(point["y"]) for point in points)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((PLOT_W - 112) / span_x, (PLOT_H - 112) / span_y)

    def mapper(point: dict[str, float]) -> tuple[float, float]:
        return (
            PLOT_X + 56 + (float(point["x"]) - min_x) * scale,
            PLOT_Y + PLOT_H - 56 - (float(point["y"]) - min_y) * scale,
        )

    return mapper, scale


def path_d(points: list[dict[str, float]], mapper: Any, close: bool = False) -> str:
    if not points:
        return ""
    coords = [mapper(point) for point in points]
    if close:
        coords.append(coords[0])
    commands = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    commands.extend(f"L {x:.1f} {y:.1f}" for x, y in coords[1:])
    if close:
        commands.append("Z")
    return " ".join(commands)


def render(data: dict[str, Any]) -> str:
    track = data["trackDefinition"]
    centerline = track["centerline"]
    checkpoints = data["checkpointPoints"]
    mapper, px_per_m = make_mapper(collect_points(data))
    road_width_m = max(float(point["leftWidth"]) + float(point["rightWidth"]) for point in centerline)
    road_width_px = max(4.0, road_width_m * px_per_m)
    pitlane_width_px = max(3.0, 5.0 * px_per_m)
    validation = data["validation"]
    preprocessed = validation.get("preprocessed", {})

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#2f5f9f"/></marker></defs>',
        '<rect x="32" y="28" width="1216" height="86" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        text(56, 66, "H-S03 - Géométrie de simulation convertie", 26, 700),
        text(56, 96, f"Statut : {data['status']} | C-S01 : {'succès' if validation['success'] else 'échec'} | {len(centerline)} points centerline", 14, 500, "#64748b"),
        f'<rect x="{PLOT_X}" y="{PLOT_Y}" width="{PLOT_W}" height="{PLOT_H}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        f'<path d="{path_d(centerline, mapper, True)}" fill="none" stroke="#d9e1ea" stroke-width="{road_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.78"/>',
        f'<path d="{path_d(centerline, mapper, True)}" fill="none" stroke="#2f5f9f" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
    ]

    arrow_step = max(1, len(centerline) // 12)
    for index in range(0, len(centerline), arrow_step):
        point = centerline[index]
        next_point = centerline[(index + 1) % len(centerline)]
        x1, y1 = mapper(point)
        x2, y2 = mapper(next_point)
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy) or 1.0
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x1 + dx / length * 22:.1f}" y2="{y1 + dy / length * 22:.1f}" '
            'stroke="#2f5f9f" stroke-width="2.2" marker-end="url(#arrow)"/>'
        )

    for lane in data["pitlaneLanes"]:
        parts.append(
            f'<path d="{path_d(lane["points"], mapper)}" fill="none" stroke="#8b5fbf" '
            f'stroke-width="{pitlane_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.22"/>'
        )
        parts.append(
            f'<path d="{path_d(lane["points"], mapper)}" fill="none" stroke="#8b5fbf" '
            'stroke-width="3" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="9 6"/>'
        )
        x, y = mapper(lane["points"][0])
        label = "pit entry" if lane["role"] == "pitlane-entry" else "pit exit"
        parts.append(text(x + 8, y - 8, label, 12, 700, "#8b5fbf"))

    for wall in data["walls"]:
        parts.append(
            f'<path d="{path_d(wall["points"], mapper)}" fill="none" stroke="#333840" '
            'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    for checkpoint in checkpoints:
        x, y = mapper(checkpoint)
        color = "#d1495b" if checkpoint.get("label") == "Finish" else "#f29f05"
        label = checkpoint.get("label") or checkpoint["id"]
        parts.append(f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="{color}" transform="rotate(45 {x:.1f} {y:.1f})"/>')
        parts.append(text(x + 10, y + 4, label, 12, 600, "#334155"))

    panel_x = 910
    notes = data["conversionNotes"]
    parts.extend(
        [
            f'<rect x="{panel_x}" y="{PLOT_Y}" width="318" height="{PLOT_H}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            text(panel_x + 22, PLOT_Y + 36, "Conversion", 16, 700),
            text(panel_x + 22, PLOT_Y + 66, f"Échelle: 1 m = {notes['scalePolicy']['editorUnitsPerMetre']} unités", 12, 500, "#475569"),
            text(panel_x + 22, PLOT_Y + 92, f"Largeur: {notes['widthPolicy']['totalRoadWidthM']:.1f} m", 12, 500, "#475569"),
            text(panel_x + 22, PLOT_Y + 118, f"Orientation: {track['direction']}", 12, 500, "#475569"),
            text(panel_x + 22, PLOT_Y + 156, "Validation C-S01", 16, 700),
            text(panel_x + 22, PLOT_Y + 186, f"Longueur: {preprocessed.get('totalLengthM', 0.0):.3f} m", 12, 500, "#475569"),
            text(panel_x + 22, PLOT_Y + 212, f"Points: {preprocessed.get('pointCount', 0)}", 12, 500, "#475569"),
            text(panel_x + 22, PLOT_Y + 238, f"Courbure max: {preprocessed.get('maxAbsCurvature', 0.0):.5f} 1/m", 12, 500, "#475569"),
            text(panel_x + 22, PLOT_Y + 276, "Éléments hors contrat C", 16, 700),
            text(panel_x + 22, PLOT_Y + 306, f"Pitlane: {len(data['pitlaneLanes'])} voies", 12, 500, "#475569"),
            text(panel_x + 22, PLOT_Y + 332, f"Murs: {len(data['walls'])}", 12, 500, "#475569"),
            text(panel_x + 22, PLOT_Y + 370, "Légende", 16, 700),
            f'<path d="M{panel_x + 22},402 L{panel_x + 52},402" stroke="#2f5f9f" stroke-width="4"/>{text(panel_x + 64, 407, "centerline", 12, 500, "#475569")}',
            f'<path d="M{panel_x + 22},434 L{panel_x + 52},434" stroke="#d9e1ea" stroke-width="12"/>{text(panel_x + 64, 439, "largeur roulable", 12, 500, "#475569")}',
            f'<path d="M{panel_x + 22},466 L{panel_x + 52},466" stroke="#8b5fbf" stroke-width="8" opacity="0.35"/>{text(panel_x + 64, 471, "pitlane", 12, 500, "#475569")}',
            f'<path d="M{panel_x + 22},498 L{panel_x + 52},498" stroke="#333840" stroke-width="5"/>{text(panel_x + 64, 503, "mur", 12, 500, "#475569")}',
            f'<rect x="{panel_x + 30}" y="522" width="14" height="14" fill="#d1495b" transform="rotate(45 {panel_x + 37} 529)"/>{text(panel_x + 64, 533, "finish", 12, 500, "#475569")}',
            text(48, 846, "H-S03 convertit les données .sav vers un repère métrique de simulation. La superposition au fond PNG est réservée à H-S04.", 13, 500, "#64748b"),
            "</svg>",
        ]
    )
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_json(args.summary)
    args.output.write_text(render(data), encoding="utf-8", newline="\n")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
