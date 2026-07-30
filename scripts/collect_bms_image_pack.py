#!/usr/bin/env python3
"""Collect generated briefing images into one flat review folder."""

from __future__ import annotations

import argparse
import json
import re
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

SLIDE_IMAGE_PRODUCTS = (
    {
        "name": "01_route_threat_map.png",
        "description": "High-level package overview from origin airbases to the target area, with route flow and threats.",
        "candidates": (
            "01_route_threat_map",
            "route_threat_map_slide",
            "route_threat_map_skyvector",
            "package_flow_overview_skyvector",
        ),
    },
    {
        "name": "02_target_area_map.png",
        "description": "Target-area package flow, named positions, enemy air axes, and low-opacity threat rings.",
        "candidates": (
            "02_target_area_map",
            "target_area_map_slide",
            "package_flow_enemy_air_axes_skyvector",
        ),
    },
    {
        "name": "03_objective_area_map.png",
        "description": "Close objective-area map for target prosecution details.",
        "candidates": (
            "03_objective_area_map",
            "objective_area_map_slide",
            "objective_area_map_skyvector",
            "package_3465_objective_area_zoom_skyvector",
            "package_1883_objective_area_zoom_skyvector",
            "objective_area_zoom_skyvector",
        ),
    },
    {
        "name": "04_weather_map.png",
        "description": "Weather review map, when available.",
        "candidates": (
            "weather_map_skyvector",
        ),
        "optional": True,
    },
)


def is_under(path: Path, parent_name: str) -> bool:
    return any(part.lower() == parent_name.lower() for part in path.parts)


def is_slide_variant_pack(path: Path) -> bool:
    return any(part.lower().startswith("slide_v") for part in path.parts)


def slide_variant_score(path: Path) -> int:
    best = -1
    for part in path.parts:
        match = re.match(r"slide_v(\d+)(?:_(\d+))?", part.lower())
        if match:
            major = int(match.group(1))
            minor = int(match.group(2) or 0)
            best = max(best, major * 1000 + minor)
    return best


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


def candidate_rank(path: Path, source_dir: Path, candidates: tuple[str, ...]) -> tuple[int, int, int, str]:
    relative = str(path.relative_to(source_dir)).lower()
    stem = path.stem.lower()
    for index, token in enumerate(candidates):
        if token in stem:
            relative_path = path.relative_to(source_dir)
            root_penalty = -10000 - slide_variant_score(relative_path) if is_slide_variant_pack(relative_path) else (0 if path.parent == source_dir else 1)
            package_penalty = 1 if "\\pkg" in relative or "/pkg" in relative else 0
            return index, root_penalty, package_penalty, relative
    return len(candidates), 9, 9, relative


def find_slide_product(source_dir: Path, candidates: tuple[str, ...]) -> Path | None:
    matches: list[Path] = []
    for path in source_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        relative = path.relative_to(source_dir)
        if is_under(relative, "assets") or is_under(relative, "image_pack"):
            continue
        if is_under(relative, "briefing_images") and not is_slide_variant_pack(relative):
            continue
        if "claude_design_pkg_" in str(relative).lower():
            continue
        stem = path.stem.lower()
        if any(token in stem for token in candidates):
            matches.append(path)
    if not matches:
        return None
    return sorted(matches, key=lambda path: candidate_rank(path, source_dir, candidates))[0]


def copy_slide_set(source_dir: Path, out_dir: Path, clean: bool) -> list[dict[str, str]]:
    if clean and out_dir.exists():
        for path in out_dir.iterdir():
            if path.is_file() and (path.suffix.lower() in IMAGE_SUFFIXES or path.name == "manifest.json"):
                path.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []
    for product in SLIDE_IMAGE_PRODUCTS:
        source = find_slide_product(source_dir, product["candidates"])
        if not source:
            if not product.get("optional"):
                print(f"Missing required slide image: {product['name']}")
            continue
        target = out_dir / product["name"]
        shutil.copy2(source, target)
        item = {
            "name": product["name"],
            "description": product["description"],
            "source": str(source.relative_to(source_dir)),
        }
        manifest.append(item)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


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
    parser.add_argument("--out-dir", type=Path, help="Flat image pack directory. Defaults to SOURCE_DIR/briefing_images for --mode slide, or SOURCE_DIR/image_pack for --mode all.")
    parser.add_argument(
        "--mode",
        choices=("slide", "all"),
        default="slide",
        help="slide writes only numbered briefing images; all preserves the previous canonical-image collection behavior.",
    )
    parser.add_argument("--include-variants", action="store_true", help="Include diagnostic/corrected/probe images.")
    parser.add_argument("--no-clean", dest="clean", action="store_false", help="Do not remove existing images from the pack first.")
    parser.set_defaults(clean=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    if not source_dir.exists():
        raise SystemExit(f"{source_dir} does not exist.")
    out_dir = (args.out_dir or (source_dir / ("briefing_images" if args.mode == "slide" else "image_pack"))).resolve()
    if args.mode == "slide":
        manifest = copy_slide_set(source_dir, out_dir, args.clean)
        for item in manifest:
            print(out_dir / item["name"])
        print(f"Collected {len(manifest)} slide image(s) into {out_dir}.")
        return

    images = collect_images(source_dir, args.include_variants)
    written = copy_images(images, source_dir, out_dir, args.clean)
    for path in written:
        print(path)
    print(f"Collected {len(written)} image(s) into {out_dir}.")


if __name__ == "__main__":
    main()
