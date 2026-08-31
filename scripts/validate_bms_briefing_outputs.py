#!/usr/bin/env python3
"""Validate player-facing BMS briefing outputs after generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image

from bms_a2a_tacan import flight_summary as deterministic_a2a_tacan_summary
from bms_milstd2525 import validate_symbol_contract


REQUIRED_IMAGES = (
    "01_route_threat_map.png",
    "02_target_area_map.png",
    "03_objective_area_map.png",
)

PLAYER_BRIEF_FORBIDDEN = (
    r"Commander context:",
    r"Unresolved target",
    r"Weather unavailable:",
    r"No FMAP sidecar",
    r"\bbriefing_read\b",
    r"No named tactical target listed",
    r"\bOkay,\s+it's time to make another briefing\b",
    r"\blet me go over\b",
    r"\bhold on,\s+let me\b",
)


def read_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def manifest_images(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [item for item in payload.get("images") or [] if isinstance(item, dict)]
    return []


def validate_brief(path: Path, package_ids: list[int]) -> list[str]:
    errors: list[str] = []
    text = read_text(path)
    for package_id in package_ids:
        if str(package_id) not in text:
            errors.append(f"{path.name} does not mention package {package_id}.")
    for pattern in PLAYER_BRIEF_FORBIDDEN:
        if re.search(pattern, text, re.I):
            errors.append(f"{path.name} contains forbidden player-facing text matching {pattern!r}.")
    return errors


def validate_manifest(out_dir: Path, max_image_mb: float) -> list[str]:
    errors: list[str] = []
    image_dir = out_dir / "briefing_images"
    manifest_path = image_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"Missing image manifest: {manifest_path}"]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = manifest_images(payload)
    by_name = {item.get("name"): item for item in manifest if isinstance(item, dict)}
    for name in REQUIRED_IMAGES:
        path = image_dir / name
        if name not in by_name:
            errors.append(f"manifest.json does not list {name}.")
        if not path.exists():
            errors.append(f"Missing briefing image {path}.")
            continue
        expected_hash = str((by_name.get(name) or {}).get("sha256") or "")
        if expected_hash and sha256_file(path) != expected_hash:
            errors.append(f"{name} does not match its manifest SHA-256.")
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_image_mb:
            errors.append(f"{name} is {size_mb:.1f} MB, above {max_image_mb:.1f} MB.")
    for item in manifest:
        name = str(item.get("name") or "")
        source = str(item.get("source") or "")
        if re.search(r"(^|[\\/])slide_v\d", source, re.I):
            errors.append(f"manifest.json points at stale variant source {source!r}.")
        if re.search(r"(^|[\\/])pkg\d+", source, re.I):
            errors.append(f"manifest.json points at package-specific source {source!r}.")
        path = image_dir / name
        if path.is_file() and path.suffix.lower() == ".png":
            with Image.open(path) as image:
                width, height = image.size
                metadata = dict(image.info)
            if name in {"01_route_threat_map.png", "02_target_area_map.png", "03_objective_area_map.png", "04_weather_map.png"}:
                if abs((width / max(height, 1)) - (16 / 9)) > 0.03:
                    errors.append(f"{name} is {width}x{height}; standard slide maps must remain 16:9 without stretching.")
                if isinstance(payload, dict) and int(payload.get("schema_version") or 0) >= 2:
                    if metadata.get("bms_pack_schema") != "2":
                        errors.append(f"{name} lacks current guarded-pack provenance metadata.")
                    if not metadata.get("bms_rendered_utc") or not metadata.get("bms_render_context_sha256"):
                        errors.append(f"{name} lacks render time or mission-context provenance.")
            if name == "04_weather_map.png" and metadata.get("bms_map_product") == "Weather Map":
                if metadata.get("bms_crop_basis") != "primary-package-flight-plans":
                    errors.append("Weather map crop is not pinned to primary-package flight-plan bounds.")
                if metadata.get("bms_support_expands_crop") != "false":
                    errors.append("Weather map allows support tracks to expand its crop.")
                try:
                    player_opacity = float(metadata.get("bms_player_route_opacity", "1"))
                except ValueError:
                    player_opacity = 1.0
                if player_opacity > 0.21:
                    errors.append(f"Weather player-route opacity is {player_opacity:.2f}; expected 0.20 or lower.")
        if "3d" in name.lower():
            path = image_dir / name
            if not path.is_file():
                errors.append(f"Missing manifest-listed 3D image {path}.")
                continue
            with Image.open(path) as image:
                profile = image.info.get("bms_3d_profile")
                compass = image.info.get("bms_3d_compass")
                friendly = image.info.get("bms_3d_friendly_approach")
                width, height = image.size
            if profile != "attack-geometry":
                errors.append(f"{name} is not tagged with the required attack-geometry profile.")
            if compass != "projected-north-east":
                errors.append(f"{name} is missing the required projected N/E compass.")
            if not friendly or friendly == "disabled" or "|" not in friendly:
                errors.append(f"{name} is missing a route-derived friendly approach pointer.")
            if abs((width / max(height, 1)) - (16 / 9)) > 0.03:
                errors.append(f"{name} is {width}x{height}, not a slide-safe 16:9 frame.")
            command_metadata = metadata.get("bms_3d_command_json")
            provenance_status = str(item.get("provenance_status") or "")
            if not command_metadata and provenance_status != "approved-existing-no-command-metadata":
                errors.append(f"{name} lacks reproducible 3D command metadata or an explicit approved-legacy provenance status.")
            if metadata.get("bms_3d_background_fill") == "true":
                errors.append(f"{name} uses post-render background fill; final 3D terrain must reach the frame natively.")
    listed = {str(item.get("name") or "") for item in manifest}
    for path in image_dir.glob("*.png"):
        if path.name not in listed:
            errors.append(f"Unmanifested PNG in canonical briefing_images: {path.name}. Move candidates/checks to diagnostics.")
    return errors


def validate_brief_sync(out_dir: Path) -> list[str]:
    generated = out_dir / "generated_briefing.md"
    combined = out_dir / "player_briefing_combined.md"
    if generated.is_file() and combined.is_file() and sha256_file(generated) != sha256_file(combined):
        return ["generated_briefing.md and player_briefing_combined.md are not synchronized."]
    return []


def validate_decoder_and_freshness(out_dir: Path, package_ids: list[int]) -> list[str]:
    errors: list[str] = []
    cam_decode_path = out_dir / "cam_decode.json"
    if not cam_decode_path.is_file():
        return [f"Missing CAM decode: {cam_decode_path}"]
    cam_decode = json.loads(cam_decode_path.read_text(encoding="utf-8"))
    provider = cam_decode.get("provider") or {}
    if str(provider.get("name") or "").lower() != "pyopencam":
        errors.append("Canonical briefing decode is not from pyopencam.")
    clock = cam_decode.get("campaign_clock") or {}
    for field in ("current_time_z", "current_time_local", "clock_base_hhmm", "clock_source"):
        if not clock.get(field):
            errors.append(f"CAM campaign clock is missing {field}.")
    cam_path_value = provider.get("cam_path")
    cam_path = Path(cam_path_value) if cam_path_value else None
    if cam_path and cam_path.is_file() and cam_decode_path.stat().st_mtime + 1 < cam_path.stat().st_mtime:
        errors.append(f"cam_decode.json is older than campaign save {cam_path}.")

    root_synthesis = out_dir / "briefing_synthesis.json"
    syntheses = [root_synthesis, *(out_dir / f"pkg{package_id}" / "briefing_synthesis.json" for package_id in package_ids)]
    syntheses = [path for path in syntheses if path.is_file()]
    if not syntheses:
        errors.append("No briefing_synthesis.json is available for freshness validation.")
    else:
        newest_input = cam_decode_path.stat().st_mtime
        context = (json.loads(root_synthesis.read_text(encoding="utf-8")).get("mission_context") or {}) if root_synthesis.is_file() else {}
        prefix = str(context.get("campaign_prefix") or out_dir.name)
        context_path = Path.cwd() / "inputs" / f"{prefix}-player-packages-context.json"
        if context_path.is_file():
            newest_input = max(newest_input, context_path.stat().st_mtime)
        for path in syntheses:
            if path.stat().st_mtime + 1 < newest_input:
                errors.append(f"{path} is older than CAM/context inputs.")
        newest_synthesis = max(path.stat().st_mtime for path in syntheses)
        for name in ("generated_briefing.md", "player_briefing_combined.md"):
            path = out_dir / name
            if path.is_file() and path.stat().st_mtime + 1 < newest_synthesis:
                errors.append(f"{name} is older than briefing synthesis.")
    return errors


def validate_render_profile_hashes(out_dir: Path) -> list[str]:
    errors: list[str] = []
    synthesis_path = out_dir / "briefing_synthesis.json"
    if not synthesis_path.is_file():
        return errors
    synthesis = json.loads(synthesis_path.read_text(encoding="utf-8"))
    context = synthesis.get("mission_context") or {}
    profiles = context.get("map_render_profiles") or {}
    context_hash = sha256_json(context)
    image_dir = out_dir / "briefing_images"
    for key, name in (("route", "01_route_threat_map.png"), ("target", "02_target_area_map.png"), ("objective", "03_objective_area_map.png"), ("weather", "04_weather_map.png")):
        path = image_dir / name
        if not path.is_file():
            continue
        with Image.open(path) as image:
            metadata = image.info
        if metadata.get("bms_pack_schema") != "2":
            continue
        if metadata.get("bms_render_context_sha256") != context_hash:
            errors.append(f"{name} was rendered from a different mission-context revision.")
        expected_profile_hash = sha256_json(profiles.get(key) or {})
        if metadata.get("bms_render_profile_sha256") != expected_profile_hash:
            errors.append(f"{name} was rendered from a different {key} map profile.")
    return errors


def weather_label(value: object) -> str:
    normalized = re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
    return normalized.removeprefix("SA")


def validate_weather_targets(out_dir: Path, package_ids: list[int]) -> list[str]:
    errors: list[str] = []
    for package_id in package_ids:
        path = out_dir / f"pkg{package_id}" / "briefing_synthesis.json"
        if not path.is_file():
            continue
        synthesis = json.loads(path.read_text(encoding="utf-8"))
        package = next(
            (item for item in synthesis.get("packages") or [] if int(item.get("package_id") or 0) == package_id),
            None,
        )
        if not package:
            errors.append(f"{path} does not contain package {package_id}.")
            continue
        expected = (package.get("human_context") or {}).get("weather_target_labels") or []
        if isinstance(expected, str):
            expected = [expected]
        if not expected:
            continue
        sample = next(
            (item for item in ((package.get("weather") or {}).get("samples") or []) if item.get("label") == "Target Area"),
            None,
        )
        if not sample:
            errors.append(f"Package {package_id} declares weather_target_labels but has no Target Area weather sample.")
            continue
        expected_set = {weather_label(item) for item in expected}
        actual_set = {weather_label(item) for item in sample.get("anchor_labels") or []}
        if actual_set != expected_set:
            errors.append(
                f"Package {package_id} weather target anchors are {sorted(actual_set)}, expected {sorted(expected_set)}."
            )
        if not str(sample.get("basis") or "").startswith("Planner-defined primary weather target anchors"):
            errors.append(f"Package {package_id} weather target fell back to a non-planner basis: {sample.get('basis')!r}.")
        overrides = (synthesis.get("mission_context") or {}).get("map_mark_overrides") or []
        points = [
            item
            for item in overrides
            if weather_label(item.get("label")) in expected_set
            and item.get("grid_x") is not None
            and item.get("grid_y") is not None
        ]
        if len(points) == len(expected_set):
            expected_x = sum(float(item["grid_x"]) for item in points) / len(points)
            expected_y = sum(float(item["grid_y"]) for item in points) / len(points)
            if abs(float(sample.get("grid_x") or 0) - expected_x) > 0.2 or abs(float(sample.get("grid_y") or 0) - expected_y) > 0.2:
                errors.append(
                    f"Package {package_id} weather TGT is grid {sample.get('grid_x')}/{sample.get('grid_y')}, "
                    f"expected anchor centroid {expected_x:.1f}/{expected_y:.1f}."
                )
    return errors


def validate_a2a_tacan(out_dir: Path, package_ids: list[int]) -> list[str]:
    errors: list[str] = []
    for package_index, package_id in enumerate(package_ids):
        path = out_dir / f"pkg{package_id}" / "briefing_synthesis.json"
        if not path.is_file():
            errors.append(f"Missing synthesis for A-A TACAN validation: {path}")
            continue
        synthesis = json.loads(path.read_text(encoding="utf-8"))
        package = next(
            (item for item in synthesis.get("packages") or [] if int(item.get("package_id") or 0) == package_id),
            None,
        )
        if not package:
            errors.append(f"{path} does not contain package {package_id} for A-A TACAN validation.")
            continue
        scheme = (synthesis.get("mission_context") or {}).get("a2a_tacan_scheme") or {}
        explicit: dict[str, str] = {}
        for item in (package.get("human_context") or {}).get("a2a_tacan_assignments") or []:
            callsign = str(item.get("callsign") or "").strip()
            channels = item.get("channels") or []
            if callsign and isinstance(channels, list):
                explicit[callsign] = " / ".join(str(channel).strip().upper() for channel in channels)
        for flight_index, flight in enumerate(package.get("flights") or []):
            callsign = str(flight.get("callsign") or "").strip()
            expected = explicit.get(callsign) or deterministic_a2a_tacan_summary(package_index, flight_index, scheme)
            actual = str(flight.get("a2a_tacan_summary") or "").strip()
            if actual != expected:
                errors.append(
                    f"Package {package_id} {callsign} A-A TACAN is {actual!r}, expected {expected!r}."
                )
    return errors


def validate_player_loadouts(out_dir: Path, package_ids: list[int]) -> list[str]:
    errors: list[str] = []
    for package_id in package_ids:
        path = out_dir / f"pkg{package_id}" / "briefing_synthesis.json"
        if not path.is_file():
            errors.append(f"Missing synthesis for player-loadout validation: {path}")
            continue
        synthesis = json.loads(path.read_text(encoding="utf-8"))
        package = next(
            (item for item in synthesis.get("packages") or [] if int(item.get("package_id") or 0) == package_id),
            None,
        )
        if not package:
            errors.append(f"{path} does not contain package {package_id} for player-loadout validation.")
            continue
        for flight in package.get("flights") or []:
            callsign = str(flight.get("callsign") or f"flight {flight.get('camp_id')}").strip()
            summary = str(flight.get("weapons_summary") or "").strip().lower()
            source = str((flight.get("weapons") or {}).get("source") or "").strip().lower()
            if not summary or summary == "not listed" or source == "not listed":
                errors.append(
                    f"Package {package_id} {callsign} has no decoded loadout; player briefs must not ship with 'not listed' weapons."
                )
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path, help="Mission output directory, e.g. outputs/740pre.")
    parser.add_argument("--package-id", type=int, action="append", required=True, help="Expected player package id. Repeat for combined ops.")
    parser.add_argument("--max-image-mb", type=float, default=20.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    errors: list[str] = []
    for name in ("generated_briefing.md", "player_briefing_combined.md"):
        errors.extend(validate_brief(out_dir / name, args.package_id))
    errors.extend(validate_brief_sync(out_dir))
    errors.extend(validate_decoder_and_freshness(out_dir, args.package_id))
    errors.extend(validate_manifest(out_dir, args.max_image_mb))
    errors.extend(validate_render_profile_hashes(out_dir))
    errors.extend(validate_symbol_contract())
    errors.extend(validate_weather_targets(out_dir, args.package_id))
    errors.extend(validate_a2a_tacan(out_dir, args.package_id))
    errors.extend(validate_player_loadouts(out_dir, args.package_id))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Validated briefing outputs in {out_dir}")


if __name__ == "__main__":
    main()
