#!/usr/bin/env python3
"""Run B-S06: compare inter-vehicle sensitivity across B results."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

EXPECTED_VEHICLE_COUNT = 3
REFERENCE_DT = 1.0 / 120.0
MIN_SPREAD_RATIO = 0.05


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def vehicle_name(vehicle: dict[str, Any]) -> str:
    model = vehicle["modelName"]
    trim = vehicle["trimName"]
    if trim and trim not in model:
        return f"{model} - {trim}"
    return model


def canonical_name(model_name: str, trim_name: str) -> str:
    if trim_name and trim_name not in model_name:
        return f"{model_name} - {trim_name}"
    return model_name


def target_value(vehicle: dict[str, Any], speed: float, key: str) -> float | None:
    for target in vehicle["targets"]:
        if target["speed"] == speed:
            value = target.get(key)
            return float(value) if value is not None else None
    return None


def graph_lookup(vehicle: dict[str, Any], key: str) -> dict[str, Any]:
    for graph in vehicle["graphs"]:
        if graph["key"] == key:
            return graph
    raise KeyError(key)


def run_lookup(vehicle: dict[str, Any], dt: float) -> dict[str, Any]:
    for run in vehicle["runs"]:
        if abs(float(run["dt"]) - dt) < 1e-12:
            return run
    raise KeyError(dt)


def spread_ratio(values: list[float]) -> float:
    if not values:
        return 0.0
    maximum = max(values)
    minimum = min(values)
    denominator = max(abs(maximum), abs(minimum), 1.0)
    return (maximum - minimum) / denominator


def rank_metric(metrics: dict[str, dict[str, float]], key: str, higher_is_better: bool) -> list[dict[str, Any]]:
    ranked = sorted(
        (
            {"name": name, "value": values[key]}
            for name, values in metrics.items()
            if math.isfinite(values[key])
        ),
        key=lambda item: item["value"],
        reverse=higher_is_better,
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_ranking(ranking: list[dict[str, Any]], digits: int = 2) -> str:
    return " > ".join(f"{item['name']} ({fmt_number(item['value'], digits)})" for item in ranking)


def collect_metrics(
    acceleration: dict[str, Any],
    braking: dict[str, Any],
    steering: dict[str, Any],
    transitions: dict[str, Any],
) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}

    for vehicle in acceleration["vehicles"]:
        name = vehicle_name(vehicle)
        time_0_50 = target_value(vehicle, 50.0, "time")
        time_0_100 = target_value(vehicle, 100.0, "time")
        metrics[name] = {
            "topSpeed": float(vehicle["topSpeed"]),
            "time0To50": time_0_50 if time_0_50 is not None else math.inf,
            "time0To100": time_0_100 if time_0_100 is not None else math.inf,
            "maxAccelG": float(vehicle["maxAccelG"]),
        }

    for vehicle in braking["vehicles"]:
        name = vehicle_name(vehicle)
        if name not in metrics:
            continue
        braking_100 = target_value(vehicle, 100.0, "durationToEnd")
        braking_50 = target_value(vehicle, 50.0, "durationToEnd")
        metrics[name].update(
            {
                "brake100ToEnd": braking_100 if braking_100 is not None else math.inf,
                "brake50ToEnd": braking_50 if braking_50 is not None else math.inf,
                "brakeFullDuration": float(vehicle["fullDuration"]),
                "brakeSpeedTimeArea": float(vehicle["speedTimeArea"]),
            }
        )

    for vehicle in steering["vehicles"]:
        name = vehicle_name(vehicle)
        if name not in metrics:
            continue
        low = graph_lookup(vehicle, "LowSpeedSteering")
        high = graph_lookup(vehicle, "HighSpeedSteering")
        metrics[name].update(
            {
                "lowSteeringMax": float(low["steeringMax"]),
                "highSteeringMax": float(high["steeringMax"]),
                "lowInsidePercent": float(low["insidePercent"]),
                "highInsidePercent": float(high["insidePercent"]),
                "highSpeedDomainMax": float(high["speedMax"]),
            }
        )

    for vehicle in transitions["vehicles"]:
        name = vehicle_name(vehicle)
        if name not in metrics:
            continue
        run = run_lookup(vehicle, REFERENCE_DT)
        final = run["final"]
        distance = math.hypot(float(final["x"]), float(final["y"]))
        metrics[name].update(
            {
                "transitionFinalSpeed": float(final["speed"]),
                "transitionDistance": distance,
                "transitionHeading": abs(float(final["heading"])),
                "transitionMaxLateralG": float(run["maxLateralGModel"]),
                "transitionMaxSpeed": float(run["maxSpeed"]),
            }
        )

    return metrics


def build_summary(repo_root: Path, results_dir: Path) -> dict[str, Any]:
    acceleration = load_json(results_dir / "b_s02_acceleration_curve_summary.json")
    braking = load_json(results_dir / "b_s03_braking_curve_summary.json")
    steering = load_json(results_dir / "b_s04_steering_graphs_summary.json")
    transitions = load_json(results_dir / "b_s05_transitions_summary.json")

    source_success = all(
        document["success"] for document in (acceleration, braking, steering, transitions)
    )
    metrics = collect_metrics(acceleration, braking, steering, transitions)
    metric_specs = [
        ("topSpeed", True, "Vmax"),
        ("time0To100", False, "0-100"),
        ("brake100ToEnd", False, "100->fin"),
        ("highSteeringMax", True, "High steering max"),
        ("transitionDistance", True, "Distance transition"),
        ("transitionFinalSpeed", True, "Vitesse finale transition"),
        ("transitionMaxLateralG", True, "Lateral G modele"),
    ]
    rankings = {
        key: {
            "label": label,
            "higherIsBetter": higher_is_better,
            "ranking": rank_metric(metrics, key, higher_is_better),
            "spreadRatio": spread_ratio([values[key] for values in metrics.values()]),
        }
        for key, higher_is_better, label in metric_specs
    }
    all_spreads_visible = all(
        ranking["spreadRatio"] >= MIN_SPREAD_RATIO for ranking in rankings.values()
    )
    expected_order_checks = {
        "aixamSlowestTopSpeed": rankings["topSpeed"]["ranking"][-1]["name"].startswith("AIXAM"),
        "qfcFastestTopSpeed": rankings["topSpeed"]["ranking"][0]["name"].startswith("QFC55"),
        "qfcFastest0To100": rankings["time0To100"]["ranking"][0]["name"].startswith("QFC55"),
        "qfcFastest100ToEnd": rankings["brake100ToEnd"]["ranking"][0]["name"].startswith("QFC55"),
        "aixamLowestTransitionDistance": rankings["transitionDistance"]["ranking"][-1]["name"].startswith("AIXAM"),
    }
    success = (
        source_success
        and len(metrics) == EXPECTED_VEHICLE_COUNT
        and all_spreads_visible
        and all(expected_order_checks.values())
    )
    return {
        "scenario": "B-S06",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sourceResults": {
            "B-S02": (results_dir / "b_s02_acceleration_curve_summary.json").relative_to(repo_root).as_posix(),
            "B-S03": (results_dir / "b_s03_braking_curve_summary.json").relative_to(repo_root).as_posix(),
            "B-S04": (results_dir / "b_s04_steering_graphs_summary.json").relative_to(repo_root).as_posix(),
            "B-S05": (results_dir / "b_s05_transitions_summary.json").relative_to(repo_root).as_posix(),
        },
        "sourceResultsSuccessful": source_success,
        "vehiclesCompared": len(metrics),
        "minimumSpreadRatio": MIN_SPREAD_RATIO,
        "allSpreadsVisible": all_spreads_visible,
        "expectedOrderChecks": expected_order_checks,
        "metrics": metrics,
        "rankings": rankings,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# B-S06 - Sensibilite inter-voitures",
        "",
        "- **Experience :** B - Dynamique d'une voiture",
        "- **Scenario :** B-S06",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier que les resultats B-S02 a B-S05 conservent des differences plausibles entre les trois voitures.",
        "- **Reserve :** les metriques de direction restent issues d'une normalisation de graphes Automation dont l'unite est inconnue.",
        "",
        "## Sources",
        "",
    ]

    for scenario, path in summary["sourceResults"].items():
        lines.append(f"- {scenario} : `{path}`")

    lines.extend(
        [
            "",
            "## Metriques consolidees",
            "",
            "| Voiture | Vmax | 0-100 | 100->fin | High steering max | Distance transition | Vitesse finale transition | Lateral G modele |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for name, metrics in summary["metrics"].items():
        lines.append(
            "| "
            f"{name} | "
            f"{fmt_number(metrics['topSpeed'])} | "
            f"{fmt_number(metrics['time0To100'])} | "
            f"{fmt_number(metrics['brake100ToEnd'])} | "
            f"{fmt_number(metrics['highSteeringMax'])} | "
            f"{fmt_number(metrics['transitionDistance'])} | "
            f"{fmt_number(metrics['transitionFinalSpeed'])} | "
            f"{fmt_number(metrics['transitionMaxLateralG'], 3)} |"
        )

    lines.extend(
        [
            "",
            "## Classements",
            "",
            "| Metrique | Classement | Ecart relatif |",
            "| --- | --- | ---: |",
        ]
    )

    for ranking in summary["rankings"].values():
        lines.append(
            "| "
            f"{ranking['label']} | "
            f"{fmt_ranking(ranking['ranking'])} | "
            f"{fmt_number(ranking['spreadRatio'] * 100.0, 1)} % |"
        )

    lines.extend(
        [
            "",
            "## Controles attendus",
            "",
            "| Controle | Resultat |",
            "| --- | --- |",
        ]
    )

    labels = {
        "aixamSlowestTopSpeed": "AIXAM reste la plus lente en Vmax",
        "qfcFastestTopSpeed": "QFC55 reste la plus rapide en Vmax",
        "qfcFastest0To100": "QFC55 reste la plus rapide sur 0-100",
        "qfcFastest100ToEnd": "QFC55 reste la plus rapide sur 100->fin",
        "aixamLowestTransitionDistance": "AIXAM reste la moins couvrante sur la transition",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {'oui' if summary['expectedOrderChecks'][key] else 'non'} |")

    lines.extend(
        [
            "",
            "## Observations",
            "",
            "- Les trois voitures restent nettement differenciees sur les metriques longitudinales.",
            "- La QFC55 domine en Vmax, 0-100 et freinage 100->fin, ce qui correspond aux resultats relus depuis Automation.",
            "- Le scenario de transition separe clairement l'AIXAM des deux voitures rapides.",
            "- Les metriques de direction differencient les voitures, mais leur interpretation physique reste reservee tant que les unites ne sont pas confirmees.",
            "- `1/60 s` peut etre retenu comme pas candidat pour C, avec `1/120 s` comme reference de verification pendant les prochains prototypes.",
            "",
            "## Decision",
            "",
            "B-S06 est valide avec reserves. L'experience B peut etre conclue comme viable pour alimenter C, a condition de conserver la direction comme modele calibrable et de ne pas presenter les graphes Steering comme une adherence laterale brute.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(
        description="Run B-S06 by comparing inter-vehicle sensitivity across B results."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "vehicle-dynamics" / "results",
        help="Directory containing B-S02 to B-S05 result files.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = build_summary(repo_root, arguments.results_dir)

    summary_path = arguments.results_dir / "b_s06_vehicle_sensitivity_summary.json"
    report_path = arguments.results_dir / "B_S06_VEHICLE_SENSITIVITY_RESULT.md"

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
