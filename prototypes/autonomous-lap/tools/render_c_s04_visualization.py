#!/usr/bin/env python3
"""Render C-S04 lateral recovery as a standalone SVG."""

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


def color_for_lateral_error(error_m: float, max_error_m: float) -> str:
    ratio = 0.0 if max_error_m <= 0.0 else max(0.0, min(1.0, error_m / max_error_m))
    stops = [
        (0.00, (38, 132, 255)),
        (0.30, (47, 176, 110)),
        (0.62, (246, 194, 68)),
        (1.00, (216, 68, 57)),
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


def render_svg(track: dict[str, Any], profile: dict[str, Any], run: dict[str, Any], c_s02: Any) -> str:
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
    event_points = []
    for event in run["perturbations"]:
        for x_key, y_key in (("appliedX", "appliedY"), ("recoveredX", "recoveredY")):
            if event.get(x_key) is not None and event.get(y_key) is not None:
                event_points.append((float(event[x_key]), float(event[y_key])))

    bounds_points = (
        left_boundary
        + right_boundary
        + centerline
        + [(sample["x"], sample["y"]) for sample in trajectory]
        + event_points
    )
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

    max_event_offset = max(abs(float(event["offsetM"])) for event in run["perturbations"])
    max_error = max(run["maxAbsLateralErrorM"], max(abs(sample["lateralErrorM"]) for sample in trajectory), max_event_offset)
    track_polygon = left_boundary + list(reversed(right_boundary))
    track_points = fmt_points(track_polygon, project)
    center_path = fmt_points(centerline, project)

    trajectory_segments: list[str] = []
    for previous, current in zip(trajectory, trajectory[1:]):
        x1, y1 = project(previous["x"], previous["y"])
        x2, y2 = project(current["x"], current["y"])
        error = (abs(previous["lateralErrorM"]) + abs(current["lateralErrorM"])) * 0.5
        color = color_for_lateral_error(error, max_error)
        trajectory_segments.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="4.2" stroke-linecap="round" />'
        )

    event_marks: list[str] = []
    for index, event in enumerate(run["perturbations"], start=1):
        if event.get("appliedX") is None or event.get("appliedY") is None:
            continue
        ax, ay = project(float(event["appliedX"]), float(event["appliedY"]))
        label_y = ay - 12 if ay > 130 else ay + 24
        event_marks.append(
            f'<path d="M {ax:.2f} {ay - 8:.2f} L {ax + 8:.2f} {ay:.2f} L {ax:.2f} {ay + 8:.2f} L {ax - 8:.2f} {ay:.2f} Z" '
            'fill="#202020" stroke="#ffffff" stroke-width="2" />'
        )
        event_marks.append(
            f'<text x="{ax:.2f}" y="{label_y:.2f}" text-anchor="middle" fill="#202020" '
            f'font-family="Arial, sans-serif" font-size="13">P{index}</text>'
        )
        if event.get("recoveredX") is not None and event.get("recoveredY") is not None:
            rx, ry = project(float(event["recoveredX"]), float(event["recoveredY"]))
            event_marks.append(
                f'<circle cx="{rx:.2f}" cy="{ry:.2f}" r="6" fill="#ffffff" stroke="#202020" stroke-width="2" />'
            )
            event_marks.append(
                f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{rx:.2f}" y2="{ry:.2f}" '
                'stroke="#202020" stroke-width="1.2" stroke-dasharray="4 5" opacity="0.75" />'
            )

    start_x, start_y = project(centerline[0][0], centerline[0][1])
    legend_x = WIDTH - 294
    legend_y = 40
    legend_width = 232
    legend_steps = 48
    legend_segments: list[str] = []
    for index in range(legend_steps):
        ratio_a = index / legend_steps
        ratio_b = (index + 1) / legend_steps
        value = max_error * ((ratio_a + ratio_b) * 0.5)
        color = color_for_lateral_error(value, max_error)
        x = legend_x + ratio_a * legend_width
        width = legend_width / legend_steps + 0.8
        legend_segments.append(
            f'<rect x="{x:.2f}" y="{legend_y + 28}" width="{width:.2f}" height="10" fill="{color}" />'
        )

    escaped_vehicle = html.escape(profile["name"])
    duration = html.escape(f"{run['durationS']:.2f} s")
    mean_error = html.escape(f"{run['meanAbsLateralErrorM']:.3f} m")
    max_error_text = html.escape(f"{max_error:.2f}")
    recovery_text = html.escape(f"{run['maxRecoveryDurationS']:.3f} s")

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            "<title id=\"title\">C-S04 QFC55 lateral recovery visualization</title>",
            f"<desc id=\"desc\">Canonical track with QFC55 trajectory colored by absolute lateral error up to {max_error_text} m, with perturbation and recovery markers.</desc>",
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
            "<g>",
            *event_marks,
            "</g>",
            f'<circle cx="{start_x:.2f}" cy="{start_y:.2f}" r="5.5" fill="#202020" />',
            f'<text x="{start_x + 10:.2f}" y="{start_y - 10:.2f}" fill="#202020" font-family="Arial, sans-serif" font-size="13">depart</text>',
            f'<g font-family="Arial, sans-serif" font-size="13" fill="#222" transform="translate({legend_x},{legend_y})">',
            '<rect x="-16" y="-18" width="270" height="136" rx="6" fill="#ffffff" opacity="0.90" stroke="#c9c9c2" />',
            f'<text x="0" y="0" font-size="15" font-weight="700">{escaped_vehicle}</text>',
            f'<text x="0" y="20">dt 1/120 s - {duration}</text>',
            *legend_segments,
            '<text x="0" y="57">0,0 m</text>',
            f'<text x="{legend_width}" y="57" text-anchor="end">{max_error_text} m</text>',
            f'<text x="0" y="80">erreur moyenne {mean_error}</text>',
            f'<text x="0" y="100">recuperation max {recovery_text}</text>',
            '<text x="0" y="120">diamant = perturbation, cercle = recup.</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render the C-S04 QFC55 lateral recovery visualization.")
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
        default=repo_root / "prototypes" / "autonomous-lap" / "results" / "C_S04_LATERAL_RECOVERY_VISUALIZATION.svg",
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
    c_s04 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s04_lateral_recovery.py",
        "run_c_s04_lateral_recovery",
    )
    validator = load_module(
        repo_root / "prototypes" / "automation-exporter" / "tools" / "validate_raw_vehicle_data.py",
        "validate_raw_vehicle_data",
    )

    track = load_json(arguments.track)
    vehicle = load_json(arguments.vehicle)
    validator.validate_document(vehicle)
    profile = c_s03.qfc55_profile(vehicle)
    run = c_s04.simulate(track, profile, c_s02, c_s03, REFERENCE_DT)
    if not run["success"]:
        raise RuntimeError("C-S04 reference run failed; visualization was not generated")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(track, profile, run, c_s02), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
