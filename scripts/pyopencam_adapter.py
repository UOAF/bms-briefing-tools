#!/usr/bin/env python3
"""Normalize pyopencam JSON exports into this repo's comparison schema."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


UNIT_COUNT_LABELS = {
    "battalion": "Battalion",
    "brigade": "Brigade",
    "flight": "Flight",
    "package": "Package",
    "squadron": "Squadron",
    "task_force": "TaskForce",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def find_export_file(json_dir: Path, suffix: str) -> Path | None:
    matches = sorted(json_dir.glob(f"*.{suffix}.json"))
    if not matches:
        return None
    if len(matches) > 1:
        raise SystemExit(f"{json_dir} contains multiple *.{suffix}.json files.")
    return matches[0]


def vuid_num(value: Any) -> int:
    if isinstance(value, dict):
        try:
            return int(value.get("num") or 0)
        except (TypeError, ValueError):
            return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def vuid_key(value: Any) -> str:
    if not isinstance(value, dict):
        return f"{vuid_num(value)}:0"
    try:
        creator = int(value.get("creator") or 0)
    except (TypeError, ValueError):
        creator = 0
    return f"{vuid_num(value)}:{creator}"


def callsign_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or "").strip()
    return str(value or "").strip()


def unit_type(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("unit_type") or {}


def class_name(record: dict[str, Any]) -> str:
    unit_class = unit_type(record).get("unit_class") or {}
    return str(unit_class.get("name") or "").strip()


def vehicle_names(record: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for slot in unit_type(record).get("vehicle_template") or []:
        name = str(slot.get("vehicle_name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def common_unit(record: dict[str, Any]) -> dict[str, Any]:
    type_data = unit_type(record)
    return {
        "id": record.get("unit_id"),
        "id_key": vuid_key(record.get("unit_id")),
        "camp_id": record.get("campaign_id"),
        "kind": type_data.get("kind"),
        "entity_type": type_data.get("raw"),
        "ct_index": type_data.get("ct_index"),
        "class_name": class_name(record),
        "vehicle_names": vehicle_names(record),
    }


def normalize_package(record: dict[str, Any]) -> dict[str, Any]:
    package = record.get("package") or {}
    tasking = package.get("tasking") or {}
    item = common_unit(record)
    item.update(
        {
            "elements": package.get("elements"),
            "element_ids": package.get("element_ids") or [],
            "support_ids": package.get("support_ids") or [],
            "mission_code": tasking.get("mission_code"),
            "mission_name": tasking.get("mission_name"),
            "time_on_target_ms": tasking.get("time_on_target_ms"),
            "time_on_target_z": tasking.get("time_on_target_z"),
        }
    )
    return item


def normalize_flight(record: dict[str, Any]) -> dict[str, Any]:
    flight = record.get("flight") or {}
    item = common_unit(record)
    item.update(
        {
            "callsign": callsign_name(flight.get("callsign")),
            "package_camp_id": flight.get("package_number"),
            "package_id": flight.get("package_id"),
            "squadron_id": flight.get("squadron_id"),
            "mission_code": flight.get("mission_code"),
            "mission_name": flight.get("mission_name"),
            "takeoff_time_z": flight.get("takeoff_time_z"),
            "push_time_z": flight.get("push_time_z"),
            "time_on_target_z": flight.get("time_on_target_z"),
            "aircraft_count": flight.get("aircraft_count"),
            "waypoint_count": len(record.get("steerpoints") or []),
        }
    )
    return item


def normalize_squadron(record: dict[str, Any]) -> dict[str, Any]:
    squadron = record.get("squadron") or {}
    assigned = squadron.get("assigned_airfield") or {}
    airframes = squadron.get("airframes") or {}
    item = common_unit(record)
    item.update(
        {
            "name": squadron.get("name"),
            "airbase_id": vuid_num(assigned.get("airfield_id")),
            "hot_spot_id": vuid_num(assigned.get("hot_spot_id")),
            "airframes": {
                "available": airframes.get("available"),
                "max": airframes.get("max"),
            },
        }
    )
    return item


def normalize_battalion(record: dict[str, Any]) -> dict[str, Any]:
    battalion = record.get("battalion") or {}
    status = battalion.get("status") or {}
    roster = battalion.get("roster") or {}
    item = common_unit(record)
    item.update(
        {
            "status": status,
            "supply": status.get("supply"),
            "morale": status.get("morale"),
            "roster": {
                "raw_signed": roster.get("raw_signed"),
                "raw_unsigned": roster.get("raw_unsigned"),
                "slots": roster.get("slots") or [],
            },
        }
    )
    return item


def normalize_simple(record: dict[str, Any]) -> dict[str, Any]:
    return common_unit(record)


def normalize_pyopencam_export(json_dir: Path) -> dict[str, Any]:
    uni_path = find_export_file(json_dir, "uni")
    if not uni_path:
        raise SystemExit(f"{json_dir} does not contain a *.uni.json pyopencam export.")
    cmp_path = find_export_file(json_dir, "cmp")
    tea_path = find_export_file(json_dir, "tea")
    obd_path = find_export_file(json_dir, "obd")

    units = load_json(uni_path)
    if not isinstance(units, list):
        raise SystemExit(f"{uni_path} is not a pyopencam unit list.")

    by_kind: dict[str, list[dict[str, Any]]] = {
        "packages": [],
        "flights": [],
        "squadrons": [],
        "battalions": [],
        "brigades": [],
        "taskforces": [],
    }
    counts: Counter[str] = Counter()

    for record in units:
        kind = str(unit_type(record).get("kind") or "").strip()
        counts[kind] += 1
        if kind == "package":
            by_kind["packages"].append(normalize_package(record))
        elif kind == "flight":
            by_kind["flights"].append(normalize_flight(record))
        elif kind == "squadron":
            by_kind["squadrons"].append(normalize_squadron(record))
        elif kind == "battalion":
            by_kind["battalions"].append(normalize_battalion(record))
        elif kind == "brigade":
            by_kind["brigades"].append(normalize_simple(record))
        elif kind == "task_force":
            by_kind["taskforces"].append(normalize_simple(record))

    for items in by_kind.values():
        items.sort(key=lambda item: int(item.get("camp_id") or 0))

    return {
        "provider": "pyopencam-json",
        "source": {
            "json_dir": str(json_dir),
            "uni": str(uni_path),
            "cmp": str(cmp_path) if cmp_path else None,
            "tea": str(tea_path) if tea_path else None,
            "obd": str(obd_path) if obd_path else None,
        },
        "campaign_clock": load_json(cmp_path) if cmp_path else {},
        "teams": (load_json(tea_path).get("teams") if tea_path else []),
        "objective_delta_count": len(load_json(obd_path)) if obd_path else 0,
        "unit_counts": {
            UNIT_COUNT_LABELS.get(kind, kind): count
            for kind, count in sorted(counts.items())
        },
        **by_kind,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-dir", type=Path, required=True, help="Directory containing pyopencam *.json exports.")
    parser.add_argument("--out", type=Path, help="Optional normalized JSON output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalized = normalize_pyopencam_export(args.json_dir)
    text = json.dumps(normalized, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
