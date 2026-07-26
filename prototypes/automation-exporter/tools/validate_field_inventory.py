#!/usr/bin/env python3
"""Validate an Automation LAP controlled field-inventory export."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA_VERSION = "0.1.0"
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class ValidationError(Exception):
    """Raised when an inventory document does not satisfy the A3 contract."""


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


def validate_field(field: Any, index: int) -> bool:
    path = f"$.fields[{index}]"

    if not isinstance(field, dict):
        fail(f"{path}: expected object")

    require_exact_keys(
        field,
        {
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
        },
        path,
    )

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
        require_non_empty_string(field[name], f"{path}.{name}")

    if not isinstance(field["candidatePaths"], list) or not field["candidatePaths"]:
        fail(f"{path}.candidatePaths: expected non-empty array")

    for candidate_index, candidate in enumerate(field["candidatePaths"]):
        require_non_empty_string(candidate, f"{path}.candidatePaths[{candidate_index}]")

    require_nullable_string(field["resolvedPath"], f"{path}.resolvedPath")

    if not isinstance(field["present"], bool):
        fail(f"{path}.present: expected boolean")

    if field["present"] and field["resolvedPath"] is None:
        fail(f"{path}.resolvedPath: expected path when present=true")

    return field["present"]


def validate_function(function: Any, index: int) -> None:
    path = f"$.functions[{index}]"

    if not isinstance(function, dict):
        fail(f"{path}: expected object")

    require_exact_keys(
        function,
        {"name", "path", "present", "luaType", "called", "reason"},
        path,
    )

    require_non_empty_string(function["name"], f"{path}.name")
    require_non_empty_string(function["path"], f"{path}.path")
    require_non_empty_string(function["luaType"], f"{path}.luaType")
    require_non_empty_string(function["reason"], f"{path}.reason")

    if not isinstance(function["present"], bool):
        fail(f"{path}.present: expected boolean")

    if not isinstance(function["called"], bool):
        fail(f"{path}.called: expected boolean")


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
            "fields",
            "functions",
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

    if document["scope"] != "controlled-field-inventory":
        fail("$.scope: expected 'controlled-field-inventory'")

    if not isinstance(document["fields"], list) or not document["fields"]:
        fail("$.fields: expected non-empty array")

    present_count = 0
    for index, field in enumerate(document["fields"]):
        if validate_field(field, index):
            present_count += 1

    if not isinstance(document["functions"], list):
        fail("$.functions: expected array")

    for index, function in enumerate(document["functions"]):
        validate_function(function, index)

    if not isinstance(document["diagnostics"], list):
        fail("$.diagnostics: expected array")

    for index, diagnostic in enumerate(document["diagnostics"]):
        require_non_empty_string(diagnostic, f"$.diagnostics[{index}]")

    reject_absolute_paths(document)

    warnings: list[str] = []
    if present_count == 0:
        warnings.append("no candidate field was present")

    return warnings


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an Automation LAP A3 field-inventory JSON export."
    )
    parser.add_argument("export", type=Path, help="automation-lap-field-inventory.json")
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

    print("SUCCESS: export satisfies A3 field-inventory contract v0.1.0.")

    for warning in warnings:
        print(f"WARNING: {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
