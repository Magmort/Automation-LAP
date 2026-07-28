#!/usr/bin/env python3
"""Render F-S03 accelerated no-render results as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1240
HEIGHT = 880
COLORS = {
    "paper": "#f7f7f3",
    "panel": "#ffffff",
    "line": "#c9c9c2",
    "ink": "#222222",
    "muted": "#5f625d",
    "ok": "#2f9d68",
    "blue": "#2f7ed8",
    "teal": "#2b8c91",
    "warn": "#d2842f",
    "soft": "#eef3f0",
}
SYSTEM_COLORS = {
    "input": "#2f7ed8",
    "motion": "#2f9d68",
    "perception": "#6f4bb2",
    "decision": "#d2842f",
    "replay": "#2b8c91",
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


def render_acceleration_chart(summary: dict[str, Any]) -> list[str]:
    profiles = summary["profiles"]
    max_factor = max(profile["aggregate"]["realTimeFactorMean"] for profile in profiles) * 1.12
    chart_x = 84
    chart_y = 184
    chart_w = 680
    chart_h = 270
    gap = 48
    bar_w = (chart_w - gap * (len(profiles) - 1)) / len(profiles)
    threshold = summary["thresholds"]["requiredMinRealtimeFactor"]
    threshold_y = chart_y + chart_h - chart_h * threshold / max_factor
    elements = [
        '<text x="84" y="150" font-size="16" font-weight="700">Facteur d acceleration sans rendu</text>',
        f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="{COLORS["line"]}" />',
        f'<line x1="{chart_x}" y1="{threshold_y:.2f}" x2="{chart_x + chart_w}" y2="{threshold_y:.2f}" stroke="{COLORS["warn"]}" stroke-dasharray="6 5" />',
        f'<text x="{chart_x + chart_w + 10}" y="{threshold_y + 4:.2f}" font-size="12" fill="{COLORS["warn"]}">seuil {threshold:.0f}x</text>',
    ]
    for index, profile in enumerate(profiles):
        aggregate = profile["aggregate"]
        x = chart_x + index * (bar_w + gap)
        bar_h = chart_h * aggregate["realTimeFactorMean"] / max_factor
        y = chart_y + chart_h - bar_h
        color = COLORS["ok"] if aggregate["realTimeFactorMean"] >= threshold or not profile["required"] else COLORS["warn"]
        elements.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" rx="5" fill="{color}" />')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{y - 10:.2f}" font-size="13" font-weight="700" text-anchor="middle">{aggregate["realTimeFactorMean"]:.1f}x</text>')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{chart_y + chart_h + 28}" font-size="12" text-anchor="middle">{aggregate["vehicleCount"]} voitures</text>')
    return elements


def render_context_cards(summary: dict[str, Any]) -> list[str]:
    metrics = summary["metrics"]
    cards = [
        ("Duree simulee", f"{metrics['simulatedDurationS']:.0f} s", COLORS["blue"]),
        ("Tick rate", f"{metrics['tickRateHz']:.0f} Hz", COLORS["teal"]),
        ("Min requis", f"{metrics['minRequiredRealtimeFactorMean']:.1f}x", COLORS["ok"]),
        ("Tick p95 max", f"{metrics['maxRequiredTickP95MsMean']:.3f} ms", COLORS["warn"]),
    ]
    elements = ['<text x="838" y="150" font-size="16" font-weight="700">Contexte</text>']
    for index, (label, value, color) in enumerate(cards):
        y = 178 + index * 68
        elements.append(f'<rect x="832" y="{y}" width="314" height="52" rx="6" fill="#ffffff" stroke="{COLORS["line"]}" />')
        elements.append(f'<text x="848" y="{y + 21}" font-size="12" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
        elements.append(f'<text x="1126" y="{y + 33}" font-size="22" font-weight="700" fill="{color}" text-anchor="end">{html.escape(value)}</text>')
    return elements


def render_system_stack(summary: dict[str, Any]) -> list[str]:
    elements = [
        '<text x="84" y="542" font-size="16" font-weight="700">Repartition du cout moyen par tick</text>',
    ]
    x = 84
    y = 576
    width = 680
    row_h = 36
    for index, profile in enumerate(summary["profiles"]):
        aggregate = profile["aggregate"]
        tick_mean = max(float(aggregate["systemTimingsMean"]["tick"]["meanMs"]), 1e-9)
        row_y = y + index * 58
        elements.append(f'<text x="{x}" y="{row_y + 24}" font-size="13" font-weight="700">{profile["aggregate"]["vehicleCount"]} voitures</text>')
        stack_x = x + 100
        cursor = stack_x
        for name in ("input", "motion", "perception", "decision", "replay"):
            mean_ms = float(aggregate["systemTimingsMean"][name]["meanMs"])
            segment_w = width * mean_ms / tick_mean
            elements.append(f'<rect x="{cursor:.2f}" y="{row_y}" width="{segment_w:.2f}" height="{row_h}" fill="{SYSTEM_COLORS[name]}" />')
            if segment_w > 44:
                elements.append(f'<text x="{cursor + segment_w / 2:.2f}" y="{row_y + 23}" font-size="11" fill="#fff" text-anchor="middle">{name}</text>')
            cursor += segment_w
        elements.append(f'<rect x="{stack_x}" y="{row_y}" width="{width}" height="{row_h}" fill="none" stroke="{COLORS["line"]}" />')
        elements.append(f'<text x="{stack_x + width + 16}" y="{row_y + 23}" font-size="12">{tick_mean:.4f} ms</text>')
    legend_y = y + len(summary["profiles"]) * 58 + 20
    cursor = x + 100
    for name in ("input", "motion", "perception", "decision", "replay"):
        elements.append(f'<rect x="{cursor}" y="{legend_y}" width="14" height="14" fill="{SYSTEM_COLORS[name]}" />')
        elements.append(f'<text x="{cursor + 20}" y="{legend_y + 12}" font-size="12">{name}</text>')
        cursor += 110
    return elements


def render_table(summary: dict[str, Any]) -> list[str]:
    elements = [
        '<text x="838" y="542" font-size="16" font-weight="700">Profils</text>',
        '<text x="838" y="574" font-size="12" fill="#5f625d">profil</text>',
        '<text x="990" y="574" font-size="12" fill="#5f625d">facteur</text>',
        '<text x="1084" y="574" font-size="12" fill="#5f625d">veh/s</text>',
    ]
    for index, profile in enumerate(summary["profiles"]):
        aggregate = profile["aggregate"]
        y = 606 + index * 44
        fill = "#fbfbf8" if index % 2 == 0 else "#ffffff"
        elements.append(f'<rect x="828" y="{y - 28}" width="318" height="38" rx="4" fill="{fill}" stroke="#ecece7" />')
        elements.append(f'<text x="838" y="{y}" font-size="12" font-weight="700">{html.escape(profile["profileId"])}</text>')
        elements.append(f'<text x="990" y="{y}" font-size="12">{aggregate["realTimeFactorMean"]:.1f}x</text>')
        elements.append(f'<text x="1084" y="{y}" font-size="12">{aggregate["vehicleTicksPerSecondMean"]:.0f}</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">F-S03 accelerated no-render simulation</title>',
            '<desc id="desc">Acceleration factor and system cost for no-render simulation profiles.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">F-S03 - Simulation acceleree sans rendu</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">{metrics["profileCount"]} profils, {metrics["repetitionsPerProfile"]} repetitions, {metrics["simulatedDurationS"]:.0f}s simules, aucun rendu</text>',
            f'<rect x="54" y="124" width="1130" height="368" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_acceleration_chart(summary),
            *render_context_cards(summary),
            f'<rect x="54" y="520" width="1130" height="272" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_system_stack(summary),
            *render_table(summary),
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render F-S03 accelerated no-render visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "f_s03_accelerated_no_render_summary.json",
        help="F-S03 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "F_S03_ACCELERATED_NO_RENDER_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("F-S03 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
