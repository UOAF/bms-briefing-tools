#!/usr/bin/env python3
"""Deterministic UOAF player-flight A-A TACAN allocation."""

from __future__ import annotations

from typing import Any


DEFAULT_SCHEME: dict[str, int] = {
    "first_package_start": 15,
    "package_stride": 10,
    "flight_block_size": 5,
    "wingman_offset": 63,
}


def normalized_scheme(value: dict[str, Any] | None = None) -> dict[str, int]:
    scheme = dict(DEFAULT_SCHEME)
    if isinstance(value, dict):
        for key in scheme:
            if value.get(key) is not None:
                scheme[key] = int(value[key])
    if scheme["flight_block_size"] < 1:
        raise ValueError("A-A TACAN flight_block_size must be positive.")
    if scheme["package_stride"] < scheme["flight_block_size"]:
        raise ValueError("A-A TACAN package_stride must be at least flight_block_size.")
    return scheme


def flight_channels(
    package_index: int,
    flight_index: int,
    scheme_value: dict[str, Any] | None = None,
) -> list[str]:
    scheme = normalized_scheme(scheme_value)
    if package_index < 0:
        raise ValueError("A-A TACAN package_index cannot be negative.")
    if not 0 <= flight_index < scheme["flight_block_size"]:
        raise ValueError(
            f"A-A TACAN flight index {flight_index + 1} exceeds the "
            f"{scheme['flight_block_size']}-flight package block."
        )
    base = scheme["first_package_start"] + package_index * scheme["package_stride"] + flight_index
    paired = base + scheme["wingman_offset"]
    if base > 126 or paired > 126:
        raise ValueError(f"A-A TACAN allocation {base}/{paired} exceeds channel 126.")
    return [f"{base}X", f"{paired}X", f"{paired}Y", f"{base}Y"]


def flight_summary(
    package_index: int,
    flight_index: int,
    scheme_value: dict[str, Any] | None = None,
) -> str:
    return " / ".join(flight_channels(package_index, flight_index, scheme_value))


def package_index_for_id(context: dict[str, Any], package_id: int) -> int | None:
    for index, package in enumerate(context.get("packages") or []):
        if int(package.get("package_id") or 0) == int(package_id):
            return index
    return None


def package_assignments(
    context: dict[str, Any],
    package_id: int,
    callsigns: list[str],
) -> dict[str, str]:
    package_index = package_index_for_id(context, package_id)
    if package_index is None:
        return {}
    scheme = context.get("a2a_tacan_scheme") or {}
    return {
        callsign: flight_summary(package_index, flight_index, scheme)
        for flight_index, callsign in enumerate(callsigns)
        if callsign
    }
