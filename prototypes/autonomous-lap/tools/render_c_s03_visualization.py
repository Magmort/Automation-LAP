#!/usr/bin/env python3
"""Render C-S03 track and trajectory as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import importlib.util
import math
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1100
HEIGHT = 820
PADDING = 54
TRACK_SAMPLE_SPACING_M = 2.0
TRAJECTORY_SAMPLE_INTERVAL_S = 0.10
REFERENCE_DT = 1.0 / 120.0


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
    import json

    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def color_for_speed(speed_kmh: float, min_speed_kmh: float, max_speed_kmh: float) -> str:
    if max_speed_kmh <= min_speed_kmh:
        ratio = 0.0
    else:
        ratio = (speed_kmh - min_speed_kmh) / (max_speed_kmh - min_speed_kmh)
    ratio = max(0.0, min(1.0, ratio))
    stops = [
        (0.00, (41, 121, 255)),
        (0.45, (44, 178, 102)),
        (0.72, (244, 192, 64)),
        (1.00, (218, 70, 56)),
    ]
    for index in range(1, len(stops)):
        previous_stop, previous_color = stops[index - 1]
        next_stop, next_color = stops[index]
        if ratio <= next_stop:
            local = (ratio - previous_stop) / (next_stop - previous_stop)
            red = round(previous_color[0] + (next_color[0] - previous_color[0]) * local)
            green = round(previous_color[1] + (next_color[1] - previous_color[1]) * local)
            blue = round(previous_color[2] + (next_color[2] - previous_color[2]) * local)
            return f"rgb({red},{green},{blue})"
    red, green, blue = stops[-1][1]
    return f"rgb({red},{green},{blue})"


def fmt_points(points: list[tuple[float, float]], project: Any) -> str:
    return " ".join(f"{project(x, y)[0]:.2f},{project(x, y)[1]:.2f}" for x, y in points)


def render_svg(
    track: dict[str, Any],
    profile: dict[str, Any],
    run: dict[str, Any],
    c_s02: Any,
) -> str:
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
        left_boundary.append(
            (
                point["x"] + point["normalX"] * point["leftWidth"],
                point["y"] + point["normalY"] * point["leftWidth"],
            )
        )
        right_boundary.append(
            (
                point["x"] - point["normalX"] * point["rightWidth"],
                point["y"] - point["normalY"] * point["rightWidth"],
            )
        )

    trajectory = [
        sample
        for sample in run["samples"]
        if "x" in sample and "y" in sample and math.isfinite(sample["x"]) and math.isfinite(sample["y"])
    ]
    bounds_points = left_boundary + right_boundary + centerline + [(sample["x"], sample["y"]) for sample in trajectory]
    min_x = min(point[0] for point in bounds_points)
    max_x = max(point[0] for point in bounds_points)
    min_y = min(point[1] for point in bounds_points)
    max_y = max(point[1] for point in bounds_points)
    world_width = max(max_x - min_x, 1.0)
    world_height = max(max_y - min_y, 1.0)
    scale = min((WIDTH - PADDING * 2) / world_width, (HEIGHT - PADDING * 2) / world_height)
    left = (WIDTH - world_width * scale) * 0.5
    top = (HEIGHT - world_height * scale) * 0.5

    def project(x: float, y: float) -> tuple[float, float]:
        return (left + (x - min_x) * scale, top + (max_y - y) * scale)

    speed_values = [sample["speedKmh"] for sample in trajectory]
    min_speed = min(speed_values)
    max_speed = max(speed_values)
    track_polygon = left_boundary + list(reversed(right_boundary))
    center_path = fmt_points(centerline, project)
    track_points = fmt_points(track_polygon, project)

    trajectory_segments: list[str] = []
    for previous, current in zip(trajectory, trajectory[1:]):
        x1, y1 = project(previous["x"], previous["y"])
        x2, y2 = project(current["x"], current["y"])
        color = color_for_speed((previous["speedKmh"] + current["speedKmh"]) * 0.5, min_speed, max_speed)
        trajectory_segments.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="4.2" stroke-linecap="round" />'
        )

    start_x, start_y = project(centerline[0][0], centerline[0][1])
    legend_x = WIDTH - 272
    legend_y = 40
    legend_width = 214
    legend_steps = 48
    legend_segments: list[str] = []
    for index in range(legend_steps):
        ratio_a = index / legend_steps
        ratio_b = (index + 1) / legend_steps
        speed = min_speed + (max_speed - min_speed) * ((ratio_a + ratio_b) * 0.5)
        color = color_for_speed(speed, min_speed, max_speed)
        x = legend_x + ratio_a * legend_width
        width = legend_width / legend_steps + 0.8
        legend_segments.append(
            f'<rect x="{x:.2f}" y="{legend_y + 28}" width="{width:.2f}" height="10" fill="{color}" />'
        )

    escaped_vehicle = html.escape(profile["name"])
    duration = html.escape(f"{run['durationS']:.2f} s")
    average_speed = html.escape(f"{run['meanSpeedKmh']:.2f} km/h")
    max_lateral_error = html.escape(f"{run['maxAbsLateralErrorM']:.3f} m")
    min_speed_text = html.escape(f"{min_speed:.1f}")
    max_speed_text = html.escape(f"{max_speed:.1f}")

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            "<title id=\"title\">C-S03 QFC55 trajectory speed visualization</title>",
            f"<desc id=\"desc\">Canonical track with QFC55 trajectory colored by speed from {min_speed_text} to {max_speed_text} km/h.</desc>",
            "<defs>",
            "<filter id=\"soft-shadow\" x=\"-10%\" y=\"-10%\" width=\"120%\" height=\"120%\">",
            "<feDropShadow dx=\"0\" dy=\"1.5\" stdDeviation=\"2\" flood-color=\"#000\" flood-opacity=\"0.18\" />",
            "</filter>",
            "</defs>",
            "<rect width=\"100%\" height=\"100%\" fill=\"#f7f7f3\" />",
            f'<polygon points="{track_points}" fill="#d6d6cf" stroke="#8e8e86" stroke-width="1.5" />',
            f'<polyline points="{center_path}" fill="none" stroke="#76766f" stroke-width="1.2" stroke-dasharray="7 8" opacity="0.75" />',
            "<g filter=\"url(#soft-shadow)\">",
            *trajectory_segments,
            "</g>",
            f'<circle cx="{start_x:.2f}" cy="{start_y:.2f}" r="6" fill="#202020" />',
            f'<text x="{start_x + 10:.2f}" y="{start_y - 10:.2f}" fill="#202020" font-family="Arial, sans-serif" font-size="13">depart</text>',
            f'<g font-family="Arial, sans-serif" font-size="13" fill="#222" transform="translate({legend_x},{legend_y})">',
            '<rect x="-16" y="-18" width="248" height="112" rx="6" fill="#ffffff" opacity="0.88" stroke="#c9c9c2" />',
            f'<text x="0" y="0" font-size="15" font-weight="700">{escaped_vehicle}</text>',
            f'<text x="0" y="20">dt 1/120 s - {duration} - {average_speed}</text>',
            *legend_segments,
            f'<text x="0" y="57">{min_speed_text} km/h</text>',
            f'<text x="{legend_width}" y="57" text-anchor="end">{max_speed_text} km/h</text>',
            f'<text x="0" y="80">erreur laterale max {max_lateral_error}</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render the C-S03 QFC55 trajectory visualization.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--vehicle",
        type=Path,
        default=repo_root
        / "outputs"
        / "a9-raw-vehicle-data"
        / "QFC55 - Magmort Carcharhini RCZ"
        / "automation-lap-raw-vehicle-data.json",
        help="QFC55 AutomationRawVehicleData A9 JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "results" / "C_S03_CURVATURE_SPEED_VISUALIZATION.svg",
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
    c_s03 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s03_curvature_speed.py",
        "run_c_s03_curvature_speed",
    )
    validator = load_module(
        repo_root / "prototypes" / "automation-exporter" / "tools" / "validate_raw_vehicle_data.py",
        "validate_raw_vehicle_data",
    )

    track = load_json(arguments.track)
    vehicle = load_json(arguments.vehicle)
    validator.validate_document(vehicle)
    profile = c_s03.qfc55_profile(vehicle)
    run = c_s03.simulate(track, profile, c_s02, REFERENCE_DT, sample_interval_s=TRAJECTORY_SAMPLE_INTERVAL_S)
    if not run["success"]:
        raise RuntimeError("C-S03 reference run failed; visualization was not generated")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(track, profile, run, c_s02), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
