#!/usr/bin/env python3
"""Render G-S03 TrackDefinition conversion as SVG."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
TRACK_PATH = RESULTS_DIR / "g_s03_track_definition_candidate.json"
SUMMARY_PATH = RESULTS_DIR / "g_s03_track_definition_conversion.json"
SVG_PATH = RESULTS_DIR / "G_S03_TRACK_DEFINITION_CONVERSION_VISUALIZATION.svg"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def map_points(points: list[dict[str, float]], width: int, height: int, pad: int):
    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    scale = min((width - 2 * pad) / max(max_x - min_x, 1.0), (height - 2 * pad) / max(max_y - min_y, 1.0))

    def mapper(point: dict[str, float]) -> tuple[float, float]:
        return pad + (point["x"] - min_x) * scale, height - pad - (point["y"] - min_y) * scale

    return mapper


def render_svg() -> str:
    if not TRACK_PATH.exists() or not SUMMARY_PATH.exists():
        return '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="360"><text x="40" y="80">G-S03 conversion not available.</text></svg>'

    track = load_json(TRACK_PATH)
    summary = load_json(SUMMARY_PATH)
    centerline = track["centerline"]
    checkpoints = track["checkpoints"]
    width = 1120
    height = 760
    plot_x = 56
    plot_y = 150
    plot_w = 650
    plot_h = 520
    mapper = map_points(centerline, plot_w, plot_h, 46)

    def mp(point: dict[str, float]) -> tuple[float, float]:
        x, y = mapper(point)
        return x + plot_x, y + plot_y

    coords = [mp(point) for point in centerline]
    coords.append(coords[0])
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    points_by_id = {point["id"]: point for point in centerline}
    preprocessed = summary["validation"].get("preprocessed", {})

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Segoe UI,Arial,sans-serif;fill:#25313f}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6b7a}",
        ".label{font-size:14px;font-weight:600}",
        ".small{font-size:12px;fill:#627282}",
        "</style>",
        '<rect width="1120" height="760" fill="#f7f9fc"/>',
        '<rect x="34" y="34" width="1052" height="88" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="58" y="72" class="title">G-S03 - TrackDefinition candidat</text>',
        f'<text x="58" y="100" class="subtitle">Validation C-S01: {"succès" if summary["validation"]["success"] else "échec"} · statut {escape(summary["status"])}</text>',
        f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        f'<polyline points="{polyline}" fill="none" stroke="#2f5f9f" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>',
    ]
    for index, point in enumerate(centerline):
        x, y = mp(point)
        fill = "#2f5f9f" if index % 2 == 0 else "#7aa6d8"
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{fill}"/>')
        parts.append(f'<text x="{x + 8:.1f}" y="{y - 8:.1f}" class="small">{escape(point["id"])}</text>')

    for checkpoint in checkpoints:
        point = points_by_id[checkpoint["centerlinePointId"]]
        x, y = mp(point)
        color = "#d1495b" if checkpoint["id"] == "finish" else "#e9a23b"
        parts.append(f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="{color}" transform="rotate(45 {x:.1f} {y:.1f})"/>')
        parts.append(f'<text x="{x + 12:.1f}" y="{y + 4:.1f}" class="small">{escape(checkpoint["id"])}</text>')

    legend_x = 760
    notes = summary["conversionNotes"]
    parts.extend(
        [
            f'<rect x="{legend_x}" y="150" width="310" height="380" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            f'<text x="{legend_x + 22}" y="184" class="label">Résumé conversion</text>',
            f'<text x="{legend_x + 22}" y="222" class="small">Échelle: 1 m = {notes["scalePolicy"]["editorUnitsPerMetre"]} unités</text>',
            f'<text x="{legend_x + 22}" y="250" class="small">Clés vectorielles: {notes["centerlinePolicy"]["rawVectorKeys"]}</text>',
            f'<text x="{legend_x + 22}" y="278" class="small">Points échantillonnés: {notes["centerlinePolicy"]["convertedCenterlinePoints"]}</text>',
            f'<text x="{legend_x + 22}" y="306" class="small">Direction: {escape(track["direction"])}</text>',
            f'<text x="{legend_x + 22}" y="334" class="small">Checkpoints: {len(checkpoints)}</text>',
            f'<text x="{legend_x + 22}" y="382" class="label">Validation C-S01</text>',
            f'<text x="{legend_x + 22}" y="416" class="small">Longueur: {preprocessed.get("totalLengthM", 0):.2f} m</text>',
            f'<text x="{legend_x + 22}" y="444" class="small">Largeur min: {preprocessed.get("minTotalWidthM", 0):.2f} m</text>',
            f'<text x="{legend_x + 22}" y="472" class="small">Courbure max: {preprocessed.get("maxAbsCurvature", 0):.5f} 1/m</text>',
            '<text x="56" y="718" class="small">Visualisation en mètres après conversion expérimentale. Les losanges indiquent les checkpoints projetés sur le point central le plus proche.</text>',
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
