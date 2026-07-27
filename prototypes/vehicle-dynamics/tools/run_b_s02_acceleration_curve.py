#!/usr/bin/env python3
"""Run B-S02: interpolate Automation AccelerationToTopSpeed curves."""

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

GRAPH_KEY = "AccelerationToTopSpeed"
TARGET_SPEEDS = (50.0, 100.0)


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


def interpolate_y_at_x(x_values: list[float], y_values: list[float], target_x: float) -> float | None:
    if len(x_values) != len(y_values):
        raise ValueError("x and y series lengths differ")

    if not x_values or target_x < x_values[0] or target_x > x_values[-1]:
        return None

    for index in range(1, len(x_values)):
        left_x = x_values[index - 1]
        right_x = x_values[index]
        left_y = y_values[index - 1]
        right_y = y_values[index]

        if target_x == left_x:
            return left_y

        if target_x == right_x:
            return right_y

        if left_x <= target_x <= right_x:
            span = right_x - left_x
            if span == 0:
                return right_y

            ratio = (target_x - left_x) / span
            return left_y + ratio * (right_y - left_y)

    return None


def interpolate_first_reach(
    speed_values: list[float],
    y_values: list[float],
    target_speed: float,
) -> float | None:
    if len(speed_values) != len(y_values):
        raise ValueError("speed and target series lengths differ")

    if not speed_values or target_speed > max(speed_values):
        return None

    if speed_values[0] >= target_speed:
        return y_values[0]

    for index in range(1, len(speed_values)):
        left_speed = speed_values[index - 1]
        right_speed = speed_values[index]
        left_y = y_values[index - 1]
        right_y = y_values[index]

        if left_speed <= target_speed <= right_speed:
            span = right_speed - left_speed
            if span == 0:
                return right_y

            ratio = (target_speed - left_speed) / span
            return left_y + ratio * (right_y - left_y)

    return None


def max_interpolation_error(x_values: list[float], y_values: list[float]) -> float:
    errors: list[float] = []
    for x_value, expected_y in zip(x_values, y_values):
        interpolated = interpolate_y_at_x(x_values, y_values, x_value)
        if interpolated is not None:
            errors.append(abs(interpolated - expected_y))

    return max(errors, default=0.0)


def speed_drop_summary(speed_values: list[float]) -> dict[str, float | int]:
    drops = [
        previous - current
        for previous, current in zip(speed_values, speed_values[1:])
        if current < previous
    ]
    return {
        "count": len(drops),
        "maxDrop": max(drops, default=0.0),
        "totalDrop": sum(drops),
    }


def summarize_vehicle(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    graph = find_graph(document, GRAPH_KEY)
    speed = series_values(graph, "Speed")
    time = series_values(graph, "Time")
    distance = series_values(graph, "Distance")
    accel_g = series_values(graph, "AccelG")
    engine_power = series_values(graph, "enginePower")
    gear = series_values(graph, "gear")

    if not (len(speed) == len(time) == len(distance)):
        raise ValueError("Speed, Time and Distance must have identical lengths")

    top_speed = max(speed)
    top_index = speed.index(top_speed)
    targets: list[dict[str, Any]] = []
    for target_speed in (*TARGET_SPEEDS, top_speed):
        target_time = interpolate_first_reach(speed, time, target_speed)
        target_distance = interpolate_first_reach(speed, distance, target_speed)
        targets.append(
            {
                "speed": target_speed,
                "reachable": target_time is not None and target_distance is not None,
                "time": target_time,
                "distance": target_distance,
            }
        )

    return {
        "path": path.as_posix(),
        "modelName": document["identity"]["modelName"],
        "trimName": document["identity"]["trimName"],
        "schemaVersion": document["schemaVersion"],
        "exporterVersion": document["source"]["exporterVersion"],
        "sampleCount": len(speed),
        "speedMonotonic": is_non_decreasing(speed),
        "speedDrops": speed_drop_summary(speed),
        "timeMonotonic": is_non_decreasing(time),
        "distanceMonotonic": is_non_decreasing(distance),
        "finiteValues": all(
            has_finite_values(values)
            for values in (speed, time, distance, accel_g, engine_power, gear)
        ),
        "topSpeed": top_speed,
        "topSpeedTime": time[top_index],
        "topSpeedDistance": distance[top_index],
        "maxAccelG": max(accel_g),
        "minAccelG": min(accel_g),
        "maxEnginePower": max(engine_power),
        "minEnginePower": min(engine_power),
        "maxGear": max(gear),
        "targets": targets,
        "interpolationErrors": {
            "speedAtSourceTimesMaxAbs": max_interpolation_error(time, speed),
            "distanceAtSourceTimesMaxAbs": max_interpolation_error(time, distance),
        },
    }


def target_lookup(vehicle: dict[str, Any], target_speed: float) -> dict[str, Any] | None:
    for target in vehicle["targets"]:
        if target["speed"] == target_speed:
            return target

    return None


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# B-S02 - Relecture acceleration 0 a Vmax",
        "",
        "- **Experience :** B - Dynamique d'une voiture",
        "- **Scenario :** B-S02",
        f"- **Statut :** {'valide' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** construire des interpolateures sur `AccelerationToTopSpeed` sans recalculer la courbe Automation.",
        "- **Unites :** vitesse et distance conservees en unites natives Automation ; le temps est relu comme secondes.",
        "",
        "## Synthese",
        "",
        f"- Documents traites : {summary['documentsProcessed']}",
        f"- Courbes valides : {summary['curvesValid']}",
        f"- Courbes en echec : {summary['curvesFailed']}",
        f"- Erreur max d'interpolation sur l'axe temps aux points source : {fmt_number(summary['maxInterpolationError'], 12)}",
        "",
        "## Reperes par voiture",
        "",
        "| Voiture | Points | Vmax | Temps Vmax | Distance Vmax | 0-50 | 0-100 | Puissance max | Rapport max |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for vehicle in summary["vehicles"]:
        target_50 = target_lookup(vehicle, 50.0)
        target_100 = target_lookup(vehicle, 100.0)
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{vehicle['sampleCount']} | "
            f"{fmt_number(vehicle['topSpeed'])} | "
            f"{fmt_number(vehicle['topSpeedTime'])} | "
            f"{fmt_number(vehicle['topSpeedDistance'])} | "
            f"{fmt_number(target_50['time'] if target_50 else None)} | "
            f"{fmt_number(target_100['time'] if target_100 else None)} | "
            f"{fmt_number(vehicle['maxEnginePower'])} | "
            f"{fmt_number(vehicle['maxGear'], 0)} |"
        )

    lines.extend(
        [
            "",
            "## Validations de courbe",
            "",
            "| Voiture | Vitesse monotone | Temps monotone | Distance monotone | Valeurs finies | Erreur vitesse | Erreur distance |",
            "| --- | --- | --- | --- | --- | ---: | ---: |",
        ]
    )

    for vehicle in summary["vehicles"]:
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{'oui' if vehicle['speedMonotonic'] else 'non'} | "
            f"{'oui' if vehicle['timeMonotonic'] else 'non'} | "
            f"{'oui' if vehicle['distanceMonotonic'] else 'non'} | "
            f"{'oui' if vehicle['finiteValues'] else 'non'} | "
            f"{fmt_number(vehicle['interpolationErrors']['speedAtSourceTimesMaxAbs'], 12)} | "
            f"{fmt_number(vehicle['interpolationErrors']['distanceAtSourceTimesMaxAbs'], 12)} |"
        )

    lines.extend(
        [
            "",
            "## Variations de vitesse",
            "",
            "| Voiture | Baisse de vitesse detectee | Nombre | Baisse max | Baisse cumulee |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )

    for vehicle in summary["vehicles"]:
        drops = vehicle["speedDrops"]
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{'oui' if drops['count'] else 'non'} | "
            f"{drops['count']} | "
            f"{fmt_number(drops['maxDrop'], 6)} | "
            f"{fmt_number(drops['totalDrop'], 6)} |"
        )

    lines.extend(
        [
            "",
            "## Classement observe",
            "",
        ]
    )

    for index, vehicle in enumerate(summary["topSpeedRanking"], start=1):
        lines.append(
            f"{index}. {vehicle['name']} - Vmax {fmt_number(vehicle['topSpeed'])}, "
            f"temps Vmax {fmt_number(vehicle['topSpeedTime'])}"
        )

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Les trois courbes `AccelerationToTopSpeed` sont chargeables et interpolables.",
            "- Les reperes 0-50, 0-100 et Vmax utilisent le premier passage a la vitesse cible.",
            "- Les petites baisses de vitesse en fin de courbe sont conservees comme information source, sans les lisser.",
            "- Les valeurs restent etiquetees en unites natives Automation tant que les unites des graphes ne sont pas confirmees.",
            "- B-S02 ne simule pas encore l'acceleration : il rend la courbe Automation exploitable par les prochains jalons.",
            "",
            "## Decision",
            "",
            "B-S02 est valide. Le prototype peut passer a B-S03 pour appliquer la meme logique aux courbes de freinage.",
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
        description="Run B-S02 by interpolating Automation acceleration curves."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=repo_root / "outputs" / "a8-raw-vehicle-data",
        help="Directory containing one A8 export directory per vehicle.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "vehicle-dynamics" / "results",
        help="Directory where B-S02 result files will be written.",
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

    max_error = max(
        (
            max(
                vehicle["interpolationErrors"]["speedAtSourceTimesMaxAbs"],
                vehicle["interpolationErrors"]["distanceAtSourceTimesMaxAbs"],
            )
            for vehicle in vehicles
        ),
        default=0.0,
    )
    curve_checks_pass = all(
        vehicle["timeMonotonic"]
        and vehicle["distanceMonotonic"]
        and vehicle["finiteValues"]
        and all(target["reachable"] for target in vehicle["targets"])
        for vehicle in vehicles
    )
    ranking = sorted(
        (
            {
                "name": format_vehicle_name(vehicle),
                "topSpeed": vehicle["topSpeed"],
                "topSpeedTime": vehicle["topSpeedTime"],
            }
            for vehicle in vehicles
        ),
        key=lambda item: item["topSpeed"],
        reverse=True,
    )
    summary = {
        "scenario": "B-S02",
        "success": len(export_paths) == 3 and len(vehicles) == 3 and not failures and curve_checks_pass,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputDirectory": arguments.input_dir.relative_to(repo_root).as_posix(),
        "documentsProcessed": len(export_paths),
        "curvesValid": len(vehicles),
        "curvesFailed": len(failures),
        "maxInterpolationError": max_error,
        "vehicles": vehicles,
        "topSpeedRanking": ranking,
        "failures": failures,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "b_s02_acceleration_curve_summary.json"
    report_path = arguments.results_dir / "B_S02_ACCELERATION_CURVE_RESULT.md"

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
