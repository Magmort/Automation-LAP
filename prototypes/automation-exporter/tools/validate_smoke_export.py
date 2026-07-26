#!/usr/bin/env python3
"""Validate an Automation LAP metadata-only smoke-test export.

This validator intentionally uses only the Python standard library so it can be
run on a clean Windows development machine without installing dependencies.
It validates the experiment's required contract rather than implementing the
entire JSON Schema specification.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA_VERSION = "0.1.0"
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
        fail(f"{path}: champs manquants: {', '.join(missing)}")

    if unexpected:
        fail(f"{path}: champs inattendus: {', '.join(unexpected)}")


def require_nullable_string(value: Any, path: str) -> None:
    if value is not None and not isinstance(value, str):
        fail(f"{path}: chaîne ou null attendu")


def require_non_empty_string(value: Any, path: str) -> None:
    if not isinstance(value, str) or not value:
        fail(f"{path}: chaîne non vide attendue")


def validate_datetime(value: Any) -> None:
    if value is None:
        return

    require_non_empty_string(value, "$.exportedAtUtc")

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        fail(f"$.exportedAtUtc: date ISO 8601 invalide: {error}")


def looks_like_absolute_path(value: str) -> bool:
    return (
        value.startswith("/")
        or value.startswith("\\\\")
        or WINDOWS_ABSOLUTE_PATH.match(value) is not None
    )


def reject_absolute_paths(value: Any, path: str = "$") -> None:
    if isinstance(value, str):
        if looks_like_absolute_path(value):
            fail(f"{path}: chemin absolu interdit dans l'export: {value!r}")
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
        fail("$: objet JSON attendu")

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
            f"{EXPECTED_SCHEMA_VERSION!r} attendu, reçu {document['schemaVersion']!r}"
        )

    require_non_empty_string(document["exporterVersion"], "$.exporterVersion")
    validate_datetime(document["exportedAtUtc"])

    source = document["source"]
    if not isinstance(source, dict):
        fail("$.source: objet attendu")

    require_exact_keys(
        source,
        {"kind", "automationVersion", "automationVersionPath"},
        "$.source",
    )

    if source["kind"] != EXPECTED_SOURCE_KIND:
        fail(
            f"$.source.kind: {EXPECTED_SOURCE_KIND!r} attendu, "
            f"reçu {source['kind']!r}"
        )

    require_nullable_string(source["automationVersion"], "$.source.automationVersion")
    require_nullable_string(
        source["automationVersionPath"], "$.source.automationVersionPath"
    )

    vehicle = document["vehicle"]
    if not isinstance(vehicle, dict):
        fail("$.vehicle: objet attendu")

    require_exact_keys(
        vehicle,
        {"modelName", "modelNamePath", "trimName", "trimNamePath"},
        "$.vehicle",
    )

    for field_name in ("modelName", "modelNamePath", "trimName", "trimNamePath"):
        require_nullable_string(vehicle[field_name], f"$.vehicle.{field_name}")

    diagnostics = document["diagnostics"]
    if not isinstance(diagnostics, list):
        fail("$.diagnostics: tableau attendu")

    if len(diagnostics) != len(set(diagnostics)):
        fail("$.diagnostics: diagnostics dupliqués")

    for index, diagnostic in enumerate(diagnostics):
        require_non_empty_string(diagnostic, f"$.diagnostics[{index}]")

    reject_absolute_paths(document)

    warnings: list[str] = []

    if vehicle["modelName"] is None:
        warnings.append("nom du modèle non récupéré")

    if vehicle["trimName"] is None:
        warnings.append("nom du trim non récupéré")

    if source["automationVersion"] is None:
        warnings.append("version d'Automation non exposée par les données Lua")

    if document["exportedAtUtc"] is None:
        warnings.append("horloge UTC indisponible dans l'environnement Lua")

    return warnings


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valide un export JSON du test de fumée Automation LAP."
    )
    parser.add_argument("export", type=Path, help="Fichier automation-lap-vehicle.json")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        with arguments.export.open("r", encoding="utf-8") as stream:
            document = json.load(stream)

        warnings = validate_document(document)
    except FileNotFoundError:
        print(f"ERREUR: fichier introuvable: {arguments.export}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as error:
        print(f"ERREUR: le fichier n'est pas un UTF-8 valide: {error}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as error:
        print(
            f"ERREUR: JSON invalide à la ligne {error.lineno}, colonne {error.colno}: "
            f"{error.msg}",
            file=sys.stderr,
        )
        return 2
    except ValidationError as error:
        print(f"ÉCHEC: {error}", file=sys.stderr)
        return 1

    print("SUCCÈS: l'export respecte le contrat du test de fumée v0.1.0.")

    for warning in warnings:
        print(f"AVERTISSEMENT: {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
