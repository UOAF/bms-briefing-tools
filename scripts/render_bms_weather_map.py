#!/usr/bin/env python3
"""Render a Falcon BMS package weather review map."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

import render_bms_package_map as package_map
from bms_weather import FMap, MAP_GRID_SIZE, weather_label
from render_bms_package_map import (
    FLIGHT_COLORS,
    MUTED,
    PANEL,
    TEXT,
    Projector,
    collect_map_bounds,
    draw_dashed_line,
    draw_flights,
    draw_ini_geometry,
    draw_scale_and_north,
    draw_support_flights,
    draw_text_box,
    find_package,
    flight_waypoints,
    expand_crop_to_aspect,
    iter_ini_line_points,
    iter_named_ini_points,
    load_font,
    load_json,
    open_base_map,
    package_raw_flights,
    parse_aspect_ratio,
    raw_flights_by_callsign,
    support_waypoints,
)


WEATHER_COLORS = {
    0: (247, 232, 84),
    1: (247, 232, 84),
    2: (80, 196, 116),
    3: (255, 158, 63),
    4: (221, 58, 73),
}

AO_OUTLINE = (230, 235, 232)
AO_FILL = (32, 34, 34)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def weather_altitude_text(value: Any, *, increment: int = 1000) -> str:
    if value is None:
        return ""
    try:
        altitude = float(value)
    except (TypeError, ValueError):
        return str(value)
    if increment > 0:
        altitude = round(altitude / increment) * increment
    return f"{int(altitude):,} ft"


def weather_cloud_base_text(sample: dict[str, Any]) -> str:
    base = sample.get("stratus_base_ft")
    if base is None:
        return "cloud base n/a"
    return f"cloud base {weather_altitude_text(base)}"


def draw_weather_cells(
    overlay: Image.Image,
    crop: tuple[int, int, int, int],
    scale: int,
    fmap: FMap,
    alpha: int = 68,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    cell_w = MAP_GRID_SIZE / fmap.size_x
    cell_h = MAP_GRID_SIZE / fmap.size_y
    for row in range(fmap.size_y):
        for col in range(fmap.size_x):
            x1 = col * cell_w
            y1 = row * cell_h
            x2 = (col + 1) * cell_w
            y2 = (row + 1) * cell_h
            if x2 < crop[0] or x1 > crop[2] or y2 < crop[1] or y1 > crop[3]:
                continue
            idx = row * fmap.size_x + col
            color = WEATHER_COLORS.get(int(fmap.basic_condition[idx]), (210, 210, 210))
            box = (
                (x1 - crop[0]) * scale,
                (y1 - crop[1]) * scale,
                (x2 - crop[0]) * scale,
                (y2 - crop[1]) * scale,
            )
            draw.rectangle(box, fill=(*color, alpha))


def draw_weather_samples(
    overlay: Image.Image,
    projector: Projector,
    samples: list[dict[str, Any]],
    font: ImageFont.ImageFont,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    marker_radius = max(18, round(getattr(font, "size", 84) * 0.28))
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for sample in samples:
        key = (round(safe_float(sample.get("grid_x"))), round(safe_float(sample.get("grid_y"))))
        grouped.setdefault(key, []).append(sample)

    short_names = {"Takeoff": "T/O", "Target Area": "TGT", "Landing": "LNDG"}
    for group_index, group in enumerate(grouped.values()):
        sample = group[0]
        xy = projector.grid(sample.get("grid_x"), sample.get("grid_y"))
        color = WEATHER_COLORS.get(int(sample.get("weather_code") or 0), (245, 245, 245))
        names = "/".join(short_names.get(str(item.get("label")), str(item.get("label"))) for item in group)
        label = f"{names}: {sample.get('condition')} {sample.get('visibility_km')}km {sample.get('wind')}"

        if "TGT" in names:
            anchor = "la"
            label_x = xy[0] + marker_radius + 34
            label_y = xy[1] + round(marker_radius * 1.45)
        else:
            anchor = "ra"
            label_x = xy[0] - marker_radius - 34
            label_y = xy[1] - round(marker_radius * 1.45)

        bbox = draw.textbbox((label_x, label_y), label, font=font, anchor=anchor)
        if bbox[2] > overlay.width - 12:
            anchor = "ra"
            label_x = xy[0] - marker_radius - 34
            bbox = draw.textbbox((label_x, label_y), label, font=font, anchor=anchor)
        if bbox[0] < 12:
            anchor = "la"
            label_x = xy[0] + marker_radius + 34
            bbox = draw.textbbox((label_x, label_y), label, font=font, anchor=anchor)
        if bbox[3] > overlay.height - 12:
            label_y -= bbox[3] - overlay.height + 12
            bbox = draw.textbbox((label_x, label_y), label, font=font, anchor=anchor)
        if bbox[1] < 12:
            label_y += 12 - bbox[1]
            bbox = draw.textbbox((label_x, label_y), label, font=font, anchor=anchor)

        pad = max(8, marker_radius // 3)
        padded_box = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
        box_center_y = (padded_box[1] + padded_box[3]) / 2
        label_edge_x = padded_box[0] if xy[0] < (padded_box[0] + padded_box[2]) / 2 else padded_box[2]
        label_edge_y = max(padded_box[1] + pad, min(padded_box[3] - pad, xy[1]))
        dx = label_edge_x - xy[0]
        dy = label_edge_y - xy[1]
        distance = max(1.0, math.hypot(dx, dy))
        marker_edge = (xy[0] + dx / distance * marker_radius, xy[1] + dy / distance * marker_radius)
        line_width = max(5, marker_radius // 4)
        draw.line((marker_edge[0], marker_edge[1], label_edge_x, label_edge_y), fill=(0, 0, 0, 220), width=line_width + 4)
        draw.line((marker_edge[0], marker_edge[1], label_edge_x, label_edge_y), fill=(255, 255, 235, 235), width=line_width)
        draw.ellipse(
            (
                label_edge_x - line_width,
                label_edge_y - line_width,
                label_edge_x + line_width,
                label_edge_y + line_width,
            ),
            fill=(255, 255, 235, 235),
            outline=(0, 0, 0, 200),
            width=max(2, line_width // 3),
        )

        draw.ellipse(
            (
                xy[0] - marker_radius - 5,
                xy[1] - marker_radius - 5,
                xy[0] + marker_radius + 5,
                xy[1] + marker_radius + 5,
            ),
            fill=(0, 0, 0, 190),
        )
        draw.ellipse(
            (
                xy[0] - marker_radius,
                xy[1] - marker_radius,
                xy[0] + marker_radius,
                xy[1] + marker_radius,
            ),
            fill=(*color, 245),
            outline=(255, 255, 255, 230),
            width=max(3, marker_radius // 5),
        )
        draw.rounded_rectangle(
            padded_box,
            radius=max(6, marker_radius // 3),
            fill=(8, 12, 14, 226),
        )
        draw.text((label_x, label_y), label, font=font, fill=TEXT, anchor=anchor)


def package_ao_points(
    flights: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    ini_points: list[dict[str, Any]],
    ini_line_points: list[dict[str, Any]],
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for _, waypoints in flights:
        for waypoint in waypoints:
            action = str(waypoint.get("action_short") or waypoint.get("action") or "").upper()
            if action in {"LAND", "REFUEL", "TANKER", "ELINT", "AWACS"}:
                continue
            if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
                continue
            points.append((safe_float(waypoint.get("grid_x")), safe_float(waypoint.get("grid_y"))))
    for point in [*ini_points, *ini_line_points]:
        grid = point.get("campaign_grid") or {}
        if grid.get("grid_x") is None or grid.get("grid_y") is None:
            continue
        points.append((safe_float(grid.get("grid_x")), safe_float(grid.get("grid_y"))))
    return points


def draw_package_ao_box(
    overlay: Image.Image,
    projector: Projector,
    ao_points: list[tuple[float, float]],
    font: ImageFont.ImageFont,
    label: str,
) -> None:
    if len(ao_points) < 2:
        return

    draw = ImageDraw.Draw(overlay, "RGBA")
    projected = [projector.grid(x, y) for x, y in ao_points]
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    font_size = getattr(font, "size", 110)
    pad = max(48, min(140, round(min(overlay.size) * 0.065)))
    left = max(8, min(xs) - pad)
    top = max(8, min(ys) - pad)
    right = min(overlay.width - 8, max(xs) + pad)
    bottom = min(overlay.height - 8, max(ys) + pad)

    draw.rounded_rectangle((left, top, right, bottom), radius=18, fill=(*AO_FILL, 18))
    corners = [(left, top), (right, top), (right, bottom), (left, bottom), (left, top)]
    line_width = max(8, round(font_size * 0.1))
    draw_dashed_line(draw, corners, (0, 0, 0, 150), width=line_width + 4, dash=line_width * 3, gap=line_width * 2)
    draw_dashed_line(draw, corners, (*AO_OUTLINE, 218), width=line_width, dash=line_width * 3, gap=line_width * 2)
    draw_text_box(
        draw,
        (left + line_width * 2, top + line_width * 2),
        label,
        font,
        fill=(238, 242, 239),
        bg=(24, 27, 27, 226),
        pad=max(10, round(font_size * 0.15)),
    )


def draw_footer(
    image: Image.Image,
    package: dict[str, Any],
    fmap: FMap,
    crop: tuple[int, int, int, int],
    map_source: Path,
    source_scale: tuple[float, float],
    footer_height: int,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = load_font(22, bold=True)
    text_font = load_font(14)
    small_font = load_font(12)
    y0 = image.height - footer_height
    draw.rectangle((0, y0, image.width, image.height), fill=PANEL)
    draw.text((18, y0 + 14), f"Package {package.get('package_id')} Weather Review", font=title_font, fill=TEXT)
    scale_x, scale_y = source_scale
    scale_note = f"{scale_x:g} px/grid" if abs(scale_x - scale_y) < 0.001 else f"{scale_x:g}x{scale_y:g} px/grid"
    draw.text(
        (18, y0 + 43),
        f"Base: {map_source.name} | source {scale_note} | crop cols {crop[0]}-{crop[2]}, rows {crop[1]}-{crop[3]}",
        font=small_font,
        fill=MUTED,
    )
    draw.text(
        (18, y0 + 65),
        f"FMAP: {fmap.size_y}x{fmap.size_x}, map wind {fmap.map_wind_heading:03d}/{round(fmap.map_wind_speed)} kt",
        font=small_font,
        fill=MUTED,
    )

    x = 18
    y = y0 + 106
    draw.text((x, y - 22), "Weather cells", font=small_font, fill=MUTED)
    for code in (1, 2, 3, 4):
        color = WEATHER_COLORS[code]
        draw.rectangle((x, y, x + 18, y + 14), fill=(*color, 170), outline=(255, 255, 255, 110))
        draw.text((x + 26, y - 2), weather_label(code), font=text_font, fill=TEXT)
        x += 120

    samples = (package.get("weather") or {}).get("samples") or []
    y = y0 + 145
    draw.text((18, y - 22), "Samples", font=small_font, fill=MUTED)
    for sample in samples[:3]:
        text = (
            f"{sample.get('label')}: {sample.get('condition')} {sample.get('cloud_cover')}, "
            f"{weather_cloud_base_text(sample)}, vis {sample.get('visibility_km')} km, "
            f"wind {sample.get('wind')}"
        )
        draw.text((18, y), text, font=text_font, fill=TEXT)
        y += 23


def render_weather_map(args: argparse.Namespace) -> Path:
    synthesis = load_json(args.synthesis)
    package = find_package(synthesis, args.package_id)
    weather = package.get("weather") or {}
    fmap_path = args.fmap or Path(weather.get("source") or "")
    if not fmap_path or not fmap_path.exists():
        raise SystemExit(f"No FMAP source found. Pass --fmap or regenerate synthesis with weather data: {fmap_path}")
    fmap = FMap.from_path(fmap_path)

    cam_decode = load_json(args.cam_decode) if args.cam_decode else None
    raw_flights = package_raw_flights(cam_decode, package)
    all_raw_flights = raw_flights_by_callsign(cam_decode)

    flights: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for flight in package.get("flights", []):
        waypoints = flight_waypoints(flight, raw_flights)
        if waypoints:
            flights.append((flight, waypoints))

    support_flights: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for support in package.get("support_flights", []):
        waypoints = support_waypoints(support, all_raw_flights)
        if waypoints:
            support_flights.append((support, waypoints))

    ini_points = iter_named_ini_points(synthesis, package)
    ini_line_points = iter_ini_line_points(package)
    bounds_flights = [*flights, *support_flights]
    crop = collect_map_bounds(
        bounds_flights,
        ini_points,
        ini_line_points,
        [],
        [],
        args.margin_grid,
        air_defense_radius_scale=0.0,
        min_size=180,
    )
    crop = expand_crop_to_aspect(crop, parse_aspect_ratio(args.aspect_ratio))

    map_source = args.map_source or (args.campaign_dir / "Korea.tm")
    base, source_scale_x, source_scale_y, _ = open_base_map(map_source)
    source_crop = (
        max(0, math.floor(crop[0] * source_scale_x)),
        max(0, math.floor(crop[1] * source_scale_y)),
        min(base.width, math.ceil(crop[2] * source_scale_x)),
        min(base.height, math.ceil(crop[3] * source_scale_y)),
    )
    crop_image = base.crop(source_crop).convert("RGBA")
    if hasattr(base, "close"):
        base.close()
    scale = args.scale
    map_width = (crop[2] - crop[0]) * scale
    map_height = (crop[3] - crop[1]) * scale
    map_image = crop_image.resize((map_width, map_height), Image.Resampling.BICUBIC)

    weather_overlay = Image.new("RGBA", (map_width, map_height), (0, 0, 0, 0))
    draw_weather_cells(weather_overlay, crop, scale, fmap, alpha=args.weather_alpha)

    route_overlay = Image.new("RGBA", (map_width, map_height), (0, 0, 0, 0))
    projector = Projector(crop, scale)
    route_label_font = load_font(args.route_label_font_size)
    ini_label_font = load_font(args.ini_label_font_size, bold=True)
    weather_label_font = load_font(args.weather_label_font_size, bold=True)
    ao_label_font = load_font(args.ao_label_font_size, bold=True)
    scale_label_font = load_font(args.scale_label_font_size, bold=True)
    flight_colors = {
        str(flight.get("callsign") or ""): FLIGHT_COLORS[index % len(FLIGHT_COLORS)]
        for index, (flight, _) in enumerate(flights)
    }
    if support_flights:
        draw_support_flights(route_overlay, projector, support_flights, route_label_font)
    draw_flights(route_overlay, projector, flights, flight_colors, route_label_font)
    route_name = (package.get("human_context") or {}).get("route_name") or "INI route"
    draw_ini_geometry(route_overlay, projector, ini_points, ini_line_points, ini_label_font, route_name=route_name)
    ao_label = args.ao_label or "PACKAGE AO"
    draw_package_ao_box(route_overlay, projector, package_ao_points(flights, ini_points, ini_line_points), ao_label_font, ao_label)
    draw_weather_samples(route_overlay, projector, weather.get("samples") or [], weather_label_font)
    draw_scale_and_north(route_overlay, crop, scale, scale_label_font)

    footer_height = 220 if args.show_footer else 0
    output = Image.new("RGBA", (map_width, map_height + footer_height), (9, 13, 15, 255))
    output.alpha_composite(map_image, (0, 0))
    output.alpha_composite(weather_overlay, (0, 0))
    output.alpha_composite(route_overlay, (0, 0))
    if args.show_footer:
        draw_footer(output, package, fmap, crop, map_source, (source_scale_x, source_scale_y), footer_height)
    output.convert("RGB").save(args.out)
    return args.out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, required=True, help="Path to briefing_synthesis.json.")
    parser.add_argument("--cam-decode", type=Path, help="Optional cam_decode.json for full flight waypoint chains.")
    parser.add_argument("--campaign-dir", type=Path, required=True, help="BMS campaign directory containing Korea.tm.")
    parser.add_argument("--package-id", type=int, required=True, help="Campaign package id to render.")
    parser.add_argument("--fmap", type=Path, help="Optional FMAP path override.")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG path.")
    parser.add_argument("--map-source", type=Path, help="Override map raster path.")
    parser.add_argument("--margin-grid", type=float, default=24.0, help="Extra grid-cell margin around plotted content.")
    parser.add_argument(
        "--feet-per-grid",
        type=float,
        default=None,
        help="Override grid distance scale for NM scale bars. Default is BMS 4.38 real-life feet: 3280.84 ft/grid.",
    )
    parser.add_argument(
        "--route-opacity",
        type=float,
        default=package_map.ROUTE_OPACITY,
        help="Opacity for flight routes, support tracks, INI lines, and assignment lanes. Range 0.0-1.0.",
    )
    parser.add_argument(
        "--marker-opacity",
        type=float,
        default=package_map.MARKER_OPACITY,
        help="Opacity for waypoint dots, INI diamonds, and airbase markers. Range 0.0-1.0.",
    )
    parser.add_argument(
        "--label-opacity",
        type=float,
        default=package_map.LABEL_OPACITY,
        help="Opacity for label background boxes. Label text remains fully readable. Range 0.0-1.0.",
    )
    parser.add_argument("--scale", type=int, default=5, help="Output scale multiplier for the cropped map.")
    parser.add_argument(
        "--aspect-ratio",
        default=None,
        help="Expand the crop to this map-area aspect ratio, for example 16:9, without clipping plotted content.",
    )
    parser.add_argument(
        "--show-footer",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include the map legend/footer. Use --no-show-footer for slide-native map-only images.",
    )
    parser.add_argument("--weather-alpha", type=int, default=112, help="Weather cell overlay alpha 0-255.")
    parser.add_argument("--ao-label", default="PACKAGE AO", help="Label for the dotted package area box.")
    parser.add_argument("--route-label-font-size", type=int, default=36, help="Full-resolution font size for route/waypoint labels.")
    parser.add_argument("--ini-label-font-size", type=int, default=54, help="Full-resolution font size for INI/PPT labels.")
    parser.add_argument("--weather-label-font-size", type=int, default=72, help="Full-resolution font size for weather sample labels.")
    parser.add_argument("--ao-label-font-size", type=int, default=76, help="Full-resolution font size for the dotted AO label.")
    parser.add_argument("--scale-label-font-size", type=int, default=52, help="Full-resolution font size for scale/north labels.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.feet_per_grid is not None:
        package_map.FEET_PER_GRID = args.feet_per_grid
    package_map.ROUTE_OPACITY = package_map.clamp_opacity(args.route_opacity, package_map.ROUTE_OPACITY)
    package_map.MARKER_OPACITY = package_map.clamp_opacity(args.marker_opacity, package_map.MARKER_OPACITY)
    package_map.LABEL_OPACITY = package_map.clamp_opacity(args.label_opacity, package_map.LABEL_OPACITY)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out = render_weather_map(args)
    print(out)


if __name__ == "__main__":
    main()
