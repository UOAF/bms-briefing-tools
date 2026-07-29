#!/usr/bin/env python3
"""Render a slide-ready enemy air-threat axis map from active squadron origins."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from render_bms_package_map import (
    MAP_GRID_SIZE,
    TEXT,
    Projector,
    draw_arrowhead,
    draw_scale_and_north,
    draw_text_box,
    expand_crop_to_aspect,
    grid_to_map_px,
    load_font,
    open_base_map,
    parse_aspect_ratio,
)
from synthesize_bms_briefing import (
    active_squadron,
    action_label,
    compass_sector,
    enemy_category,
    enemy_owner_ids,
    equipment_summary,
    grid_distance_nm,
    load_object_catalog,
    resolve_unit_class,
    safe_float,
    safe_int,
)


FIGHTER_TOKENS = (
    "f-",
    "j-",
    "mig-",
    "mirage",
    "rafale",
    "su-27",
    "su-30",
    "su-33",
    "su-35",
    "su-57",
)
STRIKE_TOKENS = (
    "a-",
    "q-",
    "su-7",
    "su-17",
    "su-22",
    "su-24",
    "su-25",
    "su-34",
    "su-39",
    "il-28",
)
EXCLUDED_TOKENS = (
    "awacs",
    "e-3",
    "e-2",
    "kc-",
    "il-76",
    "il-78",
    "mi-8",
    "mi-26",
)
TACTICAL_ANCHOR_ACTIONS = {
    "CAP",
    "SAD",
    "SEAD",
    "STRIKE",
    "BOMB",
    "GNDSTRIKE",
    "NAVSTRIKE",
}

RED = (235, 38, 38)
RED_DARK = (95, 0, 0)
RED_SOFT = (255, 88, 88, 210)
BLUE = (72, 190, 255)
BLUE_SOFT = (72, 190, 255, 70)
LABEL_BG = (10, 12, 13, 218)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def find_package(synthesis: dict[str, Any], package_id: int | None) -> dict[str, Any]:
    package_id = package_id or synthesis.get("focus_package_id")
    for package in synthesis.get("packages") or []:
        if safe_int(package.get("package_id"), -1) == safe_int(package_id, -2):
            return package
    raise SystemExit(f"Package {package_id} was not found in {synthesis.get('source') or 'synthesis'}.")


def unique_aircraft_names(squadron: dict[str, Any], object_catalog: dict[str, Any]) -> list[str]:
    unit_class = resolve_unit_class(squadron.get("entity_type"), object_catalog) if object_catalog else {}
    names = [item.strip() for item in equipment_summary(unit_class, limit=4).split(";") if item.strip()]
    if not names:
        for item in (squadron.get("unit_type") or {}).get("vehicle_template") or []:
            name = str(item.get("vehicle_name") or "").strip()
            if name and name not in names:
                names.append(name)
    if not names:
        fallback = (squadron.get("unit_type") or {}).get("unit_class", {}).get("name")
        if fallback:
            names.append(str(fallback))
    return names


def airframe_role(names: list[str]) -> str | None:
    text = " ".join(names).lower()
    if any(token in text for token in EXCLUDED_TOKENS):
        return None
    if any(token in text for token in FIGHTER_TOKENS):
        return "fighter"
    if any(token in text for token in STRIKE_TOKENS):
        return "strike"
    return None


def nearest_anchor(grid_x: float, grid_y: float, anchors: list[dict[str, Any]]) -> tuple[dict[str, Any], float]:
    nearest = min(
        anchors,
        key=lambda anchor: math.hypot(grid_x - safe_float(anchor.get("grid_x")), grid_y - safe_float(anchor.get("grid_y"))),
    )
    grid_dist = math.hypot(grid_x - safe_float(nearest.get("grid_x")), grid_y - safe_float(nearest.get("grid_y")))
    return nearest, grid_distance_nm(grid_dist)


def air_threat_anchor_points(package: dict[str, Any]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for flight in package.get("flights") or []:
        for waypoint in flight.get("key_waypoints") or []:
            action = action_label(waypoint.get("action"))
            if action not in TACTICAL_ANCHOR_ACTIONS:
                continue
            if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
                continue
            anchors.append(
                {
                    "kind": "flight",
                    "label": f"{flight.get('callsign')} {action} STPT {waypoint.get('index')}",
                    "grid_x": waypoint.get("grid_x"),
                    "grid_y": waypoint.get("grid_y"),
                }
            )
    for match in package.get("plan_correlation", {}).get("point_matches") or []:
        grid = match.get("campaign_grid") or {}
        if grid.get("grid_x") is None or grid.get("grid_y") is None:
            continue
        label = str(match.get("label") or match.get("display") or match.get("index") or "").strip()
        if not label or label.lower() in {"not set", "ini not set"}:
            continue
        anchors.append(
            {
                "kind": "ini",
                "label": f"INI {label}",
                "grid_x": grid.get("grid_x"),
                "grid_y": grid.get("grid_y"),
            }
        )
    return anchors


def collect_air_threat_origins(
    cam_decode: dict[str, Any],
    packages: list[dict[str, Any]],
    object_catalog: dict[str, Any],
    radius_nm: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    teams_by_id = {safe_int(team.get("who"), -1): team for team in cam_decode.get("teams") or []}
    enemies: set[int] = set()
    anchors: list[dict[str, Any]] = []
    for package in packages:
        enemies.update(enemy_owner_ids(package, teams_by_id))
        anchors.extend(air_threat_anchor_points(package))
    if not anchors:
        raise SystemExit("No package/INI anchors were found for air-threat map framing.")

    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for squadron in cam_decode.get("squadrons") or []:
        owner = safe_int(squadron.get("owner"), -1)
        if owner not in enemies or not active_squadron(squadron):
            continue
        unit_class = resolve_unit_class(squadron.get("entity_type"), object_catalog) if object_catalog else {}
        if object_catalog and enemy_category(unit_class) != "air unit":
            continue
        names = unique_aircraft_names(squadron, object_catalog)
        role = airframe_role(names)
        if not role:
            continue
        grid_x = squadron.get("x")
        grid_y = squadron.get("y")
        if grid_x is None or grid_y is None:
            continue
        grid_xf = safe_float(grid_x)
        grid_yf = safe_float(grid_y)
        anchor, distance_nm = nearest_anchor(grid_xf, grid_yf, anchors)
        if distance_nm > radius_nm:
            continue
        airbase_id = squadron.get("airbase_id")
        if isinstance(airbase_id, dict):
            airbase_id = airbase_id.get("num")
        key = (owner, round(grid_xf, 1), round(grid_yf, 1), airbase_id)
        group = grouped.setdefault(
            key,
            {
                "owner": owner,
                "team": teams_by_id.get(owner, {}).get("name") or str(owner),
                "airbase_id": airbase_id,
                "name": f"AB {airbase_id}" if airbase_id else f"Grid {grid_xf:.0f}/{grid_yf:.0f}",
                "grid_x": grid_xf,
                "grid_y": grid_yf,
                "nearest_anchor": anchor,
                "distance_nm": distance_nm,
                "roles": set(),
                "aircraft": [],
                "squadron_count": 0,
                "available_airframes": 0,
            },
        )
        group["roles"].add(role)
        group["squadron_count"] += 1
        group["available_airframes"] += safe_int((squadron.get("airframes") or {}).get("available"))
        if distance_nm < safe_float(group.get("distance_nm"), 9999.0):
            group["distance_nm"] = distance_nm
            group["nearest_anchor"] = anchor
        for name in names:
            if name not in group["aircraft"]:
                group["aircraft"].append(name)

    origins = []
    for group in grouped.values():
        item = dict(group)
        item["roles"] = sorted(group["roles"])
        origins.append(item)
    origins.sort(key=lambda item: (safe_float(item.get("distance_nm"), 9999.0), str(item.get("name") or "")))
    return origins, anchors


def crop_for_points(origins: list[dict[str, Any]], anchors: list[dict[str, Any]], margin_grid: float, aspect_ratio: str) -> tuple[int, int, int, int]:
    xs: list[float] = []
    ys: list[float] = []
    for item in [*origins, *anchors]:
        if item.get("grid_x") is None or item.get("grid_y") is None:
            continue
        x, y = grid_to_map_px(safe_float(item.get("grid_x")), safe_float(item.get("grid_y")))
        xs.append(x)
        ys.append(y)
    if not xs or not ys:
        return 0, 0, MAP_GRID_SIZE, MAP_GRID_SIZE
    crop = (
        max(0, math.floor(min(xs) - margin_grid)),
        max(0, math.floor(min(ys) - margin_grid)),
        min(MAP_GRID_SIZE, math.ceil(max(xs) + margin_grid)),
        min(MAP_GRID_SIZE, math.ceil(max(ys) + margin_grid)),
    )
    return expand_crop_to_aspect(crop, parse_aspect_ratio(aspect_ratio))


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[float, float], end: tuple[float, float], width: int) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    distance = math.hypot(dx, dy)
    if distance < 1:
        return
    shrink_start = 12
    shrink_end = 20
    sx = start[0] + dx / distance * shrink_start
    sy = start[1] + dy / distance * shrink_start
    ex = end[0] - dx / distance * shrink_end
    ey = end[1] - dy / distance * shrink_end
    draw.line((sx, sy, ex, ey), fill=(80, 0, 0, 170), width=width + 6)
    draw.line((sx, sy, ex, ey), fill=RED_SOFT, width=width)
    draw_arrowhead(draw, (sx, sy), (ex, ey), RED, size=22)


def label_text(origin: dict[str, Any]) -> str:
    aircraft = ", ".join(origin.get("aircraft") or [])
    if len(aircraft) > 42:
        aircraft = aircraft[:39].rstrip() + "..."
    return f"{origin.get('name')} | {aircraft}"


def draw_air_threat_map(args: argparse.Namespace) -> Path:
    syntheses = [load_json(path) for path in args.synthesis]
    if args.package_id:
        package_ids = args.package_id
    else:
        package_ids = [safe_int(synthesis.get("focus_package_id"), 0) for synthesis in syntheses]
    if len(package_ids) == 1 and len(syntheses) > 1:
        package_ids = package_ids * len(syntheses)
    if len(package_ids) != len(syntheses):
        raise SystemExit("Pass one --package-id per --synthesis, or omit --package-id to use each focus package.")

    packages = [find_package(synthesis, package_id) for synthesis, package_id in zip(syntheses, package_ids)]
    cam_decode = load_json(args.cam_decode)
    object_catalog = load_object_catalog(args.object_dir) if args.object_dir else {}
    origins, anchors = collect_air_threat_origins(cam_decode, packages, object_catalog, args.radius_nm)
    if not origins:
        raise SystemExit(f"No active enemy fighter/strike squadron origins found within {args.radius_nm:g} NM.")

    crop = crop_for_points(origins, anchors, args.margin_grid, args.aspect_ratio)
    base, source_scale_x, source_scale_y, _ = open_base_map(args.map_source or (args.campaign_dir / "Korea.tm"))
    source_crop = (
        max(0, math.floor(crop[0] * source_scale_x)),
        max(0, math.floor(crop[1] * source_scale_y)),
        min(base.width, math.ceil(crop[2] * source_scale_x)),
        min(base.height, math.ceil(crop[3] * source_scale_y)),
    )
    crop_image = base.crop(source_crop).convert("RGBA")
    if hasattr(base, "close"):
        base.close()
    map_width = (crop[2] - crop[0]) * args.scale
    map_height = (crop[3] - crop[1]) * args.scale
    map_image = crop_image.resize((map_width, map_height), Image.Resampling.BICUBIC)

    overlay = Image.new("RGBA", (map_width, map_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    projector = Projector(crop, args.scale)
    title_font = load_font(max(20, int(args.scale * 2.4)), bold=True)
    label_font = load_font(max(15, int(args.scale * 1.45)), bold=True)
    small_font = load_font(max(13, int(args.scale * 1.15)))

    anchor_points = [projector.grid(anchor.get("grid_x"), anchor.get("grid_y")) for anchor in anchors]
    ax = [point[0] for point in anchor_points]
    ay = [point[1] for point in anchor_points]
    ao_box = (min(ax) - 18, min(ay) - 18, max(ax) + 18, max(ay) + 18)
    draw.rounded_rectangle(ao_box, radius=18, outline=BLUE + (220,), width=4, fill=BLUE_SOFT)
    draw_text_box(draw, (ao_box[0] + 8, ao_box[1] - 10), "PLAYER AO", label_font, fill=BLUE, bg=LABEL_BG)

    for origin in origins:
        start = projector.grid(origin.get("grid_x"), origin.get("grid_y"))
        target_anchor = origin.get("nearest_anchor") or anchors[0]
        end = projector.grid(target_anchor.get("grid_x"), target_anchor.get("grid_y"))
        draw_arrow(draw, start, end, width=max(5, args.scale // 2))

    label_offsets = [(16, -34), (16, 16), (-16, -34), (-16, 16), (24, -4), (-24, -4)]
    for index, origin in enumerate(origins):
        xy = projector.grid(origin.get("grid_x"), origin.get("grid_y"))
        radius = max(9, args.scale)
        draw.rectangle(
            (xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius),
            fill=RED + (245,),
            outline=(255, 245, 245, 255),
            width=2,
        )
        dx, dy = label_offsets[index % len(label_offsets)]
        anchor = "la" if dx >= 0 else "ra"
        draw_text_box(draw, (xy[0] + dx, xy[1] + dy), label_text(origin), label_font, fill=TEXT, bg=LABEL_BG, anchor=anchor)
        meta = f"{compass_sector(math.degrees(math.atan2(safe_float(origin['grid_x']) - safe_float(origin['nearest_anchor']['grid_x']), safe_float(origin['grid_y']) - safe_float(origin['nearest_anchor']['grid_y']))) % 360)} | {origin['distance_nm']:.0f} NM | {origin['available_airframes']} a/c"
        draw_text_box(draw, (xy[0] + dx, xy[1] + dy + 24), meta, small_font, fill=(255, 205, 205), bg=LABEL_BG, anchor=anchor)

    draw_scale_and_north(overlay, crop, args.scale, small_font)
    draw_text_box(draw, (26, 26), args.title, title_font, fill=TEXT, bg=(9, 13, 15, 225))
    draw_text_box(
        draw,
        (26, 62),
        f"Active enemy fighter/strike squadron origins within {args.radius_nm:g} NM; arrows show likely axes toward player AO",
        small_font,
        fill=(255, 220, 220),
        bg=(9, 13, 15, 205),
    )

    output = Image.alpha_composite(map_image, overlay)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.convert("RGB").save(args.out)
    return args.out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, action="append", required=True, help="Path to briefing_synthesis.json. Repeat for combined package products.")
    parser.add_argument("--package-id", type=int, action="append", help="Package ID matching each --synthesis. Defaults to each synthesis focus package.")
    parser.add_argument("--cam-decode", type=Path, required=True, help="Path to cam_decode.json.")
    parser.add_argument("--campaign-dir", type=Path, required=True, help="BMS campaign directory containing Korea.tm.")
    parser.add_argument("--object-dir", type=Path, help="Falcon object table directory for aircraft names/category filtering.")
    parser.add_argument("--map-source", type=Path, help="Override map raster path, such as 8_KTO_16k_Skyvector.png.")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG path.")
    parser.add_argument("--radius-nm", type=float, default=100.0, help="Enemy squadron origin inclusion radius from player AO anchors.")
    parser.add_argument("--margin-grid", type=float, default=24.0, help="Extra grid-cell margin around origins and player AO.")
    parser.add_argument("--scale", type=int, default=10, help="Output scale multiplier for the cropped map.")
    parser.add_argument("--aspect-ratio", default="16:9", help="Slide map-area aspect ratio. Defaults to 16:9.")
    parser.add_argument("--title", default="Enemy Air Threat Axes", help="Map title.")
    return parser.parse_args()


def main() -> None:
    out = draw_air_threat_map(parse_args())
    print(out)


if __name__ == "__main__":
    main()
