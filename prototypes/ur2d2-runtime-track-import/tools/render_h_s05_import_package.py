#!/usr/bin/env python3
"""Render H-S05 import package summary as SVG."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SUMMARY_PATH = RESULTS_DIR / "h_s05_import_package_summary.json"
PACKAGE_PATH = RESULTS_DIR / "h_s05_import_package.json"
OUTPUT_PATH = RESULTS_DIR / "H_S05_IMPORT_PACKAGE_VISUALIZATION.svg"

WIDTH = 1280
HEIGHT = 760


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text(x: float, y: float, value: str, size: int = 14, weight: int = 400, fill: str = "#1f2937") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'
    )


def box(x: float, y: float, w: float, h: float, title: str, subtitle: str, color: str) -> str:
    return "\n".join(
        [
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" fill="#ffffff" stroke="{color}" stroke-width="2"/>',
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="34" rx="8" fill="{color}" opacity="0.12"/>',
            text(x + 18, y + 23, title, 14, 700, color),
            text(x + 18, y + 58, subtitle, 12, 500, "#475569"),
        ]
    )


def check_row(x: float, y: float, label: str, ok: bool) -> str:
    color = "#27ae60" if ok else "#d1495b"
    mark = "OK" if ok else "KO"
    return (
        f'<circle cx="{x:.1f}" cy="{y - 5:.1f}" r="8" fill="{color}" opacity="0.18"/>'
        + text(x - 7, y - 1, mark, 7, 800, color)
        + text(x + 18, y, label, 12, 500, "#475569")
    )


def arrow(x1: float, y1: float, x2: float, y2: float) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        'stroke="#94a3b8" stroke-width="2.2" marker-end="url(#arrow-h05)"/>'
    )


def render(summary: dict[str, Any], package: dict[str, Any]) -> str:
    s = summary["summary"]
    mapping = package["runtimeRendering"]["coordinateMapping"]
    checks = summary["checks"]
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<defs><marker id="arrow-h05" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#94a3b8"/></marker></defs>',
        '<rect x="32" y="28" width="1216" height="90" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        text(56, 66, "H-S05 - Paquet d'import prêt simulation", 26, 700),
        text(56, 96, f"Statut : {summary['status']} | SHA contenu : {summary['packageContentSha256'][:16]} | track.data utilisé : non", 14, 500, "#64748b"),
        box(56, 158, 250, 116, "Source .sav", "piste, pitlane, murs, checkpoints", "#2f5f9f"),
        box(56, 328, 250, 116, "track_info.data", "nom, pays, type, conditions", "#64748b"),
        box(56, 498, 250, 116, "PNG runtime", "fond de carte et calques visuels", "#d48a00"),
        arrow(306, 216, 398, 216),
        arrow(306, 386, 398, 386),
        arrow(306, 556, 398, 556),
        box(398, 158, 300, 286, "UR2D2ImportedTrackPackage", f"{s['centerlinePoints']} points | {s['totalLengthM']:.3f} m | {s['minTotalWidthM']:.1f} m", "#27ae60"),
        text(426, 244, f"Pitlane : {s['pitlaneLaneCount']} voies", 13, 600, "#475569"),
        text(426, 274, f"Murs : {s['wallCount']}", 13, 600, "#475569"),
        text(426, 304, f"Checkpoints : {s['checkpointCount']}", 13, 600, "#475569"),
        text(426, 334, f"Fond : {s['preferredBackground']}", 13, 600, "#475569"),
        text(426, 364, f"Mapping : {mapping['scaleX']:.4f} x {mapping['scaleY']:.4f}", 13, 600, "#475569"),
        arrow(698, 302, 796, 302),
        box(796, 158, 376, 286, "H-S06", "simulation voiture + rendu sur fond runtime", "#8b5fbf"),
        text(824, 244, "Entrée simulation :", 14, 700, "#475569"),
        text(844, 274, "TrackDefinition v0.1", 13, 600, "#475569"),
        text(844, 304, "simulationExtras", 13, 600, "#475569"),
        text(844, 334, "runtimeRendering", 13, 600, "#475569"),
        text(824, 382, "Objectif suivant :", 14, 700, "#475569"),
        text(844, 412, "faire rouler la QFC55", 13, 600, "#475569"),
        '<rect x="398" y="498" width="774" height="116" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        text(426, 532, "Contrôles", 16, 700),
    ]
    x = 426
    y = 566
    for index, (key, value) in enumerate(checks.items()):
        row_x = x + (index % 4) * 184
        row_y = y + (index // 4) * 34
        parts.append(check_row(row_x, row_y, key, bool(value)))
    parts.extend(
        [
            text(56, 694, "H-S05 fige le contrat d'import : C consomme TrackDefinition, la simulation avancée consomme les extras, le rendu consomme les références PNG.", 13, 500, "#64748b"),
            "</svg>",
        ]
    )
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--package", type=Path, default=PACKAGE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = load_json(args.summary)
    package = load_json(args.package)
    args.output.write_text(render(summary, package), encoding="utf-8", newline="\n")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
