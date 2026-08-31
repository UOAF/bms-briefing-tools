#!/usr/bin/env python3
"""Shared normalized MIL-STD-2525 unit glyph definitions for BMS maps.

Renderers own affiliation frames and scaling.  This module owns the interior
unit glyph so 2D and 3D products cannot silently drift into different or
malformed symbols.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GlyphPrimitive:
    kind: str
    values: tuple[float, ...]


def canonical_unit_kind(class_name: str) -> str:
    value = " ".join(str(class_name or "").upper().replace("_", " ").split())
    if value in {"MECH", "MECHANIZED", "MECHANIZED INFANTRY", "MOTOR RIFLE"}:
        return "mechanized"
    if value in {"INFANTRY", "INF"}:
        return "infantry"
    if value in {"TANK", "ARMORED", "ARMOR"}:
        return "armor"
    if value in {"TOWED GUN", "TOWED ARTILLERY", "SP GUNS", "SP ARTILLERY", "ARTILLERY"}:
        return "artillery"
    if value in {"ROCKET", "ROCKET ARTILLERY"}:
        return "rocket_artillery"
    if value in {"AIR DEFENSE", "AIR DEFENCE", "SHORAD"}:
        return "air_defense"
    if value in {"HQ", "HEADQUARTERS"}:
        return "headquarters"
    if value == "ENGINEER":
        return "engineer"
    if value == "SUPPLY":
        return "supply"
    if value == "CAVALRY":
        return "cavalry"
    return "unknown"


def unit_glyph_primitives(class_name: str) -> tuple[GlyphPrimitive, ...]:
    """Return normalized primitives centered inside a unit frame.

    Coordinates use a -0.5..0.5 symbol box.  Mechanized infantry is always a
    single coherent glyph: the infantry X crosses through the armor oval.
    """
    kind = canonical_unit_kind(class_name)
    if kind == "mechanized":
        return (
            GlyphPrimitive("ellipse", (-0.50, -0.30, 0.50, 0.30)),
            GlyphPrimitive("line", (-0.42, -0.30, 0.42, 0.30)),
            GlyphPrimitive("line", (0.42, -0.30, -0.42, 0.30)),
        )
    if kind == "infantry":
        return (
            GlyphPrimitive("line", (-0.48, -0.40, 0.48, 0.40)),
            GlyphPrimitive("line", (0.48, -0.40, -0.48, 0.40)),
        )
    if kind == "armor":
        return (GlyphPrimitive("ellipse", (-0.50, -0.30, 0.50, 0.30)),)
    if kind == "artillery":
        return (GlyphPrimitive("filled_ellipse", (-0.13, -0.13, 0.13, 0.13)),)
    if kind == "rocket_artillery":
        return tuple(
            primitive
            for x in (-0.32, 0.0, 0.32)
            for primitive in (
                GlyphPrimitive("line", (x, -0.36, x, 0.24)),
                GlyphPrimitive("filled_polygon", (x, 0.48, x - 0.10, 0.18, x + 0.10, 0.18)),
            )
        )
    if kind == "air_defense":
        return (
            GlyphPrimitive("arc", (-0.50, -0.08, 0.50, 0.48, 0.0, 180.0)),
            GlyphPrimitive("line", (0.0, -0.42, 0.0, 0.35)),
        )
    if kind == "cavalry":
        return (GlyphPrimitive("line", (-0.42, 0.32, 0.42, -0.32)),)
    if kind == "engineer":
        return (GlyphPrimitive("text_e", (0.0, 0.0)),)
    if kind == "supply":
        return (GlyphPrimitive("text_s", (0.0, 0.0)),)
    # A headquarters is identified by its frame staff, not letters inside the
    # frame.  Unknown classes intentionally remain blank instead of inventing
    # a non-standard glyph.
    return ()


def validate_symbol_contract() -> list[str]:
    """Return errors for invariants that previously regressed in brief images."""
    errors: list[str] = []
    mech = unit_glyph_primitives("MECH")
    if [item.kind for item in mech].count("ellipse") != 1 or [item.kind for item in mech].count("line") != 2:
        errors.append("Mechanized infantry must contain one armor oval and two infantry diagonals.")
    for primitive in mech:
        coords = primitive.values[:4]
        if coords and any(value < -0.55 or value > 0.55 for value in coords):
            errors.append("Mechanized infantry glyph escapes its shared frame box.")
    if unit_glyph_primitives("HQ"):
        errors.append("Headquarters must use a frame staff rather than an interior text glyph.")
    return errors
