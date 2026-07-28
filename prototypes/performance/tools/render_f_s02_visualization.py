#!/usr/bin/env python3
"""Render F-S02 real-time load results as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1240
HEIGHT = 840
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


def render_budget_chart(summary: dict[str, Any]) -> list[str]:
    profiles = summary["profiles"]
    max_ratio = max(0.5, max(profile["aggregate"]["p95BudgetRatioMean"] for profile in profiles))
    chart_x = 88
    chart_y = 196
    chart_w = 690
    chart_h = 260
    gap = 46
    bar_w = (chart_w - gap * (len(profiles) - 1)) / len(profiles)
    threshold = summary["thresholds"]["requiredMaxP95BudgetRatio"]
    threshold_y = chart_y + chart_h - chart_h * threshold / max_ratio
    elements = [
        '<text x="84" y="158" font-size="16" font-weight="700">Ratio tick p95 / budget 60 Hz</text>',
        f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="{COLORS["line"]}" />',
        f'<line x1="{chart_x}" y1="{threshold_y:.2f}" x2="{chart_x + chart_w}" y2="{threshold_y:.2f}" stroke="{COLORS["warn"]}" stroke-dasharray="6 5" />',
        f'<text x="{chart_x + chart_w + 10}" y="{threshold_y + 4:.2f}" font-size="12" fill="{COLORS["warn"]}">seuil</text>',
    ]
    for index, profile in enumerate(profiles):
        aggregate = profile["aggregate"]
        x = chart_x + index * (bar_w + gap)
        bar_h = chart_h * aggregate["p95BudgetRatioMean"] / max_ratio
        y = chart_y + chart_h - bar_h
        color = COLORS["ok"] if aggregate["p95BudgetRatioMean"] <= threshold else COLORS["warn"]
        elements.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" rx="5" fill="{color}" />')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{y - 10:.2f}" font-size="12" text-anchor="middle">{aggregate["p95BudgetRatioMean"]:.4f}</text>')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{chart_y + chart_h + 28}" font-size="12" text-anchor="middle">{profile["aggregate"]["vehicleCount"]} voitures</text>')
    return elements


def render_context_cards(summary: dict[str, Any]) -> list[str]:
    metrics = summary["metrics"]
    cards = [
        ("Tick rate", f"{metrics['tickRateHz']:.0f} Hz", COLORS["blue"]),
        ("Budget", f"{metrics['tickBudgetMs']:.3f} ms", COLORS["purple"]),
        ("Min facteur", f"{metrics['minRequiredRealtimeFactorMean']:.1f}x", COLORS["ok"]),
        ("Erreurs", str(metrics["profileErrorCount"]), COLORS["warn"]),
    ]
    elements = ['<text x="846" y="158" font-size="16" font-weight="700">Validation</text>']
    for index, (label, value, color) in enumerate(cards):
        y = 186 + index * 68
        elements.append(f'<rect x="840" y="{y}" width="300" height="52" rx="6" fill="#ffffff" stroke="{COLORS["line"]}" />')
        elements.append(f'<text x="856" y="{y + 21}" font-size="12" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
        elements.append(f'<text x="1120" y="{y + 33}" font-size="22" font-weight="700" fill="{color}" text-anchor="end">{html.escape(value)}</text>')
    return elements


def render_table(summary: dict[str, Any]) -> list[str]:
    elements = [
        '<text x="84" y="548" font-size="16" font-weight="700">Profils temps reel</text>',
        '<text x="84" y="582" font-size="12" fill="#5f625d">profil</text>',
        '<text x="244" y="582" font-size="12" fill="#5f625d">voitures</text>',
        '<text x="354" y="582" font-size="12" fill="#5f625d">wall</text>',
        '<text x="504" y="582" font-size="12" fill="#5f625d">facteur</text>',
        '<text x="634" y="582" font-size="12" fill="#5f625d">tick p95</text>',
        '<text x="774" y="582" font-size="12" fill="#5f625d">misses</text>',
        '<text x="884" y="582" font-size="12" fill="#5f625d">veh-ticks/s</text>',
    ]
    for index, profile in enumerate(summary["profiles"]):
        aggregate = profile["aggregate"]
        y = 616 + index * 44
        fill = "#fbfbf8" if index % 2 == 0 else "#ffffff"
        elements.append(f'<rect x="74" y="{y - 28}" width="1088" height="38" rx="4" fill="{fill}" stroke="#ecece7" />')
        elements.append(f'<text x="84" y="{y}" font-size="13" font-weight="700">{html.escape(profile["profileId"])}</text>')
        elements.append(f'<text x="244" y="{y}" font-size="13">{aggregate["vehicleCount"]}</text>')
        elements.append(f'<text x="354" y="{y}" font-size="13">{aggregate["wallTimeMsMean"]:.2f} ms</text>')
        elements.append(f'<text x="504" y="{y}" font-size="13">{aggregate["realTimeFactorMean"]:.1f}x</text>')
        elements.append(f'<text x="634" y="{y}" font-size="13">{aggregate["tickP95MsMean"]:.4f} ms</text>')
        elements.append(f'<text x="774" y="{y}" font-size="13">{aggregate["deadlineMissesMean"]:.0f}</text>')
        elements.append(f'<text x="884" y="{y}" font-size="13">{aggregate["vehicleTicksPerSecondMean"]:.0f}</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">F-S02 real-time load</title>',
            '<desc id="desc">Real-time budget validation for 12, 20 and 40 vehicles.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">F-S02 - Charge cible temps reel</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">{metrics["profileCount"]} profils, {metrics["repetitionsPerProfile"]} repetitions, {metrics["simulatedDurationS"]:.0f}s a {metrics["tickRateHz"]:.0f} Hz</text>',
            f'<rect x="54" y="132" width="1130" height="378" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_budget_chart(summary),
            *render_context_cards(summary),
            f'<rect x="54" y="528" width="1130" height="190" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_table(summary),
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render F-S02 real-time load visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "f_s02_realtime_load_summary.json",
        help="F-S02 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "F_S02_REALTIME_LOAD_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("F-S02 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
