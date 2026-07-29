#!/usr/bin/env python3
"""Render H-S01 runtime/G comparison as SVG."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SUMMARY_PATH = RESULTS_DIR / "h_s01_runtime_g_comparison.json"
SVG_PATH = RESULTS_DIR / "H_S01_RUNTIME_G_COMPARISON_VISUALIZATION.svg"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def render_svg(summary: dict[str, Any]) -> str:
    width = 1180
    height = 720
    checks = summary["checks"]
    y = 168
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Segoe UI,Arial,sans-serif;fill:#25313f}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6b7a}",
        ".label{font-size:14px;font-weight:700}",
        ".small{font-size:12px;fill:#627282}",
        ".mono{font-family:Consolas,monospace;font-size:12px;fill:#334155}",
        "</style>",
        '<rect width="1180" height="720" fill="#f7f9fc"/>',
        '<rect x="34" y="34" width="1112" height="86" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="58" y="72" class="title">H-S01 - Comparaison runtime / G</text>',
        f'<text x="58" y="100" class="subtitle">Fixture {html.escape(summary["runtimeFixture"])} - statut: {html.escape(summary["status"])}</text>',
        '<rect x="44" y="144" width="350" height="360" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="68" y="180" class="label">Contrôles</text>',
    ]
    for key, value in checks.items():
        color = "#2a9d8f" if value else "#d1495b"
        parts.extend(
            [
                f'<circle cx="76" cy="{y + 34}" r="6" fill="{color}"/>',
                f'<text x="92" y="{y + 39}" class="small">{html.escape(key)}</text>',
            ]
        )
        y += 36

    parts.extend(
        [
            '<rect x="416" y="144" width="338" height="360" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            '<text x="440" y="180" class="label">Clés route G dans track.data</text>',
            '<text x="440" y="214" class="small">Chaque ligne indique les occurrences exactes x/y/paire.</text>',
        ]
    )
    y = 246
    for item in summary["roadKeyPresenceInRuntime"]:
        pair_color = "#2a9d8f" if item["xyPairOccurrences"] > 0 else "#e9a23b"
        parts.extend(
            [
                f'<rect x="440" y="{y - 18}" width="286" height="26" rx="4" fill="#f4f7fb" stroke="#e2e8f0"/>',
                f'<text x="452" y="{y}" class="mono">K{item["index"]}: x {item["xOccurrences"]} / y {item["yOccurrences"]}</text>',
                f'<circle cx="712" cy="{y - 5}" r="6" fill="{pair_color}"/>',
            ]
        )
        y += 42

    parts.extend(
        [
            '<rect x="776" y="144" width="360" height="360" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            '<text x="800" y="180" class="label">Checkpoints runtime</text>',
            '<text x="800" y="214" class="small">Comparaison aux checkpoints G, en unités éditeur.</text>',
        ]
    )
    y = 250
    for record in summary["compactCheckpointRecords"]:
        comparison = record["editorComparison"]
        color = "#2a9d8f" if comparison["distanceEditorUnits"] <= 0.01 else "#e9a23b"
        parts.extend(
            [
                f'<circle cx="810" cy="{y - 5}" r="7" fill="{color}"/>',
                f'<text x="828" y="{y}" class="mono">{html.escape(comparison["editorLabel"])} @ {record["x"]:.1f},{record["y"]:.1f}</text>',
                f'<text x="828" y="{y + 20}" class="small">rot runtime = éditeur - 90°, delta {comparison["rotationRuntimeMinusEditorMinus90Deg"]:.3f}°</text>',
            ]
        )
        y += 62

    hash_match = summary["editorSavHashComparison"]["exactMatchFixture"] or "aucun match exact"
    info = " ; ".join(summary["trackInfoStrings"][:6])
    parts.extend(
        [
            '<rect x="44" y="530" width="1092" height="132" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            '<text x="68" y="566" class="label">Lecture</text>',
            f'<text x="68" y="596" class="small">track_info.data: {html.escape(info)}</text>',
            f'<text x="68" y="626" class="small">track_editor.sav vs fixtures G: {html.escape(hash_match)}</text>',
            '<text x="68" y="650" class="small">H-S02 peut lire track.data et track_info.data ; track_editor.sav sert de témoin de comparaison.</text>',
            "</svg>",
            "",
        ]
    )
    return "\n".join(parts)


def main() -> int:
    if not SUMMARY_PATH.exists():
        raise RuntimeError("Run run_h_s01_runtime_g_comparison.py before rendering H-S01")
    SVG_PATH.write_text(render_svg(load_json(SUMMARY_PATH)), encoding="utf-8", newline="\n")
    print(f"Wrote: {SVG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
