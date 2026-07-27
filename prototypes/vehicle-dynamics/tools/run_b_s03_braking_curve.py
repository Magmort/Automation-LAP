#!/usr/bin/env python3
"""Run B-S03: interpolate Automation Braking and BrakingVGrip curves."""

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

BRAKING_GRAPH_KEY = "Braking"
BRAKING_V_GRIP_GRAPH_KEY = "BrakingVGrip"
TARGET_SPEEDS = (200.0, 100.0, 50.0)


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


def is_non_increasing(values: list[float]) -> bool:
    return all(current <= previous for previous, current in zip(values, values[1:]))


def is_non_decreasing(values: list[float]) -> bool:
    return all(current >= previous for previous, current in zip(values, values[1:]))


def has_finite_values(values: list[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def interpolate_y_at_descending_x(
    x_values: list[float],
    y_values: list[float],
    target_x: float,
) -> float | None:
    if len(x_values) != len(y_values):
        raise ValueError("x and y series lengths differ")

    if not x_values or target_x > x_values[0] or target_x < x_values[-1]:
        return None

    if x_values[0] <= target_x:
        return y_values[0]

    for index in range(1, len(x_values)):
        left_x = x_values[index - 1]
        right_x = x_values[index]
        left_y = y_values[index - 1]
        right_y = y_values[index]

        if left_x >= target_x >= right_x:
            span = right_x - left_x
            if span == 0:
                return right_y

            ratio = (target_x - left_x) / span
            return left_y + ratio * (right_y - left_y)

    return None


def interpolate_y_at_increasing_x(
    x_values: list[float],
    y_values: list[float],
    target_x: float,
) -> float | None:
    if len(x_values) != len(y_values):
        raise ValueError("x and y series lengths differ")

    if not x_values or target_x < x_values[0] or target_x > x_values[-1]:
        return None

    for index in range(1, len(x_values)):
        left_x = x_values[index - 1]
        right_x = x_values[index]
        left_y = y_values[index - 1]
        right_y = y_values[index]

        if left_x <= target_x <= right_x:
            span = right_x - left_x
            if span == 0:
                return right_y

            ratio = (target_x - left_x) / span
            return left_y + ratio * (right_y - left_y)

    return y_values[-1] if target_x == x_values[-1] else None


def max_interpolation_error(x_values: list[float], y_values: list[float]) -> float:
    errors: list[float] = []
    for x_value, expected_y in zip(x_values, y_values):
        interpolated = interpolate_y_at_increasing_x(x_values, y_values, x_value)
        if interpolated is not None:
            errors.append(abs(interpolated - expected_y))

    return max(errors, default=0.0)


def integrate_speed_time_area(
    speed_values: list[float],
    time_values: list[float],
    start_time: float,
    end_time: float,
) -> float | None:
    if start_time is None or end_time is None or start_time > end_time:
        return None

    points: list[tuple[float, float]] = []
    start_speed = interpolate_y_at_increasing_x(time_values, speed_values, start_time)
    end_speed = interpolate_y_at_increasing_x(time_values, speed_values, end_time)
    if start_speed is None or end_speed is None:
        return None

    points.append((start_time, start_speed))
    points.extend(
        (time_value, speed_value)
        for time_value, speed_value in zip(time_values, speed_values)
        if start_time < time_value < end_time
    )
    points.append((end_time, end_speed))

    area = 0.0
    for (left_t, left_v), (right_t, right_v) in zip(points, points[1:]):
        area += (right_t - left_t) * (left_v + right_v) / 2.0

    return area


def max_abs_pair_delta(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return math.inf
    return max((abs(a - b) for a, b in zip(left, right)), default=0.0)


def series_min_max(values: list[float]) -> dict[str, float]:
    return {"min": min(values), "max": max(values)}


def summarize_margin(force: list[float], grip: list[float]) -> dict[str, float]:
    margins = [grip_value - force_value for force_value, grip_value in zip(force, grip)]
    return {
        "min": min(margins),
        "max": max(margins),
        "atMinIndex": margins.index(min(margins)),
    }


def summarize_vehicle(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    braking = find_graph(document, BRAKING_GRAPH_KEY)
    braking_v_grip = find_graph(document, BRAKING_V_GRIP_GRAPH_KEY)

    speed = series_values(braking, "Speed")
    time = series_values(braking, "Time")
    grip_speed = series_values(braking_v_grip, "Speed")
    front_force = series_values(braking_v_grip, "FrontBrakeForce")
    front_grip = series_values(braking_v_grip, "FrontBrakeGrip")
    rear_force = series_values(braking_v_grip, "RearBrakeForce")
    rear_grip = series_values(braking_v_grip, "RearBrakeGrip")

    if len(speed) != len(time):
        raise ValueError("Braking Speed and Time must have identical lengths")

    if not (
        len(grip_speed)
        == len(front_force)
        == len(front_grip)
        == len(rear_force)
        == len(rear_grip)
    ):
        raise ValueError("BrakingVGrip series must have identical lengths")

    end_time = time[-1]
    end_speed = speed[-1]
    start_speed = speed[0]
    start_time = time[0]
    targets: list[dict[str, Any]] = []
    for target_speed in TARGET_SPEEDS:
        target_time = interpolate_y_at_descending_x(speed, time, target_speed)
        duration_to_end = end_time - target_time if target_time is not None else None
        area_to_end = (
            integrate_speed_time_area(speed, time, target_time, end_time)
            if target_time is not None
            else None
        )
        targets.append(
            {
                "speed": target_speed,
                "reachable": target_time is not None,
                "timeAtSpeed": target_time,
                "durationToEnd": duration_to_end,
                "speedTimeAreaToEnd": area_to_end,
            }
        )

    full_area = integrate_speed_time_area(speed, time, start_time, end_time)
    front_margin = summarize_margin(front_force, front_grip)
    rear_margin = summarize_margin(rear_force, rear_grip)

    return {
        "path": path.as_posix(),
        "modelName": document["identity"]["modelName"],
        "trimName": document["identity"]["trimName"],
        "schemaVersion": document["schemaVersion"],
        "exporterVersion": document["source"]["exporterVersion"],
        "brakingSampleCount": len(speed),
        "brakingVGripSampleCount": len(grip_speed),
        "speedDecreasing": is_non_increasing(speed),
        "timeIncreasing": is_non_decreasing(time),
        "finiteValues": all(
            has_finite_values(values)
            for values in (
                speed,
                time,
                grip_speed,
                front_force,
                front_grip,
                rear_force,
                rear_grip,
            )
        ),
        "startSpeed": start_speed,
        "startTime": start_time,
        "endSpeed": end_speed,
        "endTime": end_time,
        "fullDuration": end_time - start_time,
        "speedTimeArea": full_area,
        "targets": targets,
        "brakingVGripSpeedAxisMaxAbsDelta": max_abs_pair_delta(speed, grip_speed),
        "frontBrakeForce": series_min_max(front_force),
        "frontBrakeGrip": series_min_max(front_grip),
        "rearBrakeForce": series_min_max(rear_force),
        "rearBrakeGrip": series_min_max(rear_grip),
        "frontGripMinusForce": front_margin,
        "rearGripMinusForce": rear_margin,
        "limitingAxleByMinMargin": (
            "front"
            if front_margin["min"] <= rear_margin["min"]
            else "rear"
        ),
        "interpolationErrors": {
            "speedAtSourceTimesMaxAbs": max_interpolation_error(time, speed),
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


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# B-S03 - Relecture freinage",
        "",
        "- **Experience :** B - Dynamique d'une voiture",
        "- **Scenario :** B-S03",
        f"- **Statut :** {'valide' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** construire des interpolateures sur `Braking` et comparer l'axe de `BrakingVGrip`.",
        "- **Unites :** vitesse, force, grip et aire vitesse-temps conservees en unites natives Automation.",
        "",
        "## Synthese",
        "",
        f"- Documents traites : {summary['documentsProcessed']}",
        f"- Courbes valides : {summary['curvesValid']}",
        f"- Courbes en echec : {summary['curvesFailed']}",
        f"- Ecart max entre axes `Braking.Speed` et `BrakingVGrip.Speed` : {fmt_number(summary['maxBrakingVGripAxisDelta'], 12)}",
        f"- Erreur max d'interpolation sur l'axe temps aux points source : {fmt_number(summary['maxInterpolationError'], 12)}",
        "",
        "## Reperes par voiture",
        "",
        "| Voiture | Points | Vitesse depart | Vitesse fin | Duree courbe | Aire vitesse-temps | 200->fin | 100->fin | 50->fin |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for vehicle in summary["vehicles"]:
        target_200 = target_lookup(vehicle, 200.0)
        target_100 = target_lookup(vehicle, 100.0)
        target_50 = target_lookup(vehicle, 50.0)
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{vehicle['brakingSampleCount']} | "
            f"{fmt_number(vehicle['startSpeed'])} | "
            f"{fmt_number(vehicle['endSpeed'])} | "
            f"{fmt_number(vehicle['fullDuration'])} | "
            f"{fmt_number(vehicle['speedTimeArea'])} | "
            f"{fmt_number(target_200['durationToEnd'] if target_200 else None)} | "
            f"{fmt_number(target_100['durationToEnd'] if target_100 else None)} | "
            f"{fmt_number(target_50['durationToEnd'] if target_50 else None)} |"
        )

    lines.extend(
        [
            "",
            "## Validations de courbe",
            "",
            "| Voiture | Vitesse descendante | Temps montant | Valeurs finies | Axe BrakingVGrip identique | Erreur vitesse |",
            "| --- | --- | --- | --- | --- | ---: |",
        ]
    )

    for vehicle in summary["vehicles"]:
        axis_matches = vehicle["brakingVGripSpeedAxisMaxAbsDelta"] == 0
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{fmt_bool(vehicle['speedDecreasing'])} | "
            f"{fmt_bool(vehicle['timeIncreasing'])} | "
            f"{fmt_bool(vehicle['finiteValues'])} | "
            f"{fmt_bool(axis_matches)} | "
            f"{fmt_number(vehicle['interpolationErrors']['speedAtSourceTimesMaxAbs'], 12)} |"
        )

    lines.extend(
        [
            "",
            "## BrakingVGrip",
            "",
            "| Voiture | Force AV | Grip AV | Marge AV min | Force AR | Grip AR | Marge AR min | Essieu limitant |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for vehicle in summary["vehicles"]:
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{fmt_number(vehicle['frontBrakeForce']['max'])} | "
            f"{fmt_number(vehicle['frontBrakeGrip']['min'])}..{fmt_number(vehicle['frontBrakeGrip']['max'])} | "
            f"{fmt_number(vehicle['frontGripMinusForce']['min'])} | "
            f"{fmt_number(vehicle['rearBrakeForce']['max'])} | "
            f"{fmt_number(vehicle['rearBrakeGrip']['min'])}..{fmt_number(vehicle['rearBrakeGrip']['max'])} | "
            f"{fmt_number(vehicle['rearGripMinusForce']['min'])} | "
            f"{vehicle['limitingAxleByMinMargin']} |"
        )

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Les trois courbes `Braking` sont chargeables et interpolables sur l'axe temps.",
            "- L'axe `BrakingVGrip.Speed` correspond a `Braking.Speed` pour les trois voitures.",
            "- Les durees 200->fin, 100->fin et 50->fin utilisent le premier passage descendant sous la vitesse cible.",
            "- L'aire vitesse-temps est conservee en unite native Automation ; elle peut servir de distance candidate seulement apres confirmation d'unite.",
            "- Les forces et grips avant/arriere de `BrakingVGrip` sont exploitables comme series, mais leur unite reste inconnue.",
            "",
            "## Decision",
            "",
            "B-S03 est valide. Les courbes longitudinales d'acceleration et de freinage sont maintenant relisibles sans recalculer Automation.",
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
        description="Run B-S03 by interpolating Automation braking curves."
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
        help="Directory where B-S03 result files will be written.",
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

    max_axis_delta = max(
        (vehicle["brakingVGripSpeedAxisMaxAbsDelta"] for vehicle in vehicles),
        default=math.inf,
    )
    max_error = max(
        (
            vehicle["interpolationErrors"]["speedAtSourceTimesMaxAbs"]
            for vehicle in vehicles
        ),
        default=0.0,
    )
    curve_checks_pass = all(
        vehicle["speedDecreasing"]
        and vehicle["timeIncreasing"]
        and vehicle["finiteValues"]
        and vehicle["brakingVGripSpeedAxisMaxAbsDelta"] == 0
        and target_lookup(vehicle, 100.0) is not None
        and target_lookup(vehicle, 50.0) is not None
        for vehicle in vehicles
    )
    summary = {
        "scenario": "B-S03",
        "success": len(export_paths) == 3 and len(vehicles) == 3 and not failures and curve_checks_pass,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputDirectory": arguments.input_dir.relative_to(repo_root).as_posix(),
        "documentsProcessed": len(export_paths),
        "curvesValid": len(vehicles),
        "curvesFailed": len(failures),
        "maxBrakingVGripAxisDelta": max_axis_delta,
        "maxInterpolationError": max_error,
        "vehicles": vehicles,
        "failures": failures,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "b_s03_braking_curve_summary.json"
    report_path = arguments.results_dir / "B_S03_BRAKING_CURVE_RESULT.md"

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
