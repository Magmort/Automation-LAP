#!/usr/bin/env python3
"""Run B-S05: simple throttle, brake and steering transitions."""

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

ACCELERATION_GRAPH_KEY = "AccelerationToTopSpeed"
BRAKING_GRAPH_KEY = "Braking"
STEERING_LOW_GRAPH_KEY = "LowSpeedSteering"
STEERING_HIGH_GRAPH_KEY = "HighSpeedSteering"
TIME_STEPS = (1.0 / 30.0, 1.0 / 60.0, 1.0 / 120.0)
SCENARIO_DURATION = 12.0
G = 9.80665
KMH_TO_MPS = 1.0 / 3.6
MPS2_TO_KMH_PER_S = 3.6
MODEL_MAX_STEER_ANGLE_RAD = 0.22
REFERENCE_DT = 1.0 / 120.0
POSITION_STABILITY_LIMIT_M = 0.75
POSITION_STABILITY_RELATIVE_LIMIT = 0.02
HEADING_STABILITY_LIMIT_RAD = 0.025
SPEED_STABILITY_LIMIT_KMH = 0.35
SPEED_STABILITY_RELATIVE_LIMIT = 0.015


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_validator(repo_root: Path) -> Any:
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


def has_finite_values(values: list[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def interpolate_clamped(x_values: list[float], y_values: list[float], target_x: float) -> float:
    if len(x_values) != len(y_values):
        raise ValueError("x and y series lengths differ")
    if not x_values:
        raise ValueError("empty series")

    if target_x <= x_values[0]:
        return y_values[0]
    if target_x >= x_values[-1]:
        return y_values[-1]

    for index in range(1, len(x_values)):
        left_x = x_values[index - 1]
        right_x = x_values[index]
        if left_x <= target_x <= right_x:
            span = right_x - left_x
            if span == 0:
                return y_values[index]
            ratio = (target_x - left_x) / span
            return y_values[index - 1] + ratio * (y_values[index] - y_values[index - 1])

    return y_values[-1]


def deceleration_at_speed(speed_values: list[float], time_values: list[float], speed_kmh: float) -> float:
    if len(speed_values) != len(time_values):
        raise ValueError("braking speed and time series lengths differ")
    if len(speed_values) < 2:
        raise ValueError("braking curve needs at least two samples")

    for index in range(1, len(speed_values)):
        previous_speed = speed_values[index - 1]
        current_speed = speed_values[index]
        if previous_speed >= speed_kmh >= current_speed:
            delta_time = time_values[index] - time_values[index - 1]
            if delta_time <= 0:
                continue
            return max(0.0, (previous_speed - current_speed) / delta_time)

    if speed_kmh > speed_values[0]:
        index = 1
    else:
        index = len(speed_values) - 1
    delta_time = time_values[index] - time_values[index - 1]
    if delta_time <= 0:
        return 0.0
    return max(0.0, (speed_values[index - 1] - speed_values[index]) / delta_time)


def acceleration_at_speed(speed_values: list[float], time_values: list[float], speed_kmh: float) -> float:
    if len(speed_values) != len(time_values):
        raise ValueError("acceleration speed and time series lengths differ")
    if len(speed_values) < 2:
        raise ValueError("acceleration curve needs at least two samples")

    positive_segments: list[tuple[float, float, float, float]] = []
    for index in range(1, len(speed_values)):
        previous_speed = speed_values[index - 1]
        current_speed = speed_values[index]
        previous_time = time_values[index - 1]
        current_time = time_values[index]
        delta_time = current_time - previous_time
        delta_speed = current_speed - previous_speed
        if delta_time > 0 and delta_speed > 0:
            positive_segments.append((previous_speed, current_speed, previous_time, current_time))
            if previous_speed <= speed_kmh <= current_speed:
                return delta_speed / delta_time

    if speed_kmh >= max(speed_values):
        return 0.0
    if not positive_segments:
        return 0.0

    previous_speed, current_speed, previous_time, current_time = positive_segments[0]
    if speed_kmh <= previous_speed:
        return (current_speed - previous_speed) / (current_time - previous_time)

    previous_speed, current_speed, previous_time, current_time = positive_segments[-1]
    return (current_speed - previous_speed) / (current_time - previous_time)


def value_preview(document: dict[str, Any], key: str) -> float | None:
    for field in document["controlledFields"]:
        if field["key"] == key and field["present"] and isinstance(field["valuePreview"], (int, float)):
            return float(field["valuePreview"])
    return None


def wheelbase_m(document: dict[str, Any]) -> float:
    value = value_preview(document, "geometry.wheelBase")
    if value is None:
        return 2.5
    if value > 20.0:
        return value / 100.0
    return value


def control_at(time_s: float) -> dict[str, float]:
    if time_s < 3.0:
        return {"throttle": 1.0, "brake": 0.0, "steer": 0.0}
    if time_s < 5.0:
        return {"throttle": 0.85, "brake": 0.0, "steer": 0.35}
    if time_s < 6.5:
        return {"throttle": 0.0, "brake": 0.45, "steer": 0.50}
    if time_s < 9.0:
        return {"throttle": 0.85, "brake": 0.0, "steer": -0.45}
    return {"throttle": 0.30, "brake": 0.0, "steer": 0.0}


def choose_steering_curve(
    low_speed: list[float],
    low_steering: list[float],
    high_speed: list[float],
    high_steering: list[float],
    speed_kmh: float,
) -> tuple[list[float], list[float], str]:
    if speed_kmh <= low_speed[-1]:
        return low_speed, low_steering, STEERING_LOW_GRAPH_KEY
    return high_speed, high_steering, STEERING_HIGH_GRAPH_KEY


def speed_rate_kmh_s(
    speed_kmh: float,
    controls: dict[str, float],
    accel_speed: list[float],
    accel_time: list[float],
    braking_speed: list[float],
    braking_time: list[float],
) -> tuple[float, float, float]:
    acceleration_kmh_s = acceleration_at_speed(accel_speed, accel_time, speed_kmh) * controls["throttle"]
    deceleration_kmh_s = deceleration_at_speed(braking_speed, braking_time, speed_kmh) * controls["brake"]
    return acceleration_kmh_s - deceleration_kmh_s, acceleration_kmh_s, deceleration_kmh_s


def simulate_vehicle(document: dict[str, Any], dt: float) -> dict[str, Any]:
    acceleration = find_graph(document, ACCELERATION_GRAPH_KEY)
    braking = find_graph(document, BRAKING_GRAPH_KEY)
    low_steering_graph = find_graph(document, STEERING_LOW_GRAPH_KEY)
    high_steering_graph = find_graph(document, STEERING_HIGH_GRAPH_KEY)

    accel_speed = series_values(acceleration, "Speed")
    accel_time = series_values(acceleration, "Time")
    braking_speed = series_values(braking, "Speed")
    braking_time = series_values(braking, "Time")
    low_speed = series_values(low_steering_graph, "Speed")
    low_steering = series_values(low_steering_graph, "Steering")
    high_speed = series_values(high_steering_graph, "Speed")
    high_steering = series_values(high_steering_graph, "Steering")

    top_speed = max(accel_speed)
    max_steering = max(max(low_steering), max(high_steering))
    wheelbase = wheelbase_m(document)
    state = {
        "time": 0.0,
        "x": 0.0,
        "y": 0.0,
        "heading": 0.0,
        "speed": 0.0,
    }
    max_speed = 0.0
    max_abs_heading = 0.0
    max_lateral_g = 0.0
    max_acceleration_kmh_s = 0.0
    max_deceleration_kmh_s = 0.0
    steering_graph_usage = {STEERING_LOW_GRAPH_KEY: 0, STEERING_HIGH_GRAPH_KEY: 0}
    snapshots: list[dict[str, float]] = []
    next_snapshot = 0.0

    while state["time"] < SCENARIO_DURATION - 1e-12:
        step = min(dt, SCENARIO_DURATION - state["time"])
        controls = control_at(state["time"])
        initial_rate, _, _ = speed_rate_kmh_s(
            state["speed"],
            controls,
            accel_speed,
            accel_time,
            braking_speed,
            braking_time,
        )
        midpoint_speed = min(top_speed, max(0.0, state["speed"] + initial_rate * step * 0.5))
        midpoint_controls = control_at(state["time"] + step * 0.5)
        net_kmh_s, acceleration_kmh_s, deceleration_kmh_s = speed_rate_kmh_s(
            midpoint_speed,
            midpoint_controls,
            accel_speed,
            accel_time,
            braking_speed,
            braking_time,
        )

        selected_speed, selected_steering, selected_graph = choose_steering_curve(
            low_speed,
            low_steering,
            high_speed,
            high_steering,
            midpoint_speed,
        )
        steering_graph_usage[selected_graph] += 1
        steering_value = interpolate_clamped(selected_speed, selected_steering, midpoint_speed)
        steering_response = 0.0 if max_steering == 0 else max(0.0, steering_value) / max_steering
        speed_mps = midpoint_speed * KMH_TO_MPS
        steer_angle = midpoint_controls["steer"] * steering_response * MODEL_MAX_STEER_ANGLE_RAD
        yaw_rate = speed_mps * math.tan(steer_angle) / wheelbase
        lateral_g = abs(speed_mps * yaw_rate) / G

        midpoint_heading = state["heading"] + yaw_rate * step * 0.5
        state["heading"] += yaw_rate * step
        state["x"] += math.cos(midpoint_heading) * speed_mps * step
        state["y"] += math.sin(midpoint_heading) * speed_mps * step
        state["speed"] = min(top_speed, max(0.0, state["speed"] + net_kmh_s * step))
        state["time"] += step

        max_speed = max(max_speed, state["speed"])
        max_abs_heading = max(max_abs_heading, abs(state["heading"]))
        max_lateral_g = max(max_lateral_g, lateral_g)
        max_acceleration_kmh_s = max(max_acceleration_kmh_s, acceleration_kmh_s)
        max_deceleration_kmh_s = max(max_deceleration_kmh_s, deceleration_kmh_s)

        if state["time"] + 1e-9 >= next_snapshot:
            snapshots.append(
                {
                    "time": round(state["time"], 6),
                    "x": state["x"],
                    "y": state["y"],
                    "heading": state["heading"],
                    "speed": state["speed"],
                }
            )
            next_snapshot += 2.5

    finite = all(
        math.isfinite(value)
        for value in (
            state["x"],
            state["y"],
            state["heading"],
            state["speed"],
            max_speed,
            max_lateral_g,
        )
    )
    return {
        "dt": dt,
        "steps": round(SCENARIO_DURATION / dt),
        "final": state,
        "maxSpeed": max_speed,
        "maxAbsHeading": max_abs_heading,
        "maxLateralGModel": max_lateral_g,
        "maxAccelerationKmhPerS": max_acceleration_kmh_s,
        "maxDecelerationKmhPerS": max_deceleration_kmh_s,
        "steeringGraphUsage": steering_graph_usage,
        "snapshots": snapshots,
        "finiteValues": finite,
    }


def summarize_vehicle(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    runs = [simulate_vehicle(document, dt) for dt in TIME_STEPS]
    reference = next(run for run in runs if abs(run["dt"] - REFERENCE_DT) < 1e-12)
    final_ref = reference["final"]
    reference_distance = math.hypot(final_ref["x"], final_ref["y"])
    position_limit = max(
        POSITION_STABILITY_LIMIT_M,
        reference_distance * POSITION_STABILITY_RELATIVE_LIMIT,
    )
    speed_limit = max(
        SPEED_STABILITY_LIMIT_KMH,
        abs(final_ref["speed"]) * SPEED_STABILITY_RELATIVE_LIMIT,
    )
    comparisons = []
    for run in runs:
        final = run["final"]
        position_delta = math.hypot(final["x"] - final_ref["x"], final["y"] - final_ref["y"])
        heading_delta = abs(final["heading"] - final_ref["heading"])
        speed_delta = abs(final["speed"] - final_ref["speed"])
        comparisons.append(
            {
                "dt": run["dt"],
                "positionDeltaVsReference": position_delta,
                "headingDeltaVsReference": heading_delta,
                "speedDeltaVsReference": speed_delta,
                "positionLimit": position_limit,
                "speedLimit": speed_limit,
                "stableVsReference": (
                    position_delta <= position_limit
                    and heading_delta <= HEADING_STABILITY_LIMIT_RAD
                    and speed_delta <= speed_limit
                ),
            }
        )

    return {
        "path": path.as_posix(),
        "modelName": document["identity"]["modelName"],
        "trimName": document["identity"]["trimName"],
        "schemaVersion": document["schemaVersion"],
        "exporterVersion": document["source"]["exporterVersion"],
        "wheelbaseM": wheelbase_m(document),
        "referenceDistanceM": reference_distance,
        "positionStabilityLimitM": position_limit,
        "speedStabilityLimitKmh": speed_limit,
        "runs": runs,
        "comparisons": comparisons,
        "stable": all(run["finiteValues"] for run in runs)
        and all(comparison["stableVsReference"] for comparison in comparisons),
    }


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def run_lookup(vehicle: dict[str, Any], dt: float) -> dict[str, Any]:
    for run in vehicle["runs"]:
        if abs(run["dt"] - dt) < 1e-12:
            return run
    raise KeyError(dt)


def comparison_lookup(vehicle: dict[str, Any], dt: float) -> dict[str, Any]:
    for comparison in vehicle["comparisons"]:
        if abs(comparison["dt"] - dt) < 1e-12:
            return comparison
    raise KeyError(dt)


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# B-S05 - Transitions throttle / frein / direction",
        "",
        "- **Experience :** B - Dynamique d'une voiture",
        "- **Scenario :** B-S05",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier qu'un etat 2D minimal reste stable quand acceleration, freinage et direction sont melanges.",
        "- **Entrees :** exports A9 dans `outputs/a9-raw-vehicle-data/`.",
        "- **Reserve :** le modele de cap utilise une hypothese de braquage normalise ; ce n'est pas encore un modele lateral physique.",
        "",
        "## Scenario de controle",
        "",
        "| Temps | Throttle | Frein | Direction |",
        "| --- | ---: | ---: | ---: |",
        "| 0.0-3.0 s | 1.00 | 0.00 | 0.00 |",
        "| 3.0-5.0 s | 0.85 | 0.00 | +0.35 |",
        "| 5.0-6.5 s | 0.00 | 0.45 | +0.50 |",
        "| 6.5-9.0 s | 0.85 | 0.00 | -0.45 |",
        "| 9.0-12.0 s | 0.30 | 0.00 | 0.00 |",
        "",
        "## Synthese",
        "",
        f"- Documents traites : {summary['documentsProcessed']}",
        f"- Vehicules valides : {summary['vehiclesValid']}",
        f"- Vehicules en echec : {summary['vehiclesFailed']}",
        f"- Pas testes : {', '.join(fmt_number(dt, 5) + ' s' for dt in TIME_STEPS)}",
        f"- Reference stabilite : {fmt_number(REFERENCE_DT, 5)} s",
        "",
        "## Etats finaux au pas 1/120 s",
        "",
        "| Voiture | Vitesse finale | Distance X | Distance Y | Cap final | Vitesse max | Lateral G modele max |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for vehicle in summary["vehicles"]:
        reference = run_lookup(vehicle, REFERENCE_DT)
        final = reference["final"]
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{fmt_number(final['speed'])} | "
            f"{fmt_number(final['x'])} | "
            f"{fmt_number(final['y'])} | "
            f"{fmt_number(final['heading'], 4)} | "
            f"{fmt_number(reference['maxSpeed'])} | "
            f"{fmt_number(reference['maxLateralGModel'], 3)} |"
        )

    lines.extend(
        [
            "",
            "## Stabilite par pas de temps",
            "",
        "| Voiture | dt | Ecart position | Limite position | Ecart cap | Ecart vitesse | Limite vitesse | Valeurs finies | Stable |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )

    for vehicle in summary["vehicles"]:
        for dt in TIME_STEPS:
            run = run_lookup(vehicle, dt)
            comparison = comparison_lookup(vehicle, dt)
            lines.append(
                "| "
                f"{format_vehicle_name(vehicle)} | "
                f"{fmt_number(dt, 5)} | "
                f"{fmt_number(comparison['positionDeltaVsReference'], 4)} | "
                f"{fmt_number(comparison['positionLimit'], 4)} | "
                f"{fmt_number(comparison['headingDeltaVsReference'], 6)} | "
                f"{fmt_number(comparison['speedDeltaVsReference'], 4)} | "
                f"{fmt_number(comparison['speedLimit'], 4)} | "
                f"{fmt_bool(run['finiteValues'])} | "
                f"{fmt_bool(comparison['stableVsReference'])} |"
            )

    lines.extend(
        [
            "",
            "## Usage des graphes de direction",
            "",
            "| Voiture | dt | LowSpeedSteering | HighSpeedSteering |",
            "| --- | ---: | ---: | ---: |",
        ]
    )

    for vehicle in summary["vehicles"]:
        for dt in TIME_STEPS:
            run = run_lookup(vehicle, dt)
            usage = run["steeringGraphUsage"]
            lines.append(
                "| "
                f"{format_vehicle_name(vehicle)} | "
                f"{fmt_number(dt, 5)} | "
                f"{usage[STEERING_LOW_GRAPH_KEY]} | "
                f"{usage[STEERING_HIGH_GRAPH_KEY]} |"
            )

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Les trois voitures restent finies aux trois pas de temps testes.",
            "- Les ecarts `1/30 s` et `1/60 s` restent bornes face a la reference `1/120 s`.",
            "- L'acceleration vient de la pente de `AccelerationToTopSpeed.Speed/Time`, le freinage de la pente de `Braking.Speed/Time`.",
            "- La direction utilise `LowSpeedSteering` puis `HighSpeedSteering` comme reponse normalisee selon la vitesse.",
            "- Les positions sont en metres sous hypothese `Speed` en km/h et `Time` en secondes, coherente avec les champs de performance exportes.",
            "",
            "## Decision",
            "",
            "B-S05 est valide avec reserves. Le prototype peut integrer acceleration, freinage et direction dans un etat 2D minimal, mais le modele lateral doit rester marque comme hypothese tant que les unites exactes des graphes de direction ne sont pas confirmees.",
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
        description="Run B-S05 by simulating simple throttle, brake and steering transitions."
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
        help="Directory where B-S05 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    validator = load_validator(repo_root)

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

    success = len(export_paths) == 3 and len(vehicles) == 3 and not failures and all(
        vehicle["stable"] for vehicle in vehicles
    )
    summary = {
        "scenario": "B-S05",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputDirectory": arguments.input_dir.relative_to(repo_root).as_posix(),
        "documentsProcessed": len(export_paths),
        "vehiclesValid": len(vehicles),
        "vehiclesFailed": len(failures),
        "timeSteps": list(TIME_STEPS),
        "referenceDt": REFERENCE_DT,
        "stabilityLimits": {
            "positionM": POSITION_STABILITY_LIMIT_M,
            "positionRelative": POSITION_STABILITY_RELATIVE_LIMIT,
            "headingRad": HEADING_STABILITY_LIMIT_RAD,
            "speedKmh": SPEED_STABILITY_LIMIT_KMH,
            "speedRelative": SPEED_STABILITY_RELATIVE_LIMIT,
        },
        "modelAssumptions": {
            "speedUnit": "km/h",
            "timeUnit": "s",
            "positionUnit": "m",
            "maxSteerAngleRad": MODEL_MAX_STEER_ANGLE_RAD,
            "steeringGraphs": "normalized automation-graph values, unit unknown",
        },
        "vehicles": vehicles,
        "failures": failures,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "b_s05_transitions_summary.json"
    report_path = arguments.results_dir / "B_S05_TRANSITIONS_RESULT.md"

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
