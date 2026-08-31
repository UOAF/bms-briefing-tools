#!/usr/bin/env python3
"""Render an experimental 3D Falcon BMS target-area terrain view.

The renderer uses BMS campaign grid coordinates for overlays and crops the
Falcon BMS 4.38 new-terrain heightmap directly instead of loading the full
2 GB raster into memory. It is intended as a prototype companion image for
briefing slides, not as a replacement for the checked 2D package maps.
"""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, DrawingArea

from bms_milstd2525 import canonical_unit_kind, unit_glyph_primitives
from matplotlib.patches import Arc, Ellipse, Polygon, Rectangle
from matplotlib.text import Text
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import proj3d
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL.PngImagePlugin import PngInfo

from bms_projection import feet_per_campaign_grid, source_feet_to_campaign_grid
from render_bms_enemy_air_threat_map import collect_objective_battalions

Image.MAX_IMAGE_PIXELS = None

FEET_PER_GRID = feet_per_campaign_grid()
FEET_PER_NM = 6076.11549
GRID_NM = FEET_PER_GRID / FEET_PER_NM
THEATER_GRID_SIZE = 1024.0
HEIGHTMAP_SAMPLES = 32768
MAX_VALID_ELEVATION_FT = 12000.0

PLAYER_ROUTE_COLORS = [
    "#48b8ff",
    "#ffd166",
    "#62e27e",
    "#ff5d8f",
    "#b58cff",
    "#fff478",
]
FLOW_COLOR_NAMES = {
    "blue": "#48b8ff",
    "green": "#62e27e",
    "amber": "#ffd166",
    "yellow": "#ffd166",
    "red": "#ff4242",
}


def mil2525_unit_artist(class_name: str, affiliation: str, size: float, alpha: float = 0.60) -> DrawingArea:
    """Build a screen-facing MIL-STD-2525-style battalion symbol."""
    width = float(size)
    height = float(size) + 13.0
    area = DrawingArea(width, height, 0, 0)
    friendly = affiliation.lower() == "friendly"
    edge = "#3287ff" if friendly else "#ee2828"
    fill = "#deeeff" if friendly else "#ffe1e1"
    # Keep terrain subtly visible through the frame, but never through the
    # actual tactical glyph.  A too-transparent white fill made the draped
    # imagery look like noisy/corrupted icon art at slide scale.
    # At briefing scale, anything below this reads as a broken tile rather
    # than controlled transparency over the draped terrain.
    frame_alpha = max(0.90, min(1.0, alpha))
    ink = (16 / 255.0, 16 / 255.0, 16 / 255.0, 0.98)
    cx = width / 2.0
    cy = size * 0.46
    frame_w = size * (0.92 if friendly else 0.82)
    frame_h = size * (0.58 if friendly else 0.82)
    if friendly:
        area.add_artist(Rectangle((cx - frame_w / 2, cy - frame_h / 2), frame_w, frame_h, facecolor=fill, edgecolor=edge, linewidth=2.2, alpha=frame_alpha))
    else:
        area.add_artist(Polygon([(cx, cy + frame_h / 2), (cx + frame_w / 2, cy), (cx, cy - frame_h / 2), (cx - frame_w / 2, cy)], closed=True, facecolor=fill, edgecolor=edge, linewidth=2.2, alpha=frame_alpha))
    area.add_artist(Text(cx, size + 1.0, "II", color=edge, fontsize=max(8, size * 0.22), weight="bold", ha="center", va="bottom", alpha=0.98))

    symbol_w = frame_w * (0.58 if friendly else 0.48)
    symbol_h = frame_h * (0.58 if friendly else 0.48)
    def line(x1: float, y1: float, x2: float, y2: float, linewidth: float = 1.8) -> None:
        area.add_artist(Line2D([x1, x2], [y1, y2], color=ink, linewidth=linewidth))
    for primitive in unit_glyph_primitives(class_name):
        values = primitive.values
        if primitive.kind == "line":
            line(
                cx + values[0] * symbol_w,
                cy + values[1] * symbol_h,
                cx + values[2] * symbol_w,
                cy + values[3] * symbol_h,
            )
        elif primitive.kind in {"ellipse", "filled_ellipse"}:
            x1, y1, x2, y2 = values
            area.add_artist(
                Ellipse(
                    (cx + (x1 + x2) * symbol_w / 2, cy + (y1 + y2) * symbol_h / 2),
                    (x2 - x1) * symbol_w,
                    (y2 - y1) * symbol_h,
                    fill=primitive.kind == "filled_ellipse",
                    facecolor=ink if primitive.kind == "filled_ellipse" else "none",
                    edgecolor=ink,
                    linewidth=1.9,
                )
            )
        elif primitive.kind == "filled_polygon":
            points = [
                (cx + values[index] * symbol_w, cy + values[index + 1] * symbol_h)
                for index in range(0, len(values), 2)
            ]
            area.add_artist(Polygon(points, closed=True, facecolor=ink, edgecolor=ink))
        elif primitive.kind == "arc":
            x1, y1, x2, y2, theta1, theta2 = values
            area.add_artist(
                Arc(
                    (cx + (x1 + x2) * symbol_w / 2, cy + (y1 + y2) * symbol_h / 2),
                    (x2 - x1) * symbol_w,
                    (y2 - y1) * symbol_h,
                    theta1=theta1,
                    theta2=theta2,
                    edgecolor=ink,
                    linewidth=1.9,
                )
            )
        elif primitive.kind in {"text_e", "text_s"}:
            area.add_artist(
                Text(
                    cx,
                    cy,
                    "E" if primitive.kind == "text_e" else "S",
                    color=ink,
                    fontsize=max(10, size * 0.28),
                    weight="bold",
                    ha="center",
                    va="center",
                )
            )
    if canonical_unit_kind(class_name) == "headquarters":
        staff_x = cx - frame_w / 2
        staff_y = cy - frame_h / 2
        line(staff_x, staff_y, staff_x, max(1.0, staff_y - frame_h * 0.62), 2.2)
    return area


def mil2525_ip_artist(label: str, size: float, alpha: float = 0.76) -> DrawingArea:
    """Build a friendly control-point/IP graphic rather than a generic map pin."""
    width = max(float(size) * 1.28, 44.0)
    height = max(float(size) * 0.82, 31.0)
    area = DrawingArea(width, height, 0, 0)
    edge = "#3287ff"
    ink = "#071012"
    frame_h = height * 0.57
    area.add_artist(
        Rectangle(
            (width * 0.08, height * 0.31), width * 0.84, frame_h,
            facecolor="#deeeff", edgecolor=edge, linewidth=2.0, alpha=alpha,
        )
    )
    area.add_artist(Text(width / 2, height * 0.60, "IP", color=ink, fontsize=max(8, size * 0.20), weight="bold", ha="center", va="center", alpha=alpha))
    area.add_artist(Text(width / 2, height * 0.12, label.removeprefix("IP "), color=edge, fontsize=max(7, size * 0.17), weight="bold", ha="center", va="center", alpha=alpha))
    return area

VIEW_PRESETS: dict[str, dict[str, Any]] = {
    # Recovered from the accepted Event 740 terrain-emphasis views. This is the
    # briefing default: close, edge-to-edge terrain with enough exaggeration to
    # explain masking without turning ridgelines into walls.
    "attack-geometry": {
        "margin_grid": 5.1,
        "view_extra_grid": 0.0,
        "terrain_extra_grid": 26.0,
        "mesh_size": 430,
        "z_exaggeration": 2.55,
        "vertical_box_aspect": 9.2,
        "box_x_scale": 2.65,
        "box_y_scale": 1.98,
        "camera_elev": 41.0,
        "camera_azim": -58.0,
        "camera_distance": 2.42,
        "map_texture_alpha": 1.0,
        "hillshade_strength": 0.48,
        "background_color": "#b7cce0",
        "ring_alpha": 0.22,
        "ring_linewidth": 1.05,
        "ring_pad_nm": 5.0,
        "pin_height_ft": 3600.0,
        "marker_lift_ft": 90.0,
        "label_font_size": 11.0,
        "label_alpha": 0.9,
        "label_box_alpha": 0.6,
        "marker_alpha": 0.8,
        "ad_marker_alpha": 0.8,
        "ad_label_leader_alpha": 0.3,
        "mark_size": 50.0,
        "ad_size": 85.0,
    },
    "diagnostic": {
        "margin_grid": 8.0,
        "view_extra_grid": 0.0,
        "terrain_extra_grid": 0.0,
        "mesh_size": 230,
        "z_exaggeration": 1.8,
        "vertical_box_aspect": 5.0,
        "box_x_scale": 1.0,
        "box_y_scale": 1.0,
        "camera_elev": 42.0,
        "camera_azim": -62.0,
        "camera_distance": 8.0,
        "map_texture_alpha": 0.94,
        "hillshade_strength": 0.0,
        "background_color": "#071012",
        "ring_alpha": 0.58,
        "ring_linewidth": 1.7,
        "ring_pad_nm": 12.0,
        "pin_height_ft": 5500.0,
        "marker_lift_ft": 1100.0,
        "label_font_size": 11.0,
        "label_alpha": 1.0,
        "label_box_alpha": 0.88,
        "marker_alpha": 1.0,
        "ad_marker_alpha": 0.92,
        "ad_label_leader_alpha": 0.0,
        "mark_size": 62.0,
        "ad_size": 100.0,
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_callsign(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "").lower())


def normalize_label(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "").upper())


def grid_to_nm(grid_x: float, grid_y: float, center_x: float, center_y: float) -> tuple[float, float]:
    return (float(grid_x) - center_x) * GRID_NM, (float(grid_y) - center_y) * GRID_NM


def nm_to_grid(nm: float) -> float:
    return nm / GRID_NM


def grid_to_heightmap_pixel(grid_x: float, grid_y: float, samples: int = HEIGHTMAP_SAMPLES) -> tuple[int, int]:
    max_index = samples - 1
    col = int(round(max(0.0, min(1.0, float(grid_x) / THEATER_GRID_SIZE)) * max_index))
    row = int(round(max(0.0, min(1.0, (THEATER_GRID_SIZE - float(grid_y)) / THEATER_GRID_SIZE)) * max_index))
    return col, row


def heightmap_pixel_to_grid(col: np.ndarray, row: np.ndarray, samples: int = HEIGHTMAP_SAMPLES) -> tuple[np.ndarray, np.ndarray]:
    max_index = samples - 1
    grid_x = col.astype(float) / max_index * THEATER_GRID_SIZE
    grid_y = THEATER_GRID_SIZE - row.astype(float) / max_index * THEATER_GRID_SIZE
    return grid_x, grid_y


def find_packages(syntheses: list[dict[str, Any]], package_ids: set[int]) -> list[dict[str, Any]]:
    packages: dict[int, dict[str, Any]] = {}
    for synthesis in syntheses:
        for package in synthesis.get("packages", []):
            package_id = safe_int(package.get("package_id"), -1)
            if package_id in package_ids and package_id not in packages:
                packages[package_id] = package
    missing = sorted(package_ids - set(packages))
    if missing:
        raise SystemExit(f"Package(s) not found in synthesis: {', '.join(str(item) for item in missing)}")
    return [packages[item] for item in sorted(packages)]


def raw_flights_by_package(cam_decode: dict[str, Any] | None, package_ids: set[int]) -> dict[tuple[int, str], dict[str, Any]]:
    result: dict[tuple[int, str], dict[str, Any]] = {}
    if not cam_decode:
        return result
    for flight in cam_decode.get("flights", []):
        package_id = safe_int(flight.get("package_camp_id"), -1)
        callsign = normalize_callsign(flight.get("callsign"))
        if package_id in package_ids and callsign:
            result[(package_id, callsign)] = flight
    return result


def flight_waypoints(package: dict[str, Any], flight: dict[str, Any], raw_flights: dict[tuple[int, str], dict[str, Any]]) -> list[dict[str, Any]]:
    package_id = safe_int(package.get("package_id"), -1)
    raw = raw_flights.get((package_id, normalize_callsign(flight.get("callsign"))))
    if raw and raw.get("waypoints"):
        waypoints = []
        for waypoint in raw.get("waypoints", []):
            if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
                continue
            waypoints.append(
                {
                    "index": waypoint.get("index"),
                    "action": waypoint.get("action_name"),
                    "grid_x": waypoint.get("grid_x"),
                    "grid_y": waypoint.get("grid_y"),
                    "grid_z": waypoint.get("grid_z"),
                }
            )
        return waypoints
    return [
        waypoint
        for waypoint in flight.get("key_waypoints", [])
        if waypoint.get("grid_x") is not None and waypoint.get("grid_y") is not None
    ]


def collect_named_marks(
    syntheses: list[dict[str, Any]],
    packages: list[dict[str, Any]],
    mission_context: dict[str, Any],
) -> list[dict[str, Any]]:
    marks: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()

    def add_mark(label: str, grid_x: Any, grid_y: Any, radius_nm: Any = 0.0, kind: str = "mark") -> None:
        if not label or grid_x is None or grid_y is None:
            return
        item = {
            "label": label,
            "source_label": label,
            "grid_x": safe_float(grid_x),
            "grid_y": safe_float(grid_y),
            "radius_nm": safe_float(radius_nm),
            "kind": kind,
        }
        key = (normalize_label(label), round(item["grid_x"] * 10), round(item["grid_y"] * 10))
        if key not in seen:
            seen.add(key)
            marks.append(item)

    for synthesis in syntheses:
        planning = synthesis.get("planning") or {}
        for point in [*(planning.get("points") or []), *(planning.get("transformed_points") or [])]:
            grid = point.get("campaign_grid") or {}
            if grid.get("grid_x") is None or grid.get("grid_y") is None or not grid.get("valid_for_map", True):
                continue
            display = str(point.get("display") or point.get("label") or "").strip()
            if not display or display.upper().startswith("TGT "):
                continue
            add_mark(display, grid.get("grid_x"), grid.get("grid_y"), point.get("radius_nm"), str(point.get("kind") or "mark"))

    for package in packages:
        correlation = package.get("plan_correlation") or {}
        for match in correlation.get("point_matches", []):
            grid = match.get("campaign_grid") or {}
            if grid.get("grid_x") is None or grid.get("grid_y") is None or not grid.get("valid_for_map", True):
                continue
            display = str(match.get("display") or match.get("label") or "").strip()
            if not display or display.upper().startswith("TGT "):
                continue
            add_mark(display, grid.get("grid_x"), grid.get("grid_y"), match.get("radius_nm"), str(match.get("kind") or "mark"))

    mark_names = {normalize_label(item.get("label")): item.get("name") for item in mission_context.get("named_points", [])}
    for mark in marks:
        name = mark_names.get(normalize_label(mark["label"]))
        if name:
            mark["name"] = name

    overrides = mission_context.get("map_mark_overrides") or []
    all_flights = [flight for package in packages for flight in package.get("flights", [])]
    for override in overrides:
        explicit_x = override.get("grid_x")
        explicit_y = override.get("grid_y")
        if explicit_x is not None and explicit_y is not None:
            label = str(override.get("label") or "").strip()
            add_mark(label, explicit_x, explicit_y, override.get("radius_nm"), str(override.get("kind") or "mark"))
            selected = next(
                (
                    mark
                    for mark in reversed(marks)
                    if normalize_label(mark.get("label")) == normalize_label(label)
                    and abs(safe_float(mark.get("grid_x")) - safe_float(explicit_x)) < 0.05
                    and abs(safe_float(mark.get("grid_y")) - safe_float(explicit_y)) < 0.05
                ),
                None,
            )
            if selected:
                selected["name"] = str(override.get("name") or selected.get("name") or "")
                selected["overridden"] = True
            continue
        from_label = normalize_label(override.get("from_ppt_label"))
        candidates = [mark for mark in marks if normalize_label(mark.get("source_label")) == from_label]
        if not candidates:
            continue
        reference = None
        callsign = normalize_callsign(override.get("nearest_callsign"))
        action = str(override.get("nearest_action") or "")
        for flight in all_flights:
            if normalize_callsign(flight.get("callsign")) != callsign:
                continue
            for waypoint in flight.get("key_waypoints", []):
                if waypoint.get("action") == action and waypoint.get("grid_x") is not None and waypoint.get("grid_y") is not None:
                    reference = waypoint
                    break
            if reference:
                break
        if reference:
            candidates.sort(
                key=lambda mark: math.hypot(
                    safe_float(mark.get("grid_x")) - safe_float(reference.get("grid_x")),
                    safe_float(mark.get("grid_y")) - safe_float(reference.get("grid_y")),
                )
            )
        selected = candidates[0]
        selected["label"] = str(override.get("label") or selected["label"])
        selected["name"] = str(override.get("name") or selected.get("name") or "")
        selected["overridden"] = True

    def factor_family(label: Any) -> str:
        compact = normalize_label(label).removeprefix("SA")
        for family in ("17", "11", "10", "6", "5", "3", "2"):
            if compact.startswith(family):
                return family
        return ""

    overridden = [mark for mark in marks if mark.get("overridden")]
    if overridden:
        marks = [
            mark
            for mark in marks
            if mark.get("overridden")
            or not factor_family(mark.get("label"))
            or not any(
                factor_family(mark.get("label")) == factor_family(override.get("label"))
                and math.hypot(
                    safe_float(mark.get("grid_x")) - safe_float(override.get("grid_x")),
                    safe_float(mark.get("grid_y")) - safe_float(override.get("grid_y")),
                )
                <= 2.5
                for override in overridden
            )
        ]
    return marks


def add_orion_target(packages: list[dict[str, Any]], marks: list[dict[str, Any]]) -> None:
    if any(normalize_label(mark.get("label")) in {"ORION", "ORO"} and mark.get("grid_y", 9999) < 1024 for mark in marks):
        return
    strike_actions = {"WP_STRIKE", "WP_BOMB", "WP_GNDSTRIKE", "WP_NAVSTRIKE"}
    candidates = []
    for package in packages:
        for flight in package.get("flights", []):
            for waypoint in flight.get("key_waypoints", []):
                if waypoint.get("action") in strike_actions and waypoint.get("grid_x") is not None and waypoint.get("grid_y") is not None:
                    candidates.append(waypoint)
    if not candidates:
        return
    target = candidates[0]
    marks.append(
        {
            "label": "ORION",
            "name": "Gimhae",
            "source_label": "ORION",
            "grid_x": safe_float(target.get("grid_x")),
            "grid_y": safe_float(target.get("grid_y")),
            "radius_nm": 0.0,
            "kind": "target",
        }
    )


def sam_short_label(air_defense: dict[str, Any], marks: list[dict[str, Any]]) -> str:
    equipment = str(air_defense.get("equipment") or air_defense.get("class_name") or "SAM")
    grid_x = safe_float(air_defense.get("grid_x"))
    grid_y = safe_float(air_defense.get("grid_y"))
    if "SA-10" in equipment or "S-300" in equipment:
        candidates = [
            mark
            for mark in marks
            if normalize_label(mark.get("label")) in {"10W", "10E", "10S", "10A", "10B", "10C", "10"}
        ]
        if candidates:
            candidates.sort(
                key=lambda mark: (
                    math.hypot(safe_float(mark["grid_x"]) - grid_x, safe_float(mark["grid_y"]) - grid_y),
                    0 if mark.get("overridden") else 1,
                )
            )
            return str(candidates[0].get("label") or "10")
        return "10"
    for token, label in [
        ("SA-2", "2"),
        ("SA-3", "3"),
        ("SA-5", "5"),
        ("S-200", "5"),
        ("SA-6", "6"),
        ("2K12", "6"),
        ("SA-11", "11"),
        ("SA-17", "17"),
    ]:
        if token in equipment:
            return label
    return "SAM"


def air_defense_override_labels(packages: list[dict[str, Any]], mission_context: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[int, str]:
    labels: dict[int, str] = {}
    all_flights = [flight for package in packages for flight in package.get("flights", [])]
    for override in mission_context.get("map_mark_overrides") or []:
        label = str(override.get("label") or "").strip()
        callsign = normalize_callsign(override.get("nearest_callsign"))
        action = str(override.get("nearest_action") or "").strip()
        if not label or not callsign or not action:
            continue
        reference = None
        for flight in all_flights:
            if normalize_callsign(flight.get("callsign")) != callsign:
                continue
            for waypoint in flight.get("key_waypoints") or []:
                if str(waypoint.get("action") or "") == action:
                    reference = (safe_float(waypoint.get("grid_x")), safe_float(waypoint.get("grid_y")))
                    break
            if reference:
                break
        if not reference:
            continue
        filtered = [
            (index, item)
            for index, item in enumerate(candidates)
            if ("SA-10" in str(item.get("equipment") or "") or "S-300" in str(item.get("equipment") or ""))
        ]
        if not filtered:
            filtered = list(enumerate(candidates))
        index, _ = min(
            filtered,
            key=lambda pair: math.hypot(safe_float(pair[1].get("grid_x")) - reference[0], safe_float(pair[1].get("grid_y")) - reference[1]),
        )
        labels[index] = label
    return labels


def collect_air_defenses(packages: list[dict[str, Any]], marks: list[dict[str, Any]], mission_context: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for package in packages:
        enemy = package.get("enemy_situation") or {}
        for item in enemy.get("air_defense_locations") or enemy.get("air_defenses") or []:
            if not item.get("active_tracking_radar", False):
                continue
            grid_x = item.get("grid_x")
            grid_y = item.get("grid_y")
            if grid_x is None or grid_y is None:
                continue
            candidates.append(item)

    override_labels = air_defense_override_labels(packages, mission_context, candidates)
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for index, item in enumerate(candidates):
        grid_x = item.get("grid_x")
        grid_y = item.get("grid_y")
        label = override_labels.get(index) or sam_short_label(item, marks)
        key = (label, round(safe_float(grid_x)), round(safe_float(grid_y)))
        if key in seen:
            continue
        seen.add(key)
        copied = dict(item)
        copied["map_label"] = label
        copied["map_label_source"] = "decoded waypoint -> active SA-10 radar" if index in override_labels else "nearest named mark"
        result.append(copied)
    return result


def bounds_from_labels(
    labels: list[str],
    marks: list[dict[str, Any]],
    air_defenses: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    margin_grid: float,
) -> tuple[float, float, float, float]:
    wanted = {normalize_label(label) for label in labels if label}
    mark_points: list[tuple[float, float]] = []
    for mark in marks:
        if normalize_label(mark.get("label")) in wanted or normalize_label(mark.get("source_label")) in wanted:
            mark_points.append((safe_float(mark.get("grid_x")), safe_float(mark.get("grid_y"))))
    points = list(mark_points)
    if not points:
        for air_defense in air_defenses:
            if normalize_label(air_defense.get("map_label")) in wanted:
                points.append((safe_float(air_defense.get("grid_x")), safe_float(air_defense.get("grid_y"))))
    if not points:
        for route in routes:
            for waypoint in route.get("waypoints", []):
                points.append((safe_float(waypoint.get("grid_x")), safe_float(waypoint.get("grid_y"))))
    if not points:
        raise SystemExit("No points were available to calculate a 3D crop.")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (
        max(0.0, min(xs) - margin_grid),
        min(THEATER_GRID_SIZE, max(xs) + margin_grid),
        max(0.0, min(ys) - margin_grid),
        min(THEATER_GRID_SIZE, max(ys) + margin_grid),
    )


def expand_bounds(bounds: tuple[float, float, float, float], extra_grid: float) -> tuple[float, float, float, float]:
    if extra_grid <= 0:
        return bounds
    x_min, x_max, y_min, y_max = bounds
    return (
        max(0.0, x_min - extra_grid),
        min(THEATER_GRID_SIZE, x_max + extra_grid),
        max(0.0, y_min - extra_grid),
        min(THEATER_GRID_SIZE, y_max + extra_grid),
    )


def sanitize_elevations(elevations_ft: np.ndarray) -> np.ndarray:
    """Clamp BMS heightmap sentinel/no-data spikes before plotting.

    The Korea theater metadata tops out near 10,000 ft. Values far above that
    show up in coastal/water-adjacent raw crops as vertical walls, so treat
    them as sea-level/no-data for this briefing-scale prototype.
    """
    return np.where(elevations_ft > MAX_VALID_ELEVATION_FT, 0.0, elevations_ft)


def read_heightmap_crop(
    heightmap_path: Path,
    bounds: tuple[float, float, float, float],
    *,
    mesh_size: int,
    z_exaggeration: float,
    center: tuple[float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x_min, x_max, y_min, y_max = bounds
    col_min, row_south = grid_to_heightmap_pixel(x_min, y_min)
    col_max, row_north = grid_to_heightmap_pixel(x_max, y_max)
    col_min, col_max = sorted((col_min, col_max))
    row_min, row_max = sorted((row_north, row_south))
    width = max(col_max - col_min + 1, 2)
    height = max(row_max - row_min + 1, 2)
    sample_cols = max(24, min(mesh_size, width))
    sample_rows = max(24, min(mesh_size, height))
    cols = np.linspace(col_min, col_max, sample_cols).round().astype(int)
    rows = np.linspace(row_min, row_max, sample_rows).round().astype(int)
    raster = np.memmap(heightmap_path, dtype="<u2", mode="r", shape=(HEIGHTMAP_SAMPLES, HEIGHTMAP_SAMPLES))
    elevations_ft = sanitize_elevations(np.asarray(raster[np.ix_(rows, cols)], dtype=float))
    col_grid, row_grid = np.meshgrid(cols, rows)
    grid_x, grid_y = heightmap_pixel_to_grid(col_grid, row_grid)
    center_x, center_y = center if center is not None else ((x_min + x_max) / 2.0, (y_min + y_max) / 2.0)
    x_nm = (grid_x - center_x) * GRID_NM
    y_nm = (grid_y - center_y) * GRID_NM
    z_kft = (elevations_ft / 1000.0) * z_exaggeration
    return x_nm, y_nm, z_kft, elevations_ft


def texture_from_map(
    map_source: Path,
    bounds: tuple[float, float, float, float],
    shape: tuple[int, int],
    *,
    alpha: float,
    elevations_ft: np.ndarray | None = None,
    hillshade_strength: float = 0.0,
) -> np.ndarray:
    x_min, x_max, y_min, y_max = bounds
    image = Image.open(map_source).convert("RGBA")
    width, height = image.size
    left = int(max(0.0, min(1.0, x_min / THEATER_GRID_SIZE)) * width)
    right = int(max(0.0, min(1.0, x_max / THEATER_GRID_SIZE)) * width)
    top = int(max(0.0, min(1.0, (THEATER_GRID_SIZE - y_max) / THEATER_GRID_SIZE)) * height)
    bottom = int(max(0.0, min(1.0, (THEATER_GRID_SIZE - y_min) / THEATER_GRID_SIZE)) * height)
    crop = image.crop((left, top, max(left + 1, right), max(top + 1, bottom)))
    resized = crop.resize((shape[1], shape[0]), Image.Resampling.BICUBIC)
    colors = np.asarray(resized, dtype=float) / 255.0
    if elevations_ft is not None and hillshade_strength > 0:
        low = float(np.nanpercentile(elevations_ft, 2))
        high = float(np.nanpercentile(elevations_ft, 98))
        normalized = np.clip((elevations_ft - low) / max(high - low, 1.0), 0.0, 1.0)
        shaded = LightSource(azdeg=315, altdeg=45).shade_rgb(colors[..., :3], normalized, blend_mode="overlay")
        strength = max(0.0, min(1.0, hillshade_strength))
        colors[..., :3] = colors[..., :3] * (1.0 - strength) + shaded * strength
    colors[..., 3] = alpha
    return colors


def apply_texture_hillshade(
    colors: np.ndarray,
    elevations_ft: np.ndarray | None,
    hillshade_strength: float,
) -> np.ndarray:
    if elevations_ft is None or hillshade_strength <= 0:
        return colors
    low = float(np.nanpercentile(elevations_ft, 2))
    high = float(np.nanpercentile(elevations_ft, 98))
    normalized = np.clip((elevations_ft - low) / max(high - low, 1.0), 0.0, 1.0)
    shaded = LightSource(azdeg=315, altdeg=45).shade_rgb(colors[..., :3], normalized, blend_mode="overlay")
    strength = max(0.0, min(1.0, hillshade_strength))
    colors[..., :3] = colors[..., :3] * (1.0 - strength) + shaded * strength
    return colors


def wash_texture(colors: np.ndarray, amount: float) -> np.ndarray:
    """Lift a dense photoreal texture toward the established pale briefing treatment."""
    amount = max(0.0, min(1.0, amount))
    if amount <= 0:
        return colors
    result = colors.copy()
    result[..., :3] = result[..., :3] * (1.0 - amount) + np.array([0.86, 0.88, 0.82]) * amount
    return result


def texture_from_photoreal_tiles(
    tile_dir: Path,
    bounds: tuple[float, float, float, float],
    shape: tuple[int, int],
    *,
    alpha: float,
    elevations_ft: np.ndarray | None = None,
    hillshade_strength: float = 0.0,
    tile_grid_size: int = 32,
    tile_origin: str = "top-left",
    tile_index_base: int = 1,
) -> np.ndarray:
    """Sample BMS numeric photoreal tiles directly into the terrain mesh texture.

    The 16K photoreal set is stored as a sparse 32x32 virtual theater mosaic
    using numeric DDS names. This function only opens tiles intersecting the
    current 3D crop and resizes each tile section into the final mesh texture,
    avoiding a huge intermediate mosaic.
    """
    x_min, x_max, y_min, y_max = bounds
    out_rows, out_cols = shape
    out_image = Image.new("RGBA", (out_cols, out_rows), (186, 203, 196, 255))

    probe = next(tile_dir.glob("*.dds"), None)
    if probe is None:
        raise FileNotFoundError(f"No DDS tiles found in {tile_dir}")
    with Image.open(probe) as probe_image:
        tile_px = probe_image.size[0]

    grid_size = max(1, int(tile_grid_size))
    total_px = tile_px * grid_size
    crop_left = max(0.0, min(float(total_px), x_min / THEATER_GRID_SIZE * total_px))
    crop_right = max(0.0, min(float(total_px), x_max / THEATER_GRID_SIZE * total_px))
    crop_top = max(0.0, min(float(total_px), (THEATER_GRID_SIZE - y_max) / THEATER_GRID_SIZE * total_px))
    crop_bottom = max(0.0, min(float(total_px), (THEATER_GRID_SIZE - y_min) / THEATER_GRID_SIZE * total_px))
    if crop_right <= crop_left or crop_bottom <= crop_top:
        raise ValueError(f"Invalid photoreal tile crop bounds: {bounds}")

    col_start = max(0, int(math.floor(crop_left / tile_px)))
    col_end = min(grid_size - 1, int(math.floor((crop_right - 0.001) / tile_px)))
    row_start = max(0, int(math.floor(crop_top / tile_px)))
    row_end = min(grid_size - 1, int(math.floor((crop_bottom - 0.001) / tile_px)))

    def tile_index(row_from_top: int, col_from_left: int) -> int:
        if tile_origin == "top-left":
            storage_row = row_from_top
        else:
            storage_row = grid_size - 1 - row_from_top
        return storage_row * grid_size + col_from_left + tile_index_base

    for row in range(row_start, row_end + 1):
        for col in range(col_start, col_end + 1):
            tile_path = tile_dir / f"{tile_index(row, col)}.dds"
            if not tile_path.is_file():
                continue

            tile_left = col * tile_px
            tile_right = tile_left + tile_px
            tile_top = row * tile_px
            tile_bottom = tile_top + tile_px
            inter_left = max(crop_left, tile_left)
            inter_right = min(crop_right, tile_right)
            inter_top = max(crop_top, tile_top)
            inter_bottom = min(crop_bottom, tile_bottom)
            if inter_right <= inter_left or inter_bottom <= inter_top:
                continue

            src_box = (
                int(math.floor(inter_left - tile_left)),
                int(math.floor(inter_top - tile_top)),
                int(math.ceil(inter_right - tile_left)),
                int(math.ceil(inter_bottom - tile_top)),
            )
            dst_box = (
                int(math.floor((inter_left - crop_left) / (crop_right - crop_left) * out_cols)),
                int(math.floor((inter_top - crop_top) / (crop_bottom - crop_top) * out_rows)),
                int(math.ceil((inter_right - crop_left) / (crop_right - crop_left) * out_cols)),
                int(math.ceil((inter_bottom - crop_top) / (crop_bottom - crop_top) * out_rows)),
            )
            dst_width = max(1, dst_box[2] - dst_box[0])
            dst_height = max(1, dst_box[3] - dst_box[1])
            with Image.open(tile_path) as tile_image:
                crop = tile_image.convert("RGBA").crop(src_box)
                out_image.paste(crop.resize((dst_width, dst_height), Image.Resampling.BICUBIC), dst_box[:2])

    colors = np.asarray(out_image, dtype=float) / 255.0
    colors = apply_texture_hillshade(colors, elevations_ft, hillshade_strength)
    colors[..., 3] = alpha
    return colors


def terrain_facecolors(elevations_ft: np.ndarray) -> np.ndarray:
    low = float(np.nanpercentile(elevations_ft, 2))
    high = float(np.nanpercentile(elevations_ft, 98))
    span = max(high - low, 1.0)
    normalized = np.clip((elevations_ft - low) / span, 0.0, 1.0)
    return LightSource(azdeg=315, altdeg=45).shade(normalized, cmap=plt.cm.gist_earth, blend_mode="overlay")


def parse_hex_color(value: str) -> tuple[int, int, int]:
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6:
        return 0, 0, 0
    try:
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    except ValueError:
        return 0, 0, 0


def fill_render_background(path: Path, background_color: str, threshold: float, blur_radius: float = 7.0) -> None:
    image = Image.open(path).convert("RGB")
    pixels = np.asarray(image, dtype=np.int32)
    color = np.asarray(parse_hex_color(background_color), dtype=np.int32)
    distance = np.sqrt(np.sum((pixels - color) ** 2, axis=2))
    candidates = distance <= max(0.0, threshold)
    if not np.any(candidates):
        return

    # Only replace the solid canvas connected to an image edge.  Treating all
    # background-coloured pixels as empty also captured the pale fill inside
    # friendly MIL-STD symbols, which then acquired terrain-texture artifacts.
    mask = np.zeros(candidates.shape, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    height, width = candidates.shape
    for x in range(width):
        if candidates[0, x]:
            queue.append((0, x))
        if candidates[height - 1, x]:
            queue.append((height - 1, x))
    for y in range(1, height - 1):
        if candidates[y, 0]:
            queue.append((y, 0))
        if candidates[y, width - 1]:
            queue.append((y, width - 1))
    while queue:
        y, x = queue.popleft()
        if mask[y, x] or not candidates[y, x]:
            continue
        mask[y, x] = True
        if y > 0:
            queue.append((y - 1, x))
        if y + 1 < height:
            queue.append((y + 1, x))
        if x > 0:
            queue.append((y, x - 1))
        if x + 1 < width:
            queue.append((y, x + 1))

    valid_rows, valid_cols = np.where(~mask)
    if len(valid_rows) == 0 or len(valid_cols) == 0:
        return

    left = int(np.min(valid_cols))
    right = int(np.max(valid_cols)) + 1
    top = int(np.min(valid_rows))
    bottom = int(np.max(valid_rows)) + 1
    source = image.crop((left, top, right, bottom))
    width, height = image.size
    scale = max(width / max(source.width, 1), height / max(source.height, 1))
    fill_size = (max(width, int(source.width * scale) + 2), max(height, int(source.height * scale) + 2))
    fill = source.resize(fill_size, Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(radius=max(0.0, blur_radius)))
    fill = fill.crop(((fill.width - width) // 2, (fill.height - height) // 2, (fill.width + width) // 2, (fill.height + height) // 2))

    output = np.asarray(image).copy()
    fill_pixels = np.asarray(fill)
    output[mask] = fill_pixels[mask]
    Image.fromarray(output).save(path)


def load_feature_class_names(object_dir: Path) -> dict[int, str]:
    path = object_dir / "Falcon4_FCD.xml"
    if not path.is_file():
        return {}
    names: dict[int, str] = {}
    root = ET.parse(path).getroot()
    for node in root.findall("FCD"):
        num = safe_int(node.attrib.get("Num"), -1)
        if num < 0:
            continue
        ct_idx = safe_int(node.findtext("CtIdx"), -1)
        name = str(node.findtext("Name") or "").strip()
        if ct_idx >= 0 and name:
            names[ct_idx] = name
    return names


def load_camp_objectives(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    root = ET.parse(path).getroot()
    objectives: list[dict[str, Any]] = []
    for node in root.findall("CampObj"):
        values = {child.tag: child.text or "" for child in node}
        objectives.append(
            {
                "camp_id": safe_int(node.attrib.get("CampId"), -1),
                "name": values.get("CampName", ""),
                "ocd_index": safe_int(values.get("OcdIndex"), -1),
                "heading": safe_float(values.get("Heading")),
                "source_x_ft": safe_float(values.get("PositionX")),
                "source_y_ft": safe_float(values.get("PositionY")),
                "source_z_ft": safe_float(values.get("PositionZ")),
            }
        )
    return objectives


def load_fed_features(object_dir: Path, ocd_index: int, feature_names_by_ct: dict[int, str]) -> list[dict[str, Any]]:
    if ocd_index < 0:
        return []
    path = object_dir / "ObjectiveRelatedData" / f"OCD_{ocd_index:05d}" / f"FED_{ocd_index:05d}.XML"
    if not path.is_file():
        return []
    root = ET.parse(path).getroot()
    features: list[dict[str, Any]] = []
    for node in root.findall("FED"):
        feature_ct_idx = safe_int(node.findtext("FeatureCtIdx"), -1)
        features.append(
            {
                "index": safe_int(node.attrib.get("Num"), len(features)),
                "feature_ct_idx": feature_ct_idx,
                "name": feature_names_by_ct.get(feature_ct_idx, f"Feature {feature_ct_idx}"),
                "offset_x_ft": safe_float(node.findtext("OffsetX")),
                "offset_y_ft": safe_float(node.findtext("OffsetY")),
                "offset_z_ft": safe_float(node.findtext("OffsetZ")),
                "heading": safe_float(node.findtext("Heading")),
                "value": safe_int(node.findtext("Value"), -1),
            }
        )
    return features


def rotate_feet(offset_x_ft: float, offset_y_ft: float, heading_deg: float) -> tuple[float, float]:
    radians = math.radians(heading_deg)
    cos_h = math.cos(radians)
    sin_h = math.sin(radians)
    return (
        offset_x_ft * cos_h - offset_y_ft * sin_h,
        offset_x_ft * sin_h + offset_y_ft * cos_h,
    )


def feature_offset_to_source_feet(offset_x_ft: float, offset_y_ft: float, heading_deg: float) -> tuple[float, float]:
    """Convert FED local offsets to BMS source-feet deltas.

    CampObj source X/Y are opposite the map grid axes, and FED OffsetX/OffsetY
    use the feature-layout axes rather than CampObj's source-field names. The
    swap is visible at Gimhae: runway feature centers only align with the
    north/south runway when FED OffsetY is applied to source X.
    """
    layout_x_ft, layout_y_ft = rotate_feet(offset_x_ft, offset_y_ft, heading_deg)
    return layout_y_ft, layout_x_ft


def feature_style(name: str, mode: str = "runway-and-buildings") -> dict[str, Any] | None:
    text = name.lower()
    visual_aids = (
        "light",
        "sign",
        "fence",
        "beacon",
        "windsock",
        "papi",
        "alsf",
        "malsr",
        "vordme",
        "vortac",
    )
    if any(token in text for token in visual_aids):
        return None
    if any(token in text for token in ("truck", "lifter", "mobile", "opfor", "m978", "r-11")):
        return None
    if "runway" in text:
        if mode == "buildings":
            return None
        if "stopway" in text:
            return {"length_nm": 0.25, "width_nm": 0.10, "height_ft": 6, "color": "#c4c5b9", "alpha": 0.34}
        if "thr" in text or "tdz" in text:
            return {"length_nm": 0.24, "width_nm": 0.11, "height_ft": 6, "color": "#d8d6c6", "alpha": 0.38}
        if "section" in text:
            return {"length_nm": 0.52, "width_nm": 0.105, "height_ft": 7, "color": "#d7d5c0", "alpha": 0.46}
        return {"length_nm": 0.26, "width_nm": 0.08, "height_ft": 6, "color": "#d7d5c0", "alpha": 0.35}
    if "taxi" in text or "road" in text:
        if mode == "buildings":
            return None
        return {"length_nm": 0.20, "width_nm": 0.055, "height_ft": 5, "color": "#b9c3bf", "alpha": 0.26}
    if "bridge" in text or "span" in text:
        if mode == "buildings":
            return None
        return {"length_nm": 0.23, "width_nm": 0.050, "height_ft": 25, "color": "#d2c49a", "alpha": 0.56}
    if "tower" in text or "radar" in text or "vor" in text:
        if mode == "buildings" and not ("tower" in text):
            return None
        return {"length_nm": 0.055, "width_nm": 0.055, "height_ft": 145, "color": "#ffd6a5", "alpha": 0.70}
    if "hotel" in text or "city hall" in text:
        # Town/city object layouts otherwise look unnaturally sparse: their
        # distinctive tall civic/commercial structures are named separately
        # from generic buildings in the BMS feature catalog.
        return {"length_nm": 0.15, "width_nm": 0.11, "height_ft": 92, "color": "#e8cf99", "alpha": 0.68}
    if any(token in text for token in ("hangar", "shelter", "warehouse", "terminal", "depot", "plant", "factory", "maintenance", "technical", "rffs")):
        return {"length_nm": 0.17, "width_nm": 0.11, "height_ft": 55, "color": "#f2c078", "alpha": 0.58}
    if any(token in text for token in ("building", "apartment", "barracks", "office", "admin", "storage", "squad")):
        return {"length_nm": 0.11, "width_nm": 0.08, "height_ft": 45, "color": "#e8d9b5", "alpha": 0.50}
    if "house" in text:
        return {"length_nm": 0.072, "width_nm": 0.052, "height_ft": 28, "color": "#dbc8a2", "alpha": 0.44}
    if "construction" in text:
        return {"length_nm": 0.13, "width_nm": 0.10, "height_ft": 36, "color": "#cfb67e", "alpha": 0.46}
    if any(token in text for token in ("revetment", "bunker", "ammo", "fuel", "tank")):
        if mode == "buildings":
            return None
        return {"length_nm": 0.085, "width_nm": 0.070, "height_ft": 24, "color": "#d6b56d", "alpha": 0.56}
    return None


def collect_objective_features(
    camp_obj_data: Path | None,
    object_dir: Path | None,
    view_bounds: tuple[float, float, float, float],
    *,
    include_patterns: list[str],
    exclude_patterns: list[str],
    mode: str,
    max_per_objective: int,
    limit: int,
) -> list[dict[str, Any]]:
    if not camp_obj_data or not object_dir:
        return []
    if not camp_obj_data.is_file() or not object_dir.is_dir():
        return []
    feature_names_by_ct = load_feature_class_names(object_dir)
    objectives = load_camp_objectives(camp_obj_data)
    include_regex = [re.compile(pattern, re.I) for pattern in include_patterns if pattern]
    exclude_regex = [re.compile(pattern, re.I) for pattern in exclude_patterns if pattern]
    collected: list[dict[str, Any]] = []
    fed_cache: dict[int, list[dict[str, Any]]] = {}

    for objective in objectives:
        objective_name = str(objective.get("name") or "")
        if include_regex and not any(regex.search(objective_name) for regex in include_regex):
            continue
        if exclude_regex and any(regex.search(objective_name) for regex in exclude_regex):
            continue
        base_grid_x, base_grid_y = source_feet_to_campaign_grid(
            safe_float(objective.get("source_x_ft")),
            safe_float(objective.get("source_y_ft")),
            FEET_PER_GRID,
        )
        if not point_in_bounds(base_grid_x, base_grid_y, view_bounds, pad=8.0):
            # Feature offsets can extend several grid cells away from the objective origin,
            # so keep a small pad around the visible crop.
            continue
        ocd_index = safe_int(objective.get("ocd_index"), -1)
        features = fed_cache.setdefault(ocd_index, load_fed_features(object_dir, ocd_index, feature_names_by_ct))
        objective_heading = safe_float(objective.get("heading"))
        objective_count = 0
        for feature in features:
            if max_per_objective > 0 and objective_count >= max_per_objective:
                break
            style = feature_style(str(feature.get("name") or ""), mode)
            if style is None:
                continue
            dx_ft, dy_ft = feature_offset_to_source_feet(
                safe_float(feature.get("offset_x_ft")),
                safe_float(feature.get("offset_y_ft")),
                objective_heading,
            )
            grid_x, grid_y = source_feet_to_campaign_grid(
                safe_float(objective.get("source_x_ft")) + dx_ft,
                safe_float(objective.get("source_y_ft")) + dy_ft,
                FEET_PER_GRID,
            )
            if not point_in_bounds(grid_x, grid_y, view_bounds, pad=2.0):
                continue
            item = {
                **feature,
                **style,
                "objective_name": objective_name,
                "objective_camp_id": objective.get("camp_id"),
                "grid_x": grid_x,
                "grid_y": grid_y,
                "heading": objective_heading + safe_float(feature.get("heading")) + 90.0,
            }
            collected.append(item)
            objective_count += 1
            if limit > 0 and len(collected) >= limit:
                return collected
    return collected


def cuboid_faces(
    center_x: float,
    center_y: float,
    base_z: float,
    *,
    length_nm: float,
    width_nm: float,
    height_kft: float,
    heading_deg: float,
) -> list[list[tuple[float, float, float]]]:
    radians = math.radians(heading_deg)
    ux, uy = math.sin(radians), math.cos(radians)
    vx, vy = math.cos(radians), -math.sin(radians)
    half_l = length_nm / 2.0
    half_w = width_nm / 2.0
    corners_2d = [
        (center_x - ux * half_l - vx * half_w, center_y - uy * half_l - vy * half_w),
        (center_x + ux * half_l - vx * half_w, center_y + uy * half_l - vy * half_w),
        (center_x + ux * half_l + vx * half_w, center_y + uy * half_l + vy * half_w),
        (center_x - ux * half_l + vx * half_w, center_y - uy * half_l + vy * half_w),
    ]
    bottom = [(x, y, base_z) for x, y in corners_2d]
    top = [(x, y, base_z + height_kft) for x, y in corners_2d]
    return [
        top,
        [bottom[0], bottom[1], top[1], top[0]],
        [bottom[1], bottom[2], top[2], top[1]],
        [bottom[2], bottom[3], top[3], top[2]],
        [bottom[3], bottom[0], top[0], top[3]],
    ]


def draw_objective_features(
    ax: Any,
    features: list[dict[str, Any]],
    *,
    center_x: float,
    center_y: float,
    heightmap_path: Path,
    z_exaggeration: float,
    alpha_scale: float,
    height_scale: float,
    footprint_scale: float,
) -> None:
    for feature in features:
        grid_x = safe_float(feature.get("grid_x"))
        grid_y = safe_float(feature.get("grid_y"))
        x, y = grid_to_nm(grid_x, grid_y, center_x, center_y)
        ground_z = sample_elevation_ft(heightmap_path, grid_x, grid_y) / 1000.0 * z_exaggeration + 0.015
        height_kft = max(0.006, safe_float(feature.get("height_ft"), 30.0) / 1000.0 * z_exaggeration * height_scale)
        faces = cuboid_faces(
            x,
            y,
            ground_z,
            length_nm=safe_float(feature.get("length_nm"), 0.08) * footprint_scale,
            width_nm=safe_float(feature.get("width_nm"), 0.06) * footprint_scale,
            height_kft=height_kft,
            heading_deg=safe_float(feature.get("heading")),
        )
        collection = Poly3DCollection(
            faces,
            facecolors=feature.get("color") or "#d8c7a5",
            edgecolors="#071012",
            linewidths=0.25,
            alpha=max(0.0, min(1.0, safe_float(feature.get("alpha"), 0.4) * alpha_scale)),
            zorder=35,
        )
        ax.add_collection3d(collection)


def sample_elevation_ft(heightmap_path: Path, grid_x: float, grid_y: float) -> float:
    col, row = grid_to_heightmap_pixel(grid_x, grid_y)
    raster = np.memmap(heightmap_path, dtype="<u2", mode="r", shape=(HEIGHTMAP_SAMPLES, HEIGHTMAP_SAMPLES))
    value = float(raster[row, col])
    return 0.0 if value > MAX_VALID_ELEVATION_FT else value


def point_in_bounds(grid_x: float, grid_y: float, bounds: tuple[float, float, float, float], pad: float = 0.0) -> bool:
    x_min, x_max, y_min, y_max = bounds
    return x_min - pad <= grid_x <= x_max + pad and y_min - pad <= grid_y <= y_max + pad


def clip_polygon_to_bounds(points: list[tuple[float, float]], bounds: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    """Clip a tactical polygon to the visible BMS grid rectangle."""
    x_min, x_max, y_min, y_max = bounds
    result = list(points)
    for axis, threshold, keep_greater in ((0, x_min, True), (0, x_max, False), (1, y_min, True), (1, y_max, False)):
        if not result:
            break
        clipped: list[tuple[float, float]] = []
        previous = result[-1]
        previous_inside = previous[axis] >= threshold if keep_greater else previous[axis] <= threshold
        for current in result:
            current_inside = current[axis] >= threshold if keep_greater else current[axis] <= threshold
            if current_inside != previous_inside:
                delta = current[axis] - previous[axis]
                if abs(delta) > 1e-9:
                    t = (threshold - previous[axis]) / delta
                    clipped.append((previous[0] + t * (current[0] - previous[0]), previous[1] + t * (current[1] - previous[1])))
            if current_inside:
                clipped.append(current)
            previous, previous_inside = current, current_inside
        result = clipped
    return result


def clip_segment_to_bounds(
    start: tuple[float, float], end: tuple[float, float], bounds: tuple[float, float, float, float]
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Clip one BMS line segment without inventing a crop-edge closing line."""
    x_min, x_max, y_min, y_max = bounds
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - x_min), (dx, x_max - x0), (-dy, y0 - y_min), (dy, y_max - y0)):
        if abs(p) < 1e-9:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            if r > t1:
                return None
            t0 = max(t0, r)
        else:
            if r < t0:
                return None
            t1 = min(t1, r)
    return ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy))


def find_mark(marks: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    wanted = normalize_label(label)
    for mark in marks:
        if normalize_label(mark.get("label")) == wanted or normalize_label(mark.get("source_label")) == wanted:
            return mark
    return None


def build_routes(
    packages: list[dict[str, Any]],
    raw_flights: dict[tuple[int, str], dict[str, Any]],
    allowed_callsigns: set[str],
) -> list[dict[str, Any]]:
    routes = []
    color_index = 0
    for package in packages:
        for flight in package.get("flights", []):
            callsign = str(flight.get("callsign") or "")
            if allowed_callsigns and normalize_callsign(callsign) not in allowed_callsigns:
                continue
            waypoints = flight_waypoints(package, flight, raw_flights)
            if len(waypoints) < 2:
                continue
            routes.append(
                {
                    "callsign": callsign,
                    "package_id": package.get("package_id"),
                    "mission": flight.get("mission"),
                    "color": PLAYER_ROUTE_COLORS[color_index % len(PLAYER_ROUTE_COLORS)],
                    "waypoints": waypoints,
                }
            )
            color_index += 1
    return routes


def route_color_from_context(route: dict[str, Any], mission_context: dict[str, Any]) -> str:
    callsign = normalize_callsign(route.get("callsign"))
    for group in mission_context.get("map_flow_groups") or []:
        group_callsigns = {normalize_callsign(item) for item in group.get("callsigns") or []}
        if callsign in group_callsigns:
            return FLOW_COLOR_NAMES.get(str(group.get("color") or "").lower(), route["color"])
    return route["color"]


def route_points_for_labels(
    labels: list[str],
    marks: list[dict[str, Any]],
    *,
    center_x: float,
    center_y: float,
    heightmap_path: Path,
    z_exaggeration: float,
    lift_ft: float,
) -> tuple[list[float], list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for label in labels:
        mark = find_mark(marks, label)
        if not mark:
            continue
        grid_x = safe_float(mark.get("grid_x"))
        grid_y = safe_float(mark.get("grid_y"))
        x, y = grid_to_nm(grid_x, grid_y, center_x, center_y)
        ground = sample_elevation_ft(heightmap_path, grid_x, grid_y)
        xs.append(x)
        ys.append(y)
        zs.append((ground + lift_ft) / 1000.0 * z_exaggeration)
    return xs, ys, zs


def route_points_for_callsign(
    routes: list[dict[str, Any]],
    callsign: str,
    view_bounds: tuple[float, float, float, float],
    *,
    center_x: float,
    center_y: float,
    heightmap_path: Path,
    z_exaggeration: float,
    lift_ft: float,
    pad_grid: float,
) -> tuple[list[float], list[float], list[float]]:
    wanted = normalize_callsign(callsign)
    route = next((item for item in routes if normalize_callsign(item.get("callsign")) == wanted), None)
    if not route:
        return [], [], []
    waypoints = list(route.get("waypoints") or [])
    in_view = [
        index
        for index, waypoint in enumerate(waypoints)
        if point_in_bounds(safe_float(waypoint.get("grid_x")), safe_float(waypoint.get("grid_y")), view_bounds, pad=pad_grid)
    ]
    if not in_view:
        return [], [], []
    # Include the previous waypoint so the route enters the close-up from outside the crop.
    start = max(0, min(in_view) - 1)
    end = max(in_view)
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for waypoint in waypoints[start : end + 1]:
        grid_x = safe_float(waypoint.get("grid_x"))
        grid_y = safe_float(waypoint.get("grid_y"))
        x, y = grid_to_nm(grid_x, grid_y, center_x, center_y)
        ground = sample_elevation_ft(heightmap_path, grid_x, grid_y)
        planned_agl = max(safe_float(waypoint.get("grid_z")), lift_ft)
        xs.append(x)
        ys.append(y)
        zs.append((ground + planned_agl) / 1000.0 * z_exaggeration)
    return xs, ys, zs


def friendly_approach_source(
    routes: list[dict[str, Any]],
    view_bounds: tuple[float, float, float, float],
    center_x: float,
    center_y: float,
) -> tuple[float, float] | None:
    """Return a representative pre-entry point for the selected friendly routes."""
    candidates: list[tuple[float, float]] = []
    for route in routes:
        waypoints = list(route.get("waypoints") or [])
        if not waypoints:
            continue
        inside = [
            index
            for index, waypoint in enumerate(waypoints)
            if point_in_bounds(safe_float(waypoint.get("grid_x")), safe_float(waypoint.get("grid_y")), view_bounds)
        ]
        if inside:
            first_inside = min(inside)
            source_index = max(0, first_inside - 1)
            source = waypoints[source_index]
        else:
            source = min(
                waypoints,
                key=lambda waypoint: (safe_float(waypoint.get("grid_x")) - center_x) ** 2
                + (safe_float(waypoint.get("grid_y")) - center_y) ** 2,
            )
        candidates.append((safe_float(source.get("grid_x")), safe_float(source.get("grid_y"))))
    if not candidates:
        return None
    return (
        float(np.median([point[0] for point in candidates])),
        float(np.median([point[1] for point in candidates])),
    )


def compass_sector(dx_east: float, dy_north: float) -> str:
    bearing = (math.degrees(math.atan2(dx_east, dy_north)) + 360.0) % 360.0
    sectors = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return sectors[int((bearing + 22.5) // 45.0) % 8]


def projected_vector(ax: Any, dx: float, dy: float, dz: float = 0.0) -> tuple[float, float]:
    """Project a world vector into screen coordinates with positive y upward."""
    x0, y0, _ = proj3d.proj_transform(0.0, 0.0, 0.0, ax.get_proj())
    x1, y1, _ = proj3d.proj_transform(dx, dy, dz, ax.get_proj())
    p0 = np.asarray(ax.transData.transform((x0, y0)), dtype=float)
    p1 = np.asarray(ax.transData.transform((x1, y1)), dtype=float)
    vector = p1 - p0
    length = float(np.linalg.norm(vector))
    if length < 1e-6:
        return (0.0, 1.0)
    return (float(vector[0] / length), float(vector[1] / length))


def overlay_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def transform_overlay_vector(
    vector: tuple[float, float],
    width: int,
    height: int,
    post_crop: list[int] | tuple[int, int, int, int] | None,
) -> tuple[float, float]:
    dx, dy_up = vector
    if post_crop:
        left, top, right, bottom = post_crop
        dx *= width / max(float(right - left), 1.0)
        dy_up *= height / max(float(bottom - top), 1.0)
    length = math.hypot(dx, dy_up)
    if length < 1e-6:
        return (0.0, -1.0)
    return (dx / length, -dy_up / length)  # Pillow y increases downward.


def draw_attack_geometry_overlays(
    path: Path,
    *,
    north_vector: tuple[float, float],
    east_vector: tuple[float, float],
    friendly_vector: tuple[float, float] | None,
    friendly_sector: str | None,
    friendly_label: str,
    post_crop: list[int] | tuple[int, int, int, int] | None,
    show_compass: bool,
    show_friendly: bool,
    view_preset: str,
) -> None:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    draw = ImageDraw.Draw(image, "RGBA")
    font = overlay_font(max(20, round(height * 0.022)))
    small_font = overlay_font(max(16, round(height * 0.017)))

    if show_compass:
        nx, ny = transform_overlay_vector(north_vector, width, height, post_crop)
        ex, ey = transform_overlay_vector(east_vector, width, height, post_crop)
        base = (width * 0.905, height * 0.84)
        radius = height * 0.075
        draw.ellipse(
            (base[0] - radius * 1.05, base[1] - radius * 1.05, base[0] + radius * 1.05, base[1] + radius * 1.05),
            fill=(4, 13, 16, 148),
            outline=(239, 246, 242, 210),
            width=max(2, round(height * 0.002)),
        )
        north_tip = (base[0] + nx * radius, base[1] + ny * radius)
        east_tip = (base[0] + ex * radius * 0.78, base[1] + ey * radius * 0.78)
        draw.line((base, north_tip), fill=(255, 255, 255, 245), width=max(4, round(height * 0.004)))
        draw.polygon(
            [
                north_tip,
                (north_tip[0] - nx * radius * 0.18 - ny * radius * 0.09, north_tip[1] - ny * radius * 0.18 + nx * radius * 0.09),
                (north_tip[0] - nx * radius * 0.18 + ny * radius * 0.09, north_tip[1] - ny * radius * 0.18 - nx * radius * 0.09),
            ],
            fill=(255, 255, 255, 245),
        )
        draw.line((base, east_tip), fill=(150, 207, 224, 230), width=max(2, round(height * 0.0025)))
        draw.text((north_tip[0] + nx * 8, north_tip[1] + ny * 8), "N", font=font, anchor="mm", fill=(255, 255, 255, 255))
        draw.text((east_tip[0] + ex * 8, east_tip[1] + ey * 8), "E", font=small_font, anchor="mm", fill=(180, 229, 239, 255))

    if show_friendly and friendly_vector is not None and friendly_sector:
        fx, fy = transform_overlay_vector(friendly_vector, width, height, post_crop)
        # Put the origin callout on the frame edge in the actual projected
        # source direction, then point inward toward the target complex.
        center = np.asarray((width * 0.50, height * 0.52), dtype=float)
        direction = np.asarray((fx, fy), dtype=float)
        edge_scale = min(
            (width * 0.42) / max(abs(direction[0]), 0.05),
            (height * 0.38) / max(abs(direction[1]), 0.05),
        )
        start = center + direction * edge_scale
        end = start - direction * height * 0.105
        line_width = max(5, round(height * 0.005))
        draw.line((tuple(start), tuple(end)), fill=(43, 226, 126, 245), width=line_width)
        arrow = height * 0.026
        perp = np.asarray((-direction[1], direction[0]))
        draw.polygon(
            [tuple(end), tuple(end + direction * arrow + perp * arrow * 0.46), tuple(end + direction * arrow - perp * arrow * 0.46)],
            fill=(43, 226, 126, 250),
        )
        label = f"{friendly_label}\nFROM {friendly_sector}"
        bbox = draw.multiline_textbbox((0, 0), label, font=small_font, spacing=2, align="center")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_center = start - direction * (height * 0.025)
        pad = max(8, round(height * 0.009))
        draw.rounded_rectangle(
            (
                text_center[0] - text_width / 2 - pad,
                text_center[1] - text_height / 2 - pad,
                text_center[0] + text_width / 2 + pad,
                text_center[1] + text_height / 2 + pad,
            ),
            radius=pad,
            fill=(3, 20, 14, 205),
            outline=(43, 226, 126, 245),
            width=max(2, round(height * 0.002)),
        )
        draw.multiline_text(tuple(text_center), label, font=small_font, anchor="mm", spacing=2, align="center", fill=(226, 255, 238, 255))

    pnginfo = PngInfo()
    pnginfo.add_text("bms_3d_profile", view_preset)
    pnginfo.add_text("bms_3d_compass", "projected-north-east" if show_compass else "disabled")
    pnginfo.add_text(
        "bms_3d_friendly_approach",
        f"{friendly_label}|{friendly_sector}" if show_friendly and friendly_sector else "disabled",
    )
    image.save(path, pnginfo=pnginfo)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tag_3d_provenance(
    path: Path,
    *,
    args: argparse.Namespace,
    mission_context: dict[str, Any],
    overlay_bounds: tuple[float, float, float, float],
    terrain_bounds: tuple[float, float, float, float],
    unit_count: int,
    feature_count: int,
) -> None:
    with Image.open(path) as source:
        image = source.copy()
        pnginfo = PngInfo()
        for key, value in source.info.items():
            if isinstance(value, str):
                pnginfo.add_text(key, value)
    context_payload = json.dumps(mission_context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    pnginfo.add_text("bms_3d_command_json", json.dumps(sys.argv[1:], ensure_ascii=False))
    pnginfo.add_text("bms_3d_overlay_bounds", json.dumps([round(value, 3) for value in overlay_bounds]))
    pnginfo.add_text("bms_3d_terrain_bounds", json.dumps([round(value, 3) for value in terrain_bounds]))
    pnginfo.add_text("bms_3d_unit_count", str(unit_count))
    pnginfo.add_text("bms_3d_feature_count", str(feature_count))
    pnginfo.add_text("bms_3d_context_sha256", hashlib.sha256(context_payload).hexdigest())
    pnginfo.add_text("bms_3d_cam_decode_sha256", sha256_file(args.cam_decode) if args.cam_decode and args.cam_decode.is_file() else "")
    pnginfo.add_text("bms_3d_map_source", str(args.map_source.resolve()) if args.map_source else "")
    pnginfo.add_text("bms_3d_background_fill", "true" if args.fill_background else "false")
    pnginfo.add_text("bms_3d_projection", "orthographic" if args.orthographic else "perspective")
    image.save(path, optimize=True, compress_level=9, pnginfo=pnginfo)


def render(args: argparse.Namespace) -> None:
    syntheses = [load_json(Path(path)) for path in args.synthesis]
    package_ids = {safe_int(item) for item in args.package_id}
    packages = find_packages(syntheses, package_ids)
    mission_context = syntheses[0].get("mission_context") or {}
    cam_decode = load_json(args.cam_decode) if args.cam_decode else None
    raw_flights = raw_flights_by_package(cam_decode, package_ids)
    allowed_callsigns = {normalize_callsign(item) for item in args.callsign}

    marks = collect_named_marks(syntheses, packages, mission_context)
    add_orion_target(packages, marks)
    air_defenses = collect_air_defenses(packages, marks, mission_context)
    routes = build_routes(packages, raw_flights, allowed_callsigns)
    overlay_bounds = (
        (args.crop_grid_bounds[0], args.crop_grid_bounds[2], args.crop_grid_bounds[1], args.crop_grid_bounds[3])
        if args.crop_grid_bounds
        else bounds_from_labels(args.crop_label, marks, air_defenses, routes, args.margin_grid)
    )
    view_bounds = expand_bounds(overlay_bounds, args.view_extra_grid)
    bounds = expand_bounds(view_bounds, args.terrain_extra_grid)
    center_x = (view_bounds[0] + view_bounds[1]) / 2.0
    center_y = (view_bounds[2] + view_bounds[3]) / 2.0
    if args.friendly_origin_grid:
        friendly_source = (safe_float(args.friendly_origin_grid[0]), safe_float(args.friendly_origin_grid[1]))
    else:
        friendly_source = friendly_approach_source(routes, view_bounds, center_x, center_y)
    if friendly_source is None and not args.no_friendly_approach:
        raise SystemExit(
            "Unable to derive friendly approach direction from selected package routes. "
            "Provide --cam-decode/--friendly-origin-grid or use --no-friendly-approach for a diagnostic-only render."
        )
    friendly_world_vector: tuple[float, float] | None = None
    friendly_sector: str | None = None
    if friendly_source is not None:
        friendly_dx = friendly_source[0] - center_x
        friendly_dy = friendly_source[1] - center_y
        friendly_world_vector = (friendly_dx * GRID_NM, friendly_dy * GRID_NM)
        friendly_sector = compass_sector(friendly_dx, friendly_dy)

    x_nm, y_nm, z_kft, elevations_ft = read_heightmap_crop(
        args.heightmap,
        bounds,
        mesh_size=args.mesh_size,
        z_exaggeration=args.z_exaggeration,
        center=(center_x, center_y),
    )
    if args.photoreal_tile_dir:
        facecolors = texture_from_photoreal_tiles(
            args.photoreal_tile_dir,
            bounds,
            elevations_ft.shape,
            alpha=args.map_texture_alpha,
            elevations_ft=elevations_ft,
            hillshade_strength=args.hillshade_strength,
            tile_grid_size=args.photoreal_tile_grid_size,
            tile_origin=args.photoreal_tile_origin,
            tile_index_base=args.photoreal_tile_index_base,
        )
    elif args.map_source:
        facecolors = texture_from_map(
            args.map_source,
            bounds,
            elevations_ft.shape,
            alpha=args.map_texture_alpha,
            elevations_ft=elevations_ft,
            hillshade_strength=args.hillshade_strength,
        )
    else:
        facecolors = terrain_facecolors(elevations_ft)
    facecolors = wash_texture(facecolors, args.texture_wash)

    fig = plt.figure(figsize=(args.width / args.dpi, args.height / args.dpi), dpi=args.dpi)
    fig.patch.set_facecolor(args.background_color)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0], projection="3d", computed_zorder=False)
    ax.set_facecolor(args.background_color)
    ax.plot_surface(
        x_nm,
        y_nm,
        z_kft,
        facecolors=facecolors,
        rstride=1,
        cstride=1,
        linewidth=0,
        antialiased=True,
        shade=False,
    )

    z_floor = float(np.nanmin(z_kft))
    z_max = float(np.nanmax(z_kft))
    marker_z_lift = args.marker_lift_ft / 1000.0 * args.z_exaggeration
    pin_height = args.pin_height_ft / 1000.0 * args.z_exaggeration
    projected_labels: list[tuple[float, float, float, str, str, str]] = []
    projected_unit_symbols: list[tuple[float, float, float, str, str, float, float]] = []
    projected_ip_symbols: list[tuple[float, float, float, str]] = []

    objective_feature_count = 0
    if args.show_objective_features:
        if not args.camp_obj_data or not args.object_dir:
            raise SystemExit("--show-objective-features requires both --camp-obj-data and --object-dir.")
        objective_features = collect_objective_features(
            args.camp_obj_data,
            args.object_dir,
            view_bounds,
            include_patterns=args.objective_feature_filter,
            exclude_patterns=args.objective_feature_exclude,
            mode=args.objective_feature_mode,
            max_per_objective=args.objective_feature_max_per_objective,
            limit=args.objective_feature_limit,
        )
        objective_feature_count = len(objective_features)
        if not objective_features and not args.allow_empty_objective_features:
            raise SystemExit("No objective features matched the 3D crop/filter; refusing a landmark-empty deliverable.")
        draw_objective_features(
            ax,
            objective_features,
            center_x=center_x,
            center_y=center_y,
            heightmap_path=args.heightmap,
            z_exaggeration=args.z_exaggeration,
            alpha_scale=args.objective_feature_alpha,
            height_scale=args.objective_feature_height_scale,
            footprint_scale=args.objective_feature_footprint_scale,
        )

    # Keep each tactical edge as one straight BMS segment while anchoring its
    # endpoints to terrain, so it remains positionally comparable to units.
    if args.show_killboxes:
        selected_killboxes = {normalize_label(item) for item in args.killbox_label}
        for spec in mission_context.get("map_killboxes") or []:
            label = str(spec.get("label") or "").strip()
            if selected_killboxes and normalize_label(label) not in selected_killboxes:
                continue
            points = [
                (safe_float(point.get("grid_x")), safe_float(point.get("grid_y")))
                for point in spec.get("points") or []
                if point.get("grid_x") is not None and point.get("grid_y") is not None
            ]
            if len(points) < 3:
                continue
            for start, end in zip(points, [*points[1:], points[0]]):
                # Plot the genuine BMS edge rather than closing the polygon on
                # the crop boundary. Matplotlib then clips the continuing edge
                # at the visible image frame.
                (start_x, start_y), (end_x, end_y) = start, end
                x1, y1 = grid_to_nm(start_x, start_y, center_x, center_y)
                x2, y2 = grid_to_nm(end_x, end_y, center_x, center_y)
                # Retain a straight BMS edge, but terrain-reference its two end
                # points.  A single horizontal plane caused obvious parallax
                # against ground-anchored battalion symbols in oblique views.
                z1 = (sample_elevation_ft(args.heightmap, start_x, start_y) + args.killbox_lift_ft) / 1000.0 * args.z_exaggeration
                z2 = (sample_elevation_ft(args.heightmap, end_x, end_y) + args.killbox_lift_ft) / 1000.0 * args.z_exaggeration
                ax.plot([x1, x2], [y1, y2], [z1, z2], color="#071012", linewidth=args.killbox_linewidth + 2.2, alpha=1.0, zorder=88)
                ax.plot([x1, x2], [y1, y2], [z1, z2], color=args.killbox_color, linewidth=args.killbox_linewidth, alpha=args.killbox_alpha, zorder=89)

    if args.show_ground_units and cam_decode:
        ground_units = collect_objective_battalions(cam_decode, packages, mission_context)
        for unit in ground_units:
            grid_x = safe_float(unit.get("grid_x"))
            grid_y = safe_float(unit.get("grid_y"))
            if not point_in_bounds(grid_x, grid_y, overlay_bounds, pad=0.5):
                continue
            x, y = grid_to_nm(grid_x, grid_y, center_x, center_y)
            ground_z = sample_elevation_ft(args.heightmap, grid_x, grid_y) / 1000.0 * args.z_exaggeration
            z = ground_z + args.ground_unit_lift_ft / 1000.0 * args.z_exaggeration
            class_name = str(unit.get("class_name") or "").upper()
            affiliation = str(unit.get("affiliation") or "hostile").lower()
            projected_unit_symbols.append((x, y, z, class_name, affiliation, grid_x, grid_y))

    # ADA rings first, beneath labels and route lines.
    theta = np.linspace(0, 2 * math.pi, 220)
    for air_defense in air_defenses:
        grid_x = safe_float(air_defense.get("grid_x"))
        grid_y = safe_float(air_defense.get("grid_y"))
        if not point_in_bounds(grid_x, grid_y, overlay_bounds, pad=nm_to_grid(args.ring_pad_nm)):
            continue
        radius_grid = max(safe_float(air_defense.get("air_range")), safe_float(air_defense.get("low_air_range")))
        radius_nm = radius_grid * GRID_NM
        cx, cy = grid_to_nm(grid_x, grid_y, center_x, center_y)
        ring_z = sample_elevation_ft(args.heightmap, grid_x, grid_y) / 1000.0 * args.z_exaggeration + 0.04
        ax.plot(
            cx + np.cos(theta) * radius_nm,
            cy + np.sin(theta) * radius_nm,
            np.full_like(theta, ring_z),
            color="#ff3333",
            linewidth=args.ring_linewidth,
            alpha=args.ring_alpha,
        )

    if args.show_individual_routes:
        for route in routes:
            waypoints = [
                waypoint
                for waypoint in route["waypoints"]
                if point_in_bounds(safe_float(waypoint.get("grid_x")), safe_float(waypoint.get("grid_y")), overlay_bounds, pad=args.route_pad_grid)
            ]
            if len(waypoints) < 2:
                continue
            if not any(point_in_bounds(safe_float(wp.get("grid_x")), safe_float(wp.get("grid_y")), overlay_bounds, pad=args.route_pad_grid) for wp in waypoints):
                continue
            xs: list[float] = []
            ys: list[float] = []
            zs: list[float] = []
            for waypoint in waypoints:
                grid_x = safe_float(waypoint.get("grid_x"))
                grid_y = safe_float(waypoint.get("grid_y"))
                x, y = grid_to_nm(grid_x, grid_y, center_x, center_y)
                xs.append(x)
                ys.append(y)
                ground = sample_elevation_ft(args.heightmap, grid_x, grid_y)
                planned_agl = max(safe_float(waypoint.get("grid_z")), args.route_lift_ft)
                zs.append((ground + planned_agl) / 1000.0 * args.z_exaggeration)
            color = route_color_from_context(route, mission_context)
            ax.plot(xs, ys, zs, color=color, linewidth=args.route_linewidth, alpha=0.92)
            for index in range(1, len(xs)):
                if point_in_bounds(safe_float(waypoints[index].get("grid_x")), safe_float(waypoints[index].get("grid_y")), overlay_bounds, pad=0):
                    ax.scatter([xs[index]], [ys[index]], [zs[index]], s=14, color=color, alpha=0.8, depthshade=False)

    if args.ingress_route_callsign:
        xs, ys, zs = route_points_for_callsign(
            routes,
            args.ingress_route_callsign,
            view_bounds,
            center_x=center_x,
            center_y=center_y,
            heightmap_path=args.heightmap,
            z_exaggeration=args.z_exaggeration,
            lift_ft=args.ingress_lift_ft,
            pad_grid=args.ingress_route_pad_grid,
        )
        if len(xs) >= 2:
            ax.plot(xs, ys, zs, color="#061012", linewidth=args.ingress_linewidth + 2.8, alpha=args.ingress_outline_alpha, zorder=80)
            ax.plot(xs, ys, zs, color=args.ingress_color, linewidth=args.ingress_linewidth, alpha=args.ingress_alpha, zorder=81)
            if args.ingress_marker_alpha > 0:
                ax.scatter(xs, ys, zs, s=20, color=args.ingress_color, edgecolors="#061012", linewidths=0.6, alpha=args.ingress_marker_alpha, depthshade=False, zorder=82)
        if args.ingress_highlight_waypoint >= 0:
            wanted = normalize_callsign(args.ingress_route_callsign)
            route = next((item for item in routes if normalize_callsign(item.get("callsign")) == wanted), None)
            waypoints = list(route.get("waypoints") or []) if route else []
            if args.ingress_highlight_waypoint < len(waypoints):
                waypoint = waypoints[args.ingress_highlight_waypoint]
                grid_x = safe_float(waypoint.get("grid_x"))
                grid_y = safe_float(waypoint.get("grid_y"))
                if point_in_bounds(grid_x, grid_y, overlay_bounds, pad=0.0):
                    x, y = grid_to_nm(grid_x, grid_y, center_x, center_y)
                    ground = sample_elevation_ft(args.heightmap, grid_x, grid_y)
                    planned_agl = max(safe_float(waypoint.get("grid_z")), args.ingress_lift_ft)
                    z = (ground + planned_agl) / 1000.0 * args.z_exaggeration
                    ax.scatter([x], [y], [z], marker="o", s=88, facecolors="#f7fbff", edgecolors="#061012", linewidths=1.5, alpha=1.0, depthshade=False, zorder=83)
                    projected_labels.append((x, y, z + 0.18, f"STPT {args.ingress_highlight_waypoint}", "#f7fbff", args.ingress_color))
    elif args.ingress_line:
        xs, ys, zs = route_points_for_labels(
            args.ingress_line,
            marks,
            center_x=center_x,
            center_y=center_y,
            heightmap_path=args.heightmap,
            z_exaggeration=args.z_exaggeration,
            lift_ft=args.ingress_lift_ft,
        )
        if len(xs) >= 2:
            ax.plot(xs, ys, zs, color="#061012", linewidth=args.ingress_linewidth + 2.8, alpha=args.ingress_outline_alpha, zorder=80)
            ax.plot(xs, ys, zs, color=args.ingress_color, linewidth=args.ingress_linewidth, alpha=args.ingress_alpha, zorder=81)
            if args.ingress_marker_alpha > 0:
                ax.scatter(xs, ys, zs, s=20, color=args.ingress_color, edgecolors="#061012", linewidths=0.6, alpha=args.ingress_marker_alpha, depthshade=False, zorder=82)

    # Named marks and air-defense pins.
    label_offsets = [
        (0.35, 0.15),
        (-0.35, 0.25),
        (0.25, -0.35),
        (-0.25, -0.25),
        (0.55, 0.45),
        (-0.55, 0.45),
    ]
    ad_label_offsets = [
        (0.0, 0.75),
        (0.85, 0.0),
        (0.0, -0.75),
        (-0.85, 0.0),
        (0.9, 0.65),
        (-0.9, 0.65),
    ]
    label_count = 0
    for mark in marks:
        grid_x = safe_float(mark.get("grid_x"))
        grid_y = safe_float(mark.get("grid_y"))
        if not point_in_bounds(grid_x, grid_y, overlay_bounds):
            continue
        x, y = grid_to_nm(grid_x, grid_y, center_x, center_y)
        z = sample_elevation_ft(args.heightmap, grid_x, grid_y) / 1000.0 * args.z_exaggeration + marker_z_lift
        label = str(mark.get("label") or "")
        normalized_mark_label = normalize_label(label)
        if normalized_mark_label in args.hide_mark_label:
            continue
        if args.ip_only_marks and not normalized_mark_label.startswith("IP"):
            continue
        if normalized_mark_label.isdigit() or normalized_mark_label in {
            "10W",
            "10E",
            "10S",
            "10A",
            "10B",
            "10C",
            "SA6",
            "SA5",
        }:
            continue
        color = "#2ee878" if normalize_label(label) != "ORION" else "#f5f6f0"
        is_ip = normalized_mark_label.startswith("IP")
        marker = "D" if normalize_label(label) != "ORION" else "s"
        if is_ip:
            projected_ip_symbols.append((x, y, z + 0.18, label))
            continue
        ax.scatter([x], [y], [z], marker=marker, s=args.mark_size, color=color, edgecolors="#06150b", linewidths=1.2, alpha=args.marker_alpha, depthshade=False)
        dx, dy = label_offsets[label_count % len(label_offsets)]
        label_count += 1
        shown = label
        if normalize_label(label) == "ORION":
            shown = "ORION / Gimhae"
        if label in args.mark_label_offset:
            parts = args.mark_label_offset[label].split(",", 1)
            if len(parts) == 2:
                dx = safe_float(parts[0], dx)
                dy = safe_float(parts[1], dy)
        projected_labels.append((x + dx, y + dy, z + 0.28, shown, "#f6fff5", color))

    ad_groups: dict[tuple[int, int], dict[str, Any]] = {}
    for air_defense in air_defenses:
        grid_x = safe_float(air_defense.get("grid_x"))
        grid_y = safe_float(air_defense.get("grid_y"))
        if not point_in_bounds(grid_x, grid_y, overlay_bounds):
            continue
        key = (round(grid_x), round(grid_y))
        group = ad_groups.setdefault(
            key,
            {
                "grid_x": grid_x,
                "grid_y": grid_y,
                "labels": [],
            },
        )
        label = str(air_defense.get("map_label") or "SAM")
        if label not in group["labels"]:
            group["labels"].append(label)

    def ad_label_sort_key(value: str) -> tuple[int, str]:
        if value.startswith("10"):
            return (0, value)
        if value == "6":
            return (1, value)
        if value == "5":
            return (2, value)
        return (9, value)

    ad_count = 0
    for group in ad_groups.values():
        grid_x = safe_float(group.get("grid_x"))
        grid_y = safe_float(group.get("grid_y"))
        x, y = grid_to_nm(grid_x, grid_y, center_x, center_y)
        ground_z = sample_elevation_ft(args.heightmap, grid_x, grid_y) / 1000.0 * args.z_exaggeration
        ground_marker_z = ground_z + max(0.015, pin_height * 0.012)
        top_z = ground_z + pin_height
        ax.scatter(
            [x],
            [y],
            [ground_marker_z],
            marker="s",
            s=max(args.ad_size * 0.34, 18.0),
            facecolors="#fff4ef",
            edgecolors="#ff2828",
            linewidths=1.0,
            alpha=args.ad_marker_alpha,
            depthshade=False,
        )
        ax.plot([x, x], [y, y], [ground_z, top_z], color="#ff2828", linewidth=2.4, alpha=args.ad_marker_alpha)
        ax.scatter([x], [y], [top_z], marker="^", s=args.ad_size, color="#ff2a2a", edgecolors="#fff0e8", linewidths=1.1, alpha=args.ad_marker_alpha, depthshade=False)
        dx, dy = ad_label_offsets[ad_count % len(ad_label_offsets)]
        ad_count += 1
        label = "/".join(sorted(group["labels"], key=ad_label_sort_key))
        if label in args.ad_label_offset:
            parts = args.ad_label_offset[label].split(",", 1)
            if len(parts) == 2:
                dx = safe_float(parts[0], dx)
                dy = safe_float(parts[1], dy)
        label_x = x + dx
        label_y = y + dy
        label_z = top_z + 0.45
        if args.ad_label_leader_alpha > 0:
            ax.plot([x, label_x], [y, label_y], [top_z, label_z], color="#ff2828", linewidth=1.2, alpha=args.ad_label_leader_alpha)
        projected_labels.append((label_x, label_y, label_z, label, "#fff4ef", "#ff3636"))

    if not args.no_title:
        title = args.title or "3D Objective Area Prototype"
        subtitle = f"Packages {', '.join(str(item) for item in sorted(package_ids))} | BMS heightmap + campaign grid overlays"
        ax.text2D(0.025, 0.955, title, transform=ax.transAxes, color="#f6fff5", fontsize=18, weight="bold")
        ax.text2D(0.025, 0.925, subtitle, transform=ax.transAxes, color="#c8d5d2", fontsize=10)
    if not args.no_footer:
        ax.text2D(0.025, 0.035, f"Vertical exaggeration {args.z_exaggeration:g}x | view {view_bounds[0]:.1f}-{view_bounds[1]:.1f} / {view_bounds[2]:.1f}-{view_bounds[3]:.1f} grid", transform=ax.transAxes, color="#c8d5d2", fontsize=9)

    ax.view_init(elev=args.camera_elev, azim=args.camera_azim)
    if args.orthographic:
        ax.set_proj_type("ortho")
    if args.camera_distance > 0:
        try:
            ax.dist = args.camera_distance
        except Exception:
            pass
    view_x_min = (view_bounds[0] - center_x) * GRID_NM
    view_x_max = (view_bounds[1] - center_x) * GRID_NM
    view_y_min = (view_bounds[2] - center_y) * GRID_NM
    view_y_max = (view_bounds[3] - center_y) * GRID_NM
    ax.set_xlim(view_x_min, view_x_max)
    ax.set_ylim(view_y_min, view_y_max)
    ax.set_zlim(z_floor, max(z_max + pin_height + 0.7, 2.0))
    ax.set_box_aspect((max(view_x_max - view_x_min, 1.0) * args.box_x_scale, max(view_y_max - view_y_min, 1.0) * args.box_y_scale, args.vertical_box_aspect))
    ax.set_axis_off()
    north_vector = projected_vector(ax, 0.0, 1.0)
    east_vector = projected_vector(ax, 1.0, 0.0)
    friendly_screen_vector = (
        projected_vector(ax, friendly_world_vector[0], friendly_world_vector[1])
        if friendly_world_vector is not None
        else None
    )
    for x, y, z, text, color, edge in projected_labels:
        xp, yp, _ = proj3d.proj_transform(x, y, z, ax.get_proj())
        ax.annotate(
            text,
            xy=(xp, yp),
            xycoords="data",
            xytext=(0, 0),
            textcoords="offset points",
            ha="center",
            va="center",
            color=color,
            fontsize=args.label_font_size,
            weight="bold",
            alpha=args.label_alpha,
            bbox={"facecolor": "#071012", "edgecolor": edge, "alpha": args.label_box_alpha, "pad": 2.8},
            zorder=5000,
        )
    # Compactly stagger battalions that are co-located or within one campaign
    # grid square.  This exposes different branch symbols while keeping the
    # leader short enough that the tactical side of the boundary stays clear.
    unit_clusters: list[list[int]] = []
    for item_index, (_, _, _, _, _, grid_x, grid_y) in enumerate(projected_unit_symbols):
        assigned = False
        for cluster in unit_clusters:
            if any(
                math.hypot(grid_x - projected_unit_symbols[other][5], grid_y - projected_unit_symbols[other][6]) <= 1.45
                for other in cluster
            ):
                cluster.append(item_index)
                assigned = True
                break
        if not assigned:
            unit_clusters.append([item_index])
    cluster_by_index = {item_index: cluster for cluster in unit_clusters for item_index in cluster}

    for item_index, (x, y, z, class_name, affiliation, grid_x, grid_y) in enumerate(projected_unit_symbols):
        xp, yp, _ = proj3d.proj_transform(x, y, z, ax.get_proj())
        cluster = cluster_by_index[item_index]
        index = cluster.index(item_index)
        count = len(cluster)
        if count > 1:
            angle = -math.pi / 2.0 + (2.0 * math.pi * index / count)
            radius = args.ground_unit_fan_offset
            offset = (math.cos(angle) * radius, math.sin(angle) * radius)
        else:
            offset = (0.0, 0.0)
        artist = mil2525_unit_artist(class_name, affiliation, args.ground_unit_icon_size, args.ground_unit_alpha)
        arrowprops = None
        if count > 1 or offset != (0.0, 0.0):
            arrowprops = {"arrowstyle": "-", "color": "#252525", "linewidth": 0.8, "alpha": 0.8}
        ax.add_artist(
            AnnotationBbox(
                artist,
                (xp, yp),
                xycoords="data",
                xybox=offset,
                boxcoords="offset points",
                frameon=False,
                pad=0,
                arrowprops=arrowprops,
                zorder=6100,
            )
        )
    for x, y, z, label in projected_ip_symbols:
        xp, yp, _ = proj3d.proj_transform(x, y, z, ax.get_proj())
        ax.add_artist(
            AnnotationBbox(
                mil2525_ip_artist(label, args.ip_icon_size, args.ip_alpha),
                (xp, yp),
                xycoords="data",
                frameon=False,
                pad=0,
                zorder=6200,
            )
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs: dict[str, Any] = {"facecolor": fig.get_facecolor()}
    if args.tight:
        save_kwargs.update({"bbox_inches": "tight", "pad_inches": 0.02})
    fig.savefig(args.out, **save_kwargs)
    plt.close(fig)
    if args.post_crop:
        left, top, right, bottom = args.post_crop
        image = Image.open(args.out).convert("RGB")
        cropped = image.crop((left, top, right, bottom))
        cropped = cropped.resize((args.width, args.height), Image.Resampling.LANCZOS)
        cropped.save(args.out)
    if args.fill_background:
        fill_render_background(args.out, args.background_color, args.fill_background_threshold, args.fill_background_blur)
    draw_attack_geometry_overlays(
        args.out,
        north_vector=north_vector,
        east_vector=east_vector,
        friendly_vector=friendly_screen_vector,
        friendly_sector=friendly_sector,
        friendly_label=args.friendly_approach_label,
        post_crop=args.post_crop,
        show_compass=not args.no_compass,
        show_friendly=not args.no_friendly_approach,
        view_preset=args.view_preset,
    )
    tag_3d_provenance(
        args.out,
        args=args,
        mission_context=mission_context,
        overlay_bounds=overlay_bounds,
        terrain_bounds=bounds,
        unit_count=len(projected_unit_symbols),
        feature_count=objective_feature_count,
    )
    print(f"Wrote {args.out}")


def apply_view_preset(args: argparse.Namespace) -> argparse.Namespace:
    preset = VIEW_PRESETS[args.view_preset]
    for key, value in preset.items():
        if getattr(args, key) is None:
            setattr(args, key, value)
    if args.post_crop is None and args.view_preset == "attack-geometry":
        # Normalized form of the accepted Event 740 close framing. Scale with
        # output resolution so the preset remains 16:9-safe.
        args.post_crop = [
            round(args.width * 0.21875),
            round(args.height * 0.29333),
            round(args.width * 0.78125),
            round(args.height * 0.82222),
        ]
    return args


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, nargs="+", required=True, help="One or more briefing_synthesis.json files.")
    parser.add_argument("--cam-decode", type=Path, help="Optional cam_decode.json for full route waypoints.")
    parser.add_argument("--package-id", type=int, nargs="+", required=True, help="Player package ID(s) to render.")
    parser.add_argument("--callsign", nargs="*", default=[], help="Optional callsign filter. Defaults to all flights in selected packages.")
    parser.add_argument("--heightmap", type=Path, required=True, help="BMS NewTerrain HeightMap.raw.")
    parser.add_argument("--map-source", type=Path, help="Optional north-up theater chart/texture to drape over terrain. Use Skyvector for normal briefing imagery.")
    parser.add_argument("--photoreal-tile-dir", type=Path, help="Opt-in BMS numeric photoreal tile directory, such as NewTerrain/Photoreal/16K.")
    parser.add_argument("--photoreal-tile-grid-size", type=int, default=32, help="Virtual row/column count for numeric photoreal tiles.")
    parser.add_argument("--photoreal-tile-origin", choices=("bottom-left", "top-left"), default="top-left", help="Storage origin for numeric tile IDs.")
    parser.add_argument("--photoreal-tile-index-base", type=int, default=1, help="First numeric tile ID in the photoreal tile set.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--view-preset",
        choices=tuple(VIEW_PRESETS),
        default="attack-geometry",
        help="3D camera/render profile. The default attack-geometry preset reproduces the accepted Event 740 close terrain treatment.",
    )
    parser.add_argument("--title", default="")
    parser.add_argument("--no-title", action="store_true")
    parser.add_argument("--no-footer", action="store_true")
    parser.add_argument("--crop-label", nargs="+", default=["CRO", "BLU", "SA6", "10W", "10E", "SA5", "WWO", "BAN"], help="Named marks/ADA labels used to frame the crop.")
    parser.add_argument("--crop-grid-bounds", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"), help="Exact BMS grid crop, used instead of --crop-label.")
    parser.add_argument("--margin-grid", type=float, default=None)
    parser.add_argument("--view-extra-grid", type=float, default=None, help="Add visible map around the tactical crop without changing which overlays are included.")
    parser.add_argument("--terrain-extra-grid", type=float, default=None, help="Render extra terrain outside the tactical crop so oblique views can fill the frame.")
    parser.add_argument("--mesh-size", type=int, default=None)
    parser.add_argument("--width", type=int, default=2400)
    parser.add_argument("--height", type=int, default=1350)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--z-exaggeration", type=float, default=None)
    parser.add_argument("--vertical-box-aspect", type=float, default=None)
    parser.add_argument("--box-x-scale", type=float, default=None)
    parser.add_argument("--box-y-scale", type=float, default=None)
    parser.add_argument("--camera-elev", type=float, default=None)
    parser.add_argument("--camera-azim", type=float, default=None)
    parser.add_argument("--north-up", action="store_true", help="Use a near-vertical north-up camera while retaining shallow 3D relief.")
    parser.add_argument("--camera-distance", type=float, default=None, help="Matplotlib 3D camera distance. Smaller values zoom in; <=0 leaves default.")
    parser.add_argument("--orthographic", action="store_true", help="Use orthographic 3D projection; useful for an edge-to-edge aligned terrain view without perspective side wedges.")
    parser.add_argument("--map-texture-alpha", type=float, default=None)
    parser.add_argument("--texture-wash", type=float, default=0.0, help="Blend the terrain texture toward the pale briefing style. Range 0-1.")
    parser.add_argument("--hillshade-strength", type=float, default=None, help="Blend hillshade into the draped map texture. 0 disables it; 1 is strongest.")
    parser.add_argument("--background-color", default=None)
    parser.add_argument("--fill-background", action="store_true", help="Replace the solid render background with an enlarged terrain/map underlay after cropping.")
    parser.add_argument("--fill-background-threshold", type=float, default=45.0)
    parser.add_argument("--fill-background-blur", type=float, default=7.0, help="Gaussian blur radius for the fill-background underlay.")
    parser.add_argument("--show-individual-routes", action="store_true", help="Draw each selected flight path instead of relying only on aggregate ingress lines.")
    parser.add_argument("--ingress-line", nargs="*", default=[], help="Named marks to connect as a single ingress line, e.g. BLU ORION 10W.")
    parser.add_argument("--ingress-route-callsign", default="", help="Draw a translucent decoded route segment for this callsign through the close-up view.")
    parser.add_argument("--ingress-color", default="#47c8ff")
    parser.add_argument("--ingress-linewidth", type=float, default=5.0)
    parser.add_argument("--ingress-alpha", type=float, default=0.72)
    parser.add_argument("--ingress-outline-alpha", type=float, default=0.45)
    parser.add_argument("--ingress-marker-alpha", type=float, default=0.55)
    parser.add_argument("--ingress-highlight-waypoint", type=int, default=-1, help="Show a precise labelled route waypoint in the close-up; use the decoded zero-based BMS steerpoint index.")
    parser.add_argument("--ingress-lift-ft", type=float, default=1700.0)
    parser.add_argument("--ingress-route-pad-grid", type=float, default=4.0)
    parser.add_argument("--friendly-origin-grid", nargs=2, type=float, metavar=("GRID_X", "GRID_Y"), help="Override the derived friendly pre-entry origin used by the attack-direction pointer.")
    parser.add_argument("--friendly-approach-label", default="FRIENDLY PACKAGE", help="Label shown on the friendly approach pointer.")
    parser.add_argument("--no-friendly-approach", action="store_true", help="Diagnostic opt-out only: suppress the required friendly approach pointer.")
    parser.add_argument("--no-compass", action="store_true", help="Diagnostic opt-out only: suppress the required 3D compass.")
    parser.add_argument("--ad-label-offset", action="append", default=[], type=lambda item: item.split("=", 1), help="Override ADA label offset as LABEL=dx,dy in map NM.")
    parser.add_argument("--mark-label-offset", action="append", default=[], type=lambda item: item.split("=", 1), help="Override named mark label offset as LABEL=dx,dy in map NM.")
    parser.add_argument("--hide-mark-label", action="append", default=[], help="Suppress a named mark label/marker from the 3D overlay, e.g. BAN.")
    parser.add_argument("--ip-only-marks", action="store_true", help="Show only IP control-point graphics from named map marks.")
    parser.add_argument("--camp-obj-data", type=Path, help="Optional CampObjData.XML for objective feature/building overlays.")
    parser.add_argument("--object-dir", type=Path, help="Optional TerrData/Objects directory for objective feature names/layouts.")
    parser.add_argument("--show-objective-features", action="store_true", help="Draw simplified 3D objective features from CampObjData/FED records.")
    parser.add_argument("--allow-empty-objective-features", action="store_true", help="Diagnostic only: allow a feature-enabled render with no matched landmarks.")
    parser.add_argument("--show-killboxes", action="store_true", help="Draw mission-context killbox polygons on the terrain surface.")
    parser.add_argument("--killbox-label", action="append", default=[], help="Limit killbox rendering to this label; repeat as needed.")
    parser.add_argument("--killbox-color", default="#ffd166")
    parser.add_argument("--killbox-linewidth", type=float, default=4.2)
    parser.add_argument("--killbox-alpha", type=float, default=0.96)
    parser.add_argument("--killbox-lift-ft", type=float, default=90.0)
    parser.add_argument("--show-ground-units", action="store_true", help="Draw decoded friendly and hostile battalions at their BMS positions.")
    parser.add_argument("--ground-unit-size", type=float, default=260.0, help=argparse.SUPPRESS)
    parser.add_argument("--ground-unit-font-size", type=float, default=10.0, help=argparse.SUPPRESS)
    parser.add_argument("--ground-unit-echelon-offset", type=float, default=10.0, help=argparse.SUPPRESS)
    parser.add_argument("--ground-unit-icon-size", type=float, default=42.0)
    parser.add_argument("--ground-unit-fan-offset", type=float, default=34.0)
    parser.add_argument("--ground-unit-lift-ft", type=float, default=180.0)
    parser.add_argument("--ground-unit-alpha", type=float, default=0.98)
    parser.add_argument("--ip-icon-size", type=float, default=38.0)
    parser.add_argument("--ip-alpha", type=float, default=0.76)
    parser.add_argument("--objective-feature-filter", action="append", default=[], help="Regex filter for objective names to include in 3D feature overlays.")
    parser.add_argument("--objective-feature-exclude", action="append", default=[], help="Regex filter for objective names to exclude from 3D feature overlays.")
    parser.add_argument(
        "--objective-feature-mode",
        choices=("runway-and-buildings", "buildings", "all"),
        default="runway-and-buildings",
        help="Feature classes to draw. Default keeps runway/taxi geometry and real structures while suppressing lights/signs/PAPI scatter.",
    )
    parser.add_argument("--objective-feature-max-per-objective", type=int, default=0, help="Maximum feature primitives to draw from each objective; <=0 means no per-objective cap.")
    parser.add_argument("--objective-feature-limit", type=int, default=260, help="Maximum number of feature primitives to draw; <=0 means no limit.")
    parser.add_argument("--objective-feature-alpha", type=float, default=1.0, help="Opacity multiplier for objective feature primitives.")
    parser.add_argument("--objective-feature-height-scale", type=float, default=1.0, help="Height multiplier for objective feature primitives.")
    parser.add_argument("--objective-feature-footprint-scale", type=float, default=1.0, help="Plan-view size multiplier for objective feature primitives.")
    parser.add_argument("--route-linewidth", type=float, default=3.0)
    parser.add_argument("--route-lift-ft", type=float, default=1200.0)
    parser.add_argument("--route-pad-grid", type=float, default=8.0)
    parser.add_argument("--ring-alpha", type=float, default=None)
    parser.add_argument("--ring-linewidth", type=float, default=None)
    parser.add_argument("--ring-pad-nm", type=float, default=None)
    parser.add_argument("--pin-height-ft", type=float, default=None)
    parser.add_argument("--marker-lift-ft", type=float, default=None)
    parser.add_argument("--label-font-size", type=float, default=None)
    parser.add_argument("--label-alpha", type=float, default=None)
    parser.add_argument("--label-box-alpha", type=float, default=None)
    parser.add_argument("--marker-alpha", type=float, default=None)
    parser.add_argument("--ad-marker-alpha", type=float, default=None)
    parser.add_argument("--ad-label-leader-alpha", type=float, default=None)
    parser.add_argument("--mark-size", type=float, default=None)
    parser.add_argument("--ad-size", type=float, default=None)
    parser.add_argument("--tight", action="store_true", help="Use tight bbox cropping instead of preserving the exact output frame.")
    parser.add_argument("--post-crop", nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"), help="Crop the rendered frame, then resize back to output dimensions.")
    args = parser.parse_args()
    post_crop_supplied = args.post_crop is not None
    box_x_scale_supplied = args.box_x_scale is not None
    box_y_scale_supplied = args.box_y_scale is not None
    args = apply_view_preset(args)
    if args.north_up:
        # At azimuth -90° the campaign's +Y (north) projects vertically upward.
        # 82° leaves enough elevation to read bridges and buildings as 3D forms.
        args.camera_elev = 82.0
        args.camera_azim = -90.0
        if not post_crop_supplied:
            args.post_crop = None
        if not box_x_scale_supplied:
            args.box_x_scale = 1.0
        if not box_y_scale_supplied:
            args.box_y_scale = 1.0
    args.ad_label_offset = {key: value for key, value in args.ad_label_offset if key and value}
    args.mark_label_offset = {key: value for key, value in args.mark_label_offset if key and value}
    args.hide_mark_label = {normalize_label(item) for item in args.hide_mark_label if item}
    return args


def main() -> int:
    render(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
