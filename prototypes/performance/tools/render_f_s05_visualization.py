#!/usr/bin/env python3
"""Render F-S05 performance synthesis as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1280
HEIGHT = 860
COLORS = {
    "paper": "#f7f7f3",
    "panel": "#ffffff",
    "line": "#c9c9c2",
    "ink": "#222222",
    "muted": "#5f625d",
    "green": "#2f9d68",
    "blue": "#2f7ed8",
    "orange": "#d2842f",
    "purple": "#6f4bb2",
    "teal": "#2b8c91",
}


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def render_cards(summary: dict[str, Any]) -> list[str]:
    params = summary["decision"]["candidateParameters"]
    cards = [
        ("Decision", "validee avec reserves", COLORS["green"]),
        ("Cible voitures", "12 a 20", COLORS["blue"]),
        ("Tick", "60 Hz", COLORS["teal"]),
        ("Replay", "4 Hz", COLORS["purple"]),
    ]
    elements = []
    for index, (label, value, color) in enumerate(cards):
        x = 76 + index * 286
        y = 136
        elements.append(f'<rect x="{x}" y="{y}" width="260" height="72" rx="7" fill="#ffffff" stroke="{COLORS["line"]}" />')
        elements.append(f'<text x="{x + 16}" y="{y + 28}" font-size="13" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
        elements.append(f'<text x="{x + 244}" y="{y + 50}" font-size="22" font-weight="700" fill="{color}" text-anchor="end">{html.escape(value)}</text>')
    elements.append(f'<text x="80" y="236" font-size="13" fill="{COLORS["muted"]}">20 voitures: F-S02 {params["target20RealtimeFactorMean"]:.1f}x temps reel, F-S03 {params["target20AcceleratedFactorMean"]:.1f}x accelere, replay 4 Hz {params["target20ReplayShareAt4Hz"] * 100.0:.1f}% du tick.</text>')
    return elements


def render_evidence(summary: dict[str, Any]) -> list[str]:
    params = summary["decision"]["candidateParameters"]
    bars = [
        ("F-S02 temps reel", params["target20RealtimeFactorMean"], 80.0, COLORS["blue"], "facteur"),
        ("F-S03 accelere", params["target20AcceleratedFactorMean"], 40.0, COLORS["green"], "facteur"),
        ("F-S04 replay 4 Hz", params["target20ReplayShareAt4Hz"] * 100.0, 12.0, COLORS["purple"], "% tick"),
        ("F-S04 replay 20 Hz", params["target20ReplayShareAt20Hz"] * 100.0, 25.0, COLORS["orange"], "% tick"),
    ]
    elements = ['<text x="84" y="314" font-size="17" font-weight="700">Preuves principales</text>']
    x = 286
    y = 348
    width = 760
    for index, (label, value, scale, color, unit) in enumerate(bars):
        row_y = y + index * 64
        bar_w = min(width, width * value / scale)
        elements.append(f'<text x="84" y="{row_y + 22}" font-size="13" font-weight="700">{html.escape(label)}</text>')
        elements.append(f'<rect x="{x}" y="{row_y}" width="{width}" height="28" rx="5" fill="#ecece7" />')
        elements.append(f'<rect x="{x}" y="{row_y}" width="{bar_w:.2f}" height="28" rx="5" fill="{color}" />')
        elements.append(f'<text x="{x + width + 18}" y="{row_y + 20}" font-size="13">{value:.1f} {unit}</text>')
    return elements


def render_risks(summary: dict[str, Any]) -> list[str]:
    elements = ['<text x="84" y="650" font-size="17" font-weight="700">Reserves de cloture</text>']
    for index, risk in enumerate(summary["decision"]["residualRisks"]):
        y = 684 + index * 28
        elements.append(f'<circle cx="92" cy="{y - 4}" r="4" fill="{COLORS["orange"]}" />')
        elements.append(f'<text x="108" y="{y}" font-size="13" fill="{COLORS["ink"]}">{html.escape(risk)}</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">F-S05 performance synthesis</title>',
            '<desc id="desc">Consolidated performance decision for experiment F.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="27" font-weight="700">F-S05 - Synthese charge et acceleration</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">Cloture F-S01 a F-S04, decision {html.escape(summary["decision"]["decision"])}</text>',
            f'<rect x="54" y="120" width="1172" height="138" rx="8" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_cards(summary),
            f'<rect x="54" y="292" width="1172" height="300" rx="8" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_evidence(summary),
            f'<rect x="54" y="628" width="1172" height="178" rx="8" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_risks(summary),
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render F-S05 performance synthesis visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "f_s05_performance_summary.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "F_S05_PERFORMANCE_SUMMARY_VISUALIZATION.svg",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("F-S05 failed; visualization was not generated")
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
