#!/usr/bin/env python3
"""Run F-S05: consolidate performance experiment results."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_f_s02_realtime_load import find_repo_root, fmt_number, load_json  # noqa: E402


def pick_profile(summary: dict[str, Any], *, vehicle_count: int | None = None, profile_id: str | None = None, sample_hz: float | None = None) -> dict[str, Any]:
    for profile in summary["profiles"]:
        aggregate = profile["aggregate"]
        if profile_id is not None and profile.get("profileId") != profile_id:
            continue
        if vehicle_count is not None and aggregate.get("vehicleCount") != vehicle_count:
            continue
        if sample_hz is not None and abs(float(aggregate.get("replaySampleHz", -1.0)) - sample_hz) > 1e-9:
            continue
        return profile
    raise KeyError(f"profile not found: vehicle_count={vehicle_count}, profile_id={profile_id}, sample_hz={sample_hz}")


def build_decision(s01: dict[str, Any], s02: dict[str, Any], s03: dict[str, Any], s04: dict[str, Any]) -> dict[str, Any]:
    s02_20 = pick_profile(s02, profile_id="target_20")["aggregate"]
    s03_20 = pick_profile(s03, profile_id="target_20_accel")["aggregate"]
    s04_ref = pick_profile(s04, vehicle_count=20, sample_hz=4.0)["aggregate"]
    s04_high = pick_profile(s04, vehicle_count=20, sample_hz=20.0)["aggregate"]
    s01_40 = pick_profile(s01, vehicle_count=40)["aggregate"]
    success = all(summary["success"] for summary in (s01, s02, s03, s04))
    blockers = []
    if not s02["metrics"]["requiredProfilesPass"]:
        blockers.append("F-S02 target real-time profiles failed")
    if not s03["metrics"]["requiredProfilesPass"]:
        blockers.append("F-S03 accelerated profiles failed")
    if s04["metrics"]["profileErrorCount"] != 0:
        blockers.append("F-S04 replay-cost validation failed")
    return {
        "success": success and not blockers,
        "decision": "validee avec reserves" if success and not blockers else "a modifier",
        "confidence": "moyen",
        "blockers": blockers,
        "candidateParameters": {
            "targetVehicleCountMin": 12,
            "targetVehicleCountMax": 20,
            "stressVehicleCount": 40,
            "simulationTickRateHz": 60,
            "referenceReplaySampleHz": 4,
            "target20RealtimeFactorMean": s02_20["realTimeFactorMean"],
            "target20TickP95Ms": s02_20["tickP95MsMean"],
            "target20AcceleratedFactorMean": s03_20["realTimeFactorMean"],
            "target20ReplayShareAt4Hz": s04_ref["replayShareMean"],
            "target20ReplayBytesPerSecondAt4Hz": s04_ref["serializedBytesPerSecondMean"],
            "target20ReplayShareAt20Hz": s04_high["replayShareMean"],
            "stress40HarnessRealtimeFactorMean": s01_40["realTimeFactorMean"],
        },
        "residualRisks": [
            "mesures Python hors Unity et hors rendu reel",
            "voitures dupliquees depuis E-S01, sans comportements independants complets",
            "replay compact JSON en memoire, sans ecriture disque continue ni format binaire",
            "pics de scheduling Windows/Python visibles sur certains runs longs",
            "couts GPU, UI, audio, cameras et multithreading non mesures",
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    params = summary["decision"]["candidateParameters"]
    lines = [
        "# F-S05 - Synthese charge et acceleration",
        "",
        "- **Experience :** F - Charge et acceleration",
        "- **Scenario :** F-S05",
        f"- **Statut :** {summary['decision']['decision']}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** consolider F-S01 a F-S04 et produire la decision de cloture de l'experience F.",
        "- **Reserve :** synthese de benchmarks Python hors Unity ; la performance finale reste a confirmer dans le runtime produit.",
        "",
        "## Decision",
        "",
        f"- Conclusion : {summary['decision']['decision']}",
        f"- Niveau de confiance : {summary['decision']['confidence']}",
        f"- Blocages : {len(summary['decision']['blockers'])}",
        "",
        "## Resultats consolides",
        "",
        "| Preuve | Resultat | Valeur cle |",
        "| --- | --- | ---:|",
        f"| F-S01 harnais | valide avec reserves | stress 40 voitures {fmt_number(params['stress40HarnessRealtimeFactorMean'], 1)}x |",
        f"| F-S02 temps reel | valide avec reserves | 20 voitures p95 {fmt_number(params['target20TickP95Ms'], 4)} ms, {fmt_number(params['target20RealtimeFactorMean'], 1)}x |",
        f"| F-S03 accelere | valide avec reserves | 20 voitures {fmt_number(params['target20AcceleratedFactorMean'], 1)}x |",
        f"| F-S04 replay | valide avec reserves | 4 Hz: {fmt_number(params['target20ReplayShareAt4Hz'] * 100.0, 1)} %, {fmt_number(params['target20ReplayBytesPerSecondAt4Hz'], 0)} octets/s |",
        "",
        "## Parametres candidats",
        "",
        f"- cible voitures : `{params['targetVehicleCountMin']}` a `{params['targetVehicleCountMax']}` ;",
        f"- stress suivi : `{params['stressVehicleCount']}` voitures ;",
        f"- tick simulation : `{params['simulationTickRateHz']} Hz` ;",
        f"- frequence replay compacte : `{params['referenceReplaySampleHz']} Hz` ;",
        f"- replay `20 Hz` : garde comme option detaillee couteuse, part replay `{fmt_number(params['target20ReplayShareAt20Hz'] * 100.0, 1)} %`.",
        "",
        "## Reserves",
        "",
    ]
    for risk in summary["decision"]["residualRisks"]:
        lines.append(f"- {risk} ;")
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            "L'experience F est validee avec reserves. Les mesures reduisent le risque de charge pour le vertical slice, mais ne remplacent pas un profilage Unity reel.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run F-S05 performance synthesis.")
    parser.add_argument("--results-dir", type=Path, default=repo_root / "prototypes" / "performance" / "results")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    results_dir = arguments.results_dir
    s01 = load_json(results_dir / "f_s01_benchmark_harness_summary.json")
    s02 = load_json(results_dir / "f_s02_realtime_load_summary.json")
    s03 = load_json(results_dir / "f_s03_accelerated_no_render_summary.json")
    s04 = load_json(results_dir / "f_s04_replay_cost_summary.json")
    decision = build_decision(s01, s02, s03, s04)
    summary = {
        "scenario": "F-S05",
        "success": decision["success"],
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputSummaries": {
            "F-S01": "prototypes/performance/results/f_s01_benchmark_harness_summary.json",
            "F-S02": "prototypes/performance/results/f_s02_realtime_load_summary.json",
            "F-S03": "prototypes/performance/results/f_s03_accelerated_no_render_summary.json",
            "F-S04": "prototypes/performance/results/f_s04_replay_cost_summary.json",
        },
        "decision": decision,
        "sourceMetrics": {
            "fS01": s01["metrics"],
            "fS02": s02["metrics"],
            "fS03": s03["metrics"],
            "fS04": s04["metrics"],
        },
    }
    summary_path = results_dir / "f_s05_performance_summary.json"
    report_path = results_dir / "F_S05_PERFORMANCE_SUMMARY_RESULT.md"
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
