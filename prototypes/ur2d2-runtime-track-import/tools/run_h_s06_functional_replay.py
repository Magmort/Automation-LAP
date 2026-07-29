#!/usr/bin/env python3
"""Run H-S06: simulate the imported UR2D2 package with the C autonomous lap controller."""

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
REPO_ROOT = ROOT.parents[1]
RESULTS_DIR = ROOT / "results"
PACKAGE_PATH = RESULTS_DIR / "h_s05_import_package.json"
SUMMARY_PATH = RESULTS_DIR / "h_s06_functional_replay_summary.json"
REPORT_PATH = RESULTS_DIR / "H_S06_FUNCTIONAL_REPLAY_RESULT.md"
DEFAULT_VEHICLE_PATH = (
    REPO_ROOT
    / "outputs"
    / "a9-raw-vehicle-data"
    / "QFC55 - Magmort Carcharhini RCZ"
    / "automation-lap-raw-vehicle-data.json"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def relative_or_absolute(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def vehicle_public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": profile["name"],
        "exporterVersion": profile["exporterVersion"],
        "topSpeedKmh": profile["topSpeedKmh"],
        "lateralGripProxyG": profile["lateralGripProxyG"],
        "lateralLimitG": profile["lateralLimitG"],
    }


def build_summary(package: dict[str, Any], vehicle: dict[str, Any], package_path: Path, vehicle_path: Path) -> dict[str, Any]:
    c_s01 = load_module(
        REPO_ROOT / "prototypes" / "autonomous-lap" / "tools" / "run_c_s01_track_contract.py",
        "run_c_s01_track_contract",
    )
    c_s02 = load_module(
        REPO_ROOT / "prototypes" / "autonomous-lap" / "tools" / "run_c_s02_path_following.py",
        "run_c_s02_path_following",
    )
    c_s03 = load_module(
        REPO_ROOT / "prototypes" / "autonomous-lap" / "tools" / "run_c_s03_curvature_speed.py",
        "run_c_s03_curvature_speed",
    )
    validator = load_module(
        REPO_ROOT / "prototypes" / "automation-exporter" / "tools" / "validate_raw_vehicle_data.py",
        "validate_raw_vehicle_data",
    )

    track = package["trackDefinition"]
    track_errors = c_s01.validate_track(track)
    if track_errors:
        raise RuntimeError("Invalid packaged TrackDefinition: " + "; ".join(track_errors))
    validator.validate_document(vehicle)

    profile = c_s03.qfc55_profile(vehicle)
    runs = [
        c_s03.simulate(track, profile, c_s02, dt, sample_interval_s=0.25)
        for dt in c_s03.TIME_STEPS
    ]
    reference_run = next(run for run in runs if abs(run["dt"] - c_s03.REFERENCE_DT) < 1e-12)
    preprocessed = c_s01.preprocess_track(track)

    checks = {
        "packageKindValid": package.get("kind") == "UR2D2ImportedTrackPackage",
        "packageReadyH05": package["validation"]["trackDefinitionC-S01"]["success"]
        and package["validation"]["overlayH-S04"]["success"],
        "trackDefinitionValid": not track_errors,
        "vehicleDataValid": True,
        "allTimeStepsStable": all(run["success"] for run in runs),
        "referenceRunStable": reference_run["success"],
        "referenceRunCompletedThreeLaps": reference_run["completedLaps"] >= c_s03.TARGET_LAPS,
        "referenceRunNoOffTrack": reference_run["offTrackCount"] == 0,
        "runtimeBackgroundAvailable": package["runtimeRendering"]["imageAssets"]["track_preview.png"] is not None,
        "replaySamplesPresent": len(reference_run["samples"]) > 20,
        "extrasAvailable": (
            len(package["simulationExtras"]["pitlaneLanes"]) >= 2
            and len(package["simulationExtras"]["walls"]) >= 1
        ),
    }
    status = "functional-replay-ready-for-validation" if all(checks.values()) else "functional-replay-with-reserves"
    return {
        "scenario": "H-S06",
        "status": status,
        "success": status == "functional-replay-ready-for-validation",
        "generatedAtUtc": utc_now(),
        "packagePath": relative_or_absolute(package_path),
        "vehiclePath": relative_or_absolute(vehicle_path),
        "packageContentSha256": package["contentSha256"],
        "track": {
            "trackId": package["trackId"],
            "name": package["name"],
            "centerlinePoints": len(track["centerline"]),
            "totalLengthM": preprocessed["totalLengthM"],
            "minTotalWidthM": preprocessed["minTotalWidthM"],
            "maxAbsCurvature": preprocessed["maxAbsCurvature"],
        },
        "vehicleProfile": vehicle_public_profile(profile),
        "modelAssumptions": {
            "controller": "C-S03 pure pursuit with curvature-based speed target",
            "positionSource": "H-S05 TrackDefinition centerline",
            "renderingSource": "H-S05 runtimeRendering track_preview.png mapping",
            "pitlaneAndWalls": "rendered as simulationExtras; not enforced as colliders in H-S06",
        },
        "checks": checks,
        "runs": runs,
        "referenceRun": reference_run,
        "visualizationPath": str((RESULTS_DIR / "H_S06_FUNCTIONAL_REPLAY_VISUALIZATION.svg").resolve()),
        "nextStep": "Apres validation visuelle, H peut etre cloturee ou prolongee avec des scenarios tenant compte des murs et de la pitlane.",
    }


def render_markdown(summary: dict[str, Any]) -> str:
    reference = summary["referenceRun"]
    profile = summary["vehicleProfile"]
    lines = [
        "# H-S06 - Validation fonctionnelle sur fond runtime",
        "",
        "- **Experience :** H - Import depuis les vrais fichiers de tracks UR2D2",
        "- **Scenario :** H-S06",
        f"- **Statut :** {summary['status']}",
        f"- **Date :** {summary['generatedAtUtc']}",
        f"- **Package :** `{summary['packagePath']}`",
        f"- **Vehicule :** {profile['name']}",
        "",
        "## Decision du jalon",
        "",
    ]
    if summary["success"]:
        lines.append(
            "H-S06 confirme que le paquet H-S05 peut alimenter le controleur autonome C-S03 et produire un replay coherent sur le fond runtime UR2D2."
        )
    else:
        lines.append("H-S06 produit un replay, mais certains controles restent a examiner.")

    lines.extend(
        [
            "",
            "## Controles",
            "",
            "| Controle | Resultat |",
            "| --- | --- |",
        ]
    )
    for key, value in summary["checks"].items():
        lines.append(f"| `{key}` | {fmt_bool(value)} |")

    lines.extend(
        [
            "",
            "## Reference 1/120 s",
            "",
            f"- Tours : {reference['completedLaps']}",
            f"- Duree totale : {fmt_number(reference['durationS'])} s",
            f"- Temps au tour : {', '.join(fmt_number(value) + ' s' for value in reference['lapTimesS'])}",
            f"- Vitesse moyenne : {fmt_number(reference['meanSpeedKmh'])} km/h",
            f"- Vitesse max : {fmt_number(reference['maxSpeedKmh'])} km/h",
            f"- Erreur laterale moyenne : {fmt_number(reference['meanAbsLateralErrorM'], 3)} m",
            f"- Erreur laterale max : {fmt_number(reference['maxAbsLateralErrorM'], 3)} m",
            f"- Sorties de piste : {reference['offTrackCount']}",
            "",
            "## Resultats par pas de temps",
            "",
            "| dt | Tours | Duree | Vitesse moy. | Erreur lat. moy. | Erreur lat. max | Sorties | Stable |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for run in summary["runs"]:
        lines.append(
            "| "
            f"{fmt_number(run['dt'], 5)} | "
            f"{run['completedLaps']} | "
            f"{fmt_number(run['durationS'])} | "
            f"{fmt_number(run['meanSpeedKmh'])} | "
            f"{fmt_number(run['meanAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxAbsLateralErrorM'], 3)} | "
            f"{run['offTrackCount']} | "
            f"{fmt_bool(run['success'])} |"
        )

    lines.extend(
        [
            "",
            "## Reserves",
            "",
            "- Le replay utilise le modele C-S03 actuel ; il valide le chemin d'import, pas encore le modele physique final.",
            "- Les murs et la pitlane sont disponibles et rendus, mais ne sont pas encore des contraintes de conduite.",
            "- Le rendu s'appuie sur les PNG locaux UR2D2 par reference de chemin, sans redistribution des assets.",
            "",
            "## Prochaine etape",
            "",
            summary["nextStep"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=PACKAGE_PATH)
    parser.add_argument("--vehicle", type=Path, default=DEFAULT_VEHICLE_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)
    package = load_json(args.package)
    vehicle = load_json(args.vehicle)
    summary = build_summary(package, vehicle, args.package, args.vehicle)
    write_json(args.results_dir / SUMMARY_PATH.name, summary)
    (args.results_dir / REPORT_PATH.name).write_text(render_markdown(summary), encoding="utf-8", newline="\n")
    print(f"H-S06 status: {summary['status']}")
    print(f"Wrote: {args.results_dir / SUMMARY_PATH.name}")
    print(f"Wrote: {args.results_dir / REPORT_PATH.name}")
    return 0 if summary["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
