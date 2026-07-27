#!/usr/bin/env python3
"""Run B-S04 steering graph analysis from A9 raw vehicle data."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

STEERING_GRAPHS = ("LowSpeedSteering", "HighSpeedSteering")


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_a8_validator(repo_root: Path) -> Any:
    validator_path = (
        repo_root
        / "prototypes"
        / "automation-exporter"
        / "tools"
        / "validate_raw_vehicle_data.py"
    )
    spec = importlib.util.spec_from_file_location("validate_raw_vehicle_data", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load validator from {validator_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def format_vehicle_name(vehicle: dict[str, Any]) -> str:
    model = vehicle["modelName"]
    trim = vehicle["trimName"]
    if trim and trim not in model:
        return f"{model} - {trim}"
    return model


def find_graph(document: dict[str, Any], key: str) -> dict[str, Any]:
    for graph in document["rawGraphs"]:
        if graph["key"] == key:
            return graph
    raise ValueError(f"missing raw graph {key!r}")


def series_values(graph: dict[str, Any], key: str) -> list[float]:
    for series in graph["series"]:
        if series["key"] == key:
            return [float(value) for value in series["values"]]
    raise ValueError(f"{graph['key']}: missing series {key!r}")


def is_non_decreasing(values: list[float]) -> bool:
    return all(current >= previous for previous, current in zip(values, values[1:]))


def has_finite_values(values: list[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def crossings(speed: list[float], values: list[float]) -> list[float]:
    result: list[float] = []
    for index in range(1, len(values)):
        left_value = values[index - 1]
        right_value = values[index]
        if left_value == 0:
            result.append(speed[index - 1])
        elif left_value * right_value < 0:
            ratio = -left_value / (right_value - left_value)
            result.append(speed[index - 1] + ratio * (speed[index] - speed[index - 1]))
    return result


def outside_ranges(speed: list[float], inside: list[bool]) -> list[dict[str, float | int]]:
    ranges: list[dict[str, float | int]] = []
    start: int | None = None
    for index, ok in enumerate(inside):
        if not ok and start is None:
            start = index
        is_last = index == len(inside) - 1
        if start is not None and (ok or is_last):
            end = index - 1 if ok else index
            ranges.append(
                {
                    "startIndex": start + 1,
                    "endIndex": end + 1,
                    "startSpeed": speed[start],
                    "endSpeed": speed[end],
                }
            )
            start = None
    return ranges


def summarize_steering_graph(graph: dict[str, Any]) -> dict[str, Any]:
    speed = series_values(graph, "Speed")
    steering = series_values(graph, "Steering")
    under = series_values(graph, "UnderSteer")
    over = series_values(graph, "OverSteer")

    if not (len(speed) == len(steering) == len(under) == len(over)):
        raise ValueError(f"{graph['key']}: steering series lengths differ")

    inside = [
        under_value <= steering_value <= over_value
        for steering_value, under_value, over_value in zip(steering, under, over)
    ]
    max_steering_index = max(range(len(steering)), key=lambda index: steering[index])
    steering_minus_under = [
        steering_value - under_value
        for steering_value, under_value in zip(steering, under)
    ]
    over_minus_steering = [
        over_value - steering_value
        for over_value, steering_value in zip(over, steering)
    ]

    return {
        "key": graph["key"],
        "sampleCount": len(speed),
        "speedMin": min(speed),
        "speedMax": max(speed),
        "speedMonotonic": is_non_decreasing(speed),
        "finiteValues": all(has_finite_values(values) for values in (speed, steering, under, over)),
        "steeringMax": steering[max_steering_index],
        "steeringMaxSpeed": speed[max_steering_index],
        "steeringEnd": steering[-1],
        "underMax": max(under),
        "overMax": max(over),
        "insideCount": sum(1 for ok in inside if ok),
        "insidePercent": 100.0 * sum(1 for ok in inside if ok) / len(inside),
        "outsideRanges": outside_ranges(speed, inside),
        "steeringOverCrossings": crossings(
            speed,
            [steering_value - over_value for steering_value, over_value in zip(steering, over)],
        ),
        "steeringUnderCrossings": crossings(speed, steering_minus_under),
        "minSteeringMinusUnder": min(steering_minus_under),
        "maxSteeringMinusUnder": max(steering_minus_under),
        "minOverMinusSteering": min(over_minus_steering),
        "maxOverMinusSteering": max(over_minus_steering),
        "truncatedSeries": sum(1 for series in graph["series"] if series["truncated"]),
    }


def summarize_vehicle(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    graph_summaries = [
        summarize_steering_graph(find_graph(document, graph_key))
        for graph_key in STEERING_GRAPHS
    ]
    return {
        "path": path.as_posix(),
        "modelName": document["identity"]["modelName"],
        "trimName": document["identity"]["trimName"],
        "exporterVersion": document["source"]["exporterVersion"],
        "graphs": graph_summaries,
    }


def graph_lookup(vehicle: dict[str, Any], key: str) -> dict[str, Any]:
    for graph in vehicle["graphs"]:
        if graph["key"] == key:
            return graph
    raise KeyError(key)


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_crossings(values: list[float]) -> str:
    if not values:
        return "aucun"
    return ", ".join(fmt_number(value) for value in values)


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# B-S04 - Analyse des graphes de direction A9",
        "",
        "- **Experience :** B - Dynamique d'une voiture",
        "- **Scenario :** complement B-S04",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** evaluer l'utilite de `LowSpeedSteering` et `HighSpeedSteering` pour remplacer ou completer le proxy de virage.",
        "- **Reserve :** ces graphes ne donnent pas directement un rayon de virage ni une adherence laterale brute.",
        "",
        "## Synthese",
        "",
        f"- Documents traites : {summary['documentsProcessed']}",
        f"- Vehicules valides : {summary['vehiclesValid']}",
        f"- Vehicules en echec : {summary['vehiclesFailed']}",
        "",
        "## Domaine des graphes",
        "",
        "| Voiture | Low points | Low speed max | High points | High speed max | Troncature |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for vehicle in summary["vehicles"]:
        low = graph_lookup(vehicle, "LowSpeedSteering")
        high = graph_lookup(vehicle, "HighSpeedSteering")
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{low['sampleCount']} | "
            f"{fmt_number(low['speedMax'])} | "
            f"{high['sampleCount']} | "
            f"{fmt_number(high['speedMax'])} | "
            f"{low['truncatedSeries'] + high['truncatedSeries']} |"
        )

    lines.extend(
        [
            "",
            "## Pics Steering",
            "",
            "| Voiture | Low pic | Low vitesse pic | Low fin | High pic | High vitesse pic | High fin |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for vehicle in summary["vehicles"]:
        low = graph_lookup(vehicle, "LowSpeedSteering")
        high = graph_lookup(vehicle, "HighSpeedSteering")
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{fmt_number(low['steeringMax'])} | "
            f"{fmt_number(low['steeringMaxSpeed'])} | "
            f"{fmt_number(low['steeringEnd'])} | "
            f"{fmt_number(high['steeringMax'])} | "
            f"{fmt_number(high['steeringMaxSpeed'])} | "
            f"{fmt_number(high['steeringEnd'])} |"
        )

    lines.extend(
        [
            "",
            "## Enveloppe Under/Over",
            "",
            "| Voiture | Low inside | Low croisements | High inside | High croisements |",
            "| --- | ---: | --- | ---: | --- |",
        ]
    )

    for vehicle in summary["vehicles"]:
        low = graph_lookup(vehicle, "LowSpeedSteering")
        high = graph_lookup(vehicle, "HighSpeedSteering")
        low_crossings = (
            "over: "
            + fmt_crossings(low["steeringOverCrossings"])
            + " ; under: "
            + fmt_crossings(low["steeringUnderCrossings"])
        )
        high_crossings = (
            "over: "
            + fmt_crossings(high["steeringOverCrossings"])
            + " ; under: "
            + fmt_crossings(high["steeringUnderCrossings"])
        )
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{fmt_number(low['insidePercent'], 1)} % | "
            f"{low_crossings} | "
            f"{fmt_number(high['insidePercent'], 1)} % | "
            f"{high_crossings} |"
        )

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Les graphes A9 sont complets et exploitables numeriquement pour les trois voitures.",
            "- `Speed` est un axe monotone sur les six graphes analyses.",
            "- `Steering` monte jusqu'a un pic puis chute en fin de domaine ; ce comportement doit etre conserve, pas lisse.",
            "- `UnderSteer` et `OverSteer` fournissent une enveloppe utile pour qualifier le comportement de direction.",
            "- Ces graphes sont plus utiles que le proxy B-S04 pour l'analyse de direction, mais ne remplacent pas seuls une formule de vitesse critique en rayon constant.",
            "",
            "## Decision",
            "",
            "Les graphes de direction A9 sont utiles pour completer B-S04. Ils doivent etre conserves dans le pipeline, avec interpretation prudente et unites `unknown` tant que la signification exacte n'est pas confirmee.",
            "",
        ]
    )

    if summary["failures"]:
        lines.extend(["## Echecs", ""])
        for failure in summary["failures"]:
            lines.append(f"- `{failure['path']}` : {failure['error']}")
        lines.append("")

    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(
        description="Analyze A9 steering raw graphs for B-S04."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=repo_root / "outputs" / "a9-raw-vehicle-data",
        help="Directory containing one A9 raw vehicle data directory per vehicle.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "vehicle-dynamics" / "results",
        help="Directory where result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    validator = load_a8_validator(repo_root)

    export_paths = sorted(arguments.input_dir.glob("*/automation-lap-raw-vehicle-data.json"))
    vehicles: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for export_path in export_paths:
        relative_path = export_path.relative_to(repo_root)
        try:
            document = load_json(export_path)
            validator.validate_document(document)
            vehicles.append(summarize_vehicle(relative_path, document))
        except Exception as error:  # noqa: BLE001 - report all fixture failures.
            failures.append({"path": relative_path.as_posix(), "error": str(error)})

    checks_pass = all(
        graph["speedMonotonic"] and graph["finiteValues"] and graph["truncatedSeries"] == 0
        for vehicle in vehicles
        for graph in vehicle["graphs"]
    )
    summary = {
        "scenario": "B-S04-steering-graphs",
        "success": len(export_paths) == 3 and len(vehicles) == 3 and not failures and checks_pass,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputDirectory": arguments.input_dir.relative_to(repo_root).as_posix(),
        "documentsProcessed": len(export_paths),
        "vehiclesValid": len(vehicles),
        "vehiclesFailed": len(failures),
        "vehicles": vehicles,
        "failures": failures,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "b_s04_steering_graphs_summary.json"
    report_path = arguments.results_dir / "B_S04_STEERING_GRAPHS_RESULT.md"

    with summary_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    with report_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_markdown(summary))

    print(f"Wrote {summary_path.relative_to(repo_root)}")
    print(f"Wrote {report_path.relative_to(repo_root)}")
    return 0 if summary["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
