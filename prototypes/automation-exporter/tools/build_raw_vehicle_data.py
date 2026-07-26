#!/usr/bin/env python3
"""Build an A8 AutomationRawVehicleData document from the four exporter files."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "automation-lap-a8-builder-0.1.0"
OUTPUT_FILENAME = "automation-lap-raw-vehicle-data.json"
INPUT_FILENAMES = {
    "vehicle": "automation-lap-vehicle.json",
    "field_inventory": "automation-lap-field-inventory.json",
    "graph_inventory": "automation-lap-graph-inventory.json",
    "raw_graphs": "automation-lap-raw-graphs.json",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_input_file(name: str, document: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "name": name,
        "schemaVersion": document.get("schemaVersion", "unknown"),
        "sha256": sha256_file(path),
    }


def extract_available_graphs(graph_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    available_graphs: list[dict[str, Any]] = []

    for entry in graph_inventory.get("entries", []):
        children = [
            child.get("key")
            for child in entry.get("children", [])
            if child.get("sequentialNumericCount", 0) > 0
        ]

        available_graphs.append(
            {
                "key": entry.get("key"),
                "path": entry.get("path"),
                "luaType": entry.get("luaType"),
                "entryCount": entry.get("entryCount", 0),
                "seriesLikeChildren": children,
            }
        )

    return available_graphs


def aggregate_diagnostics(*documents: dict[str, Any]) -> list[str]:
    diagnostics: list[str] = []

    for document in documents:
        for diagnostic in document.get("diagnostics", []):
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)

    return diagnostics


def require_same_exporter_version(documents: dict[str, dict[str, Any]]) -> str:
    versions = {
        name: document.get("exporterVersion")
        for name, document in documents.items()
    }
    unique_versions = set(versions.values())

    if len(unique_versions) != 1:
        details = ", ".join(f"{name}={version}" for name, version in sorted(versions.items()))
        raise ValueError(f"input exporter versions differ: {details}")

    version = next(iter(unique_versions))
    if not isinstance(version, str) or not version:
        raise ValueError("input exporter version is missing")

    return version


def build_document(export_directory: Path) -> dict[str, Any]:
    paths = {
        key: export_directory / filename
        for key, filename in INPUT_FILENAMES.items()
    }
    documents = {key: load_json(path) for key, path in paths.items()}

    exporter_version = require_same_exporter_version(documents)
    vehicle = documents["vehicle"]
    field_inventory = documents["field_inventory"]
    graph_inventory = documents["graph_inventory"]
    raw_graphs = documents["raw_graphs"]

    return {
        "schemaVersion": "0.1.0",
        "kind": "AutomationRawVehicleData",
        "generatedAtUtc": utc_now(),
        "generator": GENERATOR_VERSION,
        "source": {
            "kind": "Automation",
            "exporterVersion": exporter_version,
            "exportedAtUtc": vehicle["exportedAtUtc"],
            "automationVersion": vehicle["source"]["automationVersion"],
            "lastAccessTime": vehicle["source"]["lastAccessTime"],
            "inputFiles": [
                make_input_file(INPUT_FILENAMES["vehicle"], vehicle, paths["vehicle"]),
                make_input_file(
                    INPUT_FILENAMES["field_inventory"],
                    field_inventory,
                    paths["field_inventory"],
                ),
                make_input_file(
                    INPUT_FILENAMES["graph_inventory"],
                    graph_inventory,
                    paths["graph_inventory"],
                ),
                make_input_file(INPUT_FILENAMES["raw_graphs"], raw_graphs, paths["raw_graphs"]),
            ],
        },
        "identity": {
            "modelName": vehicle["vehicle"]["modelName"],
            "trimName": vehicle["vehicle"]["trimName"],
        },
        "unitPolicy": {
            "rawValuesPreserved": True,
            "conversionsApplied": False,
            "internalUnitSystem": "SI-candidate",
            "unknownUnitsPreserved": True,
        },
        "controlledFields": field_inventory["fields"],
        "graphInventory": {
            "rootPath": graph_inventory["rootPath"],
            "graphDataPresent": graph_inventory["graphDataPresent"],
            "availableGraphs": extract_available_graphs(graph_inventory),
            "diagnostics": graph_inventory.get("diagnostics", []),
        },
        "rawGraphs": raw_graphs["graphs"],
        "diagnostics": aggregate_diagnostics(vehicle, field_inventory, graph_inventory, raw_graphs),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an Automation LAP A8 raw vehicle data document."
    )
    parser.add_argument(
        "export_directory",
        type=Path,
        help="Directory containing the four Automation LAP exporter JSON files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=f"Output JSON path. Defaults to <export_directory>/{OUTPUT_FILENAME}.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    output = arguments.output or arguments.export_directory / OUTPUT_FILENAME

    document = build_document(arguments.export_directory)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
