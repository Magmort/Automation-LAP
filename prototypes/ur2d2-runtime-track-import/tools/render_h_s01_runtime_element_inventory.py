#!/usr/bin/env python3
"""Render H-S01b runtime element inventory as a compact SVG."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SUMMARY_PATH = RESULTS_DIR / "h_s01_runtime_element_inventory.json"
OUTPUT_PATH = RESULTS_DIR / "H_S01_RUNTIME_ELEMENT_INVENTORY_VISUALIZATION.svg"


STATUS_COLORS = {
    "localized-sampled-track-data": "#2f80ed",
    "localized-runtime-records": "#27ae60",
    "localized-token-and-sampled-connectors": "#9b51e0",
    "editor-vector-and-runtime-layer": "#d48a00",
    "editor-vector-and-baked-runtime-raster": "#6b7280",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text(x: float, y: float, value: str, size: int = 14, weight: int = 400, fill: str = "#1f2937") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'
    )


def pill(x: float, y: float, label: str, fill: str) -> str:
    width = max(120, len(label) * 7 + 22)
    return (
        f'<rect x="{x:.1f}" y="{y - 16:.1f}" width="{width:.1f}" height="24" rx="12" fill="{fill}" opacity="0.14"/>'
        f'<circle cx="{x + 12:.1f}" cy="{y - 4:.1f}" r="4" fill="{fill}"/>'
        + text(x + 22, y, label, 12, 600, fill)
    )


def render(summary: dict[str, Any]) -> str:
    width = 1200
    row_h = 54
    top = 144
    height = top + row_h * len(summary["items"]) + 150
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<rect x="32" y="28" width="1136" height="86" rx="8" fill="#ffffff" stroke="#e5e7eb"/>',
        text(56, 64, "H-S01b - Inventaire des éléments de la piste runtime", 24, 700),
        text(56, 92, f"Statut : {summary['status']} | Fixture : {summary['runtimeFixture']}", 14, 500, "#64748b"),
    ]

    headers = ["Élément", "Attendu", "Lu .sav", "Localisation runtime", "Confiance"]
    xs = [56, 432, 520, 618, 1000]
    parts.append('<rect x="32" y="124" width="1136" height="34" rx="6" fill="#e5eef7"/>')
    for x, header in zip(xs, headers):
        parts.append(text(x, 146, header, 13, 700, "#334155"))

    for index, item in enumerate(summary["items"]):
        y = top + index * row_h
        fill = "#ffffff" if index % 2 == 0 else "#f1f5f9"
        parts.append(f'<rect x="32" y="{y:.1f}" width="1136" height="{row_h}" fill="{fill}" stroke="#e5e7eb"/>')
        color = STATUS_COLORS.get(item["runtimeStatus"], "#111827")
        parts.append(text(xs[0], y + 32, item["label"], 15, 650))
        parts.append(text(xs[1], y + 32, str(item["expected"]), 15, 600))
        parts.append(text(xs[2], y + 32, str(item["detectedInEditorSav"]), 15, 600))
        parts.append(pill(xs[3], y + 32, item["runtimeStatus"], color))
        parts.append(text(xs[4], y + 32, item["confidence"], 15, 650, color))

    legend_y = top + row_h * len(summary["items"]) + 36
    parts.append(text(56, legend_y, "Lecture", 16, 700))
    legend = [
        ("track.data échantillonné", "#2f80ed"),
        ("records runtime", "#27ae60"),
        ("token + connecteurs", "#9b51e0"),
        ("calque runtime", "#d48a00"),
        ("raster composite + .sav", "#6b7280"),
    ]
    lx = 56
    for label, color in legend:
        parts.append(pill(lx, legend_y + 34, label, color))
        lx += max(180, len(label) * 8 + 50)

    parts.append(text(56, height - 38, "Conclusion : H-S02 peut utiliser une stratégie hybride track.data + track_info.data + track_editor.sav.", 14, 600, "#475569"))
    parts.append("</svg>")
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = load_json(args.summary)
    args.output.write_text(render(summary), encoding="utf-8", newline="\n")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
