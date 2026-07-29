#!/usr/bin/env python3
"""Render a compact SVG visualization for H-S00 runtime track inventory."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SUMMARY_PATH = RESULTS_DIR / "h_s00_runtime_inventory_summary.json"
SVG_PATH = RESULTS_DIR / "H_S00_RUNTIME_INVENTORY_VISUALIZATION.svg"


def load_summary() -> dict[str, Any]:
    if not SUMMARY_PATH.exists():
        return {"status": "awaiting-inventory-run", "fixtureCount": 0, "totalFileCount": 0, "fixtures": []}
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def render_svg(summary: dict[str, Any]) -> str:
    fixtures = summary.get("fixtures", [])
    width = 1120
    top = 150
    row_h = 72
    height = max(470, top + max(1, len(fixtures)) * row_h + 96)
    max_files = max([fixture.get("fileCount", 0) for fixture in fixtures] + [1])
    max_size = max([fixture.get("totalSizeBytes", 0) for fixture in fixtures] + [1])

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
        '<rect width="1120" height="100%" fill="#f7f9fc"/>',
        '<rect x="34" y="34" width="1052" height="84" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="58" y="72" class="title">H-S00 - Inventaire tracks runtime UR2D2</text>',
        f'<text x="58" y="99" class="subtitle">Statut: {escape(summary.get("status", "unknown"))} · fixtures {summary.get("fixtureCount", 0)} · fichiers {summary.get("totalFileCount", 0)}</text>',
        '<text x="58" y="142" class="small">Fixture</text>',
        '<text x="360" y="142" class="small">Nombre de fichiers</text>',
        '<text x="650" y="142" class="small">Taille totale</text>',
        '<text x="900" y="142" class="small">Signatures</text>',
    ]

    if not fixtures:
        parts.extend(
            [
                '<rect x="248" y="218" width="624" height="124" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
                '<text x="294" y="274" class="label">Aucun fichier de track runtime disponible</text>',
                '<text x="294" y="304" class="small">Déposer les pistes dans fixtures/source puis relancer H-S00.</text>',
            ]
        )

    for index, fixture in enumerate(fixtures):
        y = top + index * row_h
        file_w = int(220 * fixture.get("fileCount", 0) / max_files)
        size_w = int(200 * fixture.get("totalSizeBytes", 0) / max_size)
        signatures = ", ".join(fixture.get("signatures", {}).keys()) or "-"
        parts.extend(
            [
                f'<line x1="48" y1="{y + row_h - 10}" x2="1072" y2="{y + row_h - 10}" class="axis"/>',
                f'<text x="58" y="{y + 28}" class="label">{escape(fixture.get("fixture", "?"))}</text>',
                f'<text x="58" y="{y + 50}" class="small">{escape(fixture.get("sourceKind", ""))}</text>',
                f'<rect x="360" y="{y + 14}" width="220" height="16" rx="4" fill="#e5ebf2"/>',
                f'<rect x="360" y="{y + 14}" width="{file_w}" height="16" rx="4" fill="#457b9d"/>',
                f'<text x="594" y="{y + 28}" class="small">{fixture.get("fileCount", 0)}</text>',
                f'<rect x="650" y="{y + 14}" width="200" height="16" rx="4" fill="#e5ebf2"/>',
                f'<rect x="650" y="{y + 14}" width="{size_w}" height="16" rx="4" fill="#2a9d8f"/>',
                f'<text x="862" y="{y + 28}" class="small">{fixture.get("totalSizeBytes", 0)} o</text>',
                f'<text x="900" y="{y + 28}" class="small">{escape(signatures[:36])}</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="58" y="{height - 42}" class="small">H complète G : cette vue concerne les fichiers de piste finis/runtime, pas les sauvegardes éditeur .sav.</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(render_svg(load_summary()), encoding="utf-8")
    print(f"Wrote: {SVG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
