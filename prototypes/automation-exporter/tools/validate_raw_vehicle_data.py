#!/usr/bin/env python3
"""Validate an Automation LAP A8 unified raw vehicle data document."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA_VERSION = "0.1.0"
EXPECTED_KIND = "AutomationRawVehicleData"
EXPECTED_SOURCE_KIND = "Automation"
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
EXPECTED_INPUT_FILES = {
    "automation-lap-vehicle.json",
    "automation-lap-field-inventory.json",
    "automation-lap-graph-inventory.json",
    "automation-lap-raw-graphs.json",
}
EXPECTED_RAW_GRAPHS = {
    "AccelerationToTopSpeed",
    "Braking",
    "BrakingVGrip",
}
EXPECTED_STEERING_RAW_GRAPHS = {
    "HighSpeedSteering",
    "LowSpeedSteering",
}


class ValidationError(Exception):
    """Raised when a raw vehicle data document does not satisfy the A8 contract."""


def fail(message: str) -> None:
    raise ValidationError(message)


def require_exact_keys(value: dict[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    if missing:
        fail(f"{path}: missing fields: {', '.join(missing)}")

    if unexpected:
        fail(f"{path}: unexpected fields: {', '.join(unexpected)}")


def require_non_empty_string(value: Any, path: str) -> None:
    if not isinstance(value, str) or not value:
        fail(f"{path}: expected non-empty string")


def require_nullable_string(value: Any, path: str) -> None:
    if value is not None and not isinstance(value, str):
        fail(f"{path}: expected string or null")


def require_non_negative_integer(value: Any, path: str) -> None:
    if not isinstance(value, int) or value < 0:
        fail(f"{path}: expected non-negative integer")


def require_nullable_number(value: Any, path: str) -> None:
    if value is not None and not isinstance(value, (int, float)):
        fail(f"{path}: expected number or null")


def validate_datetime(value: Any, path: str) -> None:
    require_non_empty_string(value, path)

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"{path}: invalid ISO 8601 datetime: {error}")


def looks_like_absolute_path(value: str) -> bool:
    return (
        value.startswith("/")
        or value.startswith("\\\\")
        or WINDOWS_ABSOLUTE_PATH.match(value) is not None
    )


def reject_absolute_paths(value: Any, path: str = "$") -> None:
    if isinstance(value, str):
        if looks_like_absolute_path(value):
            fail(f"{path}: absolute path is forbidden in export: {value!r}")
        return

    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_absolute_paths(item, f"{path}[{index}]")
        return

    if isinstance(value, dict):
        for key, item in value.items():
            reject_absolute_paths(item, f"{path}.{key}")


def validate_diagnostics(value: Any, path: str) -> None:
    if not isinstance(value, list):
        fail(f"{path}: expected array")

    for index, item in enumerate(value):
        require_non_empty_string(item, f"{path}[{index}]")


def validate_input_file(value: Any, path: str) -> str:
    if not isinstance(value, dict):
        fail(f"{path}: expected object")

    require_exact_keys(value, {"name", "schemaVersion", "sha256"}, path)

    name = value["name"]
    if name not in EXPECTED_INPUT_FILES:
        fail(f"{path}.name: unexpected input file {name!r}")

    require_non_empty_string(value["schemaVersion"], f"{path}.schemaVersion")

    sha256 = value["sha256"]
    if not isinstance(sha256, str) or re.match(r"^[A-Fa-f0-9]{64}$", sha256) is None:
        fail(f"{path}.sha256: expected 64 hex characters")

    return name


def validate_source(value: Any) -> list[str]:
    if not isinstance(value, dict):
        fail("$.source: expected object")

    require_exact_keys(
        value,
        {
            "kind",
            "exporterVersion",
            "exportedAtUtc",
            "automationVersion",
            "lastAccessTime",
            "inputFiles",
        },
        "$.source",
    )

    if value["kind"] != EXPECTED_SOURCE_KIND:
        fail(f"$.source.kind: expected {EXPECTED_SOURCE_KIND!r}")

    require_non_empty_string(value["exporterVersion"], "$.source.exporterVersion")
    validate_datetime(value["exportedAtUtc"], "$.source.exportedAtUtc")
    require_nullable_string(value["automationVersion"], "$.source.automationVersion")
    require_nullable_number(value["lastAccessTime"], "$.source.lastAccessTime")

    input_files = value["inputFiles"]
    if not isinstance(input_files, list):
        fail("$.source.inputFiles: expected array")

    names = [
        validate_input_file(item, f"$.source.inputFiles[{index}]")
        for index, item in enumerate(input_files)
    ]

    if set(names) != EXPECTED_INPUT_FILES:
        fail("$.source.inputFiles: expected the four Automation exporter input files")

    if len(names) != len(set(names)):
        fail("$.source.inputFiles: duplicate input file")

    return names


def validate_identity(value: Any) -> None:
    if not isinstance(value, dict):
        fail("$.identity: expected object")

    require_exact_keys(value, {"modelName", "trimName"}, "$.identity")
    require_non_empty_string(value["modelName"], "$.identity.modelName")
    require_non_empty_string(value["trimName"], "$.identity.trimName")


def validate_unit_policy(value: Any) -> None:
    if not isinstance(value, dict):
        fail("$.unitPolicy: expected object")

    require_exact_keys(
        value,
        {
            "rawValuesPreserved",
            "conversionsApplied",
            "internalUnitSystem",
            "unknownUnitsPreserved",
        },
        "$.unitPolicy",
    )

    if value["rawValuesPreserved"] is not True:
        fail("$.unitPolicy.rawValuesPreserved: expected true")

    if value["conversionsApplied"] is not False:
        fail("$.unitPolicy.conversionsApplied: expected false")

    if value["internalUnitSystem"] != "SI-candidate":
        fail("$.unitPolicy.internalUnitSystem: expected 'SI-candidate'")

    if value["unknownUnitsPreserved"] is not True:
        fail("$.unitPolicy.unknownUnitsPreserved: expected true")


def validate_controlled_field(value: Any, path: str) -> bool:
    if not isinstance(value, dict):
        fail(f"{path}: expected object")

    required = {
        "key",
        "family",
        "candidatePaths",
        "resolvedPath",
        "present",
        "luaType",
        "valuePreview",
        "origin",
        "presence",
        "nature",
        "unitSource",
        "unitInternalCandidate",
        "stability",
        "redistribution",
    }
    missing = sorted(required - set(value))
    if missing:
        fail(f"{path}: missing fields: {', '.join(missing)}")

    for name in (
        "key",
        "family",
        "luaType",
        "origin",
        "presence",
        "nature",
        "unitSource",
        "unitInternalCandidate",
        "stability",
        "redistribution",
    ):
        require_non_empty_string(value[name], f"{path}.{name}")

    candidates = value["candidatePaths"]
    if not isinstance(candidates, list) or not candidates:
        fail(f"{path}.candidatePaths: expected non-empty array")

    for index, candidate in enumerate(candidates):
        require_non_empty_string(candidate, f"{path}.candidatePaths[{index}]")

    require_nullable_string(value["resolvedPath"], f"{path}.resolvedPath")

    if not isinstance(value["present"], bool):
        fail(f"{path}.present: expected boolean")

    if value["present"] and value["resolvedPath"] is None:
        fail(f"{path}.resolvedPath: expected path when present=true")

    return value["present"]


def validate_available_graph(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        fail(f"{path}: expected object")

    require_exact_keys(
        value,
        {"key", "path", "luaType", "entryCount", "seriesLikeChildren"},
        path,
    )

    for name in ("key", "path", "luaType"):
        require_non_empty_string(value[name], f"{path}.{name}")

    require_non_negative_integer(value["entryCount"], f"{path}.entryCount")

    children = value["seriesLikeChildren"]
    if not isinstance(children, list):
        fail(f"{path}.seriesLikeChildren: expected array")

    for index, child in enumerate(children):
        require_non_empty_string(child, f"{path}.seriesLikeChildren[{index}]")


def validate_graph_inventory(value: Any) -> None:
    if not isinstance(value, dict):
        fail("$.graphInventory: expected object")

    require_exact_keys(
        value,
        {"rootPath", "graphDataPresent", "availableGraphs", "diagnostics"},
        "$.graphInventory",
    )

    require_non_empty_string(value["rootPath"], "$.graphInventory.rootPath")

    if not isinstance(value["graphDataPresent"], bool):
        fail("$.graphInventory.graphDataPresent: expected boolean")

    graphs = value["availableGraphs"]
    if not isinstance(graphs, list):
        fail("$.graphInventory.availableGraphs: expected array")

    for index, graph in enumerate(graphs):
        validate_available_graph(graph, f"$.graphInventory.availableGraphs[{index}]")

    validate_diagnostics(value["diagnostics"], "$.graphInventory.diagnostics")


def validate_raw_series(series: Any, path: str) -> int:
    if not isinstance(series, dict):
        fail(f"{path}: expected object")

    require_exact_keys(
        series,
        {
            "key",
            "path",
            "luaType",
            "role",
            "count",
            "numericMin",
            "numericMax",
            "values",
            "truncated",
            "unitSource",
            "unitInternalCandidate",
        },
        path,
    )

    for name in ("key", "path", "luaType", "role", "unitSource", "unitInternalCandidate"):
        require_non_empty_string(series[name], f"{path}.{name}")

    if series["role"] not in {"axis-candidate", "value"}:
        fail(f"{path}.role: expected 'axis-candidate' or 'value'")

    require_non_negative_integer(series["count"], f"{path}.count")
    require_nullable_number(series["numericMin"], f"{path}.numericMin")
    require_nullable_number(series["numericMax"], f"{path}.numericMax")

    values = series["values"]
    if not isinstance(values, list):
        fail(f"{path}.values: expected array")

    if len(values) != series["count"]:
        fail(f"{path}.values: expected length to match count")

    for index, value in enumerate(values):
        if not isinstance(value, (int, float)):
            fail(f"{path}.values[{index}]: expected number")

    if not isinstance(series["truncated"], bool):
        fail(f"{path}.truncated: expected boolean")

    if series["truncated"]:
        fail(f"{path}.truncated: A8 fixtures must not be truncated")

    return series["count"]


def validate_raw_graph(graph: Any, path: str) -> str:
    if not isinstance(graph, dict):
        fail(f"{path}: expected object")

    require_exact_keys(
        graph,
        {
            "key",
            "path",
            "present",
            "luaType",
            "seriesCount",
            "expectedSeriesLength",
            "lengthMismatch",
            "series",
            "diagnostics",
        },
        path,
    )

    for name in ("key", "path", "luaType"):
        require_non_empty_string(graph[name], f"{path}.{name}")

    if not isinstance(graph["present"], bool):
        fail(f"{path}.present: expected boolean")

    if not graph["present"]:
        fail(f"{path}.present: A8 selected graphs must be present")

    require_non_negative_integer(graph["seriesCount"], f"{path}.seriesCount")

    expected_length = graph["expectedSeriesLength"]
    if expected_length is not None:
        require_non_negative_integer(expected_length, f"{path}.expectedSeriesLength")

    if graph["lengthMismatch"] is not False:
        fail(f"{path}.lengthMismatch: expected false")

    series = graph["series"]
    if not isinstance(series, list):
        fail(f"{path}.series: expected array")

    if len(series) != graph["seriesCount"]:
        fail(f"{path}.seriesCount: does not match series length")

    counts = [
        validate_raw_series(item, f"{path}.series[{index}]")
        for index, item in enumerate(series)
    ]

    if counts and len(set(counts)) != 1:
        fail(f"{path}.series: expected equal series lengths")

    if counts and expected_length != counts[0]:
        fail(f"{path}.expectedSeriesLength: expected to match series count")

    validate_diagnostics(graph["diagnostics"], f"{path}.diagnostics")

    return graph["key"]


def validate_document(document: Any) -> list[str]:
    if not isinstance(document, dict):
        fail("$: expected JSON object")

    require_exact_keys(
        document,
        {
            "schemaVersion",
            "kind",
            "generatedAtUtc",
            "generator",
            "source",
            "identity",
            "unitPolicy",
            "controlledFields",
            "graphInventory",
            "rawGraphs",
            "diagnostics",
        },
        "$",
    )

    if document["schemaVersion"] != EXPECTED_SCHEMA_VERSION:
        fail(
            "$.schemaVersion: "
            f"expected {EXPECTED_SCHEMA_VERSION!r}, got {document['schemaVersion']!r}"
        )

    if document["kind"] != EXPECTED_KIND:
        fail(f"$.kind: expected {EXPECTED_KIND!r}")

    validate_datetime(document["generatedAtUtc"], "$.generatedAtUtc")
    require_non_empty_string(document["generator"], "$.generator")
    validate_source(document["source"])
    validate_identity(document["identity"])
    validate_unit_policy(document["unitPolicy"])

    fields = document["controlledFields"]
    if not isinstance(fields, list) or not fields:
        fail("$.controlledFields: expected non-empty array")

    present_count = 0
    for index, field in enumerate(fields):
        if validate_controlled_field(field, f"$.controlledFields[{index}]"):
            present_count += 1

    validate_graph_inventory(document["graphInventory"])

    raw_graphs = document["rawGraphs"]
    if not isinstance(raw_graphs, list):
        fail("$.rawGraphs: expected array")

    graph_keys = [
        validate_raw_graph(graph, f"$.rawGraphs[{index}]")
        for index, graph in enumerate(raw_graphs)
    ]

    graph_key_set = set(graph_keys)
    missing_base_graphs = sorted(EXPECTED_RAW_GRAPHS - graph_key_set)
    if missing_base_graphs:
        fail("$.rawGraphs: missing expected raw graphs: " + ", ".join(missing_base_graphs))

    steering_graphs_present = EXPECTED_STEERING_RAW_GRAPHS & graph_key_set
    missing_steering_graphs = sorted(EXPECTED_STEERING_RAW_GRAPHS - graph_key_set)
    if steering_graphs_present and missing_steering_graphs:
        fail(
            "$.rawGraphs: incomplete A9 steering raw graphs, missing: "
            + ", ".join(missing_steering_graphs)
        )

    if len(graph_keys) != len(set(graph_keys)):
        fail("$.rawGraphs: duplicate graph key")

    validate_diagnostics(document["diagnostics"], "$.diagnostics")
    reject_absolute_paths(document)

    warnings: list[str] = []
    if present_count == 0:
        warnings.append("no controlled field was present")

    if document["source"]["automationVersion"] is None:
        warnings.append("Automation version was not exposed by Lua data")

    return warnings


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an Automation LAP A8 raw vehicle data JSON document."
    )
    parser.add_argument("export", type=Path, help="automation-lap-raw-vehicle-data.json")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        with arguments.export.open("r", encoding="utf-8") as stream:
            document = json.load(stream)

        warnings = validate_document(document)
    except FileNotFoundError:
        print(f"ERROR: file not found: {arguments.export}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as error:
        print(f"ERROR: file is not valid UTF-8: {error}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as error:
        print(
            f"ERROR: invalid JSON at line {error.lineno}, column {error.colno}: "
            f"{error.msg}",
            file=sys.stderr,
        )
        return 2
    except ValidationError as error:
        print(f"FAILURE: {error}", file=sys.stderr)
        return 1

    print("SUCCESS: export satisfies A8 raw vehicle data contract v0.1.0.")

    for warning in warnings:
        print(f"WARNING: {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
