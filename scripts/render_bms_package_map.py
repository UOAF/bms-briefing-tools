#!/usr/bin/env python3
"""Render a Falcon BMS package map from briefing synthesis data."""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from bms_projection import feet_per_campaign_grid

FEET_PER_GRID = feet_per_campaign_grid()
FEET_PER_NM = 6076.11549
MAP_GRID_SIZE = 1024
TARGET_AREA_ACTIONS = {
    "WP_TIMING",
    "WP_PUSH",
    "WP_CAP",
    "WP_SAD",
    "WP_STRIKE",
    "WP_BOMB",
    "WP_SEAD",
    "WP_GNDSTRIKE",
    "WP_NAVSTRIKE",
    "WP_SPLIT",
}
OBJECTIVE_AREA_BASE_LABELS = {
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "WCH",
    "WATCHTOWER",
    "FOXTROT",
}

FLIGHT_COLORS = [
    (0, 210, 255),
    (255, 180, 46),
    (101, 235, 113),
    (255, 93, 142),
    (181, 140, 255),
    (255, 255, 120),
]

PPT_FILL = (45, 242, 65)
PPT_OUTLINE = (0, 24, 8)
INI_LINE = (5, 5, 5)
INI_LINE_HALO = (255, 255, 255)
AD_OUTLINE = (255, 36, 36)
AD_OUTER_WEZ = (255, 0, 0)
AD_LABEL_TEXT = (255, 245, 238)
AD_LABEL_BG = (80, 0, 0, 218)
AIRBASE_FILL = (255, 92, 92)
AIRBASE_OUTLINE = (255, 235, 225)
SUPPORT_COLORS = {
    "AWACS": (122, 210, 255),
    "JSTAR": (108, 225, 210),
    "TANKER": (255, 255, 245),
    "ECM": (210, 185, 255),
    "INTERCEPT": (255, 225, 130),
}
SUPPORT_STATION_ACTIONS = {"WP_TANKER", "WP_ELINT", "WP_AWACS", "WP_JAM", "WP_CAP"}
TEXT = (239, 244, 238)
MUTED = (183, 195, 193)
PANEL = (11, 16, 19, 228)
ROUTE_OPACITY = 0.72
MARKER_OPACITY = 0.78
LABEL_OPACITY = 0.76
THREAT_OPACITY = 0.86


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


def clamp_opacity(value: Any, default: float = 1.0) -> float:
    try:
        opacity = float(value)
    except (TypeError, ValueError):
        opacity = default
    return max(0.0, min(1.0, opacity))


def alpha(value: int, opacity: float = 1.0) -> int:
    return max(0, min(255, round(value * opacity)))


def color_alpha(color: tuple[int, ...], value: int, opacity: float = 1.0) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha(value, opacity)


def route_color(color: tuple[int, ...], value: int = 255) -> tuple[int, int, int, int]:
    return color_alpha(color, value, ROUTE_OPACITY)


def marker_color(color: tuple[int, ...], value: int = 255) -> tuple[int, int, int, int]:
    return color_alpha(color, value, MARKER_OPACITY)


def threat_color(color: tuple[int, ...], value: int = 255) -> tuple[int, int, int, int]:
    return color_alpha(color, value, THREAT_OPACITY)


def grid_to_map_px(grid_x: float, grid_y: float) -> tuple[float, float]:
    """BMS campaign grid to north-up full-theater pixel space.

    CAM waypoints use grid_x as the east/west campaign-map axis and grid_y as
    the north/south axis. North-up map rasters have image y increasing
    downward, so grid_y must be inverted against the 1024 theater extent.
    """
    return float(grid_x), MAP_GRID_SIZE - float(grid_y)


def grid_distance_to_nm(grid_distance: float) -> float:
    return grid_distance * FEET_PER_GRID / FEET_PER_NM


def nm_to_grid(nm: float) -> float:
    return nm * FEET_PER_NM / FEET_PER_GRID


def action_label(action: str | None) -> str:
    text = str(action or "WP")
    return text.replace("WP_", "") if text.startswith("WP_") else text


def normalize_callsign(callsign: str | None) -> str:
    return re.sub(r"\s+", "", str(callsign or "").lower())


def find_package(synthesis: dict[str, Any], package_id: int) -> dict[str, Any]:
    for package in synthesis.get("packages", []):
        if safe_int(package.get("package_id"), -1) == package_id:
            return package
    raise SystemExit(f"Package {package_id} was not found in synthesis data.")


def package_raw_flights(cam_decode: dict[str, Any] | None, package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not cam_decode:
        return {}
    callsigns = {normalize_callsign(flight.get("callsign")) for flight in package.get("flights", [])}
    package_id = safe_int(package.get("package_id"), -1)
    result: dict[str, dict[str, Any]] = {}
    for flight in cam_decode.get("flights", []):
        callsign = normalize_callsign(flight.get("callsign"))
        if callsign not in callsigns:
            continue
        if safe_int(flight.get("package_camp_id"), package_id) != package_id:
            continue
        result[callsign] = flight
    return result


def raw_flights_by_callsign(cam_decode: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not cam_decode:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for flight in cam_decode.get("flights", []):
        callsign = normalize_callsign(flight.get("callsign"))
        if callsign:
            result[callsign] = flight
    return result


def flight_waypoints(
    synthesis_flight: dict[str, Any],
    raw_flights: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    raw = raw_flights.get(normalize_callsign(synthesis_flight.get("callsign")))
    if raw and raw.get("waypoints"):
        waypoints = []
        key_times = {
            (wp.get("index"), wp.get("action")): wp.get("arrive_hhmm")
            for wp in synthesis_flight.get("key_waypoints", [])
        }
        for waypoint in raw.get("waypoints", []):
            if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
                continue
            action = waypoint.get("action_name")
            waypoints.append(
                {
                    "index": waypoint.get("index"),
                    "action": action,
                    "action_short": action_label(action),
                    "grid_x": waypoint.get("grid_x"),
                    "grid_y": waypoint.get("grid_y"),
                    "arrive_hhmm": key_times.get((waypoint.get("index"), action)),
                }
            )
        return waypoints
    return [
        waypoint
        for waypoint in synthesis_flight.get("key_waypoints", [])
        if waypoint.get("grid_x") is not None and waypoint.get("grid_y") is not None
    ]


def support_waypoints(
    synthesis_flight: dict[str, Any],
    all_raw_flights: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    waypoints = flight_waypoints(synthesis_flight, all_raw_flights)
    station_indexes = [
        index
        for index, waypoint in enumerate(waypoints)
        if waypoint.get("action") in SUPPORT_STATION_ACTIONS
        or f"WP_{waypoint.get('action_short')}" in SUPPORT_STATION_ACTIONS
    ]
    if not station_indexes:
        return waypoints
    start = min(station_indexes)
    end = max(station_indexes) + 1
    if end - start < 2:
        start = max(0, start - 1)
        end = min(len(waypoints), end + 1)
    clipped = []
    for index, waypoint in enumerate(waypoints[start:end], start):
        item = dict(waypoint)
        if index not in station_indexes:
            item["map_context"] = True
        clipped.append(item)
    return clipped


def load_korea_tm(path: Path) -> Image.Image:
    raw = path.read_bytes()
    if len(raw) != MAP_GRID_SIZE * MAP_GRID_SIZE * 2:
        raise SystemExit(f"{path} is not a 1024x1024 uint16 Korea.tm raster.")

    values = struct.unpack(f"<{MAP_GRID_SIZE * MAP_GRID_SIZE}H", raw)
    nonzero = sorted(value for value in values if value > 0)
    if not nonzero:
        raise SystemExit(f"{path} did not contain nonzero terrain values.")
    low = nonzero[int(len(nonzero) * 0.02)]
    high = nonzero[int(len(nonzero) * 0.985)]
    span = max(high - low, 1)

    pixels = bytearray(MAP_GRID_SIZE * MAP_GRID_SIZE * 3)
    for index, value in enumerate(values):
        if value == 0:
            color = (9, 19, 29)
        else:
            shade = max(0, min(255, int((value - low) * 255 / span)))
            color = (
                min(235, 28 + int(shade * 0.78)),
                min(235, 42 + int(shade * 0.82)),
                min(220, 39 + int(shade * 0.62)),
            )
        offset = index * 3
        pixels[offset : offset + 3] = bytes(color)

    image = Image.frombytes("RGB", (MAP_GRID_SIZE, MAP_GRID_SIZE), bytes(pixels))
    image = ImageEnhance.Contrast(image).enhance(1.16)
    image = ImageEnhance.Color(image).enhance(0.85)

    mask = Image.new("L", image.size)
    mask.putdata([255 if value > 0 else 0 for value in values])
    coast = mask.filter(ImageFilter.FIND_EDGES)
    coast_layer = Image.new("RGBA", image.size, (215, 226, 220, 0))
    coast_layer.putalpha(coast.point(lambda value: 100 if value else 0))
    return Image.alpha_composite(image.convert("RGBA"), coast_layer).convert("RGBA")


def open_base_map(path: Path) -> tuple[Image.Image, float, float, str]:
    if path.suffix.lower() == ".tm":
        return load_korea_tm(path), 1.0, 1.0, "BMS Korea.tm terrain raster"

    Image.MAX_IMAGE_PIXELS = None
    image = Image.open(path)
    width, height = image.size
    if width <= 0 or height <= 0:
        raise SystemExit(f"{path} did not open as a usable image.")
    return image, width / MAP_GRID_SIZE, height / MAP_GRID_SIZE, "full-theater image raster"


def iter_named_ini_points(synthesis: dict[str, Any], package: dict[str, Any]) -> list[dict[str, Any]]:
    points = []
    source_points = (synthesis.get("planning") or {}).get("transformed_points") or []
    if not source_points:
        source_points = package.get("plan_correlation", {}).get("point_matches", [])
    for point in source_points:
        if point.get("kind") != "ppt":
            continue
        label = str(point.get("label") or point.get("display") or "").strip()
        grid = point.get("campaign_grid") or {}
        if not label or grid.get("grid_x") is None or grid.get("grid_y") is None:
            continue
        item = dict(point)
        item["label"] = label
        points.append(item)
    return sorted(points, key=lambda item: (str(item.get("label")), safe_int(item.get("index"), 0)))


def iter_ini_line_points(package: dict[str, Any]) -> list[dict[str, Any]]:
    points = []
    for point in package.get("plan_correlation", {}).get("line_matches", []):
        grid = point.get("campaign_grid") or {}
        if grid.get("grid_x") is None or grid.get("grid_y") is None:
            continue
        points.append(point)
    return sorted(points, key=lambda item: safe_int(item.get("index"), 0))


def collect_map_bounds(
    flights: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    ini_points: list[dict[str, Any]],
    ini_line_points: list[dict[str, Any]],
    air_defenses: list[dict[str, Any]],
    airbases: list[dict[str, Any]],
    margin_grid: float,
    air_defense_radius_scale: float = 1.0,
    min_size: int = 180,
) -> tuple[int, int, int, int]:
    xs: list[float] = []
    ys: list[float] = []

    def add_grid(grid_x: Any, grid_y: Any, radius: float = 0.0) -> None:
        if grid_x is None or grid_y is None:
            return
        x, y = grid_to_map_px(safe_float(grid_x), safe_float(grid_y))
        xs.extend([x - radius, x + radius])
        ys.extend([y - radius, y + radius])

    for _, waypoints in flights:
        for waypoint in waypoints:
            add_grid(waypoint.get("grid_x"), waypoint.get("grid_y"))
    for point in [*ini_points, *ini_line_points]:
        grid = point.get("campaign_grid") or {}
        add_grid(grid.get("grid_x"), grid.get("grid_y"))
    for air_defense in air_defenses:
        radius = max(safe_float(air_defense.get("air_range")), safe_float(air_defense.get("low_air_range")))
        add_grid(air_defense.get("grid_x"), air_defense.get("grid_y"), radius * air_defense_radius_scale)
    for airbase in airbases:
        add_grid(airbase.get("grid_x"), airbase.get("grid_y"))

    if not xs or not ys:
        return 0, 0, MAP_GRID_SIZE, MAP_GRID_SIZE

    left = max(0, math.floor(min(xs) - margin_grid))
    top = max(0, math.floor(min(ys) - margin_grid))
    right = min(MAP_GRID_SIZE, math.ceil(max(xs) + margin_grid))
    bottom = min(MAP_GRID_SIZE, math.ceil(max(ys) + margin_grid))
    if right - left < min_size:
        pad = (min_size - (right - left)) / 2
        left = max(0, math.floor(left - pad))
        right = min(MAP_GRID_SIZE, math.ceil(right + pad))
    if bottom - top < min_size:
        pad = (min_size - (bottom - top)) / 2
        top = max(0, math.floor(top - pad))
        bottom = min(MAP_GRID_SIZE, math.ceil(bottom + pad))
    return left, top, right, bottom


def tactical_flights(
    flights: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    result: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for flight, waypoints in flights:
        tactical_indexes = [
            index
            for index, waypoint in enumerate(waypoints)
            if waypoint.get("action") in TARGET_AREA_ACTIONS
            or f"WP_{waypoint.get('action_short')}" in TARGET_AREA_ACTIONS
        ]
        if not tactical_indexes:
            continue
        start = max(0, min(tactical_indexes) - 1)
        end = min(len(waypoints), max(tactical_indexes) + 2)
        tactical_waypoints = []
        for index, waypoint in enumerate(waypoints[start:end], start):
            item = dict(waypoint)
            if index not in tactical_indexes:
                item["map_context"] = True
            tactical_waypoints.append(item)
        result.append((flight, tactical_waypoints))
    return result


def normalized_label(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().upper())


def expand_alpha_label_range(label: str) -> list[str]:
    match = re.fullmatch(r"([A-Z])-([A-Z])", label)
    if not match:
        return [label]
    start = ord(match.group(1))
    end = ord(match.group(2))
    if start > end or end - start > 12:
        return [label]
    return [chr(value) for value in range(start, end + 1)]


def objective_area_labels(package: dict[str, Any]) -> set[str]:
    labels = set(OBJECTIVE_AREA_BASE_LABELS)
    context = package.get("human_context") or {}
    for opportunity in context.get("target_opportunities", []):
        for key in ("label", "name"):
            label = normalized_label(opportunity.get(key))
            if not label:
                continue
            labels.update(expand_alpha_label_range(label))
    for contract in context.get("cap_contracts", []):
        for key in ("label", "area", "contract"):
            label = normalized_label(contract.get(key))
            if not label:
                continue
            labels.add(label)
            if label.startswith("CAP "):
                labels.add(label[4:].strip())
    return labels


def objective_ini_points(ini_points: list[dict[str, Any]], package: dict[str, Any]) -> list[dict[str, Any]]:
    wanted = objective_area_labels(package)
    selected = [
        point
        for point in ini_points
        if normalized_label(point.get("label") or point.get("display")) in wanted
    ]
    return selected or ini_points


def projected_ini_locations(
    projector: Projector,
    ini_points: list[dict[str, Any]],
) -> dict[str, tuple[float, float]]:
    named_locations: dict[str, tuple[float, float]] = {}
    for point in ini_points:
        grid = point.get("campaign_grid") or {}
        label = str(point.get("label") or point.get("display") or "").strip()
        if not label:
            continue
        named_locations[label.upper()] = projector.grid(grid.get("grid_x"), grid.get("grid_y"))
    return named_locations


def draw_text_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] = TEXT,
    bg: tuple[int, int, int, int] = (7, 12, 14, 210),
    pad: int = 3,
    anchor: str = "la",
) -> tuple[int, int, int, int]:
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font, anchor=anchor)
    box = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
    draw.rounded_rectangle(box, radius=3, fill=color_alpha(bg, bg[3] if len(bg) > 3 else 255, LABEL_OPACITY))
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)
    return box


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    fill: tuple[int, int, int, int] | tuple[int, int, int],
    width: int,
    dash: int = 14,
    gap: int = 8,
) -> None:
    for start, end in zip(points, points[1:]):
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        distance = math.hypot(dx, dy)
        if distance <= 0:
            continue
        ux = dx / distance
        uy = dy / distance
        cursor = 0.0
        while cursor < distance:
            segment_end = min(distance, cursor + dash)
            draw.line(
                [
                    (x1 + ux * cursor, y1 + uy * cursor),
                    (x1 + ux * segment_end, y1 + uy * segment_end),
                ],
                fill=fill,
                width=width,
            )
            cursor += dash + gap


def draw_arrowhead(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    fill: tuple[int, int, int],
    size: int = 12,
) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux = dx / length
    uy = dy / length
    left = (-uy, ux)
    right = (uy, -ux)
    tip = end
    base = (end[0] - ux * size, end[1] - uy * size)
    draw.polygon(
        [
            tip,
            (base[0] + left[0] * size * 0.45, base[1] + left[1] * size * 0.45),
            (base[0] + right[0] * size * 0.45, base[1] + right[1] * size * 0.45),
        ],
        fill=fill,
    )


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def air_defense_threat_label(air_defense: dict[str, Any]) -> str:
    equipment = str(air_defense.get("equipment") or "").strip()
    class_name = str(air_defense.get("class_name") or "ADA").strip()
    if equipment:
        candidates = [part.strip() for part in equipment.split(";") if part.strip()]
        for candidate in candidates:
            if candidate.lower() in {"uaz-469", "zil-131", "hmmwv s", "kraz t 255b", "bmp-3"}:
                continue
            label = re.sub(r"\s*\([^)]*\)", "", candidate).strip()
            if label.lower() == "ksam chun-ma":
                label = "Chun-ma"
            if label:
                return label[:18]
    if class_name.lower() == "air defense":
        return "SAM"
    return class_name[:18] if class_name else "ADA"


def is_strategic_air_defense(air_defense: dict[str, Any]) -> bool:
    class_name = str(air_defense.get("class_name") or "").lower()
    radius_grid = max(safe_float(air_defense.get("air_range")), safe_float(air_defense.get("low_air_range")))
    return class_name == "air defense" or radius_grid >= 15


def has_active_tracking_radar(air_defense: dict[str, Any]) -> bool:
    radar = air_defense.get("tracking_radar")
    if isinstance(radar, dict):
        return bool(radar.get("active"))
    if "active_tracking_radar" in air_defense:
        return bool(air_defense.get("active_tracking_radar"))
    return True


def is_operational_airbase(airbase: dict[str, Any]) -> bool:
    percent = airbase.get("operational_percent")
    if percent is None:
        return True
    return safe_float(percent) > 0


class Projector:
    def __init__(self, crop: tuple[int, int, int, int], scale: int):
        self.left, self.top, _, _ = crop
        self.scale = scale

    def grid(self, grid_x: Any, grid_y: Any) -> tuple[float, float]:
        x, y = grid_to_map_px(safe_float(grid_x), safe_float(grid_y))
        return (x - self.left) * self.scale, (y - self.top) * self.scale

    def radius(self, grid_radius: float) -> float:
        return grid_radius * self.scale


def draw_air_defenses(
    overlay: Image.Image,
    projector: Projector,
    air_defenses: list[dict[str, Any]],
    font: ImageFont.ImageFont,
    draw_rings: bool = True,
    draw_labels: bool = True,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    for air_defense in sorted(
        air_defenses,
        key=lambda item: max(safe_float(item.get("air_range")), safe_float(item.get("low_air_range"))),
        reverse=True,
    ):
        center = projector.grid(air_defense.get("grid_x"), air_defense.get("grid_y"))
        radius_grid = max(safe_float(air_defense.get("air_range")), safe_float(air_defense.get("low_air_range")))
        is_long = radius_grid >= 15
        if draw_rings and radius_grid > 0:
            radius = projector.radius(radius_grid)
            box = (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)
            ring_width = 5 if is_long else 4
            draw.ellipse(box, fill=threat_color(AD_OUTLINE, 14 if is_long else 10))
            draw.ellipse(box, outline=threat_color(AD_OUTER_WEZ, 255), width=ring_width + 1)
            dot_radius = 4 if is_long else 3
            draw.ellipse(
                (
                    center[0] - dot_radius,
                    center[1] - dot_radius,
                    center[0] + dot_radius,
                    center[1] + dot_radius,
                ),
                fill=threat_color(AD_OUTLINE, 235),
                outline=threat_color((255, 238, 210), 190),
            )
        if draw_labels:
            label = air_defense_threat_label(air_defense)
            bbox = draw.textbbox(center, label, font=font, anchor="mm")
            if 0 <= bbox[0] and bbox[2] <= overlay.width and 0 <= bbox[1] and bbox[3] <= overlay.height:
                draw_text_box(draw, center, label, font, fill=AD_LABEL_TEXT, bg=AD_LABEL_BG, pad=2, anchor="mm")


def draw_airbases(
    overlay: Image.Image,
    projector: Projector,
    airbases: list[dict[str, Any]],
    font: ImageFont.ImageFont,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    for index, airbase in enumerate(airbases[:8]):
        center = projector.grid(airbase.get("grid_x"), airbase.get("grid_y"))
        size = 7
        draw.rectangle(
            (center[0] - size - 2, center[1] - size - 2, center[0] + size + 2, center[1] + size + 2),
            fill=marker_color((0, 0, 0), 145),
        )
        draw.rectangle(
            (center[0] - size, center[1] - size, center[0] + size, center[1] + size),
            fill=marker_color(AIRBASE_FILL, 235),
            outline=marker_color(AIRBASE_OUTLINE, 235),
            width=2,
        )
        draw.line((center[0] - size + 3, center[1], center[0] + size - 3, center[1]), fill=marker_color((50, 0, 0), 210), width=2)
        if index < 8:
            name = str(airbase.get("name") or "Enemy AB")
            short_name = name.replace(" Airbase", " AB").replace("Highwaystrip", " Hwy")
            aircraft = str(airbase.get("aircraft_summary") or "").strip()
            label = f"{short_name}: {aircraft}" if aircraft else short_name
            if len(label) > 44:
                label = label[:41] + "..."
            draw_text_box(draw, (center[0] + 11, center[1] + 2), label, font, fill=(255, 215, 215))


def draw_ini_geometry(
    overlay: Image.Image,
    projector: Projector,
    ini_points: list[dict[str, Any]],
    ini_line_points: list[dict[str, Any]],
    font: ImageFont.ImageFont,
) -> dict[str, tuple[float, float]]:
    draw = ImageDraw.Draw(overlay, "RGBA")
    named_locations: dict[str, tuple[float, float]] = {}
    line_xy = [
        projector.grid((point.get("campaign_grid") or {}).get("grid_x"), (point.get("campaign_grid") or {}).get("grid_y"))
        for point in ini_line_points
    ]
    if len(line_xy) >= 2:
        draw.line(line_xy, fill=route_color(INI_LINE_HALO, 220), width=7)
        draw.line(line_xy, fill=route_color(INI_LINE, 235), width=4)
        for xy in line_xy:
            radius = 4
            draw.ellipse(
                (xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius),
                fill=marker_color((245, 245, 245), 230),
                outline=marker_color(INI_LINE, 235),
                width=2,
            )
        leftmost = min(line_xy, key=lambda point: point[0])
        draw_text_box(
            draw,
            (leftmost[0] - 12, leftmost[1] - 16),
            "Route Black",
            font,
            fill=(255, 255, 255),
            anchor="ra",
        )

    offsets = [
        (9, -9),
        (9, 14),
        (-9, -9),
        (-9, 14),
        (15, 2),
        (-15, 2),
    ]
    for idx, point in enumerate(ini_points):
        grid = point.get("campaign_grid") or {}
        xy = projector.grid(grid.get("grid_x"), grid.get("grid_y"))
        label = str(point.get("label") or point.get("display") or "PPT")
        named_locations[label.upper()] = xy
        radius = 6
        diamond = [
            (xy[0], xy[1] - radius),
            (xy[0] + radius, xy[1]),
            (xy[0], xy[1] + radius),
            (xy[0] - radius, xy[1]),
        ]
        draw.polygon(diamond, fill=marker_color(PPT_FILL, 235))
        draw.line(
            [*diamond, diamond[0]],
            fill=marker_color(PPT_OUTLINE, 240),
            width=2,
        )
        dx, dy = offsets[idx % len(offsets)]
        anchor = "la" if dx >= 0 else "ra"
        draw_text_box(draw, (xy[0] + dx, xy[1] + dy), label, font, fill=(255, 255, 255), anchor=anchor)
    return named_locations


def route_from_contract(contract_text: str) -> list[str]:
    match = re.search(r"\b([A-Z]{1,4}(?:-[A-Z]{1,4})+)\b", contract_text.upper())
    if not match:
        return []
    return [part for part in match.group(1).split("-") if part]


def draw_assignment_lanes(
    overlay: Image.Image,
    package: dict[str, Any],
    named_locations: dict[str, tuple[float, float]],
    flight_colors: dict[str, tuple[int, int, int]],
    small_font: ImageFont.ImageFont,
) -> None:
    context = package.get("human_context") or {}
    draw = ImageDraw.Draw(overlay, "RGBA")
    for contract in context.get("sad_contracts", []):
        callsign = str(contract.get("callsign") or "")
        route = route_from_contract(str(contract.get("contract") or ""))
        points = [named_locations[label] for label in route if label in named_locations]
        if len(points) < 2:
            continue
        color = flight_colors.get(callsign, (245, 245, 245))
        draw_dashed_line(draw, points, route_color(color, 205), width=3, dash=9, gap=7)
        draw_arrowhead(draw, points[-2], points[-1], route_color(color, 230), size=12)

    for contract in context.get("cap_contracts", []):
        callsign = str(contract.get("callsign") or "")
        label = str(contract.get("label") or "").upper()
        if label not in named_locations:
            continue
        color = flight_colors.get(callsign, (245, 245, 245))
        center = named_locations[label]
        radius = 16
        draw.ellipse(
            (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
            outline=route_color(color, 190),
            width=3,
        )


def short_action_label(action: str) -> str:
    return {
        "TIMING": "T",
        "PUSH": "P",
        "SPLIT": "SPL",
        "CAP": "CAP",
        "SAD": "SAD",
        "STRIKE": "STK",
        "BOMB": "BMB",
        "SEAD": "SEAD",
    }.get(action, action[:4])


def draw_flights(
    overlay: Image.Image,
    projector: Projector,
    flights: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    flight_colors: dict[str, tuple[int, int, int]],
    label_font: ImageFont.ImageFont,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    label_actions = {"TIMING", "PUSH", "SAD", "CAP", "SPLIT", "STRIKE", "BOMB", "SEAD"}
    label_offsets = [(8, 8), (8, -18), (-8, 8), (-8, -18), (14, -4), (-14, -4)]
    for flight_index, (flight, waypoints) in enumerate(flights):
        callsign = str(flight.get("callsign") or "")
        color = flight_colors[callsign]
        label_dx, label_dy = label_offsets[flight_index % len(label_offsets)]
        points = [projector.grid(wp.get("grid_x"), wp.get("grid_y")) for wp in waypoints]
        if len(points) >= 2:
            draw.line(points, fill=route_color((0, 0, 0), 185), width=8, joint="curve")
            draw.line(points, fill=route_color(color, 230), width=4, joint="curve")
            draw_arrowhead(draw, points[-2], points[-1], route_color(color, 240), size=13)
        for waypoint, xy in zip(waypoints, points):
            action = str(waypoint.get("action_short") or action_label(waypoint.get("action")))
            radius = 4 if action != "NOTHING" else 2
            draw.ellipse(
                (xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius),
                fill=marker_color(color, 235),
                outline=marker_color((8, 10, 10), 220),
                width=1,
            )
            if action in label_actions or waypoint.get("map_context"):
                label = (
                    str(waypoint.get("index"))
                    if waypoint.get("map_context")
                    else f"{waypoint.get('index')} {short_action_label(action)}"
                )
                anchor = "la" if label_dx >= 0 else "ra"
                draw_text_box(draw, (xy[0] + label_dx, xy[1] + label_dy), label, label_font, fill=color, anchor=anchor)


def draw_support_flights(
    overlay: Image.Image,
    projector: Projector,
    support_flights: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    label_font: ImageFont.ImageFont,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    for index, (flight, waypoints) in enumerate(support_flights):
        role = str(flight.get("role") or flight.get("mission") or "SUPPORT").upper()
        color = SUPPORT_COLORS.get(role, (220, 220, 220))
        points = [projector.grid(wp.get("grid_x"), wp.get("grid_y")) for wp in waypoints]
        if len(points) >= 2:
            draw_dashed_line(draw, points, route_color((0, 0, 0), 165), width=8, dash=12, gap=7)
            draw_dashed_line(draw, points, route_color(color, 230), width=4, dash=12, gap=7)
            draw_arrowhead(draw, points[-2], points[-1], route_color(color, 240), size=12)
        for waypoint, xy in zip(waypoints, points):
            action = str(waypoint.get("action_short") or action_label(waypoint.get("action")))
            radius = 4
            draw.rectangle(
                (xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius),
                fill=marker_color(color, 235),
                outline=marker_color((8, 10, 10), 220),
                width=1,
            )
            if action in {"TANKER", "ELINT", "AWACS", "JAM", "CAP"} or waypoint.get("map_context"):
                label = str(waypoint.get("index")) if waypoint.get("map_context") else f"{role} {waypoint.get('index')}"
                dx = 10 if index % 2 == 0 else -10
                anchor = "la" if dx >= 0 else "ra"
                draw_text_box(draw, (xy[0] + dx, xy[1] - 10), label, label_font, fill=color, anchor=anchor)


def draw_scale_and_north(
    overlay: Image.Image,
    crop: tuple[int, int, int, int],
    scale: int,
    font: ImageFont.ImageFont,
) -> None:
    draw = ImageDraw.Draw(overlay, "RGBA")
    width, height = overlay.size
    scale_nm = 25 if (crop[2] - crop[0]) < 260 else 50
    scale_grid = nm_to_grid(scale_nm) * scale
    x1 = 28
    y = height - 32
    draw.line((x1, y, x1 + scale_grid, y), fill=(244, 246, 235, 220), width=4)
    draw.line((x1, y - 6, x1, y + 6), fill=(244, 246, 235, 220), width=2)
    draw.line((x1 + scale_grid, y - 6, x1 + scale_grid, y + 6), fill=(244, 246, 235, 220), width=2)
    draw.text((x1, y - 26), f"{scale_nm} NM", font=font, fill=TEXT)

    nx = width - 38
    ny = 34
    draw.polygon([(nx, ny - 22), (nx - 8, ny + 8), (nx + 8, ny + 8)], fill=(244, 246, 235, 225))
    draw.text((nx, ny + 12), "N", font=font, fill=TEXT, anchor="mm")


def draw_footer(
    image: Image.Image,
    package: dict[str, Any],
    flights: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    support_flights: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    flight_colors: dict[str, tuple[int, int, int]],
    crop: tuple[int, int, int, int],
    map_source: Path,
    source_scale: tuple[float, float],
    crop_mode: str,
    footer_height: int,
    show_airbases: bool,
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = load_font(22, bold=True)
    text_font = load_font(14)
    small_font = load_font(12)
    y0 = image.height - footer_height
    draw.rectangle((0, y0, image.width, image.height), fill=PANEL)
    title_suffix = {
        "package": "Route / Threat Map",
        "target-area": "Target Area Zoom",
        "objective-area": "Objective Area Zoom",
    }.get(crop_mode, "Route / Threat Map")
    draw.text((18, y0 + 14), f"Package {package.get('package_id')} {title_suffix}", font=title_font, fill=TEXT)
    route_name = (package.get("human_context") or {}).get("route_name") or "INI route"
    scale_x, scale_y = source_scale
    if abs(scale_x - scale_y) < 0.001:
        scale_note = f"{scale_x:g} px/grid"
    else:
        scale_note = f"{scale_x:g}x{scale_y:g} px/grid"
    threat_note = "radar-active strategic ADA + operational enemy airbases" if show_airbases else "radar-active strategic ADA rings"
    subtitle = f"Base: {map_source.name} | source {scale_note} | crop cols {crop[0]}-{crop[2]}, rows {crop[1]}-{crop[3]}"
    threat_line = f"Transform: x=grid_x, y=1024-grid_y | enemy-only overlays: {threat_note}"
    draw.text((18, y0 + 43), subtitle, font=small_font, fill=MUTED)
    draw.text((18, y0 + 65), threat_line, font=small_font, fill=MUTED)
    draw.text((18, y0 + 87), f"{route_name}: black INI line; named INI PPTs are green diamonds.", font=small_font, fill=MUTED)

    x = 18
    y = y0 + 136
    draw.text((x, y - 21), "Flight plans", font=small_font, fill=MUTED)
    for flight_index, (flight, _) in enumerate(flights):
        callsign = str(flight.get("callsign") or "")
        color = flight_colors[callsign]
        draw.line((x, y + 8, x + 26, y + 8), fill=(*color, 255), width=4)
        label = f"{callsign} {flight.get('mission')}"
        contract = flight.get("contract_summary") or ""
        if contract:
            label = f"{label} - {contract.split(':', 1)[0]}"
        draw.text((x + 34, y), label, font=text_font, fill=TEXT)
        y += 23
        if flight_index < len(flights) - 1 and y > image.height - 10:
            y = y0 + 136
            x += min(420, max(310, image.width // 2))

    legend_x = max(image.width - 330, 18 + min(420, max(310, image.width // 2)))
    legend_y = y0 + 136
    draw.text((legend_x, legend_y - 21), "Map overlays", font=small_font, fill=MUTED)
    legend_items = [
        (INI_LINE, "Route Black"),
        (PPT_FILL, "Named INI PPT"),
        (AD_OUTER_WEZ, "ADA WEZ"),
    ]
    if show_airbases:
        legend_items.append((AIRBASE_FILL, "Enemy active AB"))
    if support_flights:
        legend_items.append(((245, 245, 245), "Support track"))
    for color, label in legend_items:
        swatch = (legend_x, legend_y + 3, legend_x + 16, legend_y + 17)
        draw.rectangle(swatch, fill=color)
        if color == INI_LINE:
            draw.rectangle(swatch, outline=(235, 235, 235))
        draw.text((legend_x + 24, legend_y), label, font=text_font, fill=TEXT)
        legend_y += 23

    if support_flights:
        support_x = legend_x
        support_y = legend_y + 8
        draw.text((support_x, support_y), "Support", font=small_font, fill=MUTED)
        support_y += 18
        for support, _ in support_flights[:4]:
            role = str(support.get("role") or support.get("mission") or "SUPPORT").upper()
            color = SUPPORT_COLORS.get(role, (220, 220, 220))
            draw_dashed_line(draw, [(support_x, support_y + 8), (support_x + 26, support_y + 8)], (*color, 240), width=3, dash=7, gap=4)
            draw.text((support_x + 34, support_y), f"{role} {support.get('callsign')}", font=text_font, fill=TEXT)
            support_y += 22


def render_map(args: argparse.Namespace) -> Path:
    synthesis = load_json(args.synthesis)
    package = find_package(synthesis, args.package_id)
    cam_decode = load_json(args.cam_decode) if args.cam_decode else None
    raw_flights = package_raw_flights(cam_decode, package)
    all_raw_flights = raw_flights_by_callsign(cam_decode)

    flights: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for flight in package.get("flights", []):
        waypoints = flight_waypoints(flight, raw_flights)
        if waypoints:
            flights.append((flight, waypoints))

    support_flights: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    if args.crop_mode == "package":
        for support in package.get("support_flights", []):
            waypoints = support_waypoints(support, all_raw_flights)
            if waypoints:
                support_flights.append((support, waypoints))

    ini_points = iter_named_ini_points(synthesis, package)
    ini_line_points = iter_ini_line_points(package)
    enemy = package.get("enemy_situation") or {}
    air_defenses = [
        item
        for item in enemy.get("air_defense_locations", [])
        if item.get("grid_x") is not None and item.get("grid_y") is not None
    ]
    strategic_air_defenses = [
        item
        for item in air_defenses
        if is_strategic_air_defense(item) and has_active_tracking_radar(item)
    ]
    airbases = [
        item
        for item in enemy.get("airbase_locations", [])
        if item.get("grid_x") is not None and item.get("grid_y") is not None and is_operational_airbase(item)
    ]

    map_source = args.map_source or (args.campaign_dir / "Korea.tm")
    base, source_scale_x, source_scale_y, _ = open_base_map(map_source)
    tactical = tactical_flights(flights) or flights
    objective_points = objective_ini_points(ini_points, package) or ini_points
    crop_flights = tactical if args.crop_mode in {"target-area", "objective-area"} else flights
    if args.crop_mode == "objective-area":
        bounds_flights = []
        bounds_ini_points = objective_points
        bounds_ini_line_points = ini_line_points
        bounds_air_defenses: list[dict[str, Any]] = []
        bounds_air_defense_radius_scale = 0.0
        bounds_min_size = 88
        crop_airbases: list[dict[str, Any]] = []
    elif args.crop_mode == "target-area":
        bounds_flights = crop_flights
        bounds_ini_points = ini_points
        bounds_ini_line_points = ini_line_points
        bounds_air_defenses = strategic_air_defenses
        bounds_air_defense_radius_scale = 0.0
        bounds_min_size = 150
        crop_airbases = []
    else:
        bounds_flights = [*crop_flights, *support_flights]
        bounds_ini_points = ini_points
        bounds_ini_line_points = ini_line_points
        bounds_air_defenses = strategic_air_defenses
        bounds_air_defense_radius_scale = 0.15
        bounds_min_size = 180
        crop_airbases = airbases if args.show_airbases else []
    crop = collect_map_bounds(
        bounds_flights,
        bounds_ini_points,
        bounds_ini_line_points,
        bounds_air_defenses,
        crop_airbases,
        args.margin_grid,
        bounds_air_defense_radius_scale,
        bounds_min_size,
    )
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

    overlay = Image.new("RGBA", (map_width, map_height), (0, 0, 0, 0))
    projector = Projector(crop, scale)
    small_font = load_font(max(9, min(18, int(8 * scale / 4))))
    label_font = load_font(max(10, min(22, int(9 * scale / 4))), bold=True)

    flight_colors = {
        str(flight.get("callsign") or ""): FLIGHT_COLORS[index % len(FLIGHT_COLORS)]
        for index, (flight, _) in enumerate(flights)
    }

    draw_air_defenses(overlay, projector, strategic_air_defenses, small_font, draw_labels=False)
    draw_airbases_on_this_map = args.show_airbases and args.crop_mode == "package"
    if draw_airbases_on_this_map:
        draw_airbases(overlay, projector, airbases, small_font)
    draw_ini_points = objective_points if args.crop_mode == "objective-area" else ini_points
    if support_flights:
        draw_support_flights(overlay, projector, support_flights, small_font)
    draw_flights(overlay, projector, crop_flights, flight_colors, small_font)
    named_locations = projected_ini_locations(projector, draw_ini_points)
    draw_assignment_lanes(overlay, package, named_locations, flight_colors, small_font)
    draw_ini_geometry(overlay, projector, draw_ini_points, ini_line_points, label_font)
    draw_air_defenses(overlay, projector, strategic_air_defenses, small_font, draw_rings=False)
    draw_scale_and_north(overlay, crop, scale, label_font)

    footer_height = 245
    output = Image.new("RGBA", (map_width, map_height + footer_height), (9, 13, 15, 255))
    output.alpha_composite(map_image, (0, 0))
    output.alpha_composite(overlay, (0, 0))
    draw_footer(
        output,
        package,
        flights,
        support_flights,
        flight_colors,
        crop,
        map_source,
        (source_scale_x, source_scale_y),
        args.crop_mode,
        footer_height,
        draw_airbases_on_this_map,
    )
    output.convert("RGB").save(args.out)
    return args.out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, required=True, help="Path to briefing_synthesis.json.")
    parser.add_argument("--cam-decode", type=Path, help="Optional cam_decode.json for full flight waypoint chains.")
    parser.add_argument("--campaign-dir", type=Path, required=True, help="BMS campaign directory containing Korea.tm.")
    parser.add_argument("--package-id", type=int, required=True, help="Campaign package id to render.")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG path.")
    parser.add_argument("--map-source", type=Path, help="Override map raster path. Supports Korea.tm or a full-theater image such as 8_KTO_16k_Skyvector.png.")
    parser.add_argument("--margin-grid", type=float, default=34.0, help="Extra grid-cell margin around plotted content.")
    parser.add_argument(
        "--feet-per-grid",
        type=float,
        default=None,
        help="Override grid distance scale for NM rings/scale bars. Default is BMS 4.38 real-life feet: 3280.84 ft/grid.",
    )
    parser.add_argument(
        "--route-opacity",
        type=float,
        default=ROUTE_OPACITY,
        help="Opacity for flight routes, support tracks, INI lines, and assignment lanes. Range 0.0-1.0.",
    )
    parser.add_argument(
        "--marker-opacity",
        type=float,
        default=MARKER_OPACITY,
        help="Opacity for waypoint dots, INI diamonds, and airbase markers. Range 0.0-1.0.",
    )
    parser.add_argument(
        "--label-opacity",
        type=float,
        default=LABEL_OPACITY,
        help="Opacity for label background boxes. Label text remains fully readable. Range 0.0-1.0.",
    )
    parser.add_argument(
        "--threat-opacity",
        type=float,
        default=THREAT_OPACITY,
        help="Opacity for air-defense WEZ rings and ADA markers. Range 0.0-1.0.",
    )
    parser.add_argument(
        "--crop-mode",
        choices=("package", "target-area", "objective-area"),
        default="package",
        help="Use package for the full route, target-area for tactical waypoints, or objective-area for INI target geometry.",
    )
    parser.add_argument("--scale", type=int, default=4, help="Output scale multiplier for the cropped map.")
    parser.add_argument(
        "--show-airbases",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show active, non-destroyed enemy squadron airbases from the synthesis threat estimate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    global FEET_PER_GRID, ROUTE_OPACITY, MARKER_OPACITY, LABEL_OPACITY, THREAT_OPACITY
    if args.feet_per_grid is not None:
        FEET_PER_GRID = args.feet_per_grid
    ROUTE_OPACITY = clamp_opacity(args.route_opacity, ROUTE_OPACITY)
    MARKER_OPACITY = clamp_opacity(args.marker_opacity, MARKER_OPACITY)
    LABEL_OPACITY = clamp_opacity(args.label_opacity, LABEL_OPACITY)
    THREAT_OPACITY = clamp_opacity(args.threat_opacity, THREAT_OPACITY)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out = render_map(args)
    print(out)


if __name__ == "__main__":
    main()
