#!/usr/bin/env python3
"""Run F-S03: measure accelerated no-render simulation throughput."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_f_s02_realtime_load import (  # noqa: E402
    aggregate_repetitions,
    environment_info,
    find_repo_root,
    fmt_number,
    load_json,
    rounded,
    run_realtime_repetition,
)


def run_profiles(replay: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    profile_results = []
    repetitions = int(config["repetitions"])
    for profile in config["profiles"]:
        runs = [run_realtime_repetition(replay, profile, config) for _ in range(repetitions)]
        aggregate = aggregate_repetitions(runs)
        profile_results.append(
            {
                "profileId": profile["id"],
                "label": profile["label"],
                "required": profile["required"],
                "runs": runs,
                "aggregate": aggregate,
                "dominantSystems": rank_systems(aggregate),
            }
        )
    return profile_results


def rank_systems(aggregate: dict[str, Any]) -> list[dict[str, Any]]:
    timings = aggregate["systemTimingsMean"]
    tick_mean = max(float(timings["tick"]["meanMs"]), 1e-9)
    ranked = []
    for name in ("input", "motion", "perception", "decision", "replay"):
        mean_ms = float(timings[name]["meanMs"])
        ranked.append({"system": name, "meanMs": rounded(mean_ms, 6), "share": rounded(mean_ms / tick_mean, 6)})
    return sorted(ranked, key=lambda item: item["meanMs"], reverse=True)


def validate_results(profile_results: list[dict[str, Any]], thresholds: dict[str, Any]) -> list[str]:
    errors = []
    for result in profile_results:
        if not result["required"]:
            continue
        aggregate = result["aggregate"]
        if aggregate["realTimeFactorMean"] < thresholds["requiredMinRealtimeFactor"]:
            errors.append(f"{result['profileId']} acceleration factor too low")
        if aggregate["tickP95MsMean"] > thresholds["requiredMaxP95TickMs"]:
            errors.append(f"{result['profileId']} tick p95 too high")
        if aggregate["tickMeanMsStdev"] > thresholds["requiredMaxTickStdevMs"]:
            errors.append(f"{result['profileId']} tick mean variance too high")
        if not aggregate["checksumStable"]:
            errors.append(f"{result['profileId']} checksum unstable")
    return errors


def render_markdown(summary: dict[str, Any]) -> str:
    status = "valide avec reserves" if summary["success"] else "echec"
    lines = [
        "# F-S03 - Simulation acceleree sans rendu",
        "",
        "- **Experience :** F - Charge et acceleration",
        "- **Scenario :** F-S03",
        f"- **Statut :** {status}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** mesurer le facteur d'acceleration atteignable sans rendu sur les profils cible.",
        "- **Reserve :** benchmark Python hors Unity, avec etats dupliques depuis le replay E-S01.",
        "",
        "## Seuils requis",
        "",
        f"- Facteur d'acceleration moyen : >= {fmt_number(summary['thresholds']['requiredMinRealtimeFactor'], 1)}x",
        f"- Tick p95 moyen : <= {fmt_number(summary['thresholds']['requiredMaxP95TickMs'], 2)} ms",
        f"- Ecart-type du tick moyen : <= {fmt_number(summary['thresholds']['requiredMaxTickStdevMs'], 2)} ms",
        "",
        "## Profils",
        "",
        "| Profil | Voitures | Requis | Wall moyen | Facteur | Tick moyen | Tick p95 | Veh-ticks/s | Systeme dominant | Replay bytes/s |",
        "| --- | ---:| --- | ---:| ---:| ---:| ---:| ---:| --- | ---:|",
    ]
    for result in summary["profiles"]:
        aggregate = result["aggregate"]
        dominant = result["dominantSystems"][0]
        lines.append(
            "| "
            f"{result['profileId']} | "
            f"{aggregate['vehicleCount']} | "
            f"{'oui' if result['required'] else 'non'} | "
            f"{fmt_number(aggregate['wallTimeMsMean'], 2)} ms | "
            f"{fmt_number(aggregate['realTimeFactorMean'], 1)}x | "
            f"{fmt_number(aggregate['tickMeanMsMean'], 4)} ms | "
            f"{fmt_number(aggregate['tickP95MsMean'], 4)} ms | "
            f"{fmt_number(aggregate['vehicleTicksPerSecondMean'], 0)} | "
            f"{dominant['system']} ({fmt_number(dominant['share'] * 100.0, 1)} %) | "
            f"{fmt_number(aggregate['serializedBytesPerSecondMean'], 0)} |"
        )
    lines.extend(["", "## Decision", ""])
    if summary["success"]:
        lines.append(
            "F-S03 est valide avec reserves. Les profils cible depassent largement le temps reel sans rendu, avec une marge suffisante pour poursuivre l'analyse du cout replay."
        )
    else:
        lines.append("F-S03 est a corriger ou a re-mesurer avant de valider l'acceleration sans rendu.")
    lines.append("")
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run F-S03 accelerated no-render benchmark.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=repo_root / "prototypes" / "replay" / "results" / "e_s01_minimal_replay.replay.json",
        help="Replay JSON produced by E-S01.",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "fixtures" / "f_s03_accelerated_profiles.json",
        help="F-S03 profile config.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "performance" / "results",
        help="Directory where F-S03 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    replay = load_json(arguments.replay)
    config = load_json(arguments.profiles)
    profile_results = run_profiles(replay, config)
    thresholds = config["thresholds"]
    profile_errors = validate_results(profile_results, thresholds)
    required_results = [result for result in profile_results if result["required"]]
    success = len(required_results) == 2 and len(profile_errors) == 0
    metrics = {
        "profileCount": len(profile_results),
        "requiredProfileCount": len(required_results),
        "repetitionsPerProfile": int(config["repetitions"]),
        "tickRateHz": float(config["tickRateHz"]),
        "simulatedDurationS": float(config["durationS"]),
        "profileErrorCount": len(profile_errors),
        "requiredProfilesPass": len(profile_errors) == 0,
        "minRequiredRealtimeFactorMean": min(result["aggregate"]["realTimeFactorMean"] for result in required_results),
        "maxRequiredTickP95MsMean": max(result["aggregate"]["tickP95MsMean"] for result in required_results),
        "maxRequiredTickMeanStdevMs": max(result["aggregate"]["tickMeanMsStdev"] for result in required_results),
    }
    summary = {
        "scenario": "F-S03",
        "success": success,
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "replayPath": arguments.replay.relative_to(repo_root).as_posix(),
        "profilesPath": arguments.profiles.relative_to(repo_root).as_posix(),
        "environment": environment_info(),
        "thresholds": thresholds,
        "profileErrors": profile_errors,
        "profiles": profile_results,
        "metrics": metrics,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "f_s03_accelerated_no_render_summary.json"
    report_path = arguments.results_dir / "F_S03_ACCELERATED_NO_RENDER_RESULT.md"
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
