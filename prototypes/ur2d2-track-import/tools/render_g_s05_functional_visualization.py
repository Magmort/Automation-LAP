#!/usr/bin/env python3
"""Render G-S05 imported track functional validation as SVG."""

from __future__ import annotations

import html
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RAW_PATH = RESULTS_DIR / "g_s02_raw_reader.json"
TRACK_PATH = RESULTS_DIR / "g_s03_track_definition_candidate.json"
CONVERSION_PATH = RESULTS_DIR / "g_s03_track_definition_conversion.json"
SUMMARY_PATH = RESULTS_DIR / "g_s05_functional_validation.json"
SVG_PATH = RESULTS_DIR / "G_S05_FUNCTIONAL_VISUALIZATION.svg"
WIDTH = 1280
HEIGHT = 860
PLOT_X = 48
PLOT_Y = 140
PLOT_W = 820
PLOT_H = 650


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def color_for_speed(speed_kmh: float, min_speed_kmh: float, max_speed_kmh: float) -> str:
    if max_speed_kmh <= min_speed_kmh:
        ratio = 0.0
    else:
        ratio = (speed_kmh - min_speed_kmh) / (max_speed_kmh - min_speed_kmh)
    ratio = max(0.0, min(1.0, ratio))
    stops = [
        (0.00, (38, 103, 187)),
        (0.42, (36, 158, 107)),
        (0.72, (229, 181, 58)),
        (1.00, (210, 72, 61)),
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


def path_d(points: list[dict[str, float]], mapper: Any, close: bool = False) -> str:
    if not points:
        return ""
    coords = [mapper(point) for point in points]
    if close and len(coords) > 2:
        coords.append(coords[0])
    commands = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    commands.extend(f"L {x:.1f} {y:.1f}" for x, y in coords[1:])
    if close:
        commands.append("Z")
    return " ".join(commands)


def fmt_number(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def make_mapper(points: list[dict[str, float]]):
    min_x = min(point["x"] for point in points)
    max_x = max(point["x"] for point in points)
    min_y = min(point["y"] for point in points)
    max_y = max(point["y"] for point in points)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((PLOT_W - 112) / span_x, (PLOT_H - 112) / span_y)

    def mapper(point: dict[str, float]) -> tuple[float, float]:
        return (
            PLOT_X + 56 + (point["x"] - min_x) * scale,
            PLOT_Y + PLOT_H - 56 - (point["y"] - min_y) * scale,
        )

    return mapper


def load_context() -> dict[str, Any]:
    g04 = load_module(ROOT / "tools" / "render_g_s04_visual_validation.py", "g_s05_render_g_s04_visual_validation")
    raw = load_json(RAW_PATH)
    track = load_json(TRACK_PATH)
    conversion = load_json(CONVERSION_PATH)
    summary = load_json(SUMMARY_PATH)
    origin = conversion["conversionNotes"]["rawOriginEditorUnits"]
    scale = conversion["conversionNotes"]["scalePolicy"]["editorUnitsPerMetre"]
    t03 = g04.fixture_by_id(raw, "T03_ai_line")
    t04 = g04.fixture_by_id(raw, "T04_limits_or_walls")
    t05 = g04.fixture_by_id(raw, "T05_start_and_checkpoints")
    t06 = g04.fixture_by_id(raw, "T06_pit_lane")
    t07 = g04.fixture_by_id(raw, "T07_surfaces")
    ai_item = next((item for item in raw["elementInventory"]["items"] if item["id"] == "ai_lines"), {})
    ai_lines = [g04.sampled_block(g04.line_block_by_offset(t03, item["hexOffset"]), origin, scale) for item in ai_item.get("blocks", [])]
    wall = g04.sampled_block(g04.nearest_line_block_after_token(t04, "wall1", 128), origin, scale)
    pit_blocks = g04.line_blocks_after_token(t06, "spr_pit_building_to_right", 768)[:2]
    pit_lines = [g04.sampled_block(block, origin, scale) for block in pit_blocks]
    pitlane = [pit_lines[0][0], pit_lines[1][0]] if len(pit_lines) >= 2 and pit_lines[0] and pit_lines[1] else []
    tree = g04.sampled_block(g04.nearest_line_block_after_token(t07, "forrest2", 128), origin, scale)
    sand = g04.sampled_block(g04.nearest_line_block_after_token(t07, "spr_sand", 128), origin, scale)
    checkpoints = [
        {"id": checkpoint.get("label") or "Checkpoint", "point": g04.convert_raw_point(checkpoint, origin, scale)}
        for checkpoint in t05.get("checkpointCandidates", [])
    ]
    left_edge, right_edge = g04.road_ribbon(track["centerline"])
    return {
        "summary": summary,
        "track": track,
        "leftEdge": left_edge,
        "rightEdge": right_edge,
        "aiLines": ai_lines,
        "wall": wall,
        "pitLines": pit_lines,
        "pitlane": pitlane,
        "tree": tree,
        "sand": sand,
        "checkpoints": checkpoints,
    }


def render_svg() -> str:
    context = load_context()
    summary = context["summary"]
    track = context["track"]
    reference = summary["referenceRun"]
    trajectory = [
        {"x": sample["x"], "y": sample["y"], "speedKmh": sample["speedKmh"], "lateralErrorM": sample["lateralErrorM"]}
        for sample in reference["samples"]
        if all(math.isfinite(float(sample[key])) for key in ("x", "y", "speedKmh", "lateralErrorM"))
    ]
    if len(trajectory) < 2:
        raise RuntimeError("G-S05 summary does not contain enough trajectory samples")

    all_points: list[dict[str, float]] = []
    for group in [
        track["centerline"],
        context["leftEdge"],
        context["rightEdge"],
        context["sand"],
        context["tree"],
        context["wall"],
        *context["aiLines"],
        *context["pitLines"],
        context["pitlane"],
        [checkpoint["point"] for checkpoint in context["checkpoints"]],
        trajectory,
    ]:
        all_points.extend(group)
    mapper = make_mapper(all_points)

    def local_path(points: list[dict[str, float]], close: bool = False) -> str:
        return path_d(points, mapper, close)

    speed_values = [point["speedKmh"] for point in trajectory]
    min_speed = min(speed_values)
    max_speed = max(speed_values)
    road_width_m = max(point["leftWidth"] + point["rightWidth"] for point in track["centerline"])
    road_width_px = abs(mapper({"x": road_width_m, "y": 0.0})[0] - mapper({"x": 0.0, "y": 0.0})[0])
    pitlane_width_px = abs(mapper({"x": 5.0, "y": 0.0})[0] - mapper({"x": 0.0, "y": 0.0})[0])
    trajectory_segments = []
    for previous, current in zip(trajectory, trajectory[1:]):
        x1, y1 = mapper(previous)
        x2, y2 = mapper(current)
        speed = (previous["speedKmh"] + current["speedKmh"]) * 0.5
        trajectory_segments.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color_for_speed(speed, min_speed, max_speed)}" stroke-width="4.5" stroke-linecap="round"/>'
        )

    max_left_width = max(float(point["leftWidth"]) for point in track["centerline"])
    max_right_width = max(float(point["rightWidth"]) for point in track["centerline"])
    off_track_markers = []
    previous_was_off_track = False
    for sample in trajectory:
        lateral_error = float(sample["lateralErrorM"])
        is_off_track = lateral_error > max_left_width or lateral_error < -max_right_width
        if is_off_track and not previous_was_off_track:
            x, y = mapper(sample)
            off_track_markers.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.2" fill="#d1495b" stroke="#ffffff" stroke-width="1.8"/>'
            )
        previous_was_off_track = is_off_track

    legend_steps = 52
    legend_x = 930
    legend_segments = []
    for index in range(legend_steps):
        ratio_a = index / legend_steps
        ratio_b = (index + 1) / legend_steps
        speed = min_speed + (max_speed - min_speed) * ((ratio_a + ratio_b) * 0.5)
        x = legend_x + 22 + ratio_a * 236
        legend_segments.append(
            f'<rect x="{x:.1f}" y="478" width="{236 / legend_steps + 0.8:.1f}" height="12" '
            f'fill="{color_for_speed(speed, min_speed, max_speed)}"/>'
        )

    start = track["centerline"][0]
    sx, sy = mapper(start)
    status_label = "validee avec reserves" if summary["success"] else "a revoir"
    vehicle_name = html.escape(summary["vehicleProfile"]["name"])
    track_name = html.escape(summary["importedTrack"]["name"])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">G-S05 imported track functional visualization</title>",
        f"<desc id=\"desc\">Imported UR2D2 track with QFC55 trajectory colored from {min_speed:.1f} to {max_speed:.1f} km/h.</desc>",
        "<style>",
        "text{font-family:Segoe UI,Arial,sans-serif;fill:#25313f}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6b7a}",
        ".label{font-size:14px;font-weight:700}",
        ".small{font-size:12px;fill:#627282}",
        ".tiny{font-size:11px;fill:#627282}",
        "</style>",
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#244f84"/></marker></defs>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#f7f9fc"/>',
        '<rect x="32" y="32" width="1216" height="86" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        '<text x="56" y="70" class="title">G-S05 - Validation fonctionnelle UR2D2</text>',
        f'<text x="56" y="98" class="subtitle">{track_name} - {vehicle_name} - statut: {status_label}</text>',
        f'<rect x="{PLOT_X}" y="{PLOT_Y}" width="{PLOT_W}" height="{PLOT_H}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        f'<path d="{local_path(context["tree"], True)}" fill="#7fb069" fill-opacity="0.18" stroke="#5c8d55" stroke-width="2"/>',
        f'<path d="{local_path(context["sand"], True)}" fill="#e3b55d" fill-opacity="0.30" stroke="#c58a1f" stroke-width="2"/>',
        f'<path d="{local_path(track["centerline"], True)}" fill="none" stroke="#d9e1ea" stroke-width="{road_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.74"/>',
    ]
    for line in context["aiLines"]:
        parts.append(f'<path d="{local_path(line)}" fill="none" stroke="#e39b32" stroke-width="2.0" stroke-dasharray="7 6"/>')
    if context["pitlane"]:
        parts.append(f'<path d="{local_path(context["pitlane"])}" fill="none" stroke="#7c56a4" stroke-width="{pitlane_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.32"/>')
    for index, line in enumerate(context["pitLines"], start=1):
        parts.append(f'<path d="{local_path(line)}" fill="none" stroke="#7c56a4" stroke-width="{pitlane_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.22"/>')
        parts.append(f'<path d="{local_path(line)}" fill="none" stroke="#7c56a4" stroke-width="2.2" stroke-dasharray="9 5"/>')
        if line:
            x, y = mapper(line[0])
            parts.append(f'<text x="{x + 8:.1f}" y="{y - 8:.1f}" class="tiny">pit{index}</text>')
    parts.extend(
        [
            f'<path d="{local_path(context["wall"])}" fill="none" stroke="#4b4e55" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
            f'<path d="{local_path(track["centerline"], True)}" fill="none" stroke="#244f84" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" marker-mid="url(#arrow)"/>',
            *trajectory_segments,
            *off_track_markers,
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="7" fill="#20252b" stroke="#ffffff" stroke-width="2"/>',
            f'<text x="{sx + 10:.1f}" y="{sy - 10:.1f}" class="small">depart</text>',
        ]
    )
    for checkpoint in context["checkpoints"]:
        x, y = mapper(checkpoint["point"])
        color = "#d1495b" if checkpoint["id"] == "Finish" else "#f29f05"
        parts.append(f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="{color}" transform="rotate(45 {x:.1f} {y:.1f})"/>')
        parts.append(f'<text x="{x + 10:.1f}" y="{y + 4:.1f}" class="small">{html.escape(checkpoint["id"])}</text>')

    imported = summary["importedTrack"]
    comparison = summary["canonicalComparison"]
    parts.extend(
        [
            f'<rect x="{legend_x}" y="140" width="298" height="652" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            f'<text x="{legend_x + 22}" y="176" class="label">Run reference 1/120 s</text>',
            f'<text x="{legend_x + 22}" y="206" class="small">Tours: {reference["completedLaps"]}/{reference["targetLaps"]}</text>',
            f'<text x="{legend_x + 22}" y="232" class="small">Duree: {fmt_number(reference["durationS"])} s</text>',
            f'<text x="{legend_x + 22}" y="258" class="small">Vitesse moyenne: {fmt_number(reference["meanSpeedKmh"])} km/h</text>',
            f'<text x="{legend_x + 22}" y="284" class="small">Vitesse max: {fmt_number(reference["maxSpeedKmh"])} km/h</text>',
            f'<text x="{legend_x + 22}" y="310" class="small">Erreur lat. moy.: {fmt_number(reference["meanAbsLateralErrorM"], 3)} m</text>',
            f'<text x="{legend_x + 22}" y="336" class="small">Erreur lat. max: {fmt_number(reference["maxAbsLateralErrorM"], 3)} m</text>',
            f'<text x="{legend_x + 22}" y="362" class="small">Sorties piste: {reference["offTrackCount"]}</text>',
            f'<text x="{legend_x + 22}" y="394" class="label">Piste importee</text>',
            f'<text x="{legend_x + 22}" y="424" class="small">Longueur: {fmt_number(imported["totalLengthM"], 3)} m</text>',
            f'<text x="{legend_x + 22}" y="450" class="small">Largeur: {fmt_number(imported["minTotalWidthM"], 2)} m</text>',
            *legend_segments,
            f'<text x="{legend_x + 22}" y="510" class="tiny">{fmt_number(min_speed, 1)} km/h</text>',
            f'<text x="{legend_x + 258}" y="510" text-anchor="end" class="tiny">{fmt_number(max_speed, 1)} km/h</text>',
            f'<text x="{legend_x + 22}" y="546" class="label">Couches</text>',
            f'<path d="M{legend_x + 22},574 L{legend_x + 52},574" stroke="#244f84" stroke-width="3"/><text x="{legend_x + 64}" y="579" class="small">centerline importee</text>',
            f'<path d="M{legend_x + 22},606 L{legend_x + 52},606" stroke="#e39b32" stroke-width="2" stroke-dasharray="7 6"/><text x="{legend_x + 64}" y="611" class="small">lignes IA brutes</text>',
            f'<path d="M{legend_x + 22},638 L{legend_x + 52},638" stroke="#4b4e55" stroke-width="4"/><text x="{legend_x + 64}" y="643" class="small">mur</text>',
            f'<path d="M{legend_x + 22},670 L{legend_x + 52},670" stroke="#7c56a4" stroke-width="8" stroke-opacity="0.28"/><path d="M{legend_x + 22},670 L{legend_x + 52},670" stroke="#7c56a4" stroke-width="2.2" stroke-dasharray="9 5"/><text x="{legend_x + 64}" y="675" class="small">pitlane 5 m</text>',
            f'<circle cx="{legend_x + 37}" cy="698" r="5.2" fill="#d1495b" stroke="#ffffff" stroke-width="1.8"/><text x="{legend_x + 64}" y="703" class="small">debut de zone hors piste</text>',
            f'<text x="{legend_x + 22}" y="720" class="label">Comparaison C</text>',
            f'<text x="{legend_x + 22}" y="750" class="small">Ecart longueur: {fmt_number(comparison["lengthDeltaPercent"], 2)} %</text>',
            f'<text x="{legend_x + 22}" y="776" class="small">Ecart duree: {fmt_number(comparison["durationDeltaPercent"], 2)} %</text>',
            '<text x="48" y="828" class="small">Le contexte hors TrackDefinition v0.1 provient du lecteur brut G-S02/G-S04 ; la trajectoire coloree provient du controleur autonome C-S03 sur la piste importee.</text>',
            "</svg>",
            "",
        ]
    )
    return "\n".join(parts)


def main() -> int:
    if not SUMMARY_PATH.exists():
        raise RuntimeError("Run run_g_s05_functional_validation.py before rendering G-S05")
    SVG_PATH.write_text(render_svg(), encoding="utf-8", newline="\n")
    print(f"Wrote: {SVG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
