#!/usr/bin/env python3
"""Render D-S06 traffic synthesis as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1240
HEIGHT = 760
COLORS = {
    "ok": "#2f9d68",
    "reserve": "#d5a12b",
    "ink": "#222222",
    "muted": "#5f625d",
    "paper": "#f7f7f3",
    "panel": "#ffffff",
    "line": "#c9c9c2",
    "blue": "#2f7ed8",
    "red": "#d84a3a",
}


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def bar(x: float, y: float, width: float, height: float, ratio: float, color: str, label: str) -> list[str]:
    ratio = max(0.0, min(1.0, ratio))
    fill_width = width * ratio
    return [
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" rx="4" fill="#ecece7" />',
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{fill_width:.2f}" height="{height:.2f}" rx="4" fill="{color}" />',
        f'<text x="{x + width + 14:.2f}" y="{y + height - 4:.2f}" font-size="13">{html.escape(label)}</text>',
    ]


def scenario_card(index: int, scenario: dict[str, Any]) -> list[str]:
    x = 54 + index * 224
    y = 136
    status_color = COLORS["ok"] if scenario["success"] else COLORS["red"]
    return [
        f'<rect x="{x}" y="{y}" width="198" height="132" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
        f'<circle cx="{x + 24}" cy="{y + 30}" r="10" fill="{status_color}" />',
        f'<text x="{x + 42}" y="{y + 34}" font-size="16" font-weight="700">{html.escape(scenario["id"])}</text>',
        f'<text x="{x + 18}" y="{y + 66}" font-size="13">{html.escape(scenario["label"])}</text>',
        f'<text x="{x + 18}" y="{y + 92}" font-size="12" fill="{COLORS["muted"]}">{html.escape(scenario["status"])}</text>',
        f'<text x="{x + 18}" y="{y + 116}" font-size="12" fill="{COLORS["muted"]}">preuve conservee</text>',
    ]


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["globalMetrics"]
    scenario_count = max(float(metrics["scenarioCount"]), 1.0)
    success_ratio = float(metrics["successfulScenarioCount"]) / scenario_count
    decision_ratio = float(metrics["matchedDecisionCaseCount"]) / max(float(metrics["decisionCaseCount"]), 1.0)
    no_contact_ratio = 1.0 if int(metrics["totalContactTicks"]) == 0 else 0.0
    no_offtrack_ratio = 1.0 if int(metrics["totalOffTrackTicks"]) == 0 else 0.0
    bars = []
    bars.extend(bar(74, 344, 390, 24, success_ratio, COLORS["ok"], f'{metrics["successfulScenarioCount"]}/{metrics["scenarioCount"]} scenarios conformes'))
    bars.extend(bar(74, 392, 390, 24, decision_ratio, COLORS["blue"], f'{metrics["matchedDecisionCaseCount"]}/{metrics["decisionCaseCount"]} decisions conformes'))
    bars.extend(bar(74, 440, 390, 24, no_contact_ratio, COLORS["ok"], f'{metrics["totalContactTicks"]} contact ticks'))
    bars.extend(bar(74, 488, 390, 24, no_offtrack_ratio, COLORS["ok"], f'{metrics["totalOffTrackTicks"]} hors-piste'))

    capability_y = 336
    capability_rows = []
    for index, capability in enumerate(summary["capabilities"]):
        y = capability_y + index * 46
        status_color = COLORS["ok"] if capability["status"] == "validee" else COLORS["reserve"]
        capability_rows.extend(
            [
                f'<circle cx="630" cy="{y}" r="6" fill="{status_color}" />',
                f'<text x="646" y="{y + 5}" font-size="13" font-weight="700">{html.escape(capability["capability"])}</text>',
                f'<text x="646" y="{y + 25}" font-size="12" fill="{COLORS["muted"]}">{html.escape(capability["evidence"])}</text>',
            ]
        )

    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">D-S06 traffic synthesis</title>',
            '<desc id="desc">Consolidated validation status for traffic and overtaking experiment D.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">D-S06 - Synthese trafic</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">Decision : {html.escape(summary["decision"])} - temps dynamique {metrics["totalSimulatedDynamicTimeS"]:.0f} s</text>',
            *[element for index, scenario in enumerate(summary["scenarios"]) for element in scenario_card(index, scenario)],
            '<rect x="54" y="306" width="500" height="248" rx="7" fill="#ffffff" stroke="#c9c9c2" />',
            '<text x="74" y="332" font-size="16" font-weight="700">Indicateurs consolides</text>',
            *bars,
            '<rect x="598" y="306" width="586" height="294" rx="7" fill="#ffffff" stroke="#c9c9c2" />',
            '<text x="622" y="332" font-size="16" font-weight="700">Capacites couvertes</text>',
            *capability_rows,
            '<rect x="54" y="622" width="1130" height="76" rx="7" fill="#ffffff" stroke="#c9c9c2" />',
            '<text x="74" y="650" font-size="15" font-weight="700">Reserve de conclusion</text>',
            '<text x="74" y="676" font-size="13" fill="#5f625d">Validation nominale et deterministe : interactions longues, denses, contestees et performance restent a couvrir par E/F ou par de futurs cas D et production.</text>',
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render D-S06 traffic synthesis visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "d_s06_traffic_summary.json",
        help="D-S06 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results" / "D_S06_TRAFFIC_SUMMARY_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("D-S06 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
