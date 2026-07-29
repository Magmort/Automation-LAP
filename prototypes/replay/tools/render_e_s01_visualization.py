#!/usr/bin/env python3
"""Render E-S01 replay contract summary as a standalone SVG."""

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
    "ego": "#2f7ed8",
    "front": "#2f9d68",
    "rear": "#d84a3a",
    "event": "#6f4bb2",
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


def project_track(replay: dict[str, Any]) -> tuple[Any, str]:
    points = replay["track"]["centerline"]
    min_x = min(point["x"] for point in points)
    max_x = max(point["x"] for point in points)
    min_y = min(point["y"] for point in points)
    max_y = max(point["y"] for point in points)
    left = 74
    top = 132
    width = 430
    height = 330
    scale = min(width / max(max_x - min_x, 1.0), height / max(max_y - min_y, 1.0))

    def project(x: float, y: float) -> tuple[float, float]:
        return (left + (x - min_x) * scale, top + (max_y - y) * scale)

    path = " ".join(f"{project(point['x'], point['y'])[0]:.2f},{project(point['x'], point['y'])[1]:.2f}" for point in points)
    return project, path


def timeline_line(summary: dict[str, Any], replay: dict[str, Any]) -> list[str]:
    x = 604
    y = 214
    width = 550
    duration = replay["timeline"]["durationS"]
    elements = [
        f'<line x1="{x}" y1="{y}" x2="{x + width}" y2="{y}" stroke="{COLORS["line"]}" stroke-width="8" stroke-linecap="round" />',
        f'<text x="{x}" y="{y - 28}" font-size="16" font-weight="700">Timeline et événements</text>',
    ]
    for event in replay["events"]:
        event_x = x + width * event["timeS"] / duration
        elements.append(f'<line x1="{event_x:.2f}" y1="{y - 34}" x2="{event_x:.2f}" y2="{y + 34}" stroke="{COLORS["event"]}" stroke-width="2" />')
        elements.append(f'<circle cx="{event_x:.2f}" cy="{y}" r="7" fill="{COLORS["event"]}" />')
        elements.append(f'<text x="{event_x + 8:.2f}" y="{y + 28:.2f}" font-size="12">{html.escape(event["id"])}</text>')
    for check in summary["seekChecks"]:
        seek_x = x + width * check["timeS"] / duration
        elements.append(f'<circle cx="{seek_x:.2f}" cy="{y - 28}" r="4" fill="{COLORS["ego"]}" />')
    return elements


def render_svg(summary: dict[str, Any], replay: dict[str, Any]) -> str:
    project, centerline_path = project_track(replay)
    frames = replay["frames"]
    vehicle_paths = {}
    color_for = {"ego": COLORS["ego"], "target_front": COLORS["front"], "target_rear": COLORS["rear"]}
    for vehicle_id in replay["timeline"]["vehicleIds"]:
        points = [
            project(frame["vehicles"][vehicle_id]["xM"], frame["vehicles"][vehicle_id]["yM"])
            for frame in frames
        ]
        vehicle_paths[vehicle_id] = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">E-S01 replay contract</title>',
            '<desc id="desc">Replay file contract summary, embedded track, timeline events and seek checks.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">E-S01 - Contrat replay autonome</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">Replay JSON autonome - {metrics["frameCount"]} frames, {metrics["replayFileBytes"]} octets</text>',
            f'<rect x="54" y="124" width="480" height="380" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            f'<polyline points="{centerline_path}" fill="none" stroke="#777" stroke-width="1.8" stroke-dasharray="6 7" />',
            *[
                f'<polyline points="{path}" fill="none" stroke="{color_for[vehicle_id]}" stroke-width="2.7" opacity="0.82" />'
                for vehicle_id, path in vehicle_paths.items()
            ],
            f'<rect x="584" y="124" width="600" height="180" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *timeline_line(summary, replay),
            f'<rect x="584" y="338" width="600" height="258" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            '<text x="614" y="372" font-size="16" font-weight="700">Validation</text>',
            f'<text x="614" y="410">Version schema : {html.escape(replay["schemaVersion"])}</text>',
            f'<text x="614" y="438">Erreurs structure : {metrics["validationErrorCount"]}</text>',
            f'<text x="614" y="466">Seek checks : {metrics["seekCheckCount"]}</text>',
            f'<text x="614" y="494">Vehicules : {metrics["vehicleCount"]}</text>',
            f'<text x="614" y="522">Evenements : {metrics["eventCount"]}</text>',
            f'<text x="614" y="550">Points piste embarques : {metrics["trackPointCount"]}</text>',
            f'<rect x="54" y="626" width="1130" height="82" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            '<text x="74" y="656" font-size="15" font-weight="700">Reserve</text>',
            '<text x="74" y="684" font-size="13" fill="#5f625d">Format lisible et autonome, mais non compresse ; la navigation avant/arriere et les versions incompatibles seront testees dans les jalons suivants.</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render E-S01 replay contract visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_replay_contract_summary.json",
        help="E-S01 summary JSON.",
    )
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="E-S01 replay JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "E_S01_REPLAY_CONTRACT_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    replay = load_json(arguments.replay)
    if not summary["success"]:
        raise RuntimeError("E-S01 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary, replay), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
