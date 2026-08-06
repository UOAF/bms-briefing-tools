#!/usr/bin/env python3
"""Render the canonical slide image pack for one or more BMS player packages."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image


PRODUCTS = (
    {
        "name": "01_route_threat_map.png",
        "description": "High-level package overview from origin airbases to the target area, with route flow and threats.",
    },
    {
        "name": "02_target_area_map.png",
        "description": "Target-area package flow, named positions, enemy air axes, and strategic rings.",
    },
    {
        "name": "03_objective_area_map.png",
        "description": "Close objective-area map for target prosecution details.",
    },
    {
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


def optimize_png(path: Path, max_mb: float) -> None:
    if not path.exists() or path.suffix.lower() != ".png":
        return
    limit = int(max_mb * 1024 * 1024)
    if path.stat().st_size <= limit:
        return
    with Image.open(path) as image:
        image.save(path, optimize=True, compress_level=9)
    if path.stat().st_size <= limit:
        return
    with Image.open(path) as image:
        image = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
        image.save(path, optimize=True, compress_level=9)


def clean_pack(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for product in PRODUCTS:
        path = out_dir / str(product["name"])
        if path.exists():
            path.unlink()
    manifest = out_dir / "manifest.json"
    if manifest.exists():
        manifest.unlink()


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
            ]
        )
        if args.objective_crop_labels:
            command.extend(["--combined-crop-labels", *args.objective_crop_labels])
        if args.objective_crop_top_fraction:
            command.extend(["--combined-objective-crop-top-fraction", str(args.objective_crop_top_fraction)])
    return command


def render_weather(args: argparse.Namespace, out: Path) -> bool:
    primary_synthesis = args.synthesis[0]
    primary_package = args.package_id[0]
    command = [
        sys.executable,
        str(Path(__file__).with_name("render_bms_weather_map.py")),
        "--synthesis",
        str(primary_synthesis),
        "--cam-decode",
        str(args.cam_decode),
        "--campaign-dir",
        str(args.campaign_dir),
        "--package-id",
        str(primary_package),
        "--out",
        str(out),
        "--scale",
        str(max(5, args.scale // 2)),
        "--aspect-ratio",
        args.aspect_ratio,
        "--no-show-footer",
        "--weather-alpha",
        "132",
        "--ao-label",
        "PACKAGE AO",
        "--weather-label-font-size",
        "54",
        "--ao-label-font-size",
        "62",
        "--ini-label-font-size",
        "44",
        "--route-label-font-size",
        "32",
        "--scale-label-font-size",
        "44",
    ]
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
    parser.add_argument("--objective-north-bound-label", default="")
    parser.add_argument("--objective-north-padding-nm", type=float, default=0.0)
    parser.add_argument("--objective-crop-top-fraction", type=float, default=0.0)
    parser.add_argument("--max-image-mb", type=float, default=20.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.synthesis) != len(args.package_id):
        raise SystemExit("Pass one --package-id per --synthesis.")
    clean_pack(args.out_dir)
    diagnostic_dir = args.out_dir.parent / "_map_diagnostics"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    render_specs = (
        ("route", args.out_dir / "01_route_threat_map.png", diagnostic_dir / "enemy_air_axes_route.png"),
        ("target", args.out_dir / "02_target_area_map.png", diagnostic_dir / "enemy_air_axes_target.png"),
        ("objective", args.out_dir / "03_objective_area_map.png", diagnostic_dir / "enemy_air_axes_objective.png"),
    )
    for kind, out, diagnostic in render_specs:
        run(enemy_map_command(args, out, diagnostic, kind=kind))
        optimize_png(out, args.max_image_mb)

    weather_out = args.out_dir / "04_weather_map.png"
    if render_weather(args, weather_out):
        optimize_png(weather_out, args.max_image_mb)

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
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(args.out_dir)


if __name__ == "__main__":
    main()
