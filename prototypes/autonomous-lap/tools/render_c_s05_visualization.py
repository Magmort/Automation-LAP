#!/usr/bin/env python3
"""Render C-S05 driver profile comparison as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import importlib.util
import math
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1240
HEIGHT = 980
PADDING = 54
TRACK_SAMPLE_SPACING_M = 2.0
REFERENCE_DT = 1.0 / 120.0
PROFILE_COLORS = {
    "cautious": "#2f7ed8",
    "balanced": "#2f9d68",
    "aggressive": "#d84a3a",
    "overspeed_probe": "#6f4bb2",
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
    import json

    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def fmt_points(points: list[tuple[float, float]], project: Any) -> str:
    return " ".join(f"{project(x, y)[0]:.2f},{project(x, y)[1]:.2f}" for x, y in points)


def sample_series_points(
    samples: list[dict[str, float]],
    track_length: float,
    x: float,
    y: float,
    width: float,
    height: float,
    value_fn: Any,
    value_max: float,
) -> str:
    total_progress = track_length * 3.0
    points = []
    for sample in samples:
        progress = max(0.0, min(total_progress, sample["progressM"]))
        value = max(0.0, min(value_max, value_fn(sample)))
        px = x + width * progress / total_progress
        py = y + height - height * value / value_max
        points.append((px, py))
    return " ".join(f"{px:.2f},{py:.2f}" for px, py in points)


def render_plot(
    title: str,
    unit_label: str,
    runs: list[tuple[dict[str, Any], list[dict[str, float]]]],
    track_length: float,
    x: float,
    y: float,
    width: float,
    height: float,
    value_fn: Any,
    value_max: float,
) -> list[str]:
    elements = [
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" fill="#ffffff" stroke="#c9c9c2" />',
        f'<text x="{x:.2f}" y="{y - 10:.2f}" font-size="14" font-weight="700">{html.escape(title)}</text>',
        f'<text x="{x + width - 70:.2f}" y="{y - 10:.2f}" font-size="12" fill="#555">{html.escape(unit_label)}</text>',
    ]
    for index in range(1, 3):
        gx = x + width * index / 3.0
        elements.append(f'<line x1="{gx:.2f}" y1="{y:.2f}" x2="{gx:.2f}" y2="{y + height:.2f}" stroke="#deded8" stroke-dasharray="4 5" />')
        elements.append(f'<text x="{gx + 4:.2f}" y="{y + height - 6:.2f}" font-size="11" fill="#777">tour {index + 1}</text>')
    for ratio in (0.25, 0.5, 0.75):
        gy = y + height * ratio
        elements.append(f'<line x1="{x:.2f}" y1="{gy:.2f}" x2="{x + width:.2f}" y2="{gy:.2f}" stroke="#ecece7" />')
    for run, samples in runs:
        color = PROFILE_COLORS[run["driverProfileId"]]
        dash = ' stroke-dasharray="9 8"' if run["driverProfileId"] == "overspeed_probe" else ""
        points = sample_series_points(samples, track_length, x, y, width, height, value_fn, value_max)
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.4" '
            f'stroke-linecap="round" stroke-linejoin="round"{dash} />'
        )
    return elements


def render_svg(track: dict[str, Any], vehicle_profile: dict[str, Any], runs: list[dict[str, Any]], c_s02: Any) -> str:
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

    trajectories = []
    for run in runs:
        samples = [
            sample
            for sample in run["samples"]
            if "x" in sample and "y" in sample and math.isfinite(sample["x"]) and math.isfinite(sample["y"])
        ]
        trajectories.append((run, samples))

    bounds_points = left_boundary + right_boundary + centerline

    min_x = min(point[0] for point in bounds_points)
    max_x = max(point[0] for point in bounds_points)
    min_y = min(point[1] for point in bounds_points)
    max_y = max(point[1] for point in bounds_points)
    world_width = max(max_x - min_x, 1.0)
    world_height = max(max_y - min_y, 1.0)
    map_width = 780
    map_height = 440
    map_x = PADDING
    map_y = PADDING
    scale = min(map_width / world_width, map_height / world_height)
    left = PADDING
    top = map_y + (map_height - world_height * scale) * 0.5

    def project(x: float, y: float) -> tuple[float, float]:
        return (left + (x - min_x) * scale, top + (max_y - y) * scale)

    track_polygon = left_boundary + list(reversed(right_boundary))
    track_points = fmt_points(track_polygon, project)
    center_path = fmt_points(centerline, project)
    trajectory_paths: list[str] = []
    for run, samples in trajectories:
        color = PROFILE_COLORS[run["driverProfileId"]]
        path_points = fmt_points([(sample["x"], sample["y"]) for sample in samples], project)
        dash = ' stroke-dasharray="9 8"' if run["driverProfileId"] == "overspeed_probe" else ""
        trajectory_paths.append(
            f'<polyline points="{path_points}" fill="none" stroke="{color}" stroke-width="4" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="0.84"{dash} />'
        )

    start_x, start_y = project(centerline[0][0], centerline[0][1])
    panel_x = 900
    panel_y = 42
    panel_width = 282
    max_duration = max(run["durationS"] for run in runs)
    min_duration = min(run["durationS"] for run in runs)
    duration_span = max_duration - min_duration

    panel_rows: list[str] = []
    for index, run in enumerate(sorted(runs, key=lambda item: item["durationS"])):
        y = panel_y + 78 + index * 74
        color = PROFILE_COLORS[run["driverProfileId"]]
        normalized = 0.35 if duration_span <= 0.0 else 0.35 + 0.65 * (run["durationS"] - min_duration) / duration_span
        bar_width = 150 * normalized
        label = html.escape(run["driverProfileLabel"])
        duration = html.escape(f"{run['durationS']:.2f} s")
        speed = html.escape(f"{run['meanSpeedKmh']:.1f} km/h")
        error = html.escape(f"{run['maxAbsLateralErrorM']:.2f} m")
        saturation = html.escape(f"sat {run.get('gripSaturationTickPercent', 0.0):.1f}%")
        offtrack = html.escape(f"sorties {run['offTrackCount']}")
        panel_rows.extend(
            [
                f'<circle cx="{panel_x}" cy="{y - 4}" r="5" fill="{color}" />',
                f'<text x="{panel_x + 14}" y="{y}" font-size="14" font-weight="700">{label}</text>',
                f'<rect x="{panel_x}" y="{y + 10}" width="{bar_width:.2f}" height="9" rx="4.5" fill="{color}" opacity="0.82" />',
                f'<text x="{panel_x}" y="{y + 36}">{duration} - {speed}</text>',
                f'<text x="{panel_x}" y="{y + 56}">err {error} - {saturation} - {offtrack}</text>',
            ]
        )

    chart_runs = trajectories
    max_speed = max(sample["speedKmh"] for _, samples in chart_runs for sample in samples)
    max_lateral_g = max(sample.get("requestedLateralGModel", sample["lateralGModel"]) for _, samples in chart_runs for sample in samples)
    speed_plot = render_plot(
        "Vitesse sur la progression",
        "km/h",
        chart_runs,
        track_length,
        PADDING,
        560,
        1040,
        92,
        lambda sample: sample["speedKmh"],
        max(110.0, math.ceil(max_speed / 10.0) * 10.0),
    )
    lateral_g_plot = render_plot(
        "G lateral demande",
        "g",
        chart_runs,
        track_length,
        PADDING,
        700,
        1040,
        92,
        lambda sample: sample.get("requestedLateralGModel", sample["lateralGModel"]),
        max(1.5, math.ceil(max_lateral_g * 2.0) / 2.0),
    )
    lateral_error_plot = render_plot(
        "Erreur laterale absolue (cap 5 m)",
        "m",
        chart_runs,
        track_length,
        PADDING,
        840,
        1040,
        92,
        lambda sample: abs(sample["lateralErrorM"]),
        5.0,
    )

    escaped_vehicle = html.escape(vehicle_profile["name"])
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            "<title id=\"title\">C-S05 QFC55 driver profile comparison</title>",
            "<desc id=\"desc\">Canonical track with trajectories and telemetry plots for cautious, balanced, aggressive and overspeed probe runs.</desc>",
            "<rect width=\"100%\" height=\"100%\" fill=\"#f7f7f3\" />",
            f'<rect x="{map_x - 14:.2f}" y="{map_y - 14:.2f}" width="{map_width + 28:.2f}" height="{map_height + 28:.2f}" rx="6" fill="#ffffff" stroke="#c9c9c2" />',
            f'<polygon points="{track_points}" fill="#d6d6cf" stroke="#8e8e86" stroke-width="1.5" />',
            f'<polyline points="{center_path}" fill="none" stroke="#76766f" stroke-width="1.2" stroke-dasharray="7 8" opacity="0.72" />',
            *trajectory_paths,
            f'<circle cx="{start_x:.2f}" cy="{start_y:.2f}" r="5.5" fill="#202020" />',
            f'<text x="{start_x + 10:.2f}" y="{start_y - 10:.2f}" fill="#202020" font-family="Arial, sans-serif" font-size="13">depart</text>',
            f'<g font-family="Arial, sans-serif" font-size="13" fill="#222" transform="translate({panel_x},{panel_y})">',
            f'<rect x="-18" y="-18" width="{panel_width}" height="396" rx="6" fill="#ffffff" opacity="0.90" stroke="#c9c9c2" />',
            f'<text x="0" y="0" font-size="15" font-weight="700">{escaped_vehicle}</text>',
            '<text x="0" y="22">C-S05 - profils pilote</text>',
            '<text x="0" y="44">dt 1/120 s, 3 tours</text>',
            '<text x="0" y="374" font-size="12" fill="#666">Trajectoires nominales proches : comparer les graphes ci-dessous.</text>',
            "</g>",
            f'<g font-family="Arial, sans-serif" font-size="13" fill="#222">',
            *panel_rows,
            "</g>",
            f'<g font-family="Arial, sans-serif" font-size="12" fill="#222">',
            *speed_plot,
            *lateral_g_plot,
            *lateral_error_plot,
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render the C-S05 QFC55 driver profile visualization.")
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
        default=repo_root / "prototypes" / "autonomous-lap" / "results" / "C_S05_DRIVER_PROFILES_VISUALIZATION.svg",
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
    c_s05 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s05_driver_profiles.py",
        "run_c_s05_driver_profiles",
    )
    validator = load_module(
        repo_root / "prototypes" / "automation-exporter" / "tools" / "validate_raw_vehicle_data.py",
        "validate_raw_vehicle_data",
    )
    track = load_json(arguments.track)
    vehicle = load_json(arguments.vehicle)
    validator.validate_document(vehicle)
    vehicle_profile = c_s03.qfc55_profile(vehicle)
    runs = [
        c_s05.simulate_driver(track, vehicle_profile, driver_profile, c_s02, c_s03, REFERENCE_DT)
        for driver_profile in c_s05.DRIVER_PROFILES
    ]
    limit_probe_run = c_s05.simulate_driver(track, vehicle_profile, c_s05.LIMIT_PROBE_PROFILE, c_s02, c_s03, REFERENCE_DT)
    if not all(run["success"] for run in runs):
        raise RuntimeError("C-S05 reference run failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(track, vehicle_profile, [*runs, limit_probe_run], c_s02), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
