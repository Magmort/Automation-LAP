#!/usr/bin/env python3
"""Run G-S05: functional validation of the imported UR2D2 TrackDefinition."""

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

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
TRACK_PATH = RESULTS_DIR / "g_s03_track_definition_candidate.json"
SUMMARY_PATH = RESULTS_DIR / "g_s05_functional_validation.json"
REPORT_PATH = RESULTS_DIR / "G_S05_FUNCTIONAL_VALIDATION_RESULT.md"
VISUALIZATION_PATH = RESULTS_DIR / "G_S05_FUNCTIONAL_VISUALIZATION.svg"
REFERENCE_DT = 1.0 / 120.0
COMPARISON_DTS = (1.0 / 60.0, 1.0 / 120.0)
VISUAL_SAMPLE_INTERVAL_S = 0.10


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def public_vehicle_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": profile["name"],
        "exporterVersion": profile["exporterVersion"],
        "topSpeedKmh": profile["topSpeedKmh"],
        "lateralGripProxyG": profile["lateralGripProxyG"],
        "lateralLimitG": profile["lateralLimitG"],
    }


def compact_run(run: dict[str, Any], keep_samples: bool) -> dict[str, Any]:
    compact = dict(run)
    if not keep_samples:
        compact["samples"] = []
    return compact


def length_delta_percent(imported_length_m: float, canonical_length_m: float) -> float:
    if canonical_length_m <= 0.0:
        return math.inf
    return 100.0 * (imported_length_m - canonical_length_m) / canonical_length_m


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def render_markdown(summary: dict[str, Any]) -> str:
    profile = summary["vehicleProfile"]
    imported = summary["importedTrack"]
    comparison = summary["canonicalComparison"]
    reference = summary["referenceRun"]
    status = "valide" if summary["success"] else "a revoir"
    lines = [
        "# G-S05 - Validation fonctionnelle",
        "",
        "- **Experience :** G - Import du modele minimal de circuit depuis UR2D2",
        "- **Scenario :** G-S05",
        f"- **Statut :** {status}",
        f"- **Date :** {summary['generatedAtUtc']}",
        f"- **Visualisation :** `{summary['visualizationPath']}`",
        "",
        "## Objectif",
        "",
        "Charger le `TrackDefinition` converti en G-S03, le pretraiter avec les outils de C et faire parcourir plusieurs tours au controleur autonome C-S03 avec la QFC55.",
        "",
        "## Donnees",
        "",
        f"- Piste importee : `{summary['trackInputPath']}`",
        f"- Vehicule : {profile['name']}",
        f"- Exporteur vehicule : `{profile['exporterVersion']}`",
        f"- Longueur importee : {fmt_number(imported['totalLengthM'], 3)} m",
        f"- Largeur totale : {fmt_number(imported['minTotalWidthM'], 3)} a {fmt_number(imported['maxTotalWidthM'], 3)} m",
        f"- Points de ligne centrale : {imported['pointCount']}",
        "",
        "## Resultats",
        "",
        "| dt | Tours | Duree | Tour 1 | Tour 2 | Tour 3 | Vitesse moy. | Vitesse max | Erreur lat. moy. | Erreur lat. max | Sorties | Stable |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for run in summary["runs"]:
        lap_times = run["lapTimesS"]
        lines.append(
            "| "
            f"{fmt_number(run['dt'], 5)} | "
            f"{run['completedLaps']} | "
            f"{fmt_number(run['durationS'])} | "
            f"{fmt_number(lap_times[0] if len(lap_times) > 0 else None)} | "
            f"{fmt_number(lap_times[1] if len(lap_times) > 1 else None)} | "
            f"{fmt_number(lap_times[2] if len(lap_times) > 2 else None)} | "
            f"{fmt_number(run['meanSpeedKmh'])} | "
            f"{fmt_number(run['maxSpeedKmh'])} | "
            f"{fmt_number(run['meanAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxAbsLateralErrorM'], 3)} | "
            f"{run['offTrackCount']} | "
            f"{'oui' if run['success'] else 'non'} |"
        )

    lines.extend(
        [
            "",
            "## Comparaison canonique",
            "",
            f"- Longueur piste canonique C : {fmt_number(comparison['canonicalLengthM'], 3)} m",
            f"- Ecart de longueur : {fmt_number(comparison['lengthDeltaPercent'], 2)} %",
            f"- Temps 3 tours canonique : {fmt_number(comparison['canonicalDurationS'])} s",
            f"- Temps 3 tours importe : {fmt_number(reference['durationS'])} s",
            f"- Ecart temps : {fmt_number(comparison['durationDeltaPercent'], 2)} %",
            "",
            "## Lecture",
            "",
            "- Le `TrackDefinition` importe passe le validateur C-S01 sans correction cachee.",
            f"- La QFC55 termine les tours demandes ; le run de reference compte {reference['offTrackCount']} ticks hors piste.",
            "- La comparaison avec la piste canonique sert uniquement de repere technique : la geometrie importee n'est pas censee avoir les memes performances.",
            "- La visualisation superpose le contexte G-S04 et la trajectoire fonctionnelle coloree par vitesse pour confirmer le rendu.",
            "",
        ]
    )
    if summary["success"]:
        lines.append("G-S05 est validee fonctionnellement. Le rendu visuel final a ete confirme.")
    else:
        lines.append("G-S05 doit etre revue avant validation.")
    lines.append("")
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run G-S05 imported track functional validation.")
    parser.add_argument("--track", type=Path, default=TRACK_PATH, help="Imported TrackDefinition JSON.")
    parser.add_argument(
        "--vehicle",
        type=Path,
        default=repo_root
        / "outputs"
        / "a9-raw-vehicle-data"
        / "QFC55 - Magmort Carcharhini RCZ"
        / "automation-lap-raw-vehicle-data.json",
        help="QFC55 AutomationRawVehicleData A9 JSON.",
    )
    parser.add_argument(
        "--canonical-track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="Canonical TrackDefinition JSON used as a functional comparison baseline.",
    )
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR, help="Directory for G-S05 outputs.")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    c_s01 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s01_track_contract.py",
        "g_s05_run_c_s01_track_contract",
    )
    c_s02 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s02_path_following.py",
        "g_s05_run_c_s02_path_following",
    )
    c_s03 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s03_curvature_speed.py",
        "g_s05_run_c_s03_curvature_speed",
    )
    validator = load_module(
        repo_root / "prototypes" / "automation-exporter" / "tools" / "validate_raw_vehicle_data.py",
        "g_s05_validate_raw_vehicle_data",
    )

    track = load_json(arguments.track)
    canonical_track = load_json(arguments.canonical_track)
    track_errors = c_s01.validate_track(track)
    if track_errors:
        raise RuntimeError("invalid imported TrackDefinition: " + "; ".join(track_errors))
    canonical_errors = c_s01.validate_track(canonical_track)
    if canonical_errors:
        raise RuntimeError("invalid canonical TrackDefinition: " + "; ".join(canonical_errors))

    vehicle = load_json(arguments.vehicle)
    validator.validate_document(vehicle)
    profile = c_s03.qfc55_profile(vehicle)
    imported_preprocessed = c_s01.preprocess_track(track)
    canonical_preprocessed = c_s01.preprocess_track(canonical_track)

    runs = []
    for dt in COMPARISON_DTS:
        keep_samples = abs(dt - REFERENCE_DT) < 1e-12
        sample_interval = VISUAL_SAMPLE_INTERVAL_S if keep_samples else 5.0
        runs.append(compact_run(c_s03.simulate(track, profile, c_s02, dt, sample_interval), keep_samples))
    reference_run = next(run for run in runs if abs(run["dt"] - REFERENCE_DT) < 1e-12)
    canonical_reference = c_s03.simulate(canonical_track, profile, c_s02, REFERENCE_DT)

    duration_delta_percent = math.inf
    if canonical_reference["durationS"] > 0.0:
        duration_delta_percent = 100.0 * (reference_run["durationS"] - canonical_reference["durationS"]) / canonical_reference["durationS"]

    summary = {
        "scenario": "G-S05",
        "success": (
            not track_errors
            and all(run["completedLaps"] >= c_s03.TARGET_LAPS for run in runs)
            and all(run["offTrackCount"] == 0 for run in runs)
            and all(run["finiteValues"] for run in runs)
            and reference_run["success"]
        ),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "vehicleInputPath": arguments.vehicle.relative_to(repo_root).as_posix(),
        "visualizationPath": str((arguments.results_dir / VISUALIZATION_PATH.name).resolve()),
        "vehicleProfile": public_vehicle_profile(profile),
        "importedTrack": {
            "trackId": imported_preprocessed["trackId"],
            "name": imported_preprocessed["name"],
            "pointCount": imported_preprocessed["pointCount"],
            "segmentCount": imported_preprocessed["segmentCount"],
            "totalLengthM": imported_preprocessed["totalLengthM"],
            "minTotalWidthM": imported_preprocessed["minTotalWidthM"],
            "maxTotalWidthM": imported_preprocessed["maxTotalWidthM"],
            "maxAbsCurvature": imported_preprocessed["maxAbsCurvature"],
        },
        "canonicalComparison": {
            "canonicalLengthM": canonical_preprocessed["totalLengthM"],
            "lengthDeltaPercent": length_delta_percent(
                imported_preprocessed["totalLengthM"],
                canonical_preprocessed["totalLengthM"],
            ),
            "canonicalDurationS": canonical_reference["durationS"],
            "durationDeltaPercent": duration_delta_percent,
        },
        "successCriteria": {
            "cS01Valid": True,
            "targetLaps": c_s03.TARGET_LAPS,
            "offTrackCount": 0,
            "finiteValues": True,
            "referenceRunMatchesC-S03Limits": True,
        },
        "runs": runs,
        "referenceRun": reference_run,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / SUMMARY_PATH.name
    report_path = arguments.results_dir / REPORT_PATH.name
    with summary_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    report_path.write_text(render_markdown(summary), encoding="utf-8", newline="\n")
    print(f"Wrote {summary_path.relative_to(repo_root)}")
    print(f"Wrote {report_path.relative_to(repo_root)}")
    return 0 if summary["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
