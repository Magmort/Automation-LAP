#!/usr/bin/env python3
"""Render E-S02 replay navigation as a standalone SVG."""

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
    "forward": "#2f7ed8",
    "backward": "#d84a3a",
    "seek": "#6f4bb2",
    "pause": "#777777",
    "ok": "#2f9d68",
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


def polyline(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def render_plot(
    title: str,
    samples: list[dict[str, Any]],
    x: float,
    y: float,
    width: float,
    height: float,
    value_key: str,
    value_min: float,
    value_max: float,
    color: str,
) -> list[str]:
    playback_max = max(sample["playbackTimeS"] for sample in samples)
    span = max(value_max - value_min, 1e-9)
    points = []
    for sample in samples:
        value = sample[value_key]
        px = x + width * sample["playbackTimeS"] / max(playback_max, 1e-9)
        py = y + height - height * (value - value_min) / span
        points.append((px, py))
    return [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="#fff" stroke="{COLORS["line"]}" />',
        f'<text x="{x}" y="{y - 10}" font-size="14" font-weight="700">{html.escape(title)}</text>',
        f'<polyline points="{polyline(points)}" fill="none" stroke="{color}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" />',
    ]


def command_timeline(summary: dict[str, Any]) -> list[str]:
    commands = summary["run"]["commandResults"]
    trace = summary["run"]["trace"]
    playback_max = max(sample["playbackTimeS"] for sample in trace)
    x = 70
    y = 180
    width = 1080
    elements = [
        f'<line x1="{x}" y1="{y}" x2="{x + width}" y2="{y}" stroke="{COLORS["line"]}" stroke-width="8" stroke-linecap="round" />',
        '<text x="70" y="146" font-size="16" font-weight="700">Script de navigation</text>',
    ]
    color_for_type = {"seek": COLORS["seek"], "pause": COLORS["pause"], "play": COLORS["forward"]}
    for command in commands:
        matching = [sample for sample in trace if sample["commandLabel"] == command["label"]]
        if not matching:
            continue
        start_x = x + width * matching[0]["playbackTimeS"] / max(playback_max, 1e-9)
        end_x = x + width * matching[-1]["playbackTimeS"] / max(playback_max, 1e-9)
        color = color_for_type.get(command["type"], COLORS["muted"])
        if command["type"] == "play" and command["endReplayTimeS"] < command["startReplayTimeS"]:
            color = COLORS["backward"]
        elements.append(f'<line x1="{start_x:.2f}" y1="{y}" x2="{max(end_x, start_x + 2):.2f}" y2="{y}" stroke="{color}" stroke-width="12" stroke-linecap="round" />')
        elements.append(f'<text x="{start_x:.2f}" y="{y + 30}" font-size="11">{html.escape(command["label"])}</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    trace = summary["run"]["trace"]
    replay_times = [sample["replayTimeS"] for sample in trace]
    ego_progress = [sample["ego"]["progressM"] for sample in trace]
    metrics = summary["metrics"]
    replay_plot_samples = [{**sample, "value": sample["replayTimeS"]} for sample in trace]
    progress_plot_samples = [{**sample, "value": sample["ego"]["progressM"]} for sample in trace]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">E-S02 replay navigation</title>',
            '<desc id="desc">Forward and backward replay navigation validation.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">E-S02 - Navigation temporelle</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">{metrics["traceSampleCount"]} samples, {metrics["commandCount"]} commandes, {metrics["clampedSamples"]} clamps aux bornes</text>',
            *command_timeline(summary),
            '<rect x="54" y="250" width="1130" height="430" rx="7" fill="#ffffff" stroke="#c9c9c2" />',
            *render_plot("Temps replay lu pendant le script", replay_plot_samples, 84, 310, 1030, 130, "value", 0.0, max(replay_times), COLORS["forward"]),
            *render_plot("Progression ego lue dans le replay", progress_plot_samples, 84, 510, 1030, 110, "value", min(ego_progress), max(ego_progress), COLORS["backward"]),
            '<rect x="54" y="706" width="1130" height="72" rx="7" fill="#ffffff" stroke="#c9c9c2" />',
            f'<text x="78" y="736" font-size="14" font-weight="700">Validation : {metrics["forwardCommandCount"]} lecture(s) avant, {metrics["backwardCommandCount"]} lecture(s) arriere, {metrics["seekCommandCount"]} seek(s), {metrics["monotonicFailures"]} echec(s) de monotonicite</text>',
            '<text x="78" y="762" font-size="13" fill="#5f625d">La navigation est testee hors UI : les sauts vers evenements seront couverts par E-S03.</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render E-S02 replay navigation visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s02_navigation_summary.json",
        help="E-S02 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "E_S02_NAVIGATION_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("E-S02 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
