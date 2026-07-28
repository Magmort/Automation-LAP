#!/usr/bin/env python3
"""Run E-S06: aggregate replay minimal feasibility results."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "prototypes").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError(f"could not find repository root from {start}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def fmt_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def load_summaries(results_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        "E-S01": load_json(results_dir / "e_s01_replay_contract_summary.json"),
        "E-S02": load_json(results_dir / "e_s02_navigation_summary.json"),
        "E-S03": load_json(results_dir / "e_s03_event_jump_summary.json"),
        "E-S04": load_json(results_dir / "e_s04_sampling_size_summary.json"),
        "E-S05": load_json(results_dir / "e_s05_version_compatibility_summary.json"),
    }


def build_summary(summaries: dict[str, dict[str, Any]], repo_root: Path, results_dir: Path) -> dict[str, Any]:
    e_s01 = summaries["E-S01"]["metrics"]
    e_s02 = summaries["E-S02"]["metrics"]
    e_s03 = summaries["E-S03"]["metrics"]
    e_s04 = summaries["E-S04"]["metrics"]
    e_s05 = summaries["E-S05"]["metrics"]
    scenario_results = [
        {
            "scenario": scenario,
            "success": summary["success"],
            "resultPath": {
                "E-S01": "prototypes/replay/results/E_S01_REPLAY_CONTRACT_RESULT.md",
                "E-S02": "prototypes/replay/results/E_S02_NAVIGATION_RESULT.md",
                "E-S03": "prototypes/replay/results/E_S03_EVENT_JUMP_RESULT.md",
                "E-S04": "prototypes/replay/results/E_S04_SAMPLING_SIZE_RESULT.md",
                "E-S05": "prototypes/replay/results/E_S05_VERSION_COMPATIBILITY_RESULT.md",
            }[scenario],
        }
        for scenario, summary in summaries.items()
    ]
    metrics = {
        "validatedScenarioCount": sum(1 for result in scenario_results if result["success"]),
        "scenarioCount": len(scenario_results),
        "durationS": e_s01["durationS"],
        "replayFileBytes": e_s01["replayFileBytes"],
        "frameCount": e_s01["frameCount"],
        "vehicleCount": e_s01["vehicleCount"],
        "eventCount": e_s01["eventCount"],
        "trackPointCount": e_s01["trackPointCount"],
        "seekCheckCount": e_s01["seekCheckCount"],
        "navigationCommandCount": e_s02["commandCount"],
        "navigationTraceSampleCount": e_s02["traceSampleCount"],
        "navigationClampCount": e_s02["clampedSamples"],
        "navigationMonotonicFailures": e_s02["monotonicFailures"],
        "eventJumpCount": e_s03["jumpCount"],
        "validEventContextCount": e_s03["validContextCount"],
        "samplingProfileCount": e_s04["profileCount"],
        "samplingMinFileBytes": e_s04["minFileBytes"],
        "samplingMaxFileBytes": e_s04["maxFileBytes"],
        "samplingMinBytesPerSecond": e_s04["minBytesPerSecond"],
        "samplingMaxBytesPerSecond": e_s04["maxBytesPerSecond"],
        "compatibilityCaseCount": e_s05["caseCount"],
        "compatibilityMismatchCount": e_s05["mismatchCount"],
    }
    success = (
        metrics["validatedScenarioCount"] == metrics["scenarioCount"]
        and metrics["navigationMonotonicFailures"] == 0
        and metrics["compatibilityMismatchCount"] == 0
        and e_s04["validationErrorCount"] == 0
    )
    return {
        "scenario": "E-S06",
        "success": success,
        "decision": "validee avec reserves" if success else "a modifier",
        "confidence": "moyen a bon" if success else "faible",
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "resultsDir": results_dir.relative_to(repo_root).as_posix(),
            "summaries": {
                "E-S01": "prototypes/replay/results/e_s01_replay_contract_summary.json",
                "E-S02": "prototypes/replay/results/e_s02_navigation_summary.json",
                "E-S03": "prototypes/replay/results/e_s03_event_jump_summary.json",
                "E-S04": "prototypes/replay/results/e_s04_sampling_size_summary.json",
                "E-S05": "prototypes/replay/results/e_s05_version_compatibility_summary.json",
            },
        },
        "candidateContract": {
            "kind": "AutomationLapReplay",
            "schemaVersion": "0.1.0",
            "format": "JSON readable prototype",
            "units": {"time": "s", "distance": "m", "speed": "m/s", "angle": "rad"},
            "referenceTelemetryHz": 4.0,
            "measuredTelemetryHzRange": [1.0, 20.0],
            "keyframeIntervalS": 1.0,
            "versionPolicy": "strict accept list, no automatic migration in prototype",
        },
        "scenarioResults": scenario_results,
        "metrics": metrics,
        "residualRisks": [
            "JSON readable and not optimized; compression or binary packing remains to evaluate.",
            "Measurements use one deterministic 55 s scenario with 3 vehicles.",
            "Replay rendering and interpolation are not validated inside Unity UI yet.",
            "Schema migration is not implemented; incompatible versions are rejected explicitly.",
            "Advanced event categories, bookmarks and camera metadata are not covered yet.",
            "Load impact with 12 to 20 vehicles belongs to experiment F.",
        ],
        "recommendedNextWork": [
            "Use the E-S01 replay contract as candidate input for debugging and F load tests.",
            "Keep 4 Hz telemetry and 1 s keyframes as baseline until F measures cost at scale.",
            "Design schema migrations only when a second real replay schema exists.",
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        "# E-S06 - Synthese replay minimal",
        "",
        "- **Experience :** E - Replay minimal",
        "- **Scenario :** E-S06",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** consolider les preuves E-S01 a E-S05 et conclure sur la viabilite du replay minimal.",
        "- **Reserve :** conclusion hors Unity UI, hors compression finale et hors charge 12 a 20 voitures.",
        "",
        "## Decision",
        "",
        f"- Decision : **{summary['decision']}**",
        f"- Niveau de confiance : **{summary['confidence']}**",
        f"- Scenarios valides : {metrics['validatedScenarioCount']} / {metrics['scenarioCount']}",
        "",
        "## Contrat candidat",
        "",
        f"- Kind : `{summary['candidateContract']['kind']}`",
        f"- Schema : `{summary['candidateContract']['schemaVersion']}`",
        f"- Format : {summary['candidateContract']['format']}",
        "- Unites : `s`, `m`, `m/s`, `rad`",
        f"- Telemetrie de reference : {fmt_number(summary['candidateContract']['referenceTelemetryHz'], 1)} Hz",
        f"- Images-cles : toutes les {fmt_number(summary['candidateContract']['keyframeIntervalS'], 1)} s",
        f"- Politique version : {summary['candidateContract']['versionPolicy']}",
        "",
        "## Preuves consolidees",
        "",
        f"- E-S01 : replay autonome `55 s`, `{metrics['frameCount']}` frames, `{metrics['vehicleCount']}` vehicules, `{metrics['eventCount']}` evenements, `{metrics['replayFileBytes']}` octets.",
        f"- E-S02 : `{metrics['navigationCommandCount']}` commandes, `{metrics['navigationTraceSampleCount']}` samples, `{metrics['navigationClampCount']}` clamps, `{metrics['navigationMonotonicFailures']}` echec de monotonicite.",
        f"- E-S03 : `{metrics['eventJumpCount']}` sauts evenementiels, `{metrics['validEventContextCount']}` contextes valides.",
        f"- E-S04 : `{metrics['samplingProfileCount']}` frequences mesurees, `{metrics['samplingMinFileBytes']}` a `{metrics['samplingMaxFileBytes']}` octets, `{fmt_number(metrics['samplingMinBytesPerSecond'], 1)}` a `{fmt_number(metrics['samplingMaxBytesPerSecond'], 1)}` octets/s.",
        f"- E-S05 : `{metrics['compatibilityCaseCount']}` cas de compatibilite, `{metrics['compatibilityMismatchCount']}` mismatch.",
        "",
        "## Risques residuels",
        "",
    ]
    lines.extend(f"- {risk}" for risk in summary["residualRisks"])
    lines.extend(
        [
            "",
            "## Travaux recommandes",
            "",
            *[f"- {item}" for item in summary["recommendedNextWork"]],
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run E-S06 replay minimal summary.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results",
        help="Directory containing E-S01 to E-S05 summaries.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    summary = build_summary(load_summaries(arguments.results_dir), repo_root, arguments.results_dir)
    summary_path = arguments.results_dir / "e_s06_replay_summary.json"
    report_path = arguments.results_dir / "E_S06_REPLAY_SUMMARY_RESULT.md"
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
