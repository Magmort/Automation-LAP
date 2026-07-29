#!/usr/bin/env python3
"""Run H-S04: prepare raw .sav to runtime PNG overlay validation."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
H_S02_PATH = RESULTS_DIR / "h_s02_runtime_sav_reader.json"
H_S03_PATH = RESULTS_DIR / "h_s03_simulation_geometry.json"
SUMMARY_PATH = RESULTS_DIR / "h_s04_runtime_overlay.json"
REPORT_PATH = RESULTS_DIR / "H_S04_RUNTIME_OVERLAY_RESULT.md"
SVG_PATH = RESULTS_DIR / "H_S04_RUNTIME_OVERLAY_VISUALIZATION.svg"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def point_values(points: list[dict[str, Any]], key: str) -> list[float]:
    return [float(point[key]) for point in points]


def feature_points(h_s02: dict[str, Any]) -> list[dict[str, Any]]:
    features = h_s02["simulationFeatures"]
    points = []
    if features.get("track"):
        points.extend(features["track"]["points"])
    for lane in features.get("pitlaneLanes", []):
        points.extend(lane["points"])
    for wall in features.get("walls", []):
        points.extend(wall["points"])
    points.extend(features.get("checkpoints", []))
    return points


def bbox(points: list[dict[str, Any]]) -> dict[str, float]:
    xs = point_values(points, "x")
    ys = point_values(points, "y")
    return {
        "minX": min(xs),
        "maxX": max(xs),
        "minY": min(ys),
        "maxY": max(ys),
        "spanX": max(xs) - min(xs),
        "spanY": max(ys) - min(ys),
    }


def bbox_inside_canvas(box: dict[str, float], width: float, height: float) -> bool:
    return box["minX"] >= 0.0 and box["minY"] >= 0.0 and box["maxX"] <= width and box["maxY"] <= height


def build_summary(h_s02: dict[str, Any], h_s03: dict[str, Any]) -> dict[str, Any]:
    track_dir = Path(h_s02["trackDirectory"])
    background_path = track_dir / "track_preview.png"
    source_track_size = h_s02["imageLayers"]["track.png"]["size"]
    preview_size = h_s02["imageLayers"]["track_preview.png"]["size"]
    scale_x = preview_size[0] / source_track_size[0]
    scale_y = preview_size[1] / source_track_size[1]
    points = feature_points(h_s02)
    raw_bbox = bbox(points)
    converted_preview_bbox = {
        "minX": raw_bbox["minX"] * scale_x,
        "maxX": raw_bbox["maxX"] * scale_x,
        "minY": raw_bbox["minY"] * scale_y,
        "maxY": raw_bbox["maxY"] * scale_y,
        "spanX": raw_bbox["spanX"] * scale_x,
        "spanY": raw_bbox["spanY"] * scale_y,
    }
    editor_units_per_metre = h_s03["conversionNotes"]["scalePolicy"]["editorUnitsPerMetre"]
    road_width_m = h_s03["conversionNotes"]["widthPolicy"]["totalRoadWidthM"]
    road_width_editor_units = road_width_m * editor_units_per_metre
    pitlane_width_m = 5.0
    pitlane_width_editor_units = pitlane_width_m * editor_units_per_metre
    checks = {
        "backgroundPreviewPresent": background_path.exists(),
        "aspectRatioMatchesTrackPng": math.isclose(
            source_track_size[0] / source_track_size[1],
            preview_size[0] / preview_size[1],
            rel_tol=1e-9,
        ),
        "uniformPreviewScale": math.isclose(scale_x, scale_y, rel_tol=1e-9),
        "featureBoundsInsideTrackCanvas": bbox_inside_canvas(raw_bbox, source_track_size[0], source_track_size[1]),
        "trackFeaturePresent": h_s02["simulationFeatures"].get("track") is not None,
        "pitlaneLanesPresent": len(h_s02["simulationFeatures"].get("pitlaneLanes", [])) >= 2,
        "wallPresent": len(h_s02["simulationFeatures"].get("walls", [])) >= 1,
        "checkpointsPresent": len(h_s02["simulationFeatures"].get("checkpoints", [])) >= 3,
        "hS03TrackDefinitionValid": h_s03["validation"]["success"],
    }
    status = "overlay-ready" if all(checks.values()) else "overlay-with-reserves"
    return {
        "scenario": "H-S04",
        "status": status,
        "generatedAtUtc": utc_now(),
        "background": {
            "path": str(background_path),
            "sourceTrackPngSize": source_track_size,
            "previewSize": preview_size,
            "scaleX": scale_x,
            "scaleY": scale_y,
            "displayPolicy": "embed track_preview.png and map raw .sav coordinates using track.png -> preview scale",
        },
        "sourceGeometry": {
            "hS02Path": str(H_S02_PATH.resolve()),
            "hS03Path": str(H_S03_PATH.resolve()),
            "rawFeatureBboxEditorUnits": raw_bbox,
            "featureBboxPreviewPx": converted_preview_bbox,
            "trackOffset": h_s02["simulationFeatures"]["track"]["hexOffset"],
            "pitlaneOffsets": [lane["hexOffset"] for lane in h_s02["simulationFeatures"].get("pitlaneLanes", [])],
            "wallOffsets": [wall["hexOffset"] for wall in h_s02["simulationFeatures"].get("walls", [])],
            "checkpointLabels": [checkpoint.get("label") for checkpoint in h_s02["simulationFeatures"].get("checkpoints", [])],
        },
        "strokePolicy": {
            "roadWidthM": road_width_m,
            "roadWidthEditorUnits": road_width_editor_units,
            "roadWidthPreviewPx": road_width_editor_units * scale_x,
            "pitlaneWidthM": pitlane_width_m,
            "pitlaneWidthEditorUnits": pitlane_width_editor_units,
            "pitlaneWidthPreviewPx": pitlane_width_editor_units * scale_x,
        },
        "checks": checks,
        "visualizationPath": str((RESULTS_DIR / SVG_PATH.name).resolve()),
        "notes": [
            "H-S04 uses raw editor/screen coordinates for overlay, so Y points down like UR2D2 images.",
            "The SVG embeds track_preview.png and overlays vector-sampled .sav features.",
            "H-S04 does not run vehicle simulation; that remains H-S06.",
        ],
    }


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# H-S04 - Superposition sur fond runtime",
        "",
        "- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2",
        "- **Scénario :** H-S04",
        f"- **Statut :** {summary['status']}",
        f"- **Date :** {summary['generatedAtUtc']}",
        f"- **Visualisation :** `{summary['visualizationPath']}`",
        "",
        "## Décision du jalon",
        "",
    ]
    if summary["status"] == "overlay-ready":
        lines.append("H-S04 est prête pour validation visuelle : les coordonnées `.sav` peuvent être superposées au fond `track_preview.png` avec une échelle uniforme.")
    else:
        lines.append("H-S04 produit une superposition, mais au moins un contrôle d'alignement reste en réserve.")

    lines.extend(
        [
            "",
            "## Contrôles",
            "",
            "| Contrôle | Résultat |",
            "| --- | --- |",
        ]
    )
    for key, value in summary["checks"].items():
        lines.append(f"| `{key}` | {fmt_bool(value)} |")

    background = summary["background"]
    strokes = summary["strokePolicy"]
    lines.extend(
        [
            "",
            "## Mapping",
            "",
            f"- Fond : `{background['path']}`",
            f"- Image source : {background['sourceTrackPngSize'][0]} x {background['sourceTrackPngSize'][1]} px",
            f"- Preview : {background['previewSize'][0]} x {background['previewSize'][1]} px",
            f"- Échelle preview : x `{background['scaleX']:.6f}`, y `{background['scaleY']:.6f}`",
            f"- Largeur piste : {strokes['roadWidthM']:.3f} m -> {strokes['roadWidthPreviewPx']:.3f} px preview",
            f"- Largeur pitlane : {strokes['pitlaneWidthM']:.3f} m -> {strokes['pitlaneWidthPreviewPx']:.3f} px preview",
            "",
            "## Géométrie superposée",
            "",
            f"- Piste : `{summary['sourceGeometry']['trackOffset']}`",
            f"- Pitlane : {', '.join(f'`{item}`' for item in summary['sourceGeometry']['pitlaneOffsets'])}",
            f"- Murs : {', '.join(f'`{item}`' for item in summary['sourceGeometry']['wallOffsets'])}",
            f"- Checkpoints : {', '.join(str(item) for item in summary['sourceGeometry']['checkpointLabels'])}",
            "",
            "## Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in summary["notes"])
    lines.extend(
        [
            "",
            "## Prochaine étape",
            "",
            "Après validation visuelle, H-S05 pourra préparer la conversion finale `TrackDefinition`/données hors contrat pour la simulation fonctionnelle.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h-s02", type=Path, default=H_S02_PATH)
    parser.add_argument("--h-s03", type=Path, default=H_S03_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(load_json(args.h_s02), load_json(args.h_s03))
    (args.results_dir / SUMMARY_PATH.name).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.results_dir / REPORT_PATH.name).write_text(render_markdown(summary), encoding="utf-8", newline="\n")
    print(f"H-S04 status: {summary['status']}")
    print(f"Wrote: {args.results_dir / REPORT_PATH.name}")
    return 0 if summary["status"] == "overlay-ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
