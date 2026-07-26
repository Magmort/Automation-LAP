#!/usr/bin/env python3
"""Compare two Automation LAP smoke-test exports while ignoring timestamps."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


def load_document(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def normalized(document: Any) -> Any:
    value = deepcopy(document)

    if isinstance(value, dict):
        value.pop("exportedAtUtc", None)

    return value


def first_difference(left: Any, right: Any, path: str = "$") -> str | None:
    if type(left) is not type(right):
        return f"{path}: types différents ({type(left).__name__} / {type(right).__name__})"

    if isinstance(left, dict):
        left_keys = set(left)
        right_keys = set(right)

        if left_keys != right_keys:
            missing_left = sorted(right_keys - left_keys)
            missing_right = sorted(left_keys - right_keys)
            return (
                f"{path}: clés différentes; absentes à gauche={missing_left}, "
                f"absentes à droite={missing_right}"
            )

        for key in sorted(left_keys):
            difference = first_difference(left[key], right[key], f"{path}.{key}")

            if difference is not None:
                return difference

        return None

    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path}: tailles différentes ({len(left)} / {len(right)})"

        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            difference = first_difference(left_item, right_item, f"{path}[{index}]")

            if difference is not None:
                return difference

        return None

    if left != right:
        return f"{path}: valeurs différentes ({left!r} / {right!r})"

    return None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare deux exports du test de fumée hors horodatage UTC."
    )
    parser.add_argument("left", type=Path, help="Premier export JSON")
    parser.add_argument("right", type=Path, help="Second export JSON")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        left = normalized(load_document(arguments.left))
        right = normalized(load_document(arguments.right))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"ERREUR: impossible de lire les exports: {error}", file=sys.stderr)
        return 2

    difference = first_difference(left, right)

    if difference is not None:
        print(f"ÉCHEC: exports non équivalents: {difference}", file=sys.stderr)
        return 1

    print("SUCCÈS: les exports sont sémantiquement équivalents hors horodatage UTC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
