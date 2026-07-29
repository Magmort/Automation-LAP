#!/usr/bin/env python3
"""Render H-S06 vehicle replay over the UR2D2 runtime preview background."""

from __future__ import annotations

import argparse
import base64
import html
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
PACKAGE_PATH = RESULTS_DIR / "h_s05_import_package.json"
SUMMARY_PATH = RESULTS_DIR / "h_s06_functional_replay_summary.json"
OUTPUT_PATH = RESULTS_DIR / "H_S06_FUNCTIONAL_REPLAY_VISUALIZATION.svg"

WIDTH = 1280
HEIGHT = 760
PLOT_X = 48
PLOT_Y = 128
DISPLAY_W = 1024
DISPLAY_H = 512
PANEL_X = 1100


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text(x: float, y: float, value: str, size: int = 14, weight: int = 400, fill: str = "#1f2937") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'
    )


def image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def color_for_speed(speed_kmh: float, min_speed_kmh: float, max_speed_kmh: float) -> str:
    if max_speed_kmh <= min_speed_kmh:
        ratio = 0.0
    else:
        ratio = (speed_kmh - min_speed_kmh) / (max_speed_kmh - min_speed_kmh)
    ratio = max(0.0, min(1.0, ratio))
    stops = [
        (0.00, (37, 99, 235)),
        (0.42, (22, 163, 74)),
        (0.72, (234, 179, 8)),
        (1.00, (220, 38, 38)),
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


def sim_to_preview_mapper(package: dict[str, Any]):
    conversion = package["conversion"]
    mapping = package["runtimeRendering"]["coordinateMapping"]
    origin = conversion["rawOriginEditorUnits"]
    editor_units_per_m = conversion["scalePolicy"]["editorUnitsPerMetre"]
    preview_w, preview_h = mapping["previewSize"]
    scale_x = mapping["scaleX"]
    scale_y = mapping["scaleY"]
    display_scale = min(DISPLAY_W / preview_w, DISPLAY_H / preview_h)
    offset_x = PLOT_X + (DISPLAY_W - preview_w * display_scale) * 0.5
    offset_y = PLOT_Y + (DISPLAY_H - preview_h * display_scale) * 0.5

    def mapper(point: dict[str, Any]) -> tuple[float, float]:
        raw_x = origin["x"] + float(point["x"]) * editor_units_per_m
        raw_y = origin["y"] - float(point["y"]) * editor_units_per_m
        return offset_x + raw_x * scale_x * display_scale, offset_y + raw_y * scale_y * display_scale

    return mapper, display_scale


def path_d(points: list[dict[str, Any]], mapper: Any, close: bool = False) -> str:
    if not points:
        return ""
    coords = [mapper(point) for point in points]
    if close:
        coords.append(coords[0])
    commands = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    commands.extend(f"L {x:.1f} {y:.1f}" for x, y in coords[1:])
    if close:
        commands.append("Z")
    return " ".join(commands)


def vehicle_marker(sample: dict[str, Any], mapper: Any) -> str:
    x, y = mapper(sample)
    heading = -math.degrees(float(sample["heading"]))
    return (
        f'<g transform="translate({x:.1f} {y:.1f}) rotate({heading:.1f})">'
        '<path d="M10,0 L-7,-5 L-4,0 L-7,5 Z" fill="#111827" stroke="#ffffff" stroke-width="1.4"/>'
        "</g>"
    )


def render(package: dict[str, Any], summary: dict[str, Any]) -> str:
    mapper, display_scale = sim_to_preview_mapper(package)
    background_ref = package["runtimeRendering"]["imageAssets"]["track_preview.png"]
    background_path = Path(background_ref["absolutePath"])
    background_url = image_data_url(background_path)
    preview_w, preview_h = package["runtimeRendering"]["coordinateMapping"]["previewSize"]
    image_w = preview_w * display_scale
    image_h = preview_h * display_scale
    image_x = PLOT_X + (DISPLAY_W - image_w) * 0.5
    image_y = PLOT_Y + (DISPLAY_H - image_h) * 0.5
    stroke_policy = package["runtimeRendering"]["strokePolicy"]
    road_width_px = stroke_policy["roadWidthPreviewPx"] * display_scale
    pit_width_px = stroke_policy["pitlaneWidthPreviewPx"] * display_scale

    track_points = package["trackDefinition"]["centerline"]
    extras = package["simulationExtras"]
    run = summary["referenceRun"]
    samples = [sample for sample in run["samples"] if "x" in sample and "y" in sample]
    speeds = [float(sample["speedKmh"]) for sample in samples]
    min_speed = min(speeds)
    max_speed = max(speeds)

    trajectory_segments: list[str] = []
    for previous, current in zip(samples, samples[1:]):
        x1, y1 = mapper(previous)
        x2, y2 = mapper(current)
        speed = (float(previous["speedKmh"]) + float(current["speedKmh"])) * 0.5
        trajectory_segments.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color_for_speed(speed, min_speed, max_speed)}" stroke-width="4.4" stroke-linecap="round"/>'
        )

    legend_segments: list[str] = []
    legend_x = PANEL_X + 18
    legend_y = PLOT_Y + 264
    legend_w = 110
    for index in range(36):
        ratio = (index + 0.5) / 36
        speed = min_speed + (max_speed - min_speed) * ratio
        x = legend_x + index * legend_w / 36
        legend_segments.append(
            f'<rect x="{x:.1f}" y="{legend_y:.1f}" width="{legend_w / 36 + 0.8:.1f}" height="10" '
            f'fill="{color_for_speed(speed, min_speed, max_speed)}"/>'
        )

    first_sample = samples[0]
    final_sample = samples[-1]
    sx, sy = mapper(first_sample)
    fx, fy = mapper(final_sample)
    lap_times = ", ".join(f"{value:.2f}s" for value in run["lapTimesS"])

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">H-S06 functional replay over UR2D2 runtime background</title>",
        "<desc id=\"desc\">QFC55 autonomous replay on the imported First Track, colored by speed and aligned over track_preview.png.</desc>",
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<defs><filter id="shadow-h06" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="2" stdDeviation="2.2" flood-color="#000" flood-opacity="0.20"/></filter></defs>',
        '<rect x="32" y="28" width="1216" height="76" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        text(56, 64, "H-S06 - Replay fonctionnel sur fond runtime", 25, 700),
        text(
            56,
            92,
            f"Statut : {summary['status']} | {summary['track']['name']} | QFC55 | {run['completedLaps']} tours sans sortie",
            14,
            500,
            "#64748b",
        ),
        f'<rect x="{PLOT_X}" y="{PLOT_Y}" width="{DISPLAY_W}" height="{DISPLAY_H}" rx="8" fill="#111827" stroke="#d9e1ea"/>',
        f'<image x="{image_x:.1f}" y="{image_y:.1f}" width="{image_w:.1f}" height="{image_h:.1f}" href="{background_url}" preserveAspectRatio="none"/>',
        f'<path d="{path_d(track_points, mapper, True)}" fill="none" stroke="#ffffff" stroke-width="{road_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.22"/>',
        f'<path d="{path_d(track_points, mapper, True)}" fill="none" stroke="#1d4ed8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.70"/>',
    ]

    for lane in extras["pitlaneLanes"]:
        parts.append(
            f'<path d="{path_d(lane["points"], mapper)}" fill="none" stroke="#7c3aed" stroke-width="{pit_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.22"/>'
        )
        parts.append(
            f'<path d="{path_d(lane["points"], mapper)}" fill="none" stroke="#7c3aed" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="8 6"/>'
        )
    for wall in extras["walls"]:
        parts.append(
            f'<path d="{path_d(wall["points"], mapper)}" fill="none" stroke="#111827" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        parts.append(
            f'<path d="{path_d(wall["points"], mapper)}" fill="none" stroke="#f8fafc" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" opacity="0.75"/>'
        )

    parts.extend(
        [
            '<g filter="url(#shadow-h06)">',
            *trajectory_segments,
            "</g>",
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="6" fill="#0f172a" stroke="#ffffff" stroke-width="2"/>',
            text(sx + 12, sy - 10, "depart", 12, 700, "#0f172a"),
            f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="5" fill="#ffffff" stroke="#0f172a" stroke-width="2"/>',
            vehicle_marker(final_sample, mapper),
        ]
    )

    for checkpoint in extras["checkpointPoints"]:
        x, y = mapper(checkpoint)
        fill = "#dc2626" if checkpoint.get("label") == "Finish" else "#f59e0b"
        parts.append(
            f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="{fill}" stroke="#ffffff" stroke-width="2" transform="rotate(45 {x:.1f} {y:.1f})"/>'
        )

    parts.extend(
        [
            f'<rect x="{PANEL_X}" y="{PLOT_Y}" width="148" height="{DISPLAY_H}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            text(PANEL_X + 16, PLOT_Y + 34, "Replay", 15, 700),
            text(PANEL_X + 16, PLOT_Y + 64, f"{run['durationS']:.2f} s", 18, 700, "#111827"),
            text(PANEL_X + 16, PLOT_Y + 88, f"{run['meanSpeedKmh']:.1f} km/h moy.", 12, 500, "#475569"),
            text(PANEL_X + 16, PLOT_Y + 112, f"{run['maxSpeedKmh']:.1f} km/h max", 12, 500, "#475569"),
            text(PANEL_X + 16, PLOT_Y + 150, "Precision", 15, 700),
            text(PANEL_X + 16, PLOT_Y + 178, f"{run['meanAbsLateralErrorM']:.3f} m moy.", 12, 500, "#475569"),
            text(PANEL_X + 16, PLOT_Y + 202, f"{run['maxAbsLateralErrorM']:.3f} m max", 12, 500, "#475569"),
            text(PANEL_X + 16, PLOT_Y + 226, f"{run['offTrackCount']} sortie", 12, 500, "#475569"),
            text(PANEL_X + 16, PLOT_Y + 256, "Vitesse", 15, 700),
            *legend_segments,
            text(legend_x, legend_y + 30, f"{min_speed:.1f}", 11, 500, "#475569"),
            text(legend_x + legend_w, legend_y + 30, f"{max_speed:.1f}", 11, 500, "#475569"),
            text(PANEL_X + 16, PLOT_Y + 346, "Tours", 15, 700),
            text(PANEL_X + 16, PLOT_Y + 374, lap_times, 11, 500, "#475569"),
            text(PANEL_X + 16, PLOT_Y + 420, "Couches", 15, 700),
            f'<path d="M{PANEL_X + 18},574 L{PANEL_X + 50},574" stroke="#1d4ed8" stroke-width="2.2"/>{text(PANEL_X + 58, 579, "piste", 12, 500, "#475569")}',
            f'<path d="M{PANEL_X + 18},604 L{PANEL_X + 50},604" stroke="#7c3aed" stroke-width="2.2" stroke-dasharray="8 6"/>{text(PANEL_X + 58, 609, "pit", 12, 500, "#475569")}',
            f'<path d="M{PANEL_X + 18},634 L{PANEL_X + 50},634" stroke="#111827" stroke-width="5.5"/>{text(PANEL_X + 58, 639, "mur", 12, 500, "#475569")}',
            text(48, 688, "La trajectoire vient du controleur C-S03 execute sur le TrackDefinition H-S05 ; le fond et les calques proviennent du package runtime UR2D2.", 13, 500, "#64748b"),
            "</svg>",
        ]
    )
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=PACKAGE_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = load_json(args.package)
    summary = load_json(args.summary)
    args.output.write_text(render(package, summary), encoding="utf-8", newline="\n")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
