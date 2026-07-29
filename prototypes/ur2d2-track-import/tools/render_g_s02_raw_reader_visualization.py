#!/usr/bin/env python3
"""Render G-S02 raw reader geometry and object candidates as SVG."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RAW_PATH = RESULTS_DIR / "g_s02_raw_reader.json"
SVG_PATH = RESULTS_DIR / "G_S02_RAW_READER_VISUALIZATION.svg"


def load_result() -> dict[str, Any]:
    if not RAW_PATH.exists():
        return {"status": "awaiting-raw-reader-run", "rawFixtures": []}
    return json.loads(RAW_PATH.read_text(encoding="utf-8"))


def choose_fixture(result: dict[str, Any]) -> dict[str, Any] | None:
    fixtures = result.get("rawFixtures", [])
    for fixture in fixtures:
        if fixture.get("fixture") == "T05_start_and_checkpoints":
            return fixture
    return fixtures[-1] if fixtures else None


def collect_points(fixture: dict[str, Any]) -> list[dict[str, float]]:
    geometry = fixture.get("pairedGeometryCandidates", {})
    points = []
    for key in ["roadControlPoints", "generatedEdgeOrMeshPoints", "sampledLinePoints"]:
        points.extend(geometry.get(key, []))
    for checkpoint in fixture.get("checkpointCandidates", []):
        points.append({"x": checkpoint["x"], "y": checkpoint["y"]})
    return points


def transform(points: list[dict[str, float]], width: int, height: int, pad: int):
    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)

    def map_point(point: dict[str, float]) -> tuple[float, float]:
        x = pad + (point["x"] - min_x) * scale
        y = height - pad - (point["y"] - min_y) * scale
        return x, y

    return map_point


def polyline(points: list[dict[str, float]], mapper, color: str, width: int, close: bool = False) -> str:
    if not points:
        return ""
    coords = [mapper(point) for point in points]
    if close and len(coords) > 2:
        coords.append(coords[0])
    attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    return f'<polyline points="{attr}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'


def render_svg(result: dict[str, Any]) -> str:
    fixture = choose_fixture(result)
    width = 1180
    height = 760
    plot_x = 50
    plot_y = 142
    plot_w = 700
    plot_h = 560
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Segoe UI,Arial,sans-serif;fill:#25313f}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6b7a}",
        ".label{font-size:14px;font-weight:600}",
        ".small{font-size:12px;fill:#627282}",
        "</style>",
        '<rect width="1180" height="760" fill="#f7f9fc"/>',
        '<rect x="34" y="34" width="1112" height="84" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="58" y="72" class="title">G-S02 - Lecteur brut UR2D2 .sav</text>',
        f'<text x="58" y="99" class="subtitle">Statut: {escape(result.get("status", "unknown"))}</text>',
    ]
    if fixture is None:
        parts.extend(
            [
                '<rect x="260" y="250" width="660" height="120" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
                '<text x="310" y="304" class="label">Aucune fixture brute disponible</text>',
                "</svg>",
            ]
        )
        return "\n".join(parts)

    points = collect_points(fixture)
    mapper = transform(points, plot_w, plot_h, 38)

    def mp(point: dict[str, float]) -> tuple[float, float]:
        x, y = mapper(point)
        return x + plot_x, y + plot_y

    geometry = fixture.get("pairedGeometryCandidates", {})
    road = geometry.get("roadControlPoints", [])
    edge = geometry.get("generatedEdgeOrMeshPoints", [])
    sampled = geometry.get("sampledLinePoints", [])
    checkpoints = fixture.get("checkpointCandidates", [])

    parts.extend(
        [
            f'<text x="{plot_x}" y="134" class="label">Fixture affichée: {escape(fixture.get("fixture", "?"))}</text>',
            f'<rect x="{plot_x}" y="{plot_y}" width="{plot_w}" height="{plot_h}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            f'<g transform="translate({plot_x},{plot_y})">',
            polyline(edge, mapper, "#9cc7b5", 3, False),
            polyline(sampled, mapper, "#e9a23b", 2, False),
            polyline(road, mapper, "#2f5f9f", 4, True),
            "</g>",
        ]
    )
    for index, point in enumerate(road):
        x, y = mp(point)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#2f5f9f"/>')
        parts.append(f'<text x="{x + 7:.1f}" y="{y - 7:.1f}" class="small">R{index}</text>')
    for checkpoint in checkpoints:
        x, y = mp({"x": checkpoint["x"], "y": checkpoint["y"]})
        label = escape(checkpoint.get("label") or "checkpoint")
        parts.extend(
            [
                f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="#d1495b" transform="rotate(45 {x:.1f} {y:.1f})"/>',
                f'<text x="{x + 10:.1f}" y="{y + 4:.1f}" class="small">{label}</text>',
            ]
        )

    legend_x = 800
    inventory = result.get("elementInventory", {})
    inventory_items = inventory.get("items", [])
    ok_count = sum(1 for item in inventory_items if item.get("detected") == item.get("expected"))
    parts.extend(
        [
            f'<rect x="{legend_x}" y="142" width="328" height="476" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            f'<text x="{legend_x + 24}" y="176" class="label">Structures candidates</text>',
            f'<circle cx="{legend_x + 30}" cy="212" r="5" fill="#2f5f9f"/><text x="{legend_x + 48}" y="217" class="small">Tableaux 0/1: route control x/y</text>',
            f'<line x1="{legend_x + 24}" y1="244" x2="{legend_x + 46}" y2="244" stroke="#9cc7b5" stroke-width="4"/><text x="{legend_x + 58}" y="249" class="small">Tableaux 7/8: enveloppe/mesh</text>',
            f'<line x1="{legend_x + 24}" y1="276" x2="{legend_x + 46}" y2="276" stroke="#e9a23b" stroke-width="3"/><text x="{legend_x + 58}" y="281" class="small">Tableaux 13/14: ligne échantillonnée</text>',
            f'<rect x="{legend_x + 24}" y="304" width="12" height="12" fill="#d1495b" transform="rotate(45 {legend_x + 30} 310)"/><text x="{legend_x + 48}" y="315" class="small">Checkpoints candidats</text>',
            f'<text x="{legend_x + 24}" y="364" class="small">Tableaux extraits: {fixture["countedFloatArrayRegion"]["arrayCount"]}</text>',
            f'<text x="{legend_x + 24}" y="390" class="small">Points route: {len(road)}</text>',
            f'<text x="{legend_x + 24}" y="416" class="small">Points échantillonnés: {len(sampled)}</text>',
            f'<text x="{legend_x + 24}" y="442" class="small">Checkpoints: {len(checkpoints)}</text>',
            f'<text x="{legend_x + 24}" y="468" class="small">Région tableaux: {fixture["countedFloatArrayRegion"]["startHexOffset"]}..{fixture["countedFloatArrayRegion"]["endHexOffset"]}</text>',
            f'<text x="{legend_x + 24}" y="514" class="label">Inventaire attendu: {ok_count}/{len(inventory_items)}</text>',
            f'<text x="{legend_x + 24}" y="542" class="small">Route 4, IA 3, checkpoints 3: lus</text>',
            f'<text x="{legend_x + 24}" y="568" class="small">Mur, sable, arbres: blocs lus</text>',
            f'<text x="{legend_x + 24}" y="594" class="small">Pitlane: détectée, rôles entrée/sortie candidats</text>',
            '<text x="50" y="734" class="small">Les coordonnées sont en unités éditeur brutes. Aucune échelle SI ni orientation finale n’est appliquée à ce stade.</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(render_svg(load_result()), encoding="utf-8")
    print(f"Wrote: {SVG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
