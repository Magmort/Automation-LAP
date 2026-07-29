#!/usr/bin/env python3
"""Render H-S04 .sav geometry over embedded UR2D2 runtime preview PNG."""

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
H_S02_PATH = RESULTS_DIR / "h_s02_runtime_sav_reader.json"
SUMMARY_PATH = RESULTS_DIR / "h_s04_runtime_overlay.json"
OUTPUT_PATH = RESULTS_DIR / "H_S04_RUNTIME_OVERLAY_VISUALIZATION.svg"

WIDTH = 1280
HEIGHT = 820
PLOT_X = 48
PLOT_Y = 138
DISPLAY_W = 1024
DISPLAY_H = 512
SAMPLES_PER_VECTOR_SEGMENT = 20


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text(x: float, y: float, value: str, size: int = 14, weight: int = 400, fill: str = "#1f2937") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'
    )


def is_duplicate_point(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return math.isclose(float(a["x"]), float(b["x"])) and math.isclose(float(a["y"]), float(b["y"]))


def vector2(angle_deg: float, length: float) -> dict[str, float]:
    radians = math.radians(angle_deg)
    return {"x": math.cos(radians) * length, "y": math.sin(radians) * length}


def handle_vector2(angle_deg: float, length: float) -> dict[str, float]:
    vector = vector2(angle_deg, length)
    return {"x": vector["x"], "y": -vector["y"]}


def raw_incoming_handle_endpoint(source_key: dict[str, Any], target_point: dict[str, float]) -> dict[str, float]:
    vector_b = handle_vector2(float(source_key["angleBDeg"]), float(source_key["weightB"]))
    return {"x": target_point["x"] + vector_b["x"], "y": target_point["y"] + vector_b["y"]}


def bezier(
    p0: dict[str, float],
    c0: dict[str, float],
    c1: dict[str, float],
    p1: dict[str, float],
    t: float,
) -> dict[str, float]:
    u = 1.0 - t
    return {
        "x": u**3 * p0["x"] + 3 * u * u * t * c0["x"] + 3 * u * t * t * c1["x"] + t**3 * p1["x"],
        "y": u**3 * p0["y"] + 3 * u * u * t * c0["y"] + 3 * u * t * t * c1["y"] + t**3 * p1["y"],
    }


def sample_vector_trace(feature: dict[str, Any]) -> list[dict[str, float]]:
    vector = feature.get("vectorTraceCandidate")
    if not vector:
        return [{"x": float(point["x"]), "y": float(point["y"])} for point in feature.get("points", [])]
    keys = vector["keys"]
    if len(keys) < 2:
        return [{"x": float(key["x"]), "y": float(key["y"])} for key in keys]
    closed = is_duplicate_point(keys[0], keys[-1])
    unique_keys = keys[:-1] if closed else keys
    segment_count = len(unique_keys) if closed else len(unique_keys) - 1
    sampled = []
    for index in range(segment_count):
        key = unique_keys[index]
        next_key = unique_keys[(index + 1) % len(unique_keys)]
        p0 = {"x": float(key["x"]), "y": float(key["y"])}
        p1 = {"x": float(next_key["x"]), "y": float(next_key["y"])}
        out_handle = handle_vector2(float(key["angleADeg"]), float(key["weightA"]))
        c0 = {"x": p0["x"] + out_handle["x"], "y": p0["y"] + out_handle["y"]}
        c1 = raw_incoming_handle_endpoint(key, p1)
        for step in range(SAMPLES_PER_VECTOR_SEGMENT):
            sampled.append(bezier(p0, c0, c1, p1, step / SAMPLES_PER_VECTOR_SEGMENT))
    if closed and sampled:
        sampled.append(sampled[0])
    elif unique_keys:
        sampled.append({"x": float(unique_keys[-1]["x"]), "y": float(unique_keys[-1]["y"])})
    return sampled


def make_mapper(summary: dict[str, Any]):
    source_w, source_h = summary["background"]["sourceTrackPngSize"]
    scale_x = DISPLAY_W / source_w
    scale_y = DISPLAY_H / source_h

    def mapper(point: dict[str, Any]) -> tuple[float, float]:
        return PLOT_X + float(point["x"]) * scale_x, PLOT_Y + float(point["y"]) * scale_y

    return mapper, scale_x, scale_y


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


def image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render(summary: dict[str, Any], h_s02: dict[str, Any]) -> str:
    features = h_s02["simulationFeatures"]
    mapper, display_scale_x, _ = make_mapper(summary)
    background_path = Path(summary["background"]["path"])
    background_url = image_data_url(background_path)
    road_width_px = summary["strokePolicy"]["roadWidthEditorUnits"] * display_scale_x
    pitlane_width_px = summary["strokePolicy"]["pitlaneWidthEditorUnits"] * display_scale_x

    track = features["track"]
    track_points = sample_vector_trace(track)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<defs><marker id="arrow-h04" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#1f5aa6"/></marker></defs>',
        '<rect x="32" y="28" width="1216" height="86" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        text(56, 66, "H-S04 - Superposition .sav sur fond runtime", 26, 700),
        text(56, 96, f"Statut : {summary['status']} | fond : track_preview.png embarqué | coordonnées éditeur Y-down", 14, 500, "#64748b"),
        f'<rect x="{PLOT_X}" y="{PLOT_Y}" width="{DISPLAY_W}" height="{DISPLAY_H}" rx="8" fill="#111827" stroke="#d9e1ea"/>',
        f'<image x="{PLOT_X}" y="{PLOT_Y}" width="{DISPLAY_W}" height="{DISPLAY_H}" href="{background_url}" preserveAspectRatio="none"/>',
        f'<path d="{path_d(track_points, mapper, True)}" fill="none" stroke="#f8fafc" stroke-width="{road_width_px:.2f}" stroke-linecap="round" stroke-linejoin="round" opacity="0.36"/>',
        f'<path d="{path_d(track_points, mapper, True)}" fill="none" stroke="#1f5aa6" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
    ]

    arrow_step = max(1, len(track_points) // 12)
    for index in range(0, len(track_points), arrow_step):
        point = track_points[index]
        next_point = track_points[(index + 1) % len(track_points)]
        x1, y1 = mapper(point)
        x2, y2 = mapper(next_point)
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy) or 1.0
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x1 + dx / length * 18:.1f}" y2="{y1 + dy / length * 18:.1f}" '
            'stroke="#1f5aa6" stroke-width="2.2" marker-end="url(#arrow-h04)"/>'
        )

    for lane in features.get("pitlaneLanes", []):
        points = sample_vector_trace(lane)
        parts.append(
            f'<path d="{path_d(points, mapper)}" fill="none" stroke="#7c3aed" stroke-width="{pitlane_width_px:.2f}" '
            'stroke-linecap="round" stroke-linejoin="round" opacity="0.34"/>'
        )
        parts.append(
            f'<path d="{path_d(points, mapper)}" fill="none" stroke="#7c3aed" stroke-width="3" '
            'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="9 6"/>'
        )
    for wall in features.get("walls", []):
        points = sample_vector_trace(wall)
        parts.append(
            f'<path d="{path_d(points, mapper)}" fill="none" stroke="#111827" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        parts.append(
            f'<path d="{path_d(points, mapper)}" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>'
        )

    for checkpoint in features.get("checkpoints", []):
        x, y = mapper(checkpoint)
        color = "#dc2626" if checkpoint.get("label") == "Finish" else "#f59e0b"
        label = checkpoint.get("label") or "Checkpoint"
        parts.append(f'<rect x="{x - 8:.1f}" y="{y - 8:.1f}" width="16" height="16" fill="{color}" stroke="#ffffff" stroke-width="2" transform="rotate(45 {x:.1f} {y:.1f})"/>')
        parts.append(text(x + 12, y + 5, label, 12, 700, "#111827"))

    panel_x = 1100
    parts.extend(
        [
            f'<rect x="{panel_x}" y="{PLOT_Y}" width="148" height="{DISPLAY_H}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            text(panel_x + 16, PLOT_Y + 34, "Couches", 15, 700),
            f'<path d="M{panel_x + 16},184 L{panel_x + 48},184" stroke="#1f5aa6" stroke-width="4"/>{text(panel_x + 58, 189, "piste", 12, 500, "#475569")}',
            f'<path d="M{panel_x + 16},220 L{panel_x + 48},220" stroke="#f8fafc" stroke-width="12" opacity="0.7"/>{text(panel_x + 58, 225, "largeur", 12, 500, "#475569")}',
            f'<path d="M{panel_x + 16},256 L{panel_x + 48},256" stroke="#7c3aed" stroke-width="8" opacity="0.5"/>{text(panel_x + 58, 261, "pit", 12, 500, "#475569")}',
            f'<path d="M{panel_x + 16},292 L{panel_x + 48},292" stroke="#111827" stroke-width="6"/>{text(panel_x + 58, 297, "mur", 12, 500, "#475569")}',
            f'<rect x="{panel_x + 25}" y="322" width="14" height="14" fill="#dc2626" stroke="#ffffff" stroke-width="1.5" transform="rotate(45 {panel_x + 32} 329)"/>{text(panel_x + 58, 333, "finish", 12, 500, "#475569")}',
            text(panel_x + 16, 386, "Mapping", 15, 700),
            text(panel_x + 16, 414, f"x {summary['background']['scaleX']:.4f}", 12, 500, "#475569"),
            text(panel_x + 16, 438, f"y {summary['background']['scaleY']:.4f}", 12, 500, "#475569"),
            text(panel_x + 16, 474, "Largeurs", 15, 700),
            text(panel_x + 16, 502, f"route {summary['strokePolicy']['roadWidthM']:.0f} m", 12, 500, "#475569"),
            text(panel_x + 16, 526, f"pit {summary['strokePolicy']['pitlaneWidthM']:.0f} m", 12, 500, "#475569"),
            text(48, 696, "Les traits colorés proviennent du .sav ; le rendu de la piste reste celui d'UR2D2. H-S04 valide l'alignement visuel avant simulation.", 13, 500, "#64748b"),
            "</svg>",
        ]
    )
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--h-s02", type=Path, default=H_S02_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = load_json(args.summary)
    h_s02 = load_json(args.h_s02)
    args.output.write_text(render(summary, h_s02), encoding="utf-8", newline="\n")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
