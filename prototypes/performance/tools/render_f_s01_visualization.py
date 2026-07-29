#!/usr/bin/env python3
"""Render F-S01 benchmark harness results as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1240
HEIGHT = 820
COLORS = {
    "paper": "#f7f7f3",
    "panel": "#ffffff",
    "line": "#c9c9c2",
    "ink": "#222222",
    "muted": "#5f625d",
    "ok": "#2f9d68",
    "blue": "#2f7ed8",
    "purple": "#6f4bb2",
    "warn": "#d2842f",
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


def render_factor_chart(summary: dict[str, Any]) -> list[str]:
    profiles = summary["profiles"]
    max_factor = max(profile["aggregate"]["realTimeFactorMean"] for profile in profiles)
    chart_x = 88
    chart_y = 190
    chart_w = 710
    chart_h = 270
    gap = 34
    bar_w = (chart_w - gap * (len(profiles) - 1)) / len(profiles)
    elements = [
        '<text x="84" y="156" font-size="16" font-weight="700">Facteur temps reel moyen</text>',
        f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="{COLORS["line"]}" />',
    ]
    for index, profile in enumerate(profiles):
        aggregate = profile["aggregate"]
        x = chart_x + index * (bar_w + gap)
        bar_h = chart_h * aggregate["realTimeFactorMean"] / max_factor
        y = chart_y + chart_h - bar_h
        color = COLORS["ok"] if aggregate["realTimeFactorMean"] > 1.0 else COLORS["warn"]
        elements.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" rx="5" fill="{color}" />')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{y - 10:.2f}" font-size="12" text-anchor="middle">{aggregate["realTimeFactorMean"]:.1f}x</text>')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{chart_y + chart_h + 28}" font-size="12" text-anchor="middle">{profile["vehicleCount"]} voitures</text>')
    return elements


def render_side_cards(summary: dict[str, Any]) -> list[str]:
    metrics = summary["metrics"]
    env = summary["environment"]
    cards = [
        ("Profils", str(metrics["profileCount"]), COLORS["blue"]),
        ("Repetitions", str(metrics["repetitionsPerProfile"]), COLORS["purple"]),
        ("CPU logiques", str(env["cpuCount"]), COLORS["ok"]),
        ("Erreurs", str(metrics["benchmarkErrorCount"]), COLORS["warn"]),
    ]
    elements = ['<text x="856" y="156" font-size="16" font-weight="700">Contexte</text>']
    for index, (label, value, color) in enumerate(cards):
        y = 184 + index * 68
        elements.append(f'<rect x="850" y="{y}" width="286" height="52" rx="6" fill="#ffffff" stroke="{COLORS["line"]}" />')
        elements.append(f'<text x="866" y="{y + 21}" font-size="12" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
        elements.append(f'<text x="1014" y="{y + 33}" font-size="23" font-weight="700" fill="{color}" text-anchor="end">{html.escape(value)}</text>')
    elements.append(f'<text x="856" y="482" font-size="12" fill="{COLORS["muted"]}">{html.escape(env["platform"][:48])}</text>')
    return elements


def render_table(summary: dict[str, Any]) -> list[str]:
    elements = [
        '<text x="84" y="552" font-size="16" font-weight="700">Profils mesures</text>',
        '<text x="84" y="586" font-size="12" fill="#5f625d">voitures</text>',
        '<text x="204" y="586" font-size="12" fill="#5f625d">wall moyen</text>',
        '<text x="364" y="586" font-size="12" fill="#5f625d">facteur</text>',
        '<text x="504" y="586" font-size="12" fill="#5f625d">veh-frames/s</text>',
        '<text x="684" y="586" font-size="12" fill="#5f625d">replay bytes/s</text>',
        '<text x="884" y="586" font-size="12" fill="#5f625d">pic memoire</text>',
    ]
    for index, profile in enumerate(summary["profiles"]):
        aggregate = profile["aggregate"]
        y = 620 + index * 42
        fill = "#fbfbf8" if index % 2 == 0 else "#ffffff"
        elements.append(f'<rect x="74" y="{y - 27}" width="1088" height="36" rx="4" fill="{fill}" stroke="#ecece7" />')
        elements.append(f'<text x="84" y="{y}" font-size="13" font-weight="700">{profile["vehicleCount"]}</text>')
        elements.append(f'<text x="204" y="{y}" font-size="13">{aggregate["wallTimeMsMean"]:.2f} ms</text>')
        elements.append(f'<text x="364" y="{y}" font-size="13">{aggregate["realTimeFactorMean"]:.1f}x</text>')
        elements.append(f'<text x="504" y="{y}" font-size="13">{aggregate["vehicleFramesPerSecondMean"]:.0f}</text>')
        elements.append(f'<text x="684" y="{y}" font-size="13">{aggregate["serializedBytesPerSecondMean"]:.0f}</text>')
        elements.append(f'<text x="884" y="{y}" font-size="13">{aggregate["peakTracedBytesMean"]:.0f}</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">F-S01 benchmark harness</title>',
            '<desc id="desc">No-render benchmark harness across 1, 12, 20 and 40 vehicles.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">F-S01 - Harnais de benchmark</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">{metrics["profileCount"]} profils, {metrics["repetitionsPerProfile"]} repetitions, {metrics["simulatedDurationS"]:.0f}s simules, hors rendu Unity</text>',
            f'<rect x="54" y="132" width="1130" height="384" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_factor_chart(summary),
            *render_side_cards(summary),
            f'<rect x="54" y="532" width="1130" height="222" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_table(summary),
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render F-S01 benchmark visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "f_s01_benchmark_harness_summary.json",
        help="F-S01 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "F_S01_BENCHMARK_HARNESS_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("F-S01 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
