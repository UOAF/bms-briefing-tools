#!/usr/bin/env python3
"""Compare BMSUtils decode JSON with a normalized pyopencam JSON export."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from pyopencam_adapter import normalize_pyopencam_export


COUNT_KEYS = ("Battalion", "Brigade", "Flight", "Package", "Squadron", "TaskForce")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_callsign(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").lower())


def vuid_nums(items: list[dict[str, Any]]) -> list[int]:
    return [safe_int(item.get("num")) for item in items]


def bms_package_flights(bms: dict[str, Any], package_id: int) -> list[dict[str, Any]]:
    return [
        flight
        for flight in bms.get("flights", [])
        if safe_int(flight.get("package_camp_id"), -1) == package_id
    ]


def py_package_flights(pyoc: dict[str, Any], package_id: int) -> list[dict[str, Any]]:
    return [
        flight
        for flight in pyoc.get("flights", [])
        if safe_int(flight.get("package_camp_id"), -1) == package_id
    ]


def flight_signature(flight: dict[str, Any]) -> tuple[int, str]:
    return safe_int(flight.get("camp_id")), normalize_callsign(flight.get("callsign"))


def compare_counts(label: str, bms: dict[str, Any], pyoc: dict[str, Any]) -> list[str]:
    mismatches = []
    bms_counts = bms.get("unit_counts") or {}
    py_counts = pyoc.get("unit_counts") or {}
    for key in COUNT_KEYS:
        if safe_int(bms_counts.get(key)) != safe_int(py_counts.get(key)):
            mismatches.append(
                f"{label}: {key} count mismatch BMSUtils={bms_counts.get(key)} pyopencam={py_counts.get(key)}"
            )
    return mismatches


def compare_package(label: str, bms: dict[str, Any], pyoc: dict[str, Any], package_id: int) -> list[str]:
    mismatches = []
    bms_package = next((item for item in bms.get("packages", []) if safe_int(item.get("camp_id"), -1) == package_id), None)
    py_package = next((item for item in pyoc.get("packages", []) if safe_int(item.get("camp_id"), -1) == package_id), None)
    if not bms_package and not py_package:
        return mismatches
    if not bms_package or not py_package:
        return [f"{label}: package {package_id} is present in only one decoder."]

    bms_elements = vuid_nums(bms_package.get("element_ids") or [])
    py_elements = vuid_nums(py_package.get("element_ids") or [])
    if bms_elements != py_elements:
        mismatches.append(
            f"{label}: package {package_id} element VU_IDs mismatch BMSUtils={bms_elements} pyopencam={py_elements}"
        )

    bms_flights = sorted(flight_signature(flight) for flight in bms_package_flights(bms, package_id))
    py_flights = sorted(flight_signature(flight) for flight in py_package_flights(pyoc, package_id))
    if bms_flights != py_flights:
        mismatches.append(
            f"{label}: package {package_id} flight signatures mismatch BMSUtils={bms_flights} pyopencam={py_flights}"
        )

    bms_wp = {
        safe_int(flight.get("camp_id")): safe_int(flight.get("num_waypoints"))
        for flight in bms_package_flights(bms, package_id)
    }
    py_wp = {
        safe_int(flight.get("camp_id")): safe_int(flight.get("waypoint_count"))
        for flight in py_package_flights(pyoc, package_id)
    }
    common_ids = sorted(set(bms_wp) & set(py_wp))
    mismatched_waypoints = [
        (flight_id, bms_wp[flight_id], py_wp[flight_id])
        for flight_id in common_ids
        if bms_wp[flight_id] != py_wp[flight_id]
    ]
    if mismatched_waypoints:
        mismatches.append(f"{label}: package {package_id} waypoint counts mismatch {mismatched_waypoints}")
    return mismatches


def compare_case(label: str, bms_path: Path, pyopencam_json_dir: Path, package_id: int | None) -> dict[str, Any]:
    bms = load_json(bms_path)
    pyoc = normalize_pyopencam_export(pyopencam_json_dir)
    mismatches = compare_counts(label, bms, pyoc)
    package_status = None
    if package_id is not None:
        bms_has_package = any(safe_int(item.get("camp_id"), -1) == package_id for item in bms.get("packages", []))
        py_has_package = any(safe_int(item.get("camp_id"), -1) == package_id for item in pyoc.get("packages", []))
        if not bms_has_package and not py_has_package:
            package_status = "not present in either decoder"
        else:
            package_status = "checked"
            mismatches.extend(compare_package(label, bms, pyoc, package_id))
    return {
        "label": label,
        "bmsutils": str(bms_path),
        "pyopencam_json_dir": str(pyopencam_json_dir),
        "package_id": package_id,
        "package_status": package_status,
        "status": "pass" if not mismatches else "fail",
        "mismatches": mismatches,
        "unit_counts": {
            "bmsutils": bms.get("unit_counts") or {},
            "pyopencam": pyoc.get("unit_counts") or {},
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        action="append",
        nargs=3,
        metavar=("LABEL", "BMSUTILS_JSON", "PYOPENCAM_JSON_DIR"),
        required=True,
        help="Comparison case. May be repeated.",
    )
    parser.add_argument("--package-id", type=int, help="Optional package id to compare when present.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = [
        compare_case(label, Path(bms_path), Path(py_dir), args.package_id)
        for label, bms_path, py_dir in args.case
    ]
    failed = [result for result in results if result["status"] != "pass"]
    if args.json:
        print(json.dumps({"status": "pass" if not failed else "fail", "cases": results}, indent=2))
    else:
        for result in results:
            print(f"{result['label']}: {result['status']}")
            if result["mismatches"]:
                for mismatch in result["mismatches"]:
                    print(f"  - {mismatch}")
            else:
                counts = result["unit_counts"]["bmsutils"]
                count_text = ", ".join(f"{key}={counts.get(key, 0)}" for key in COUNT_KEYS)
                package_text = ""
                if result.get("package_id") and result.get("package_status") == "checked":
                    package_text = f", package {result['package_id']} matched"
                elif result.get("package_id") and result.get("package_status"):
                    package_text = f", package {result['package_id']} {result['package_status']}"
                print(f"  {count_text}{package_text}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
