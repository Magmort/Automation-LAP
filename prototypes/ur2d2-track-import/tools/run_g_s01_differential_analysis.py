#!/usr/bin/env python3
"""Perform a first differential analysis over the G-S00 UR2D2 .sav fixtures."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import struct
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES_ROOT = ROOT / "fixtures" / "source"
DEFAULT_RESULTS_DIR = ROOT / "results"

EXPECTED_FILES = [
    ("T00_empty_save", ["T00_empty_save.sav"]),
    ("T01_single_straight", ["T01_single_straight.sav"]),
    ("T02_simple_closed_loop", ["T02_simple_closed_loop.sav"]),
    ("T03_ai_line", ["T03_ai_line.sav"]),
    ("T04_limits_or_walls", ["T04_limits_or_walls.sav", "T04_limit_or_walls.sav"]),
    ("T05_start_and_checkpoints", ["T05_start_and_checkpoints.sav"]),
    ("T06_pit_lane", ["T06_pit_lane.sav"]),
    ("T07_surfaces", ["T07_surfaces.sav"]),
]

STRING_RE = re.compile(rb"[\x20-\x7e]{4,}")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_fixture_files(root: Path) -> list[dict[str, Any]]:
    fixtures = []
    for fixture_id, aliases in EXPECTED_FILES:
        path = next((root / alias for alias in aliases if (root / alias).is_file()), None)
        if path is None:
            directory = root / fixture_id
            if directory.is_dir():
                candidates = sorted(p for p in directory.rglob("*") if p.is_file())
                path = candidates[0] if len(candidates) == 1 else None
        if path is not None:
            fixtures.append({"fixture": fixture_id, "path": path, "data": path.read_bytes()})
    return fixtures


def common_prefix(a: bytes, b: bytes) -> int:
    count = 0
    for left, right in zip(a, b):
        if left != right:
            break
        count += 1
    return count


def common_suffix(a: bytes, b: bytes, prefix: int) -> int:
    count = 0
    maximum = min(len(a), len(b)) - prefix
    for left, right in zip(reversed(a), reversed(b)):
        if count >= maximum or left != right:
            break
        count += 1
    return count


def strings_with_offsets(data: bytes) -> list[dict[str, Any]]:
    return [
        {"offset": match.start(), "hexOffset": f"0x{match.start():04x}", "value": match.group(0).decode("ascii", "ignore")}
        for match in STRING_RE.finditer(data)
    ]


def plausible_f32(data: bytes, start: int, end: int, limit: int = 24) -> list[dict[str, Any]]:
    candidates = []
    safe_start = max(0, start)
    safe_end = min(len(data) - 4, end)
    for offset in range(safe_start, safe_end + 1):
        value = struct.unpack_from("<f", data, offset)[0]
        if not math.isfinite(value):
            continue
        if abs(value) < 1e-5 or abs(value) > 10000:
            continue
        # Keep values that look like editor coordinates, dimensions, angles or counters.
        if abs(value) <= 2048 or abs(value - round(value)) < 1e-4:
            candidates.append({"offset": offset, "hexOffset": f"0x{offset:04x}", "value": round(value, 6)})
        if len(candidates) >= limit:
            break
    return candidates


def opcodes_summary(a: bytes, b: bytes) -> list[dict[str, Any]]:
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    opcodes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        opcodes.append(
            {
                "tag": tag,
                "oldStart": i1,
                "oldEnd": i2,
                "newStart": j1,
                "newEnd": j2,
                "oldSize": i2 - i1,
                "newSize": j2 - j1,
            }
        )
    return opcodes[:40]


def compare_pair(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    a = previous["data"]
    b = current["data"]
    prefix = common_prefix(a, b)
    suffix = common_suffix(a, b, prefix)
    old_mid_start = prefix
    old_mid_end = len(a) - suffix
    new_mid_start = prefix
    new_mid_end = len(b) - suffix
    return {
        "from": previous["fixture"],
        "to": current["fixture"],
        "oldSize": len(a),
        "newSize": len(b),
        "deltaBytes": len(b) - len(a),
        "commonPrefixBytes": prefix,
        "commonSuffixBytes": suffix,
        "changedOldRange": [old_mid_start, max(old_mid_start, old_mid_end)],
        "changedNewRange": [new_mid_start, max(new_mid_start, new_mid_end)],
        "oldChangedSize": max(0, old_mid_end - old_mid_start),
        "newChangedSize": max(0, new_mid_end - new_mid_start),
        "opcodes": opcodes_summary(a, b),
        "newStringsInChangedRange": [
            item
            for item in strings_with_offsets(b)
            if new_mid_start <= item["offset"] < max(new_mid_start, new_mid_end)
        ],
        "newFloat32CandidatesInChangedRange": plausible_f32(b, new_mid_start, max(new_mid_start, new_mid_end)),
    }


def build_analysis(fixtures_root: Path) -> dict[str, Any]:
    fixtures = load_fixture_files(fixtures_root)
    fixture_summaries = []
    for fixture in fixtures:
        strings = strings_with_offsets(fixture["data"])
        fixture_summaries.append(
            {
                "fixture": fixture["fixture"],
                "path": str(fixture["path"]),
                "sizeBytes": len(fixture["data"]),
                "stringCount": len(strings),
                "strings": strings,
                "leadingFloat32": plausible_f32(fixture["data"], 0, min(len(fixture["data"]), 96), limit=12),
            }
        )

    comparisons = [compare_pair(previous, current) for previous, current in zip(fixtures, fixtures[1:])]
    status = "valid-for-g-s02-probing" if len(fixtures) == len(EXPECTED_FILES) else "partial-fixtures"
    return {
        "scenario": "G-S01",
        "status": status,
        "generatedAt": utc_now(),
        "fixturesRoot": str(fixtures_root),
        "fixtureCount": len(fixtures),
        "fixtures": fixture_summaries,
        "comparisons": comparisons,
        "initialFindings": [
            "Les sauvegardes .sav ne semblent pas compressées : chaînes lisibles et entropie basse à moyenne observées en G-S00.",
            "Le fichier commence par un float32 little-endian valant 10.0, candidat pour une largeur, échelle ou paramètre global.",
            "Les étapes ajoutent des blocs lisibles liés aux familles d'objets attendues : wall1, spr_checkpoint, checkpoint, spr_pit_building_to_right, surfaces.",
            "La géométrie de route apparaît avant les objets décoratifs/fonctionnels et contient des float32 plausibles, dont -48.0 dès T01.",
        ],
    }


def write_json(path: Path, analysis: dict[str, Any]) -> None:
    path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, analysis: dict[str, Any]) -> None:
    lines = [
        "# G-S01 - Analyse différentielle initiale des sauvegardes UR2D2",
        "",
        "- **Expérience :** G - Import du modèle minimal depuis UR2D2",
        "- **Scénario :** G-S01",
        f"- **Statut :** {analysis['status']}",
        f"- **Date :** {analysis['generatedAt']}",
        f"- **Dossier analysé :** `{analysis['fixturesRoot']}`",
        f"- **Fixtures analysées :** {analysis['fixtureCount']} / {len(EXPECTED_FILES)}",
        "- **Nature des fichiers :** sauvegardes `.sav` directement issues de l'éditeur, pas exports finaux de piste",
        "",
        "## Synthèse",
        "",
    ]
    lines.extend(f"- {finding}" for finding in analysis["initialFindings"])

    lines.extend(
        [
            "",
            "## Taille et chaînes lisibles",
            "",
            "| Fixture | Taille | Chaînes lisibles principales |",
            "| --- | ---: | --- |",
        ]
    )
    for fixture in analysis["fixtures"]:
        strings = ", ".join(f"`{item['value']}`@{item['hexOffset']}" for item in fixture["strings"][:8]) or "-"
        lines.append(f"| {fixture['fixture']} | {fixture['sizeBytes']} | {strings} |")

    lines.extend(
        [
            "",
            "## Deltas successifs",
            "",
            "| Transition | Delta | Préfixe commun | Suffixe commun | Zone nouvelle | Chaînes nouvelles | Candidats float32 |",
            "| --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for comparison in analysis["comparisons"]:
        new_range = comparison["changedNewRange"]
        strings = ", ".join(
            f"`{item['value']}`@{item['hexOffset']}" for item in comparison["newStringsInChangedRange"][:5]
        ) or "-"
        floats = ", ".join(
            f"{item['value']}@{item['hexOffset']}" for item in comparison["newFloat32CandidatesInChangedRange"][:6]
        ) or "-"
        lines.append(
            f"| {comparison['from']} -> {comparison['to']} | {comparison['deltaBytes']} | "
            f"{comparison['commonPrefixBytes']} | {comparison['commonSuffixBytes']} | "
            f"`0x{new_range[0]:04x}..0x{new_range[1]:04x}` ({comparison['newChangedSize']} o) | "
            f"{strings} | {floats} |"
        )

    lines.extend(
        [
            "",
            "## Interprétation provisoire",
            "",
            "- Les fixtures sont suffisantes pour commencer G-S02 sur un lecteur brut exploratoire.",
            "- La prochaine cible est d'isoler la table de route avec T00/T01/T02, puis la table d'objets avec T04/T05/T06/T07.",
            "- Aucune transformation vers `TrackDefinition` ne doit encore être figée : les offsets et structures restent hypothétiques.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures-root", type=Path, default=DEFAULT_FIXTURES_ROOT)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis(args.fixtures_root.resolve())
    write_json(results_dir / "g_s01_differential_analysis.json", analysis)
    write_markdown(results_dir / "G_S01_DIFFERENTIAL_ANALYSIS_RESULT.md", analysis)
    print(f"G-S01 status: {analysis['status']}")
    print(f"Analysed fixtures: {analysis['fixtureCount']} / {len(EXPECTED_FILES)}")
    print(f"Wrote: {results_dir / 'G_S01_DIFFERENTIAL_ANALYSIS_RESULT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
