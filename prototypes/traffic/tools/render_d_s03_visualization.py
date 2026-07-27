#!/usr/bin/env python3
"""Render D-S03 overtake candidate decisions as a standalone SVG."""

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

WIDTH = 1280
HEIGHT = 900
PADDING = 40
COLORS = {
    "ego": "#2f7ed8",
    "leader": "#d84a3a",
    "traffic": "#6f4bb2",
    "candidate": "#2f9d68",
    "blocked": "#b23b3b",
    "track": "#d6d6cf",
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


def render_case_panel(case: dict[str, Any], x: float, y: float, width: float, height: float) -> list[str]:
    lane_y_center = y + height * 0.52
    current_y = lane_y_center - 28
    candidate_y = lane_y_center + 42
    s_min = 15.0
    s_max = 95.0

    def px(progress_m: float) -> float:
        return x + 26 + (width - 52) * (progress_m - s_min) / (s_max - s_min)

    elements = [
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" rx="6" fill="#ffffff" stroke="#c9c9c2" />',
        f'<text x="{x + 18:.2f}" y="{y + 28:.2f}" font-size="15" font-weight="700">{html.escape(case["label"])}</text>',
        f'<text x="{x + width - 78:.2f}" y="{y + 28:.2f}" font-size="13" font-weight="700" fill="{COLORS["candidate"] if case["actualDecision"] else COLORS["blocked"]}">{ "GO" if case["actualDecision"] else "NO GO" }</text>',
        f'<line x1="{x + 22:.2f}" y1="{current_y:.2f}" x2="{x + width - 22:.2f}" y2="{current_y:.2f}" stroke="#76766f" stroke-width="2" />',
        f'<line x1="{x + 22:.2f}" y1="{candidate_y:.2f}" x2="{x + width - 22:.2f}" y2="{candidate_y:.2f}" stroke="{COLORS["candidate"]}" stroke-width="2" stroke-dasharray="8 7" />',
        f'<text x="{x + 22:.2f}" y="{current_y - 12:.2f}" font-size="11" fill="#555">ligne actuelle</text>',
        f'<text x="{x + 22:.2f}" y="{candidate_y - 12:.2f}" font-size="11" fill="#555">ligne candidate</text>',
    ]
    for vehicle in case["vehicles"]:
        role = vehicle["role"]
        color = COLORS.get(role, COLORS["traffic"])
        vy = candidate_y if abs(vehicle["lateralOffsetM"] - case["candidateOffsetM"]) <= 1.2 else current_y
        vx = px(vehicle["progressM"])
        elements.extend(
            [
                f'<rect x="{vx - 10:.2f}" y="{vy - 8:.2f}" width="20" height="16" rx="3" fill="{color}" stroke="#202020" />',
                f'<text x="{vx + 13:.2f}" y="{vy + 4:.2f}" font-size="11">{html.escape(vehicle["label"])}</text>',
            ]
        )
    front = case["currentFront"]
    front_text = "front n/a" if front is None else f"front {front['id']} / TTC {front['timeToCatchS']:.2f}s"
    blockers = ", ".join(f"{item['where']}:{item['id']}" for item in case["candidateBlockers"]) or "clear"
    reason = ", ".join(case["reasons"])
    elements.extend(
        [
            f'<text x="{x + 18:.2f}" y="{y + height - 48:.2f}" font-size="12">{html.escape(front_text)}</text>',
            f'<text x="{x + 18:.2f}" y="{y + height - 30:.2f}" font-size="12">candidate: {html.escape(blockers)}</text>',
            f'<text x="{x + 18:.2f}" y="{y + height - 12:.2f}" font-size="12" fill="#555">{html.escape(reason)}</text>',
        ]
    )
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    panels: list[str] = []
    panel_width = 580
    panel_height = 182
    positions = [
        (PADDING, 92),
        (PADDING + panel_width + 38, 92),
        (PADDING, 318),
        (PADDING + panel_width + 38, 318),
    ]
    for case, (x, y) in zip(summary["caseResults"], positions):
        panels.extend(render_case_panel(case, x, y, panel_width, panel_height))
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">D-S03 overtake candidate decisions</title>',
            '<desc id="desc">Four static traffic cases showing current lane, candidate lane, blockers and overtake decision.</desc>',
            '<rect width="100%" height="100%" fill="#f7f7f3" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="40" y="48" font-size="22" font-weight="700">D-S03 - declenchement de depassement candidat</text>',
            '<text x="40" y="72" font-size="13" fill="#555">La decision ne deplace pas encore la voiture : elle choisit seulement si la ligne candidate est libre.</text>',
            *panels,
            '<rect x="40" y="570" width="1200" height="120" rx="6" fill="#ffffff" stroke="#c9c9c2" />',
            f'<text x="66" y="604" font-size="15" font-weight="700">Synthese</text>',
            f'<text x="66" y="632" font-size="13">cas conformes : {metrics["matchedCases"]} / {metrics["caseCount"]}</text>',
            f'<text x="310" y="632" font-size="13">decisions positives : {metrics["positiveDecisions"]}</text>',
            f'<text x="560" y="632" font-size="13">decisions negatives : {metrics["negativeDecisions"]}</text>',
            f'<text x="810" y="632" font-size="13">cas bloques par ligne candidate : {metrics["blockedCandidateCases"]}</text>',
            f'<circle cx="66" cy="666" r="5" fill="{COLORS["ego"]}" /><text x="80" y="670" font-size="12">Ego</text>',
            f'<circle cx="150" cy="666" r="5" fill="{COLORS["leader"]}" /><text x="164" y="670" font-size="12">Leader lent</text>',
            f'<circle cx="270" cy="666" r="5" fill="{COLORS["traffic"]}" /><text x="284" y="670" font-size="12">Trafic adjacent</text>',
            f'<line x1="420" y1="666" x2="452" y2="666" stroke="{COLORS["candidate"]}" stroke-width="2" stroke-dasharray="8 7" /><text x="462" y="670" font-size="12">Ligne candidate</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render the D-S03 overtake candidate visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "d_s03_overtake_candidate_summary.json",
        help="D-S03 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "D_S03_OVERTAKE_CANDIDATE_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("D-S03 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
