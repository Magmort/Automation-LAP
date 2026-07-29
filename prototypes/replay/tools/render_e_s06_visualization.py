#!/usr/bin/env python3
"""Render E-S06 replay summary as a standalone SVG."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

WIDTH = 1240
HEIGHT = 820
COLORS = {
    "paper": "#f7f7f3",
    "panel": "#ffffff",
    "line": "#c9c9c2",
    "ink": "#222222",
    "muted": "#5f625d",
    "ok": "#2f9d68",
    "blue": "#2f7ed8",
    "purple": "#6f4bb2",
    "warn": "#d2842f",
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


def render_proof_chain(summary: dict[str, Any]) -> list[str]:
    labels = [
        ("E-S01", "Autonome"),
        ("E-S02", "Navigation"),
        ("E-S03", "Evenements"),
        ("E-S04", "Taille"),
        ("E-S05", "Version"),
    ]
    x0 = 94
    y = 238
    gap = 204
    elements = ['<text x="84" y="176" font-size="16" font-weight="700">Preuves validees</text>']
    for index, (scenario, label) in enumerate(labels):
        x = x0 + index * gap
        if index > 0:
            elements.append(f'<line x1="{x - 126}" y1="{y}" x2="{x - 52}" y2="{y}" stroke="{COLORS["line"]}" stroke-width="4" />')
        elements.append(f'<circle cx="{x}" cy="{y}" r="44" fill="{COLORS["ok"]}" opacity="0.14" stroke="{COLORS["ok"]}" stroke-width="3" />')
        elements.append(f'<text x="{x}" y="{y - 4}" font-size="16" font-weight="700" text-anchor="middle" fill="{COLORS["ok"]}">{scenario}</text>')
        elements.append(f'<text x="{x}" y="{y + 18}" font-size="12" text-anchor="middle" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
    return elements


def render_metric_cards(summary: dict[str, Any]) -> list[str]:
    metrics = summary["metrics"]
    cards = [
        ("Replay", f"{metrics['durationS']:.0f}s / {metrics['frameCount']} frames", COLORS["blue"]),
        ("Taille 4 Hz", f"{metrics['replayFileBytes'] // 1000} kB", COLORS["purple"]),
        ("Echantillonnage", f"{metrics['samplingMinFileBytes'] // 1000}-{metrics['samplingMaxFileBytes'] // 1000} kB", COLORS["warn"]),
        ("Compatibilite", f"{metrics['compatibilityMismatchCount']} mismatch", COLORS["ok"]),
    ]
    elements = []
    for index, (label, value, color) in enumerate(cards):
        x = 74 + index * 274
        elements.append(f'<rect x="{x}" y="332" width="242" height="86" rx="7" fill="#ffffff" stroke="{COLORS["line"]}" />')
        elements.append(f'<text x="{x + 18}" y="366" font-size="13" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
        elements.append(f'<text x="{x + 18}" y="398" font-size="24" font-weight="700" fill="{color}">{html.escape(value)}</text>')
    return elements


def render_contract(summary: dict[str, Any]) -> list[str]:
    contract = summary["candidateContract"]
    rows = [
        ("Kind", contract["kind"]),
        ("Schema", contract["schemaVersion"]),
        ("Unites", "s, m, m/s, rad"),
        ("Telemetrie", "4 Hz reference; 1 a 20 Hz mesures"),
        ("Keyframes", "1 s"),
        ("Version", "accept-list stricte"),
    ]
    elements = ['<text x="84" y="496" font-size="16" font-weight="700">Contrat candidat</text>']
    for index, (label, value) in enumerate(rows):
        y = 532 + index * 34
        elements.append(f'<text x="94" y="{y}" font-size="13" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
        elements.append(f'<text x="254" y="{y}" font-size="13" font-weight="700">{html.escape(value)}</text>')
    return elements


def render_risks(summary: dict[str, Any]) -> list[str]:
    risks = summary["residualRisks"][:4]
    elements = ['<text x="684" y="496" font-size="16" font-weight="700">Reserves</text>']
    for index, risk in enumerate(risks):
        y = 532 + index * 46
        elements.append(f'<circle cx="694" cy="{y - 4}" r="5" fill="{COLORS["warn"]}" />')
        elements.append(f'<text x="714" y="{y}" font-size="13" fill="{COLORS["ink"]}">{html.escape(risk[:76])}</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">E-S06 replay minimal summary</title>',
            '<desc id="desc">Replay minimal feasibility synthesis and decision.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">E-S06 - Synthese replay minimal</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">Decision: {html.escape(summary["decision"])}; confiance {html.escape(summary["confidence"])}; scenarios {metrics["validatedScenarioCount"]}/{metrics["scenarioCount"]}</text>',
            f'<rect x="54" y="132" width="1130" height="174" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_proof_chain(summary),
            *render_metric_cards(summary),
            f'<rect x="54" y="456" width="544" height="256" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_contract(summary),
            f'<rect x="644" y="456" width="540" height="256" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_risks(summary),
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render E-S06 replay summary visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s06_replay_summary.json",
        help="E-S06 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "E_S06_REPLAY_SUMMARY_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("E-S06 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
