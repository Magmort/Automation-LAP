#!/usr/bin/env python3
"""Render D-S05 rejoin traffic as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1240
HEIGHT = 940
PADDING = 54
TRACK_SAMPLE_SPACING_M = 2.0
COLORS = {
    "ego": "#2f7ed8",
    "target_front": "#2f9d68",
    "target_rear": "#d84a3a",
    "front_gap": "#2f9d68",
    "rear_gap": "#d84a3a",
    "lateral": "#6f4bb2",
    "edge": "#555555",
}


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def fmt_points(points: list[tuple[float, float]], project: Any) -> str:
    return " ".join(f"{project(x, y)[0]:.2f},{project(x, y)[1]:.2f}" for x, y in points)


def sample_points(
    samples: list[dict[str, Any]],
    x: float,
    y: float,
    width: float,
    height: float,
    duration_s: float,
    value_fn: Any,
    value_min: float,
    value_max: float,
) -> str:
    span = max(value_max - value_min, 1e-9)
    points = []
    for sample in samples:
        value = min(value_max, max(value_min, value_fn(sample)))
        px = x + width * sample["timeS"] / duration_s
        py = y + height - height * (value - value_min) / span
        points.append((px, py))
    return " ".join(f"{px:.2f},{py:.2f}" for px, py in points)


def render_plot(
    title: str,
    unit_label: str,
    samples: list[dict[str, Any]],
    series: list[tuple[str, str, Any]],
    x: float,
    y: float,
    width: float,
    height: float,
    duration_s: float,
    value_min: float,
    value_max: float,
    markers_s: list[tuple[str, float | None]],
) -> list[str]:
    elements = [
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" fill="#ffffff" stroke="#c9c9c2" />',
        f'<text x="{x:.2f}" y="{y - 10:.2f}" font-size="14" font-weight="700">{html.escape(title)}</text>',
        f'<text x="{x + width - 70:.2f}" y="{y - 10:.2f}" font-size="12" fill="#555">{html.escape(unit_label)}</text>',
    ]
    for ratio in (0.25, 0.5, 0.75):
        gx = x + width * ratio
        gy = y + height * ratio
        elements.append(f'<line x1="{gx:.2f}" y1="{y:.2f}" x2="{gx:.2f}" y2="{y + height:.2f}" stroke="#deded8" stroke-dasharray="4 5" />')
        elements.append(f'<line x1="{x:.2f}" y1="{gy:.2f}" x2="{x + width:.2f}" y2="{gy:.2f}" stroke="#ecece7" />')
    for label, time_s in markers_s:
        if time_s is None:
            continue
        px = x + width * time_s / duration_s
        elements.append(f'<line x1="{px:.2f}" y1="{y:.2f}" x2="{px:.2f}" y2="{y + height:.2f}" stroke="#222" stroke-width="1.4" stroke-dasharray="5 5" opacity="0.7" />')
        elements.append(f'<text x="{px + 5:.2f}" y="{y + 14:.2f}" font-size="11">{html.escape(label)}</text>')
    for label, color, value_fn in series:
        points = sample_points(samples, x, y, width, height, duration_s, value_fn, value_min, value_max)
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.4" '
            'stroke-linecap="round" stroke-linejoin="round" />'
        )
    legend_x = x + width - 280
    for index, (label, color, _) in enumerate(series):
        legend_y = y + 18 + index * 20
        elements.append(f'<line x1="{legend_x:.2f}" y1="{legend_y:.2f}" x2="{legend_x + 24:.2f}" y2="{legend_y:.2f}" stroke="{color}" stroke-width="2.4" />')
        elements.append(f'<text x="{legend_x + 32:.2f}" y="{legend_y + 4:.2f}" font-size="12">{html.escape(label)}</text>')
    return elements


def render_svg(summary: dict[str, Any], track: dict[str, Any], c_s02: Any) -> str:
    points = c_s02.build_points(track)
    segments, track_length = c_s02.build_segments(points)
    track_sample_count = max(120, math.ceil(track_length / TRACK_SAMPLE_SPACING_M))
    left_boundary: list[tuple[float, float]] = []
    right_boundary: list[tuple[float, float]] = []
    centerline: list[tuple[float, float]] = []
    for index in range(track_sample_count + 1):
        s = track_length * index / track_sample_count
        point = c_s02.point_at_s(segments, track_length, s)
        centerline.append((point["x"], point["y"]))
        left_boundary.append((point["x"] + point["normalX"] * point["leftWidth"], point["y"] + point["normalY"] * point["leftWidth"]))
        right_boundary.append((point["x"] - point["normalX"] * point["rightWidth"], point["y"] - point["normalY"] * point["rightWidth"]))

    samples = summary["run"]["samples"]
    bounds_points = left_boundary + right_boundary + centerline
    min_x = min(point[0] for point in bounds_points)
    max_x = max(point[0] for point in bounds_points)
    min_y = min(point[1] for point in bounds_points)
    max_y = max(point[1] for point in bounds_points)
    map_width = 620
    map_height = 450
    scale = min(map_width / max(max_x - min_x, 1.0), map_height / max(max_y - min_y, 1.0))
    left = PADDING
    top = PADDING + (map_height - (max_y - min_y) * scale) * 0.5

    def project(x: float, y: float) -> tuple[float, float]:
        return (left + (x - min_x) * scale, top + (max_y - y) * scale)

    vehicle_paths = {
        vehicle_id: fmt_points([(sample["vehicles"][vehicle_id]["x"], sample["vehicles"][vehicle_id]["y"]) for sample in samples], project)
        for vehicle_id in ("ego", "target_front", "target_rear")
    }
    last_positions = {
        vehicle_id: project(samples[-1]["vehicles"][vehicle_id]["x"], samples[-1]["vehicles"][vehicle_id]["y"])
        for vehicle_id in ("ego", "target_front", "target_rear")
    }
    duration_s = summary["run"]["durationS"]
    metrics = summary["run"]["metrics"]
    markers = [("start", metrics["rejoinStartedS"]), ("done", metrics["rejoinCompletedS"])]
    lateral_plot = render_plot(
        "Offset lateral ego",
        "m",
        samples,
        [("Ego", COLORS["lateral"], lambda sample: sample["vehicles"]["ego"]["lateralOffsetM"])],
        PADDING,
        555,
        1060,
        86,
        duration_s,
        -0.2,
        2.0,
        markers,
    )
    gap_plot = render_plot(
        "Gaps corridor cible",
        "m",
        samples,
        [
            ("Avant", COLORS["front_gap"], lambda sample: sample["frontGapM"] or 0.0),
            ("Arriere", COLORS["rear_gap"], lambda sample: sample["rearGapM"] or 0.0),
        ],
        PADDING,
        695,
        1060,
        86,
        duration_s,
        0.0,
        60.0,
        markers,
    )
    speed_plot = render_plot(
        "Vitesses",
        "km/h",
        samples,
        [
            ("Ego", COLORS["ego"], lambda sample: sample["vehicles"]["ego"]["speedKmh"]),
            ("Front", COLORS["target_front"], lambda sample: sample["vehicles"]["target_front"]["speedKmh"]),
            ("Rear", COLORS["target_rear"], lambda sample: sample["vehicles"]["target_rear"]["speedKmh"]),
        ],
        PADDING,
        835,
        1060,
        60,
        duration_s,
        54.0,
        66.0,
        markers,
    )
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">D-S05 rejoin after offset</title>',
            '<desc id="desc">Track view and telemetry plots for a car rejoining the target corridor between two cars.</desc>',
            '<rect width="100%" height="100%" fill="#f7f7f3" />',
            f'<polygon points="{fmt_points(left_boundary + list(reversed(right_boundary)), project)}" fill="#d6d6cf" stroke="#8e8e86" stroke-width="1.5" />',
            f'<polyline points="{fmt_points(centerline, project)}" fill="none" stroke="#76766f" stroke-width="1.2" stroke-dasharray="7 8" opacity="0.70" />',
            f'<polyline points="{vehicle_paths["ego"]}" fill="none" stroke="{COLORS["ego"]}" stroke-width="3.4" opacity="0.88" />',
            f'<polyline points="{vehicle_paths["target_front"]}" fill="none" stroke="{COLORS["target_front"]}" stroke-width="2.8" opacity="0.78" />',
            f'<polyline points="{vehicle_paths["target_rear"]}" fill="none" stroke="{COLORS["target_rear"]}" stroke-width="2.8" opacity="0.78" />',
            f'<circle cx="{last_positions["ego"][0]:.2f}" cy="{last_positions["ego"][1]:.2f}" r="8.5" fill="{COLORS["ego"]}" stroke="#202020" />',
            f'<circle cx="{last_positions["target_front"][0]:.2f}" cy="{last_positions["target_front"][1]:.2f}" r="7" fill="{COLORS["target_front"]}" stroke="#202020" />',
            f'<circle cx="{last_positions["target_rear"][0]:.2f}" cy="{last_positions["target_rear"][1]:.2f}" r="7" fill="{COLORS["target_rear"]}" stroke="#202020" />',
            '<g font-family="Arial, sans-serif" font-size="13" fill="#222">',
            '<rect x="760" y="54" width="380" height="278" rx="6" fill="#ffffff" opacity="0.92" stroke="#c9c9c2" />',
            '<text x="786" y="86" font-size="15" font-weight="700">D-S05 - reinsertion</text>',
            f'<text x="786" y="118">debut : {metrics["rejoinStartedS"]:.2f} s</text>',
            f'<text x="786" y="142">fin : {metrics["rejoinCompletedS"]:.2f} s</text>',
            f'<text x="786" y="166">contact ticks : {metrics["contactTicks"]}</text>',
            f'<text x="786" y="190">hors piste ticks : {metrics["offTrackTicks"]}</text>',
            f'<text x="786" y="214">gap avant min : {metrics["minFrontGapDuringRejoinM"]:.2f} m</text>',
            f'<text x="786" y="238">gap arriere min : {metrics["minRearGapDuringRejoinM"]:.2f} m</text>',
            f'<text x="786" y="262">offset final : {metrics["finalLateralOffsetM"]:.2f} m</text>',
            f'<circle cx="786" cy="300" r="5" fill="{COLORS["ego"]}" /><text x="800" y="304">Ego</text>',
            f'<circle cx="856" cy="300" r="5" fill="{COLORS["target_front"]}" /><text x="870" y="304">Front</text>',
            f'<circle cx="944" cy="300" r="5" fill="{COLORS["target_rear"]}" /><text x="958" y="304">Rear</text>',
            "</g>",
            '<g font-family="Arial, sans-serif" font-size="12" fill="#222">',
            *lateral_plot,
            *gap_plot,
            *speed_plot,
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render the D-S05 rejoin visualization.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "d_s05_rejoin_summary.json",
        help="D-S05 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "D_S05_REJOIN_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    c_s02 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s02_path_following.py",
        "run_c_s02_path_following",
    )
    track = load_json(arguments.track)
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("D-S05 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary, track, c_s02), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
