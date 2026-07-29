#!/usr/bin/env python3
"""Render the G-S01 differential analysis as a compact SVG."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
ANALYSIS_PATH = RESULTS_DIR / "g_s01_differential_analysis.json"
SVG_PATH = RESULTS_DIR / "G_S01_DIFFERENTIAL_ANALYSIS_VISUALIZATION.svg"


def load_analysis() -> dict[str, Any]:
    if not ANALYSIS_PATH.exists():
        return {"status": "awaiting-analysis-run", "fixtures": [], "comparisons": []}
    return json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))


def render_svg(analysis: dict[str, Any]) -> str:
    fixtures = analysis.get("fixtures", [])
    comparisons = analysis.get("comparisons", [])
    width = 1220
    top = 150
    row_h = 66
    height = max(540, top + max(len(fixtures), len(comparisons)) * row_h + 100)
    max_size = max([fixture.get("sizeBytes", 0) for fixture in fixtures] + [1])
    max_delta = max([abs(comparison.get("deltaBytes", 0)) for comparison in comparisons] + [1])

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Segoe UI,Arial,sans-serif;fill:#25313f}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6b7a}",
        ".label{font-size:13px;font-weight:600}",
        ".small{font-size:12px;fill:#627282}",
        ".axis{stroke:#c9d2dd;stroke-width:1}",
        "</style>",
        '<rect width="1220" height="100%" fill="#f7f9fc"/>',
        '<rect x="34" y="34" width="1152" height="84" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="58" y="72" class="title">G-S01 - Analyse différentielle .sav</text>',
        f'<text x="58" y="99" class="subtitle">Statut: {escape(analysis.get("status", "unknown"))} · {len(fixtures)} fixtures · sauvegardes éditeur, pas exports finaux</text>',
        '<text x="58" y="142" class="small">Fixture</text>',
        '<text x="320" y="142" class="small">Taille fichier</text>',
        '<text x="610" y="142" class="small">Delta vs précédent</text>',
        '<text x="880" y="142" class="small">Indices textuels</text>',
    ]

    comparisons_by_to = {comparison["to"]: comparison for comparison in comparisons}
    for index, fixture in enumerate(fixtures):
        y = top + index * row_h
        size = fixture.get("sizeBytes", 0)
        size_w = int(240 * size / max_size)
        comparison = comparisons_by_to.get(fixture.get("fixture"))
        delta = comparison.get("deltaBytes", 0) if comparison else 0
        delta_w = int(210 * abs(delta) / max_delta)
        strings = ", ".join(item["value"] for item in fixture.get("strings", [])[:3]) or "-"
        parts.extend(
            [
                f'<line x1="48" y1="{y + row_h - 10}" x2="1172" y2="{y + row_h - 10}" class="axis"/>',
                f'<text x="58" y="{y + 28}" class="label">{escape(fixture.get("fixture", "?"))}</text>',
                f'<rect x="320" y="{y + 14}" width="240" height="16" rx="4" fill="#e5ebf2"/>',
                f'<rect x="320" y="{y + 14}" width="{size_w}" height="16" rx="4" fill="#2a9d8f"/>',
                f'<text x="574" y="{y + 28}" class="small">{size} o</text>',
                f'<rect x="610" y="{y + 14}" width="210" height="16" rx="4" fill="#e5ebf2"/>',
                f'<rect x="610" y="{y + 14}" width="{delta_w}" height="16" rx="4" fill="#e76f51"/>',
                f'<text x="834" y="{y + 28}" class="small">{delta:+d} o</text>',
                f'<text x="880" y="{y + 28}" class="small">{escape(strings[:54])}</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="58" y="{height - 42}" class="small">Lecture: les tailles augmentent à chaque ajout fonctionnel ; les chaînes lisibles localisent déjà route, murs, checkpoints, stands et surfaces.</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(render_svg(load_analysis()), encoding="utf-8")
    print(f"Wrote: {SVG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
