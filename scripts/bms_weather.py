#!/usr/bin/env python3
"""Falcon BMS FMAP weather parsing and sampling helpers."""

from __future__ import annotations

import math
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any, Sequence


MAP_GRID_SIZE = 1024.0
NUM_ALOFT_BREAKPOINTS = 10
ALOFT_BREAKPOINTS_FT = [0, 3000, 6000, 9000, 12000, 18000, 24000, 30000, 40000, 50000]
HEADER_FORMAT = "<IIIifii4i"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

WEATHER_LABELS = {
    0: "Sunny",
    1: "Sunny",
    2: "Fair",
    3: "Poor",
    4: "Inclement",
}


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


def clamp_index(value: int, upper: int) -> int:
    return max(0, min(upper - 1, value))


def grid_to_weather_cell(grid_x: float, grid_y: float, size_x: int, size_y: int) -> tuple[int, int]:
    """Convert BMS campaign grid to FMAP row/column.

    FMAP row 0 is the northern edge, matching the F4Wx preview window. BMS
    campaign grid Y increases northward, so it is inverted into north-up row
    space here.
    """
    col = math.floor((safe_float(grid_x) / MAP_GRID_SIZE) * size_x)
    row = math.floor(((MAP_GRID_SIZE - safe_float(grid_y)) / MAP_GRID_SIZE) * size_y)
    return clamp_index(row, size_y), clamp_index(col, size_x)


def weather_label(code: int) -> str:
    return WEATHER_LABELS.get(safe_int(code), f"Type {code}")


def contrail_layer_for_condition(layers: Sequence[int], condition: int) -> int | None:
    if not layers:
        return None
    index = max(0, safe_int(condition) - 1)
    if index >= len(layers):
        index = len(layers) - 1
    return safe_int(layers[index])


def cloud_cover_label(condition: int, density: int, size: float, tower: int, shower: int) -> str:
    if safe_int(condition) <= 1:
        return "CLR"
    density_mod = safe_float(density) * (1.0 + (5.0 - safe_float(size)) / 5.0)
    if density_mod < 6:
        base = "FEW"
    elif density_mod < 14:
        base = "SCT"
    elif density_mod < 24:
        base = "BKN"
    else:
        base = "OVC"
    if safe_int(shower):
        return f"{base} CB"
    if safe_int(tower):
        return f"{base} TCU"
    return base


def time_of_day_label(hhmm: str | None) -> str | None:
    if not hhmm or len(hhmm) < 4 or not hhmm[:4].isdigit():
        return None
    hour = int(hhmm[:2])
    minute = int(hhmm[2:4])
    minutes = hour * 60 + minute
    if 6 * 60 <= minutes < 18 * 60:
        return "Day"
    if 5 * 60 <= minutes < 6 * 60 or 18 * 60 <= minutes < 19 * 60:
        return "Twilight"
    return "Night"


def format_wind(direction_deg: float, speed_kt: float) -> str:
    direction = round(safe_float(direction_deg)) % 360
    speed = round(safe_float(speed_kt))
    return f"{direction:03d}/{speed} kt"


@dataclass
class FMap:
    version: int
    size_y: int
    size_x: int
    map_wind_heading: int
    map_wind_speed: float
    map_stratus_z_fair: int
    map_stratus_z_inc: int
    map_contrail_layer: list[int]
    basic_condition: list[int]
    pressure: list[float]
    temperature: list[float]
    wind_speed: list[float]
    wind_dir: list[float]
    cumulus_base: list[float]
    cumulus_density: list[int]
    cumulus_size: list[float]
    has_tower_cumulus: list[int]
    has_shower_cumulus: list[int]
    visibility: list[float]
    fog_layer_z: list[float] | None

    @property
    def cell_count(self) -> int:
        return self.size_y * self.size_x

    @property
    def has_fog_layer_z(self) -> bool:
        return self.fog_layer_z is not None

    @classmethod
    def from_bytes(cls, data: bytes) -> "FMap":
        if len(data) < HEADER_SIZE:
            raise ValueError(f"FMAP file is too small: {len(data)} bytes")

        (
            version,
            size_y,
            size_x,
            map_wind_heading,
            map_wind_speed,
            map_stratus_z_fair,
            map_stratus_z_inc,
            *map_contrail_layer,
        ) = struct.unpack_from(HEADER_FORMAT, data, 0)

        cell_count = size_y * size_x
        remaining = len(data) - HEADER_SIZE
        bytes_per_cell_v7 = 29 * 4
        bytes_per_cell_v8 = 30 * 4
        if remaining == cell_count * bytes_per_cell_v8:
            has_fog_layer_z = True
        elif remaining == cell_count * bytes_per_cell_v7:
            has_fog_layer_z = False
        else:
            raise ValueError(
                "Unsupported FMAP layout: "
                f"version={version}, cells={cell_count}, remaining={remaining} bytes"
            )

        offset = HEADER_SIZE

        def read(fmt: str, count: int) -> list[int] | list[float]:
            nonlocal offset
            size = struct.calcsize(fmt) * count
            values = list(struct.unpack_from(f"<{count}{fmt}", data, offset))
            offset += size
            return values

        basic_condition = read("i", cell_count)
        pressure = read("f", cell_count)
        temperature = read("f", cell_count)
        wind_speed = read("f", cell_count * NUM_ALOFT_BREAKPOINTS)
        wind_dir = read("f", cell_count * NUM_ALOFT_BREAKPOINTS)
        cumulus_base = read("f", cell_count)
        cumulus_density = read("i", cell_count)
        cumulus_size = read("f", cell_count)
        has_tower_cumulus = read("i", cell_count)
        has_shower_cumulus = read("i", cell_count)
        visibility = read("f", cell_count)
        fog_layer_z = read("f", cell_count) if has_fog_layer_z else None

        if offset != len(data):
            raise ValueError(f"FMAP parse did not consume the full file: {offset} != {len(data)}")

        return cls(
            version=version,
            size_y=size_y,
            size_x=size_x,
            map_wind_heading=map_wind_heading,
            map_wind_speed=map_wind_speed,
            map_stratus_z_fair=map_stratus_z_fair,
            map_stratus_z_inc=map_stratus_z_inc,
            map_contrail_layer=map_contrail_layer,
            basic_condition=basic_condition,
            pressure=pressure,
            temperature=temperature,
            wind_speed=wind_speed,
            wind_dir=wind_dir,
            cumulus_base=cumulus_base,
            cumulus_density=cumulus_density,
            cumulus_size=cumulus_size,
            has_tower_cumulus=has_tower_cumulus,
            has_shower_cumulus=has_shower_cumulus,
            visibility=visibility,
            fog_layer_z=fog_layer_z,
        )

    @classmethod
    def from_path(cls, path: Path) -> "FMap":
        return cls.from_bytes(path.read_bytes())

    def cell_index(self, row: int, col: int) -> int:
        row = clamp_index(row, self.size_y)
        col = clamp_index(col, self.size_x)
        return row * self.size_x + col

    def sample_cell(self, row: int, col: int, level: int = 0) -> dict[str, Any]:
        idx = self.cell_index(row, col)
        level = clamp_index(level, NUM_ALOFT_BREAKPOINTS)
        wind_idx = idx * NUM_ALOFT_BREAKPOINTS + level
        condition = safe_int(self.basic_condition[idx])
        contrail_layer = contrail_layer_for_condition(self.map_contrail_layer, condition)
        return {
            "row": row,
            "col": col,
            "weather_code": condition,
            "condition": weather_label(condition),
            "pressure_hpa": round(safe_float(self.pressure[idx]), 1),
            "temperature_c": round(safe_float(self.temperature[idx]), 1),
            "wind_level_ft": ALOFT_BREAKPOINTS_FT[level],
            "wind_direction_deg": round(safe_float(self.wind_dir[wind_idx])),
            "wind_speed_kt": round(safe_float(self.wind_speed[wind_idx])),
            "wind": format_wind(self.wind_dir[wind_idx], self.wind_speed[wind_idx]),
            "visibility_km": round(safe_float(self.visibility[idx]), 1),
            "cumulus_base_ft": round(safe_float(self.cumulus_base[idx])),
            "cumulus_density": safe_int(self.cumulus_density[idx]),
            "cumulus_size": round(safe_float(self.cumulus_size[idx]), 1),
            "cloud_cover": cloud_cover_label(
                condition,
                safe_int(self.cumulus_density[idx]),
                safe_float(self.cumulus_size[idx]),
                safe_int(self.has_tower_cumulus[idx]),
                safe_int(self.has_shower_cumulus[idx]),
            ),
            "has_tower_cumulus": bool(self.has_tower_cumulus[idx]),
            "has_shower_cumulus": bool(self.has_shower_cumulus[idx]),
            "stratus_base_ft": self.map_stratus_z_fair if condition <= 2 else self.map_stratus_z_inc,
            "contrail_layer_ft": contrail_layer,
            "contrail_layer_fl": round(contrail_layer / 100) if contrail_layer else None,
            "fog_layer_ft": round(safe_float(self.fog_layer_z[idx])) if self.fog_layer_z is not None else None,
        }

    def sample_grid(self, grid_x: float, grid_y: float, level: int = 0) -> dict[str, Any]:
        row, col = grid_to_weather_cell(grid_x, grid_y, self.size_x, self.size_y)
        sample = self.sample_cell(row, col, level)
        sample["grid_x"] = round(safe_float(grid_x), 1)
        sample["grid_y"] = round(safe_float(grid_y), 1)
        return sample

    def summary(self) -> dict[str, Any]:
        counts = Counter(self.basic_condition)
        return {
            "version": self.version,
            "grid": {"rows": self.size_y, "cols": self.size_x, "cells": self.cell_count},
            "layout": "v8+" if self.has_fog_layer_z else "v7",
            "map_wind": format_wind(self.map_wind_heading, self.map_wind_speed),
            "map_wind_direction_deg": self.map_wind_heading,
            "map_wind_speed_kt": round(self.map_wind_speed),
            "stratus_base_fair_ft": self.map_stratus_z_fair,
            "stratus_base_inclement_ft": self.map_stratus_z_inc,
            "contrail_layers_ft": self.map_contrail_layer,
            "weather_counts": {weather_label(code): count for code, count in sorted(counts.items())},
            "visibility_km": {
                "min": round(min(self.visibility), 1),
                "max": round(max(self.visibility), 1),
                "mean": round(fmean(self.visibility), 1),
            },
            "temperature_c": {
                "min": round(min(self.temperature), 1),
                "max": round(max(self.temperature), 1),
                "mean": round(fmean(self.temperature), 1),
            },
            "cumulus_base_ft": {
                "min": round(min(self.cumulus_base)),
                "max": round(max(self.cumulus_base)),
                "mean": round(fmean(self.cumulus_base)),
            },
        }
