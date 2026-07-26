#!/usr/bin/env python3
"""Validate an Automation LAP A7 selected raw GraphData export."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA_VERSION = "0.1.0"
EXPECTED_SCOPE = "selected-raw-graphs"
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class ValidationError(Exception):
    """Raised when a raw graph document does not satisfy the A7 contract."""


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


def validate_string_array(value: Any, path: str) -> None:
    if not isinstance(value, list) or not value:
        fail(f"{path}: expected non-empty array")

    for index, item in enumerate(value):
        require_non_empty_string(item, f"{path}[{index}]")


def validate_number_array(value: Any, expected_count: int, path: str) -> None:
    if not isinstance(value, list):
        fail(f"{path}: expected array")

    if len(value) > expected_count:
        fail(f"{path}: value array cannot be longer than declared count")

    for index, item in enumerate(value):
        if not isinstance(item, (int, float)):
            fail(f"{path}[{index}]: expected number")


def validate_series(series: Any, path: str, value_limit: int) -> int:
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

    if not isinstance(series["truncated"], bool):
        fail(f"{path}.truncated: expected boolean")

    validate_number_array(series["values"], series["count"], f"{path}.values")

    if len(series["values"]) > value_limit:
        fail(f"{path}.values: exceeds valueLimitPerSeries")

    if not series["truncated"] and len(series["values"]) != series["count"]:
        fail(f"{path}.values: expected full sequence when truncated=false")

    if series["count"] > 0:
        if series["numericMin"] is None or series["numericMax"] is None:
            fail(f"{path}: numericMin/numericMax required when count > 0")

    return series["count"]


def validate_graph(graph: Any, path: str, value_limit: int) -> list[str]:
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

    require_non_negative_integer(graph["seriesCount"], f"{path}.seriesCount")
    require_nullable_number(graph["expectedSeriesLength"], f"{path}.expectedSeriesLength")

    if (
        graph["expectedSeriesLength"] is not None
        and not isinstance(graph["expectedSeriesLength"], int)
    ):
        fail(f"{path}.expectedSeriesLength: expected integer or null")

    if not isinstance(graph["lengthMismatch"], bool):
        fail(f"{path}.lengthMismatch: expected boolean")

    series_items = graph["series"]
    if not isinstance(series_items, list):
        fail(f"{path}.series: expected array")

    if len(series_items) != graph["seriesCount"]:
        fail(f"{path}.seriesCount: does not match series length")

    counts: list[int] = []
    for index, series in enumerate(series_items):
        counts.append(validate_series(series, f"{path}.series[{index}]", value_limit))

    expected = graph["expectedSeriesLength"]
    if expected is not None and counts and counts[0] != expected:
        fail(f"{path}.expectedSeriesLength: expected first series count")

    mismatch = len(set(counts)) > 1
    if mismatch != graph["lengthMismatch"]:
        fail(f"{path}.lengthMismatch: inconsistent with series counts")

    diagnostics = graph["diagnostics"]
    if not isinstance(diagnostics, list):
        fail(f"{path}.diagnostics: expected array")

    for index, diagnostic in enumerate(diagnostics):
        require_non_empty_string(diagnostic, f"{path}.diagnostics[{index}]")

    return diagnostics


def validate_document(document: Any) -> list[str]:
    if not isinstance(document, dict):
        fail("$: expected JSON object")

    require_exact_keys(
        document,
        {
            "schemaVersion",
            "exporterVersion",
            "exportedAtUtc",
            "scope",
            "rootPath",
            "graphDataPresent",
            "selectedGraphs",
            "valueLimitPerSeries",
            "graphs",
            "diagnostics",
        },
        "$",
    )

    if document["schemaVersion"] != EXPECTED_SCHEMA_VERSION:
        fail(
            "$.schemaVersion: "
            f"expected {EXPECTED_SCHEMA_VERSION!r}, got {document['schemaVersion']!r}"
        )

    require_non_empty_string(document["exporterVersion"], "$.exporterVersion")
    validate_datetime(document["exportedAtUtc"], "$.exportedAtUtc")

    if document["scope"] != EXPECTED_SCOPE:
        fail(f"$.scope: expected {EXPECTED_SCOPE!r}")

    require_non_empty_string(document["rootPath"], "$.rootPath")

    if not isinstance(document["graphDataPresent"], bool):
        fail("$.graphDataPresent: expected boolean")

    validate_string_array(document["selectedGraphs"], "$.selectedGraphs")
    require_non_negative_integer(document["valueLimitPerSeries"], "$.valueLimitPerSeries")

    graphs = document["graphs"]
    if not isinstance(graphs, list):
        fail("$.graphs: expected array")

    if document["graphDataPresent"] and len(graphs) != len(document["selectedGraphs"]):
        fail("$.graphs: expected one graph object for each selected graph")

    graph_keys = [graph.get("key") for graph in graphs if isinstance(graph, dict)]
    if len(graph_keys) != len(set(graph_keys)):
        fail("$.graphs: duplicate graph keys")

    if document["graphDataPresent"] and set(graph_keys) != set(document["selectedGraphs"]):
        fail("$.graphs: graph keys do not match selectedGraphs")

    nested_diagnostics: list[str] = []
    for index, graph in enumerate(graphs):
        nested_diagnostics.extend(
            validate_graph(graph, f"$.graphs[{index}]", document["valueLimitPerSeries"])
        )

    diagnostics = document["diagnostics"]
    if not isinstance(diagnostics, list):
        fail("$.diagnostics: expected array")

    for index, diagnostic in enumerate(diagnostics):
        require_non_empty_string(diagnostic, f"$.diagnostics[{index}]")

    if sorted(nested_diagnostics) != sorted(diagnostics):
        fail("$.diagnostics: expected aggregate of graph diagnostics")

    reject_absolute_paths(document)

    warnings: list[str] = []
    if not document["graphDataPresent"]:
        warnings.append("GraphData was not present")
    elif not graphs:
        warnings.append("GraphData was present but no selected graph was exported")

    if diagnostics:
        warnings.extend(diagnostics)

    return warnings


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an Automation LAP A7 selected raw GraphData JSON export."
    )
    parser.add_argument("export", type=Path, help="automation-lap-raw-graphs.json")
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

    print("SUCCESS: export satisfies A7 selected raw graph contract v0.1.0.")

    for warning in warnings:
        print(f"WARNING: {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
