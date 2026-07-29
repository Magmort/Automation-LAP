#!/usr/bin/env python3
"""Run C-S06: consolidate the minimal TrackDefinition contract for experiment G."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

EXPECTED_SCENARIOS = ("C-S01", "C-S02", "C-S03", "C-S04", "C-S05")

SOURCE_FIELDS = (
    ("kind", "string", "must be TrackDefinition", "contract identity"),
    ("schemaVersion", "semver string", "0.1.0 candidate", "versioned importer target"),
    ("trackId", "string", "stable unique id", "persistence and replay references"),
    ("name", "string", "human readable", "debug and authoring"),
    ("coordinateSystem.units.distance", "enum", "m", "SI distance contract"),
    ("coordinateSystem.units.angle", "enum", "rad", "SI angle contract"),
    ("coordinateSystem.units.time", "enum", "s", "SI time contract"),
    ("coordinateSystem.axis.x", "enum", "right", "2D coordinate convention"),
    ("coordinateSystem.axis.y", "enum", "forward", "2D coordinate convention"),
    ("coordinateSystem.orientation", "enum", "clockwise or counter-clockwise", "authoring convention"),
    ("closedLoop", "bool", "true for current scope", "lap counting and implicit closure"),
    ("direction", "enum", "clockwise or counter-clockwise", "progression direction"),
    ("surface.type", "string", "asphalt in fixture", "future surface model"),
    ("surface.grip", "number", "finite positive scalar", "future surface grip multiplier"),
    ("centerline[].id", "string", "unique and stable", "references from start/checkpoints"),
    ("centerline[].x", "number", "finite metres", "track geometry"),
    ("centerline[].y", "number", "finite metres", "track geometry"),
    ("centerline[].leftWidth", "number", "finite metres", "left track limit"),
    ("centerline[].rightWidth", "number", "finite metres", "right track limit"),
    ("startLine.centerlinePointId", "string", "references centerline[].id", "lap origin"),
    ("startLine.width", "number", "finite metres", "start line drawing/import hint"),
    ("checkpoints[].id", "string", "unique and stable", "checkpoint identity"),
    ("checkpoints[].centerlinePointId", "string", "references centerline[].id", "progress validation"),
)

DERIVED_FIELDS = (
    "segment list and segment length",
    "cumulative distance / curvilinear coordinate",
    "total track length",
    "sampled x/y positions along the centerline",
    "tangent and normal vectors",
    "local left/right width interpolation",
    "curvature and lookahead curvature",
    "projection of vehicle position onto centerline",
    "lateral error and off-track test",
    "lap count from wrapped progress",
)

VALIDATED_INVARIANTS = (
    "kind == TrackDefinition",
    "schemaVersion == 0.1.0",
    "units are metres, radians and seconds",
    "closed loop is implicit from last centerline point to first point",
    "direction is explicit and finite",
    "centerline has at least 8 points",
    "centerline ids are unique",
    "coordinates and widths are finite",
    "total width is at least 4 m everywhere",
    "start line references a centerline point",
    "checkpoints are present and reference centerline points",
    "loop length is finite and above 100 m",
    "preprocessed curvature is finite",
)

G_IMPORTER_ACCEPTANCE = (
    "Produce a TrackDefinition JSON with the source fields listed by C-S06.",
    "Do not store derived runtime geometry as source truth when it can be reconstructed deterministically.",
    "Preserve SI units or document a deterministic conversion to metres/radians/seconds.",
    "Preserve the ordered centerline and the driving direction.",
    "Provide left/right drivable widths or a deterministic fallback width policy.",
    "Provide a start line and at least one checkpoint reference.",
    "Pass the C-S01 validator without hidden repair.",
    "Run at least the C-S02 path-following smoke test after conversion.",
)


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def scenario_success(summary: dict[str, Any]) -> bool:
    return bool(summary.get("success"))


def collect_evidence(results_dir: Path) -> dict[str, Any]:
    paths = {
        "C-S01": results_dir / "c_s01_track_contract_summary.json",
        "C-S02": results_dir / "c_s02_path_following_summary.json",
        "C-S03": results_dir / "c_s03_curvature_speed_summary.json",
        "C-S04": results_dir / "c_s04_lateral_recovery_summary.json",
        "C-S05": results_dir / "c_s05_driver_profiles_summary.json",
    }
    return {scenario: load_json(path) for scenario, path in paths.items()}


def c_s01_metrics(evidence: dict[str, Any]) -> dict[str, Any]:
    processed = evidence["C-S01"]["preprocessed"]
    return {
        "pointCount": processed["pointCount"],
        "segmentCount": processed["segmentCount"],
        "totalLengthM": processed["totalLengthM"],
        "minTotalWidthM": processed["minTotalWidthM"],
        "maxAbsCurvature": processed["maxAbsCurvature"],
        "checkpointDistancesM": processed["checkpointDistancesM"],
    }


def reference_run(summary: dict[str, Any]) -> dict[str, Any]:
    reference_runs = summary.get("referenceRuns")
    if reference_runs:
        return reference_runs[0]
    for run in summary["runs"]:
        if abs(float(run["dt"]) - (1.0 / 120.0)) < 1e-12:
            return run
    raise RuntimeError(f"missing reference run for {summary.get('scenario')}")


def scenario_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    c2 = reference_run(evidence["C-S02"])
    c3 = reference_run(evidence["C-S03"])
    c4 = reference_run(evidence["C-S04"])
    c5_spread = evidence["C-S05"]["profileSpread"]
    c5_probe = evidence["C-S05"]["limitProbe"]
    return {
        "C-S01": c_s01_metrics(evidence),
        "C-S02": {
            "durationS": c2["durationS"],
            "meanAbsLateralErrorM": c2["meanAbsLateralErrorM"],
            "maxAbsLateralErrorM": c2["maxAbsLateralErrorM"],
            "offTrackCount": c2["offTrackCount"],
        },
        "C-S03": {
            "durationS": c3["durationS"],
            "meanSpeedKmh": c3["meanSpeedKmh"],
            "maxSpeedKmh": c3["maxSpeedKmh"],
            "meanAbsLateralErrorM": c3["meanAbsLateralErrorM"],
            "maxAbsLateralErrorM": c3["maxAbsLateralErrorM"],
            "maxLateralGModel": c3["maxLateralGModel"],
            "offTrackCount": c3["offTrackCount"],
        },
        "C-S04": {
            "maxRecoveryDurationS": c4["maxRecoveryDurationS"],
            "meanAbsLateralErrorM": c4["meanAbsLateralErrorM"],
            "maxAbsLateralErrorM": c4["maxAbsLateralErrorM"],
            "offTrackCount": c4["offTrackCount"],
            "recoveredPerturbations": sum(1 for event in c4["perturbations"] if event["recovered"]),
            "perturbationCount": len(c4["perturbations"]),
        },
        "C-S05": {
            "durationByProfileS": c5_spread["durationByProfileS"],
            "meanLateralErrorByProfileM": c5_spread["meanLateralErrorByProfileM"],
            "overspeedProbe": c5_probe,
        },
    }


def build_summary(track: dict[str, Any], evidence: dict[str, Any], repo_root: Path, track_path: Path) -> dict[str, Any]:
    scenario_ok = {scenario: scenario_success(evidence[scenario]) for scenario in EXPECTED_SCENARIOS}
    track_metrics = c_s01_metrics(evidence)
    source_field_paths = [field[0] for field in SOURCE_FIELDS]
    contract_ready_for_g = (
        all(scenario_ok.values())
        and track.get("kind") == "TrackDefinition"
        and track.get("schemaVersion") == "0.1.0"
        and track_metrics["pointCount"] >= 8
        and track_metrics["minTotalWidthM"] >= 4.0
        and math.isfinite(track_metrics["maxAbsCurvature"])
        and evidence["C-S05"]["limitProbe"]["expectedFailure"]
    )
    return {
        "scenario": "C-S06",
        "success": contract_ready_for_g,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": track_path.relative_to(repo_root).as_posix(),
        "contractCandidate": {
            "kind": "TrackDefinition",
            "schemaVersion": "0.1.0",
            "sourceFields": source_field_paths,
            "derivedRuntimeFields": list(DERIVED_FIELDS),
            "validatedInvariants": list(VALIDATED_INVARIANTS),
            "gImporterAcceptance": list(G_IMPORTER_ACCEPTANCE),
        },
        "sourceFieldDetails": [
            {
                "path": path,
                "type": field_type,
                "constraint": constraint,
                "reason": reason,
            }
            for path, field_type, constraint, reason in SOURCE_FIELDS
        ],
        "scenarioSuccess": scenario_ok,
        "evidence": scenario_evidence(evidence),
        "decision": {
            "status": "valide avec reserves" if contract_ready_for_g else "a modifier",
            "readyForExperimentG": contract_ready_for_g,
            "confidence": "moyen a bon",
            "mainReservation": (
                "TrackDefinition v0.1 is validated for centerline-based autonomous control, "
                "but not yet for real imported tracks, detailed surfaces, elevation, racing lines, "
                "or a full understeer/oversteer tyre model."
            ),
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    evidence = summary["evidence"]
    decision = summary["decision"]
    lines = [
        "# C-S06 - Consolidation du contrat minimal TrackDefinition",
        "",
        "- **Experience :** C - Tour autonome et modele minimal de circuit",
        "- **Scenario :** C-S06",
        f"- **Statut :** {decision['status']}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** figer le contrat minimal candidat que G devra reconstruire depuis UR2D2.",
        "- **Reserve :** le contrat est valide pour un controle centre-ligne ; il ne couvre pas encore elevation, surfaces detaillees, racing line ou pneus detailles.",
        "",
        "## Decision",
        "",
        f"- Pret pour l'experience G : {'oui' if decision['readyForExperimentG'] else 'non'}",
        f"- Niveau de confiance : {decision['confidence']}",
        f"- Reserve principale : {decision['mainReservation']}",
        "",
        "## Champs source TrackDefinition v0.1",
        "",
        "| Champ | Type | Contrainte | Raison |",
        "| --- | --- | --- | --- |",
    ]
    for field in summary["sourceFieldDetails"]:
        lines.append(f"| `{field['path']}` | {field['type']} | {field['constraint']} | {field['reason']} |")

    lines.extend(
        [
            "",
            "## Valeurs derivees a ne pas stocker comme verite source",
            "",
        ]
    )
    for field in summary["contractCandidate"]["derivedRuntimeFields"]:
        lines.append(f"- {field}")

    lines.extend(
        [
            "",
            "## Invariants valides",
            "",
        ]
    )
    for invariant in summary["contractCandidate"]["validatedInvariants"]:
        lines.append(f"- {invariant}")

    lines.extend(
        [
            "",
            "## Preuves C-S01 a C-S05",
            "",
            "| Scenario | Preuve retenue |",
            "| --- | --- |",
            (
                "| C-S01 | "
                f"{evidence['C-S01']['pointCount']} points, "
                f"{fmt_number(evidence['C-S01']['totalLengthM'])} m, "
                f"largeur min {fmt_number(evidence['C-S01']['minTotalWidthM'])} m, "
                f"courbure max {fmt_number(evidence['C-S01']['maxAbsCurvature'], 5)} 1/m |"
            ),
            (
                "| C-S02 | "
                f"3 tours, erreur laterale moyenne {fmt_number(evidence['C-S02']['meanAbsLateralErrorM'], 3)} m, "
                f"max {fmt_number(evidence['C-S02']['maxAbsLateralErrorM'], 3)} m, "
                f"sorties {evidence['C-S02']['offTrackCount']} |"
            ),
            (
                "| C-S03 | "
                f"3 tours en {fmt_number(evidence['C-S03']['durationS'])} s, "
                f"vitesse moyenne {fmt_number(evidence['C-S03']['meanSpeedKmh'])} km/h, "
                f"G lateral max {fmt_number(evidence['C-S03']['maxLateralGModel'], 3)} g |"
            ),
            (
                "| C-S04 | "
                f"{evidence['C-S04']['recoveredPerturbations']} / {evidence['C-S04']['perturbationCount']} perturbations recuperees, "
                f"recuperation max {fmt_number(evidence['C-S04']['maxRecoveryDurationS'], 3)} s, "
                f"sorties {evidence['C-S04']['offTrackCount']} |"
            ),
            (
                "| C-S05 | "
                f"profils differencies ; temoin sur-vitesse sat. grip "
                f"{fmt_number(evidence['C-S05']['overspeedProbe']['gripSaturationTickPercent'], 2)} %, "
                f"ratio {fmt_number(evidence['C-S05']['overspeedProbe']['maxGripSaturationRatio'], 2)}x, "
                f"sorties {evidence['C-S05']['overspeedProbe']['offTrackCount']} |"
            ),
            "",
            "## Contrat attendu pour G",
            "",
        ]
    )
    for item in summary["contractCandidate"]["gImporterAcceptance"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Limites reportees",
            "",
            "- Les largeurs restent scalaires gauche/droite ; pas encore de polygones de bord de piste.",
            "- La piste canonique est synthetique ; G devra verifier un vrai import.",
            "- La courbure est derivee d'une polyligne ; un lissage pourra etre necessaire.",
            "- La limite laterale vehicule reste un proxy issu de B-S04/A9.",
            "- C-S05 valide la detection de saturation du grip, pas un modele detaille sous-virage/survirage.",
            "",
            "## Conclusion",
            "",
            (
                "C-S06 valide avec reserves `TrackDefinition` v0.1 comme contrat d'entree de G."
                if summary["success"]
                else "C-S06 est a modifier avant de debloquer G."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run C-S06 TrackDefinition contract consolidation.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "results",
        help="Directory where C-S06 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    track = load_json(arguments.track)
    evidence = collect_evidence(arguments.results_dir)
    summary = build_summary(track, evidence, repo_root, arguments.track)

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "c_s06_contract_consolidation_summary.json"
    report_path = arguments.results_dir / "C_S06_CONTRACT_CONSOLIDATION_RESULT.md"
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
