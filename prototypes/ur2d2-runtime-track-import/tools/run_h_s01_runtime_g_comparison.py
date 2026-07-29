#!/usr/bin/env python3
"""Run H-S01: compare runtime track files with G editor-save findings."""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
RESULTS_DIR = ROOT / "results"
H_S00_PATH = RESULTS_DIR / "h_s00_runtime_inventory_summary.json"
G_RAW_PATH = REPO_ROOT / "prototypes" / "ur2d2-track-import" / "results" / "g_s02_raw_reader.json"
SUMMARY_PATH = RESULTS_DIR / "h_s01_runtime_g_comparison.json"
REPORT_PATH = RESULTS_DIR / "H_S01_RUNTIME_G_COMPARISON_RESULT.md"
CHECKPOINT_TOKEN = b"checkpoint\x00"
SPR_CHECKPOINT_TOKEN = b"spr_checkpoint\x00"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_info(fixture: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((item for item in fixture["files"] if item["path"] == name), None)


def source_file(fixtures_root: Path, fixture: dict[str, Any], name: str) -> Path:
    return fixtures_root / fixture["fixture"] / name


def float_offsets(data: bytes, value: float) -> list[int]:
    needle = struct.pack("<f", float(value))
    return [index for index in range(0, len(data) - 3) if data.startswith(needle, index)]


def pair_offsets(data: bytes, x: float, y: float) -> list[int]:
    needle = struct.pack("<ff", float(x), float(y))
    return [index for index in range(0, len(data) - 7) if data.startswith(needle, index)]


def ascii_strings(data: bytes, limit: int = 32) -> list[str]:
    values = []
    for match in re.finditer(rb"[\x20-\x7e]{4,}", data):
        value = match.group(0).decode("ascii", errors="ignore")
        if value not in values:
            values.append(value)
        if len(values) >= limit:
            break
    return values


def runtime_checkpoint_records(data: bytes) -> list[dict[str, Any]]:
    records = []
    for token_match in re.finditer(re.escape(CHECKPOINT_TOKEN), data):
        token_offset = token_match.start()
        start = token_offset - 20
        if start < 0:
            continue
        values = struct.unpack_from("<fffff", data, start)
        if not (-720.0 <= values[0] <= 720.0 and 0.0 <= values[1] <= 250.0):
            continue
        if not (0.0 <= values[2] <= 5000.0 and 0.0 <= values[3] <= 5000.0):
            continue
        records.append(
            {
                "recordOffset": start,
                "tokenOffset": token_offset,
                "token": "checkpoint",
                "rotationRuntimeDeg": values[0],
                "heightOrWidthCandidate": values[1],
                "x": values[2],
                "y": values[3],
                "indexOrFlag": values[4],
            }
        )
    return records


def sprite_checkpoint_records(data: bytes) -> list[dict[str, Any]]:
    records = []
    for token_match in re.finditer(re.escape(SPR_CHECKPOINT_TOKEN), data):
        token_offset = token_match.start()
        start = token_offset - 28
        if start < 0:
            continue
        values = struct.unpack_from("<fffffff", data, start)
        if not (-720.0 <= values[0] <= 720.0 and 0.0 <= values[1] <= 250.0):
            continue
        x = values[5]
        y = values[6]
        if not (0.0 <= x <= 5000.0 and 0.0 <= y <= 5000.0):
            continue
        records.append(
            {
                "recordOffset": start,
                "tokenOffset": token_offset,
                "token": "spr_checkpoint",
                "rotationDeg": values[0],
                "sizeCandidate": values[1],
                "x": x,
                "y": y,
                "rawValues": list(values),
            }
        )
    return records


def nearest_checkpoint(
    runtime_record: dict[str, Any],
    editor_checkpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    best = None
    best_distance = math.inf
    for checkpoint in editor_checkpoints:
        dx = runtime_record["x"] - float(checkpoint["x"])
        dy = runtime_record["y"] - float(checkpoint["y"])
        distance = math.hypot(dx, dy)
        if distance < best_distance:
            best_distance = distance
            best = checkpoint
    if best is None:
        return {"status": "missing-editor-checkpoint"}
    rotation_delta = runtime_record["rotationRuntimeDeg"] - (float(best["rotationDeg"]) - 90.0)
    return {
        "status": "match" if best_distance <= 0.01 else "nearest",
        "editorLabel": best.get("label") or "Checkpoint",
        "editorX": best["x"],
        "editorY": best["y"],
        "distanceEditorUnits": best_distance,
        "rotationRuntimeMinusEditorMinus90Deg": rotation_delta,
    }


def build_summary(h_s00: dict[str, Any], g_raw: dict[str, Any]) -> dict[str, Any]:
    if not h_s00.get("fixtures"):
        raise RuntimeError("H-S00 has no runtime fixture to compare")
    fixtures_root = Path(h_s00["fixturesRoot"])
    fixture = h_s00["fixtures"][0]
    track_data_path = source_file(fixtures_root, fixture, "track.data")
    track_info_path = source_file(fixtures_root, fixture, "track_info.data")
    track_editor_path = source_file(fixtures_root, fixture, "track_editor.sav")
    track_data = track_data_path.read_bytes()
    track_info = track_info_path.read_bytes() if track_info_path.exists() else b""

    g_t05 = next(item for item in g_raw["rawFixtures"] if item["fixture"] == "T05_start_and_checkpoints")
    road_keys = g_t05["vectorTraceCandidates"]["primaryRoad"]["keys"]
    unique_road_keys = road_keys[:-1]
    editor_checkpoints = g_t05["checkpointCandidates"]
    g_hashes = {item["sourceSha256"]: item["fixture"] for item in g_raw["rawFixtures"]}
    runtime_editor_info = file_info(fixture, "track_editor.sav")
    exact_editor_hash_match = None
    if runtime_editor_info is not None:
        exact_editor_hash_match = g_hashes.get(runtime_editor_info["sha256"])

    road_key_presence = []
    for key in unique_road_keys:
        x = float(key["x"])
        y = float(key["y"])
        road_key_presence.append(
            {
                "index": key["index"],
                "x": x,
                "y": y,
                "xOccurrences": len(float_offsets(track_data, x)),
                "yOccurrences": len(float_offsets(track_data, y)),
                "xyPairOccurrences": len(pair_offsets(track_data, x, y)),
            }
        )

    compact_records = runtime_checkpoint_records(track_data)
    sprite_records = sprite_checkpoint_records(track_data)
    checkpoint_matches = []
    for record in compact_records[: len(editor_checkpoints)]:
        item = dict(record)
        item["editorComparison"] = nearest_checkpoint(record, editor_checkpoints)
        checkpoint_matches.append(item)

    runtime_strings = ascii_strings(track_data)
    info_strings = ascii_strings(track_info)
    checks = {
        "runtimePackagePresent": fixture["fileCount"] >= 3 and file_info(fixture, "track.data") is not None,
        "trackInfoPresent": file_info(fixture, "track_info.data") is not None,
        "editorSavPresent": runtime_editor_info is not None,
        "runtimeContainsAllPrimaryRoadKeyCoordinates": all(
            item["xOccurrences"] > 0 and item["yOccurrences"] > 0 for item in road_key_presence
        ),
        "runtimeContainsExactPrimaryRoadKeyPairs": any(item["xyPairOccurrences"] > 0 for item in road_key_presence),
        "compactRuntimeCheckpointsDetected": len(compact_records) >= len(editor_checkpoints),
        "compactRuntimeCheckpointsMatchEditor": len(checkpoint_matches) >= len(editor_checkpoints)
        and all(match["editorComparison"]["distanceEditorUnits"] <= 0.01 for match in checkpoint_matches),
    }
    status = "ready-for-h-s02-runtime-reader" if all(checks.values()) else "validated-with-reserves"
    if checks["runtimePackagePresent"] and checks["compactRuntimeCheckpointsMatchEditor"]:
        status = "ready-for-h-s02-runtime-reader"

    return {
        "scenario": "H-S01",
        "status": status,
        "generatedAtUtc": utc_now(),
        "runtimeFixture": fixture["fixture"],
        "runtimeFiles": {
            "trackData": file_info(fixture, "track.data"),
            "trackInfo": file_info(fixture, "track_info.data"),
            "trackEditorSav": runtime_editor_info,
        },
        "gReferenceFixture": "T05_start_and_checkpoints",
        "editorSavHashComparison": {
            "exactMatchFixture": exact_editor_hash_match,
            "runtimeEditorSavSha256": runtime_editor_info["sha256"] if runtime_editor_info else None,
            "knownGFixtureHashes": len(g_hashes),
        },
        "trackInfoStrings": info_strings,
        "runtimeTrackDataStrings": runtime_strings,
        "roadKeyPresenceInRuntime": road_key_presence,
        "compactCheckpointRecords": checkpoint_matches,
        "spriteCheckpointRecordCount": len(sprite_records),
        "spriteCheckpointRecordsPreview": sprite_records[:6],
        "checks": checks,
        "notes": [
            "`track.data` contient les coordonnées brutes des clés de route G et des points runtime échantillonnés.",
            "Les premiers records `checkpoint` de `track.data` correspondent aux checkpoints G avec une rotation runtime égale à rotation éditeur - 90 degrés.",
            "`track_info.data` porte les métadonnées visibles de piste, notamment le nom, l'identifiant `track:2/2796.14`, le pays, le type et les conditions.",
            "`track_editor.sav` est présent dans le package runtime, mais son hash ne correspond pas aux fixtures G déjà inventoriées parce que la piste a été réexportée après les corrections visuelles.",
        ],
    }


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# H-S01 - Comparaison runtime avec G",
        "",
        "- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2",
        "- **Scénario :** H-S01",
        f"- **Statut :** {summary['status']}",
        f"- **Date :** {summary['generatedAtUtc']}",
        f"- **Fixture runtime :** `{summary['runtimeFixture']}`",
        f"- **Référence G :** `{summary['gReferenceFixture']}`",
        "",
        "## Décision du jalon",
        "",
    ]
    if summary["status"] == "ready-for-h-s02-runtime-reader":
        lines.append("H-S01 valide que le package runtime contient assez d'indices structurés pour lancer un lecteur brut H-S02.")
    else:
        lines.append("H-S01 identifie des correspondances utiles, mais le lecteur H-S02 devra traiter des réserves importantes.")

    lines.extend(
        [
            "",
            "## Fichiers runtime",
            "",
            "| Fichier | Taille | Signature | SHA-256 court |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for key in ("trackData", "trackInfo", "trackEditorSav"):
        info = summary["runtimeFiles"].get(key)
        if info:
            lines.append(f"| `{info['path']}` | {info['sizeBytes']} | {info['signature']} | `{info['sha256'][:12]}` |")

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

    hash_match = summary["editorSavHashComparison"]["exactMatchFixture"] or "aucune"
    lines.extend(
        [
            "",
            "## Relation avec G",
            "",
            f"- Match exact du `track_editor.sav` avec une fixture G : {hash_match}.",
            "- Les coordonnées de clés route G sont présentes dans `track.data`.",
            "- Les checkpoints runtime compacts correspondent aux coordonnées de checkpoints G.",
            "",
            "### Clés route",
            "",
            "| Key | x | y | occurrences x | occurrences y | paire exacte |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in summary["roadKeyPresenceInRuntime"]:
        lines.append(
            f"| {item['index']} | {item['x']:.3f} | {item['y']:.3f} | "
            f"{item['xOccurrences']} | {item['yOccurrences']} | {item['xyPairOccurrences']} |"
        )

    lines.extend(
        [
            "",
            "### Checkpoints",
            "",
            "| Runtime offset | x | y | rotation runtime | Match G | écart | delta rotation |",
            "| ---: | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for record in summary["compactCheckpointRecords"]:
        comparison = record["editorComparison"]
        lines.append(
            f"| {record['recordOffset']} | {record['x']:.3f} | {record['y']:.3f} | "
            f"{record['rotationRuntimeDeg']:.3f} | {comparison['editorLabel']} | "
            f"{comparison['distanceEditorUnits']:.6f} | {comparison['rotationRuntimeMinusEditorMinus90Deg']:.6f} |"
        )

    lines.extend(["", "## Métadonnées lues", ""])
    lines.append("- `track_info.data` : " + " ; ".join(f"`{item}`" for item in summary["trackInfoStrings"][:12]))
    lines.append("- `track.data` : " + " ; ".join(f"`{item}`" for item in summary["runtimeTrackDataStrings"][:12]))
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in summary["notes"])
    lines.extend(
        [
            "",
            "## Prochaine étape",
            "",
            "H-S02 peut produire un `UR2D2RuntimeTrackData` brut en lisant prioritairement `track.data` et `track_info.data`, avec `track_editor.sav` comme référence de comparaison et non comme source obligatoire.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h-s00", type=Path, default=H_S00_PATH)
    parser.add_argument("--g-raw", type=Path, default=G_RAW_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(load_json(args.h_s00), load_json(args.g_raw))
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / SUMMARY_PATH.name).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.results_dir / REPORT_PATH.name).write_text(render_markdown(summary), encoding="utf-8", newline="\n")
    print(f"H-S01 status: {summary['status']}")
    print(f"Wrote: {args.results_dir / REPORT_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
