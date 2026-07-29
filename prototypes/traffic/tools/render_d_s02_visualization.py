#!/usr/bin/env python3
"""Render D-S02 longitudinal following as a standalone SVG."""

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
HEIGHT = 920
PADDING = 54
TRACK_SAMPLE_SPACING_M = 2.0
COLORS = {
    "leader": "#d84a3a",
    "follower": "#2f7ed8",
    "gap": "#2f9d68",
    "desired": "#555555",
    "accel": "#6f4bb2",
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
) -> list[str]:
    elements = [
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" fill="#ffffff" stroke="#c9c9c2" />',
        f'<text x="{x:.2f}" y="{y - 10:.2f}" font-size="14" font-weight="700">{html.escape(title)}</text>',
        f'<text x="{x + width - 70:.2f}" y="{y - 10:.2f}" font-size="12" fill="#555">{html.escape(unit_label)}</text>',
    ]
    for ratio in (0.25, 0.5, 0.75):
        gx = x + width * ratio
        elements.append(f'<line x1="{gx:.2f}" y1="{y:.2f}" x2="{gx:.2f}" y2="{y + height:.2f}" stroke="#deded8" stroke-dasharray="4 5" />')
        gy = y + height * ratio
        elements.append(f'<line x1="{x:.2f}" y1="{gy:.2f}" x2="{x + width:.2f}" y2="{gy:.2f}" stroke="#ecece7" />')
    for label, color, value_fn in series:
        points = sample_points(samples, x, y, width, height, duration_s, value_fn, value_min, value_max)
        dash = ' stroke-dasharray="7 7"' if label.lower().startswith("cible") else ""
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.4" '
            f'stroke-linecap="round" stroke-linejoin="round"{dash} />'
        )
    legend_x = x + width - 250
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
    map_height = 440
    scale = min(map_width / max(max_x - min_x, 1.0), map_height / max(max_y - min_y, 1.0))
    left = PADDING
    top = PADDING + (map_height - (max_y - min_y) * scale) * 0.5

    def project(x: float, y: float) -> tuple[float, float]:
        return (left + (x - min_x) * scale, top + (max_y - y) * scale)

    leader_path = fmt_points([(sample["leader"]["x"], sample["leader"]["y"]) for sample in samples], project)
    follower_path = fmt_points([(sample["follower"]["x"], sample["follower"]["y"]) for sample in samples], project)
    leader_last = samples[-1]["leader"]
    follower_last = samples[-1]["follower"]
    leader_x, leader_y = project(leader_last["x"], leader_last["y"])
    follower_x, follower_y = project(follower_last["x"], follower_last["y"])
    track_points = fmt_points(left_boundary + list(reversed(right_boundary)), project)
    center_path = fmt_points(centerline, project)
    duration_s = summary["run"]["durationS"]
    max_gap = max(sample["gapM"] for sample in samples)
    max_speed = max(max(sample["leader"]["speedKmh"], sample["follower"]["speedKmh"]) for sample in samples)
    gap_plot = render_plot(
        "Gap longitudinal",
        "m",
        samples,
        [
            ("Gap reel", COLORS["gap"], lambda sample: sample["gapM"]),
            ("Cible", COLORS["desired"], lambda sample: sample["desiredGapM"]),
        ],
        PADDING,
        560,
        1060,
        90,
        duration_s,
        0.0,
        math.ceil(max_gap / 10.0) * 10.0,
    )
    speed_plot = render_plot(
        "Vitesses",
        "km/h",
        samples,
        [
            ("Leader", COLORS["leader"], lambda sample: sample["leader"]["speedKmh"]),
            ("Follower", COLORS["follower"], lambda sample: sample["follower"]["speedKmh"]),
        ],
        PADDING,
        700,
        1060,
        90,
        duration_s,
        0.0,
        math.ceil(max_speed / 10.0) * 10.0,
    )
    accel_plot = render_plot(
        "Acceleration suiveur",
        "m/s2",
        samples,
        [("Follower", COLORS["accel"], lambda sample: sample["follower"]["accelMps2"])],
        PADDING,
        840,
        1060,
        50,
        duration_s,
        -6.0,
        3.0,
    )
    metrics = summary["run"]["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">D-S02 longitudinal following</title>',
            '<desc id="desc">Track view and telemetry plots for a follower car stabilizing behind a slower leader.</desc>',
            '<rect width="100%" height="100%" fill="#f7f7f3" />',
            f'<polygon points="{track_points}" fill="#d6d6cf" stroke="#8e8e86" stroke-width="1.5" />',
            f'<polyline points="{center_path}" fill="none" stroke="#76766f" stroke-width="1.2" stroke-dasharray="7 8" opacity="0.70" />',
            f'<polyline points="{leader_path}" fill="none" stroke="{COLORS["leader"]}" stroke-width="3" opacity="0.82" />',
            f'<polyline points="{follower_path}" fill="none" stroke="{COLORS["follower"]}" stroke-width="3" opacity="0.82" />',
            f'<line x1="{follower_x:.2f}" y1="{follower_y:.2f}" x2="{leader_x:.2f}" y2="{leader_y:.2f}" stroke="#222" stroke-width="2" stroke-dasharray="5 6" opacity="0.55" />',
            f'<circle cx="{leader_x:.2f}" cy="{leader_y:.2f}" r="8.5" fill="{COLORS["leader"]}" stroke="#202020" />',
            f'<circle cx="{follower_x:.2f}" cy="{follower_y:.2f}" r="8.5" fill="{COLORS["follower"]}" stroke="#202020" />',
            '<g font-family="Arial, sans-serif" font-size="13" fill="#222">',
            '<rect x="760" y="54" width="360" height="274" rx="6" fill="#ffffff" opacity="0.92" stroke="#c9c9c2" />',
            '<text x="786" y="86" font-size="15" font-weight="700">D-S02 - suivi longitudinal</text>',
            f'<text x="786" y="118">gap min : {metrics["minGapM"]:.2f} m</text>',
            f'<text x="786" y="142">gap final : {metrics["finalGapM"]:.2f} m</text>',
            f'<text x="786" y="166">gap moyen 20s : {metrics["meanGapLast20S"]:.2f} m</text>',
            f'<text x="786" y="190">cible moyenne 20s : {metrics["meanDesiredGapLast20S"]:.2f} m</text>',
            f'<text x="786" y="214">contact ticks : {metrics["contactTicks"]}</text>',
            f'<text x="786" y="238">detection avant : {metrics["frontDetectedTickPercent"]:.1f}%</text>',
            f'<text x="786" y="262">decel max : {metrics["maxFollowerDecelMps2"]:.2f} m/s2</text>',
            f'<circle cx="786" cy="294" r="5" fill="{COLORS["leader"]}" /><text x="800" y="298">Leader</text>',
            f'<circle cx="876" cy="294" r="5" fill="{COLORS["follower"]}" /><text x="890" y="298">Follower</text>',
            "</g>",
            '<g font-family="Arial, sans-serif" font-size="12" fill="#222">',
            *gap_plot,
            *speed_plot,
            *accel_plot,
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render the D-S02 longitudinal following visualization.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "d_s02_longitudinal_follow_summary.json",
        help="D-S02 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "D_S02_LONGITUDINAL_FOLLOW_VISUALIZATION.svg",
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
        raise RuntimeError("D-S02 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary, track, c_s02), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
