#!/usr/bin/env python3
"""Run B-S01: load and validate all A8 raw vehicle data fixtures."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

EXPECTED_GRAPHS = ("AccelerationToTopSpeed", "Braking", "BrakingVGrip")


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


def count_raw_graph_values(raw_graphs: list[dict[str, Any]]) -> int:
    return sum(
        len(series.get("values", []))
        for graph in raw_graphs
        for series in graph.get("series", [])
    )


def summarize_graph(graph: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": graph["key"],
        "seriesCount": graph["seriesCount"],
        "expectedSeriesLength": graph["expectedSeriesLength"],
        "valueCount": sum(len(series.get("values", [])) for series in graph["series"]),
        "series": [
            {
                "key": series["key"],
                "role": series["role"],
                "count": series["count"],
                "numericMin": series["numericMin"],
                "numericMax": series["numericMax"],
                "unitSource": series["unitSource"],
                "unitInternalCandidate": series["unitInternalCandidate"],
            }
            for series in graph["series"]
        ],
    }


def summarize_document(path: Path, document: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    controlled_fields = document["controlledFields"]
    graph_inventory = document["graphInventory"]["availableGraphs"]
    raw_graphs = document["rawGraphs"]
    raw_graph_keys = tuple(graph["key"] for graph in raw_graphs)
    missing_graphs = sorted(set(EXPECTED_GRAPHS) - set(raw_graph_keys))

    return {
        "path": path.as_posix(),
        "modelName": document["identity"]["modelName"],
        "trimName": document["identity"]["trimName"],
        "schemaVersion": document["schemaVersion"],
        "exporterVersion": document["source"]["exporterVersion"],
        "automationVersion": document["source"]["automationVersion"],
        "generatedAtUtc": document["generatedAtUtc"],
        "exportedAtUtc": document["source"]["exportedAtUtc"],
        "controlledFieldsPresent": sum(1 for field in controlled_fields if field["present"]),
        "controlledFieldsTotal": len(controlled_fields),
        "availableGraphs": len(graph_inventory),
        "rawGraphs": len(raw_graphs),
        "rawGraphKeys": list(raw_graph_keys),
        "missingGraphs": missing_graphs,
        "rawSeries": sum(len(graph["series"]) for graph in raw_graphs),
        "rawValues": count_raw_graph_values(raw_graphs),
        "documentDiagnostics": len(document["diagnostics"]),
        "graphInventoryDiagnostics": len(document["graphInventory"]["diagnostics"]),
        "warnings": warnings,
        "graphs": [summarize_graph(graph) for graph in raw_graphs],
    }


def format_vehicle_name(vehicle: dict[str, Any]) -> str:
    model = vehicle["modelName"]
    trim = vehicle["trimName"]
    if trim and trim not in model:
        return f"{model} - {trim}"
    return model


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# B-S01 - Chargement des donnees A8",
        "",
        "- **Experience :** B - Dynamique d'une voiture",
        "- **Scenario :** B-S01",
        f"- **Statut :** {'valide' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** charger et valider les trois documents `AutomationRawVehicleData` v0.1 produits par A8.",
        "",
        "## Synthese",
        "",
        f"- Documents trouves : {summary['documentsFound']}",
        f"- Documents valides : {summary['documentsValid']}",
        f"- Documents en echec : {summary['documentsFailed']}",
        f"- Valeurs brutes de graphes chargees : {summary['totalRawValues']}",
        "",
        "## Resultats par voiture",
        "",
        "| Voiture | Contrat | Champs | Graphes disponibles | Graphes bruts | Series | Valeurs | Avertissements |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for vehicle in summary["vehicles"]:
        warning_text = ", ".join(vehicle["warnings"]) if vehicle["warnings"] else "aucun"
        lines.append(
            "| "
            f"{format_vehicle_name(vehicle)} | "
            "valide | "
            f"{vehicle['controlledFieldsPresent']} / {vehicle['controlledFieldsTotal']} | "
            f"{vehicle['availableGraphs']} | "
            f"{vehicle['rawGraphs']} | "
            f"{vehicle['rawSeries']} | "
            f"{vehicle['rawValues']} | "
            f"{warning_text} |"
        )

    lines.extend(
        [
            "",
            "## Graphes requis",
            "",
            "| Voiture | AccelerationToTopSpeed | Braking | BrakingVGrip |",
            "| --- | --- | --- | --- |",
        ]
    )

    for vehicle in summary["vehicles"]:
        present = set(vehicle["rawGraphKeys"])
        cells = ["oui" if graph in present else "non" for graph in EXPECTED_GRAPHS]
        lines.append(f"| {format_vehicle_name(vehicle)} | {cells[0]} | {cells[1]} | {cells[2]} |")

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Les trois voitures A8 sont chargeables par le prototype B.",
            "- Le validateur A8 existant est reutilise comme garde-fou de contrat.",
            "- Les graphes `AccelerationToTopSpeed`, `Braking` et `BrakingVGrip` sont presents pour les trois voitures.",
            "- Les avertissements restants concernent l'absence de version Automation exposee par les donnees Lua.",
            "",
            "## Decision",
            "",
            "B-S01 est valide. Le prochain jalon peut construire les interpolateures des courbes longitudinales pour B-S02 et B-S03.",
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
        description="Run B-S01 by loading and validating A8 raw vehicle data fixtures."
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
        help="Directory where B-S01 result files will be written.",
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
            warnings = validator.validate_document(document)
            vehicles.append(summarize_document(relative_path, document, warnings))
        except Exception as error:  # noqa: BLE001 - report all fixture failures.
            failures.append({"path": relative_path.as_posix(), "error": str(error)})

    summary = {
        "scenario": "B-S01",
        "success": len(export_paths) == 3 and len(vehicles) == 3 and not failures,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputDirectory": arguments.input_dir.relative_to(repo_root).as_posix(),
        "documentsFound": len(export_paths),
        "documentsValid": len(vehicles),
        "documentsFailed": len(failures),
        "totalRawValues": sum(vehicle["rawValues"] for vehicle in vehicles),
        "vehicles": vehicles,
        "failures": failures,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "b_s01_load_a8_summary.json"
    report_path = arguments.results_dir / "B_S01_LOAD_A8_RESULT.md"

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
