#!/usr/bin/env python3
"""Decode a Falcon BMS CAM save through an external pyopencam checkout."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_TEAM_NAMES = {
    0: "XX",
    1: "U.S.",
    2: "ROK",
    3: "Japan",
    4: "USSR",
    5: "PRC",
    6: "DPRK",
    7: "NATO",
}

ACTION_NAME_BY_CODE = {
    255: "WP_PRECISION",
    0: "WP_NOTHING",
    1: "WP_TAKEOFF",
    2: "WP_PUSH",
    3: "WP_SPLIT",
    4: "WP_REFUEL",
    5: "WP_REARM",
    6: "WP_PICKUP",
    7: "WP_LAND",
    8: "WP_TIMING",
    9: "WP_CASCP",
    10: "WP_ESCORT",
    11: "WP_SWEEP",
    12: "WP_CAP",
    13: "WP_INTERCEPT",
    14: "WP_GNDSTRIKE",
    15: "WP_NAVSTRIKE",
    16: "WP_SAD",
    17: "WP_STRIKE",
    18: "WP_BOMB",
    19: "WP_SEAD",
    20: "WP_ELINT",
    21: "WP_RECON",
    22: "WP_RESCUE",
    23: "WP_ASW",
    24: "WP_TANKER",
    25: "WP_AIRDROP",
    26: "WP_JAM",
    27: "WP_LAND2",
}

LOADOUT_STATION_COUNT = 16
FLIGHT_SLOT_COUNT = 4
LOADOUT_ENTRY_SIZE = 48


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def vuid(value: Any) -> dict[str, int | str]:
    if isinstance(value, dict):
        num = safe_int(value.get("num"))
        creator = safe_int(value.get("creator"))
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        num = safe_int(value[0])
        creator = safe_int(value[1])
    else:
        num = safe_int(value)
        creator = 0
    return {"num": num, "creator": creator, "key": f"{num}:{creator}"}


def field(record: Any, name: str, default: Any = None) -> Any:
    try:
        value = record.get(name)
    except Exception:
        return default
    return default if value is None else value


def decode_z_raw(value: Any) -> float:
    if not isinstance(value, (bytes, bytearray)) or len(value) != 4:
        return 0.0
    raw = struct.unpack("<f", value)[0]
    return raw if math.isfinite(raw) else 0.0


def raw_bytes(record: Any, name: str) -> bytes:
    value = field(record, name, b"")
    return bytes(value) if isinstance(value, (bytes, bytearray)) else b""


def decode_loadouts(raw: bytes, count: Any) -> list[dict[str, list[int]]]:
    loadout_count = safe_int(count)
    loadouts: list[dict[str, list[int]]] = []
    for index in range(loadout_count):
        start = index * LOADOUT_ENTRY_SIZE
        chunk = raw[start : start + LOADOUT_ENTRY_SIZE]
        if len(chunk) < LOADOUT_ENTRY_SIZE:
            break
        weapon_ids = list(struct.unpack("<" + ("H" * LOADOUT_STATION_COUNT), chunk[:32]))
        weapon_counts = list(chunk[32:48])
        loadouts.append({"weapon_ids": weapon_ids, "weapon_counts": weapon_counts})
    return loadouts


def decode_laser_codes(raw: bytes) -> list[int]:
    if len(raw) < FLIGHT_SLOT_COUNT * 2:
        return []
    return list(struct.unpack("<" + ("H" * FLIGHT_SLOT_COUNT), raw[: FLIGHT_SLOT_COUNT * 2]))


def decode_tacan(raw: bytes) -> list[dict[str, int]]:
    if len(raw) < FLIGHT_SLOT_COUNT * 2:
        return []
    channels = list(raw[:FLIGHT_SLOT_COUNT])
    bands = list(raw[FLIGHT_SLOT_COUNT : FLIGHT_SLOT_COUNT * 2])
    return [{"slot": index, "channel": channels[index], "band": bands[index]} for index in range(FLIGHT_SLOT_COUNT)]


def decode_loaded_cft(raw: bytes) -> list[bool]:
    if len(raw) < FLIGHT_SLOT_COUNT:
        return []
    return [bool(value) for value in raw[:FLIGHT_SLOT_COUNT]]


def aircraft_count_from_roster(value: Any) -> int:
    roster = safe_int(value)
    return sum((roster >> (2 * index)) & 3 for index in range(16))


def decode_waypoint_target(raw: bytes) -> tuple[dict[str, int | str], int]:
    if len(raw) < 9:
        return vuid((0, 0)), 255
    target_num, target_creator = struct.unpack("<II", raw[:8])
    return vuid((target_num, target_creator)), raw[8]


def first_vehicle_name(record: Any, support: Any) -> str:
    unit_type = unit_type_view(record, support)
    for slot in unit_type.get("vehicle_template") or []:
        name = str(slot.get("vehicle_name") or "").strip()
        if name:
            return name
    return ""


def unit_type_view(record: Any, support: Any) -> dict[str, Any]:
    ct_entry = support.ct_by_number.get(record.ct_index)
    unit_class = support.ucd_by_ct_idx.get(record.ct_index)
    vehicle_template = []
    if unit_class is not None:
        for slot, vehicle_ct_index in enumerate(unit_class.vehicle_ct_indices):
            if vehicle_ct_index is None:
                continue
            vehicle = support.vcd_by_ct_idx.get(vehicle_ct_index)
            vehicle_template.append(
                {
                    "slot": slot,
                    "vehicle_ct_index": vehicle_ct_index,
                    "vehicle_name": None if vehicle is None else vehicle.name,
                    "max_count": unit_class.element_counts[slot] if slot < len(unit_class.element_counts) else None,
                }
            )
    return {
        "raw": record.unit_type,
        "ct_index": record.ct_index,
        "kind": record.kind,
        "class_table": None
        if ct_entry is None
        else {
            "number": ct_entry.number,
            "domain": ct_entry.domain,
            "class": ct_entry.class_,
            "type": ct_entry.type_,
            "subtype": ct_entry.subtype,
            "specific": ct_entry.specific,
            "entity_type": ct_entry.entity_type,
            "entity_idx": ct_entry.entity_idx,
        },
        "unit_class": None
        if unit_class is None
        else {
            "number": unit_class.number,
            "ct_index": unit_class.ct_idx,
            "name": unit_class.name,
        },
        "vehicle_template": vehicle_template,
    }


def common_unit(record: Any, support: Any) -> dict[str, Any]:
    waypoints = list(field(record, "waypoints", ()))
    return {
        "id": vuid(field(record, "unit_id")),
        "type": str(record.kind).replace("_", " ").title().replace(" ", ""),
        "entity_type": field(record, "entity_type_copy", record.unit_type),
        "camp_id": field(record, "camp_id"),
        "name_id": field(record, "name_id"),
        "owner": field(record, "owner"),
        "x": field(record, "x"),
        "y": field(record, "y"),
        "z": decode_z_raw(field(record, "z_raw")),
        "roster": field(record, "roster"),
        "unit_flags": field(record, "unit_flags"),
        "current_wp": field(record, "current_wp"),
        "num_waypoints": len(waypoints),
        "unit_type": unit_type_view(record, support),
    }


def waypoint_item(index: int, waypoint: Any) -> dict[str, Any]:
    action = safe_int(getattr(waypoint, "action", 0))
    if action == 255:
        action_value = 255
    else:
        action_value = action
    target_id, target_building = decode_waypoint_target(getattr(waypoint, "target_data", b""))
    return {
        "index": index,
        "grid_x": getattr(waypoint, "x", None),
        "grid_y": getattr(waypoint, "y", None),
        "grid_z": getattr(waypoint, "z", None),
        "arrive": getattr(waypoint, "arrive_ms", None),
        "depart": getattr(waypoint, "depart_ms", None),
        "action": action_value,
        "action_name": ACTION_NAME_BY_CODE.get(action_value, f"WP_{action_value}"),
        "route_action": getattr(waypoint, "route_action", None),
        "speed": 0,
        "flags": getattr(waypoint, "flags", None),
        "target_id": target_id,
        "target_building": target_building,
    }


def mission_name(code: Any, support: Any, raw_name: Any = None) -> str:
    mission_code = safe_int(code)
    value = raw_name or support.strings_by_id.get(300 + mission_code)
    return str(value or f"MISSION_{mission_code}").strip()


def mission_short(code: Any, support: Any, raw_name: Any = None) -> str:
    return mission_name(code, support, raw_name)


def flight_item(record: Any, records_by_id: dict[tuple[int, int], Any], support: Any) -> dict[str, Any]:
    item = common_unit(record, support)
    mission_code = safe_int(field(record, "mission"))
    old_mission_code = safe_int(field(record, "old_mission"))
    current_mission_name = mission_name(mission_code, support)
    old_mission_name = mission_name(old_mission_code, support)
    package_id = vuid(field(record, "package_id"))
    squadron_id = vuid(field(record, "squadron_id"))
    package_record = records_by_id.get((safe_int(package_id["num"]), safe_int(package_id["creator"])))
    squadron_record = records_by_id.get((safe_int(squadron_id["num"]), safe_int(squadron_id["creator"])))
    callsign_id = safe_int(field(record, "callsign_id"))
    callsign_num = safe_int(field(record, "callsign_num"))
    callsign_root = support.strings_by_id.get(2000 + callsign_id, "")
    callsign = f"{callsign_root} {callsign_num}".strip() if callsign_root and callsign_num else ""
    plane_stats = list(field(record, "plane_stats", ()))
    loadout_count = safe_int(field(record, "loadouts"))
    loadouts = decode_loadouts(raw_bytes(record, "loadout_raw"), loadout_count)
    item.update(
        {
            "mission": mission_code,
            "mission_name": current_mission_name,
            "mission_short": mission_short(mission_code, support, current_mission_name),
            "pyopencam_mission_name": current_mission_name,
            "old_mission": old_mission_code,
            "old_mission_name": old_mission_name,
            "time_on_target": field(record, "time_on_target"),
            "mission_over_time": field(record, "mission_over_time"),
            "mission_target": field(record, "mission_id"),
            "mission_id": field(record, "mission_id"),
            "mission_context": field(record, "mission_context"),
            "requester_id": vuid(field(record, "requester_id")),
            "aircraft_count": aircraft_count_from_roster(field(record, "roster")),
            "plane_stats": plane_stats,
            "last_player_slot": field(record, "last_player_slot"),
            "player_slots": list(field(record, "player_slots", ())),
            "use_loadout": 0,
            "loadout_count": loadout_count,
            "loadouts": loadouts,
            "weapon_ids": [0],
            "weapon_counts": [0],
            "laser_codes": decode_laser_codes(raw_bytes(record, "laser_code_raw")),
            "loaded_cft": decode_loaded_cft(raw_bytes(record, "loaded_cft_raw")),
            "callsign_id": callsign_id,
            "callsign_name": callsign_root,
            "callsign_num": callsign_num,
            "callsign": callsign,
            "package_id": package_id,
            "package_camp_id": field(package_record, "camp_id") if package_record is not None else None,
            "squadron_id": squadron_id,
            "squadron_camp_id": field(squadron_record, "camp_id") if squadron_record is not None else None,
            "squadron_name": "",
            "tacan": decode_tacan(raw_bytes(record, "tacan_raw")),
            "pilots": list(field(record, "pilots", ())),
            "slots": list(field(record, "slots", ())),
            "waypoints": [waypoint_item(index, waypoint) for index, waypoint in enumerate(field(record, "waypoints", ()))],
        }
    )
    return item


def package_item(record: Any, support: Any) -> dict[str, Any]:
    item = common_unit(record, support)
    support_ids = [vuid(value) for value in field(record, "support_ids", ())]
    while len(support_ids) < 6:
        support_ids.append(vuid((0, 0)))
    mission_code = None
    tasking = None
    try:
        from lib.uni_wrappers import PackageUnit, wrap_units  # type: ignore

        wrapped = next(unit for unit in wrap_units((record,), support) if isinstance(unit, PackageUnit))
        tasking = wrapped.tasking
        mission_code = None if tasking is None else tasking.mission_code
    except Exception:
        mission_code = None
    mission_code = safe_int(mission_code, 0)
    request_mission_name = mission_name(mission_code, support, None if tasking is None else tasking.mission_name)
    item.update(
        {
            "elements": field(record, "elements"),
            "element_ids": [vuid(value) for value in field(record, "element_ids", ())],
            "awacs_id": support_ids[0],
            "jstar_id": support_ids[1],
            "ecm_id": support_ids[2],
            "tanker_id": support_ids[3],
            "interceptor_id": support_ids[4],
            "cargo_id": support_ids[5],
            "flights": 0,
            "takeoff": 0,
            "target_time": 0 if tasking is None else tasking.time_on_target_ms,
            "package_flags": 0,
            "ingress_point": {"x": 0, "y": 0},
            "egress_point": {"x": 0, "y": 0},
            "target_point": {"x": 0, "y": 0},
            "ingress_waypoints": None,
            "egress_waypoints": None,
            "mission_request": {
                "mission": mission_code,
                "mission_name": request_mission_name,
                "mission_short": mission_short(mission_code, support, request_mission_name),
                "aircraft": 0 if tasking is None else tasking.aircraft_code,
                "context": 0 if tasking is None else tasking.context_code,
                "tot": 0 if tasking is None else tasking.time_on_target_ms,
                "tx": 0 if tasking is None or tasking.target_x is None else tasking.target_x,
                "ty": 0 if tasking is None or tasking.target_y is None else tasking.target_y,
                "target_id": vuid((0, 0)),
                "requester_id": vuid((0, 0)),
                "priority": 0 if tasking is None else tasking.priority,
            },
        }
    )
    return item


def squadron_item(record: Any, support: Any) -> dict[str, Any]:
    item = common_unit(record, support)
    airfield_id = vuid(field(record, "airbase_id", (0, 0)))
    airframes = {}
    try:
        from lib.uni_wrappers import SquadronUnit, wrap_units  # type: ignore

        wrapped = next(unit for unit in wrap_units((record,), support) if isinstance(unit, SquadronUnit))
        airfield_id = vuid(wrapped.assigned_airfield_id)
        airframes = {
            "available": wrapped.available_airframes,
            "max": wrapped.max_airframes,
        }
    except Exception:
        pass
    item.update(
        {
            "airbase_id": airfield_id,
            "fuel": field(record, "fuel"),
            "specialty": field(record, "specialty"),
            "missions_flown": field(record, "missions_flown"),
            "total_losses": field(record, "total_losses"),
            "squadron_patch": 0,
            "squadron_name": "",
            "airframes": airframes,
        }
    )
    return item


def battalion_item(record: Any, support: Any) -> dict[str, Any]:
    item = common_unit(record, support)
    roster_slots = []
    try:
        from lib.uni_wrappers import BattalionUnit, wrap_units  # type: ignore

        wrapped = next(unit for unit in wrap_units((record,), support) if isinstance(unit, BattalionUnit))
        roster_slots = [
            {
                "index": slot.index,
                "status_code": slot.status_code,
                "current_count": slot.current_count,
                "max_count": slot.max_count,
                "vehicle_ct_index": slot.vehicle_ct_index,
                "vehicle_name": slot.vehicle_name,
            }
            for slot in wrapped.roster_slots
        ]
    except Exception:
        pass
    item.update(
        {
            "parent_id": vuid(field(record, "parent_id")),
            "last_obj": vuid(field(record, "last_obj")),
            "left_front": {"x": 0, "y": 0},
            "right_front": {"x": 0, "y": 0},
            "supply": field(record, "supply"),
            "fatigue": field(record, "fatigue"),
            "morale": field(record, "morale"),
            "heading": field(record, "heading"),
            "final_heading": field(record, "final_heading"),
            "position": field(record, "position"),
            "roster_slots": roster_slots,
        }
    )
    return item


def brigade_item(record: Any, support: Any) -> dict[str, Any]:
    item = common_unit(record, support)
    item.update({"elements": field(record, "elements"), "element_ids": [vuid(value) for value in field(record, "element_ids", ())]})
    return item


def task_force_item(record: Any, support: Any) -> dict[str, Any]:
    item = common_unit(record, support)
    item["waypoints"] = [waypoint_item(index, waypoint) for index, waypoint in enumerate(field(record, "waypoints", ()))]
    return item


def objective_delta_item(delta: Any) -> dict[str, Any]:
    statuses = list(getattr(delta, "feature_statuses", ()))
    return {
        "id": vuid(getattr(delta, "objective_id", (0, 0))),
        "last_repair": field(delta, "last_repair"),
        "owner": field(delta, "owner"),
        "supply": field(delta, "supply"),
        "fuel": field(delta, "fuel"),
        "losses": field(delta, "losses"),
        "fstatus_count": len(statuses),
        "fstatus": [safe_int(status) for status in statuses],
    }


def bullseye_item(cmp_record: Any) -> dict[str, Any] | None:
    x = field(cmp_record, "bullseye_x")
    y = field(cmp_record, "bullseye_y")
    if x is None or y is None:
        return None
    return {
        "name": field(cmp_record, "bullseye_name"),
        "x": safe_int(x),
        "y": safe_int(y),
        "grid_x": safe_int(x),
        "grid_y": safe_int(y),
        "source": ".cmp bullseye",
    }


def team_item(team: Any) -> dict[str, Any]:
    who = safe_int(getattr(team, "who", 0))
    stances = list(getattr(team, "stance", ()))
    return {
        "who": who,
        "cteam": getattr(team, "cteam", None),
        "flags": getattr(team, "flags", None),
        "team_flag": 0,
        "team_color": 0,
        "equipment": 0,
        "name": DEFAULT_TEAM_NAMES.get(who, str(who)),
        "member": list(getattr(team, "member", ())),
        "stance": [safe_int(stance) for stance in stances],
    }


def load_pyopencam(pyopencam_root: Path) -> None:
    if not (pyopencam_root / "cam_to_json.py").exists():
        raise FileNotFoundError(f"{pyopencam_root} does not look like a pyopencam checkout; missing cam_to_json.py")
    sys.path.insert(0, str(pyopencam_root))


def decode_cam(cam_path: Path, theater_folder: Path, pyopencam_root: Path) -> dict[str, Any]:
    load_pyopencam(pyopencam_root)
    from cam_to_json import find_entries_by_extension  # type: ignore
    from lib.cam_container import CamContainer  # type: ignore
    from lib.cmp_parser import parse_cmp_record  # type: ignore
    from lib.obd_parser import parse_obd_records  # type: ignore
    from lib.support_files import detect_container_version, load_support_data, resolve_support_paths  # type: ignore
    from lib.tea_parser import parse_tea_record  # type: ignore
    from lib.uni_parser import parse_uni_records  # type: ignore
    from lib.tea_wrappers import wrap_teams  # type: ignore

    container = CamContainer.from_path(cam_path)
    entries = find_entries_by_extension(container)
    version = detect_container_version(container)
    support = load_support_data(resolve_support_paths(theater_folder))

    cmp_record = parse_cmp_record(entries[".cmp"], container_version=version)
    obd_records = parse_obd_records(entries[".obd"], container_version=version)
    tea_record = parse_tea_record(entries[".tea"], container_version=version)
    uni_records = parse_uni_records(entries[".uni"], container_version=version, support=support)
    records_by_id = {field(record, "unit_id"): record for record in uni_records}

    packages = [package_item(record, support) for record in uni_records if record.kind == "package"]
    flights = [flight_item(record, records_by_id, support) for record in uni_records if record.kind == "flight"]
    squadrons = [squadron_item(record, support) for record in uni_records if record.kind == "squadron"]
    battalions = [battalion_item(record, support) for record in uni_records if record.kind == "battalion"]
    brigades = [brigade_item(record, support) for record in uni_records if record.kind == "brigade"]
    task_forces = [task_force_item(record, support) for record in uni_records if record.kind == "task_force"]

    unit_counts = Counter(record.kind for record in uni_records)
    mission_counts = Counter(flight.get("mission_short") for flight in flights if flight.get("mission_short"))
    bullseye = bullseye_item(cmp_record)
    return {
        "provider": {
            "name": "pyopencam",
            "pyopencam_root": str(pyopencam_root),
            "cam_path": str(cam_path),
            "theater_folder": str(theater_folder),
            "container_version": version,
            "save_version": version,
            "class_table_entries": len(support.ct_by_number),
            "gaps": [],
        },
        "campaign_clock": {
            "campaign_time_ms": field(cmp_record, "current_time"),
            "clock_base_ms": 50400000,
            "clock_base_hhmm": "1400",
            "current_time_z": None,
        },
        "bullseye": bullseye,
        "unit_counts": {
            "Battalion": unit_counts.get("battalion", 0),
            "Brigade": unit_counts.get("brigade", 0),
            "Flight": unit_counts.get("flight", 0),
            "Package": unit_counts.get("package", 0),
            "Squadron": unit_counts.get("squadron", 0),
            "TaskForce": unit_counts.get("task_force", 0),
        },
        "mission_counts": dict(sorted(mission_counts.items())),
        "teams": [team_item(team) for team in wrap_teams(tea_record).teams],
        "objective_deltas": [objective_delta_item(delta) for delta in obd_records],
        "packages": sorted(packages, key=lambda item: safe_int(item.get("camp_id"))),
        "flights": sorted(flights, key=lambda item: safe_int(item.get("camp_id"))),
        "squadrons": sorted(squadrons, key=lambda item: safe_int(item.get("camp_id"))),
        "battalions": sorted(battalions, key=lambda item: safe_int(item.get("camp_id"))),
        "brigades": sorted(brigades, key=lambda item: safe_int(item.get("camp_id"))),
        "task_forces": sorted(task_forces, key=lambda item: safe_int(item.get("camp_id"))),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cam", type=Path, required=True, help="CAM file to decode.")
    parser.add_argument("--theater-folder", type=Path, required=True, help="Matching theater folder containing Campaign and TerrData/Objects.")
    parser.add_argument("--pyopencam-root", type=Path, required=True, help="External pyopencam checkout/source directory.")
    parser.add_argument("--out", type=Path, required=True, help="Output cam_decode.json path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    decoded = decode_cam(args.cam.resolve(), args.theater_folder.resolve(), args.pyopencam_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(decoded, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
