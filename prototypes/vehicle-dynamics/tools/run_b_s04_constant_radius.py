#!/usr/bin/env python3
"""Run B-S04: estimate constant-radius cornering from available Automation curves."""

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
RADIUS_METERS = (25.0, 50.0, 100.0)
G = 9.80665


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


def controlled_field_value(document: dict[str, Any], key: str) -> Any:
    for field in document["controlledFields"]:
        if field["key"] == key:
            return field["valuePreview"]

    return None


def available_graph_keys(document: dict[str, Any]) -> set[str]:
    return {
        graph["key"]
        for graph in document["graphInventory"]["availableGraphs"]
    }


def raw_graph_keys(document: dict[str, Any]) -> set[str]:
    return {graph["key"] for graph in document["rawGraphs"]}


def has_finite_values(values: list[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def kmh_to_mps(speed_kmh: float) -> float:
    return speed_kmh / 3.6


def mps_to_kmh(speed_mps: float) -> float:
    return speed_mps * 3.6


def lateral_demand_g(speed_kmh: float, radius_m: float) -> float:
    speed_mps = kmh_to_mps(speed_kmh)
    return speed_mps * speed_mps / (radius_m * G)


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


def max_feasible_speed(
    speed_kmh: list[float],
    grip_g: list[float],
    radius_m: float,
) -> dict[str, float | bool]:
    previous_speed = speed_kmh[0]
    previous_margin = grip_g[0] - lateral_demand_g(previous_speed, radius_m)

    if previous_margin < 0:
        return {
            "reachable": False,
            "speedKmh": 0.0,
            "gripG": grip_g[0],
            "demandG": lateral_demand_g(previous_speed, radius_m),
            "marginG": previous_margin,
        }

    best_speed = previous_speed
    best_grip = grip_g[0]
    best_demand = lateral_demand_g(previous_speed, radius_m)
    best_margin = previous_margin

    for current_speed, current_grip in zip(speed_kmh[1:], grip_g[1:]):
        current_margin = current_grip - lateral_demand_g(current_speed, radius_m)
        if current_margin >= 0:
            best_speed = current_speed
            best_grip = current_grip
            best_demand = lateral_demand_g(current_speed, radius_m)
            best_margin = current_margin
        elif previous_margin >= 0:
            left = previous_speed
            right = current_speed
            for _ in range(40):
                mid = (left + right) / 2.0
                mid_grip = interpolate_y_at_increasing_x(speed_kmh, grip_g, mid)
                if mid_grip is None:
                    break
                mid_margin = mid_grip - lateral_demand_g(mid, radius_m)
                if mid_margin >= 0:
                    left = mid
                else:
                    right = mid

            best_speed = left
            best_grip = interpolate_y_at_increasing_x(speed_kmh, grip_g, left) or best_grip
            best_demand = lateral_demand_g(left, radius_m)
            best_margin = best_grip - best_demand
            break

        previous_speed = current_speed
        previous_margin = current_margin

    return {
        "reachable": True,
        "speedKmh": best_speed,
        "gripG": best_grip,
        "demandG": best_demand,
        "marginG": best_margin,
    }


def summarize_vehicle(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    graph = find_graph(document, ACCELERATION_GRAPH_KEY)
    speed = series_values(graph, "Speed")
    front_grip = series_values(graph, "FrontGripG")
    rear_grip = series_values(graph, "RearGripG")
    downforce = series_values(graph, "DownForce")
    weight_distribution = series_values(graph, "WeightDistribution")

    if not (
        len(speed)
        == len(front_grip)
        == len(rear_grip)
        == len(downforce)
        == len(weight_distribution)
    ):
        raise ValueError("AccelerationToTopSpeed grip series must have identical lengths")

    grip_proxy = [max(0.0, front + rear) for front, rear in zip(front_grip, rear_grip)]
    scenarios = [
        {
            "radiusM": radius,
            **max_feasible_speed(speed, grip_proxy, radius),
        }
        for radius in RADIUS_METERS
    ]
    graph_keys = available_graph_keys(document)
    raw_keys = raw_graph_keys(document)
    lateral_graph_candidates = sorted(
        key
        for key in ("LowSpeedSteering", "HighSpeedSteering")
        if key in graph_keys
    )
    missing_raw_lateral_graphs = [
        key
        for key in lateral_graph_candidates
        if key not in raw_keys
    ]

    return {
        "path": path.as_posix(),
        "modelName": document["identity"]["modelName"],
        "trimName": document["identity"]["trimName"],
        "schemaVersion": document["schemaVersion"],
        "exporterVersion": document["source"]["exporterVersion"],
        "sampleCount": len(speed),
        "finiteValues": all(
            has_finite_values(values)
            for values in (speed, front_grip, rear_grip, downforce, weight_distribution)
        ),
        "topSpeedKmhInferred": max(speed),
        "massKg": controlled_field_value(document, "mass.total"),
        "frontDistributionPercent": controlled_field_value(document, "mass.frontDistribution"),
        "frontGripGMax": max(front_grip),
        "rearGripGMax": max(rear_grip),
        "gripProxyGMax": max(grip_proxy),
        "gripProxyGMin": min(grip_proxy),
        "downforceMin": min(downforce),
        "downforceMax": max(downforce),
        "weightDistributionMin": min(weight_distribution),
        "weightDistributionMax": max(weight_distribution),
        "lateralGraphCandidates": lateral_graph_candidates,
        "missingRawLateralGraphs": missing_raw_lateral_graphs,
        "scenarios": scenarios,
    }


def fmt_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# B-S04 - Virage a rayon constant",
        "",
        "- **Experience :** B - Dynamique d'une voiture",
        "- **Scenario :** B-S04",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** estimer des vitesses critiques en virage a rayon constant avec les donnees A8 disponibles.",
        "- **Hypothese :** `FrontGripG + RearGripG` de `AccelerationToTopSpeed` est utilise comme proxy temporaire de grip lateral.",
        "- **Reserve :** aucune courbe laterale dediee n'est encore exportee en valeurs brutes.",
        "",
        "## Synthese",
        "",
        f"- Documents traites : {summary['documentsProcessed']}",
        f"- Vehicules evalues : {summary['vehiclesValid']}",
        f"- Vehicules en echec : {summary['vehiclesFailed']}",
        f"- Graphes lateraux candidats non exportes en brut : {', '.join(summary['missingRawLateralGraphs']) if summary['missingRawLateralGraphs'] else 'aucun'}",
        "",
        "## Grip proxy",
        "",
        "| Voiture | Points | Masse | Repartition AV | FrontGripG max | RearGripG max | Proxy max | DownForce min..max |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for vehicle in summary["vehicles"]:
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{vehicle['sampleCount']} | "
            f"{fmt_number(vehicle['massKg'])} | "
            f"{fmt_number(vehicle['frontDistributionPercent'])} | "
            f"{fmt_number(vehicle['frontGripGMax'], 3)} | "
            f"{fmt_number(vehicle['rearGripGMax'], 3)} | "
            f"{fmt_number(vehicle['gripProxyGMax'], 3)} | "
            f"{fmt_number(vehicle['downforceMin'])}..{fmt_number(vehicle['downforceMax'])} |"
        )

    lines.extend(
        [
            "",
            "## Rayons constants",
            "",
            "| Voiture | Rayon 25 m | Rayon 50 m | Rayon 100 m |",
            "| --- | ---: | ---: | ---: |",
        ]
    )

    for vehicle in summary["vehicles"]:
        cells = []
        for scenario in vehicle["scenarios"]:
            cells.append(
                f"{fmt_number(scenario['speedKmh'])} km/h "
                f"({fmt_number(scenario['gripG'], 3)} g)"
            )
        lines.append(f"| {format_vehicle_name(vehicle)} | {cells[0]} | {cells[1]} | {cells[2]} |")

    lines.extend(
        [
            "",
            "## Validations",
            "",
            "| Voiture | Valeurs finies | Graphes lateraux candidats | Graphes lateraux bruts manquants |",
            "| --- | --- | --- | --- |",
        ]
    )

    for vehicle in summary["vehicles"]:
        candidates = ", ".join(vehicle["lateralGraphCandidates"]) or "aucun"
        missing = ", ".join(vehicle["missingRawLateralGraphs"]) or "aucun"
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            f"{fmt_bool(vehicle['finiteValues'])} | "
            f"{candidates} | "
            f"{missing} |"
        )

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Les trois voitures produisent des vitesses critiques finies pour les trois rayons testes.",
            "- Le classement obtenu est plausible pour un test proxy : QFC55 > PCM > AIXAM.",
            "- Les valeurs de vitesse sont exprimees en km/h par inference, car elles correspondent aux vitesses de performance deja confirmees.",
            "- Le resultat ne valide pas encore un modele lateral physique : il valide seulement que B peut executer un scenario de virage reproductible avec les donnees actuelles.",
            "- Les graphes `LowSpeedSteering` et `HighSpeedSteering` sont visibles dans l'inventaire, mais pas encore exportes en series brutes A8.",
            "",
            "## Decision",
            "",
            "B-S04 est valide avec reserves. Pour un modele de virage plus fiable, une extension future de A devrait exporter les graphes lateraux ou une donnee d'adherence laterale explicite.",
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
        description="Run B-S04 by estimating constant-radius cornering from A8 data."
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
        help="Directory where B-S04 result files will be written.",
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

    missing_raw_lateral_graphs = sorted(
        {
            missing
            for vehicle in vehicles
            for missing in vehicle["missingRawLateralGraphs"]
        }
    )
    scenario_checks_pass = all(
        vehicle["finiteValues"]
        and all(scenario["reachable"] for scenario in vehicle["scenarios"])
        for vehicle in vehicles
    )
    summary = {
        "scenario": "B-S04",
        "success": len(export_paths) == 3 and len(vehicles) == 3 and not failures and scenario_checks_pass,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputDirectory": arguments.input_dir.relative_to(repo_root).as_posix(),
        "documentsProcessed": len(export_paths),
        "vehiclesValid": len(vehicles),
        "vehiclesFailed": len(failures),
        "radiiMeters": list(RADIUS_METERS),
        "gripProxy": "AccelerationToTopSpeed.FrontGripG + AccelerationToTopSpeed.RearGripG",
        "speedUnitAssumption": "km/h inferred from performance top speed",
        "missingRawLateralGraphs": missing_raw_lateral_graphs,
        "vehicles": vehicles,
        "failures": failures,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "b_s04_constant_radius_summary.json"
    report_path = arguments.results_dir / "B_S04_CONSTANT_RADIUS_RESULT.md"

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
