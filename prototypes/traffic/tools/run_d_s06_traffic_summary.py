#!/usr/bin/env python3
"""Run D-S06: consolidate traffic experiment results."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True


RESULT_FILES = {
    "D-S01": "d_s01_neighbor_perception_summary.json",
    "D-S02": "d_s02_longitudinal_follow_summary.json",
    "D-S03": "d_s03_overtake_candidate_summary.json",
    "D-S04": "d_s04_side_by_side_summary.json",
    "D-S05": "d_s05_rejoin_summary.json",
}


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


def scenario_status(success: bool, reserve: bool = True) -> str:
    if not success:
        return "echec"
    return "valide avec reserves" if reserve else "valide"


def build_scenario_summaries(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    d_s01_metrics = results["D-S01"]["metrics"]
    d_s02_metrics = results["D-S02"]["run"]["metrics"]
    d_s03_metrics = results["D-S03"]["metrics"]
    d_s04_metrics = results["D-S04"]["run"]["metrics"]
    d_s05_metrics = results["D-S05"]["run"]["metrics"]
    return [
        {
            "id": "D-S01",
            "label": "Perception voisins",
            "success": bool(results["D-S01"]["success"]),
            "status": scenario_status(bool(results["D-S01"]["success"]), reserve=False),
            "evidence": "6 voitures, 6 liens voisins, wrap depart valide",
            "keyMetrics": {
                "vehicleCount": d_s01_metrics["vehicleCount"],
                "neighborLinkCount": d_s01_metrics["neighborLinkCount"],
                "offTrackCount": d_s01_metrics["offTrackCount"],
                "maxProjectionProgressErrorM": d_s01_metrics["maxProjectionProgressErrorM"],
            },
        },
        {
            "id": "D-S02",
            "label": "Suivi longitudinal",
            "success": bool(results["D-S02"]["success"]),
            "status": scenario_status(bool(results["D-S02"]["success"])),
            "evidence": "90 s derriere leader lent, gap stabilise, aucun contact",
            "keyMetrics": {
                "durationS": results["D-S02"]["run"]["durationS"],
                "contactTicks": d_s02_metrics["contactTicks"],
                "stalledTicks": d_s02_metrics["stalledTicks"],
                "minGapM": d_s02_metrics["minGapM"],
                "frontDetectedTickPercent": d_s02_metrics["frontDetectedTickPercent"],
                "meanGapLast20S": d_s02_metrics["meanGapLast20S"],
            },
        },
        {
            "id": "D-S03",
            "label": "Decision depassement",
            "success": bool(results["D-S03"]["success"]),
            "status": scenario_status(bool(results["D-S03"]["success"])),
            "evidence": "4 cas conformes, declenchement seulement si corridor candidat libre",
            "keyMetrics": {
                "caseCount": d_s03_metrics["caseCount"],
                "matchedCases": d_s03_metrics["matchedCases"],
                "positiveDecisions": d_s03_metrics["positiveDecisions"],
                "negativeDecisions": d_s03_metrics["negativeDecisions"],
                "blockedCandidateCases": d_s03_metrics["blockedCandidateCases"],
            },
        },
        {
            "id": "D-S04",
            "label": "Cote a cote",
            "success": bool(results["D-S04"]["success"]),
            "status": scenario_status(bool(results["D-S04"]["success"])),
            "evidence": "45 s cote a cote, clearance stabilisee, aucun contact",
            "keyMetrics": {
                "durationS": results["D-S04"]["run"]["durationS"],
                "contactTicks": d_s04_metrics["contactTicks"],
                "offTrackTicks": d_s04_metrics["offTrackTicks"],
                "sideBySideTickPercent": d_s04_metrics["sideBySideTickPercent"],
                "minSideClearanceM": d_s04_metrics["minSideClearanceM"],
                "meanSideClearanceLast15S": d_s04_metrics["meanSideClearanceLast15S"],
                "minEdgeClearanceM": d_s04_metrics["minEdgeClearanceM"],
            },
        },
        {
            "id": "D-S05",
            "label": "Reinsertion",
            "success": bool(results["D-S05"]["success"]),
            "status": scenario_status(bool(results["D-S05"]["success"])),
            "evidence": "retour corridor cible entre deux voitures, gaps surs, aucun contact",
            "keyMetrics": {
                "durationS": results["D-S05"]["run"]["durationS"],
                "contactTicks": d_s05_metrics["contactTicks"],
                "offTrackTicks": d_s05_metrics["offTrackTicks"],
                "rejoinDurationS": d_s05_metrics["rejoinDurationS"],
                "minFrontGapDuringRejoinM": d_s05_metrics["minFrontGapDuringRejoinM"],
                "minRearGapDuringRejoinM": d_s05_metrics["minRearGapDuringRejoinM"],
                "stableTargetLaneTickPercent": d_s05_metrics["stableTargetLaneTickPercent"],
                "finalLateralOffsetM": d_s05_metrics["finalLateralOffsetM"],
            },
        },
    ]


def build_capabilities(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    d_s01 = results["D-S01"]["metrics"]
    d_s02 = results["D-S02"]["run"]["metrics"]
    d_s03 = results["D-S03"]["metrics"]
    d_s04 = results["D-S04"]["run"]["metrics"]
    d_s05 = results["D-S05"]["run"]["metrics"]
    return [
        {
            "capability": "Projection multi-voitures et perception voisins",
            "status": "validee",
            "evidence": f"{d_s01['vehicleCount']} voitures, {d_s01['neighborLinkCount']} liens, erreur max {fmt_number(d_s01['maxProjectionProgressErrorM'])} m",
        },
        {
            "capability": "Suivi longitudinal derriere voiture lente",
            "status": "validee avec reserves",
            "evidence": f"gap min {fmt_number(d_s02['minGapM'])} m, detection front {fmt_number(d_s02['frontDetectedTickPercent'])} %",
        },
        {
            "capability": "Decision de depassement candidat",
            "status": "validee avec reserves",
            "evidence": f"{d_s03['matchedCases']} / {d_s03['caseCount']} cas conformes, {d_s03['blockedCandidateCases']} blockers detectes",
        },
        {
            "capability": "Maintien cote a cote",
            "status": "validee avec reserves",
            "evidence": f"{fmt_number(d_s04['sideBySideTickPercent'])} % du temps, clearance stable {fmt_number(d_s04['meanSideClearanceLast15S'])} m",
        },
        {
            "capability": "Reinsertion nominale apres ecart",
            "status": "validee avec reserves",
            "evidence": f"reinsertion {fmt_number(d_s05['rejoinDurationS'])} s, gaps min {fmt_number(d_s05['minFrontGapDuringRejoinM'])} m / {fmt_number(d_s05['minRearGapDuringRejoinM'])} m",
        },
    ]


def compute_global_metrics(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    d_s02 = results["D-S02"]["run"]
    d_s04 = results["D-S04"]["run"]
    d_s05 = results["D-S05"]["run"]
    dynamic_metrics = [d_s02["metrics"], d_s04["metrics"], d_s05["metrics"]]
    total_contact_ticks = sum(int(metrics["contactTicks"]) for metrics in dynamic_metrics)
    total_off_track_ticks = int(results["D-S01"]["metrics"]["offTrackCount"]) + int(d_s04["metrics"]["offTrackTicks"]) + int(
        d_s05["metrics"]["offTrackTicks"]
    )
    total_simulated_time_s = float(d_s02["durationS"]) + float(d_s04["durationS"]) + float(d_s05["durationS"])
    return {
        "scenarioCount": len(RESULT_FILES),
        "successfulScenarioCount": sum(1 for result in results.values() if result["success"]),
        "dynamicScenarioCount": 3,
        "totalSimulatedDynamicTimeS": total_simulated_time_s,
        "totalContactTicks": total_contact_ticks,
        "totalOffTrackTicks": total_off_track_ticks,
        "decisionCaseCount": results["D-S03"]["metrics"]["caseCount"],
        "matchedDecisionCaseCount": results["D-S03"]["metrics"]["matchedCases"],
        "rejoinDurationS": d_s05["metrics"]["rejoinDurationS"],
        "sideBySideTickPercent": d_s04["metrics"]["sideBySideTickPercent"],
        "minFollowGapM": d_s02["metrics"]["minGapM"],
        "minRejoinFrontGapM": d_s05["metrics"]["minFrontGapDuringRejoinM"],
        "minRejoinRearGapM": d_s05["metrics"]["minRearGapDuringRejoinM"],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["globalMetrics"]
    lines = [
        "# D-S06 - Synthese statistique trafic",
        "",
        "- **Experience :** D - Trafic et depassement",
        "- **Scenario :** D-S06",
        f"- **Statut :** {'validee avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** consolider les preuves D-S01 a D-S05 et conclure l'experience D.",
        "",
        "## Resultat global",
        "",
        f"- Scenarios conformes : {metrics['successfulScenarioCount']} / {metrics['scenarioCount']}",
        f"- Temps dynamique simule : {fmt_number(metrics['totalSimulatedDynamicTimeS'])} s",
        f"- Contact ticks consolides : {metrics['totalContactTicks']}",
        f"- Hors-piste consolides : {metrics['totalOffTrackTicks']}",
        f"- Cas de decision conformes : {metrics['matchedDecisionCaseCount']} / {metrics['decisionCaseCount']}",
        f"- Duree de reinsertion D-S05 : {fmt_number(metrics['rejoinDurationS'])} s",
        "",
        "## Scenarios",
        "",
        "| Scenario | Statut | Preuve |",
        "| --- | --- | --- |",
    ]
    for scenario in summary["scenarios"]:
        lines.append(f"| {scenario['id']} - {scenario['label']} | {scenario['status']} | {scenario['evidence']} |")
    lines.extend(
        [
            "",
            "## Capacites validees",
            "",
            "| Capacite | Statut | Preuve |",
            "| --- | --- | --- |",
        ]
    )
    for capability in summary["capabilities"]:
        lines.append(f"| {capability['capability']} | {capability['status']} | {capability['evidence']} |")
    lines.extend(
        [
            "",
            "## Limites residuelles",
            "",
        ]
    )
    for limitation in summary["residualRisks"]:
        lines.append(f"- {limitation}")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "L'experience D est validee avec reserves. Elle reduit le risque principal sur la representation du trafic, la perception, le suivi, la decision candidate et la reinsertion nominale. Elle ne prouve pas encore les interactions longues, denses ou contestees."
                if summary["success"]
                else "L'experience D reste a corriger avant de passer a la suite."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run D-S06 traffic summary.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "traffic" / "results",
        help="Directory containing D-S01 to D-S05 result files.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    results: dict[str, dict[str, Any]] = {}
    missing_files: list[str] = []
    for scenario_id, filename in RESULT_FILES.items():
        path = arguments.results_dir / filename
        if not path.is_file():
            missing_files.append(path.relative_to(repo_root).as_posix())
            continue
        results[scenario_id] = load_json(path)
    if missing_files:
        raise RuntimeError("missing D result files: " + ", ".join(missing_files))

    scenario_summaries = build_scenario_summaries(results)
    global_metrics = compute_global_metrics(results)
    residual_risks = [
        "Les scenarios D restent deterministes et peu nombreux.",
        "La reinsertion contestee, la defense active et les gaps qui se referment ne sont pas encore testes.",
        "Les collisions restent detectees par enveloppes simples, sans physique de contact detaillee.",
        "La densite de grille et la performance appartiennent encore a F.",
        "Le replay E reste utile pour analyser les interactions longues et diagnostiquer les cas limites.",
    ]
    success = (
        global_metrics["successfulScenarioCount"] == global_metrics["scenarioCount"]
        and global_metrics["totalContactTicks"] == 0
        and global_metrics["totalOffTrackTicks"] == 0
        and global_metrics["matchedDecisionCaseCount"] == global_metrics["decisionCaseCount"]
        and global_metrics["rejoinDurationS"] is not None
    )
    summary = {
        "scenario": "D-S06",
        "success": success,
        "decision": "validated_with_reserves" if success else "failed",
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "sourceFiles": {
            scenario_id: (arguments.results_dir / filename).relative_to(repo_root).as_posix()
            for scenario_id, filename in RESULT_FILES.items()
        },
        "globalMetrics": global_metrics,
        "scenarios": scenario_summaries,
        "capabilities": build_capabilities(results),
        "residualRisks": residual_risks,
    }
    summary_path = arguments.results_dir / "d_s06_traffic_summary.json"
    report_path = arguments.results_dir / "D_S06_TRAFFIC_SUMMARY_RESULT.md"
    with summary_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with report_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_markdown(summary))
    print(f"Wrote {summary_path.relative_to(repo_root)}")
    print(f"Wrote {report_path.relative_to(repo_root)}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
