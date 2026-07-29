#!/usr/bin/env python3
"""Render slide-ready Falcon BMS briefing map products for one package."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


MAP_PRODUCTS = (
    {
        "key": "overview",
        "crop_mode": "package",
        "filename": "package_{package_id}_route_threat_map_skyvector.png",
        "margin": 12.0,
        "scale": 8,
        "route_opacity": 0.62,
        "marker_opacity": 0.84,
        "label_opacity": 0.72,
        "threat_opacity": 0.36,
    },
    {
        "key": "target",
        "crop_mode": "target-area",
        "filename": "package_{package_id}_target_area_zoom_skyvector.png",
        "margin": 8.0,
        "scale": 10,
        "route_opacity": 0.56,
        "marker_opacity": 0.86,
        "label_opacity": 0.72,
        "threat_opacity": 0.34,
    },
    {
        "key": "objective",
        "crop_mode": "objective-area",
        "filename": "package_{package_id}_objective_area_zoom_skyvector.png",
        "margin": 4.0,
        "scale": 18,
        "route_opacity": 0.50,
        "marker_opacity": 0.88,
        "label_opacity": 0.72,
        "threat_opacity": 0.32,
        "objective_include_ini_lines_in_bounds": False,
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, required=True, help="Path to briefing_synthesis.json.")
    parser.add_argument("--cam-decode", type=Path, help="Optional cam_decode.json for full flight waypoint chains.")
    parser.add_argument("--campaign-dir", type=Path, required=True, help="BMS campaign directory containing Korea.tm.")
    parser.add_argument("--package-id", type=int, required=True, help="Campaign package id to render.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for rendered map PNGs.")
    parser.add_argument("--map-source", type=Path, help="Override map raster path, such as 8_KTO_16k_Skyvector.png.")
    parser.add_argument(
        "--feet-per-grid",
        type=float,
        default=None,
        help="Override grid distance scale for NM rings/scale bars. Default is BMS 4.38 real-life feet: 3280.84 ft/grid.",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="16:9",
        help="Slide map-area aspect ratio. Defaults to 16:9.",
    )
    parser.add_argument(
        "--with-footer",
        action="store_true",
        help="Keep renderer footers. By default map-set products are map-only so they fill slides cleanly.",
    )
    parser.add_argument(
        "--include-support-in-overview-bounds",
        action="store_true",
        help="Let support tracks expand the overview crop. By default they draw only if they fall inside the player-package crop.",
    )
    parser.add_argument(
        "--products",
        nargs="+",
        choices=[item["key"] for item in MAP_PRODUCTS],
        default=[item["key"] for item in MAP_PRODUCTS],
        help="Map products to render.",
    )
    parser.add_argument("--overview-margin", type=float, help="Override overview crop margin in campaign grid cells.")
    parser.add_argument("--target-margin", type=float, help="Override target-area crop margin in campaign grid cells.")
    parser.add_argument("--objective-margin", type=float, help="Override objective-area crop margin in campaign grid cells.")
    parser.add_argument("--overview-scale", type=int, help="Override overview output scale.")
    parser.add_argument("--target-scale", type=int, help="Override target-area output scale.")
    parser.add_argument("--objective-scale", type=int, help="Override objective-area output scale.")
    return parser.parse_args()


def product_value(args: argparse.Namespace, key: str, suffix: str, default: float | int) -> float | int:
    return getattr(args, f"{key}_{suffix}") or default


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    renderer = Path(__file__).with_name("render_bms_package_map.py")
    selected = set(args.products)

    for product in MAP_PRODUCTS:
        key = str(product["key"])
        if key not in selected:
            continue
        out_path = args.out_dir / str(product["filename"]).format(package_id=args.package_id)
        command = [
            sys.executable,
            str(renderer),
            "--synthesis",
            str(args.synthesis),
            "--campaign-dir",
            str(args.campaign_dir),
            "--package-id",
            str(args.package_id),
            "--out",
            str(out_path),
            "--crop-mode",
            str(product["crop_mode"]),
            "--margin-grid",
            str(product_value(args, key, "margin", product["margin"])),
            "--scale",
            str(product_value(args, key, "scale", product["scale"])),
            "--aspect-ratio",
            args.aspect_ratio,
            "--route-opacity",
            str(product["route_opacity"]),
            "--marker-opacity",
            str(product["marker_opacity"]),
            "--label-opacity",
            str(product["label_opacity"]),
            "--threat-opacity",
            str(product["threat_opacity"]),
        ]
        if args.cam_decode:
            command.extend(["--cam-decode", str(args.cam_decode)])
        if args.map_source:
            command.extend(["--map-source", str(args.map_source)])
        if args.feet_per_grid is not None:
            command.extend(["--feet-per-grid", str(args.feet_per_grid)])
        if not args.with_footer:
            command.append("--no-show-footer")
        if key == "overview" and not args.include_support_in_overview_bounds:
            command.append("--no-include-support-in-bounds")
        if key == "objective" and not product.get("objective_include_ini_lines_in_bounds", True):
            command.append("--no-objective-include-ini-lines-in-bounds")
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
