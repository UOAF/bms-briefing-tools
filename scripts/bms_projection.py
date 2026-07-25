#!/usr/bin/env python3
"""Falcon BMS theater coordinate helpers.

The campaign/INI coordinates are stored as BMS world feet. For KTO-style
1024 km theaters, one decoded campaign grid cell is one kilometer wide.
BMS 4.38 uses real-life/international feet for this conversion: 1000 m =
3280.839895 ft. BMS 4.37 used the older BMS-foot value, which gives about
3279.98 ft per kilometer grid cell.
Latitude/longitude conversion needs PROJ/pyproj and the theater projection
string from Theater.txt.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


REAL_WORLD_METERS_PER_FOOT = 0.3048
LEGACY_BMS_437_METERS_PER_FOOT = 0.3048799096
DEFAULT_METERS_PER_FOOT = REAL_WORLD_METERS_PER_FOOT
DEFAULT_THEATER_SIZE_KM = 1024.0
DEFAULT_CAMPAIGN_GRID_SIZE = 1024.0
DEFAULT_CENTER_LAT = 38.5
DEFAULT_CENTER_LON = 127.5
DEFAULT_PROJECTION_STRING = "+proj=tmerc +lon_0=127.5 +ellps=WGS84 +k=0.9996 +units=m +x_0=512000 +y_0=-3.74929e+06"


class ProjectionUnavailableError(RuntimeError):
    """Raised when pyproj is required but not installed."""


def feet_per_campaign_grid(
    theater_size_km: float = DEFAULT_THEATER_SIZE_KM,
    campaign_grid_size: float = DEFAULT_CAMPAIGN_GRID_SIZE,
    meters_per_foot: float = DEFAULT_METERS_PER_FOOT,
) -> float:
    return (theater_size_km * 1000.0 / meters_per_foot) / campaign_grid_size


def parse_theater_txt(path: Path) -> dict[str, Any]:
    """Parse the small coordinate subset we need from a BMS Theater.txt file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    config: dict[str, Any] = {"path": str(path)}
    patterns = {
        "name": r"Theater\s+name\s*=\s*(.+)",
        "theater_size_km": r"Theater\s+size\s+in\s+KM\s*=\s*([+-]?\d+(?:\.\d+)?)",
        "map_size_pixels": r"Map\s+size\s+in\s+pixels\s*=\s*(\d+)",
        "center_lat": r"Center\s+latitude\s*=\s*([+-]?\d+(?:\.\d+)?)",
        "center_lon": r"Center\s+longitude\s*=\s*([+-]?\d+(?:\.\d+)?)",
        "projection_string": r"Projection\s+string\s*=\s*(.+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        value = match.group(1).strip()
        if key in {"theater_size_km", "center_lat", "center_lon"}:
            config[key] = float(value)
        elif key == "map_size_pixels":
            config[key] = int(value)
        else:
            config[key] = value
    if "theater_size_km" not in config:
        config["theater_size_km"] = DEFAULT_THEATER_SIZE_KM
    if "projection_string" not in config:
        config["projection_string"] = DEFAULT_PROJECTION_STRING
    return config


def source_feet_to_campaign_grid(
    source_x_ft: float,
    source_y_ft: float,
    feet_per_grid: float | None = None,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> tuple[float, float]:
    """Convert BMS world feet into decoded campaign grid coordinates.

    INI and objective source feet use x/y names opposite our map axes:
    source Y is east/west grid X, and source X is north/south grid Y.
    """
    scale = feet_per_grid if feet_per_grid is not None else feet_per_campaign_grid()
    return (source_y_ft / scale) + offset_x, (source_x_ft / scale) + offset_y


def campaign_grid_to_source_feet(
    grid_x: float,
    grid_y: float,
    feet_per_grid: float | None = None,
) -> tuple[float, float]:
    scale = feet_per_grid if feet_per_grid is not None else feet_per_campaign_grid()
    return grid_y * scale, grid_x * scale


def game_feet_to_latlon(
    source_x_ft: float,
    source_y_ft: float,
    projection_string: str = DEFAULT_PROJECTION_STRING,
    meters_per_foot: float = DEFAULT_METERS_PER_FOOT,
) -> tuple[float, float]:
    try:
        from pyproj import Proj
    except ImportError as exc:
        raise ProjectionUnavailableError("Install pyproj to emit latitude/longitude coordinates.") from exc

    proj = Proj(projection_string)
    lon, lat = proj(source_x_ft * meters_per_foot, source_y_ft * meters_per_foot, inverse=True)
    return float(lat), float(lon)


def campaign_grid_to_latlon(
    grid_x: float,
    grid_y: float,
    projection_string: str = DEFAULT_PROJECTION_STRING,
    feet_per_grid: float | None = None,
    meters_per_foot: float = DEFAULT_METERS_PER_FOOT,
) -> tuple[float, float]:
    source_x_ft, source_y_ft = campaign_grid_to_source_feet(grid_x, grid_y, feet_per_grid)
    return game_feet_to_latlon(source_x_ft, source_y_ft, projection_string, meters_per_foot)
