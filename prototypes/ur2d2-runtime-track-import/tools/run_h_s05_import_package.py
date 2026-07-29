#!/usr/bin/env python3
"""Run H-S05: consolidate the UR2D2 runtime import package for simulation."""

from __future__ import annotations

import argparse
import hashlib
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
H_S02_PATH = RESULTS_DIR / "h_s02_runtime_sav_reader.json"
H_S03_PATH = RESULTS_DIR / "h_s03_simulation_geometry.json"
H_S04_PATH = RESULTS_DIR / "h_s04_runtime_overlay.json"
TRACK_PATH = RESULTS_DIR / "h_s03_track_definition_candidate.json"
PACKAGE_PATH = RESULTS_DIR / "h_s05_import_package.json"
REPORT_PATH = RESULTS_DIR / "H_S05_IMPORT_PACKAGE_RESULT.md"
C_S01_VALIDATOR_PATH = REPO_ROOT / "prototypes" / "autonomous-lap" / "tools" / "run_c_s01_track_contract.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_c_s01_validator() -> Any:
    spec = importlib.util.spec_from_file_location("c_s01_track_contract", C_S01_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load C-S01 validator from {C_S01_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def relative_or_name(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def asset_reference(path: Path, track_dir: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return {
        "path": relative_or_name(path, track_dir),
        "absolutePath": str(path.resolve()),
        "sizeBytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def validate_track(track: dict[str, Any]) -> dict[str, Any]:
    validator = load_c_s01_validator()
    errors = validator.validate_track(track)
    preprocessed = validator.preprocess_track(track) if not errors else {}
    success = (
        not errors
        and preprocessed["totalLengthM"] > validator.MIN_LOOP_LENGTH_M
        and preprocessed["minTotalWidthM"] >= validator.MIN_TOTAL_WIDTH_M
        and math.isfinite(preprocessed["maxAbsCurvature"])
    )
    return {
        "success": success,
        "errors": errors,
        "preprocessed": preprocessed,
    }


def build_package(h_s02: dict[str, Any], h_s03: dict[str, Any], h_s04: dict[str, Any], track: dict[str, Any]) -> dict[str, Any]:
    track_dir = Path(h_s02["trackDirectory"])
    track_validation = validate_track(track)
    source_files = h_s02["sourceFiles"]
    image_names = ("track.png", "track_preview.png", "grass.png", "gravel.png", "minimap.png")
    image_assets = {
        name: asset_reference(track_dir / name, track_dir)
        for name in image_names
    }
    editor_asset = asset_reference(track_dir / "track_editor.sav", track_dir)
    info_asset = asset_reference(track_dir / "track_info.data", track_dir)

    package_core = {
        "kind": "UR2D2ImportedTrackPackage",
        "schemaVersion": "0.1.0",
        "trackId": track["trackId"],
        "name": track["name"],
        "trackDefinition": track,
        "simulationExtras": {
            "pitlaneLanes": h_s03["pitlaneLanes"],
            "walls": h_s03["walls"],
            "checkpointPoints": h_s03["checkpointPoints"],
        },
        "runtimeRendering": {
            "preferredBackground": "track_preview.png",
            "coordinateMapping": {
                "source": "track_editor.sav raw editor coordinates",
                "target": "track_preview.png pixels",
                "sourceTrackPngSize": h_s04["background"]["sourceTrackPngSize"],
                "previewSize": h_s04["background"]["previewSize"],
                "scaleX": h_s04["background"]["scaleX"],
                "scaleY": h_s04["background"]["scaleY"],
                "yAxis": "down",
            },
            "strokePolicy": h_s04["strokePolicy"],
            "imageAssets": image_assets,
        },
        "sourceProvenance": {
            "trackDirectory": h_s02["trackDirectory"],
            "trackEditorSav": editor_asset,
            "trackInfoData": info_asset,
            "trackDataUsed": False,
            "sourceFeatureOffsets": {
                "track": h_s04["sourceGeometry"]["trackOffset"],
                "pitlane": h_s04["sourceGeometry"]["pitlaneOffsets"],
                "walls": h_s04["sourceGeometry"]["wallOffsets"],
            },
            "metadataStrings": h_s02["trackInfo"]["strings"],
        },
        "conversion": h_s03["conversionNotes"],
        "validation": {
            "trackDefinitionC-S01": track_validation,
            "overlayH-S04": {
                "success": h_s04["status"] == "overlay-ready",
                "status": h_s04["status"],
                "checks": h_s04["checks"],
            },
        },
        "nonGuarantees": [
            "The package references UR2D2 image assets by local path; it does not redistribute them.",
            "Pitlane and walls are outside TrackDefinition v0.1 and must be consumed from simulationExtras.",
            "Vehicle simulation and replay rendering are not performed in H-S05.",
        ],
    }
    package_core["contentSha256"] = stable_sha256(package_core)
    return package_core


def build_result(package: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "trackDefinitionValid": package["validation"]["trackDefinitionC-S01"]["success"],
        "overlayValidated": package["validation"]["overlayH-S04"]["success"],
        "trackDataNotRequired": package["sourceProvenance"]["trackDataUsed"] is False,
        "pitlaneIncluded": len(package["simulationExtras"]["pitlaneLanes"]) >= 2,
        "wallsIncluded": len(package["simulationExtras"]["walls"]) >= 1,
        "backgroundIncluded": package["runtimeRendering"]["imageAssets"]["track_preview.png"] is not None,
        "uniformPixelMapping": math.isclose(
            package["runtimeRendering"]["coordinateMapping"]["scaleX"],
            package["runtimeRendering"]["coordinateMapping"]["scaleY"],
            rel_tol=1e-9,
        ),
    }
    status = "import-package-ready-for-h-s06" if all(checks.values()) else "import-package-with-reserves"
    preprocessed = package["validation"]["trackDefinitionC-S01"].get("preprocessed", {})
    return {
        "scenario": "H-S05",
        "status": status,
        "success": status == "import-package-ready-for-h-s06",
        "generatedAtUtc": utc_now(),
        "packagePath": str((RESULTS_DIR / PACKAGE_PATH.name).resolve()),
        "packageContentSha256": package["contentSha256"],
        "checks": checks,
        "summary": {
            "trackId": package["trackId"],
            "name": package["name"],
            "centerlinePoints": len(package["trackDefinition"]["centerline"]),
            "totalLengthM": preprocessed.get("totalLengthM"),
            "minTotalWidthM": preprocessed.get("minTotalWidthM"),
            "pitlaneLaneCount": len(package["simulationExtras"]["pitlaneLanes"]),
            "wallCount": len(package["simulationExtras"]["walls"]),
            "checkpointCount": len(package["simulationExtras"]["checkpointPoints"]),
            "preferredBackground": package["runtimeRendering"]["preferredBackground"],
            "trackDataUsed": package["sourceProvenance"]["trackDataUsed"],
        },
        "nextStep": "H-S06 can run the autonomous vehicle on the packaged TrackDefinition and render it over the runtime background.",
    }


def fmt_bool(value: bool) -> str:
    return "oui" if value else "non"


def render_markdown(result: dict[str, Any], package: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# H-S05 - Paquet d'import simulation",
        "",
        "- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2",
        "- **Scénario :** H-S05",
        f"- **Statut :** {result['status']}",
        f"- **Date :** {result['generatedAtUtc']}",
        f"- **Package :** `{result['packagePath']}`",
        f"- **SHA-256 contenu :** `{result['packageContentSha256'][:16]}`",
        "",
        "## Décision du jalon",
        "",
    ]
    if result["success"]:
        lines.append("H-S05 consolide un paquet d'import prêt pour la simulation : `TrackDefinition` valide, données hors contrat utiles et mapping runtime PNG sont réunis sans dépendre de `track.data`.")
    else:
        lines.append("H-S05 produit un paquet d'import, mais certains contrôles restent en réserve.")

    lines.extend(
        [
            "",
            "## Contrôles",
            "",
            "| Contrôle | Résultat |",
            "| --- | --- |",
        ]
    )
    for key, value in result["checks"].items():
        lines.append(f"| `{key}` | {fmt_bool(value)} |")

    lines.extend(
        [
            "",
            "## Contenu",
            "",
            "| Élément | Valeur |",
            "| --- | ---: |",
            f"| Points centerline | {summary['centerlinePoints']} |",
            f"| Longueur | {summary['totalLengthM']:.3f} m |",
            f"| Largeur min | {summary['minTotalWidthM']:.3f} m |",
            f"| Voies pitlane | {summary['pitlaneLaneCount']} |",
            f"| Murs | {summary['wallCount']} |",
            f"| Checkpoints | {summary['checkpointCount']} |",
        ]
    )

    mapping = package["runtimeRendering"]["coordinateMapping"]
    lines.extend(
        [
            "",
            "## Rendu runtime",
            "",
            f"- Fond préféré : `{package['runtimeRendering']['preferredBackground']}`",
            f"- Mapping : `{mapping['source']}` -> `{mapping['target']}`",
            f"- Échelle : x `{mapping['scaleX']:.6f}`, y `{mapping['scaleY']:.6f}`",
            f"- Axe Y : `{mapping['yAxis']}`",
            "",
            "## Provenance",
            "",
            f"- `.sav` : `{package['sourceProvenance']['trackEditorSav']['path']}`",
            f"- `track_info.data` : `{package['sourceProvenance']['trackInfoData']['path']}`",
            f"- `track.data` utilisé : {fmt_bool(package['sourceProvenance']['trackDataUsed'])}",
            "",
            "## Réserves",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in package["nonGuarantees"])
    lines.extend(
        [
            "",
            "## Prochaine étape",
            "",
            result["nextStep"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h-s02", type=Path, default=H_S02_PATH)
    parser.add_argument("--h-s03", type=Path, default=H_S03_PATH)
    parser.add_argument("--h-s04", type=Path, default=H_S04_PATH)
    parser.add_argument("--track", type=Path, default=TRACK_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.results_dir.mkdir(parents=True, exist_ok=True)
    package = build_package(load_json(args.h_s02), load_json(args.h_s03), load_json(args.h_s04), load_json(args.track))
    result = build_result(package)
    write_json(args.results_dir / PACKAGE_PATH.name, package)
    write_json(args.results_dir / "h_s05_import_package_summary.json", result)
    (args.results_dir / REPORT_PATH.name).write_text(render_markdown(result, package), encoding="utf-8", newline="\n")
    print(f"H-S05 status: {result['status']}")
    print(f"Wrote: {args.results_dir / REPORT_PATH.name}")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
