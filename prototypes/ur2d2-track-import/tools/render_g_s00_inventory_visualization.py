#!/usr/bin/env python3
"""Render a compact SVG visualization for the G-S00 UR2D2 inventory."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SUMMARY_PATH = RESULTS_DIR / "g_s00_inventory_summary.json"
SVG_PATH = RESULTS_DIR / "G_S00_INVENTORY_VISUALIZATION.svg"


def load_summary() -> dict[str, Any]:
    if not SUMMARY_PATH.exists():
        return {
            "scenario": "G-S00",
            "status": "awaiting-inventory-run",
            "observedFixtureCount": 0,
            "expectedFixtureCount": 8,
            "fixtures": [],
            "comparisons": [],
        }
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def fixture_color(fixture: dict[str, Any]) -> str:
    if not fixture.get("exists"):
        return "#d8dee7"
    if fixture.get("fileCount", 0) == 0:
        return "#f4b860"
    return "#2a9d8f"


def comparison_lookup(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {comparison["to"]: comparison for comparison in summary.get("comparisons", [])}


def render_svg(summary: dict[str, Any]) -> str:
    fixtures = summary.get("fixtures", [])
    comparisons = comparison_lookup(summary)
    width = 1160
    row_h = 74
    top = 150
    height = max(520, top + len(fixtures) * row_h + 90)
    max_files = max([fixture.get("fileCount", 0) for fixture in fixtures] + [1])
    max_delta = max(
        [
            comparison.get("addedCount", 0) + comparison.get("modifiedCount", 0) + comparison.get("removedCount", 0)
            for comparison in comparisons.values()
        ]
        + [1]
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Segoe UI,Arial,sans-serif;fill:#25313f}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6b7a}",
        ".label{font-size:14px;font-weight:600}",
        ".small{font-size:12px;fill:#627282}",
        ".axis{stroke:#c9d2dd;stroke-width:1}",
        "</style>",
        '<rect width="1160" height="100%" fill="#f7f9fc"/>',
        '<rect x="34" y="34" width="1092" height="84" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="58" y="72" class="title">G-S00 - Inventaire UR2D2</text>',
        f'<text x="58" y="99" class="subtitle">Statut: {escape(summary.get("status", "unknown"))} · fixtures observées {summary.get("observedFixtureCount", 0)} / {summary.get("expectedFixtureCount", 8)}</text>',
        '<text x="58" y="142" class="small">Fixture</text>',
        '<text x="330" y="142" class="small">Couverture fichiers</text>',
        '<text x="650" y="142" class="small">Différence vs fixture précédente</text>',
        '<text x="940" y="142" class="small">Signatures</text>',
    ]

    if not fixtures:
        parts.extend(
            [
                '<rect x="250" y="230" width="660" height="120" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
                '<text x="300" y="284" class="label">Aucun inventaire disponible</text>',
                '<text x="300" y="314" class="small">Lancer run_g_s00_inventory.py après avoir préparé les fixtures.</text>',
            ]
        )
    for index, fixture in enumerate(fixtures):
        y = top + index * row_h
        color = fixture_color(fixture)
        file_count = fixture.get("fileCount", 0)
        file_bar = int(230 * (file_count / max_files))
        comparison = comparisons.get(fixture.get("fixture"), {})
        added = comparison.get("addedCount", 0)
        modified = comparison.get("modifiedCount", 0)
        removed = comparison.get("removedCount", 0)
        delta_total = added + modified + removed
        delta_bar = int(230 * (delta_total / max_delta))
        signatures = ", ".join(fixture.get("signatures", {}).keys()) or "-"

        parts.extend(
            [
                f'<line x1="48" y1="{y + row_h - 10}" x2="1112" y2="{y + row_h - 10}" class="axis"/>',
                f'<rect x="58" y="{y + 13}" width="18" height="18" rx="3" fill="{color}"/>',
                f'<text x="88" y="{y + 28}" class="label">{escape(fixture.get("fixture", "?"))}</text>',
                f'<text x="88" y="{y + 50}" class="small">{escape(fixture.get("purpose", ""))}</text>',
                f'<rect x="330" y="{y + 14}" width="230" height="16" rx="4" fill="#e5ebf2"/>',
                f'<rect x="330" y="{y + 14}" width="{file_bar}" height="16" rx="4" fill="#457b9d"/>',
                f'<text x="572" y="{y + 28}" class="small">{file_count} fichiers</text>',
                f'<rect x="650" y="{y + 14}" width="230" height="16" rx="4" fill="#e5ebf2"/>',
                f'<rect x="650" y="{y + 14}" width="{delta_bar}" height="16" rx="4" fill="#e76f51"/>',
                f'<text x="892" y="{y + 28}" class="small">+{added} / ~{modified} / -{removed}</text>',
                f'<text x="940" y="{y + 28}" class="small">{escape(signatures[:42])}</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="58" y="{height - 42}" class="small">Légende: vert = fixture présente, gris = manquante, orange = dossier présent sans fichier. Les barres de différence affichent ajouts / modifications / suppressions.</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = load_summary()
    SVG_PATH.write_text(render_svg(summary), encoding="utf-8")
    print(f"Wrote: {SVG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
