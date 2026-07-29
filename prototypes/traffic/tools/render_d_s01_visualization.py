#!/usr/bin/env python3
"""Render D-S01 neighbor perception as a standalone SVG."""

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

WIDTH = 1180
HEIGHT = 820
PADDING = 54
TRACK_SAMPLE_SPACING_M = 2.0
COLORS = {
    "red": "#d84a3a",
    "blue": "#2f7ed8",
    "green": "#2f9d68",
    "purple": "#6f4bb2",
    "orange": "#d8842f",
    "yellow": "#c7a928",
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

    bounds_points = left_boundary + right_boundary + centerline
    min_x = min(point[0] for point in bounds_points)
    max_x = max(point[0] for point in bounds_points)
    min_y = min(point[1] for point in bounds_points)
    max_y = max(point[1] for point in bounds_points)
    map_width = 760
    map_height = 700
    scale = min(map_width / max(max_x - min_x, 1.0), map_height / max(max_y - min_y, 1.0))
    left = PADDING
    top = PADDING + (map_height - (max_y - min_y) * scale) * 0.5

    def project(x: float, y: float) -> tuple[float, float]:
        return (left + (x - min_x) * scale, top + (max_y - y) * scale)

    track_polygon = left_boundary + list(reversed(right_boundary))
    vehicle_by_id = {vehicle["id"]: vehicle for vehicle in summary["vehicleStates"]}
    link_elements: list[str] = []
    for ego_id, perception in summary["perception"].items():
        ego = vehicle_by_id[ego_id]
        ego_x, ego_y = project(ego["x"], ego["y"])
        for relation, dash in (("front", ""), ("rear", " stroke-dasharray=\"5 5\"")):
            link = perception[relation]
            if link is None:
                continue
            other = vehicle_by_id[link["id"]]
            other_x, other_y = project(other["x"], other["y"])
            color = COLORS.get(ego_id, "#333333")
            link_elements.append(
                f'<line x1="{ego_x:.2f}" y1="{ego_y:.2f}" x2="{other_x:.2f}" y2="{other_y:.2f}" '
                f'stroke="{color}" stroke-width="2" opacity="0.42"{dash} />'
            )

    vehicle_elements: list[str] = []
    panel_rows: list[str] = []
    for index, vehicle in enumerate(summary["vehicleStates"]):
        x, y = project(vehicle["x"], vehicle["y"])
        color = COLORS.get(vehicle["id"], "#333333")
        label = html.escape(vehicle["label"])
        vehicle_elements.extend(
            [
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="9" fill="{color}" stroke="#202020" stroke-width="1.2" />',
                f'<text x="{x + 12:.2f}" y="{y - 10:.2f}" font-size="12" font-weight="700">{label}</text>',
            ]
        )
        perception = summary["perception"][vehicle["id"]]
        front = perception["front"]["id"] if perception["front"] else "n/a"
        rear = perception["rear"]["id"] if perception["rear"] else "n/a"
        row_y = 126 + index * 46
        panel_rows.extend(
            [
                f'<circle cx="902" cy="{row_y - 5}" r="5" fill="{color}" />',
                f'<text x="916" y="{row_y}" font-weight="700">{label}</text>',
                f'<text x="916" y="{row_y + 18}">avant {html.escape(front)} / arriere {html.escape(rear)}</text>',
            ]
        )

    track_points = fmt_points(track_polygon, project)
    center_path = fmt_points(centerline, project)
    start_x, start_y = project(centerline[0][0], centerline[0][1])
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">D-S01 neighbor perception</title>',
            '<desc id="desc">Canonical track with six cars and front/rear perception links.</desc>',
            '<rect width="100%" height="100%" fill="#f7f7f3" />',
            f'<polygon points="{track_points}" fill="#d6d6cf" stroke="#8e8e86" stroke-width="1.5" />',
            f'<polyline points="{center_path}" fill="none" stroke="#76766f" stroke-width="1.2" stroke-dasharray="7 8" opacity="0.70" />',
            *link_elements,
            *vehicle_elements,
            f'<circle cx="{start_x:.2f}" cy="{start_y:.2f}" r="5.5" fill="#202020" />',
            f'<text x="{start_x + 10:.2f}" y="{start_y - 10:.2f}" font-size="13">depart</text>',
            '<g font-family="Arial, sans-serif" font-size="13" fill="#222">',
            '<rect x="878" y="42" width="250" height="392" rx="6" fill="#ffffff" opacity="0.92" stroke="#c9c9c2" />',
            '<text x="902" y="72" font-size="15" font-weight="700">D-S01 - voisins</text>',
            '<text x="902" y="94">trait plein : avant</text>',
            '<text x="902" y="112">pointille : arriere</text>',
            *panel_rows,
            '<rect x="878" y="466" width="250" height="112" rx="6" fill="#ffffff" opacity="0.92" stroke="#c9c9c2" />',
            f'<text x="902" y="498">liens detectes : {summary["metrics"]["neighborLinkCount"]}</text>',
            f'<text x="902" y="522">hors piste : {summary["metrics"]["offTrackCount"]}</text>',
            f'<text x="902" y="546">gap min : {summary["metrics"]["minDetectedGapM"]:.2f} m</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render the D-S01 neighbor perception visualization.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "d_s01_neighbor_perception_summary.json",
        help="D-S01 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "D_S01_NEIGHBOR_PERCEPTION_VISUALIZATION.svg",
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
        raise RuntimeError("D-S01 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary, track, c_s02), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
