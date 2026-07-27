#!/usr/bin/env python3
"""Run C-S03: QFC55 path following with curvature-based speed targets."""

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
LOOKAHEAD_M = 16.0
CURVATURE_LOOKAHEAD_M = 34.0
CURVATURE_SAMPLE_SPACING_M = 4.0
WHEELBASE_M = 2.5
MAX_STEER_RAD = 0.32
MAX_DURATION_S = 160.0
LATERAL_GRIP_SAFETY_FACTOR = 0.85
BRAKE_USAGE_FACTOR = 0.70
ACCEL_USAGE_FACTOR = 0.85
SPEED_RESPONSE_TIME_S = 0.85
MIN_TARGET_SPEED_MPS = 9.0
MEAN_LATERAL_ERROR_LIMIT_M = 1.50
MAX_LATERAL_ERROR_LIMIT_M = 4.75
LAP_TIME_VARIATION_LIMIT = 0.05
G = 9.80665
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


def find_graph(document: dict[str, Any], key: str) -> dict[str, Any]:
    for graph in document["rawGraphs"]:
        if graph["key"] == key:
            return graph
    raise ValueError(f"missing raw graph {key!r}")


def series_values(graph: dict[str, Any], key: str) -> list[float]:
    for series in graph["series"]:
        if series["key"] == key:
            return [float(value) for value in series["values"]]
    raise ValueError(f"{graph['key']}: missing series {key!r}")


def format_vehicle_name(document: dict[str, Any]) -> str:
    model = document["identity"]["modelName"]
    trim = document["identity"]["trimName"]
    if trim and trim not in model:
        return f"{model} - {trim}"
    return model


def acceleration_at_speed_kmh(speed_values: list[float], time_values: list[float], speed_kmh: float) -> float:
    positive_segments: list[tuple[float, float, float, float]] = []
    for index in range(1, len(speed_values)):
        previous_speed = speed_values[index - 1]
        current_speed = speed_values[index]
        previous_time = time_values[index - 1]
        current_time = time_values[index]
        delta_time = current_time - previous_time
        delta_speed = current_speed - previous_speed
        if delta_time > 0.0 and delta_speed > 0.0:
            positive_segments.append((previous_speed, current_speed, previous_time, current_time))
            if previous_speed <= speed_kmh <= current_speed:
                return delta_speed / delta_time
    if not positive_segments or speed_kmh >= max(speed_values):
        return 0.0
    previous_speed, current_speed, previous_time, current_time = positive_segments[0]
    if speed_kmh <= previous_speed:
        return (current_speed - previous_speed) / (current_time - previous_time)
    previous_speed, current_speed, previous_time, current_time = positive_segments[-1]
    return (current_speed - previous_speed) / (current_time - previous_time)


def deceleration_at_speed_kmh(speed_values: list[float], time_values: list[float], speed_kmh: float) -> float:
    for index in range(1, len(speed_values)):
        previous_speed = speed_values[index - 1]
        current_speed = speed_values[index]
        delta_time = time_values[index] - time_values[index - 1]
        if delta_time <= 0.0:
            continue
        if previous_speed >= speed_kmh >= current_speed:
            return max(0.0, (previous_speed - current_speed) / delta_time)
    if len(speed_values) < 2:
        return 0.0
    index = 1 if speed_kmh > speed_values[0] else len(speed_values) - 1
    delta_time = time_values[index] - time_values[index - 1]
    if delta_time <= 0.0:
        return 0.0
    return max(0.0, (speed_values[index - 1] - speed_values[index]) / delta_time)


def curvature_from_three_points(left: dict[str, float], center: dict[str, float], right: dict[str, float]) -> float:
    ax = center["x"] - left["x"]
    ay = center["y"] - left["y"]
    bx = right["x"] - center["x"]
    by = right["y"] - center["y"]
    a = math.hypot(ax, ay)
    b = math.hypot(bx, by)
    c = math.hypot(right["x"] - left["x"], right["y"] - left["y"])
    area2 = abs(ax * by - ay * bx)
    denominator = a * b * c
    if denominator <= 1e-9:
        return 0.0
    return 2.0 * area2 / denominator


def curvature_ahead(c_s02: Any, segments: list[Any], track_length: float, s: float) -> float:
    max_curvature = 0.0
    sample_count = max(1, math.ceil(CURVATURE_LOOKAHEAD_M / CURVATURE_SAMPLE_SPACING_M))
    for sample_index in range(sample_count + 1):
        sample_s = s + sample_index * CURVATURE_LOOKAHEAD_M / sample_count
        left = c_s02.point_at_s(segments, track_length, sample_s - CURVATURE_SAMPLE_SPACING_M)
        center = c_s02.point_at_s(segments, track_length, sample_s)
        right = c_s02.point_at_s(segments, track_length, sample_s + CURVATURE_SAMPLE_SPACING_M)
        max_curvature = max(max_curvature, curvature_from_three_points(left, center, right))
    return max_curvature


def qfc55_profile(document: dict[str, Any]) -> dict[str, Any]:
    acceleration = find_graph(document, "AccelerationToTopSpeed")
    braking = find_graph(document, "Braking")
    speed = series_values(acceleration, "Speed")
    accel_time = series_values(acceleration, "Time")
    braking_speed = series_values(braking, "Speed")
    braking_time = series_values(braking, "Time")
    front_grip = series_values(acceleration, "FrontGripG")
    rear_grip = series_values(acceleration, "RearGripG")
    grip_proxy = [max(0.0, front) + max(0.0, rear) for front, rear in zip(front_grip, rear_grip)]
    grip_proxy_max = max(grip_proxy)
    return {
        "name": format_vehicle_name(document),
        "exporterVersion": document["source"]["exporterVersion"],
        "topSpeedKmh": max(speed),
        "topSpeedMps": max(speed) * KMH_TO_MPS,
        "accelerationSpeedKmh": speed,
        "accelerationTimeS": accel_time,
        "brakingSpeedKmh": braking_speed,
        "brakingTimeS": braking_time,
        "lateralGripProxyG": grip_proxy_max,
        "lateralLimitG": grip_proxy_max * LATERAL_GRIP_SAFETY_FACTOR,
    }


def target_speed_for_curvature(profile: dict[str, Any], curvature: float) -> float:
    if curvature <= 1e-7:
        return profile["topSpeedMps"]
    lateral_limited = math.sqrt(profile["lateralLimitG"] * G / curvature)
    return max(MIN_TARGET_SPEED_MPS, min(profile["topSpeedMps"], lateral_limited))


def grip_limited_yaw(
    speed_mps: float,
    steer_rad: float,
    wheelbase_m: float,
    lateral_limit_g: float,
) -> dict[str, float | bool]:
    requested_yaw_rate = speed_mps * math.tan(steer_rad) / wheelbase_m
    if speed_mps <= 1e-6:
        return {
            "requestedYawRate": requested_yaw_rate,
            "actualYawRate": requested_yaw_rate,
            "requestedLateralG": 0.0,
            "actualLateralG": 0.0,
            "saturated": False,
            "saturationRatio": 0.0,
        }

    requested_lateral_g = abs(speed_mps * requested_yaw_rate) / G
    if requested_lateral_g <= lateral_limit_g:
        return {
            "requestedYawRate": requested_yaw_rate,
            "actualYawRate": requested_yaw_rate,
            "requestedLateralG": requested_lateral_g,
            "actualLateralG": requested_lateral_g,
            "saturated": False,
            "saturationRatio": 0.0,
        }

    actual_yaw_rate = math.copysign(lateral_limit_g * G / speed_mps, requested_yaw_rate)
    return {
        "requestedYawRate": requested_yaw_rate,
        "actualYawRate": actual_yaw_rate,
        "requestedLateralG": requested_lateral_g,
        "actualLateralG": lateral_limit_g,
        "saturated": True,
        "saturationRatio": requested_lateral_g / lateral_limit_g if lateral_limit_g > 0.0 else math.inf,
    }


def simulate(
    track: dict[str, Any],
    profile: dict[str, Any],
    c_s02: Any,
    dt: float,
    sample_interval_s: float = 5.0,
) -> dict[str, Any]:
    points = c_s02.build_points(track)
    segments, track_length = c_s02.build_segments(points)
    start = c_s02.point_at_s(segments, track_length, 0.0)
    state = {
        "time": 0.0,
        "x": start["x"],
        "y": start["y"],
        "heading": start["heading"],
        "speed": MIN_TARGET_SPEED_MPS,
    }
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

        lateral_abs = abs(projection["lateral"])
        lateral_abs_values.append(lateral_abs)
        max_lateral_error = max(max_lateral_error, lateral_abs)
        if lateral_abs > c_s02.track_limit_for_lateral(projection):
            off_track_count += 1

        lookahead_curvature = curvature_ahead(c_s02, segments, track_length, wrapped_s)
        max_curvature = max(max_curvature, lookahead_curvature)
        target_speed = target_speed_for_curvature(profile, lookahead_curvature)
        target_speed_values.append(target_speed)
        speed_values.append(state["speed"])

        target = c_s02.point_at_s(segments, track_length, wrapped_s + LOOKAHEAD_M)
        to_target_x = target["x"] - state["x"]
        to_target_y = target["y"] - state["y"]
        target_distance = max(math.hypot(to_target_x, to_target_y), 1e-9)
        forward_x = math.cos(state["heading"])
        forward_y = math.sin(state["heading"])
        dot = forward_x * to_target_x + forward_y * to_target_y
        cross = forward_x * to_target_y - forward_y * to_target_x
        heading_error = math.atan2(cross, dot)
        pursuit_curvature = 2.0 * math.sin(heading_error) / target_distance
        steer = c_s02.clamp(math.atan(WHEELBASE_M * pursuit_curvature), -MAX_STEER_RAD, MAX_STEER_RAD)
        max_abs_steer = max(max_abs_steer, abs(steer))

        speed_kmh = state["speed"] * MPS_TO_KMH
        available_accel = (
            acceleration_at_speed_kmh(
                profile["accelerationSpeedKmh"],
                profile["accelerationTimeS"],
                speed_kmh,
            )
            * KMH_TO_MPS
            * ACCEL_USAGE_FACTOR
        )
        available_decel = (
            deceleration_at_speed_kmh(
                profile["brakingSpeedKmh"],
                profile["brakingTimeS"],
                speed_kmh,
            )
            * KMH_TO_MPS
            * BRAKE_USAGE_FACTOR
        )
        desired_accel = (target_speed - state["speed"]) / SPEED_RESPONSE_TIME_S
        accel = c_s02.clamp(desired_accel, -available_decel, available_accel)
        if accel > 0.05:
            throttle_ticks += 1
        elif accel < -0.05:
            brake_ticks += 1

        midpoint_speed = max(0.0, state["speed"] + accel * dt * 0.5)
        yaw_model = grip_limited_yaw(midpoint_speed, steer, WHEELBASE_M, profile["lateralLimitG"])
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
            samples[-1]["x"] = state["x"]
            samples[-1]["y"] = state["y"]
            samples[-1]["heading"] = state["heading"]
            next_sample_time += sample_interval_s

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
            and max_lateral_g <= profile["lateralLimitG"] * 1.05
        ),
    }


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def render_markdown(summary: dict[str, Any]) -> str:
    profile = summary["vehicleProfile"]
    lines = [
        "# C-S03 - Adaptation de vitesse par courbure",
        "",
        "- **Experience :** C - Tour autonome et modele minimal de circuit",
        "- **Scenario :** C-S03",
        f"- **Statut :** {'valide avec reserves' if summary['success'] else 'echec'}",
        f"- **Date :** {summary['generatedAtUtc']}",
        "- **Objectif :** utiliser la QFC55 pour adapter la vitesse selon la courbure de la piste canonique.",
        "- **Reserve :** la limite laterale reste derivee du proxy B-S04 `FrontGripG + RearGripG` avec facteur de securite.",
        "",
        "## Donnees vehicule",
        "",
        f"- Vehicule : {profile['name']}",
        f"- Exporteur : `{profile['exporterVersion']}`",
        f"- Source : `{summary['vehicleInputPath']}`",
        f"- Vmax courbe : {fmt_number(profile['topSpeedKmh'])} km/h",
        f"- Grip proxy max : {fmt_number(profile['lateralGripProxyG'], 3)} g",
        f"- Limite laterale utilisee : {fmt_number(profile['lateralLimitG'], 3)} g",
        f"- Acceleration : pente `AccelerationToTopSpeed.Speed/Time`",
        f"- Freinage : pente `Braking.Speed/Time`",
        "",
        "## Resultats par pas de temps",
        "",
        "| dt | Tours | Duree | Vitesse moy. | Vitesse max | Cible min | Erreur lat. moy. | Erreur lat. max | Lat. G max | Sorties | Variation tours | Stable |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for run in summary["runs"]:
        lines.append(
            "| "
            f"{fmt_number(run['dt'], 5)} | "
            f"{run['completedLaps']} | "
            f"{fmt_number(run['durationS'])} | "
            f"{fmt_number(run['meanSpeedKmh'])} | "
            f"{fmt_number(run['maxSpeedKmh'])} | "
            f"{fmt_number(run['minTargetSpeedKmh'])} | "
            f"{fmt_number(run['meanAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxAbsLateralErrorM'], 3)} | "
            f"{fmt_number(run['maxLateralGModel'], 3)} | "
            f"{run['offTrackCount']} | "
            f"{fmt_number(run['lapTimeVariation'] * 100.0, 2)} % | "
            f"{fmt_bool(run['success'])} |"
        )

    lines.extend(
        [
            "",
            "## Temps au tour",
            "",
            "| dt | Tour 1 | Tour 2 | Tour 3 | Throttle | Frein |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for run in summary["runs"]:
        lap_times = run["lapTimesS"]
        lines.append(
            "| "
            f"{fmt_number(run['dt'], 5)} | "
            f"{fmt_number(lap_times[0] if len(lap_times) > 0 else None)} | "
            f"{fmt_number(lap_times[1] if len(lap_times) > 1 else None)} | "
            f"{fmt_number(lap_times[2] if len(lap_times) > 2 else None)} | "
            f"{fmt_number(run['throttleTickPercent'], 1)} % | "
            f"{fmt_number(run['brakeTickPercent'], 1)} % |"
        )

    reference = summary["referenceRun"]
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
            f"- Lateral G modele max : {fmt_number(reference['maxLateralGModel'], 3)} g",
            "",
            "## Observations",
            "",
            "- La QFC55 utilise ses propres courbes d'acceleration et de freinage A9 pour rejoindre la vitesse cible.",
            "- La vitesse cible varie avec la courbure anticipee de la piste, sans script par virage.",
            "- Les deux pas de temps terminent trois tours sans sortie de piste.",
            "- La limite laterale reste un proxy issu de B-S04 ; elle doit etre recalibree quand le modele lateral sera mieux defini.",
            "",
            "## Decision",
            "",
            "C-S03 est valide avec reserves. Le prototype peut passer a C-S04 pour tester la recuperation apres perturbation laterale avec le meme vehicule et la meme logique de vitesse.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    repo_root = find_repo_root(Path(__file__))
    parser = argparse.ArgumentParser(description="Run C-S03 curvature speed adaptation with QFC55.")
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
        help="Directory where C-S03 result files will be written.",
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
    profile = qfc55_profile(vehicle)
    runs = [simulate(track, profile, c_s02, dt) for dt in TIME_STEPS]
    reference_run = next(run for run in runs if abs(run["dt"] - REFERENCE_DT) < 1e-12)
    public_profile = {
        "name": profile["name"],
        "exporterVersion": profile["exporterVersion"],
        "topSpeedKmh": profile["topSpeedKmh"],
        "lateralGripProxyG": profile["lateralGripProxyG"],
        "lateralLimitG": profile["lateralLimitG"],
    }
    summary = {
        "scenario": "C-S03",
        "success": all(run["success"] for run in runs),
        "generatedAtUtc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "trackInputPath": arguments.track.relative_to(repo_root).as_posix(),
        "vehicleInputPath": arguments.vehicle.relative_to(repo_root).as_posix(),
        "vehicleProfile": public_profile,
        "modelAssumptions": {
            "lateralGripProxy": "max(AccelerationToTopSpeed.FrontGripG, 0) + max(RearGripG, 0)",
            "lateralGripSafetyFactor": LATERAL_GRIP_SAFETY_FACTOR,
            "brakeUsageFactor": BRAKE_USAGE_FACTOR,
            "accelUsageFactor": ACCEL_USAGE_FACTOR,
            "curvatureLookaheadM": CURVATURE_LOOKAHEAD_M,
            "lookaheadM": LOOKAHEAD_M,
        },
        "successCriteria": {
            "targetLaps": TARGET_LAPS,
            "offTrackCount": 0,
            "meanLateralErrorMMax": MEAN_LATERAL_ERROR_LIMIT_M,
            "maxLateralErrorMMax": MAX_LATERAL_ERROR_LIMIT_M,
            "lapTimeVariationMax": LAP_TIME_VARIATION_LIMIT,
            "maxLateralGModel": "not above lateral limit + 5 percent",
        },
        "runs": runs,
        "referenceRun": reference_run,
    }

    arguments.results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = arguments.results_dir / "c_s03_curvature_speed_summary.json"
    report_path = arguments.results_dir / "C_S03_CURVATURE_SPEED_RESULT.md"
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
