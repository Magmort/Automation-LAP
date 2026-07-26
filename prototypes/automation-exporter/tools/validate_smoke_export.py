#!/usr/bin/env python3
"""Validate an Automation LAP metadata-only smoke-test export."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA_VERSION = "0.1.1"
EXPECTED_SOURCE_KIND = "Automation"
WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class ValidationError(Exception):
    """Raised when an exported document does not satisfy the smoke contract."""


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


def require_nullable_string(value: Any, path: str) -> None:
    if value is not None and not isinstance(value, str):
        fail(f"{path}: expected string or null")


def require_nullable_number(value: Any, path: str) -> None:
    if value is not None and not isinstance(value, (int, float)):
        fail(f"{path}: expected number or null")


def require_non_empty_string(value: Any, path: str) -> None:
    if not isinstance(value, str) or not value:
        fail(f"{path}: expected non-empty string")


def validate_datetime(value: Any) -> None:
    require_non_empty_string(value, "$.exportedAtUtc")

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"$.exportedAtUtc: invalid ISO 8601 datetime: {error}")


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


def validate_document(document: Any) -> list[str]:
    if not isinstance(document, dict):
        fail("$: expected JSON object")

    require_exact_keys(
        document,
        {
            "schemaVersion",
            "exporterVersion",
            "exportedAtUtc",
            "source",
            "vehicle",
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
    validate_datetime(document["exportedAtUtc"])

    source = document["source"]
    if not isinstance(source, dict):
        fail("$.source: expected object")

    require_exact_keys(
        source,
        {
            "kind",
            "automationVersion",
            "automationVersionPath",
            "lastAccessTime",
            "lastAccessTimePath",
        },
        "$.source",
    )

    if source["kind"] != EXPECTED_SOURCE_KIND:
        fail(f"$.source.kind: expected {EXPECTED_SOURCE_KIND!r}, got {source['kind']!r}")

    require_nullable_string(source["automationVersion"], "$.source.automationVersion")
    require_nullable_string(
        source["automationVersionPath"], "$.source.automationVersionPath"
    )
    require_nullable_number(source["lastAccessTime"], "$.source.lastAccessTime")
    require_nullable_string(source["lastAccessTimePath"], "$.source.lastAccessTimePath")

    vehicle = document["vehicle"]
    if not isinstance(vehicle, dict):
        fail("$.vehicle: expected object")

    require_exact_keys(
        vehicle,
        {"modelName", "modelNamePath", "trimName", "trimNamePath"},
        "$.vehicle",
    )

    for field_name in ("modelName", "modelNamePath", "trimName", "trimNamePath"):
        require_nullable_string(vehicle[field_name], f"$.vehicle.{field_name}")

    diagnostics = document["diagnostics"]
    if not isinstance(diagnostics, list):
        fail("$.diagnostics: expected array")

    if len(diagnostics) != len(set(diagnostics)):
        fail("$.diagnostics: duplicate diagnostics")

    for index, diagnostic in enumerate(diagnostics):
        require_non_empty_string(diagnostic, f"$.diagnostics[{index}]")

    reject_absolute_paths(document)

    warnings: list[str] = []

    if vehicle["modelName"] is None:
        warnings.append("vehicle model name was not recovered")

    if vehicle["trimName"] is None:
        warnings.append("vehicle trim name was not recovered")

    if source["automationVersion"] is None:
        warnings.append("Automation version was not exposed by Lua data")

    if source["lastAccessTime"] is None:
        warnings.append("lastAccessTime was not exposed by Lua data")

    return warnings


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate an Automation LAP smoke-test JSON export."
    )
    parser.add_argument("export", type=Path, help="automation-lap-vehicle.json file")
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

    print("SUCCESS: export satisfies smoke-test contract v0.1.1.")

    for warning in warnings:
        print(f"WARNING: {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
