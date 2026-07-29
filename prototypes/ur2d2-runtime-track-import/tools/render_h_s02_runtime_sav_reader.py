#!/usr/bin/env python3
"""Render H-S02 .sav simulation features as SVG."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
SUMMARY_PATH = RESULTS_DIR / "h_s02_runtime_sav_reader.json"
OUTPUT_PATH = RESULTS_DIR / "H_S02_RUNTIME_SAV_READER_VISUALIZATION.svg"

WIDTH = 1280
HEIGHT = 880
PLOT_X = 48
PLOT_Y = 148
PLOT_W = 820
PLOT_H = 660
SAMPLES_PER_VECTOR_SEGMENT = 16


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text(x: float, y: float, value: str, size: int = 14, weight: int = 400, fill: str = "#1f2937") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(value)}</text>'
    )


def feature_blocks(data: dict[str, Any]) -> list[dict[str, Any]]:
    features = data["simulationFeatures"]
    blocks = []
    if features.get("track"):
        blocks.append(features["track"])
    blocks.extend(features.get("pitlaneLanes", []))
    blocks.extend(features.get("walls", []))
    return blocks


def bounds(blocks: list[dict[str, Any]], checkpoints: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for block in blocks:
        for point in block["points"]:
            xs.append(float(point["x"]))
            ys.append(float(point["y"]))
    for checkpoint in checkpoints:
        xs.append(float(checkpoint["x"]))
        ys.append(float(checkpoint["y"]))
    if not xs:
        return 0.0, 1.0, 0.0, 1.0
    return min(xs), max(xs), min(ys), max(ys)


def make_mapper(blocks: list[dict[str, Any]], checkpoints: list[dict[str, Any]]):
    min_x, max_x, min_y, max_y = bounds(blocks, checkpoints)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    scale = min((PLOT_W - 96) / span_x, (PLOT_H - 96) / span_y)

    def mapper(point: dict[str, Any]) -> tuple[float, float]:
        return (
            PLOT_X + 48 + (float(point["x"]) - min_x) * scale,
            PLOT_Y + 48 + (float(point["y"]) - min_y) * scale,
        )

    return mapper


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


def sample_vector_trace(block: dict[str, Any]) -> list[dict[str, float]]:
    vector = block.get("vectorTraceCandidate")
    if not vector:
        return block["points"]
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


def path_d(points: list[dict[str, Any]], mapper: Any, close: bool) -> str:
    if not points:
        return ""
    mapped = [mapper(point) for point in points]
    commands = [f"M {mapped[0][0]:.1f} {mapped[0][1]:.1f}"]
    commands.extend(f"L {x:.1f} {y:.1f}" for x, y in mapped[1:])
    if close:
        commands.append("Z")
    return " ".join(commands)


def role_color(role: str) -> str:
    if role == "main-track":
        return "#2f5f9f"
    if role in {"pitlane-entry", "pitlane-exit"}:
        return "#8b5fbf"
    if role == "wall":
        return "#333840"
    return "#6b7280"


def render(data: dict[str, Any]) -> str:
    features = data["simulationFeatures"]
    blocks = feature_blocks(data)
    checkpoints = features["checkpoints"]
    mapper = make_mapper(blocks, checkpoints)
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<rect x="32" y="28" width="1216" height="92" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
        text(56, 66, "H-S02 - Éléments de simulation lus depuis le .sav", 26, 700),
        text(56, 96, f"Statut : {data['status']} | Piste : {'oui' if features['status']['trackFound'] else 'non'} | Pitlane : {features['status']['pitlaneLaneCount']} | Murs : {features['status']['wallCount']} | Checkpoints : {features['status']['checkpointCount']}", 14, 500, "#64748b"),
        f'<rect x="{PLOT_X}" y="{PLOT_Y}" width="{PLOT_W}" height="{PLOT_H}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
    ]

    track = features.get("track")
    if track:
        track_points = sample_vector_trace(track)
        parts.append(
            f'<path d="{path_d(track_points, mapper, True)}" fill="none" '
            f'stroke="#d9e1ea" stroke-width="42" stroke-linecap="round" stroke-linejoin="round" opacity="0.72"/>'
        )
        parts.append(
            f'<path d="{path_d(track_points, mapper, True)}" fill="none" '
            f'stroke="#2f5f9f" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    for lane in features.get("pitlaneLanes", []):
        color = role_color(lane["role"])
        lane_points = sample_vector_trace(lane)
        parts.append(
            f'<path d="{path_d(lane_points, mapper, False)}" fill="none" stroke="{color}" '
            f'stroke-width="18" stroke-linecap="round" stroke-linejoin="round" opacity="0.20"/>'
        )
        parts.append(
            f'<path d="{path_d(lane_points, mapper, False)}" fill="none" stroke="{color}" '
            f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="9 6"/>'
        )
        x, y = mapper(lane["points"][0])
        label = "pit entry" if lane["role"] == "pitlane-entry" else "pit exit"
        parts.append(text(x + 8, y - 8, label, 12, 700, color))

    for wall in features.get("walls", []):
        wall_points = sample_vector_trace(wall)
        parts.append(
            f'<path d="{path_d(wall_points, mapper, False)}" fill="none" stroke="#333840" '
            f'stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    for checkpoint in checkpoints:
        x, y = mapper(checkpoint)
        color = "#d1495b" if checkpoint.get("label") == "Finish" else "#f29f05"
        label = checkpoint.get("label") or "Checkpoint"
        parts.append(f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="{color}" transform="rotate(45 {x:.1f} {y:.1f})"/>')
        parts.append(text(x + 10, y + 4, label, 12, 600, "#334155"))

    panel_x = 910
    parts.extend(
        [
            f'<rect x="{panel_x}" y="{PLOT_Y}" width="318" height="{PLOT_H}" rx="8" fill="#ffffff" stroke="#d9e1ea"/>',
            text(panel_x + 22, PLOT_Y + 36, "Éléments retenus", 16, 700),
            text(panel_x + 22, PLOT_Y + 64, "Source unique: track_editor.sav", 12, 500, "#64748b"),
        ]
    )
    y = PLOT_Y + 98
    for block in blocks:
        color = role_color(block["role"])
        parts.append(f'<circle cx="{panel_x + 28}" cy="{y - 5}" r="5" fill="{color}"/>')
        parts.append(text(panel_x + 42, y, f"{block['role']} | {block['hexOffset']} | {block['pointCount']} pts", 12, 650))
        parts.append(text(panel_x + 42, y + 18, f"L={block['lengthEditorUnits']:.0f} | confiance={block['confidence']}", 11, 400, "#64748b"))
        y += 46

    legend_y = PLOT_Y + PLOT_H - 154
    legend = [
        ("piste principale", "#2f5f9f"),
        ("voies de pitlane", "#8b5fbf"),
        ("murs", "#333840"),
        ("checkpoints", "#f29f05"),
        ("finish", "#d1495b"),
    ]
    parts.append(text(panel_x + 22, legend_y, "Légende", 16, 700))
    ly = legend_y + 24
    for label, color in legend:
        parts.append(f'<circle cx="{panel_x + 30}" cy="{ly - 5}" r="5" fill="{color}"/>')
        parts.append(text(panel_x + 44, ly, label, 12, 500, "#475569"))
        ly += 22

    parts.append(text(48, 846, "H-S02 affiche uniquement piste, pitlane, murs et checkpoints depuis le .sav, avec courbes vectorielles échantillonnées et orientation éditeur.", 13, 500, "#64748b"))
    parts.append("</svg>")
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = load_json(args.summary)
    args.output.write_text(render(data), encoding="utf-8", newline="\n")
    print(f"Wrote: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
