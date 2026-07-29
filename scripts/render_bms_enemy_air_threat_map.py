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
    air_defense_threat_label,
    draw_arrowhead,
    draw_scale_and_north,
    draw_text_box,
    expand_crop_to_aspect,
    grid_to_map_px,
    has_active_tracking_radar,
    is_strategic_air_defense,
    load_font,
    open_base_map,
    parse_aspect_ratio,
)
from synthesize_bms_briefing import (
    active_squadron,
    action_label,
    build_airbase_objective_refs,
    compass_sector,
    enemy_category,
    enemy_owner_ids,
    equipment_summary,
    load_objectives,
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
FLOW_BLUE = (58, 176, 255)
FLOW_BLUE_SOFT = (58, 176, 255, 190)
GREEN = (67, 238, 91)
LABEL_BG = (10, 12, 13, 218)
THREAT_RING = (255, 0, 0)
THREAT_FILL = (190, 0, 0)
THREAT_LABEL_BG = (72, 0, 0, 150)


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
        nearest_action = (match.get("nearest_route") or {}).get("action_short")
        if not label or label.lower() in {"not set", "ini not set"}:
            continue
        if label.upper().startswith("TGT ") and nearest_action not in TACTICAL_ANCHOR_ACTIONS:
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


def nearest_airbase_objective_name(
    grid_x: float,
    grid_y: float,
    airbase_objectives: list[dict[str, Any]],
    max_grid_distance: float = 12.0,
) -> str | None:
    best: tuple[float, dict[str, Any]] | None = None
    for airbase in airbase_objectives:
        if airbase.get("grid_x") is None or airbase.get("grid_y") is None:
            continue
        dist = math.hypot(grid_x - safe_float(airbase.get("grid_x")), grid_y - safe_float(airbase.get("grid_y")))
        if best is None or dist < best[0]:
            best = (dist, airbase)
    if not best or best[0] > max_grid_distance:
        return None
    name = str(best[1].get("name") or "").strip()
    return name or None


def collect_air_threat_origins(
    cam_decode: dict[str, Any],
    packages: list[dict[str, Any]],
    object_catalog: dict[str, Any],
    radius_nm: float,
    airbase_objectives: list[dict[str, Any]] | None = None,
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
        airbase_name = nearest_airbase_objective_name(grid_xf, grid_yf, airbase_objectives or [])
        key = (owner, round(grid_xf, 1), round(grid_yf, 1), airbase_id)
        group = grouped.setdefault(
            key,
            {
                "owner": owner,
                "team": teams_by_id.get(owner, {}).get("name") or str(owner),
                "airbase_id": airbase_id,
                "name": origin_name(grid_xf, grid_yf, airbase_name),
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


def crop_for_points(items: list[dict[str, Any]], margin_grid: float, aspect_ratio: str) -> tuple[int, int, int, int]:
    xs: list[float] = []
    ys: list[float] = []
    for item in items:
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


def crop_for_air_threat_map(origins: list[dict[str, Any]], anchors: list[dict[str, Any]], args: argparse.Namespace) -> tuple[int, int, int, int]:
    if args.crop_mode == "all":
        return crop_for_points([*origins, *anchors], args.margin_grid, args.aspect_ratio)
    return crop_for_points(anchors, args.ao_margin_grid, args.aspect_ratio)


def crop_for_combined_map(
    anchors: list[dict[str, Any]],
    flow_groups: list[dict[str, Any]],
    named_positions: list[dict[str, Any]],
    args: argparse.Namespace,
) -> tuple[int, int, int, int]:
    flow_points = [point for group in flow_groups for point in (group.get("points") or [])[1:]]
    return crop_for_points([*anchors, *flow_points, *named_positions], args.combined_margin_grid, args.aspect_ratio)


def point_inside_image(point: tuple[float, float], width: int, height: int, pad: float = 0.0) -> bool:
    return pad <= point[0] <= width - pad and pad <= point[1] <= height - pad


def clip_segment_to_rect(
    start: tuple[float, float],
    end: tuple[float, float],
    width: int,
    height: int,
    pad: float = 18.0,
) -> tuple[float, float]:
    if point_inside_image(start, width, height, pad):
        return start
    x0, y0 = start
    x1, y1 = end
    dx = x1 - x0
    dy = y1 - y0
    candidates: list[tuple[float, tuple[float, float]]] = []
    edges = (
        ("x", pad),
        ("x", width - pad),
        ("y", pad),
        ("y", height - pad),
    )
    for axis, value in edges:
        if axis == "x":
            if abs(dx) < 0.000001:
                continue
            t = (value - x0) / dx
            y = y0 + t * dy
            point = (value, y)
        else:
            if abs(dy) < 0.000001:
                continue
            t = (value - y0) / dy
            x = x0 + t * dx
            point = (x, value)
        if 0.0 <= t <= 1.0 and point_inside_image(point, width, height, pad - 0.5):
            candidates.append((t, point))
    if not candidates:
        return (max(pad, min(width - pad, start[0])), max(pad, min(height - pad, start[1])))
    return min(candidates, key=lambda item: item[0])[1]


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


def draw_flow_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
    width: int,
) -> None:
    if len(points) < 2:
        return
    for start, end in zip(points, points[1:]):
        draw.line((start[0], start[1], end[0], end[1]), fill=(5, 28, 38, 180), width=width + 7)
        draw.line((start[0], start[1], end[0], end[1]), fill=color + (205,), width=width)
    draw_arrowhead(draw, points[-2], points[-1], color + (235,), size=24)


def point_along_polyline(points: list[tuple[float, float]], fraction: float) -> tuple[float, float]:
    if not points:
        return (0.0, 0.0)
    if len(points) == 1:
        return points[0]
    segments = [(start, end, math.hypot(end[0] - start[0], end[1] - start[1])) for start, end in zip(points, points[1:])]
    total = sum(segment[2] for segment in segments)
    if total <= 0:
        return points[0]
    target = max(0.0, min(1.0, fraction)) * total
    traversed = 0.0
    for start, end, length in segments:
        if traversed + length >= target:
            t = 0.0 if length <= 0 else (target - traversed) / length
            return (start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t)
        traversed += length
    return points[-1]


def label_text(origin: dict[str, Any]) -> str:
    aircraft = ", ".join(origin.get("aircraft") or [])
    if len(aircraft) > 42:
        aircraft = aircraft[:39].rstrip() + "..."
    return f"{origin.get('name')} | {aircraft}"


def origin_name(grid_x: float, grid_y: float, airbase_name: str | None) -> str:
    if airbase_name:
        return airbase_name
    # Most non-airbase fighter origins in naval scenarios are carrier or offshore groups.
    return f"Offshore group {grid_x:.0f}/{grid_y:.0f}"


def edge_label_position(point: tuple[float, float], width: int, height: int) -> tuple[tuple[float, float], str]:
    margin = 22
    x = max(margin, min(width - margin, point[0]))
    y = max(margin, min(height - margin, point[1]))
    if x >= width - margin - 1:
        return (x - 8, y - 14), "ra"
    if x <= margin + 1:
        return (x + 8, y - 14), "la"
    return (x + 8, y + (24 if y < height / 2 else -14)), "la"


def collect_strategic_air_defenses(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, float, float], dict[str, Any]] = {}
    for package in packages:
        enemy = package.get("enemy_situation") or {}
        for air_defense in enemy.get("air_defense_locations") or []:
            if air_defense.get("grid_x") is None or air_defense.get("grid_y") is None:
                continue
            if not is_strategic_air_defense(air_defense) or not has_active_tracking_radar(air_defense):
                continue
            label = air_defense_threat_label(air_defense)
            key = (
                label,
                round(safe_float(air_defense.get("grid_x")), 1),
                round(safe_float(air_defense.get("grid_y")), 1),
            )
            deduped[key] = air_defense
    return sorted(
        deduped.values(),
        key=lambda item: max(safe_float(item.get("air_range")), safe_float(item.get("low_air_range"))),
        reverse=True,
    )


def draw_low_opacity_air_defense_rings(
    overlay: Image.Image,
    projector: Projector,
    air_defenses: list[dict[str, Any]],
    font: ImageFont.ImageFont,
    opacity: float,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    alpha = max(0, min(255, int(255 * opacity)))
    fill_alpha = max(0, min(60, int(alpha * 0.22)))
    label_alpha = max(80, min(180, int(alpha * 1.15)))
    for air_defense in air_defenses:
        center = projector.grid(air_defense.get("grid_x"), air_defense.get("grid_y"))
        radius_grid = max(safe_float(air_defense.get("air_range")), safe_float(air_defense.get("low_air_range")))
        if radius_grid <= 0:
            continue
        radius = projector.radius(radius_grid)
        box = (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)
        draw.ellipse(box, fill=THREAT_FILL + (fill_alpha,))
        draw.ellipse(box, outline=THREAT_RING + (alpha,), width=max(3, projector.scale // 2))
        if point_inside_image(center, overlay.width, overlay.height, 16):
            label = air_defense_threat_label(air_defense)
            draw_text_box(draw, center, label, font, fill=(255, 230, 230), bg=THREAT_LABEL_BG[:3] + (label_alpha,), pad=2, anchor="mm")


def objective_path(args: argparse.Namespace) -> Path | None:
    if args.camp_obj_data:
        return args.camp_obj_data
    candidate = args.campaign_dir / "CampObjData.XML"
    return candidate if candidate.exists() else None


def load_airbase_objectives(args: argparse.Namespace, object_catalog: dict[str, Any]) -> list[dict[str, Any]]:
    path = objective_path(args)
    if not path or not path.exists():
        return []
    return build_airbase_objective_refs(load_objectives(path), object_catalog, 0.0, 0.0)


def draw_flow_groups(
    draw: ImageDraw.ImageDraw,
    projector: Projector,
    flow_groups: list[dict[str, Any]],
    label_font: ImageFont.ImageFont,
    scale: int,
    map_width: int,
    map_height: int,
) -> None:
    labeled_origins: set[str] = set()
    origin_labels: list[tuple[tuple[float, float], str, str]] = []
    flow_labels: list[tuple[tuple[float, float], tuple[float, float], str, tuple[int, int, int]]] = []
    flow_label_specs = {
        "SEAD / DEAD Flow": (0.58, (-145, 42)),
        "Escort / BARCAP Flow": (0.53, (34, -50)),
        "East Fighter Screen": (0.66, (34, 34)),
    }
    for group in flow_groups:
        points = [projector.grid(point.get("grid_x"), point.get("grid_y")) for point in group.get("points") or []]
        if len(points) < 2:
            continue
        color = group.get("color") or FLOW_BLUE
        if len(points) >= 2 and not point_inside_image(points[0], map_width, map_height, 18):
            clipped_origin = clip_segment_to_rect(points[0], points[1], map_width, map_height, pad=18)
            points = [clipped_origin, *points[1:]]
            origin_label = str(group.get("origin_label") or "").strip()
            if origin_label and origin_label not in labeled_origins:
                label_xy, anchor = edge_label_position(clipped_origin, map_width, map_height)
                if label_xy[0] < 580 and label_xy[1] < 104:
                    label_xy = (label_xy[0], 104)
                origin_labels.append((label_xy, origin_label, anchor))
                labeled_origins.add(origin_label)
        draw_flow_arrow(draw, points, color, width=max(8, scale))
        label = str(group.get("label"))
        fraction, label_offset = flow_label_specs.get(label, (0.55, (14, -24)))
        route_point = point_along_polyline(points, fraction)
        label_xy = (route_point[0] + label_offset[0], route_point[1] + label_offset[1])
        flow_labels.append((label_xy, route_point, label, color))
    for xy, route_point, _label, color in flow_labels:
        draw.line((route_point[0], route_point[1], xy[0], xy[1]), fill=color + (190,), width=max(2, scale // 3))
        dot_radius = max(4, scale // 2)
        draw.ellipse(
            (route_point[0] - dot_radius, route_point[1] - dot_radius, route_point[0] + dot_radius, route_point[1] + dot_radius),
            fill=color + (220,),
            outline=(8, 18, 22, 230),
        )
    for xy, _route_point, label, color in flow_labels:
        draw_text_box(draw, xy, label, label_font, fill=color, bg=LABEL_BG)
    for xy, label, anchor in origin_labels:
        draw_text_box(draw, xy, label, label_font, fill=TEXT, bg=LABEL_BG, anchor=anchor)


def draw_air_threat_map(args: argparse.Namespace, *, include_flow: bool = False, output_path: Path | None = None) -> Path:
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
    airbase_objectives = load_airbase_objectives(args, object_catalog)
    origins, anchors = collect_air_threat_origins(cam_decode, packages, object_catalog, args.radius_nm, airbase_objectives)
    if not origins:
        raise SystemExit(f"No active enemy fighter/strike squadron origins found within {args.radius_nm:g} NM.")
    flow_groups = package_flow_groups(packages) if include_flow else []
    named_positions = (named_position_points(packages) + sa10_named_positions(syntheses, packages)) if include_flow else []
    air_defenses = collect_strategic_air_defenses(packages) if include_flow and args.combined_threat_rings else []

    crop = crop_for_combined_map(anchors, flow_groups, named_positions, args) if include_flow else crop_for_air_threat_map(origins, anchors, args)
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

    if air_defenses:
        draw_low_opacity_air_defense_rings(overlay, projector, air_defenses, small_font, args.combined_threat_opacity)

    anchor_points = [projector.grid(anchor.get("grid_x"), anchor.get("grid_y")) for anchor in anchors]
    ax = [point[0] for point in anchor_points]
    ay = [point[1] for point in anchor_points]
    ao_box = (min(ax) - 18, min(ay) - 18, max(ax) + 18, max(ay) + 18)
    if not include_flow:
        draw.rounded_rectangle(ao_box, radius=18, outline=BLUE + (220,), width=4, fill=BLUE_SOFT)
        draw_text_box(draw, (ao_box[0] + 8, ao_box[1] - 10), "PLAYER AO", label_font, fill=BLUE, bg=LABEL_BG)

    for origin in origins:
        target_anchor = origin.get("nearest_anchor") or anchors[0]
        end = projector.grid(target_anchor.get("grid_x"), target_anchor.get("grid_y"))
        origin_xy = projector.grid(origin.get("grid_x"), origin.get("grid_y"))
        start = clip_segment_to_rect(origin_xy, end, map_width, map_height)
        draw_arrow(draw, start, end, width=max(5, args.scale // 2))

    if include_flow:
        draw_flow_groups(draw, projector, flow_groups, label_font, args.scale, map_width, map_height)
        draw_named_positions(draw, projector, named_positions, label_font)

    label_offsets = [(16, -34), (16, 16), (-16, -34), (-16, 16), (24, -4), (-24, -4)]
    for index, origin in enumerate(origins):
        origin_xy = projector.grid(origin.get("grid_x"), origin.get("grid_y"))
        target_anchor = origin.get("nearest_anchor") or anchors[0]
        target_xy = projector.grid(target_anchor.get("grid_x"), target_anchor.get("grid_y"))
        xy = clip_segment_to_rect(origin_xy, target_xy, map_width, map_height)
        radius = max(9, args.scale)
        draw.rectangle(
            (xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius),
            fill=RED + (245,),
            outline=(255, 245, 245, 255),
            width=2,
        )
        if point_inside_image(origin_xy, map_width, map_height, 20):
            dx, dy = label_offsets[index % len(label_offsets)]
            label_xy = (xy[0] + dx, xy[1] + dy)
            anchor = "la" if dx >= 0 else "ra"
        else:
            label_xy, anchor = edge_label_position(xy, map_width, map_height)
        draw_text_box(draw, label_xy, label_text(origin), label_font, fill=TEXT, bg=LABEL_BG, anchor=anchor)
        meta = f"{compass_sector(math.degrees(math.atan2(safe_float(origin['grid_x']) - safe_float(origin['nearest_anchor']['grid_x']), safe_float(origin['grid_y']) - safe_float(origin['nearest_anchor']['grid_y']))) % 360)} | {origin['distance_nm']:.0f} NM | {origin['available_airframes']} a/c"
        meta_y = label_xy[1] + (24 if anchor == "la" else 24)
        draw_text_box(draw, (label_xy[0], meta_y), meta, small_font, fill=(255, 205, 205), bg=LABEL_BG, anchor=anchor)

    draw_scale_and_north(overlay, crop, args.scale, small_font)
    title = args.combined_title if include_flow else args.title
    subtitle = (
        f"Package flow, named positions, and active enemy fighter/strike origins within {args.radius_nm:g} NM"
        if include_flow
        else f"Active enemy fighter/strike squadron origins within {args.radius_nm:g} NM; arrows show likely axes toward player AO"
    )
    draw_text_box(draw, (26, 26), title, title_font, fill=TEXT, bg=(9, 13, 15, 225))
    draw_text_box(
        draw,
        (26, 62),
        subtitle,
        small_font,
        fill=(255, 220, 220),
        bg=(9, 13, 15, 205),
    )

    output = Image.alpha_composite(map_image, overlay)
    out = output_path or args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    output.convert("RGB").save(out)
    return out


def centroid(points: list[dict[str, Any]]) -> tuple[float, float] | None:
    clean = [point for point in points if point.get("grid_x") is not None and point.get("grid_y") is not None]
    if not clean:
        return None
    return (
        sum(safe_float(point.get("grid_x")) for point in clean) / len(clean),
        sum(safe_float(point.get("grid_y")) for point in clean) / len(clean),
    )


def flow_stage_point(flights: list[dict[str, Any]], actions: set[str]) -> dict[str, Any] | None:
    points: list[dict[str, Any]] = []
    for flight in flights:
        for waypoint in flight.get("key_waypoints") or []:
            if waypoint.get("action") in actions and waypoint.get("grid_x") is not None and waypoint.get("grid_y") is not None:
                points.append(waypoint)
    center = centroid(points)
    if not center:
        return None
    return {"grid_x": center[0], "grid_y": center[1]}


def flow_stage_occurrence(flights: list[dict[str, Any]], action: str, occurrence: int) -> dict[str, Any] | None:
    points: list[dict[str, Any]] = []
    for flight in flights:
        matches = [
            waypoint
            for waypoint in flight.get("key_waypoints") or []
            if waypoint.get("action") == action and waypoint.get("grid_x") is not None and waypoint.get("grid_y") is not None
        ]
        if len(matches) > occurrence:
            points.append(matches[occurrence])
    center = centroid(points)
    if not center:
        return None
    return {"grid_x": center[0], "grid_y": center[1]}


def short_origin_label(name: str) -> str:
    cleaned = name.replace(" International", " Intl").replace(" Airport", "").replace(" Airbase", " AB")
    return cleaned[:34].rstrip()


def flow_origin_point(flights: list[dict[str, Any]]) -> dict[str, Any] | None:
    points: list[dict[str, Any]] = []
    names: list[str] = []
    for flight in flights:
        waypoint = next(
            (
                item
                for item in flight.get("key_waypoints") or []
                if item.get("action") == "WP_TAKEOFF" and item.get("grid_x") is not None and item.get("grid_y") is not None
            ),
            None,
        )
        if not waypoint:
            continue
        points.append(waypoint)
        target = waypoint.get("target") or {}
        name = str(target.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    center = centroid(points)
    if not center:
        return None
    label = short_origin_label(names[0]) if len(names) == 1 else "Mixed Origins"
    return {"grid_x": center[0], "grid_y": center[1], "origin_label": label}


def package_flow_groups(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flights = [flight for package in packages for flight in package.get("flights") or []]
    groups: list[dict[str, Any]] = []
    sead_flights = [flight for flight in flights if str(flight.get("mission") or "").upper() in {"SEAD", "SAD"}]
    barcap_flights = [flight for flight in flights if str(flight.get("mission") or "").upper() == "BARCAP"]
    east_screen = [flight for flight in barcap_flights if "F-15" in str(flight.get("aircraft_type") or flight.get("aircraft_class") or "")]
    escort_cap = [flight for flight in barcap_flights if flight not in east_screen]

    specs = [
        ("SEAD / DEAD Flow", sead_flights, (FLOW_BLUE[0], FLOW_BLUE[1], FLOW_BLUE[2]), "sead"),
        ("Escort / BARCAP Flow", escort_cap, (98, 235, 128), "cap"),
        ("East Fighter Screen", east_screen, (255, 199, 71), "cap"),
    ]
    for label, group_flights, color, mode in specs:
        if not group_flights:
            continue
        origin = flow_origin_point(group_flights)
        if mode == "sead":
            push = flow_stage_point(group_flights, {"WP_PUSH"}) or flow_stage_point(group_flights, {"WP_TIMING"})
            stages = [
                origin,
                push,
                flow_stage_point(group_flights, {"WP_SEAD", "WP_SAD", "WP_STRIKE", "WP_BOMB", "WP_GNDSTRIKE", "WP_NAVSTRIKE"}),
            ]
        else:
            stages = [
                origin,
                flow_stage_occurrence(group_flights, "WP_CAP", 0),
                flow_stage_occurrence(group_flights, "WP_CAP", 1),
            ]
        path = [point for point in stages if point]
        if len(path) >= 2:
            groups.append({"label": label, "points": path, "color": color, "origin_label": (origin or {}).get("origin_label")})
    return groups


def named_position_points(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    points: list[dict[str, Any]] = []
    for package in packages:
        for match in package.get("plan_correlation", {}).get("point_matches") or []:
            grid = match.get("campaign_grid") or {}
            label = str(match.get("display") or match.get("label") or "").strip()
            if not label or label.upper().startswith("TGT ") or label.lower() in {"not set", "ini not set"}:
                continue
            key = label.upper()
            if key in seen or grid.get("grid_x") is None or grid.get("grid_y") is None:
                continue
            seen.add(key)
            points.append({"label": label, "grid_x": grid.get("grid_x"), "grid_y": grid.get("grid_y")})
    return points


def sa10_named_positions(syntheses: list[dict[str, Any]], packages: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    context_names = {
        str(item.get("label") or item.get("name") or "").upper(): str(item.get("name") or item.get("label") or "")
        for package in packages
        for item in (package.get("human_context") or {}).get("target_opportunities", [])
        if "SA-10" in str(item.get("label") or item.get("name") or "").upper()
    }
    if not context_names:
        return []
    tactical_points = [
        point
        for group in package_flow_groups(packages)
        for point in group.get("points") or []
        if point.get("grid_x") is not None and point.get("grid_y") is not None
    ]
    numeric_ppts: list[dict[str, Any]] = []
    for synthesis in syntheses:
        for point in synthesis.get("planning", {}).get("transformed_points") or []:
            if point.get("kind") != "ppt":
                continue
            label = str(point.get("display") or point.get("label") or "").strip()
            grid = point.get("campaign_grid") or {}
            if label != "10" or grid.get("grid_x") is None or grid.get("grid_y") is None:
                continue
            distance = 0.0
            if tactical_points:
                distance = min(
                    math.hypot(safe_float(grid.get("grid_x")) - safe_float(tactical.get("grid_x")), safe_float(grid.get("grid_y")) - safe_float(tactical.get("grid_y")))
                    for tactical in tactical_points
                )
            numeric_ppts.append({"grid_x": grid.get("grid_x"), "grid_y": grid.get("grid_y"), "distance": distance})
    unique: dict[tuple[float, float], dict[str, Any]] = {}
    for point in numeric_ppts:
        unique[(round(safe_float(point.get("grid_x")), 1), round(safe_float(point.get("grid_y")), 1))] = point
    selected = sorted(unique.values(), key=lambda item: safe_float(item.get("distance")))[:limit]
    if not selected:
        return []
    west = min(selected, key=lambda item: safe_float(item.get("grid_x")))
    east = max(selected, key=lambda item: safe_float(item.get("grid_x")))
    south = min(selected, key=lambda item: safe_float(item.get("grid_y")))
    assignments = [
        ("SA-10 W", west),
        ("SA-10 E", east),
        ("SA-10 S", south),
    ]
    result: list[dict[str, Any]] = []
    seen: set[tuple[float, float, str]] = set()
    for key, point in assignments:
        label = context_names.get(key, key)
        marker_key = (round(safe_float(point.get("grid_x")), 1), round(safe_float(point.get("grid_y")), 1), label)
        if marker_key in seen:
            continue
        seen.add(marker_key)
        result.append({"label": label, "grid_x": point.get("grid_x"), "grid_y": point.get("grid_y")})
    return result


def draw_named_positions(
    draw: ImageDraw.ImageDraw,
    projector: Projector,
    positions: list[dict[str, Any]],
    font: ImageFont.ImageFont,
) -> None:
    fixed_offsets = {
        "SA-10 WEST": (-18, -34, "ra"),
        "SA-10 EAST": (15, -28, "la"),
        "SA-10 SOUTH": (14, 20, "la"),
        "SA6": (14, 22, "la"),
        "JEW": (14, -11, "la"),
        "CRO": (14, 16, "la"),
        "TIG": (14, 18, "la"),
    }
    for index, position in enumerate(positions):
        xy = projector.grid(position.get("grid_x"), position.get("grid_y"))
        size = 9
        diamond = [(xy[0], xy[1] - size), (xy[0] + size, xy[1]), (xy[0], xy[1] + size), (xy[0] - size, xy[1])]
        draw.polygon(diamond, fill=GREEN + (230,), outline=(0, 18, 5, 255))
        label = str(position.get("label"))
        dx, dy, anchor = fixed_offsets.get(label.upper(), (13, -10 if index % 2 == 0 else 18, "la"))
        draw_text_box(draw, (xy[0] + dx, xy[1] + dy), label, font, fill=TEXT, bg=LABEL_BG, anchor=anchor)


def draw_package_flow_map(args: argparse.Namespace) -> Path | None:
    if not args.flow_out:
        return None
    syntheses = [load_json(path) for path in args.synthesis]
    if args.package_id:
        package_ids = args.package_id
    else:
        package_ids = [safe_int(synthesis.get("focus_package_id"), 0) for synthesis in syntheses]
    if len(package_ids) == 1 and len(syntheses) > 1:
        package_ids = package_ids * len(syntheses)
    packages = [find_package(synthesis, package_id) for synthesis, package_id in zip(syntheses, package_ids)]
    flow_groups = package_flow_groups(packages)
    named_positions = named_position_points(packages) + sa10_named_positions(syntheses, packages)
    crop_items = [
        point
        for group in flow_groups
        for point in group.get("points") or []
    ] + named_positions
    crop = crop_for_points(crop_items, args.flow_margin_grid, args.aspect_ratio)

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

    draw_flow_groups(draw, projector, flow_groups, label_font, args.scale, map_width, map_height)
    draw_named_positions(draw, projector, named_positions, label_font)
    draw_scale_and_north(overlay, crop, args.scale, small_font)
    draw_text_box(draw, (26, 26), args.flow_title, title_font, fill=TEXT, bg=(9, 13, 15, 225))
    draw_text_box(
        draw,
        (26, 62),
        "High-level package flow and named data-cartridge positions",
        small_font,
        fill=(210, 238, 255),
        bg=(9, 13, 15, 205),
    )

    output = Image.alpha_composite(map_image, overlay)
    args.flow_out.parent.mkdir(parents=True, exist_ok=True)
    output.convert("RGB").save(args.flow_out)
    return args.flow_out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, action="append", required=True, help="Path to briefing_synthesis.json. Repeat for combined package products.")
    parser.add_argument("--package-id", type=int, action="append", help="Package ID matching each --synthesis. Defaults to each synthesis focus package.")
    parser.add_argument("--cam-decode", type=Path, required=True, help="Path to cam_decode.json.")
    parser.add_argument("--campaign-dir", type=Path, required=True, help="BMS campaign directory containing Korea.tm.")
    parser.add_argument("--object-dir", type=Path, help="Falcon object table directory for aircraft names/category filtering.")
    parser.add_argument("--camp-obj-data", type=Path, help="CampObjData.XML for human-readable airbase objective names. Defaults beside --campaign-dir.")
    parser.add_argument("--map-source", type=Path, help="Override map raster path, such as 8_KTO_16k_Skyvector.png.")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG path.")
    parser.add_argument("--combined-out", type=Path, help="Optional output PNG combining enemy air axes, package flow, and named positions.")
    parser.add_argument("--flow-out", type=Path, help="Optional output PNG for a high-level package-flow map.")
    parser.add_argument("--radius-nm", type=float, default=100.0, help="Enemy squadron origin inclusion radius from player AO anchors.")
    parser.add_argument("--crop-mode", choices=("ao", "all"), default="ao", help="Crop around player AO by default; use all to include origin bases.")
    parser.add_argument("--margin-grid", type=float, default=24.0, help="Extra grid-cell margin when --crop-mode all includes origins and player AO.")
    parser.add_argument("--ao-margin-grid", type=float, default=22.0, help="Extra grid-cell margin around the player AO for the default enemy-air crop.")
    parser.add_argument("--flow-margin-grid", type=float, default=22.0, help="Extra grid-cell margin around package-flow diagram points.")
    parser.add_argument("--combined-margin-grid", type=float, default=18.0, help="Extra grid-cell margin around combined map flow, named positions, and AO anchors.")
    parser.add_argument("--combined-threat-opacity", type=float, default=0.18, help="Opacity for strategic ADA rings on --combined-out. Range 0.0-1.0.")
    parser.add_argument("--no-combined-threat-rings", dest="combined_threat_rings", action="store_false", help="Disable strategic ADA rings on --combined-out.")
    parser.set_defaults(combined_threat_rings=True)
    parser.add_argument("--scale", type=int, default=10, help="Output scale multiplier for the cropped map.")
    parser.add_argument("--aspect-ratio", default="16:9", help="Slide map-area aspect ratio. Defaults to 16:9.")
    parser.add_argument("--title", default="Enemy Air Threat Axes", help="Map title.")
    parser.add_argument("--combined-title", default="Package Flow + Enemy Air Threat Axes", help="Combined map title.")
    parser.add_argument("--flow-title", default="Package Flow Overview", help="Flow map title.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = draw_air_threat_map(args)
    print(out)
    if args.combined_out:
        combined_out = draw_air_threat_map(args, include_flow=True, output_path=args.combined_out)
        print(combined_out)
    flow_out = draw_package_flow_map(args)
    if flow_out:
        print(flow_out)


if __name__ == "__main__":
    main()
