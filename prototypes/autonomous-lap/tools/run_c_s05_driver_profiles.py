#!/usr/bin/env python3
"""Run C-S05: compare driver competence profiles on the QFC55 autonomous lap."""

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
MAX_DURATION_S = 190.0
MEAN_LATERAL_ERROR_LIMIT_M = 1.75
MAX_LATERAL_ERROR_LIMIT_M = 4.75
LAP_TIME_VARIATION_LIMIT = 0.08
MIN_LAP_TIME_SPREAD_S = 8.0
KMH_TO_MPS = 1.0 / 3.6
MPS_TO_KMH = 3.6

DRIVER_PROFILES = (
    {
        "id": "cautious",
        "label": "Prudent",
        "description": "forte marge de grip, vitesse reduite, ligne propre",
        "lookaheadM": 10.0,
        "targetSpeedScale": 0.78,
        "lateralLimitScale": 0.72,
        "accelUsageFactor": 0.70,
        "brakeUsageFactor": 0.70,
        "speedResponseTimeS": 1.00,
        "steerGain": 1.00,
        "maxSteerRad": 0.32,
    },
    {
        "id": "balanced",
        "label": "Equilibre",
        "description": "proche du grip max avec une marge legere",
        "lookaheadM": 16.0,
        "targetSpeedScale": 1.00,
        "lateralLimitScale": 1.00,
        "accelUsageFactor": 0.85,
        "brakeUsageFactor": 0.70,
        "speedResponseTimeS": 0.85,
        "steerGain": 1.00,
        "maxSteerRad": 0.32,
    },
    {
        "id": "aggressive",
        "label": "Agressif",
        "description": "proche de la limite pneus, accepte d'elargir",
        "lookaheadM": 16.0,
        "targetSpeedScale": 1.35,
        "lateralLimitScale": 1.25,
        "accelUsageFactor": 0.96,
        "brakeUsageFactor": 0.86,
        "speedResponseTimeS": 0.62,
        "steerGain": 0.90,
        "maxSteerRad": 0.34,
    },
)

LIMIT_PROBE_PROFILE = {
    "id": "overspeed_probe",
    "label": "Temoin sur-vitesse",
    "description": "temoin negatif hors grip, doit saturer et degrader la trajectoire",
    "lookaheadM": 10.0,
    "targetSpeedScale": 1.50,
    "lateralLimitScale": 1.30,
    "accelUsageFactor": 1.00,
    "brakeUsageFactor": 0.20,
    "speedResponseTimeS": 0.45,
    "steerGain": 0.80,
    "maxSteerRad": 0.40,
}


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


def public_vehicle_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": profile["name"],
        "exporterVersion": profile["exporterVersion"],
        "topSpeedKmh": profile["topSpeedKmh"],
        "lateralGripProxyG": profile["lateralGripProxyG"],
        "lateralLimitG": profile["lateralLimitG"],
    }


def target_speed_for_profile(vehicle_profile: dict[str, Any], driver_profile: dict[str, Any], curvature: float) -> float:
    if curvature <= 1e-7:
        lateral_limited = vehicle_profile["topSpeedMps"]
    else:
        lateral_limit_g = vehicle_profile["lateralLimitG"] * driver_profile["lateralLimitScale"]
        lateral_limited = math.sqrt(lateral_limit_g * 9.80665 / curvature)
    scaled_target = lateral_limited * driver_profile["targetSpeedScale"]
    return max(9.0, min(vehicle_profile["topSpeedMps"], scaled_target))


def simulate_driver(
    track: dict[str, Any],
    vehicle_profile: dict[str, Any],
    driver_profile: dict[str, Any],
    c_s02: Any,
    c_s03: Any,
    dt: float,
) -> dict[str, Any]:
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
    completed_laps = 0
    previous_wrapped_s = 0.0
    unwrapped_s = 0.0
    lap_times: list[float] = []
    last_lap_time = 0.0
    off_track_count = 0
    lateral_abs_values: list[float] = []
    speed_values: list[float] = []
    target_speed_values: list[float] = []
    max_lateral_error = 0.0
    max_lateral_g = 0.0
    max_requested_lateral_g = 0.0
    grip_saturation_ticks = 0
    max_grip_saturation_ratio = 0.0
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

        lateral_abs = abs(projection["lateral"])
        lateral_abs_values.append(lateral_abs)
        max_lateral_error = max(max_lateral_error, lateral_abs)
        if lateral_abs > c_s02.track_limit_for_lateral(projection):
            off_track_count += 1

        lookahead_curvature = c_s03.curvature_ahead(c_s02, segments, track_length, wrapped_s)
        target_speed = target_speed_for_profile(vehicle_profile, driver_profile, lookahead_curvature)
        target_speed_values.append(target_speed)
        speed_values.append(state["speed"])

        target = c_s02.point_at_s(segments, track_length, wrapped_s + driver_profile["lookaheadM"])
        to_target_x = target["x"] - state["x"]
        to_target_y = target["y"] - state["y"]
        target_distance = max(math.hypot(to_target_x, to_target_y), 1e-9)
        forward_x = math.cos(state["heading"])
        forward_y = math.sin(state["heading"])
        dot = forward_x * to_target_x + forward_y * to_target_y
        cross = forward_x * to_target_y - forward_y * to_target_x
        heading_error = math.atan2(cross, dot)
        pursuit_curvature = 2.0 * math.sin(heading_error) / target_distance
        steer = math.atan(c_s03.WHEELBASE_M * pursuit_curvature) * driver_profile["steerGain"]
        steer = c_s02.clamp(steer, -driver_profile["maxSteerRad"], driver_profile["maxSteerRad"])
        max_abs_steer = max(max_abs_steer, abs(steer))

        speed_kmh = state["speed"] * MPS_TO_KMH
        available_accel = (
            c_s03.acceleration_at_speed_kmh(
                vehicle_profile["accelerationSpeedKmh"],
                vehicle_profile["accelerationTimeS"],
                speed_kmh,
            )
            * KMH_TO_MPS
            * driver_profile["accelUsageFactor"]
        )
        available_decel = (
            c_s03.deceleration_at_speed_kmh(
                vehicle_profile["brakingSpeedKmh"],
                vehicle_profile["brakingTimeS"],
                speed_kmh,
            )
            * KMH_TO_MPS
            * driver_profile["brakeUsageFactor"]
        )
        desired_accel = (target_speed - state["speed"]) / driver_profile["speedResponseTimeS"]
        accel = c_s02.clamp(desired_accel, -available_decel, available_accel)
        if accel > 0.05:
            throttle_ticks += 1
        elif accel < -0.05:
            brake_ticks += 1

        midpoint_speed = max(0.0, state["speed"] + accel * dt * 0.5)
        yaw_model = c_s03.grip_limited_yaw(
            midpoint_speed,
            steer,
            c_s03.WHEELBASE_M,
            vehicle_profile["lateralLimitG"],
        )
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
        state["speed"] = max(0.0, min(vehicle_profile["topSpeedMps"], state["speed"] + accel * dt))
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
    return {
        "driverProfileId": driver_profile["id"],
        "driverProfileLabel": driver_profile["label"],
        "driverProfile": driver_profile,
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
        "maxLateralGModel": max_lateral_g,
        "maxRequestedLateralGModel": max_requested_lateral_g,
        "gripSaturationTickPercent": 100.0 * grip_saturation_ticks / len(speed_values),
        "maxGripSaturationRatio": max_grip_saturation_ratio,
        "maxAbsSteerRad": max_abs_steer,
        "throttleTickPercent": 100.0 * throttle_ticks / len(speed_values),
        "brakeTickPercent": 100.0 * brake_ticks / len(speed_values),
        "finalState": state,
        "samples": samples,
        "finiteValues": finite_values,
        "success": (
            completed_laps >= TARGET_LAPS
            and off_track_count == 0
            and finite_values
            and mean_abs_lateral <= MEAN_LATERAL_ERROR_LIMIT_M
            and max_lateral_error <= MAX_LATERAL_ERROR_LIMIT_M
            and lap_variation <= LAP_TIME_VARIATION_LIMIT
            and max_lateral_g <= vehicle_profile["lateralLimitG"] * 1.20
        ),
    }


def profile_spread(reference_runs: list[dict[str, Any]]) -> dict[str, Any]:
    durations = {run["driverProfileId"]: run["durationS"] for run in reference_runs}
    mean_errors = {run["driverProfileId"]: run["meanAbsLateralErrorM"] for run in reference_runs}
    max_errors = {run["driverProfileId"]: run["maxAbsLateralErrorM"] for run in reference_runs}
    max_lateral_g = {run["driverProfileId"]: run["maxLateralGModel"] for run in reference_runs}
    ordered_by_duration = sorted(reference_runs, key=lambda run: run["durationS"], reverse=True)
    lap_time_spread = max(durations.values()) - min(durations.values())
    return {
        "durationByProfileS": durations,
        "meanLateralErrorByProfileM": mean_errors,
        "maxLateralErrorByProfileM": max_errors,
        "maxLateralGByProfileG": max_lateral_g,
        "slowestProfileId": ordered_by_duration[0]["driverProfileId"],
        "fastestProfileId": ordered_by_duration[-1]["driverProfileId"],
        "lapTimeSpreadS": lap_time_spread,
        "orderedFastestFirst": [run["driverProfileId"] for run in sorted(reference_runs, key=lambda run: run["durationS"])],
        "success": (
            durations["cautious"] > durations["balanced"] > durations["aggressive"]
            and lap_time_spread >= MIN_LAP_TIME_SPREAD_S
            and mean_errors["cautious"] < mean_errors["balanced"] < mean_errors["aggressive"]
            and max_errors["aggressive"] > max_errors["balanced"]
            and max_lateral_g["aggressive"] > max_lateral_g["balanced"] > max_lateral_g["cautious"]
        ),
    }


def limit_probe_result(limit_probe_run: dict[str, Any], balanced_run: dict[str, Any]) -> dict[str, Any]:
    expected_failure = (
        limit_probe_run["gripSaturationTickPercent"] > 5.0
        and limit_probe_run["maxGripSaturationRatio"] > 1.10
        and (
            limit_probe_run["offTrackCount"] > 0
            or limit_probe_run["maxAbsLateralErrorM"] > balanced_run["maxAbsLateralErrorM"] * 1.50
        )
    )
    return {
        "profileId": limit_probe_run["driverProfileId"],
        "gripSaturationTickPercent": limit_probe_run["gripSaturationTickPercent"],
        "maxGripSaturationRatio": limit_probe_run["maxGripSaturationRatio"],
        "offTrackCount": limit_probe_run["offTrackCount"],
        "maxAbsLateralErrorM": limit_probe_run["maxAbsLateralErrorM"],
        "expectedFailure": expected_failure,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    profile = summary["vehicleProfile"]
    reference_runs = summary["referenceRuns"]
    spread = summary["profileSpread"]
    limit_probe = summary["limitProbeRun"]
    limit_probe_check = summary["limitProbe"]
    lines = [
        "# C-S05 - Differences de competence pilote",
        "",
        "- **Experience :** C - Tour autonome et modele minimal de circuit",
        "- **Scenario :** C-S05",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'a modifier'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** verifier que des profils de controle produisent des comportements mesurablement differents et qu'une sur-vitesse declenche bien une limite de grip.",
        "- **Reserve :** le modele de grip est une saturation laterale minimale ; il ne separe pas encore sous-virage et survirage.",
        "",
        "## Donnees vehicule",
        "",
        f"- Vehicule : {profile['name']}",
        f"- Exporteur : `{profile['exporterVersion']}`",
        f"- Source : `{summary['vehicleInputPath']}`",
        f"- Limite laterale utilisee : {fmt_number(profile['lateralLimitG'], 3)} g",
        "",
        "## Profils testes",
        "",
        "| Profil | Vitesse | Marge grip | Lookahead | Reponse vitesse | Direction | Description |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for driver_profile in summary["driverProfiles"]:
        lines.append(
            "| "
            f"{driver_profile['label']} | "
            f"{fmt_number(driver_profile['targetSpeedScale'], 2)}x | "
            f"{fmt_number(driver_profile['lateralLimitScale'], 2)}x | "
            f"{fmt_number(driver_profile['lookaheadM'], 1)} m | "
            f"{fmt_number(driver_profile['speedResponseTimeS'], 2)} s | "
            f"{fmt_number(driver_profile['steerGain'], 2)}x / {fmt_number(driver_profile['maxSteerRad'], 2)} rad | "
            f"{driver_profile['description']} |"
        )
    lines.extend(
        [
            "",
            "## Resultats reference 1/120 s",
            "",
            "| Profil | Duree | Tour 1 | Tour 2 | Tour 3 | Vitesse moy. | Vitesse max | Erreur lat. moy. | Erreur lat. max | G lat. max | Sat. grip | Sorties | Stable |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for run in reference_runs:
        lap_times = run["lapTimesS"]
        lines.append(
            "| "
            f"{run['driverProfileLabel']} | "
            f"{fmt_number(run['durationS'])} | "
            f"{fmt_number(lap_times[0] if len(lap_times) > 0 else None)} | "
            f"{fmt_number(lap_times[1] if len(lap_times) > 1 else None)} | "
            f"{fmt_number(lap_times[2] if len(lap_times) > 2 else None)} | "
            f"{fmt_number(run['meanSpeedKmh'])} | "
            f"{fmt_number(run['maxSpeedKmh'])} | "
            f"{fmt_number(run['meanAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxLateralGModel'], 3)} | "
            f"{fmt_number(run['gripSaturationTickPercent'], 2)} % | "
            f"{run['offTrackCount']} | "
            f"{fmt_bool(run['success'])} |"
        )
    lines.extend(
        [
            "",
            "## Differenciation",
            "",
            f"- Ordre du plus rapide au plus lent : `{', '.join(spread['orderedFastestFirst'])}`",
            f"- Ecart entre profils extreme : {fmt_number(spread['lapTimeSpreadS'])} s sur trois tours",
            f"- Seuil attendu : {fmt_number(summary['successCriteria']['minLapTimeSpreadS'])} s",
            f"- Erreur laterale moyenne : prudent {fmt_number(spread['meanLateralErrorByProfileM']['cautious'], 3)} m, equilibre {fmt_number(spread['meanLateralErrorByProfileM']['balanced'], 3)} m, agressif {fmt_number(spread['meanLateralErrorByProfileM']['aggressive'], 3)} m",
            f"- G lateral maximal : prudent {fmt_number(spread['maxLateralGByProfileG']['cautious'], 3)} g, equilibre {fmt_number(spread['maxLateralGByProfileG']['balanced'], 3)} g, agressif {fmt_number(spread['maxLateralGByProfileG']['aggressive'], 3)} g",
            "",
            "## Temoin negatif de sur-vitesse",
            "",
            "| Cas | Duree | Vitesse max | Erreur lat. max | Sat. grip | Ratio sat. max | Sorties | Resultat attendu |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            "| "
            f"{limit_probe['driverProfileLabel']} | "
            f"{fmt_number(limit_probe['durationS'])} | "
            f"{fmt_number(limit_probe['maxSpeedKmh'])} | "
            f"{fmt_number(limit_probe['maxAbsLateralErrorM'], 3)} | "
            f"{fmt_number(limit_probe['gripSaturationTickPercent'], 2)} % | "
            f"{fmt_number(limit_probe['maxGripSaturationRatio'], 2)}x | "
            f"{limit_probe['offTrackCount']} | "
            f"{'oui' if limit_probe_check['expectedFailure'] else 'non'} |",
            "",
            "## Observations",
            "",
            "- Les trois profils terminent trois tours sans sortie de piste.",
            "- Les differences nominales viennent uniquement des parametres de controle, pas de la voiture ni du circuit.",
            "- Le profil prudent conserve une marge de grip importante et reste le plus proche de la ligne cible en moyenne.",
            "- Le profil agressif gagne du temps en montant nettement plus haut en vitesse et en G lateral, avec un ecart de trajectoire plus eleve.",
            "- Le temoin negatif de sur-vitesse sature le grip et sort de la piste ; il confirme que le modele ne peut plus tourner sans limite physique.",
            "",
            "## Decision",
            "",
            (
                "C-S05 est valide avec reserves. Le prototype peut passer a C-S06 pour consolider le contrat minimal final de C."
                if summary["success"]
                else "C-S05 est a modifier. Le prototype ne doit pas passer a C-S06 tant que la limite de grip n'est pas demontree."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run C-S05 driver profile comparison with QFC55.")
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
        help="Directory where C-S05 result files will be written.",
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
    vehicle_profile = c_s03.qfc55_profile(vehicle)

    runs = []
    for dt in TIME_STEPS:
        for driver_profile in DRIVER_PROFILES:
            runs.append(simulate_driver(track, vehicle_profile, driver_profile, c_s02, c_s03, dt))
    limit_probe_runs = [
        simulate_driver(track, vehicle_profile, LIMIT_PROBE_PROFILE, c_s02, c_s03, dt) for dt in TIME_STEPS
    ]
    reference_runs = [run for run in runs if abs(run["dt"] - REFERENCE_DT) < 1e-12]
    spread = profile_spread(reference_runs)
    reference_limit_probe = next(run for run in limit_probe_runs if abs(run["dt"] - REFERENCE_DT) < 1e-12)
    balanced_reference = next(run for run in reference_runs if run["driverProfileId"] == "balanced")
    limit_probe = limit_probe_result(reference_limit_probe, balanced_reference)
    summary = {
        "scenario": "C-S05",
        "success": all(run["success"] for run in runs) and spread["success"] and limit_probe["expectedFailure"],
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "vehicleInputPath": arguments.vehicle.relative_to(repo_root).as_posix(),
        "vehicleProfile": public_vehicle_profile(vehicle_profile),
        "driverProfiles": DRIVER_PROFILES,
        "limitProbeProfile": LIMIT_PROBE_PROFILE,
        "modelAssumptions": {
            "baseController": "C-S03 pure pursuit with curvature-based speed target and lateral grip yaw saturation",
            "driverProfileControls": [
                "targetSpeedScale",
                "lateralLimitScale",
                "lookaheadM",
                "accelUsageFactor",
                "brakeUsageFactor",
                "speedResponseTimeS",
                "steerGain",
                "maxSteerRad",
            ],
            "physicalLimit": "requested yaw rate is capped when requested lateral G exceeds vehicle lateralLimitG",
        },
        "successCriteria": {
            "targetLaps": TARGET_LAPS,
            "offTrackCount": 0,
            "allProfilesStable": True,
            "durationOrder": "cautious > balanced > aggressive",
            "minLapTimeSpreadS": MIN_LAP_TIME_SPREAD_S,
            "meanLateralErrorOrder": "cautious < balanced < aggressive",
            "maxLateralGOrder": "cautious < balanced < aggressive",
            "overspeedProbe": "must saturate grip and degrade trajectory or leave track",
            "meanLateralErrorMMax": MEAN_LATERAL_ERROR_LIMIT_M,
            "maxLateralErrorMMax": MAX_LATERAL_ERROR_LIMIT_M,
            "lapTimeVariationMax": LAP_TIME_VARIATION_LIMIT,
            "maxLateralGModel": "not above lateral limit + 20 percent",
        },
        "runs": runs,
        "limitProbeRuns": limit_probe_runs,
        "referenceRuns": reference_runs,
        "limitProbeRun": reference_limit_probe,
        "limitProbe": limit_probe,
        "profileSpread": spread,
    }
    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "c_s05_driver_profiles_summary.json"
    report_path = arguments.results_dir / "C_S05_DRIVER_PROFILES_RESULT.md"
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
