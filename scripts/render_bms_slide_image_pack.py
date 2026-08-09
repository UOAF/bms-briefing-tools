#!/usr/bin/env python3
"""Render the canonical slide image pack for one or more BMS player packages."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo


PRODUCTS = (
    {
        "key": "route",
        "name": "01_route_threat_map.png",
        "description": "High-level package overview from origin airbases to the target area, with route flow and threats.",
    },
    {
        "key": "target",
        "name": "02_target_area_map.png",
        "description": "Target-area package flow, named positions, enemy air axes, and strategic rings.",
    },
    {
        "key": "objective",
        "name": "03_objective_area_map.png",
        "description": "Close objective-area map for target prosecution details.",
    },
    {
        "key": "weather",
        "name": "04_weather_map.png",
        "description": "Weather review map, when available.",
        "optional": True,
    },
)


def run(command: list[str]) -> None:
    print("> " + " ".join(f'"{part}"' if " " in part else part for part in command))
    subprocess.run(command, check=True)


def append_repeated(command: list[str], flag: str, values: list[Path | int]) -> None:
    for value in values:
        command.extend([flag, str(value)])


def append_if(command: list[str], flag: str, value: object | None) -> None:
    if value not in (None, ""):
        command.extend([flag, str(value)])


def mission_context_render_defaults(synthesis_paths: list[Path]) -> dict[str, object]:
    for path in synthesis_paths:
        try:
            synthesis = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        context = synthesis.get("mission_context") or {}
        if isinstance(context, dict):
            return context
    return {}


def optimize_png(path: Path, max_mb: float) -> None:
    if not path.exists() or path.suffix.lower() != ".png":
        return
    limit = int(max_mb * 1024 * 1024)
    if path.stat().st_size <= limit:
        return
    with Image.open(path) as image:
        pnginfo = PngInfo()
        for key, value in image.info.items():
            if isinstance(value, str):
                pnginfo.add_text(key, value)
        image.save(path, optimize=True, compress_level=9, pnginfo=pnginfo)
    if path.stat().st_size <= limit:
        return
    with Image.open(path) as image:
        pnginfo = PngInfo()
        for key, value in image.info.items():
            if isinstance(value, str):
                pnginfo.add_text(key, value)
        image = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
        image.save(path, optimize=True, compress_level=9, pnginfo=pnginfo)


def selected_product_keys(values: list[str] | None) -> set[str]:
    return set(values or [str(product["key"]) for product in PRODUCTS])


def backup_changed_products(out_dir: Path, staged: dict[str, Path], enabled: bool) -> Path | None:
    changed = {
        name: candidate
        for name, candidate in staged.items()
        if (out_dir / name).is_file() and not filecmp.cmp(out_dir / name, candidate, shallow=False)
    }
    if not changed or not enabled:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_dir = out_dir.parent / "_image_history" / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    for name in changed:
        shutil.copy2(out_dir / name, backup_dir / name)
    manifest = out_dir / "manifest.json"
    if manifest.is_file():
        shutil.copy2(manifest, backup_dir / "manifest.json")
    return backup_dir


def promote_staged_products(out_dir: Path, staged: dict[str, Path]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, candidate in staged.items():
        os.replace(candidate, out_dir / name)


def existing_extra_products(out_dir: Path) -> list[dict[str, object]]:
    """Preserve approved optional products when rebuilding the numbered 2D pack."""
    manifest = out_dir / "manifest.json"
    if not manifest.exists():
        return []
    standard_names = {str(product["name"]) for product in PRODUCTS}
    try:
        entries = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and str(entry.get("name") or "") not in standard_names
        and (out_dir / str(entry.get("source") or entry.get("name") or "")).exists()
    ]


def enemy_map_command(args: argparse.Namespace, out: Path, diagnostic_out: Path, *, kind: str) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).with_name("render_bms_enemy_air_threat_map.py")),
    ]
    append_repeated(command, "--synthesis", args.synthesis)
    append_repeated(command, "--package-id", args.package_id)
    command.extend(
        [
            "--cam-decode",
            str(args.cam_decode),
            "--campaign-dir",
            str(args.campaign_dir),
            "--out",
            str(diagnostic_out),
            "--combined-out",
            str(out),
            "--radius-nm",
            str(args.radius_nm),
            "--presentation-profile",
            "slide",
            "--combined-threat-style",
            "route-reference",
            "--combined-threat-opacity",
            "0.58" if kind == "route" else "0.42",
            "--scale",
            str(args.scale),
            "--aspect-ratio",
            args.aspect_ratio,
            "--no-show-map-title",
        ]
    )
    append_if(command, "--map-source", args.map_source)
    append_if(command, "--object-dir", args.object_dir)
    append_if(command, "--camp-obj-data", args.camp_obj_data)
    if kind == "route":
        command.extend(
            [
                "--crop-mode",
                "all",
                "--combined-crop-mode",
                "target-area",
                "--combined-margin-grid",
                str(args.route_margin_grid),
                "--combined-include-flow-origins-in-bounds",
                "--show-flow-origin-labels",
                "--combined-title",
                "Route & Threat Map",
            ]
        )
    elif kind == "target":
        command.extend(
            [
                "--crop-mode",
                "ao",
                "--combined-crop-mode",
                "target-area",
                "--combined-margin-grid",
                str(args.target_margin_grid),
                "--combined-title",
                "Target Area Map",
            ]
        )
    elif kind == "objective":
        command.extend(
            [
                "--crop-mode",
                "ao",
                "--combined-crop-mode",
                "objective-area",
                "--combined-objective-margin-grid",
                str(args.objective_margin_grid),
                "--combined-objective-north-bound-label",
                args.objective_north_bound_label,
                "--combined-objective-north-padding-nm",
                str(args.objective_north_padding_nm),
                "--combined-title",
                "Objective Area Map",
                "--no-show-combined-flow-labels",
            ]
        )
        if args.objective_crop_labels:
            command.extend(["--combined-crop-labels", *args.objective_crop_labels])
            command.extend(
                [
                    "--combined-crop-label-margin-grid",
                    str(args.objective_crop_label_margin_grid),
                ]
            )
        if args.objective_crop_top_fraction:
            command.extend(["--combined-objective-crop-top-fraction", str(args.objective_crop_top_fraction)])
    return command


def render_weather(args: argparse.Namespace, out: Path) -> bool:
    command = [
        sys.executable,
        str(Path(__file__).with_name("render_bms_weather_map.py")),
    ]
    append_repeated(command, "--synthesis", args.synthesis)
    append_repeated(command, "--package-id", args.package_id)
    command.extend([
        "--cam-decode",
        str(args.cam_decode),
        "--campaign-dir",
        str(args.campaign_dir),
        "--out",
        str(out),
        "--scale",
        str(max(5, args.scale // 2)),
        "--aspect-ratio",
        args.aspect_ratio,
        "--no-show-footer",
        "--weather-alpha",
        "132",
        "--player-route-opacity",
        "0.20",
        "--ao-label",
        "PACKAGE AO",
        "--weather-label-font-size",
        "42",
        "--ao-label-font-size",
        "44",
        "--ini-label-font-size",
        "44",
        "--route-label-font-size",
        "32",
        "--scale-label-font-size",
        "44",
    ])
    append_if(command, "--map-source", args.map_source)
    if args.feet_per_grid is not None:
        command.extend(["--feet-per-grid", str(args.feet_per_grid)])
    try:
        run(command)
    except subprocess.CalledProcessError:
        return False
    return out.exists()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, action="append", required=True, help="Package synthesis path. Repeat in package order.")
    parser.add_argument("--package-id", type=int, action="append", required=True, help="Package id matching each synthesis. Repeat in package order.")
    parser.add_argument("--cam-decode", type=Path, required=True)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True, help="Canonical briefing_images directory.")
    parser.add_argument("--object-dir", type=Path)
    parser.add_argument("--camp-obj-data", type=Path)
    parser.add_argument("--map-source", type=Path)
    parser.add_argument("--feet-per-grid", type=float)
    parser.add_argument("--radius-nm", type=float, default=100.0)
    parser.add_argument("--scale", type=int, default=9)
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--route-margin-grid", type=float, default=18.0)
    parser.add_argument("--target-margin-grid", type=float, default=12.0)
    parser.add_argument("--objective-margin-grid", type=float, default=6.0)
    parser.add_argument("--objective-crop-labels", nargs="*", default=[])
    parser.add_argument("--objective-crop-label-margin-grid", type=float)
    parser.add_argument("--objective-north-bound-label", default="")
    parser.add_argument("--objective-north-padding-nm", type=float, default=0.0)
    parser.add_argument("--objective-crop-top-fraction", type=float, default=0.0)
    parser.add_argument("--max-image-mb", type=float, default=20.0)
    parser.add_argument(
        "--product",
        action="append",
        choices=[str(product["key"]) for product in PRODUCTS],
        help="Render only this product. Repeat as needed. Default: render the full 2D pack.",
    )
    parser.add_argument(
        "--backup-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Archive changed canonical images under _image_history before promotion.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.synthesis) != len(args.package_id):
        raise SystemExit("Pass one --package-id per --synthesis.")
    context_defaults = mission_context_render_defaults(args.synthesis)
    if not args.objective_crop_labels:
        labels = context_defaults.get("map_objective_crop_labels") or []
        if isinstance(labels, list):
            args.objective_crop_labels = [str(label) for label in labels if str(label).strip()]
    if args.objective_crop_label_margin_grid is None:
        args.objective_crop_label_margin_grid = float(
            context_defaults.get("map_objective_crop_label_margin_grid") or 8.0
        )
    chosen = selected_product_keys(args.product)
    extra_products = existing_extra_products(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    diagnostic_dir = args.out_dir.parent / "_map_diagnostics"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    staged: dict[str, Path] = {}
    with tempfile.TemporaryDirectory(prefix=".briefing-image-stage-", dir=args.out_dir.parent) as temp_name:
        stage_dir = Path(temp_name)
        render_specs = (
            ("route", "01_route_threat_map.png", diagnostic_dir / "enemy_air_axes_route.png"),
            ("target", "02_target_area_map.png", diagnostic_dir / "enemy_air_axes_target.png"),
            ("objective", "03_objective_area_map.png", diagnostic_dir / "enemy_air_axes_objective.png"),
        )
        for kind, name, diagnostic in render_specs:
            if kind not in chosen:
                continue
            candidate = stage_dir / name
            run(enemy_map_command(args, candidate, diagnostic, kind=kind))
            optimize_png(candidate, args.max_image_mb)
            staged[name] = candidate

        if "weather" in chosen:
            weather_candidate = stage_dir / "04_weather_map.png"
            if not render_weather(args, weather_candidate):
                raise SystemExit("Weather was selected but could not be rendered; canonical images were not changed.")
            optimize_png(weather_candidate, args.max_image_mb)
            staged[weather_candidate.name] = weather_candidate

        backup_dir = backup_changed_products(args.out_dir, staged, args.backup_existing)
        promote_staged_products(args.out_dir, staged)
        if backup_dir:
            print(f"Preserved previous canonical image(s) in {backup_dir}")

    manifest = []
    for product in PRODUCTS:
        path = args.out_dir / str(product["name"])
        if path.exists():
            manifest.append(
                {
                    "name": product["name"],
                    "description": product["description"],
                    "source": product["name"],
                }
            )
        elif not product.get("optional"):
            raise SystemExit(f"Missing required slide image: {product['name']}")
    manifest.extend(extra_products)
    manifest_temp = args.out_dir / ".manifest.json.tmp"
    manifest_temp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(manifest_temp, args.out_dir / "manifest.json")
    print(args.out_dir)


if __name__ == "__main__":
    main()
