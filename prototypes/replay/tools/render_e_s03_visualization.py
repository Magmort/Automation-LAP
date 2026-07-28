#!/usr/bin/env python3
"""Render E-S03 event jumps as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1240
HEIGHT = 780
COLORS = {
    "paper": "#f7f7f3",
    "panel": "#ffffff",
    "line": "#c9c9c2",
    "ink": "#222222",
    "muted": "#5f625d",
    "event": "#6f4bb2",
    "pre": "#2f7ed8",
    "post": "#2f9d68",
    "clamp": "#d84a3a",
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


def render_timeline(summary: dict[str, Any]) -> list[str]:
    jumps = summary["jumps"]
    duration = 55.0
    x = 76
    y = 206
    width = 1050
    elements = [
        '<text x="76" y="164" font-size="16" font-weight="700">Evenements indexes</text>',
        f'<line x1="{x}" y1="{y}" x2="{x + width}" y2="{y}" stroke="{COLORS["line"]}" stroke-width="8" stroke-linecap="round" />',
    ]
    for jump in jumps:
        event_x = x + width * jump["eventTimeS"] / duration
        pre_x = x + width * jump["preRollTimeS"] / duration
        post_x = x + width * jump["postRollTimeS"] / duration
        elements.append(f'<line x1="{pre_x:.2f}" y1="{y}" x2="{post_x:.2f}" y2="{y}" stroke="{COLORS["pre"]}" stroke-width="14" stroke-linecap="round" opacity="0.25" />')
        elements.append(f'<circle cx="{pre_x:.2f}" cy="{y}" r="5" fill="{COLORS["pre"]}" />')
        elements.append(f'<circle cx="{post_x:.2f}" cy="{y}" r="5" fill="{COLORS["post"]}" />')
        elements.append(f'<line x1="{event_x:.2f}" y1="{y - 42}" x2="{event_x:.2f}" y2="{y + 42}" stroke="{COLORS["event"]}" stroke-width="2.6" />')
        elements.append(f'<circle cx="{event_x:.2f}" cy="{y}" r="8" fill="{COLORS["event"]}" />')
        elements.append(f'<text x="{event_x + 8:.2f}" y="{y + 34:.2f}" font-size="12">{html.escape(jump["eventId"])}</text>')
        if jump["preRollClamped"] or jump["postRollClamped"]:
            elements.append(f'<circle cx="{event_x:.2f}" cy="{y - 34:.2f}" r="5" fill="{COLORS["clamp"]}" />')
    return elements


def render_jump_rows(summary: dict[str, Any]) -> list[str]:
    elements = [
        '<text x="84" y="316" font-size="16" font-weight="700">Jumps verifies</text>',
        '<text x="84" y="350" font-size="12" fill="#5f625d">event</text>',
        '<text x="314" y="350" font-size="12" fill="#5f625d">time</text>',
        '<text x="424" y="350" font-size="12" fill="#5f625d">mode</text>',
        '<text x="566" y="350" font-size="12" fill="#5f625d">pre/post</text>',
        '<text x="746" y="350" font-size="12" fill="#5f625d">ego offset</text>',
        '<text x="914" y="350" font-size="12" fill="#5f625d">gaps</text>',
    ]
    for index, jump in enumerate(summary["jumps"]):
        y = 382 + index * 64
        fill = "#fbfbf8" if index % 2 == 0 else "#ffffff"
        elements.append(f'<rect x="74" y="{y - 28}" width="1088" height="52" rx="5" fill="{fill}" stroke="#ecece7" />')
        elements.append(f'<text x="84" y="{y}" font-size="13" font-weight="700">{html.escape(jump["eventId"])}</text>')
        elements.append(f'<text x="314" y="{y}" font-size="13">{jump["eventTimeS"]:.3f}s</text>')
        elements.append(f'<text x="424" y="{y}" font-size="13">{html.escape(jump["eventSeekMode"])}</text>')
        elements.append(f'<text x="566" y="{y}" font-size="13">{jump["preRollTimeS"]:.2f}s / {jump["postRollTimeS"]:.2f}s</text>')
        elements.append(f'<text x="746" y="{y}" font-size="13">{jump["egoLateralOffsetM"]:.3f}m</text>')
        elements.append(f'<text x="914" y="{y}" font-size="13">{jump["frontGapM"]:.2f}m / {jump["rearGapM"]:.2f}m</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">E-S03 event jumps</title>',
            '<desc id="desc">Replay event index and event jump validation.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">E-S03 - Saut vers evenement</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">{metrics["jumpCount"]} jumps, {metrics["requiredEventFoundCount"]}/{metrics["requiredEventCount"]} evenements requis, {metrics["contextClampCount"]} clamp(s)</text>',
            f'<rect x="54" y="132" width="1130" height="128" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_timeline(summary),
            f'<rect x="54" y="286" width="1130" height="270" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_jump_rows(summary),
            f'<rect x="54" y="604" width="1130" height="82" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            '<text x="76" y="636" font-size="15" font-weight="700">Validation</text>',
            f'<text x="76" y="666" font-size="13" fill="#5f625d">Index errors: {metrics["eventIndexErrorCount"]}, contexts valides: {metrics["validContextCount"]}, jumps interpoles: {metrics["interpolatedJumpCount"]}. Les evenements sont testees hors UI Unity.</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render E-S03 event jump visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s03_event_jump_summary.json",
        help="E-S03 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "E_S03_EVENT_JUMP_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("E-S03 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
