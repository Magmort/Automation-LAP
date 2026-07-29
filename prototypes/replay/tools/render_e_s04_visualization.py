#!/usr/bin/env python3
"""Render E-S04 sampling size measurements as a standalone SVG."""

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
    "bar": "#2f7ed8",
    "bar_ref": "#2f9d68",
    "event": "#6f4bb2",
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


def render_size_chart(summary: dict[str, Any]) -> list[str]:
    profiles = summary["profiles"]
    max_bytes = max(profile["fileBytes"] for profile in profiles)
    chart_x = 86
    chart_y = 190
    chart_w = 760
    chart_h = 290
    gap = 24
    bar_w = (chart_w - gap * (len(profiles) - 1)) / len(profiles)
    elements = [
        '<text x="84" y="156" font-size="16" font-weight="700">Taille brute par frequence</text>',
        f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="{COLORS["line"]}" />',
    ]
    for index, profile in enumerate(profiles):
        x = chart_x + index * (bar_w + gap)
        bar_h = chart_h * profile["fileBytes"] / max_bytes
        y = chart_y + chart_h - bar_h
        color = COLORS["bar_ref"] if profile["profileId"] == summary["metrics"]["referenceProfileId"] else COLORS["bar"]
        elements.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" rx="5" fill="{color}" />')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{chart_y + chart_h + 28}" font-size="12" text-anchor="middle">{html.escape(profile["profileId"])}</text>')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{y - 10:.2f}" font-size="12" text-anchor="middle">{profile["fileBytes"] // 1000} kB</text>')
        elements.append(f'<text x="{x + bar_w / 2:.2f}" y="{chart_y + chart_h + 48}" font-size="11" fill="{COLORS["muted"]}" text-anchor="middle">{profile["sampleHz"]:.0f} Hz</text>')
    return elements


def render_profile_table(summary: dict[str, Any]) -> list[str]:
    elements = [
        '<text x="84" y="558" font-size="16" font-weight="700">Profils mesures</text>',
        '<text x="84" y="592" font-size="12" fill="#5f625d">profil</text>',
        '<text x="244" y="592" font-size="12" fill="#5f625d">frames</text>',
        '<text x="354" y="592" font-size="12" fill="#5f625d">taille</text>',
        '<text x="484" y="592" font-size="12" fill="#5f625d">octets/s</text>',
        '<text x="624" y="592" font-size="12" fill="#5f625d">octets/frame</text>',
        '<text x="784" y="592" font-size="12" fill="#5f625d">ecart evenement max</text>',
    ]
    for index, profile in enumerate(summary["profiles"]):
        y = 624 + index * 36
        fill = "#fbfbf8" if index % 2 == 0 else "#ffffff"
        elements.append(f'<rect x="74" y="{y - 24}" width="1088" height="31" rx="4" fill="{fill}" stroke="#ecece7" />')
        elements.append(f'<text x="84" y="{y}" font-size="13" font-weight="700">{html.escape(profile["profileId"])}</text>')
        elements.append(f'<text x="244" y="{y}" font-size="13">{profile["frameCount"]}</text>')
        elements.append(f'<text x="354" y="{y}" font-size="13">{profile["fileBytes"]}</text>')
        elements.append(f'<text x="484" y="{y}" font-size="13">{profile["bytesPerSecond"]:.1f}</text>')
        elements.append(f'<text x="624" y="{y}" font-size="13">{profile["bytesPerFrame"]:.1f}</text>')
        elements.append(f'<text x="784" y="{y}" font-size="13">{profile["eventNearestFrameMaxDeltaS"]:.3f}s</text>')
    return elements


def render_side_metrics(summary: dict[str, Any]) -> list[str]:
    metrics = summary["metrics"]
    return [
        '<text x="910" y="156" font-size="16" font-weight="700">Lecture rapide</text>',
        f'<text x="910" y="196" font-size="13" fill="{COLORS["muted"]}">Duree</text>',
        f'<text x="910" y="222" font-size="24" font-weight="700">{metrics["durationS"]:.0f}s</text>',
        f'<text x="910" y="270" font-size="13" fill="{COLORS["muted"]}">Taille min / max</text>',
        f'<text x="910" y="296" font-size="24" font-weight="700">{metrics["minFileBytes"] // 1000} / {metrics["maxFileBytes"] // 1000} kB</text>',
        f'<text x="910" y="344" font-size="13" fill="{COLORS["muted"]}">Debit min / max</text>',
        f'<text x="910" y="370" font-size="24" font-weight="700">{metrics["minBytesPerSecond"]:.0f} / {metrics["maxBytesPerSecond"]:.0f} B/s</text>',
        f'<text x="910" y="418" font-size="13" fill="{COLORS["muted"]}">Validation</text>',
        f'<text x="910" y="444" font-size="24" font-weight="700">{metrics["validationErrorCount"]} erreur</text>',
        f'<text x="910" y="486" font-size="12" fill="{COLORS["muted"]}">Taille monotone: {str(metrics["sizeIsMonotonicWithFrequency"]).lower()}, evenements couverts: {str(metrics["eventCoverageOk"]).lower()}</text>',
    ]


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">E-S04 replay sampling size</title>',
            '<desc id="desc">Replay JSON file size by sampling frequency.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">E-S04 - Taille et frequence replay</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">{metrics["profileCount"]} profils, {metrics["vehicleCount"]} vehicules, {metrics["eventCount"]} evenements, JSON non compresse</text>',
            f'<rect x="54" y="132" width="1130" height="388" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_size_chart(summary),
            *render_side_metrics(summary),
            f'<rect x="54" y="536" width="1130" height="228" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_profile_table(summary),
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render E-S04 sampling size visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s04_sampling_size_summary.json",
        help="E-S04 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "E_S04_SAMPLING_SIZE_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("E-S04 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
