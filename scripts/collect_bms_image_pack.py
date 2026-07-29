#!/usr/bin/env python3
"""Collect generated briefing images into one flat review folder."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


CANONICAL_TOKENS = (
    "package_flow_enemy_air_axes",
    "package_flow_overview",
    "enemy_air_threat_axes",
    "route_threat_map",
    "target_area_zoom",
    "objective_area_zoom",
    "weather_map",
)

VARIANT_TOKENS = (
    "corrected",
    "probe",
    "montage",
)

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def is_under(path: Path, parent_name: str) -> bool:
    return any(part.lower() == parent_name.lower() for part in path.parts)


def is_variant(path: Path) -> bool:
    name = path.stem.lower()
    return any(token in name for token in VARIANT_TOKENS)


def is_canonical_image(path: Path) -> bool:
    name = path.stem.lower()
    return path.suffix.lower() in IMAGE_SUFFIXES and any(token in name for token in CANONICAL_TOKENS)


def collect_images(source_dir: Path, include_variants: bool) -> list[Path]:
    images: list[Path] = []
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if is_under(path.relative_to(source_dir), "assets") and is_under(path.relative_to(source_dir), "claude_design_combined"):
            continue
        if "claude_design_pkg_" in str(path.relative_to(source_dir)).lower():
            continue
        if is_under(path.relative_to(source_dir), "image_pack"):
            continue
        if not is_canonical_image(path):
            continue
        if is_variant(path) and not include_variants:
            continue
        images.append(path)
    return images


def copy_images(images: list[Path], source_dir: Path, out_dir: Path, clean: bool) -> list[Path]:
    if clean and out_dir.exists():
        for path in out_dir.iterdir():
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                path.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    used_names: set[str] = set()
    for source in images:
        name = source.name
        if name in used_names:
            prefix = "_".join(source.relative_to(source_dir).parts[:-1])
            name = f"{prefix}_{source.name}" if prefix else source.name
        used_names.add(name)
        target = out_dir / name
        shutil.copy2(source, target)
        written.append(target)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path, help="Mission output directory, e.g. outputs/739pre.")
    parser.add_argument("--out-dir", type=Path, help="Flat image pack directory. Defaults to SOURCE_DIR/image_pack.")
    parser.add_argument("--include-variants", action="store_true", help="Include diagnostic/corrected/probe images.")
    parser.add_argument("--no-clean", dest="clean", action="store_false", help="Do not remove existing images from the pack first.")
    parser.set_defaults(clean=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    if not source_dir.exists():
        raise SystemExit(f"{source_dir} does not exist.")
    out_dir = (args.out_dir or (source_dir / "image_pack")).resolve()
    images = collect_images(source_dir, args.include_variants)
    written = copy_images(images, source_dir, out_dir, args.clean)
    for path in written:
        print(path)
    print(f"Collected {len(written)} image(s) into {out_dir}.")


if __name__ == "__main__":
    main()
