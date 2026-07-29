#!/usr/bin/env python3
"""Inventory UR2D2 Track Editor fixture folders for Experiment G-S00."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES_ROOT = ROOT / "fixtures" / "source"
DEFAULT_RESULTS_DIR = ROOT / "results"

EXPECTED_FIXTURES = [
    ("T00_empty_save", "Circuit vide enregistré", ["T00_empty_save.sav"]),
    ("T01_single_straight", "Route droite unique", ["T01_single_straight.sav"]),
    ("T02_simple_closed_loop", "Boucle simple fermée", ["T02_simple_closed_loop.sav"]),
    ("T03_ai_line", "Ligne IA ajoutée", ["T03_ai_line.sav"]),
    ("T04_limits_or_walls", "Limites ou murs ajoutés", ["T04_limits_or_walls.sav", "T04_limit_or_walls.sav"]),
    ("T05_start_and_checkpoints", "Départ et checkpoints", ["T05_start_and_checkpoints.sav"]),
    ("T06_pit_lane", "Voie des stands", ["T06_pit_lane.sav"]),
    ("T07_surfaces", "Surfaces distinctes", ["T07_surfaces.sav"]),
]

TEXT_BYTES = set(range(32, 127)) | {9, 10, 13}
STRING_RE = re.compile(rb"[\x20-\x7e]{4,}")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shannon_entropy(sample: bytes) -> float:
    if not sample:
        return 0.0
    counts = [0] * 256
    for byte in sample:
        counts[byte] += 1
    length = len(sample)
    entropy = 0.0
    for count in counts:
        if count:
            probability = count / length
            entropy -= probability * math.log2(probability)
    return entropy


def detect_signature(data: bytes) -> str:
    if data.startswith(b"PK\x03\x04"):
        return "zip"
    if data.startswith(b"\x1f\x8b"):
        return "gzip"
    if data.startswith(b"\x04\x22\x4d\x18"):
        return "lz4-frame"
    if len(data) >= 2 and data[0] == 0x78 and data[1] in {0x01, 0x5E, 0x9C, 0xDA}:
        return "zlib-candidate"
    if data.startswith(b"SQLite format 3\x00"):
        return "sqlite"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"BM"):
        return "bmp"
    if data.startswith(b"OggS"):
        return "ogg"
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "wav"
    stripped = data.lstrip()
    if stripped.startswith((b"{", b"[")):
        return "json-or-text"
    if data and all(byte in TEXT_BYTES for byte in data[: min(len(data), 4096)]):
        return "text"
    return "unknown-binary"


def extract_strings(data: bytes, limit: int) -> list[str]:
    strings: list[str] = []
    for match in STRING_RE.finditer(data):
        value = match.group(0).decode("ascii", errors="ignore").strip()
        if value and value not in strings:
            strings.append(value)
        if len(strings) >= limit:
            break
    return strings


def inspect_file(path: Path, fixture_root: Path, string_limit: int, rel_path_override: str | None = None) -> dict[str, Any]:
    stat = path.stat()
    with path.open("rb") as handle:
        sample = handle.read(65536)
    rel_path = rel_path_override or path.relative_to(fixture_root).as_posix()
    return {
        "path": rel_path,
        "sourcePath": str(path),
        "sizeBytes": stat.st_size,
        "modifiedUtc": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "sha256": sha256_file(path),
        "firstBytesHex": sample[:32].hex(" "),
        "signature": detect_signature(sample),
        "entropy64k": round(shannon_entropy(sample), 4),
        "strings": extract_strings(sample, string_limit),
    }


def inventory_fixture(fixture_source: Path, canonical_name: str, string_limit: int) -> dict[str, Any]:
    files = []
    source_kind = "directory"
    if fixture_source.is_file():
        source_kind = "file"
        files.append(inspect_file(fixture_source, fixture_source.parent, string_limit, "track.sav"))
    else:
        for path in sorted(fixture_source.rglob("*")):
            if path.is_file():
                files.append(inspect_file(path, fixture_source, string_limit))
    total_size = sum(file_info["sizeBytes"] for file_info in files)
    signatures: dict[str, int] = {}
    for file_info in files:
        signatures[file_info["signature"]] = signatures.get(file_info["signature"], 0) + 1
    return {
        "fixture": canonical_name,
        "exists": True,
        "sourceKind": source_kind,
        "sourcePath": str(fixture_source),
        "fileCount": len(files),
        "totalSizeBytes": total_size,
        "signatures": dict(sorted(signatures.items())),
        "files": files,
    }


def empty_fixture(name: str, purpose: str) -> dict[str, Any]:
    return {
        "fixture": name,
        "purpose": purpose,
        "exists": False,
        "sourceKind": None,
        "sourcePath": None,
        "fileCount": 0,
        "totalSizeBytes": 0,
        "signatures": {},
        "files": [],
    }


def compare_fixtures(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    previous_files = {file_info["path"]: file_info for file_info in previous.get("files", [])}
    current_files = {file_info["path"]: file_info for file_info in current.get("files", [])}
    previous_paths = set(previous_files)
    current_paths = set(current_files)
    added = sorted(current_paths - previous_paths)
    removed = sorted(previous_paths - current_paths)
    modified = sorted(
        path
        for path in previous_paths & current_paths
        if previous_files[path]["sha256"] != current_files[path]["sha256"]
    )
    unchanged = sorted(
        path
        for path in previous_paths & current_paths
        if previous_files[path]["sha256"] == current_files[path]["sha256"]
    )
    return {
        "from": previous["fixture"],
        "to": current["fixture"],
        "addedCount": len(added),
        "removedCount": len(removed),
        "modifiedCount": len(modified),
        "unchangedCount": len(unchanged),
        "added": added[:50],
        "removed": removed[:50],
        "modified": modified[:50],
    }


def build_summary(fixtures_root: Path, string_limit: int) -> dict[str, Any]:
    fixtures = []
    for name, purpose, aliases in EXPECTED_FIXTURES:
        fixture_dir = fixtures_root / name
        if fixture_dir.is_dir():
            fixture = inventory_fixture(fixture_dir, name, string_limit)
            fixture["purpose"] = purpose
            fixtures.append(fixture)
        else:
            fixture_file = next((fixtures_root / alias for alias in aliases if (fixtures_root / alias).is_file()), None)
            if fixture_file is not None:
                fixture = inventory_fixture(fixture_file, name, string_limit)
                fixture["purpose"] = purpose
                fixtures.append(fixture)
            else:
                fixtures.append(empty_fixture(name, purpose))

    comparisons = []
    for previous, current in zip(fixtures, fixtures[1:]):
        if previous["exists"] and current["exists"]:
            comparisons.append(compare_fixtures(previous, current))

    observed = [fixture for fixture in fixtures if fixture["exists"]]
    high_entropy_unknown = []
    readable_candidates = []
    for fixture in observed:
        for file_info in fixture["files"]:
            if file_info["signature"] == "unknown-binary" and file_info["entropy64k"] >= 7.5:
                high_entropy_unknown.append(
                    {"fixture": fixture["fixture"], "path": file_info["path"], "entropy64k": file_info["entropy64k"]}
                )
            if file_info["strings"]:
                readable_candidates.append(
                    {
                        "fixture": fixture["fixture"],
                        "path": file_info["path"],
                        "signature": file_info["signature"],
                        "strings": file_info["strings"][:5],
                    }
                )

    status = "ready-for-differential-analysis" if len(observed) >= 2 else "awaiting-fixtures"
    if len(observed) >= len(EXPECTED_FIXTURES):
        status = "complete-inventory"

    return {
        "scenario": "G-S00",
        "status": status,
        "generatedAt": utc_now(),
        "fixturesRoot": str(fixtures_root),
        "expectedFixtureCount": len(EXPECTED_FIXTURES),
        "observedFixtureCount": len(observed),
        "fixtures": fixtures,
        "comparisons": comparisons,
        "globalHints": {
            "highEntropyUnknownFiles": high_entropy_unknown[:50],
            "readableStringCandidates": readable_candidates[:50],
        },
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# G-S00 - Inventaire des fichiers UR2D2",
        "",
        "- **Expérience :** G - Import du modèle minimal depuis UR2D2",
        "- **Scénario :** G-S00",
        f"- **Statut :** {summary['status']}",
        f"- **Date :** {summary['generatedAt']}",
        f"- **Dossier analysé :** `{summary['fixturesRoot']}`",
        f"- **Fixtures observées :** {summary['observedFixtureCount']} / {summary['expectedFixtureCount']}",
        "",
        "## Couverture",
        "",
        "| Fixture | Présente | Fichiers | Taille totale | Signatures |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for fixture in summary["fixtures"]:
        signatures = ", ".join(f"{key}: {value}" for key, value in fixture["signatures"].items()) or "-"
        present = "oui" if fixture["exists"] else "non"
        lines.append(
            f"| {fixture['fixture']} | {present} | {fixture['fileCount']} | {fixture['totalSizeBytes']} | {signatures} |"
        )

    lines.extend(["", "## Comparaisons successives", ""])
    if summary["comparisons"]:
        lines.extend(
            [
                "| De | Vers | Ajoutés | Modifiés | Supprimés | Inchangés |",
                "| --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for comparison in summary["comparisons"]:
            lines.append(
                f"| {comparison['from']} | {comparison['to']} | {comparison['addedCount']} | "
                f"{comparison['modifiedCount']} | {comparison['removedCount']} | {comparison['unchangedCount']} |"
            )
    else:
        lines.append("Aucune comparaison disponible : il faut au moins deux fixtures présentes.")

    lines.extend(["", "## Indices initiaux", ""])
    high_entropy = summary["globalHints"]["highEntropyUnknownFiles"]
    readable = summary["globalHints"]["readableStringCandidates"]
    lines.append(f"- Fichiers binaires inconnus à forte entropie : {len(high_entropy)}")
    lines.append(f"- Fichiers ou échantillons contenant des chaînes lisibles : {len(readable)}")

    if readable:
        lines.extend(["", "### Exemples de chaînes lisibles", ""])
        for item in readable[:10]:
            strings = " ; ".join(item["strings"])
            lines.append(f"- `{item['fixture']}/{item['path']}` ({item['signature']}) : {strings}")

    lines.extend(
        [
            "",
            "## Prochaine étape",
            "",
            "Quand au moins T00 et T01 sont présents, l'inventaire peut alimenter G-S01 pour isoler les structures modifiées par la géométrie.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures-root", type=Path, default=DEFAULT_FIXTURES_ROOT)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--string-limit", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args.fixtures_root.resolve(), max(0, args.string_limit))
    write_json(results_dir / "g_s00_inventory_summary.json", summary)
    write_markdown(results_dir / "G_S00_INVENTORY_RESULT.md", summary)
    print(f"G-S00 inventory status: {summary['status']}")
    print(f"Observed fixtures: {summary['observedFixtureCount']} / {summary['expectedFixtureCount']}")
    print(f"Wrote: {results_dir / 'G_S00_INVENTORY_RESULT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
