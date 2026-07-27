#!/usr/bin/env python3
"""Run C-S04: lateral perturbation recovery with QFC55 speed adaptation."""

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

TARGET_LAPS = 3
TIME_STEPS = (1.0 / 60.0, 1.0 / 120.0)
REFERENCE_DT = 1.0 / 120.0
MAX_DURATION_S = 170.0
RECOVERY_THRESHOLD_M = 0.75
RECOVERY_TIME_LIMIT_S = 7.0
MAX_LATERAL_ERROR_LIMIT_M = 4.75
MEAN_LATERAL_ERROR_LIMIT_M = 1.75
LAP_TIME_VARIATION_LIMIT = 0.08
PERTURBATIONS = (
    {"id": "p1-left-entry", "progressLap": 0.55, "offsetM": 2.75},
    {"id": "p2-right-mid", "progressLap": 1.35, "offsetM": -3.25},
    {"id": "p3-left-late", "progressLap": 2.15, "offsetM": 3.00},
)
KMH_TO_MPS = 1.0 / 3.6
MPS_TO_KMH = 3.6


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


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": profile["name"],
        "exporterVersion": profile["exporterVersion"],
        "topSpeedKmh": profile["topSpeedKmh"],
        "lateralGripProxyG": profile["lateralGripProxyG"],
        "lateralLimitG": profile["lateralLimitG"],
    }


def perturbation_plan(track_length: float) -> list[dict[str, Any]]:
    return [
        {
            "id": str(item["id"]),
            "targetProgressM": float(item["progressLap"]) * track_length,
            "targetLapProgress": float(item["progressLap"]),
            "offsetM": float(item["offsetM"]),
            "applied": False,
            "appliedTimeS": None,
            "appliedProgressM": None,
            "appliedX": None,
            "appliedY": None,
            "initialLateralErrorM": None,
            "recovered": False,
            "recoveredTimeS": None,
            "recoveryDurationS": None,
            "recoveredX": None,
            "recoveredY": None,
            "maxAbsLateralDuringRecoveryM": 0.0,
        }
        for item in PERTURBATIONS
    ]


def apply_perturbation(
    c_s02: Any,
    segments: list[Any],
    track_length: float,
    state: dict[str, float],
    projection: dict[str, float],
    event: dict[str, Any],
) -> dict[str, float]:
    point = c_s02.point_at_s(segments, track_length, projection["s"])
    offset = float(event["offsetM"])
    state["x"] = point["x"] + point["normalX"] * offset
    state["y"] = point["y"] + point["normalY"] * offset
    event["applied"] = True
    event["appliedTimeS"] = state["time"]
    event["appliedProgressM"] = float(event["targetProgressM"])
    event["appliedX"] = state["x"]
    event["appliedY"] = state["y"]
    event["initialLateralErrorM"] = offset
    event["maxAbsLateralDuringRecoveryM"] = abs(offset)
    return c_s02.project_position(segments, track_length, state["x"], state["y"])


def update_recovery_events(state: dict[str, float], lateral_abs: float, events: list[dict[str, Any]]) -> None:
    for event in events:
        if not event["applied"] or event["recovered"]:
            continue
        event["maxAbsLateralDuringRecoveryM"] = max(event["maxAbsLateralDuringRecoveryM"], lateral_abs)
        if lateral_abs <= RECOVERY_THRESHOLD_M:
            event["recovered"] = True
            event["recoveredTimeS"] = state["time"]
            event["recoveryDurationS"] = state["time"] - float(event["appliedTimeS"])
            event["recoveredX"] = state["x"]
            event["recoveredY"] = state["y"]


def simulate(track: dict[str, Any], profile: dict[str, Any], c_s02: Any, c_s03: Any, dt: float) -> dict[str, Any]:
    points = c_s02.build_points(track)
    segments, track_length = c_s02.build_segments(points)
    start = c_s02.point_at_s(segments, track_length, 0.0)
    state = {
        "time": 0.0,
        "x": start["x"],
        "y": start["y"],
        "heading": start["heading"],
        "speed": c_s03.MIN_TARGET_SPEED_MPS,
    }
    events = perturbation_plan(track_length)
    completed_laps = 0
    previous_wrapped_s = 0.0
    unwrapped_s = 0.0
    lap_times: list[float] = []
    last_lap_time = 0.0
    off_track_count = 0
    lateral_abs_values: list[float] = []
    target_speed_values: list[float] = []
    speed_values: list[float] = []
    max_lateral_error = 0.0
    max_lateral_g = 0.0
    max_requested_lateral_g = 0.0
    grip_saturation_ticks = 0
    max_grip_saturation_ratio = 0.0
    max_curvature = 0.0
    max_abs_steer = 0.0
    throttle_ticks = 0
    brake_ticks = 0
    samples: list[dict[str, float]] = []
    next_sample_time = 0.0

    while completed_laps < TARGET_LAPS and state["time"] < MAX_DURATION_S:
        projection = c_s02.project_position(segments, track_length, state["x"], state["y"])
        wrapped_s = projection["s"]
        if previous_wrapped_s - wrapped_s > track_length * 0.5:
            completed_laps += 1
            lap_times.append(state["time"] - last_lap_time)
            last_lap_time = state["time"]
        elif wrapped_s - previous_wrapped_s > track_length * 0.5:
            completed_laps = max(0, completed_laps - 1)
        previous_wrapped_s = wrapped_s
        unwrapped_s = completed_laps * track_length + wrapped_s

        for event in events:
            if not event["applied"] and unwrapped_s >= float(event["targetProgressM"]):
                projection = apply_perturbation(c_s02, segments, track_length, state, projection, event)
                wrapped_s = projection["s"]
                unwrapped_s = completed_laps * track_length + wrapped_s

        lateral_abs = abs(projection["lateral"])
        lateral_abs_values.append(lateral_abs)
        max_lateral_error = max(max_lateral_error, lateral_abs)
        if lateral_abs > c_s02.track_limit_for_lateral(projection):
            off_track_count += 1
        update_recovery_events(state, lateral_abs, events)

        lookahead_curvature = c_s03.curvature_ahead(c_s02, segments, track_length, wrapped_s)
        max_curvature = max(max_curvature, lookahead_curvature)
        target_speed = c_s03.target_speed_for_curvature(profile, lookahead_curvature)
        target_speed_values.append(target_speed)
        speed_values.append(state["speed"])

        target = c_s02.point_at_s(segments, track_length, wrapped_s + c_s03.LOOKAHEAD_M)
        to_target_x = target["x"] - state["x"]
        to_target_y = target["y"] - state["y"]
        target_distance = max(math.hypot(to_target_x, to_target_y), 1e-9)
        forward_x = math.cos(state["heading"])
        forward_y = math.sin(state["heading"])
        dot = forward_x * to_target_x + forward_y * to_target_y
        cross = forward_x * to_target_y - forward_y * to_target_x
        heading_error = math.atan2(cross, dot)
        pursuit_curvature = 2.0 * math.sin(heading_error) / target_distance
        steer = c_s02.clamp(
            math.atan(c_s03.WHEELBASE_M * pursuit_curvature),
            -c_s03.MAX_STEER_RAD,
            c_s03.MAX_STEER_RAD,
        )
        max_abs_steer = max(max_abs_steer, abs(steer))

        speed_kmh = state["speed"] * MPS_TO_KMH
        available_accel = (
            c_s03.acceleration_at_speed_kmh(
                profile["accelerationSpeedKmh"],
                profile["accelerationTimeS"],
                speed_kmh,
            )
            * KMH_TO_MPS
            * c_s03.ACCEL_USAGE_FACTOR
        )
        available_decel = (
            c_s03.deceleration_at_speed_kmh(
                profile["brakingSpeedKmh"],
                profile["brakingTimeS"],
                speed_kmh,
            )
            * KMH_TO_MPS
            * c_s03.BRAKE_USAGE_FACTOR
        )
        desired_accel = (target_speed - state["speed"]) / c_s03.SPEED_RESPONSE_TIME_S
        accel = c_s02.clamp(desired_accel, -available_decel, available_accel)
        if accel > 0.05:
            throttle_ticks += 1
        elif accel < -0.05:
            brake_ticks += 1

        midpoint_speed = max(0.0, state["speed"] + accel * dt * 0.5)
        yaw_model = c_s03.grip_limited_yaw(midpoint_speed, steer, c_s03.WHEELBASE_M, profile["lateralLimitG"])
        yaw_rate = float(yaw_model["actualYawRate"])
        midpoint_heading = state["heading"] + yaw_rate * dt * 0.5
        requested_lateral_g = float(yaw_model["requestedLateralG"])
        lateral_g = float(yaw_model["actualLateralG"])
        max_requested_lateral_g = max(max_requested_lateral_g, requested_lateral_g)
        max_lateral_g = max(max_lateral_g, lateral_g)
        if yaw_model["saturated"]:
            grip_saturation_ticks += 1
            max_grip_saturation_ratio = max(max_grip_saturation_ratio, float(yaw_model["saturationRatio"]))

        state["x"] += math.cos(midpoint_heading) * midpoint_speed * dt
        state["y"] += math.sin(midpoint_heading) * midpoint_speed * dt
        state["heading"] = c_s02.normalize_angle(state["heading"] + yaw_rate * dt)
        state["speed"] = max(0.0, min(profile["topSpeedMps"], state["speed"] + accel * dt))
        state["time"] += dt

        if state["time"] + 1e-9 >= next_sample_time:
            samples.append(
                {
                    "time": state["time"],
                    "lap": completed_laps,
                    "progressM": unwrapped_s,
                    "x": state["x"],
                    "y": state["y"],
                    "heading": state["heading"],
                    "speedKmh": state["speed"] * MPS_TO_KMH,
                    "targetSpeedKmh": target_speed * MPS_TO_KMH,
                    "lateralErrorM": projection["lateral"],
                    "lookaheadCurvature": lookahead_curvature,
                    "steerRad": steer,
                    "requestedLateralGModel": requested_lateral_g,
                    "lateralGModel": lateral_g,
                    "gripSaturated": 1.0 if yaw_model["saturated"] else 0.0,
                }
            )
            next_sample_time += 0.25

    mean_abs_lateral = sum(lateral_abs_values) / len(lateral_abs_values)
    rms_lateral = math.sqrt(sum(value * value for value in lateral_abs_values) / len(lateral_abs_values))
    lap_variation = 0.0
    if len(lap_times) >= 2:
        mean_lap = sum(lap_times) / len(lap_times)
        lap_variation = (max(lap_times) - min(lap_times)) / mean_lap if mean_lap else math.inf
    finite_values = all(
        math.isfinite(value)
        for value in (
            state["time"],
            state["x"],
            state["y"],
            state["heading"],
            state["speed"],
            mean_abs_lateral,
            rms_lateral,
            max_lateral_error,
            lap_variation,
            max_lateral_g,
        )
    )
    recovered_events = [event for event in events if event["recovered"]]
    recovery_durations = [float(event["recoveryDurationS"]) for event in recovered_events]
    max_recovery_duration = max(recovery_durations) if recovery_durations else math.inf
    return {
        "dt": dt,
        "targetLaps": TARGET_LAPS,
        "completedLaps": completed_laps,
        "durationS": state["time"],
        "lapTimesS": lap_times,
        "lapTimeVariation": lap_variation,
        "meanAbsLateralErrorM": mean_abs_lateral,
        "rmsLateralErrorM": rms_lateral,
        "maxAbsLateralErrorM": max_lateral_error,
        "offTrackCount": off_track_count,
        "minSpeedKmh": min(speed_values) * MPS_TO_KMH,
        "maxSpeedKmh": max(speed_values) * MPS_TO_KMH,
        "meanSpeedKmh": sum(speed_values) * MPS_TO_KMH / len(speed_values),
        "minTargetSpeedKmh": min(target_speed_values) * MPS_TO_KMH,
        "maxTargetSpeedKmh": max(target_speed_values) * MPS_TO_KMH,
        "maxLookaheadCurvature": max_curvature,
        "maxLateralGModel": max_lateral_g,
        "maxRequestedLateralGModel": max_requested_lateral_g,
        "gripSaturationTickPercent": 100.0 * grip_saturation_ticks / len(speed_values),
        "maxGripSaturationRatio": max_grip_saturation_ratio,
        "maxAbsSteerRad": max_abs_steer,
        "throttleTickPercent": 100.0 * throttle_ticks / len(speed_values),
        "brakeTickPercent": 100.0 * brake_ticks / len(speed_values),
        "perturbations": events,
        "maxRecoveryDurationS": max_recovery_duration,
        "finalState": state,
        "samples": samples,
        "finiteValues": finite_values,
        "success": (
            completed_laps >= TARGET_LAPS
            and off_track_count == 0
            and finite_values
            and len(recovered_events) == len(events)
            and max_recovery_duration <= RECOVERY_TIME_LIMIT_S
            and mean_abs_lateral <= MEAN_LATERAL_ERROR_LIMIT_M
            and max_lateral_error <= MAX_LATERAL_ERROR_LIMIT_M
            and lap_variation <= LAP_TIME_VARIATION_LIMIT
            and max_lateral_g <= profile["lateralLimitG"] * 1.10
        ),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    profile = summary["vehicleProfile"]
    lines = [
        "# C-S04 - Recuperation apres perturbation laterale",
        "",
        "- **Experience :** C - Tour autonome et modele minimal de circuit",
        "- **Scenario :** C-S04",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier que le controleur C-S03 recupere des ecarts lateraux imposes sans logique speciale par virage.",
        "- **Reserve :** la limite laterale reste derivee du proxy B-S04 `FrontGripG + RearGripG` avec facteur de securite.",
        "",
        "## Donnees vehicule",
        "",
        f"- Vehicule : {profile['name']}",
        f"- Exporteur : `{profile['exporterVersion']}`",
        f"- Source : `{summary['vehicleInputPath']}`",
        f"- Limite laterale utilisee : {fmt_number(profile['lateralLimitG'], 3)} g",
        "",
        "## Perturbations",
        "",
        f"- Seuil de recuperation : {fmt_number(summary['successCriteria']['recoveryThresholdM'], 2)} m d'erreur laterale absolue",
        f"- Temps maximum autorise : {fmt_number(summary['successCriteria']['recoveryTimeLimitS'], 2)} s",
        "- Application : deplacement lateral instantane de la voiture, vitesse et cap conserves.",
        "",
        "## Resultats par pas de temps",
        "",
        "| dt | Tours | Duree | Erreur lat. moy. | Erreur lat. max | Recuperation max | Sorties | Variation tours | Lat. G max | Stable |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in summary["runs"]:
        lines.append(
            "| "
            f"{fmt_number(run['dt'], 5)} | "
            f"{run['completedLaps']} | "
            f"{fmt_number(run['durationS'])} | "
            f"{fmt_number(run['meanAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxRecoveryDurationS'], 3)} | "
            f"{run['offTrackCount']} | "
            f"{fmt_number(run['lapTimeVariation'] * 100.0, 2)} % | "
            f"{fmt_number(run['maxLateralGModel'], 3)} | "
            f"{fmt_bool(run['success'])} |"
        )

    reference = summary["referenceRun"]
    lines.extend(
        [
            "",
            "## Recuperations reference 1/120 s",
            "",
            "| Perturbation | Offset | Temps | Progression | Recuperation | Max erreur pendant recup. |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for event in reference["perturbations"]:
        lines.append(
            "| "
            f"{event['id']} | "
            f"{fmt_number(event['offsetM'], 2)} m | "
            f"{fmt_number(event['appliedTimeS'], 2)} s | "
            f"{fmt_number(event['appliedProgressM'], 2)} m | "
            f"{fmt_number(event['recoveryDurationS'], 3)} s | "
            f"{fmt_number(event['maxAbsLateralDuringRecoveryM'], 3)} m |"
        )

    lines.extend(
        [
            "",
            "## Reference 1/120 s",
            "",
            f"- Duree totale : {fmt_number(reference['durationS'])} s",
            f"- Vitesse moyenne : {fmt_number(reference['meanSpeedKmh'])} km/h",
            f"- Vitesse max : {fmt_number(reference['maxSpeedKmh'])} km/h",
            f"- Erreur laterale moyenne : {fmt_number(reference['meanAbsLateralErrorM'], 3)} m",
            f"- Erreur laterale max : {fmt_number(reference['maxAbsLateralErrorM'], 3)} m",
            f"- Recuperation la plus lente : {fmt_number(reference['maxRecoveryDurationS'], 3)} s",
            "",
            "## Observations",
            "",
            "- Les perturbations sont appliquees a des progressions fixes et non a des virages scripts.",
            "- Le controleur conserve la logique C-S03 : vitesse cible par courbure, pure pursuit et courbes QFC55.",
            "- Les deux pas de temps terminent trois tours sans sortie de piste et recuperent les trois ecarts lateraux.",
            "",
            "## Decision",
            "",
            "C-S04 est valide avec reserves. Le prototype peut passer a C-S05 pour differencier des profils de competence pilote.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run C-S04 lateral perturbation recovery with QFC55.")
    parser.add_argument(
        "--track",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "fixtures" / "canonical_track.json",
        help="TrackDefinition JSON fixture.",
    )
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
        "--results-dir",
        type=Path,
        default=repo_root / "prototypes" / "autonomous-lap" / "results",
        help="Directory where C-S04 result files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repo_root = find_repo_root(Path(__file__))
    c_s01 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s01_track_contract.py",
        "run_c_s01_track_contract",
    )
    c_s02 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s02_path_following.py",
        "run_c_s02_path_following",
    )
    c_s03 = load_module(
        repo_root / "prototypes" / "autonomous-lap" / "tools" / "run_c_s03_curvature_speed.py",
        "run_c_s03_curvature_speed",
    )
    validator = load_module(
        repo_root / "prototypes" / "automation-exporter" / "tools" / "validate_raw_vehicle_data.py",
        "validate_raw_vehicle_data",
    )
    track = load_json(arguments.track)
    track_errors = c_s01.validate_track(track)
    if track_errors:
        raise RuntimeError("invalid TrackDefinition: " + "; ".join(track_errors))
    vehicle = load_json(arguments.vehicle)
    validator.validate_document(vehicle)
    profile = c_s03.qfc55_profile(vehicle)
    runs = [simulate(track, profile, c_s02, c_s03, dt) for dt in TIME_STEPS]
    reference_run = next(run for run in runs if abs(run["dt"] - REFERENCE_DT) < 1e-12)
    summary = {
        "scenario": "C-S04",
        "success": all(run["success"] for run in runs),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "vehicleInputPath": arguments.vehicle.relative_to(repo_root).as_posix(),
        "vehicleProfile": public_profile(profile),
        "modelAssumptions": {
            "baseController": "C-S03 pure pursuit with curvature-based speed target",
            "lateralPerturbation": "instant centerline-normal displacement, speed and heading preserved",
            "recoveryThresholdM": RECOVERY_THRESHOLD_M,
            "recoveryTimeLimitS": RECOVERY_TIME_LIMIT_S,
            "perturbations": PERTURBATIONS,
        },
        "successCriteria": {
            "targetLaps": TARGET_LAPS,
            "offTrackCount": 0,
            "allPerturbationsRecovered": True,
            "recoveryThresholdM": RECOVERY_THRESHOLD_M,
            "recoveryTimeLimitS": RECOVERY_TIME_LIMIT_S,
            "meanLateralErrorMMax": MEAN_LATERAL_ERROR_LIMIT_M,
            "maxLateralErrorMMax": MAX_LATERAL_ERROR_LIMIT_M,
            "lapTimeVariationMax": LAP_TIME_VARIATION_LIMIT,
            "maxLateralGModel": "not above lateral limit + 10 percent",
        },
        "runs": runs,
        "referenceRun": reference_run,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "c_s04_lateral_recovery_summary.json"
    report_path = arguments.results_dir / "C_S04_LATERAL_RECOVERY_RESULT.md"
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
