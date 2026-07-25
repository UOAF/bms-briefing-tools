#!/usr/bin/env python3
"""A/B compare direct pyopencam CAM decode against legacy BMSUtils decode."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


FLIGHT_FIELD_KEYS = (
    "owner",
    "x",
    "y",
    "z",
    "current_wp",
    "num_waypoints",
    "aircraft_count",
    "plane_stats",
    "use_loadout",
    "loadout_count",
    "loadouts",
    "weapon_ids",
    "weapon_counts",
    "laser_codes",
    "loaded_cft",
    "package_id",
    "package_camp_id",
    "squadron_id",
    "squadron_camp_id",
    "tacan",
)

WAYPOINT_FIELD_KEYS = (
    "grid_x",
    "grid_y",
    "grid_z",
    "arrive",
    "depart",
    "action",
    "route_action",
    "flags",
    "target_id",
    "target_building",
)

PACKAGE_FIELD_KEYS = (
    "owner",
    "x",
    "y",
    "z",
    "current_wp",
    "elements",
    "element_ids",
    "awacs_id",
    "jstar_id",
    "ecm_id",
    "tanker_id",
    "interceptor_id",
    "cargo_id",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, (int, float)) or isinstance(right, (int, float)):
        return math.isclose(safe_float(left), safe_float(right), abs_tol=0.01)
    return left == right


def by_camp_id(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(item["camp_id"]): item for item in items if item.get("camp_id") is not None}


def mismatch(label: str, field: str, left: Any, right: Any) -> str:
    return f"{label}: {field} mismatch pyopencam={left!r} bmsutils={right!r}"


def compare_fields(label: str, py_item: dict[str, Any], bms_item: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    return [
        mismatch(label, key, py_item.get(key), bms_item.get(key))
        for key in keys
        if not values_equal(py_item.get(key), bms_item.get(key))
    ]


def compare_waypoints(label: str, py_flight: dict[str, Any], bms_flight: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    py_waypoints = py_flight.get("waypoints") or []
    bms_waypoints = bms_flight.get("waypoints") or []
    if len(py_waypoints) != len(bms_waypoints):
        mismatches.append(mismatch(label, "waypoint_count", len(py_waypoints), len(bms_waypoints)))
        return mismatches
    for index, (py_wp, bms_wp) in enumerate(zip(py_waypoints, bms_waypoints)):
        wp_label = f"{label} waypoint {index}"
        mismatches.extend(compare_fields(wp_label, py_wp, bms_wp, WAYPOINT_FIELD_KEYS))
    return mismatches


def compare_collection(
    name: str,
    py_items: list[dict[str, Any]],
    bms_items: list[dict[str, Any]],
    keys: tuple[str, ...],
    focus_ids: set[int] | None = None,
) -> list[str]:
    mismatches: list[str] = []
    py_by_id = by_camp_id(py_items)
    bms_by_id = by_camp_id(bms_items)
    ids = sorted((set(py_by_id) & set(bms_by_id)) if focus_ids is None else focus_ids)
    missing_py = sorted(id_ for id_ in ids if id_ not in py_by_id)
    missing_bms = sorted(id_ for id_ in ids if id_ not in bms_by_id)
    if missing_py:
        mismatches.append(f"{name}: missing from pyopencam {missing_py[:20]}")
    if missing_bms:
        mismatches.append(f"{name}: missing from bmsutils {missing_bms[:20]}")
    for id_ in ids:
        if id_ not in py_by_id or id_ not in bms_by_id:
            continue
        label = f"{name} {id_}"
        mismatches.extend(compare_fields(label, py_by_id[id_], bms_by_id[id_], keys))
        if name == "flight":
            mismatches.extend(compare_waypoints(label, py_by_id[id_], bms_by_id[id_]))
    return mismatches


def package_flight_ids(decoded: dict[str, Any], package_id: int) -> set[int]:
    return {
        int(flight["camp_id"])
        for flight in decoded.get("flights", [])
        if flight.get("camp_id") is not None and int(flight.get("package_camp_id") or -1) == package_id
    }


def support_flight_ids(decoded: dict[str, Any], package_id: int) -> set[int]:
    packages = by_camp_id(decoded.get("packages", []))
    package = packages.get(package_id)
    if not package:
        return set()
    support_ids = {
        str((package.get(key) or {}).get("key") or "")
        for key in ("awacs_id", "jstar_id", "ecm_id", "tanker_id", "interceptor_id", "cargo_id")
    }
    return {
        int(flight["camp_id"])
        for flight in decoded.get("flights", [])
        if flight.get("camp_id") is not None and str((flight.get("id") or {}).get("key") or "") in support_ids
    }


def run_pyopencam(cam: Path, theater_folder: Path, pyopencam_root: Path, out: Path) -> None:
    helper = Path(__file__).with_name("pyopencam_provider.py")
    subprocess.run(
        [
            sys.executable,
            str(helper),
            "--cam",
            str(cam),
            "--theater-folder",
            str(theater_folder),
            "--pyopencam-root",
            str(pyopencam_root),
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def run_bmsutils(cam: Path, bms_root: Path, object_dir: Path | None, out: Path) -> None:
    helper = Path(__file__).with_name("extract_bms_cam.ps1")
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(helper),
        "-CamPath",
        str(cam),
        "-BmsRoot",
        str(bms_root),
        "-OutputPath",
        str(out),
    ]
    if object_dir:
        command.extend(["-ObjectDir", str(object_dir)])
    subprocess.run(command, check=True, capture_output=True, text=True)


def compare_decodes(pyoc: dict[str, Any], bms: dict[str, Any], package_id: int | None) -> list[str]:
    mismatches: list[str] = []
    if pyoc.get("unit_counts") != bms.get("unit_counts"):
        mismatches.append(mismatch("decode", "unit_counts", pyoc.get("unit_counts"), bms.get("unit_counts")))
    if len(pyoc.get("objective_deltas", [])) != len(bms.get("objective_deltas", [])):
        mismatches.append(
            mismatch(
                "decode",
                "objective_delta_count",
                len(pyoc.get("objective_deltas", [])),
                len(bms.get("objective_deltas", [])),
            )
        )
    if package_id is None:
        focus_flights = None
        focus_packages = None
    else:
        focus_packages = {package_id}
        focus_flights = package_flight_ids(pyoc, package_id) | support_flight_ids(pyoc, package_id)
    mismatches.extend(compare_collection("package", pyoc.get("packages", []), bms.get("packages", []), PACKAGE_FIELD_KEYS, focus_packages))
    mismatches.extend(compare_collection("flight", pyoc.get("flights", []), bms.get("flights", []), FLIGHT_FIELD_KEYS, focus_flights))
    return mismatches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cam", type=Path, required=True)
    parser.add_argument("--theater-folder", type=Path, required=True)
    parser.add_argument("--pyopencam-root", type=Path, required=True)
    parser.add_argument("--bms-root", type=Path, required=True)
    parser.add_argument("--object-dir", type=Path)
    parser.add_argument("--package-id", type=int)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="bms_cam_ab_") as temp_dir:
        temp = Path(temp_dir)
        pyoc_path = temp / "pyopencam.json"
        bms_path = temp / "bmsutils.json"
        run_pyopencam(args.cam, args.theater_folder, args.pyopencam_root, pyoc_path)
        run_bmsutils(args.cam, args.bms_root, args.object_dir, bms_path)
        pyoc = load_json(pyoc_path)
        bms = load_json(bms_path)
        mismatches = compare_decodes(pyoc, bms, args.package_id)
        result = {
            "status": "pass" if not mismatches else "fail",
            "cam": str(args.cam),
            "package_id": args.package_id,
            "mismatches": mismatches,
            "pyopencam_provider_gaps": (pyoc.get("provider") or {}).get("gaps", []),
        }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{args.cam.name}: {result['status']}")
        if args.package_id is not None:
            print(f"package {args.package_id}: checked package, package flights, and linked support flights")
        for gap in result["pyopencam_provider_gaps"]:
            print(f"provider note: {gap}")
        for item in mismatches[:50]:
            print(f"- {item}")
        if len(mismatches) > 50:
            print(f"... {len(mismatches) - 50} more mismatch(es)")
    if mismatches:
        sys.exit(1)


if __name__ == "__main__":
    main()
