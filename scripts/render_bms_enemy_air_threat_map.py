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

from bms_milstd2525 import canonical_unit_kind, unit_glyph_primitives
from PIL.PngImagePlugin import PngInfo

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
    iter_named_ini_points,
    is_strategic_air_defense,
    load_font,
    nm_to_grid,
    objective_ini_points,
    open_base_map,
    parse_aspect_ratio,
)
from synthesize_bms_briefing import (
    active_squadron,
    action_label,
    build_airbase_objective_refs,
    bullseye_reference,
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
FLOW_COLOR_NAMES = {
    "blue": FLOW_BLUE,
    "green": (98, 235, 128),
    "amber": (255, 199, 71),
    "yellow": (255, 199, 71),
    "red": RED,
}


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


def crop_top_fraction(crop: tuple[int, int, int, int], fraction: float) -> tuple[int, int, int, int]:
    fraction = max(0.0, min(0.9, fraction))
    if fraction <= 0:
        return crop
    left, top, right, bottom = crop
    height = bottom - top
    if height <= 1:
        return crop
    top = min(bottom - 1, top + math.floor(height * fraction))
    return left, top, right, bottom


def normalized_marker_label(value: Any) -> str:
    return "".join(char for char in str(value or "").upper() if char.isalnum())


def crop_with_top_preserving_aspect(
    crop: tuple[int, int, int, int],
    top: int,
    aspect_ratio: str,
) -> tuple[int, int, int, int]:
    left, _old_top, right, bottom = crop
    top = max(0, min(top, bottom - 1))
    height = bottom - top
    if height <= 1:
        return crop
    aspect = parse_aspect_ratio(aspect_ratio)
    width = max(1, math.ceil(height * aspect))
    center_x = (left + right) / 2
    new_left = math.floor(center_x - width / 2)
    new_right = new_left + width
    if new_left < 0:
        new_right -= new_left
        new_left = 0
    if new_right > MAP_GRID_SIZE:
        new_left -= new_right - MAP_GRID_SIZE
        new_right = MAP_GRID_SIZE
    new_left = max(0, new_left)
    return new_left, top, new_right, bottom


def apply_north_bound_from_marker(
    crop: tuple[int, int, int, int],
    markers: list[dict[str, Any]],
    label: str | None,
    padding_nm: float,
    aspect_ratio: str,
) -> tuple[int, int, int, int]:
    wanted = normalized_marker_label(label)
    if not wanted or padding_nm <= 0:
        return crop
    for marker in markers:
        marker_label = normalized_marker_label(marker.get("label"))
        if marker_label != wanted or marker.get("grid_y") is None:
            continue
        north_grid_y = safe_float(marker.get("grid_y")) + nm_to_grid(padding_nm)
        north_map_y = MAP_GRID_SIZE - north_grid_y
        bounded_top = max(crop[1], math.floor(north_map_y))
        return crop_with_top_preserving_aspect(crop, bounded_top, aspect_ratio)
    return crop


def crop_for_combined_map(
    anchors: list[dict[str, Any]],
    flow_groups: list[dict[str, Any]],
    named_positions: list[dict[str, Any]],
    objective_positions: list[dict[str, Any]],
    ground_units: list[dict[str, Any]],
    args: argparse.Namespace,
) -> tuple[int, int, int, int]:
    if args.combined_objective_explicit_grid_bounds:
        west, south, east, north = args.combined_objective_explicit_grid_bounds
        return (
            max(0, math.floor(west)),
            max(0, math.floor(MAP_GRID_SIZE - north)),
            min(MAP_GRID_SIZE, math.ceil(east)),
            min(MAP_GRID_SIZE, math.ceil(MAP_GRID_SIZE - south)),
        )
    labeled_crop = crop_for_requested_labels(named_positions, args.combined_crop_labels, args, ground_units)
    if labeled_crop:
        return labeled_crop

    if args.combined_crop_mode == "objective-area":
        objective_points = objective_positions or named_positions or anchors
        crop = crop_for_points(objective_points, args.combined_objective_margin_grid, args.aspect_ratio)
        crop = apply_north_bound_from_marker(
            crop,
            [*objective_positions, *named_positions],
            args.combined_objective_north_bound_label,
            args.combined_objective_north_padding_nm,
            args.aspect_ratio,
        )
        return crop_top_fraction(crop, args.combined_objective_crop_top_fraction)

    flow_points = [
        point
        for group in flow_groups
        for point in (
            group.get("points") or []
            if args.combined_include_flow_origins_in_bounds
            else (group.get("points") or [])[1:]
        )
    ]
    return crop_for_points([*anchors, *flow_points, *named_positions], args.combined_margin_grid, args.aspect_ratio)


def crop_for_requested_labels(
    named_positions: list[dict[str, Any]],
    labels: list[str] | None,
    args: argparse.Namespace,
    extra_points: list[dict[str, Any]] | None = None,
) -> tuple[int, int, int, int] | None:
    wanted = {normalized_marker_label(label) for label in labels or [] if normalized_marker_label(label)}
    if not wanted:
        return None
    selected = [
        point
        for point in named_positions
        if normalized_marker_label(point.get("label")) in wanted and valid_map_grid(point.get("grid_x"), point.get("grid_y"))
    ]
    found = {normalized_marker_label(point.get("label")) for point in selected}
    missing = sorted(wanted - found)
    if missing:
        raise SystemExit(f"Could not find combined crop label(s): {', '.join(missing)}")
    return crop_for_points([*selected, *(extra_points or [])], args.combined_crop_label_margin_grid, args.aspect_ratio)


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


def draw_dual_cap_circuits(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
    width: int,
    label_font: ImageFont.ImageFont,
    map_width: int,
    map_height: int,
    origin: tuple[float, float] | None = None,
    callsign_label: str = "",
) -> None:
    """Draw SAFE and FWD racetracks with a decisive hold/gate between them."""
    if len(points) < 4:
        draw_flow_arrow(draw, points, color, width)
        return

    def racetrack(start: tuple[float, float], end: tuple[float, float]) -> tuple[float, float]:
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = max(math.hypot(dx, dy), 1.0)
        offset = max(15.0, min(34.0, distance * 0.18))
        px, py = -dy / distance * offset, dx / distance * offset
        loop = [(start[0] + px, start[1] + py), (end[0] + px, end[1] + py), (end[0] - px, end[1] - py), (start[0] - px, start[1] - py)]
        for first, second in zip(loop, [*loop[1:], loop[0]]):
            draw.line((first[0], first[1], second[0], second[1]), fill=(5, 28, 38, 185), width=width + 6)
            draw.line((first[0], first[1], second[0], second[1]), fill=color + (220,), width=width)
        draw_arrowhead(draw, loop[0], loop[1], color + (240,), size=20)
        draw_arrowhead(draw, loop[2], loop[3], color + (240,), size=20)
        center = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        draw_fitted_text_box(draw, center, "CAP", label_font, map_width, map_height, fill=color, bg=LABEL_BG)
        return center

    if origin is not None:
        # A deliberate feeder shows who owns the first, SAFE patrol circuit.
        draw_flow_arrow(draw, [origin, points[0]], color, max(3, width - 1))
        if callsign_label:
            # Origins frequently sit outside the tight target-area crop.  Anchor the
            # callsign on the visible feeder segment, never beyond the slide edge.
            feeder_start = origin
            if not point_inside_image(origin, map_width, map_height, 12):
                feeder_start = clip_segment_to_rect(origin, points[0], map_width, map_height, pad=20)
            feeder_mid = (
                feeder_start[0] + (points[0][0] - feeder_start[0]) * 0.58,
                feeder_start[1] + (points[0][1] - feeder_start[1]) * 0.58,
            )
            draw_fitted_text_box(
                draw, feeder_mid, callsign_label, label_font, map_width, map_height,
                fill=color, bg=LABEL_BG,
            )

    safe_center = racetrack(points[0], points[1])
    fwd_center = racetrack(points[2], points[3])
    gate = ((safe_center[0] + fwd_center[0]) / 2.0, (safe_center[1] + fwd_center[1]) / 2.0)
    radius = max(15, width * 3)
    diamond = [(gate[0], gate[1] - radius), (gate[0] + radius, gate[1]), (gate[0], gate[1] + radius), (gate[0] - radius, gate[1])]
    draw.polygon(diamond, fill=(9, 24, 33, 235), outline=color + (255,))
    draw.line([*diamond, diamond[0]], fill=color + (255,), width=max(3, width // 2))
    draw_fitted_text_box(draw, (gate[0], gate[1] - radius - 10), "HOLD", label_font, map_width, map_height, fill=color, bg=LABEL_BG)


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
    name = str(origin.get("name") or "Origin")
    if name.lower().startswith("offshore group") and origin.get("bullseye_ref"):
        name = f"{name} {origin['bullseye_ref']}"
    return f"{name} | {aircraft}"


def compact_aircraft_name(name: str) -> str:
    cleaned = str(name or "").strip()
    compact = cleaned.upper().replace("-", "").replace(" ", "")
    replacements = (
        ("MIG29S", "M29S"),
        ("MIG29", "M29"),
        ("MIG27", "M27"),
        ("MIG31", "M31"),
        ("SU35S", "S35S"),
        ("SU35", "S35"),
        ("SU33", "S33"),
        ("SU39", "S39"),
        ("SU27", "S27"),
        ("SU30", "S30"),
        ("SU34", "S34"),
    )
    for needle, replacement in replacements:
        if needle in compact:
            return replacement
    return cleaned[:8]


def compact_aircraft_list(names: list[str], limit: int = 3) -> str:
    compacted: list[str] = []
    for name in names:
        compact = compact_aircraft_name(name)
        if compact and compact not in compacted:
            compacted.append(compact)
    shown = compacted[:limit]
    if len(compacted) > limit:
        shown.append("+")
    return ", ".join(shown)


def compact_origin_name(name: Any) -> str:
    text = str(name or "").strip()
    text = text.split("(", 1)[0].strip()
    for token in (" International", " Intl", " Airport", " Airbase", " AB"):
        text = text.replace(token, "")
    return text.strip() or "Origin"


def compact_sam_label(label: Any) -> str:
    text = str(label or "").upper().replace(" ", "")
    text = text.replace("SA-", "SA").replace("_", "")
    if text.startswith("SA10"):
        return "10"
    if text.startswith("SA6"):
        return "6"
    if text.startswith("SA17"):
        return "17"
    if text.startswith("SA11"):
        return "11"
    if text.startswith("SA5"):
        return "5"
    if text.startswith("SA3"):
        return "3"
    if text.startswith("SA2"):
        return "2"
    return str(label or "")[:6]


def compact_named_label(label: Any) -> str:
    text = str(label or "").strip()
    upper = text.upper().replace("-", "").replace(" ", "")
    if upper in {"SA10W", "SA10WEST", "10WEST"}:
        return "10W"
    if upper in {"SA10E", "SA10EAST", "10EAST"}:
        return "10E"
    if upper in {"SA10S", "SA10SOUTH", "10SOUTH"}:
        return "10S"
    if upper in {"SA6", "SA6MARK"}:
        return "6"
    if upper.startswith("SA") and any(char.isdigit() for char in upper[2:]):
        return compact_sam_label(text)
    return text


def canonical_named_position_key(label: Any) -> str:
    """Treat raw `SA5` and planner `5` labels as one tactical marker."""
    return normalized_marker_label(compact_named_label(label))


def tactical_factor_family(label: Any) -> str:
    compact = canonical_named_position_key(label).removeprefix("SA")
    for family in ("17", "11", "10", "6", "5", "3", "2"):
        if compact.startswith(family):
            return family
    return ""


def merge_named_positions(
    raw_positions: list[dict[str, Any]],
    override_positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge map marks with planner overrides taking precedence."""
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for position in override_positions:
        key = canonical_named_position_key(position.get("label"))
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(position)
    for position in raw_positions:
        key = canonical_named_position_key(position.get("label"))
        if not key or key in seen:
            continue
        raw_label = normalized_label(position.get("label"))
        if raw_label and any(
            normalized_label(override.get("source_label")) == raw_label
            for override in override_positions
            if override.get("source_label")
        ):
            continue
        family = tactical_factor_family(position.get("label"))
        if family and any(
            tactical_factor_family(override.get("label")) == family
            and math.hypot(
                safe_float(position.get("grid_x")) - safe_float(override.get("grid_x")),
                safe_float(position.get("grid_y")) - safe_float(override.get("grid_y")),
            )
            <= 2.5
            for override in override_positions
        ):
            continue
        seen.add(key)
        merged.append(position)
    return merged


def co_located_factor_marker(
    air_defense: dict[str, Any],
    named_positions: list[dict[str, Any]],
    max_distance_grid: float = 2.5,
) -> bool:
    factor_keys = {"2", "3", "5", "6", "10", "10A", "10B", "10C", "10N", "10W", "10E", "10S", "11", "17"}
    for position in named_positions:
        if canonical_named_position_key(position.get("label")) not in factor_keys:
            continue
        distance = math.hypot(
            safe_float(air_defense.get("grid_x")) - safe_float(position.get("grid_x")),
            safe_float(air_defense.get("grid_y")) - safe_float(position.get("grid_y")),
        )
        if distance <= max_distance_grid:
            return True
    return False


def normalized_label(value: Any) -> str:
    return "".join(char for char in str(value or "").upper() if char.isalnum())


def compact_label_text(origin: dict[str, Any]) -> str:
    shown = compact_aircraft_list(origin.get("aircraft") or [])
    name = str(origin.get("name") or "").strip()
    if name.lower().startswith("offshore group"):
        parts = [shown or "Offshore"]
        if origin.get("bullseye_ref"):
            parts.append(str(origin["bullseye_ref"]))
        return " | ".join(parts)
    origin_name_short = compact_origin_name(name)
    return f"{origin_name_short} ({shown})" if shown else origin_name_short


def is_airbase_origin(origin: dict[str, Any]) -> bool:
    name = str(origin.get("name") or "").lower()
    # Carrier/naval squadrons can carry a campaign base identifier even though
    # their origin is not a land airbase. The resolved offshore identity wins.
    if name.startswith("offshore group"):
        return False
    return bool(origin.get("airbase_id")) or bool(name)


def origin_name(grid_x: float, grid_y: float, airbase_name: str | None) -> str:
    if airbase_name:
        return airbase_name
    # Most non-airbase fighter origins in naval scenarios are carrier or offshore groups.
    # Raw campaign-grid coordinates are not a valid bullseye call and must not
    # be placed in the display name. The renderer adds a calculated BE reference
    # after all origins have been correlated with the current synthesis.
    return "Offshore group"


def add_origin_bullseye_references(
    origins: list[dict[str, Any]],
    syntheses: list[dict[str, Any]],
) -> None:
    bullseye = next(
        (
            synthesis.get("bullseye")
            for synthesis in syntheses
            if (synthesis.get("bullseye") or {}).get("grid_x") is not None
            and (synthesis.get("bullseye") or {}).get("grid_y") is not None
        ),
        None,
    )
    if not bullseye:
        return
    reference_source = {"bullseye": bullseye}
    for origin in origins:
        reference = bullseye_reference(reference_source, origin)
        if reference:
            origin["bullseye_ref"] = reference


def edge_label_position(point: tuple[float, float], width: int, height: int) -> tuple[tuple[float, float], str]:
    margin = 22
    x = max(margin, min(width - margin, point[0]))
    y = max(margin, min(height - margin, point[1]))
    if x >= width - margin - 1:
        return (x - 8, y - 14), "ra"
    if x <= margin + 1:
        return (x + 8, y - 14), "la"
    return (x + 8, y + (24 if y < height / 2 else -14)), "la"


def draw_fitted_text_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    width: int,
    height: int,
    fill: tuple[int, int, int] = TEXT,
    bg: tuple[int, int, int, int] = LABEL_BG,
    pad: int = 3,
    anchor: str = "la",
    margin: int = 8,
) -> tuple[int, int, int, int]:
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font, anchor=anchor)
    dx = 0
    dy = 0
    if bbox[0] < margin:
        dx = margin - bbox[0]
    elif bbox[2] > width - margin:
        dx = width - margin - bbox[2]
    if bbox[1] < margin:
        dy = margin - bbox[1]
    elif bbox[3] > height - margin:
        dy = height - margin - bbox[3]
    return draw_text_box(draw, (x + dx, y + dy), text, font, fill=fill, bg=bg, pad=pad, anchor=anchor)


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


def collect_visible_enemy_units(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect deduplicated enemy ground-unit records exposed by package intelligence."""
    units: dict[tuple[int, float, float], dict[str, Any]] = {}
    for package in packages:
        enemy = package.get("enemy_situation") or {}
        for unit in enemy.get("closest_units") or []:
            if not valid_map_grid(unit.get("grid_x"), unit.get("grid_y")):
                continue
            key = (
                safe_int(unit.get("camp_id"), -1),
                round(safe_float(unit.get("grid_x")), 1),
                round(safe_float(unit.get("grid_y")), 1),
            )
            units[key] = unit
    return list(units.values())


def point_in_grid_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    inside = False
    previous = len(polygon) - 1
    for current in range(len(polygon)):
        x1, y1 = polygon[current]
        x2, y2 = polygon[previous]
        if ((y1 > y) != (y2 > y)) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-9) + x1:
            inside = not inside
        previous = current
    return inside


def decoded_unit_equipment(unit: dict[str, Any], limit: int = 3) -> str:
    names: list[str] = []
    for item in (unit.get("unit_type") or {}).get("vehicle_template") or []:
        name = str(item.get("vehicle_name") or "").strip()
        if name and name not in names:
            names.append(name)
        if len(names) >= limit:
            break
    return "; ".join(names)


def collect_objective_ground_units(
    cam_decode: dict[str, Any],
    packages: list[dict[str, Any]],
    mission_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build a readable brigade-level ground picture plus discrete enemy ADA."""
    polygons = [
        [
            (safe_float(point.get("grid_x")), safe_float(point.get("grid_y")))
            for point in spec.get("points") or []
            if valid_map_grid(point.get("grid_x"), point.get("grid_y"))
        ]
        for spec in mission_context.get("map_killboxes") or []
        if isinstance(spec, dict)
    ]
    polygons = [polygon for polygon in polygons if len(polygon) >= 3]
    if not polygons:
        return collect_visible_enemy_units(packages)

    teams_by_id = {safe_int(team.get("who"), -1): team for team in cam_decode.get("teams") or []}
    friendly_owners = {
        safe_int(flight.get("owner"), -1)
        for package in packages
        for flight in package.get("flights") or []
        if safe_int(flight.get("owner"), -1) >= 0
    }
    enemy_owners: set[int] = set()
    for package in packages:
        enemy_owners.update(enemy_owner_ids(package, teams_by_id))

    reference_points = [point for polygon in polygons for point in polygon]
    for polygon in polygons:
        reference_points.append(
            (
                sum(point[0] for point in polygon) / len(polygon),
                sum(point[1] for point in polygon) / len(polygon),
            )
        )

    result: dict[tuple[str, int], dict[str, Any]] = {}
    for brigade in cam_decode.get("brigades") or []:
        owner = safe_int(brigade.get("owner"), -1)
        x = safe_float(brigade.get("x"))
        y = safe_float(brigade.get("y"))
        inside_killbox = any(point_in_grid_polygon(x, y, polygon) for polygon in polygons)
        near_killbox = min((math.hypot(x - px, y - py) for px, py in reference_points), default=9999.0) <= 22.0
        if owner in enemy_owners and not inside_killbox:
            continue
        if owner in friendly_owners and not near_killbox:
            continue
        if owner not in enemy_owners and owner not in friendly_owners:
            continue
        class_name = str((((brigade.get("unit_type") or {}).get("unit_class") or {}).get("name")) or "Unit")
        item = {
            "camp_id": safe_int(brigade.get("camp_id"), -1),
            "team": str((teams_by_id.get(owner) or {}).get("name") or owner),
            "affiliation": "friendly" if owner in friendly_owners else "hostile",
            "echelon": "brigade",
            "class_name": class_name,
            "category": "maneuver",
            "grid_x": x,
            "grid_y": y,
            "equipment": decoded_unit_equipment(brigade),
        }
        result[(item["affiliation"], item["camp_id"])] = item

    # Preserve discrete, player-relevant enemy ADA locations that are not
    # represented by maneuver-brigade frames.
    for unit in collect_visible_enemy_units(packages):
        if str(unit.get("class_name") or "").upper() != "AIR DEFENSE":
            continue
        x = safe_float(unit.get("grid_x"))
        y = safe_float(unit.get("grid_y"))
        if min((math.hypot(x - px, y - py) for px, py in reference_points), default=9999.0) > 18.0:
            continue
        item = dict(unit)
        item.update({"affiliation": "hostile", "echelon": "battalion"})
        result[("hostile", safe_int(item.get("camp_id"), -1))] = item
    grouped: dict[tuple[str, str, float, float, str], dict[str, Any]] = {}
    for item in result.values():
        key = (
            str(item.get("affiliation") or "hostile"),
            str(item.get("echelon") or "battalion"),
            round(safe_float(item.get("grid_x")), 1),
            round(safe_float(item.get("grid_y")), 1),
            str(item.get("class_name") or "Unit").upper(),
        )
        if key not in grouped:
            grouped[key] = dict(item)
            grouped[key]["count"] = 1
        else:
            grouped[key]["count"] = safe_int(grouped[key].get("count"), 1) + 1
    return list(grouped.values())


def collect_objective_battalions(
    cam_decode: dict[str, Any],
    packages: list[dict[str, Any]],
    mission_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Select decoded battalions at their actual BMS campaign positions."""
    # BMSUtils' compatibility decode does not expose the unit-class record.
    # Retain readable MIL symbols when a freshly decoded CAM is used; the map
    # still takes every coordinate directly from that new CAM record.
    entity_class_fallback = {
        152: "Tank", 161: "Tank", 158: "Motor Rifle", 5291: "Motor Rifle",
        2620: "Cavalry", 181: "HQ", 681: "HQ", 827: "Infantry",
        1531: "Towed Gun", 673: "Mech", 154: "Mech",
    }
    polygons = [
        [
            (safe_float(point.get("grid_x")), safe_float(point.get("grid_y")))
            for point in spec.get("points") or []
            if valid_map_grid(point.get("grid_x"), point.get("grid_y"))
        ]
        for spec in mission_context.get("map_killboxes") or []
        if isinstance(spec, dict)
    ]
    polygons = [polygon for polygon in polygons if len(polygon) >= 3]
    if not polygons:
        return []
    teams_by_id = {safe_int(team.get("who"), -1): team for team in cam_decode.get("teams") or []}
    friendly_owners = {
        safe_int(flight.get("owner"), -1)
        for package in packages
        for flight in package.get("flights") or []
        if safe_int(flight.get("owner"), -1) >= 0
    }
    enemy_owners: set[int] = set()
    for package in packages:
        enemy_owners.update(enemy_owner_ids(package, teams_by_id))
    reference_points = [point for polygon in polygons for point in polygon]
    for polygon in polygons:
        reference_points.append(
            (
                sum(point[0] for point in polygon) / len(polygon),
                sum(point[1] for point in polygon) / len(polygon),
            )
        )

    units: list[dict[str, Any]] = []
    for battalion in cam_decode.get("battalions") or []:
        owner = safe_int(battalion.get("owner"), -1)
        if owner not in friendly_owners and owner not in enemy_owners:
            continue
        x = safe_float(battalion.get("x"))
        y = safe_float(battalion.get("y"))
        class_name = str((((battalion.get("unit_type") or {}).get("unit_class") or {}).get("name")) or "")
        if not class_name:
            class_name = entity_class_fallback.get(safe_int(battalion.get("entity_type"), -1), "Unit")
        inside_killbox = any(point_in_grid_polygon(x, y, polygon) for polygon in polygons)
        distance_to_killbox = min((math.hypot(x - px, y - py) for px, py in reference_points), default=9999.0)
        if owner in enemy_owners:
            discrete_ada = class_name.upper() in {"AIR DEFENSE", "SHORAD"} and distance_to_killbox <= 18.0
            if not inside_killbox and not discrete_ada:
                continue
        elif distance_to_killbox > 22.0:
            continue
        units.append(
            {
                "camp_id": safe_int(battalion.get("camp_id"), -1),
                "team": str((teams_by_id.get(owner) or {}).get("name") or owner),
                "affiliation": "friendly" if owner in friendly_owners else "hostile",
                "echelon": "battalion",
                "class_name": class_name,
                "grid_x": x,
                "grid_y": y,
                "equipment": decoded_unit_equipment(battalion),
            }
        )
    return units


def mil2525_unit_label(unit: dict[str, Any]) -> str:
    equipment = str(unit.get("equipment") or "").upper()
    for token in ("SA-10", "SA-11", "SA-13", "SA-17", "SA-19", "BM-21", "D-30"):
        if token in equipment:
            base = token
            count = safe_int(unit.get("count"), 1)
            return f"{count}× {base}" if count > 1 else base
    class_name = str(unit.get("class_name") or "UNIT").upper()
    base = {
        "AIR DEFENSE": "ADA",
        "ROCKET": "RKT",
        "ROCKET ARTILLERY": "RKT ARTY",
        "TOWED GUN": "ARTY",
        "TOWED ARTILLERY": "ARTY",
        "SP ARTILLERY": "SP ARTY",
        "ARMORED": "ARM",
        "MECH": "MECH",
        "INFANTRY": "INF",
        "ENGINEER": "ENG",
        "SUPPLY": "SUP",
        "MOTOR RIFLE": "MOT INF",
        "HQ": "HQ",
    }.get(class_name, class_name[:8])
    count = safe_int(unit.get("count"), 1)
    return f"{count}× {base}" if count > 1 else base


def draw_mil2525_enemy_units(
    overlay: Image.Image,
    projector: Projector,
    units: list[dict[str, Any]],
    reserved_positions: list[dict[str, Any]] | None = None,
) -> None:
    """Draw compact MIL-STD-2525-style ground-unit symbols with leaders."""
    draw = ImageDraw.Draw(overlay, "RGBA")
    half = max(16, min(24, int(projector.scale * 1.2)))
    line_width = max(3, min(5, projector.scale // 4))
    icon_width = max(2, min(3, line_width - 1))
    icon_font = load_font(max(11, int(projector.scale * 1.15)), bold=True)
    label_font = load_font(max(11, int(projector.scale * 1.05)), bold=True)
    placed: list[tuple[float, float, float, float]] = []
    for position in reserved_positions or []:
        xy = projector.grid(position.get("grid_x"), position.get("grid_y"))
        if not point_inside_image(xy, overlay.width, overlay.height, 4):
            continue
        placed.append((xy[0] - 34, xy[1] - 30, xy[0] + 112, xy[1] + 42))
    spacing = half * 2.4
    candidate_offsets = [
        (0.0, 0.0),
        (0.0, -spacing),
        (spacing, 0.0),
        (-spacing, 0.0),
        (0.0, spacing),
        (spacing, -spacing),
        (-spacing, -spacing),
        (spacing, spacing),
        (-spacing, spacing),
        (spacing * 1.8, 0.0),
        (-spacing * 1.8, 0.0),
        (0.0, spacing * 1.8),
        (0.0, -spacing * 1.8),
        (spacing * 2.8, 0.0),
        (-spacing * 2.8, 0.0),
        (spacing * 2.2, -spacing * 1.7),
        (-spacing * 2.2, -spacing * 1.7),
        (spacing * 2.2, spacing * 1.7),
        (-spacing * 2.2, spacing * 1.7),
    ]
    for radius_multiplier in (3.0, 3.8, 4.6, 5.4, 6.2):
        radius = spacing * radius_multiplier
        for angle in range(0, 360, 30):
            radians = math.radians(angle)
            candidate_offsets.append((radius * math.cos(radians), radius * math.sin(radians)))
    ink = (25, 10, 10, 255)
    for unit in sorted(units, key=lambda item: (safe_float(item.get("grid_y")), safe_float(item.get("grid_x"))), reverse=True):
        actual = projector.grid(unit.get("grid_x"), unit.get("grid_y"))
        if not point_inside_image(actual, overlay.width, overlay.height, half + 4):
            continue
        label = mil2525_unit_label(unit)
        label_bbox = draw.textbbox((0, 0), label, font=label_font)
        label_width = max(half * 2, label_bbox[2] - label_bbox[0] + 10)
        symbol_height = half * 2 + (label_bbox[3] - label_bbox[1]) + 11
        chosen = actual
        chosen_box = (actual[0] - label_width / 2, actual[1] - half - 12, actual[0] + label_width / 2, actual[1] - half - 12 + symbol_height)
        for dx, dy in candidate_offsets:
            candidate = (actual[0] + dx, actual[1] + dy)
            box = (
                candidate[0] - label_width / 2 - 4,
                candidate[1] - half - 16,
                candidate[0] + label_width / 2 + 4,
                candidate[1] - half - 16 + symbol_height + 8,
            )
            if box[0] < 4 or box[1] < 4 or box[2] > overlay.width - 4 or box[3] > overlay.height - 4:
                continue
            if any(not (box[2] < other[0] or box[0] > other[2] or box[3] < other[1] or box[1] > other[3]) for other in placed):
                continue
            chosen = candidate
            chosen_box = box
            break
        placed.append(chosen_box)
        friendly = str(unit.get("affiliation") or "hostile").lower() == "friendly"
        frame = (50, 135, 255, 255) if friendly else (238, 40, 40, 255)
        frame_fill = (222, 238, 255, 225) if friendly else (255, 225, 225, 220)
        label_fill = (210, 232, 255) if friendly else (255, 220, 220)
        label_bg = (0, 42, 92, 220) if friendly else (72, 0, 0, 215)
        if math.hypot(chosen[0] - actual[0], chosen[1] - actual[1]) > 2:
            draw.line((actual[0], actual[1], chosen[0], chosen[1]), fill=frame, width=max(2, line_width - 1))
            draw.ellipse((actual[0] - 3, actual[1] - 3, actual[0] + 3, actual[1] + 3), fill=frame)

        cx, cy = chosen
        if friendly:
            frame_points = [
                (cx - half, cy - half * 0.72),
                (cx + half, cy - half * 0.72),
                (cx + half, cy + half * 0.72),
                (cx - half, cy + half * 0.72),
            ]
        else:
            frame_points = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
        draw.polygon(frame_points, fill=frame_fill, outline=frame)
        draw.line([*frame_points, frame_points[0]], fill=frame, width=line_width, joint="curve")
        echelon_y = cy - half - 10
        echelon = "X" if str(unit.get("echelon") or "").lower() == "brigade" else "II"
        draw.text((cx, echelon_y), echelon, font=label_font, fill=frame, anchor="ms")

        class_name = str(unit.get("class_name") or "").upper()
        if class_name == "AIR DEFENSE":
            arc_box = (cx - half * 0.48, cy - half * 0.05, cx + half * 0.48, cy + half * 0.55)
            draw.arc(arc_box, 180, 360, fill=ink, width=icon_width)
            draw.line((cx, cy + half * 0.25, cx, cy - half * 0.45), fill=ink, width=icon_width)
        elif class_name in {"ROCKET", "ROCKET ARTILLERY"}:
            for offset in (-half * 0.32, 0.0, half * 0.32):
                draw.line((cx + offset, cy + half * 0.38, cx + offset, cy - half * 0.28), fill=ink, width=icon_width)
                draw.polygon(
                    [(cx + offset, cy - half * 0.48), (cx + offset - 3, cy - half * 0.23), (cx + offset + 3, cy - half * 0.23)],
                    fill=ink,
                )
        elif class_name in {"TOWED GUN", "TOWED ARTILLERY", "SP ARTILLERY"}:
            dot = max(3, half // 5)
            draw.ellipse((cx - dot, cy - dot, cx + dot, cy + dot), fill=ink)
            draw.line((cx - half * 0.48, cy, cx + half * 0.48, cy), fill=ink, width=icon_width)
        elif class_name in {"MECH", "MOTOR RIFLE"}:
            # BMS motor-rifle formations are shown as mechanized infantry:
            # one centered composite, with the infantry cross integrated over
            # the armored oval rather than stacked above it.
            draw.ellipse((cx - half * 0.60, cy - half * 0.34, cx + half * 0.60, cy + half * 0.34), outline=ink, width=icon_width)
            draw.line((cx - half * 0.42, cy - half * 0.28, cx + half * 0.42, cy + half * 0.28), fill=ink, width=icon_width)
            draw.line((cx + half * 0.42, cy - half * 0.28, cx - half * 0.42, cy + half * 0.28), fill=ink, width=icon_width)
        elif class_name == "INFANTRY":
            draw.line((cx - half * 0.50, cy - half * 0.40, cx + half * 0.50, cy + half * 0.40), fill=ink, width=icon_width)
            draw.line((cx + half * 0.50, cy - half * 0.40, cx - half * 0.50, cy + half * 0.40), fill=ink, width=icon_width)
        elif class_name == "ARMORED":
            draw.ellipse((cx - half * 0.60, cy - half * 0.34, cx + half * 0.60, cy + half * 0.34), outline=ink, width=icon_width)
        else:
            code = {"ENGINEER": "E", "SUPPLY": "S", "HQ": "HQ"}.get(class_name, "U")
            draw.text((cx, cy), code, font=icon_font, fill=ink, anchor="mm")

        draw_fitted_text_box(
            draw,
            (cx, cy + half + 5),
            label,
            label_font,
            overlay.width,
            overlay.height,
            fill=label_fill,
            bg=label_bg,
            pad=2,
            anchor="ma",
        )


def draw_mil2525_battalions_exact(
    overlay: Image.Image,
    projector: Projector,
    units: list[dict[str, Any]],
) -> None:
    """Draw individual battalions at decoded BMS positions without type labels."""
    draw = ImageDraw.Draw(overlay, "RGBA")
    # Keep the symbols readable on a slide without letting a higher-resolution
    # objective render inflate them into oversized, unfamiliar-looking glyphs.
    half = max(16, min(24, int(projector.scale * 1.2)))
    line_width = max(3, min(5, projector.scale // 4))
    icon_width = max(2, min(3, line_width))
    echelon_font = load_font(max(11, int(projector.scale * 1.15)), bold=True)
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        actual = projector.grid(unit.get("grid_x"), unit.get("grid_y"))
        grouped[(round(actual[0]), round(actual[1]))].append(unit)

    for (actual_x, actual_y), group in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
        if not point_inside_image((actual_x, actual_y), overlay.width, overlay.height, half + 2):
            continue
        if len(group) > 1:
            draw.ellipse((actual_x - 2, actual_y - 2, actual_x + 2, actual_y + 2), fill=(25, 25, 25, 245))
        for index, unit in enumerate(group):
            if len(group) == 1:
                cx, cy = float(actual_x), float(actual_y)
            else:
                angle = -math.pi / 2 + (2 * math.pi * index / len(group))
                fan_radius = half * 1.45
                cx = actual_x + fan_radius * math.cos(angle)
                cy = actual_y + fan_radius * math.sin(angle)
                draw.line((actual_x, actual_y, cx, cy), fill=(35, 35, 35, 210), width=1)

            friendly = str(unit.get("affiliation") or "hostile").lower() == "friendly"
            frame = (50, 135, 255, 255) if friendly else (238, 40, 40, 255)
            frame_fill = (222, 238, 255, 225) if friendly else (255, 225, 225, 225)
            ink = (20, 20, 20, 255)
            if friendly:
                frame_points = [
                    (cx - half, cy - half * 0.72),
                    (cx + half, cy - half * 0.72),
                    (cx + half, cy + half * 0.72),
                    (cx - half, cy + half * 0.72),
                ]
            else:
                frame_points = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
            draw.polygon(frame_points, fill=frame_fill, outline=frame)
            draw.line([*frame_points, frame_points[0]], fill=frame, width=line_width, joint="curve")
            draw.text((cx, cy - half - 4), "II", font=echelon_font, fill=frame, anchor="ms")

            class_name = str(unit.get("class_name") or "").upper()
            if canonical_unit_kind(class_name) == "headquarters":
                if friendly:
                    staff_x = cx - half
                    staff_y = cy + half * 0.72
                else:
                    staff_x = cx - half * 0.5
                    staff_y = cy + half * 0.5
                draw.line((staff_x, staff_y, staff_x, staff_y + half * 0.72), fill=frame, width=line_width)
            symbol_w = half * 1.20
            symbol_h = half * 1.12
            for primitive in unit_glyph_primitives(class_name):
                values = primitive.values
                if primitive.kind == "line":
                    draw.line(
                        (
                            cx + values[0] * symbol_w,
                            cy - values[1] * symbol_h,
                            cx + values[2] * symbol_w,
                            cy - values[3] * symbol_h,
                        ),
                        fill=ink,
                        width=icon_width,
                    )
                elif primitive.kind in {"ellipse", "filled_ellipse"}:
                    x1, y1, x2, y2 = values
                    box = (
                        cx + x1 * symbol_w,
                        cy - y2 * symbol_h,
                        cx + x2 * symbol_w,
                        cy - y1 * symbol_h,
                    )
                    if primitive.kind == "filled_ellipse":
                        draw.ellipse(box, fill=ink)
                    else:
                        draw.ellipse(box, outline=ink, width=icon_width)
                elif primitive.kind == "filled_polygon":
                    points = [
                        (cx + values[offset] * symbol_w, cy - values[offset + 1] * symbol_h)
                        for offset in range(0, len(values), 2)
                    ]
                    draw.polygon(points, fill=ink)
                elif primitive.kind == "arc":
                    x1, y1, x2, y2, theta1, theta2 = values
                    draw.arc(
                        (
                            cx + x1 * symbol_w,
                            cy - y2 * symbol_h,
                            cx + x2 * symbol_w,
                            cy - y1 * symbol_h,
                        ),
                        int(180 + theta1),
                        int(180 + theta2),
                        fill=ink,
                        width=icon_width,
                    )
                elif primitive.kind in {"text_e", "text_s"}:
                    draw.text(
                        (cx, cy),
                        "E" if primitive.kind == "text_e" else "S",
                        font=echelon_font,
                        fill=ink,
                        anchor="mm",
                    )


def apply_context_air_defense_ring_overrides(
    air_defenses: list[dict[str, Any]],
    named_positions: list[dict[str, Any]],
    mission_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Force planner-named WEZ rings and allow deployment-state styling."""
    specs = mission_context.get("map_threat_ring_overrides") or []
    if not isinstance(specs, list):
        return air_defenses
    positions = {
        canonical_named_position_key(item.get("label")): item
        for item in named_positions
        if canonical_named_position_key(item.get("label"))
    }
    result = list(air_defenses)
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        key = canonical_named_position_key(spec.get("label"))
        position = positions.get(key)
        if not position:
            continue
        grid_x = safe_float(position.get("grid_x"))
        grid_y = safe_float(position.get("grid_y"))
        nearby = [
            item
            for item in result
            if math.hypot(
                safe_float(item.get("grid_x")) - grid_x,
                safe_float(item.get("grid_y")) - grid_y,
            )
            <= safe_float(spec.get("match_radius_grid"), 3.0)
        ]
        result = [item for item in result if item not in nearby]
        base = dict(nearby[0]) if nearby else {}
        radius_grid = safe_float(
            spec.get("threat_range_grid"),
            max(safe_float(base.get("air_range")), safe_float(base.get("low_air_range")), 85.0),
        )
        base.update(
            {
                "grid_x": grid_x,
                "grid_y": grid_y,
                "air_range": radius_grid,
                "low_air_range": radius_grid,
                "ring_style": str(spec.get("ring_style") or "normal"),
                "planner_ring_label": str(spec.get("label") or key),
            }
        )
        result.append(base)
    return sorted(
        result,
        key=lambda item: max(safe_float(item.get("air_range")), safe_float(item.get("low_air_range"))),
        reverse=True,
    )


def draw_low_opacity_air_defense_rings(
    overlay: Image.Image,
    projector: Projector,
    air_defenses: list[dict[str, Any]],
    font: ImageFont.ImageFont,
    opacity: float,
    style: str = "target-area",
    compact_labels: bool = False,
    named_positions: list[dict[str, Any]] | None = None,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    opacity = max(0.0, min(1.0, opacity))
    if style == "route-reference":
        outline_alpha = max(218, min(255, int(255 * max(opacity, 0.86))))
        fill_alpha = max(8, min(28, int(32 * max(opacity, 0.35))))
        label_alpha = max(205, min(232, int(255 * max(opacity, 0.82))))
        ring_width = max(4, projector.scale // 2 + 1)
    else:
        outline_alpha = max(0, min(255, int(255 * opacity)))
        fill_alpha = max(0, min(80, int(outline_alpha * 0.28)))
        label_alpha = max(145, min(225, int(outline_alpha * 1.45)))
        ring_width = max(3, projector.scale // 2)
    for air_defense in air_defenses:
        center = projector.grid(air_defense.get("grid_x"), air_defense.get("grid_y"))
        radius_grid = max(safe_float(air_defense.get("air_range")), safe_float(air_defense.get("low_air_range")))
        if radius_grid <= 0:
            continue
        radius = projector.radius(radius_grid)
        box = (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)
        ring_style = str(air_defense.get("ring_style") or "normal").strip().lower()
        if ring_style in {"dotted", "dotted-outline", "undeployed"}:
            # A broken, unfilled outline communicates a potential WEZ for a
            # mobile system assessed unlikely to be deployed.
            dot_radius = max(3, ring_width // 2 + 1)
            # Dense, fine dots retain the NATO suspected-position convention at
            # slide scale without reading as a coarse, sparse dashed circle.
            for angle in range(0, 360, 2):
                radians = math.radians(angle)
                dot_x = center[0] + radius * math.cos(radians)
                dot_y = center[1] + radius * math.sin(radians)
                draw.ellipse(
                    (
                        dot_x - dot_radius,
                        dot_y - dot_radius,
                        dot_x + dot_radius,
                        dot_y + dot_radius,
                    ),
                    fill=THREAT_RING + (outline_alpha,),
                )
        else:
            draw.ellipse(box, fill=THREAT_FILL + (fill_alpha,))
            draw.ellipse(box, outline=THREAT_RING + (outline_alpha,), width=ring_width)
        if point_inside_image(center, overlay.width, overlay.height, 16) and not co_located_factor_marker(
            air_defense,
            named_positions or [],
        ):
            label = contextual_air_defense_label(air_defense, named_positions or [], compact_labels)
            draw_text_box(draw, center, label, font, fill=(255, 230, 230), bg=THREAT_LABEL_BG[:3] + (label_alpha,), pad=2, anchor="mm")


def draw_context_killboxes(
    overlay: Image.Image,
    projector: Projector,
    mission_context: dict[str, Any],
) -> None:
    """Draw planner-defined killbox boundaries as a quiet objective layer."""
    specs = mission_context.get("map_killboxes") or []
    if not isinstance(specs, list):
        return
    draw = ImageDraw.Draw(overlay, "RGBA")
    outline = FLOW_COLOR_NAMES["amber"] + (235,)
    fill = FLOW_COLOR_NAMES["amber"] + (30,)
    width = max(4, projector.scale // 2)
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        points = [
            projector.grid(point.get("grid_x"), point.get("grid_y"))
            for point in spec.get("points") or []
            if valid_map_grid(point.get("grid_x"), point.get("grid_y"))
        ]
        if len(points) < 3:
            continue
        draw.polygon(points, fill=fill)
        draw.line([*points, points[0]], fill=outline, width=width, joint="curve")


def draw_context_package_color_legend(
    draw: ImageDraw.ImageDraw,
    mission_context: dict[str, Any],
    font: ImageFont.ImageFont,
    map_width: int,
    map_height: int,
) -> None:
    specs = mission_context.get("map_package_color_legend") or []
    if not isinstance(specs, list):
        return
    y = 24
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        label = str(spec.get("label") or f"PKG {spec.get('package_id') or ''}").strip()
        if not label:
            continue
        color = color_from_context(spec.get("color"), FLOW_BLUE)
        bbox = draw_fitted_text_box(
            draw,
            (26, y),
            label,
            font,
            map_width,
            map_height,
            fill=color,
            bg=(9, 13, 15, 225),
            anchor="la",
        )
        y = bbox[3] + 12


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
    width_multiplier: float = 1.0,
    compact_labels: bool = False,
    show_origin_labels: bool = False,
    show_flow_labels: bool = True,
) -> None:
    labeled_origins: set[str] = set()
    origin_labels: list[tuple[tuple[float, float], str, str]] = []
    flow_labels: list[tuple[tuple[float, float], tuple[float, float], str, tuple[int, int, int]]] = []
    flow_label_specs = {
        "SEAD / DEAD Flow": (0.58, (-145, 42)),
        "Escort / BARCAP Flow": (0.53, (34, -50)),
        "East Fighter Screen": (0.66, (34, 34)),
        "ORION STRIKE": (0.70, (-56, 44)),
        "10E SEAD": (0.62, (38, -58)),
        "HIGH COVER": (0.52, (-76, -58)),
    }
    for group in flow_groups:
        points = [projector.grid(point.get("grid_x"), point.get("grid_y")) for point in group.get("points") or []]
        if len(points) < 2:
            continue
        color = group.get("color") or FLOW_BLUE
        origin_label = str(group.get("origin_label") or "").strip()
        if len(points) >= 2 and not point_inside_image(points[0], map_width, map_height, 18):
            clipped_origin = clip_segment_to_rect(points[0], points[1], map_width, map_height, pad=18)
            points = [clipped_origin, *points[1:]]
            if show_origin_labels and origin_label and origin_label not in labeled_origins:
                label_xy, anchor = edge_label_position(clipped_origin, map_width, map_height)
                if label_xy[0] < 580 and label_xy[1] < 104:
                    label_xy = (label_xy[0], 104)
                origin_labels.append((label_xy, origin_label, anchor))
                labeled_origins.add(origin_label)
        elif show_origin_labels and origin_label and origin_label not in labeled_origins:
            origin_xy = points[0]
            marker_radius = max(8, int(scale * width_multiplier * 0.65))
            draw.rectangle(
                (
                    origin_xy[0] - marker_radius,
                    origin_xy[1] - marker_radius,
                    origin_xy[0] + marker_radius,
                    origin_xy[1] + marker_radius,
                ),
                fill=(64, 180, 255, 235),
                outline=(5, 20, 28, 250),
                width=max(2, scale // 5),
            )
            draw.line(
                (
                    origin_xy[0] - marker_radius + 3,
                    origin_xy[1] + marker_radius - 3,
                    origin_xy[0] + marker_radius - 3,
                    origin_xy[1] - marker_radius + 3,
                ),
                fill=(235, 250, 255, 245),
                width=max(2, scale // 6),
            )
            origin_labels.append(((origin_xy[0] + marker_radius + 8, origin_xy[1] - marker_radius - 2), origin_label, "la"))
            labeled_origins.add(origin_label)
        flow_width = max(4, int(scale * width_multiplier))
        if group.get("render_mode") == "dual-cap":
            origin_data = group.get("origin_point") or {}
            origin = projector.grid(origin_data.get("grid_x"), origin_data.get("grid_y")) if valid_map_grid(origin_data.get("grid_x"), origin_data.get("grid_y")) else None
            draw_dual_cap_circuits(
                draw, points, color, flow_width, label_font, map_width, map_height,
                origin=origin, callsign_label=str(group.get("callsign_label") or ""),
            )
        else:
            draw_flow_arrow(draw, points, color, width=flow_width)
        if show_flow_labels and group.get("show_label", True):
            original_label = str(group.get("label"))
            label = str(group.get("compact_label") if compact_labels and group.get("compact_label") else original_label)
            fraction, label_offset = next(
                (spec for prefix, spec in flow_label_specs.items() if original_label.startswith(prefix)),
                (0.55, (14, -24)),
            )
            if group.get("label_fraction") is not None:
                fraction = safe_float(group.get("label_fraction"), fraction)
            custom_offset = group.get("label_offset")
            if isinstance(custom_offset, (list, tuple)) and len(custom_offset) >= 2:
                label_offset = (safe_float(custom_offset[0]), safe_float(custom_offset[1]))
            if compact_labels and original_label.startswith("East Fighter Screen"):
                label_offset = (34, -58)
            route_point = point_along_polyline(points, fraction)
            label_xy = (route_point[0] + label_offset[0], route_point[1] + label_offset[1])
            flow_labels.append((label_xy, route_point, label, color))
    for xy, route_point, _label, color in flow_labels:
        draw.line((route_point[0], route_point[1], xy[0], xy[1]), fill=color + (190,), width=max(2, int(scale * width_multiplier) // 3))
        dot_radius = max(4, int(scale * width_multiplier) // 2)
        draw.ellipse(
            (route_point[0] - dot_radius, route_point[1] - dot_radius, route_point[0] + dot_radius, route_point[1] + dot_radius),
            fill=color + (220,),
            outline=(8, 18, 22, 230),
        )
    for xy, _route_point, label, color in flow_labels:
        draw_fitted_text_box(draw, xy, label, label_font, map_width, map_height, fill=color, bg=LABEL_BG)
    for xy, label, anchor in origin_labels:
        draw_fitted_text_box(draw, xy, label, label_font, map_width, map_height, fill=TEXT, bg=LABEL_BG, anchor=anchor)


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
    add_origin_bullseye_references(origins, syntheses)
    mission_context = mission_context_from_syntheses(syntheses)
    excluded_origins = [
        normalized_label(value)
        for value in mission_context.get("map_excluded_air_origins") or []
        if normalized_label(value)
    ]
    if excluded_origins:
        origins = [
            origin
            for origin in origins
            if not any(token in normalized_label(origin.get("name")) for token in excluded_origins)
        ]
    if not origins:
        raise SystemExit(f"No active enemy fighter/strike squadron origins found within {args.radius_nm:g} NM.")
    flow_groups = (
        package_flow_groups(packages, syntheses, context_key=args.combined_flow_context_key)
        if include_flow and args.show_combined_flows
        else []
    )
    named_positions = (
        merge_named_positions(named_position_points(packages), sa10_named_positions(syntheses, packages))
        if include_flow
        else []
    )
    if include_flow and args.combined_crop_mode != "objective-area":
        named_positions = [position for position in named_positions if not position.get("objective_only")]
    objective_positions = objective_crop_points(syntheses, packages, named_positions) if include_flow else []
    air_defenses = collect_strategic_air_defenses(packages) if include_flow and args.combined_threat_rings else []
    visible_enemy_units = (
        collect_objective_battalions(cam_decode, packages, mission_context)
        if include_flow and args.show_visible_enemy_units
        else []
    )
    if include_flow and args.combined_threat_rings:
        air_defenses = apply_context_air_defense_ring_overrides(air_defenses, named_positions, mission_context)

    crop = crop_for_combined_map(anchors, flow_groups, named_positions, objective_positions, visible_enemy_units, args) if include_flow else crop_for_air_threat_map(origins, anchors, args)
    inset_layout = bool(args.combined_objective_inset_16x9 and include_flow and args.combined_crop_mode == "objective-area")
    base, source_scale_x, source_scale_y, _ = open_base_map(args.map_source or (args.campaign_dir / "Korea.tm"))
    source_crop = (
        max(0, math.floor(crop[0] * source_scale_x)),
        max(0, math.floor(crop[1] * source_scale_y)),
        min(base.width, math.ceil(crop[2] * source_scale_x)),
        min(base.height, math.ceil(crop[3] * source_scale_y)),
    )
    crop_image = base.crop(source_crop).convert("RGBA")
    inset_background: Image.Image | None = None
    inset_canvas_crop: tuple[int, int, int, int] | None = None
    if inset_layout:
        aspect = parse_aspect_ratio(args.aspect_ratio)
        crop_height_grid = crop[3] - crop[1]
        background_width_grid = max(crop[2] - crop[0], int(math.ceil(crop_height_grid * aspect)))
        crop_center_x = (crop[0] + crop[2]) / 2
        background_left = max(0, math.floor(crop_center_x - background_width_grid / 2))
        background_right = min(MAP_GRID_SIZE, background_left + background_width_grid)
        background_left = max(0, background_right - background_width_grid)
        inset_canvas_crop = (background_left, crop[1], background_right, crop[3])
        background_source_crop = (
            max(0, math.floor(background_left * source_scale_x)),
            max(0, math.floor(crop[1] * source_scale_y)),
            min(base.width, math.ceil(background_right * source_scale_x)),
            min(base.height, math.ceil(crop[3] * source_scale_y)),
        )
        inset_background = base.crop(background_source_crop).convert("RGBA")
    if hasattr(base, "close"):
        base.close()
    map_width = (crop[2] - crop[0]) * args.scale
    map_height = (crop[3] - crop[1]) * args.scale
    map_image = crop_image.resize((map_width, map_height), Image.Resampling.BICUBIC)

    overlay = Image.new("RGBA", (map_width, map_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    projector = Projector(crop, args.scale)
    if args.presentation_profile == "slide":
        label_multiplier = args.slide_label_multiplier
        small_multiplier = args.slide_small_label_multiplier
        flow_width_multiplier = args.slide_flow_width_multiplier
    else:
        label_multiplier = 1.0
        small_multiplier = 1.0
        flow_width_multiplier = 1.0
    title_font = load_font(max(20, int(args.scale * 2.4 * label_multiplier)), bold=True)
    label_font = load_font(max(15, int(args.scale * 1.45 * label_multiplier)), bold=True)
    small_font = load_font(max(13, int(args.scale * 1.15 * small_multiplier)))
    threat_label_font = label_font if args.presentation_profile == "slide" else small_font

    if air_defenses:
        draw_low_opacity_air_defense_rings(
            overlay,
            projector,
            air_defenses,
            threat_label_font,
            args.combined_threat_opacity,
            args.combined_threat_style,
            compact_labels=args.presentation_profile == "slide",
            named_positions=named_positions,
        )
    if include_flow and args.show_killboxes:
        draw_context_killboxes(overlay, projector, mission_context)

    anchor_points = [projector.grid(anchor.get("grid_x"), anchor.get("grid_y")) for anchor in anchors]
    ax = [point[0] for point in anchor_points]
    ay = [point[1] for point in anchor_points]
    ao_box = (min(ax) - 18, min(ay) - 18, max(ax) + 18, max(ay) + 18)
    if not include_flow:
        draw.rounded_rectangle(ao_box, radius=18, outline=BLUE + (220,), width=4, fill=BLUE_SOFT)
        draw_text_box(draw, (ao_box[0] + 8, ao_box[1] - 10), "PLAYER AO", label_font, fill=BLUE, bg=LABEL_BG)

    if (not include_flow or args.show_combined_air_axes) and not inset_layout:
        for origin in origins:
            target_anchor = origin.get("nearest_anchor") or anchors[0]
            end = projector.grid(target_anchor.get("grid_x"), target_anchor.get("grid_y"))
            origin_xy = projector.grid(origin.get("grid_x"), origin.get("grid_y"))
            start = clip_segment_to_rect(origin_xy, end, map_width, map_height)
            draw_arrow(draw, start, end, width=max(5, args.scale // 2))

    if include_flow:
        draw_flow_groups(
            draw,
            projector,
            flow_groups,
            label_font,
            args.scale,
            map_width,
            map_height,
            width_multiplier=flow_width_multiplier,
            compact_labels=args.presentation_profile == "slide",
            show_origin_labels=False,
            show_flow_labels=args.show_combined_flow_labels,
        )
        marker_size = max(9, int(args.scale * args.slide_marker_multiplier)) if args.presentation_profile == "slide" else 9
        if args.show_flow_origin_labels:
            draw_friendly_origins(
                draw,
                projector,
                flow_origin_points(packages),
                label_font,
                args.scale,
                map_width,
                map_height,
            )
        if visible_enemy_units:
            draw_mil2525_battalions_exact(overlay, projector, visible_enemy_units)
        display_positions = named_positions
        if args.show_visible_enemy_units and args.combined_crop_mode == "objective-area":
            display_labels = mission_context.get("map_objective_display_labels") or args.combined_crop_labels or []
            wanted = {normalized_marker_label(label) for label in display_labels}
            display_positions = [
                position
                for position in named_positions
                if normalized_marker_label(position.get("label")) in wanted
            ]
        if inset_layout:
            edge_cue_positions = [position for position in display_positions if position.get("edge_cue")]
            display_positions = [position for position in display_positions if not position.get("edge_cue")]
        else:
            edge_cue_positions = []
        draw_named_positions(draw, projector, display_positions, label_font, marker_size=marker_size, map_width=map_width, map_height=map_height)
        if args.show_package_color_legend:
            draw_context_package_color_legend(draw, mission_context, label_font, map_width, map_height)

    origin_label_font = load_font(
        max(15, int(args.scale * 1.45 * (args.slide_origin_label_multiplier if args.presentation_profile == "slide" else 1.0))),
        bold=True,
    )
    offshore_origin_label_font = load_font(
        max(9, int(getattr(origin_label_font, "size", 15) * args.combined_offshore_origin_label_scale)),
        bold=True,
    )
    label_offsets = [(16, -34), (16, 16), (-16, -34), (-16, 16), (24, -4), (-24, -4)]
    visible_origins = origins if (not include_flow or args.show_combined_air_axes) and not inset_layout else []
    for index, origin in enumerate(visible_origins):
        origin_xy = projector.grid(origin.get("grid_x"), origin.get("grid_y"))
        target_anchor = origin.get("nearest_anchor") or anchors[0]
        target_xy = projector.grid(target_anchor.get("grid_x"), target_anchor.get("grid_y"))
        xy = clip_segment_to_rect(origin_xy, target_xy, map_width, map_height)
        radius = max(9, int(args.scale * (args.slide_marker_multiplier if args.presentation_profile == "slide" else 1.0)))
        if is_airbase_origin(origin):
            draw.rectangle(
                (xy[0] - radius - 2, xy[1] - radius - 2, xy[0] + radius + 2, xy[1] + radius + 2),
                fill=(40, 0, 0, 155),
            )
            draw.rectangle(
                (xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius),
                fill=(235, 38, 38, 245),
                outline=(255, 240, 225, 255),
                width=2,
            )
            draw.line(
                (xy[0] - radius + 3, xy[1] + radius - 3, xy[0] + radius - 3, xy[1] - radius + 3),
                fill=(255, 245, 235, 245),
                width=max(2, radius // 4),
            )
        else:
            draw.polygon(
                [(xy[0], xy[1] - radius), (xy[0] + radius, xy[1]), (xy[0], xy[1] + radius), (xy[0] - radius, xy[1])],
                fill=RED + (245,),
                outline=(255, 245, 245, 255),
            )
        if point_inside_image(origin_xy, map_width, map_height, 20):
            dx, dy = label_offsets[index % len(label_offsets)]
            label_xy = (xy[0] + dx, xy[1] + dy)
            anchor = "la" if dx >= 0 else "ra"
        else:
            label_xy, anchor = edge_label_position(xy, map_width, map_height)
        if args.combined_edge_air_origin_name_only and not point_inside_image(origin_xy, map_width, map_height, 20) and is_airbase_origin(origin):
            origin_label = str(origin.get("name") or "Airbase").split("(", 1)[0].strip()
        else:
            origin_label = compact_label_text(origin) if args.presentation_profile == "slide" else label_text(origin)
        label_fill = (255, 226, 218) if is_airbase_origin(origin) else TEXT
        label_bg = (72, 8, 8, 210) if is_airbase_origin(origin) else LABEL_BG
        selected_origin_font = offshore_origin_label_font if not is_airbase_origin(origin) else origin_label_font
        draw_fitted_text_box(draw, label_xy, origin_label, selected_origin_font, map_width, map_height, fill=label_fill, bg=label_bg, anchor=anchor)
        meta = f"{compass_sector(math.degrees(math.atan2(safe_float(origin['grid_x']) - safe_float(origin['nearest_anchor']['grid_x']), safe_float(origin['grid_y']) - safe_float(origin['nearest_anchor']['grid_y']))) % 360)} | {origin['distance_nm']:.0f} NM | {origin['available_airframes']} a/c"
        if args.presentation_profile != "slide":
            meta_y = label_xy[1] + (24 if anchor == "la" else 24)
            draw_text_box(draw, (label_xy[0], meta_y), meta, small_font, fill=(255, 205, 205), bg=LABEL_BG, anchor=anchor)

    draw_scale_and_north(overlay, crop, args.scale, small_font)
    if args.show_map_title:
        title = args.combined_title if include_flow else args.title
        subtitle = (
            f"Package flow, named positions, and active enemy fighter/strike origins within {args.radius_nm:g} NM"
            if include_flow
            else f"Active enemy fighter/strike squadron origins within {args.radius_nm:g} NM; arrows show likely axes toward player AO"
        )
        draw_text_box(draw, (26, 26), title, title_font, fill=TEXT, bg=(9, 13, 15, 225))
        draw_text_box(
            draw,
            (26, 62 + int(20 * (label_multiplier - 1.0))),
            subtitle,
            small_font,
            fill=(255, 220, 220),
            bg=(9, 13, 15, 205),
        )

    output = Image.alpha_composite(map_image, overlay)
    if inset_layout:
        # Preserve an undistorted, full-height tactical crop and fill the
        # surrounding 16:9 canvas with contiguous map terrain.
        aspect = parse_aspect_ratio(args.aspect_ratio)
        canvas_width = max(output.width, int(round(output.height * aspect)))
        canvas = inset_background.resize((canvas_width, output.height), Image.Resampling.BICUBIC) if inset_background else Image.new("RGBA", (canvas_width, output.height), (12, 17, 20, 255))
        x_offset = (canvas_width - output.width) // 2
        canvas.paste(output, (x_offset, 0))
        output = canvas
        if inset_canvas_crop:
            canvas_draw = ImageDraw.Draw(output, "RGBA")
            canvas_projector = Projector(inset_canvas_crop, args.scale)
            radius = max(9, int(args.scale * (args.slide_marker_multiplier if args.presentation_profile == "slide" else 1.0)))
            for origin in origins:
                target_anchor = origin.get("nearest_anchor") or anchors[0]
                origin_xy = canvas_projector.grid(origin.get("grid_x"), origin.get("grid_y"))
                target_xy = canvas_projector.grid(target_anchor.get("grid_x"), target_anchor.get("grid_y"))
                xy = clip_segment_to_rect(origin_xy, target_xy, output.width, output.height)
                draw_arrow(canvas_draw, xy, target_xy, width=max(5, args.scale // 2))
                if is_airbase_origin(origin):
                    canvas_draw.rectangle((xy[0] - radius - 2, xy[1] - radius - 2, xy[0] + radius + 2, xy[1] + radius + 2), fill=(40, 0, 0, 155))
                    canvas_draw.rectangle((xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius), fill=(235, 38, 38, 245), outline=(255, 240, 225, 255), width=2)
                    canvas_draw.line((xy[0] - radius + 3, xy[1] + radius - 3, xy[0] + radius - 3, xy[1] - radius + 3), fill=(255, 245, 235, 245), width=max(2, radius // 4))
                else:
                    canvas_draw.polygon([(xy[0], xy[1] - radius), (xy[0] + radius, xy[1]), (xy[0], xy[1] + radius), (xy[0] - radius, xy[1])], fill=RED + (245,), outline=(255, 245, 245, 255))
                label_xy, anchor = edge_label_position(xy, output.width, output.height)
                if args.combined_edge_air_origin_name_only and is_airbase_origin(origin):
                    origin_label = str(origin.get("name") or "Airbase").split("(", 1)[0].strip()
                else:
                    origin_label = compact_label_text(origin) if args.presentation_profile == "slide" else label_text(origin)
                selected_font = offshore_origin_label_font if not is_airbase_origin(origin) else origin_label_font
                draw_fitted_text_box(canvas_draw, label_xy, origin_label, selected_font, output.width, output.height, fill=(255, 226, 218) if is_airbase_origin(origin) else TEXT, bg=(72, 8, 8, 210) if is_airbase_origin(origin) else LABEL_BG, anchor=anchor)
            if edge_cue_positions:
                draw_named_positions(canvas_draw, canvas_projector, edge_cue_positions, label_font, marker_size=marker_size, map_width=output.width, map_height=output.height)
    out = output_path or args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    pnginfo = PngInfo()
    pnginfo.add_text("bms_map_product", args.combined_title if include_flow else args.title)
    pnginfo.add_text("bms_crop_bounds", json.dumps(list(crop)))
    pnginfo.add_text("bms_north_up", "true")
    pnginfo.add_text("bms_aspect_ratio", args.aspect_ratio or "native")
    if args.combined_objective_inset_16x9:
        pnginfo.add_text("bms_objective_layout", "full-height tactical inset")
    output.convert("RGB").save(out, pnginfo=pnginfo)
    return out


def centroid(points: list[dict[str, Any]]) -> tuple[float, float] | None:
    clean = [point for point in points if point.get("grid_x") is not None and point.get("grid_y") is not None]
    if not clean:
        return None
    return (
        sum(safe_float(point.get("grid_x")) for point in clean) / len(clean),
        sum(safe_float(point.get("grid_y")) for point in clean) / len(clean),
    )


def valid_map_grid(grid_x: Any, grid_y: Any) -> bool:
    if grid_x is None or grid_y is None:
        return False
    x = safe_float(grid_x)
    y = safe_float(grid_y)
    return 0.0 <= x <= MAP_GRID_SIZE and 0.0 <= y <= MAP_GRID_SIZE


def mission_context_from_syntheses(syntheses: list[dict[str, Any]]) -> dict[str, Any]:
    for synthesis in syntheses:
        context = synthesis.get("mission_context")
        if isinstance(context, dict) and context:
            return context
    return {}


def flight_map(packages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        normalized_label(flight.get("callsign")): flight
        for package in packages
        for flight in package.get("flights") or []
        if flight.get("callsign")
    }


def first_matching_waypoint(flight: dict[str, Any] | None, action: str | None) -> dict[str, Any] | None:
    if not flight:
        return None
    for waypoint in flight.get("key_waypoints") or []:
        if action and waypoint.get("action") != action:
            continue
        if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
            continue
        return waypoint
    return None


def context_map_mark_overrides(syntheses: list[dict[str, Any]], packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    context = mission_context_from_syntheses(syntheses)
    overrides = context.get("map_mark_overrides") or []
    if not isinstance(overrides, list):
        return []

    flights = flight_map(packages)
    transformed_points = [
        point
        for synthesis in syntheses
        for point in (synthesis.get("planning", {}).get("transformed_points") or [])
    ]
    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in overrides:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("name") or "").strip()
        if not label:
            continue
        if label.upper() in seen:
            continue

        explicit_x = item.get("grid_x")
        explicit_y = item.get("grid_y")
        if valid_map_grid(explicit_x, explicit_y):
            result.append(
                {
                    "label": label,
                    "grid_x": explicit_x,
                    "grid_y": explicit_y,
                    "name": item.get("name"),
                    "source_label": item.get("from_ppt_label") or item.get("source_label"),
                    "objective_only": bool(item.get("objective_only", False)),
                    "label_scale": safe_float(item.get("label_scale"), 1.0),
                    "edge_cue": bool(item.get("edge_cue", False)),
                }
            )
            seen.add(label.upper())
            continue

        source_label = normalized_label(item.get("from_ppt_label") or item.get("source_label") or label)
        candidates: list[dict[str, Any]] = []
        for point in transformed_points:
            point_label = normalized_label(point.get("display") or point.get("label"))
            grid = point.get("campaign_grid") or {}
            if point.get("kind") != "ppt" or point_label != source_label:
                continue
            if not grid.get("valid_for_map", True) or not valid_map_grid(grid.get("grid_x"), grid.get("grid_y")):
                continue
            candidates.append(point)
        if not candidates:
            continue

        anchor = first_matching_waypoint(
            flights.get(normalized_label(item.get("nearest_callsign"))),
            item.get("nearest_action"),
        )
        if anchor:
            chosen = min(
                candidates,
                key=lambda point: math.hypot(
                    safe_float((point.get("campaign_grid") or {}).get("grid_x")) - safe_float(anchor.get("grid_x")),
                    safe_float((point.get("campaign_grid") or {}).get("grid_y")) - safe_float(anchor.get("grid_y")),
                ),
            )
        else:
            chosen = candidates[0]
        grid = chosen.get("campaign_grid") or {}
        result.append(
            {
                "label": label,
                "grid_x": grid.get("grid_x"),
                "grid_y": grid.get("grid_y"),
                "name": item.get("name"),
                "source_label": item.get("from_ppt_label") or item.get("source_label"),
                "objective_only": bool(item.get("objective_only", False)),
                "label_scale": safe_float(item.get("label_scale"), 1.0),
                "edge_cue": bool(item.get("edge_cue", False)),
            }
        )
        seen.add(label.upper())
    return result


def contextual_air_defense_label(
    air_defense: dict[str, Any],
    named_positions: list[dict[str, Any]],
    compact: bool,
) -> str:
    base_label = air_defense_threat_label(air_defense)
    is_sa10 = normalized_label(base_label).startswith("SA10")
    if is_sa10:
        for position in named_positions:
            label = compact_named_label(position.get("label"))
            if normalized_label(label) not in {"10W", "10E", "10S", "10A", "10B", "10C"}:
                continue
            distance = math.hypot(
                safe_float(air_defense.get("grid_x")) - safe_float(position.get("grid_x")),
                safe_float(air_defense.get("grid_y")) - safe_float(position.get("grid_y")),
            )
            if distance <= 2.5:
                return label
    return compact_sam_label(base_label) if compact else base_label


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


def compact_callsign(callsign: Any) -> str:
    return str(callsign or "").replace(" ", "")


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


def flow_origin_points(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, float, float]] = set()
    origins: list[dict[str, Any]] = []
    for package in packages:
        for flight in package.get("flights") or []:
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
            target = waypoint.get("target") or {}
            name = str(target.get("name") or "Departure").strip()
            label = short_origin_label(name)
            key = (label, round(safe_float(waypoint.get("grid_x")), 1), round(safe_float(waypoint.get("grid_y")), 1))
            if key in seen:
                continue
            seen.add(key)
            origins.append({"label": label, "grid_x": waypoint.get("grid_x"), "grid_y": waypoint.get("grid_y")})
    return origins


def color_from_context(value: Any, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (safe_int(value[0], fallback[0]), safe_int(value[1], fallback[1]), safe_int(value[2], fallback[2]))
    return FLOW_COLOR_NAMES.get(str(value or "").strip().lower(), fallback)


def context_flow_stage_point(
    stage: dict[str, Any],
    group_flights: list[dict[str, Any]],
    named_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    stage_type = str(stage.get("type") or "").lower()
    if stage_type == "origin":
        return flow_origin_point(group_flights)
    if stage_type == "action":
        action = str(stage.get("action") or "").strip()
        occurrence = stage.get("occurrence")
        if occurrence is not None:
            return flow_stage_occurrence(group_flights, action, safe_int(occurrence))
        return flow_stage_point(group_flights, {action})
    if stage_type in {"ini", "target", "mark"}:
        return named_lookup.get(normalized_label(stage.get("label")))
    if valid_map_grid(stage.get("grid_x"), stage.get("grid_y")):
        return {"grid_x": stage.get("grid_x"), "grid_y": stage.get("grid_y")}
    return None


def context_package_flow_groups(
    packages: list[dict[str, Any]],
    syntheses: list[dict[str, Any]] | None,
    context_key: str = "map_flow_groups",
) -> list[dict[str, Any]]:
    if not syntheses:
        return []
    context = mission_context_from_syntheses(syntheses)
    flow_specs = context.get(context_key) or context.get("map_flow_groups") or []
    if not isinstance(flow_specs, list):
        return []

    flights = flight_map(packages)
    named_positions = merge_named_positions(
        named_position_points(packages),
        context_map_mark_overrides(syntheses, packages),
    )
    named_lookup = {normalized_label(point.get("label")): point for point in named_positions}
    groups: list[dict[str, Any]] = []
    for spec in flow_specs:
        if not isinstance(spec, dict):
            continue
        group_flights = [
            flights[key]
            for key in (normalized_label(callsign) for callsign in spec.get("callsigns") or [])
            if key in flights
        ]
        if not group_flights:
            continue
        stages = [
            context_flow_stage_point(stage, group_flights, named_lookup)
            for stage in spec.get("stages") or []
            if isinstance(stage, dict)
        ]
        path = [point for point in stages if point]
        if len(path) < 2:
            continue
        origin = flow_origin_point(group_flights)
        groups.append(
            {
                "label": str(spec.get("label") or "Package Flow"),
                "compact_label": str(spec.get("compact_label") or spec.get("label") or "Flow"),
                "points": path,
                "color": color_from_context(spec.get("color"), FLOW_BLUE),
                "origin_label": (origin or {}).get("origin_label"),
                "origin_point": origin,
                "callsign_label": str(spec.get("callsign_label") or " / ".join(spec.get("callsigns") or [])),
                "show_label": spec.get("show_label", True),
                "label_fraction": spec.get("label_fraction"),
                "label_offset": spec.get("label_offset"),
                "render_mode": str(spec.get("render_mode") or ""),
            }
        )
    return groups


def package_flow_groups(
    packages: list[dict[str, Any]],
    syntheses: list[dict[str, Any]] | None = None,
    context_key: str = "map_flow_groups",
) -> list[dict[str, Any]]:
    custom_groups = context_package_flow_groups(packages, syntheses, context_key=context_key)
    if custom_groups:
        return custom_groups

    flights = [flight for package in packages for flight in package.get("flights") or []]
    groups: list[dict[str, Any]] = []
    sead_flights = [flight for flight in flights if str(flight.get("mission") or "").upper() in {"SEAD", "SAD"}]
    barcap_flights = [flight for flight in flights if str(flight.get("mission") or "").upper() == "BARCAP"]
    east_screen = [flight for flight in barcap_flights if "F-15" in str(flight.get("aircraft_type") or flight.get("aircraft_class") or "")]
    escort_cap = [flight for flight in barcap_flights if flight not in east_screen]

    specs = [
        ("SEAD / DEAD Flow", "SEAD", sead_flights, (FLOW_BLUE[0], FLOW_BLUE[1], FLOW_BLUE[2]), "sead"),
        ("Escort / BARCAP Flow", "CAP", escort_cap, (98, 235, 128), "cap"),
        ("East Fighter Screen", "Eagles", east_screen, (255, 199, 71), "cap"),
    ]
    for label, compact_role, group_flights, color, mode in specs:
        if not group_flights:
            continue
        flight_names = ", ".join(
            str(flight.get("callsign") or f"Flight {flight.get('camp_id')}")
            for flight in group_flights
        )
        compact_names = ", ".join(
            compact_callsign(flight.get("callsign") or f"Flight {flight.get('camp_id')}")
            for flight in group_flights
        )
        display_label = f"{label} ({flight_names})" if flight_names else label
        compact_label = f"{compact_role} ({compact_names})" if compact_names else compact_role
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
            groups.append({"label": display_label, "compact_label": compact_label, "points": path, "color": color, "origin_label": (origin or {}).get("origin_label")})
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
            if key in seen or not grid.get("valid_for_map", True) or not valid_map_grid(grid.get("grid_x"), grid.get("grid_y")):
                continue
            seen.add(key)
            points.append({"label": label, "grid_x": grid.get("grid_x"), "grid_y": grid.get("grid_y")})
    return points


def objective_crop_points(
    syntheses: list[dict[str, Any]],
    packages: list[dict[str, Any]],
    named_positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[tuple[str, float, float]] = set()
    points: list[dict[str, Any]] = []

    def add(label: str, grid_x: Any, grid_y: Any) -> None:
        if not valid_map_grid(grid_x, grid_y):
            return
        key = (label.upper(), round(safe_float(grid_x), 1), round(safe_float(grid_y), 1))
        if key in seen:
            return
        seen.add(key)
        points.append({"label": label, "grid_x": grid_x, "grid_y": grid_y})

    for synthesis, package in zip(syntheses, packages):
        ini_points = iter_named_ini_points(synthesis, package)
        for point in objective_ini_points(ini_points, package) or ini_points:
            grid = point.get("campaign_grid") or {}
            label = str(point.get("label") or point.get("display") or "").strip()
            add(label, grid.get("grid_x"), grid.get("grid_y"))

    for position in named_positions:
        label = str(position.get("label") or "").strip()
        upper = label.upper()
        if upper.startswith("SA-") or upper.startswith("SA") or upper in {"SA6", "SA10"}:
            add(label, position.get("grid_x"), position.get("grid_y"))

    return points


def sa10_named_positions(syntheses: list[dict[str, Any]], packages: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    overrides = context_map_mark_overrides(syntheses, packages)
    if overrides:
        return overrides

    context_names: dict[str, str] = {}
    for package in packages:
        for item in (package.get("human_context") or {}).get("target_opportunities", []):
            raw_label = str(item.get("label") or "").strip()
            raw_name = str(item.get("name") or "").strip()
            combined = f"{raw_label} {raw_name}".upper()
            compact = combined.replace("-", "").replace(" ", "")
            if "SA-10" not in combined and not any(token in compact for token in ("10W", "10E", "10S", "10WEST", "10EAST", "10SOUTH")):
                continue
            display = raw_label or raw_name
            if "10W" in compact or "10WEST" in compact:
                context_names["SA-10 W"] = display
            elif "10E" in compact or "10EAST" in compact:
                context_names["SA-10 E"] = display
            elif "10S" in compact or "10SOUTH" in compact:
                context_names["SA-10 S"] = display
            if raw_label:
                context_names[raw_label.upper()] = display
    if not context_names:
        return []
    tactical_points = [
        point
        for group in package_flow_groups(packages, syntheses)
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
            if not grid.get("valid_for_map", True) or not valid_map_grid(grid.get("grid_x"), grid.get("grid_y")):
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
        if key not in context_names:
            continue
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
    marker_size: int = 9,
    map_width: int | None = None,
    map_height: int | None = None,
) -> None:
    fixed_offsets = {
        "SA-10 WEST": (-18, -34, "ra"),
        "SA-10 EAST": (15, -28, "la"),
        "SA-10 SOUTH": (14, 20, "la"),
        "SA6": (14, 22, "la"),
        "10W": (-18, -34, "ra"),
        "10E": (15, -28, "la"),
        "10S": (14, 20, "la"),
        "10A": (-15, -26, "ra"),
        "10B": (15, -28, "la"),
        "10C": (15, 30, "la"),
        "11": (-15, 22, "ra"),
        "IP1": (15, 22, "la"),
        "IP2": (15, -22, "la"),
        "IP M7": (-15, 20, "ra"),
        "IP C5": (-15, -24, "ra"),
        "IP P7": (15, 20, "la"),
        "IP HAM6": (15, -24, "la"),
        "6": (14, 22, "la"),
        "JEW": (14, -11, "la"),
        "CRO": (14, 16, "la"),
        "TIG": (14, 18, "la"),
    }
    for index, position in enumerate(positions):
        xy = projector.grid(position.get("grid_x"), position.get("grid_y"))
        is_edge_cue = False
        if map_width is not None and map_height is not None and not point_inside_image(xy, map_width, map_height, marker_size + 4):
            if not position.get("edge_cue"):
                continue
            clipped = clip_segment_to_rect(xy, (map_width / 2, map_height / 2), map_width, map_height)
            xy = (
                min(map_width - marker_size - 3, max(marker_size + 3, clipped[0])),
                min(map_height - marker_size - 3, max(marker_size + 3, clipped[1])),
            )
            is_edge_cue = True
        size = marker_size
        diamond = [(xy[0], xy[1] - size), (xy[0] + size, xy[1]), (xy[0], xy[1] + size), (xy[0] - size, xy[1])]
        draw.polygon(diamond, fill=GREEN + (230,), outline=(0, 18, 5, 255))
        label = compact_named_label(position.get("label"))
        dx, dy, anchor = fixed_offsets.get(label.upper(), (13, -10 if index % 2 == 0 else 18, "la"))
        if is_edge_cue and map_width is not None and map_height is not None:
            if xy[0] >= map_width / 2:
                dx, dy, anchor = -15, 18, "ra"
            else:
                dx, dy, anchor = 15, 18, "la"
        label_scale = max(0.25, safe_float(position.get("label_scale"), 1.0))
        position_font = (
            load_font(max(8, int(getattr(font, "size", 16) * label_scale)), bold=True)
            if abs(label_scale - 1.0) > 0.01
            else font
        )
        if map_width is not None and map_height is not None:
            draw_fitted_text_box(draw, (xy[0] + dx, xy[1] + dy), label, position_font, map_width, map_height, fill=TEXT, bg=LABEL_BG, anchor=anchor)
        else:
            draw_text_box(draw, (xy[0] + dx, xy[1] + dy), label, position_font, fill=TEXT, bg=LABEL_BG, anchor=anchor)


def draw_friendly_origins(
    draw: ImageDraw.ImageDraw,
    projector: Projector,
    origins: list[dict[str, Any]],
    font: ImageFont.ImageFont,
    scale: int,
    map_width: int,
    map_height: int,
) -> None:
    for origin in origins:
        xy = projector.grid(origin.get("grid_x"), origin.get("grid_y"))
        if not point_inside_image(xy, map_width, map_height, 18):
            continue
        marker_radius = max(8, int(scale * 0.85))
        draw.rectangle(
            (
                xy[0] - marker_radius,
                xy[1] - marker_radius,
                xy[0] + marker_radius,
                xy[1] + marker_radius,
            ),
            fill=(64, 180, 255, 238),
            outline=(5, 20, 28, 255),
            width=max(2, scale // 5),
        )
        draw.line(
            (
                xy[0] - marker_radius + 3,
                xy[1] + marker_radius - 3,
                xy[0] + marker_radius - 3,
                xy[1] - marker_radius + 3,
            ),
            fill=(235, 250, 255, 245),
            width=max(2, scale // 6),
        )
        label_xy = (xy[0] + marker_radius + 8, xy[1] - marker_radius - 2)
        draw_fitted_text_box(draw, label_xy, str(origin.get("label") or "Departure"), font, map_width, map_height, fill=TEXT, bg=LABEL_BG, anchor="la")


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
    flow_groups = package_flow_groups(packages, syntheses)
    named_positions = merge_named_positions(named_position_points(packages), sa10_named_positions(syntheses, packages))
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
    parser.add_argument(
        "--combined-crop-labels",
        nargs="+",
        help="Frame --combined-out around these named INI/PPT/context labels, e.g. CRO SA5 10W 10E BAN WWO.",
    )
    parser.add_argument(
        "--combined-objective-explicit-grid-bounds",
        type=float,
        nargs=4,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        help="Exact objective crop in BMS grid coordinates; overrides objective crop labels.",
    )
    parser.add_argument(
        "--combined-crop-label-margin-grid",
        type=float,
        default=8.0,
        help="Extra grid-cell margin around --combined-crop-labels before enforcing the output aspect ratio.",
    )
    parser.add_argument(
        "--combined-crop-mode",
        choices=("target-area", "objective-area"),
        default="target-area",
        help="Frame --combined-out as a target-area overview or a tighter objective-area crop.",
    )
    parser.add_argument(
        "--combined-objective-margin-grid",
        type=float,
        default=7.0,
        help="Extra grid-cell margin around named objective positions when --combined-crop-mode objective-area is used.",
    )
    parser.add_argument(
        "--combined-objective-crop-top-fraction",
        type=float,
        default=0.0,
        help="Trim this fraction from the north/top of an objective-area combined crop after framing. Use 0.25 to remove the top quarter.",
    )
    parser.add_argument(
        "--combined-objective-north-bound-label",
        help="For objective-area combined crops, set the north edge relative to this named marker label, for example SA6.",
    )
    parser.add_argument(
        "--combined-objective-north-padding-nm",
        type=float,
        default=0.0,
        help="Distance north of --combined-objective-north-bound-label to use as the objective crop's top edge.",
    )
    parser.add_argument(
        "--combined-include-flow-origins-in-bounds",
        action="store_true",
        help="Include friendly package origin airbases in the combined-map crop. Use this for a full route/threat overview.",
    )
    parser.add_argument("--combined-threat-opacity", type=float, default=0.26, help="Opacity for strategic ADA rings on --combined-out. Range 0.0-1.0.")
    parser.add_argument(
        "--combined-threat-style",
        choices=("target-area", "route-reference"),
        default="target-area",
        help="ADA ring style for --combined-out. target-area keeps soft existing target-map rings; route-reference uses near-solid 738-style WEZ outlines.",
    )
    parser.add_argument("--no-combined-threat-rings", dest="combined_threat_rings", action="store_false", help="Disable strategic ADA rings on --combined-out.")
    parser.set_defaults(combined_threat_rings=True)
    parser.add_argument("--scale", type=int, default=10, help="Output scale multiplier for the cropped map.")
    parser.add_argument("--aspect-ratio", default="16:9", help="Slide map-area aspect ratio. Defaults to 16:9.")
    parser.add_argument("--title", default="Enemy Air Threat Axes", help="Map title.")
    parser.add_argument("--combined-title", default="Package Flow + Enemy Air Threat Axes", help="Combined map title.")
    parser.add_argument("--flow-title", default="Package Flow Overview", help="Flow map title.")
    parser.add_argument(
        "--presentation-profile",
        choices=("reference", "slide"),
        default="reference",
        help="Use reference for data-rich standalone map PNGs, or slide for larger labels/strokes intended to be shrunk onto briefing slides.",
    )
    parser.add_argument(
        "--slide-label-multiplier",
        type=float,
        default=2.25,
        help="Font multiplier for labels when --presentation-profile slide is used.",
    )
    parser.add_argument(
        "--slide-small-label-multiplier",
        type=float,
        default=1.85,
        help="Font multiplier for secondary labels when --presentation-profile slide is used.",
    )
    parser.add_argument(
        "--slide-origin-label-multiplier",
        type=float,
        default=1.65,
        help="Font multiplier for enemy-origin labels when --presentation-profile slide is used.",
    )
    parser.add_argument(
        "--slide-flow-width-multiplier",
        type=float,
        default=1.45,
        help="Route/flow stroke multiplier when --presentation-profile slide is used.",
    )
    parser.add_argument(
        "--slide-marker-multiplier",
        type=float,
        default=1.25,
        help="Marker-size multiplier when --presentation-profile slide is used.",
    )
    parser.add_argument(
        "--show-map-title",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Draw the map-internal title/subtitle. Use --no-show-map-title when the slide already has a title rail.",
    )
    parser.add_argument(
        "--show-flow-origin-labels",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Label friendly package departure airbases on combined flow maps. Best for route overviews; keep disabled for target/objective maps.",
    )
    parser.add_argument(
        "--show-combined-flow-labels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Draw role/callsign labels on combined package-flow lines. Disable for tight objective close-ups when labels obscure the objective.",
    )
    parser.add_argument(
        "--show-combined-flows",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Draw friendly package-flow lines on combined maps.",
    )
    parser.add_argument(
        "--combined-flow-context-key",
        default="map_flow_groups",
        help="Mission-context key containing the flow-group specification for this product.",
    )
    parser.add_argument(
        "--show-combined-air-axes",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Draw enemy air-origin axes and labels on combined maps.",
    )
    parser.add_argument(
        "--combined-edge-air-origin-name-only",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use only the airbase name when an enemy air origin is clipped to the map edge.",
    )
    parser.add_argument(
        "--combined-offshore-origin-label-scale",
        type=float,
        default=1.0,
        help="Scale factor for offshore enemy-origin labels; useful for decluttering tight objective maps.",
    )
    parser.add_argument(
        "--combined-objective-inset-16x9",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Place a narrow objective close-up as a full-height inset on an exact 16:9 canvas instead of widening its tactical crop.",
    )
    parser.add_argument(
        "--show-killboxes",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Draw planner-defined killbox polygons from mission context.",
    )
    parser.add_argument(
        "--show-package-color-legend",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Draw the mission-context package color key on a combined map.",
    )
    parser.add_argument(
        "--show-visible-enemy-units",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Draw visible enemy ground units with hostile MIL-STD-2525-style symbols.",
    )
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
