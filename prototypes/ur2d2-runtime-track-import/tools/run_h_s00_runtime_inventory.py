#!/usr/bin/env python3
"""Inventory final/runtime UR2D2 track files for Experiment H-S00."""

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
    entropy = 0.0
    length = len(sample)
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
    if data.startswith(b"DDS "):
        return "dds"
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


def inspect_file(path: Path, root: Path, string_limit: int) -> dict[str, Any]:
    stat = path.stat()
    with path.open("rb") as handle:
        sample = handle.read(65536)
    return {
        "path": path.relative_to(root).as_posix(),
        "sizeBytes": stat.st_size,
        "modifiedUtc": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "sha256": sha256_file(path),
        "extension": path.suffix.lower(),
        "firstBytesHex": sample[:32].hex(" "),
        "signature": detect_signature(sample),
        "entropy64k": round(shannon_entropy(sample), 4),
        "strings": extract_strings(sample, string_limit),
    }


def discover_entries(fixtures_root: Path) -> list[Path]:
    if not fixtures_root.exists():
        return []
    return sorted(path for path in fixtures_root.iterdir() if path.is_dir() or path.is_file())


def inventory_entry(entry: Path, string_limit: int) -> dict[str, Any]:
    if entry.is_file():
        files = [inspect_file(entry, entry.parent, string_limit)]
        source_kind = "file"
    else:
        files = [inspect_file(path, entry, string_limit) for path in sorted(entry.rglob("*")) if path.is_file()]
        source_kind = "directory"

    signatures: dict[str, int] = {}
    extensions: dict[str, int] = {}
    for file_info in files:
        signatures[file_info["signature"]] = signatures.get(file_info["signature"], 0) + 1
        extension = file_info["extension"] or "<none>"
        extensions[extension] = extensions.get(extension, 0) + 1

    return {
        "fixture": entry.stem if entry.is_file() else entry.name,
        "sourceKind": source_kind,
        "sourcePath": str(entry),
        "fileCount": len(files),
        "totalSizeBytes": sum(file_info["sizeBytes"] for file_info in files),
        "signatures": dict(sorted(signatures.items())),
        "extensions": dict(sorted(extensions.items())),
        "files": files,
    }


def build_summary(fixtures_root: Path, string_limit: int) -> dict[str, Any]:
    entries = discover_entries(fixtures_root)
    fixtures = [inventory_entry(entry, string_limit) for entry in entries]
    archive_candidates = []
    readable_candidates = []
    high_entropy_unknown = []
    for fixture in fixtures:
        for file_info in fixture["files"]:
            if file_info["signature"] in {"zip", "gzip", "lz4-frame", "zlib-candidate"}:
                archive_candidates.append({"fixture": fixture["fixture"], "path": file_info["path"], "signature": file_info["signature"]})
            if file_info["strings"]:
                readable_candidates.append(
                    {
                        "fixture": fixture["fixture"],
                        "path": file_info["path"],
                        "signature": file_info["signature"],
                        "strings": file_info["strings"][:5],
                    }
                )
            if file_info["signature"] == "unknown-binary" and file_info["entropy64k"] >= 7.5:
                high_entropy_unknown.append(
                    {"fixture": fixture["fixture"], "path": file_info["path"], "entropy64k": file_info["entropy64k"]}
                )

    status = "ready-for-h-s01-comparison" if fixtures else "awaiting-track-files"
    return {
        "scenario": "H-S00",
        "status": status,
        "generatedAt": utc_now(),
        "fixturesRoot": str(fixtures_root),
        "fixtureCount": len(fixtures),
        "totalFileCount": sum(fixture["fileCount"] for fixture in fixtures),
        "totalSizeBytes": sum(fixture["totalSizeBytes"] for fixture in fixtures),
        "fixtures": fixtures,
        "globalHints": {
            "archiveCandidates": archive_candidates[:50],
            "highEntropyUnknownFiles": high_entropy_unknown[:50],
            "readableStringCandidates": readable_candidates[:50],
        },
    }


def write_json(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# H-S00 - Inventaire des vrais fichiers de tracks UR2D2",
        "",
        "- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2",
        "- **Scénario :** H-S00",
        f"- **Statut :** {summary['status']}",
        f"- **Date :** {summary['generatedAt']}",
        f"- **Dossier analysé :** `{summary['fixturesRoot']}`",
        f"- **Fixtures observées :** {summary['fixtureCount']}",
        f"- **Fichiers observés :** {summary['totalFileCount']}",
        f"- **Taille totale :** {summary['totalSizeBytes']} octets",
        "",
        "## Couverture",
        "",
    ]

    if summary["fixtures"]:
        lines.extend(
            [
                "| Fixture | Source | Fichiers | Taille | Extensions | Signatures |",
                "| --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for fixture in summary["fixtures"]:
            extensions = ", ".join(f"{key}: {value}" for key, value in fixture["extensions"].items()) or "-"
            signatures = ", ".join(f"{key}: {value}" for key, value in fixture["signatures"].items()) or "-"
            lines.append(
                f"| {fixture['fixture']} | {fixture['sourceKind']} | {fixture['fileCount']} | "
                f"{fixture['totalSizeBytes']} | {extensions} | {signatures} |"
            )
    else:
        lines.append("Aucun fichier runtime UR2D2 n'est encore présent dans le dossier source.")

    lines.extend(["", "## Indices initiaux", ""])
    hints = summary["globalHints"]
    lines.append(f"- Archives ou compressions candidates : {len(hints['archiveCandidates'])}")
    lines.append(f"- Fichiers binaires inconnus à forte entropie : {len(hints['highEntropyUnknownFiles'])}")
    lines.append(f"- Fichiers ou échantillons contenant des chaînes lisibles : {len(hints['readableStringCandidates'])}")

    if hints["readableStringCandidates"]:
        lines.extend(["", "### Exemples de chaînes lisibles", ""])
        for item in hints["readableStringCandidates"][:10]:
            strings = " ; ".join(item["strings"])
            lines.append(f"- `{item['fixture']}/{item['path']}` ({item['signature']}) : {strings}")

    lines.extend(
        [
            "",
            "## Prochaine étape",
            "",
            "Quand au moins une piste runtime est présente, H-S01 pourra comparer sa structure avec les sauvegardes `.sav` analysées par G.",
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
    write_json(results_dir / "h_s00_runtime_inventory_summary.json", summary)
    write_markdown(results_dir / "H_S00_RUNTIME_INVENTORY_RESULT.md", summary)
    print(f"H-S00 inventory status: {summary['status']}")
    print(f"Observed fixtures: {summary['fixtureCount']}")
    print(f"Wrote: {results_dir / 'H_S00_RUNTIME_INVENTORY_RESULT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
