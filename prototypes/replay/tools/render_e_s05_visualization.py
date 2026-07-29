#!/usr/bin/env python3
"""Render E-S05 compatibility checks as a standalone SVG."""

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
    "reject": "#d84a3a",
    "warn": "#d2842f",
    "blue": "#2f7ed8",
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


def pill(x: int, y: int, text: str, color: str) -> str:
    width = 18 + len(text) * 7
    return (
        f'<rect x="{x}" y="{y - 17}" width="{width}" height="24" rx="5" fill="{color}" opacity="0.12" stroke="{color}" />'
        f'<text x="{x + 9}" y="{y}" font-size="12" fill="{color}" font-weight="700">{html.escape(text)}</text>'
    )


def render_case_rows(summary: dict[str, Any]) -> list[str]:
    elements = [
        '<text x="84" y="252" font-size="16" font-weight="700">Matrice de compatibilite</text>',
        '<text x="84" y="286" font-size="12" fill="#5f625d">cas</text>',
        '<text x="386" y="286" font-size="12" fill="#5f625d">attendu</text>',
        '<text x="516" y="286" font-size="12" fill="#5f625d">obtenu</text>',
        '<text x="646" y="286" font-size="12" fill="#5f625d">code obtenu</text>',
        '<text x="934" y="286" font-size="12" fill="#5f625d">validation</text>',
    ]
    for index, case in enumerate(summary["cases"]):
        y = 320 + index * 42
        fill = "#fbfbf8" if index % 2 == 0 else "#ffffff"
        result_color = COLORS["ok"] if case["success"] else COLORS["warn"]
        actual_color = COLORS["ok"] if case["actualCanLoad"] else COLORS["reject"]
        expected_text = "ACCEPT" if case["expectedCanLoad"] else "REJECT"
        actual_text = "ACCEPT" if case["actualCanLoad"] else "REJECT"
        elements.append(f'<rect x="74" y="{y - 27}" width="1088" height="36" rx="4" fill="{fill}" stroke="#ecece7" />')
        elements.append(f'<text x="84" y="{y}" font-size="13" font-weight="700">{html.escape(case["caseId"])}</text>')
        elements.append(pill(386, y, expected_text, COLORS["blue"]))
        elements.append(pill(516, y, actual_text, actual_color))
        elements.append(f'<text x="646" y="{y}" font-size="13">{html.escape(case["actualErrorCode"])}</text>')
        elements.append(pill(934, y, "OK" if case["success"] else "MISMATCH", result_color))
    return elements


def render_summary_cards(summary: dict[str, Any]) -> list[str]:
    metrics = summary["metrics"]
    cards = [
        ("Cas testes", str(metrics["caseCount"]), COLORS["blue"]),
        ("Acceptes", str(metrics["actualAcceptCount"]), COLORS["ok"]),
        ("Refuses", str(metrics["actualRejectCount"]), COLORS["reject"]),
        ("Mismatches", str(metrics["mismatchCount"]), COLORS["warn"]),
    ]
    elements = []
    for index, (label, value, color) in enumerate(cards):
        x = 74 + index * 274
        elements.append(f'<rect x="{x}" y="132" width="242" height="82" rx="7" fill="#ffffff" stroke="{COLORS["line"]}" />')
        elements.append(f'<text x="{x + 18}" y="164" font-size="13" fill="{COLORS["muted"]}">{html.escape(label)}</text>')
        elements.append(f'<text x="{x + 18}" y="196" font-size="28" font-weight="700" fill="{color}">{html.escape(value)}</text>')
    return elements


def render_svg(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">E-S05 replay version compatibility</title>',
            '<desc id="desc">Replay compatibility reader accepts current schema and rejects incompatible cases.</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["paper"]}" />',
            '<g font-family="Arial, sans-serif" fill="#222">',
            '<text x="54" y="70" font-size="26" font-weight="700">E-S05 - Compatibilite replay</text>',
            f'<text x="54" y="102" font-size="15" fill="{COLORS["muted"]}">Versions supportees: {html.escape(", ".join(summary["supportedSchemaVersions"]))}; attentes respectees: {metrics["successfulCaseCount"]}/{metrics["caseCount"]}</text>',
            *render_summary_cards(summary),
            f'<rect x="54" y="232" width="1130" height="508" rx="7" fill="{COLORS["panel"]}" stroke="{COLORS["line"]}" />',
            *render_case_rows(summary),
            "</g>",
            "</svg>",
            "",
        ]
    )


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Render E-S05 compatibility visualization.")
    parser.add_argument(
        "--summary",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s05_version_compatibility_summary.json",
        help="E-S05 summary JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "E_S05_VERSION_COMPATIBILITY_VISUALIZATION.svg",
        help="SVG output path.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = load_json(arguments.summary)
    if not summary["success"]:
        raise RuntimeError("E-S05 failed; visualization was not generated")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render_svg(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {arguments.output.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
