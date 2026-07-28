#!/usr/bin/env python3
"""Render F-S04 replay cost results as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1280
HEIGHT = 900
COLORS = {
    "paper": "#f7f7f3",
    "panel": "#ffffff",
    "line": "#c9c9c2",
    "ink": "#222222",
    "muted": "#5f625d",
    "green": "#2f9d68",
    "blue": "#2f7ed8",
    "teal": "#2b8c91",
    "orange": "#d2842f",
    "purple": "#6f4bb2",
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


def profiles_for(summary: dict[str, Any], vehicle_count: int) -> list[dict[str, Any]]:
    return sorted(
        [profile for profile in summary["profiles"] if profile["aggregate"]["vehicleCount"] == vehicle_count],
        key=lambda profile: profile["aggregate"]["replaySampleHz"],
    )


def hz_label(value: float) -> str:
    return "off" if value <= 0 else f"{value:.0f} Hz"


def render_volume_chart(summary: dict[str, Any]) -> list[str]:
    profiles = profiles_for(summary, int(summary["config"]["targetVehicleCount"]))
    max_bps = max(profile["aggregate"]["serializedBytesPerSecondMean"] for profile in profiles) or 1.0
    chart_x = 86
    chart_y = 180
    chart_w = 690
    chart_h = 278
    gap = 28
    bar_w = (chart_w - gap * (len(profiles) - 1)) / len(profiles)
    elements = [
        '<text x="86" y="146" font-size="16" font-weight="700">Debit replay - 20 voitures</text>',
        f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="{COLORS["line"]}" />',
    ]
    for index, profile in enumerate(profiles):
        aggregate = profile["aggregate"]
        x = chart_x + index * (bar_w + gap)
        bar_h = chart_h * aggregate["serializedBytesPerSecondMean"] / max_bps
        y = chart_y + chart_h - bar_h
        color = COLORS["blue"] if aggregate["replaySampleHz"] != summary["config"]["referenceReplaySampleHz"] else COLORS["green"]
        elements.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" rx="5" fill="{color}" />')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{y - 9:.2f}" font-size="12" text-anchor="middle">{aggregate["serializedBytesPerSecondMean"]:.0f}</text>')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{chart_y + chart_h + 28}" font-size="12" text-anchor="middle">{hz_label(aggregate["replaySampleHz"])}</text>')
    return elements


def render_share_chart(summary: dict[str, Any]) -> list[str]:
    profiles = profiles_for(summary, int(summary["config"]["targetVehicleCount"]))
    max_share = max(0.12, max(profile["aggregate"]["replayShareMean"] for profile in profiles) * 1.25)
    chart_x = 856
    chart_y = 180
    chart_w = 286
    chart_h = 278
    threshold = summary["thresholds"]["requiredMaxReferenceReplayShare"]
    threshold_y = chart_y + chart_h - chart_h * threshold / max_share
    elements = [
        '<text x="856" y="146" font-size="16" font-weight="700">Part moyenne du tick</text>',
        f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="{COLORS["line"]}" />',
        f'<line x1="{chart_x}" y1="{threshold_y:.2f}" x2="{chart_x + chart_w}" y2="{threshold_y:.2f}" stroke="{COLORS["orange"]}" stroke-dasharray="6 5" />',
        f'<text x="{chart_x + chart_w + 8}" y="{threshold_y + 4:.2f}" font-size="12" fill="{COLORS["orange"]}">seuil</text>',
    ]
    point_gap = chart_w / max(len(profiles) - 1, 1)
    points = []
    for index, profile in enumerate(profiles):
        aggregate = profile["aggregate"]
        x = chart_x + index * point_gap
        y = chart_y + chart_h - chart_h * aggregate["replayShareMean"] / max_share
        points.append((x, y, aggregate))
    if len(points) > 1:
        path = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)
        elements.append(f'<polyline points="{path}" fill="none" stroke="{COLORS["purple"]}" stroke-width="3" />')
    for x, y, aggregate in points:
        elements.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{COLORS["purple"]}" />')
        elements.append(f'<text x="{x:.2f}" y="{y - 12:.2f}" font-size="11" text-anchor="middle">{aggregate["replayShareMean"] * 100.0:.1f}%</text>')
        elements.append(f'<text x="{x:.2f}" y="{chart_y + chart_h + 28}" font-size="10" text-anchor="middle">{hz_label(aggregate["replaySampleHz"])}</text>')
    return elements


def render_context_cards(summary: dict[str, Any]) -> list[str]:
    metrics = summary["metrics"]
    cards = [
        ("Reference", f"{metrics['referenceVehicleCount']} voitures / {metrics['referenceReplaySampleHz']:.0f} Hz", COLORS["blue"]),
        ("Part replay", f"{metrics['referenceReplayShareMean'] * 100.0:.1f} %", COLORS["green"]),
        ("Indic. wall", f"{metrics['referenceWallOverheadRatio'] * 100.0:.1f} %", COLORS["orange"]),
        ("Debit ref.", f"{metrics['referenceSerializedBytesPerSecond']:.0f} o/s", COLORS["teal"]),
    ]
    elements = []
    for index, (label, value, color) in enumerate(cards):
        x = 84 + index * 274
        y = 512
        elements.append(f'<rect x="{x}" y="{y}" width="246" height="58" rx="6" fill="#ffffff" stroke="{COLORS["line"]}" />')
        elements.append(f'<text x="{x + 14}" y="{y + 23}" font-size="12" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
        elements.append(f'<text x="{x + 232}" y="{y + 39}" font-size="20" font-weight="700" fill="{color}" text-anchor="end">{html.escape(value)}</text>')
    return elements


def render_table(summary: dict[str, Any]) -> list[str]:
    elements = [
        '<text x="86" y="636" font-size="16" font-weight="700">Comparaison des frequences</text>',
        '<text x="86" y="670" font-size="12" fill="#5f625d">voitures</text>',
        '<text x="186" y="670" font-size="12" fill="#5f625d">Hz</text>',
        '<text x="284" y="670" font-size="12" fill="#5f625d">wall</text>',
        '<text x="430" y="670" font-size="12" fill="#5f625d">overhead</text>',
        '<text x="568" y="670" font-size="12" fill="#5f625d">tick</text>',
        '<text x="704" y="670" font-size="12" fill="#5f625d">replay</text>',
        '<text x="842" y="670" font-size="12" fill="#5f625d">part</text>',
        '<text x="956" y="670" font-size="12" fill="#5f625d">octets/s</text>',
    ]
    rows = sorted(summary["profiles"], key=lambda profile: (profile["aggregate"]["vehicleCount"], profile["aggregate"]["replaySampleHz"]))
    for index, profile in enumerate(rows):
        aggregate = profile["aggregate"]
        y = 704 + index * 25
        if y > 858:
            break
        fill = "#fbfbf8" if index % 2 == 0 else "#ffffff"
        elements.append(f'<rect x="76" y="{y - 18}" width="1116" height="23" rx="3" fill="{fill}" stroke="#ecece7" />')
        elements.append(f'<text x="86" y="{y}" font-size="12">{aggregate["vehicleCount"]}</text>')
        elements.append(f'<text x="186" y="{y}" font-size="12">{hz_label(aggregate["replaySampleHz"])}</text>')
        elements.append(f'<text x="284" y="{y}" font-size="12">{aggregate["wallTimeMsMean"]:.2f} ms</text>')
        elements.append(f'<text x="430" y="{y}" font-size="12">{aggregate["wallOverheadRatio"] * 100.0:.1f}%</text>')
        elements.append(f'<text x="568" y="{y}" font-size="12">{aggregate["tickMeanMsMean"]:.4f} ms</text>')
        elements.append(f'<text x="704" y="{y}" font-size="12">{aggregate["replayMeanMsMean"]:.4f} ms</text>')
        elements.append(f'<text x="842" y="{y}" font-size="12">{aggregate["replayShareMean"] * 100.0:.1f}%</text>')
        elements.append(f'<text x="956" y="{y}" font-size="12">{aggregate["serializedBytesPerSecondMean"]:.0f}</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">F-S04 replay cost</title>',
            '<desc id="desc">Replay serialization throughput and tick share by sampling rate.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">F-S04 - Cout replay detaille</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">{metrics["profileCount"]} profils, {metrics["repetitionsPerProfile"]} repetitions, replay off puis 1/2/4/10/20 Hz</text>',
            f'<rect x="54" y="124" width="1156" height="372" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_volume_chart(summary),
            *render_share_chart(summary),
            *render_context_cards(summary),
            f'<rect x="54" y="610" width="1156" height="260" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_table(summary),
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render F-S04 replay cost visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "f_s04_replay_cost_summary.json",
        help="F-S04 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results" / "F_S04_REPLAY_COST_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("F-S04 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
