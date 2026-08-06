#!/usr/bin/env python3
"""Validate player-facing BMS briefing outputs after generation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_name = {item.get("name"): item for item in manifest if isinstance(item, dict)}
    for name in REQUIRED_IMAGES:
        path = image_dir / name
        if name not in by_name:
            errors.append(f"manifest.json does not list {name}.")
        if not path.exists():
            errors.append(f"Missing briefing image {path}.")
            continue
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_image_mb:
            errors.append(f"{name} is {size_mb:.1f} MB, above {max_image_mb:.1f} MB.")
    for item in manifest:
        source = str(item.get("source") or "")
        if re.search(r"(^|[\\/])slide_v\d", source, re.I):
            errors.append(f"manifest.json points at stale variant source {source!r}.")
        if re.search(r"(^|[\\/])pkg\d+", source, re.I):
            errors.append(f"manifest.json points at package-specific source {source!r}.")
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
    errors.extend(validate_manifest(out_dir, args.max_image_mb))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Validated briefing outputs in {out_dir}")


if __name__ == "__main__":
    main()
