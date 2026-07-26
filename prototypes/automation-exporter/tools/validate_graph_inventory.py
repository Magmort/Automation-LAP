#!/usr/bin/env python3
"""Validate an Automation LAP A6 GraphData inventory export."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA_VERSION = "0.1.0"
EXPECTED_SCOPE = "results-graph-inventory"
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class ValidationError(Exception):
    """Raised when a graph inventory document does not satisfy the A6 contract."""


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


def validate_number_array(value: Any, path: str) -> None:
    if not isinstance(value, list):
        fail(f"{path}: expected array")

    if len(value) > 5:
        fail(f"{path}: expected at most 5 sampled values")

    for index, item in enumerate(value):
        if not isinstance(item, (int, float)):
            fail(f"{path}[{index}]: expected number")


def validate_entry(entry: Any, path: str, depth: int = 0) -> None:
    if not isinstance(entry, dict):
        fail(f"{path}: expected object")

    require_exact_keys(
        entry,
        {
            "key",
            "path",
            "luaType",
            "entryCount",
            "sequentialNumericCount",
            "numericValueCount",
            "tableValueCount",
            "stringValueCount",
            "booleanValueCount",
            "otherValueCount",
            "numericMin",
            "numericMax",
            "firstNumericValues",
            "lastNumericValues",
            "children",
            "truncatedChildren",
        },
        path,
    )

    for name in ("key", "path", "luaType"):
        require_non_empty_string(entry[name], f"{path}.{name}")

    for name in (
        "entryCount",
        "sequentialNumericCount",
        "numericValueCount",
        "tableValueCount",
        "stringValueCount",
        "booleanValueCount",
        "otherValueCount",
    ):
        require_non_negative_integer(entry[name], f"{path}.{name}")

    require_nullable_number(entry["numericMin"], f"{path}.numericMin")
    require_nullable_number(entry["numericMax"], f"{path}.numericMax")
    validate_number_array(entry["firstNumericValues"], f"{path}.firstNumericValues")
    validate_number_array(entry["lastNumericValues"], f"{path}.lastNumericValues")

    if not isinstance(entry["truncatedChildren"], bool):
        fail(f"{path}.truncatedChildren: expected boolean")

    children = entry["children"]
    if not isinstance(children, list):
        fail(f"{path}.children: expected array")

    if len(children) > 64:
        fail(f"{path}.children: expected at most 64 child summaries")

    for index, child in enumerate(children):
        validate_entry(child, f"{path}.children[{index}]", depth + 1)


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
            "rootLuaType",
            "rootEntryCount",
            "entries",
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
    require_non_empty_string(document["rootLuaType"], "$.rootLuaType")
    require_non_negative_integer(document["rootEntryCount"], "$.rootEntryCount")

    if not isinstance(document["graphDataPresent"], bool):
        fail("$.graphDataPresent: expected boolean")

    entries = document["entries"]
    if not isinstance(entries, list):
        fail("$.entries: expected array")

    for index, entry in enumerate(entries):
        validate_entry(entry, f"$.entries[{index}]")

    diagnostics = document["diagnostics"]
    if not isinstance(diagnostics, list):
        fail("$.diagnostics: expected array")

    for index, diagnostic in enumerate(diagnostics):
        require_non_empty_string(diagnostic, f"$.diagnostics[{index}]")

    reject_absolute_paths(document)

    warnings: list[str] = []
    if not document["graphDataPresent"]:
        warnings.append("GraphData was not present")
    elif not entries:
        warnings.append("GraphData was present but no named graph entries were exported")

    return warnings


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an Automation LAP A6 GraphData inventory JSON export."
    )
    parser.add_argument("export", type=Path, help="automation-lap-graph-inventory.json")
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

    print("SUCCESS: export satisfies A6 graph-inventory contract v0.1.0.")

    for warning in warnings:
        print(f"WARNING: {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
