#!/usr/bin/env python3
"""Build a first-pass human-readable briefing draft from decoded BMS data."""

from __future__ import annotations

import argparse
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from bms_weather import FMap, time_of_day_label
from bms_projection import feet_per_campaign_grid, source_feet_to_campaign_grid


STRIKE_MISSIONS = {
    "AI",
    "OCASTRIKE",
    "INTSTRIKE",
    "STRIKE",
    "DEEPSTRIKE",
    "STSTRIKE",
    "STRATBOMB",
    "SEADSTRIKE",
    "SEADESCORT",
    "CAS",
    "ONCALLCAS",
    "PRPLANCAS",
    "PREPLANCAS",
    "BAI",
    "SAD",
    "SCAR",
    "ASHIP",
    "TASMO",
}

SUPPORT_MISSIONS = {
    "ESCORT",
    "ECM",
    "EWSESJ",
    "AWACS",
    "AEWABCCC",
    "JSTAR",
    "ELINT",
    "TANKER",
    "AIRREFUEL",
    "RECON",
    "RECCE",
    "RECCEPATROL",
    "BDA",
}
CAP_MISSIONS = {
    "BARCAP",
    "BARCAP1",
    "BARCAP2",
    "HAVCAP",
    "TARCAP",
    "SWEEP",
    "INTERCEPT",
    "INTERCEPTION",
    "ALERT",
    "QRA",
}
TARGET_ACTIONS = {
    "WP_STRIKE",
    "WP_BOMB",
    "WP_SEAD",
    "WP_SAD",
    "WP_GNDSTRIKE",
    "WP_NAVSTRIKE",
    "WP_CAP",
    "WP_ESCORT",
    "WP_JAM",
    "WP_TANKER",
    "WP_ELINT",
}

ROUTE_ACTIONS = {
    "WP_TAKEOFF",
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
    "WP_TANKER",
    "WP_ELINT",
    "WP_JAM",
    "WP_REFUEL",
    "WP_LAND",
}
AIRBASE_WAYPOINT_ACTIONS = {"WP_TAKEOFF", "WP_LAND"}


def mission_key(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())

THREAT_AREA_ACTIONS = {
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

FEET_PER_GRID = feet_per_campaign_grid()
FEET_PER_NM = 6076.11549
DEFAULT_THEATER_GRID_ROWS = 928.0
DEFAULT_INI_GRID_OFFSET_X = 0.0
DEFAULT_INI_GRID_OFFSET_Y = 0.0
PLAN_MATCH_DISTANCE_GRID = 25.0
AIRBASE_WAYPOINT_MATCH_DISTANCE_GRID = 5.0
ENEMY_SITUATION_RADIUS_NM = 35.0
AIR_DEFENSE_RADIUS_NM = 60.0
ENEMY_AIRBASE_RADIUS_NM = 100.0
ACTIVE_AIR_CONTACT_RADIUS_NM = 30.0
ACTIVE_AIR_CONTACT_VECTOR_LOOKAHEAD_MIN = 20
ACTIVE_AIR_CONTACT_VECTOR_SOURCE_RADIUS_NM = 45.0
OTHER_PACKAGE_FRIENDLY_RADIUS_NM = 35.0
OTHER_PACKAGE_ENEMY_RADIUS_NM = 65.0
OTHER_PACKAGE_TIME_WINDOW_MIN = 90
SUPPORT_ID_FIELDS = (
    ("awacs_id", "AWACS"),
    ("jstar_id", "JSTAR"),
    ("ecm_id", "ECM"),
    ("tanker_id", "TANKER"),
    ("interceptor_id", "INTERCEPT"),
)

AIR_DEFENSE_NAMES = {"air defense", "aaa", "base defense"}
AIR_DEFENSE_KEYWORDS = (
    "aaa",
    "sam",
    "sa-",
    "zsu",
    "zu-",
    "ks-",
    "ksam",
    "chun-ma",
    "fan song",
    "spoon rest",
    "fire can",
    "radar",
)
AIR_UNIT_NAMES = {"fighter", "attack", "bomber", "air cavalry", "aggressor", "tanker", "airlift", "sigint"}

AIRBASE_OBJECTIVE_KEYWORDS = (
    "airbase",
    "air base",
    "airport",
    "airstrip",
    "highwaystrip",
    " ab",
    " as",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_mission_context(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return load_json(path)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_xml_records(path: Path, tag: str) -> dict[int, dict[str, Any]]:
    if not path.exists():
        return {}
    records: dict[int, dict[str, Any]] = {}
    root = ET.parse(path).getroot()
    for node in root.findall(tag):
        num = safe_int(node.attrib.get("Num"), -1)
        if num < 0:
            continue
        record = {"num": num}
        for child in node:
            record[child.tag] = child.text.strip() if child.text else ""
        records[num] = record
    return records


def load_objective_class_records(object_dir: Path) -> dict[int, dict[str, Any]]:
    base = object_dir / "ObjectiveRelatedData"
    if not base.exists():
        return {}
    records: dict[int, dict[str, Any]] = {}
    for path in base.glob("OCD_*/OCD_*.XML"):
        root = ET.parse(path).getroot()
        for node in root.findall("OCD"):
            num = safe_int(node.attrib.get("Num"), -1)
            if num < 0:
                continue
            record = {"num": num}
            for child in node:
                record[child.tag] = child.text.strip() if child.text else ""
            records[num] = record
    return records


def load_object_catalog(object_dir: Path | None) -> dict[str, Any]:
    if not object_dir:
        return {}
    if not object_dir.exists():
        return {}
    ucd = load_xml_records(object_dir / "Falcon4_UCD.xml", "UCD")
    ct = load_xml_records(object_dir / "Falcon4_CT.xml", "CT")
    vcd = load_xml_records(object_dir / "Falcon4_VCD.xml", "VCD")
    wcd = load_xml_records(object_dir / "Falcon4_WCD.xml", "WCD")
    ocd = load_objective_class_records(object_dir)
    vcd_by_ct = {
        safe_int(record.get("CtIdx")): record
        for record in vcd.values()
        if safe_int(record.get("CtIdx")) > 0
    }
    return {
        "object_dir": str(object_dir),
        "ucd": ucd,
        "ct": ct,
        "vcd_by_ct": vcd_by_ct,
        "wcd": wcd,
        "ocd": ocd,
    }


def mission_context_by_package(context: dict[str, Any]) -> dict[int, dict[str, Any]]:
    if not context:
        return {}
    packages = context.get("packages")
    if isinstance(packages, list):
        result: dict[int, dict[str, Any]] = {}
        for package_context in packages:
            package_id = int(package_context.get("package_id") or 0)
            if package_id:
                result[package_id] = package_context
        return result
    package_id = int(context.get("package_id") or 0)
    return {package_id: context} if package_id else {}


def context_contract_map(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for contract in [*context.get("sad_contracts", []), *context.get("cap_contracts", [])]:
        callsign = str(contract.get("callsign") or "").strip()
        if callsign:
            result[callsign] = contract
    return result


def load_objectives(path: Path) -> dict[int, dict[str, Any]]:
    root = ET.parse(path).getroot()
    objectives: dict[int, dict[str, Any]] = {}
    for node in root.findall("CampObj"):
        camp_id = int(node.attrib["CampId"])
        values = {child.tag: child.text or "" for child in node}
        objectives[camp_id] = {
            "camp_id": camp_id,
            "name": values.get("CampName", ""),
            "ocd_index": int(values.get("OcdIndex", "0") or 0),
            "heading": float(values.get("Heading", "0") or 0),
            "x": float(values.get("PositionX", "0") or 0),
            "y": float(values.get("PositionY", "0") or 0),
            "z": float(values.get("PositionZ", "0") or 0),
        }
    return objectives


def deck_package_mentions(briefing_data: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    mentions: dict[int, list[dict[str, Any]]] = defaultdict(list)
    deck = briefing_data.get("deck") or {}
    for slide in deck.get("relevant_slides", []):
        joined = "\n".join(slide.get("lines", []))
        for match in re.finditer(r"\b(?:PKG|Package)\s+(\d{3,5})\b", joined, re.I):
            package_id = int(match.group(1))
            mentions[package_id].append({"slide": slide.get("number"), "title": slide.get("title")})
    return dict(mentions)


def objective_delta_map(cam_decode: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for delta in cam_decode.get("objective_deltas", []):
        num = int(delta.get("id", {}).get("num", 0) or 0)
        if num:
            result[num] = delta
    return result


def objective_delta_key_map(cam_decode: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for delta in cam_decode.get("objective_deltas", []):
        key = delta.get("id", {}).get("key")
        if key:
            result[key] = delta
    return result


def format_clock(ms: int | None, clock: dict[str, Any] | None) -> str | None:
    if ms is None or not clock:
        return None
    campaign_time = int(clock.get("campaign_time_ms") or 0)
    base = int(clock.get("clock_base_ms") or 0)
    display = (int(ms) - campaign_time + base) % 86400000
    total_minutes = display // 60000
    return f"{total_minutes // 60:02d}{total_minutes % 60:02d}"


def unique_preserve(items: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for item in items:
        key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else item
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def vu_num(value: Any) -> int:
    if isinstance(value, dict):
        return int(value.get("num", 0) or 0)
    return int(value or 0)


def vu_key(value: Any) -> str | None:
    if isinstance(value, dict):
        key = value.get("key")
        if key:
            return str(key)
        num = value.get("num")
        creator = value.get("creator")
        if num is not None and creator is not None:
            return f"{num}:{creator}"
    return None


def unit_name(kind: str, unit: dict[str, Any]) -> str | None:
    if kind == "flight":
        return unit.get("callsign")
    if kind == "package":
        return f"PKG {unit.get('camp_id')}" if unit.get("camp_id") else None
    if kind == "squadron":
        return unit.get("squadron_name") or (f"Squadron {unit.get('camp_id')}" if unit.get("camp_id") else None)
    if unit.get("camp_id"):
        return f"{kind.title()} {unit.get('camp_id')}"
    if unit.get("name_id"):
        return f"{kind.title()} name {unit.get('name_id')}"
    return None


def unit_display(kind: str, unit: dict[str, Any], name: str | None) -> str:
    if kind == "flight":
        mission = unit.get("mission_short")
        return f"{name} ({mission})" if name and mission else name or "Flight"
    if kind == "package":
        mission = (unit.get("mission_request") or {}).get("mission_short")
        return f"{name} ({mission})" if name and mission else name or "Package"
    if kind == "squadron":
        return name or "Squadron"
    return name or kind.title()


def build_unit_index(cam_decode: dict[str, Any]) -> dict[str, dict[Any, list[dict[str, Any]]]]:
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_num: dict[int, list[dict[str, Any]]] = defaultdict(list)
    collections = {
        "flight": cam_decode.get("flights", []),
        "package": cam_decode.get("packages", []),
        "squadron": cam_decode.get("squadrons", []),
        "battalion": cam_decode.get("battalions", []),
        "brigade": cam_decode.get("brigades", []),
        "taskforce": cam_decode.get("taskforces", []),
    }
    for kind, units in collections.items():
        for unit in units:
            unit_id = unit.get("id") or {}
            num = vu_num(unit_id)
            key = vu_key(unit_id)
            if not num and not key:
                continue
            name = unit_name(kind, unit)
            ref = {
                "kind": kind,
                "id": unit_id,
                "camp_id": unit.get("camp_id"),
                "name_id": unit.get("name_id"),
                "name": name,
                "display": unit_display(kind, unit, name),
                "owner": unit.get("owner"),
                "x": unit.get("x"),
                "y": unit.get("y"),
            }
            if kind == "flight":
                ref["mission"] = unit.get("mission_short")
                ref["package_camp_id"] = unit.get("package_camp_id")
                ref["squadron_name"] = unit.get("squadron_name")
            elif kind == "package":
                ref["mission"] = (unit.get("mission_request") or {}).get("mission_short")
            elif kind == "squadron":
                ref["airbase_id"] = unit.get("airbase_id")
                ref["squadron_name"] = unit.get("squadron_name")
            elif kind in {"battalion", "brigade", "taskforce"}:
                ref["parent_id"] = unit.get("parent_id")
            if key:
                by_key[key].append(ref)
            if num:
                by_num[num].append(ref)
    return {"by_key": dict(by_key), "by_num": dict(by_num)}


def resolve_objective_like(
    objective_id: int,
    objectives: dict[int, dict[str, Any]],
    deltas: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    if not objective_id:
        return None
    base = objectives.get(objective_id)
    delta = deltas.get(objective_id)
    if not base and not delta:
        return None
    resolved = dict(base or {"camp_id": objective_id, "name": None})
    resolved["kind"] = "objective"
    if delta:
        resolved["owner"] = delta.get("owner")
        resolved["supply"] = delta.get("supply")
        resolved["fuel"] = delta.get("fuel")
        resolved["losses"] = delta.get("losses")
        resolved["fstatus_count"] = delta.get("fstatus_count")
    resolved["resolved"] = base is not None
    return resolved


def resolved_unit_refs(target_num: int, target_key: str | None, refs: list[dict[str, Any]]) -> dict[str, Any]:
    refs = unique_preserve(refs)
    if len(refs) == 1:
        resolved = dict(refs[0])
        resolved["target_num"] = target_num
        resolved["target_key"] = target_key
        resolved["resolved"] = True
        return resolved
    return {
        "kind": "unit_refs",
        "camp_id": target_num,
        "target_key": target_key,
        "name": " / ".join(ref.get("display") or ref.get("name") or ref.get("kind", "unit") for ref in refs[:4]),
        "refs": refs,
        "resolved": True,
    }


def resolve_target(
    target_id: Any,
    objectives: dict[int, dict[str, Any]],
    deltas_by_num: dict[int, dict[str, Any]],
    deltas_by_key: dict[str, dict[str, Any]],
    unit_index: dict[str, dict[Any, list[dict[str, Any]]]],
) -> dict[str, Any] | None:
    target_num = vu_num(target_id)
    target_key = vu_key(target_id)
    if not target_num:
        return None

    if target_key and target_key in unit_index["by_key"]:
        return resolved_unit_refs(target_num, target_key, unit_index["by_key"][target_key])
    if target_num in unit_index["by_num"]:
        return resolved_unit_refs(target_num, target_key, unit_index["by_num"][target_num])

    objective = resolve_objective_like(target_num, objectives, deltas_by_num)
    if objective:
        if target_key and target_key in deltas_by_key:
            objective["delta_id"] = deltas_by_key[target_key].get("id")
        return objective

    return {"kind": "unresolved", "camp_id": target_num, "id": target_id, "name": None, "resolved": False}


def flight_targets(
    flight: dict[str, Any],
    objectives: dict[int, dict[str, Any]],
    deltas_by_num: dict[int, dict[str, Any]],
    deltas_by_key: dict[str, dict[str, Any]],
    unit_index: dict[str, dict[Any, list[dict[str, Any]]]],
    tactical_only: bool = True,
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for waypoint in flight.get("waypoints", []):
        action = waypoint.get("action_name")
        if tactical_only and action not in TARGET_ACTIONS:
            continue
        target_id = waypoint.get("target_id", {})
        target = resolve_target(target_id, objectives, deltas_by_num, deltas_by_key, unit_index)
        if not target:
            continue
        target = dict(target)
        target["waypoint_index"] = waypoint.get("index")
        target["action"] = action
        target["arrive"] = waypoint.get("arrive")
        target["grid_x"] = waypoint.get("grid_x")
        target["grid_y"] = waypoint.get("grid_y")
        targets.append(target)
    return unique_preserve(targets)


def waypoint_summary(
    flight: dict[str, Any],
    clock: dict[str, Any] | None,
    objectives: dict[int, dict[str, Any]],
    deltas_by_num: dict[int, dict[str, Any]],
    deltas_by_key: dict[str, dict[str, Any]],
    unit_index: dict[str, dict[Any, list[dict[str, Any]]]],
    airbase_objectives: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    waypoints: list[dict[str, Any]] = []
    for waypoint in flight.get("waypoints", []):
        action = waypoint.get("action_name")
        if action not in ROUTE_ACTIONS:
            continue
        target_id = waypoint.get("target_id", {})
        target = resolve_target(target_id, objectives, deltas_by_num, deltas_by_key, unit_index)
        if target and target.get("kind") == "unresolved" and vu_num(target_id) == 0:
            target = None
        if action in AIRBASE_WAYPOINT_ACTIONS and not target_is_airbase(target, airbase_objectives):
            airbase = nearest_airbase_objective_for_waypoint(waypoint, airbase_objectives)
            if airbase:
                target = dict(airbase)
                target["original_target"] = target_id
                target["basis"] = "nearest airbase objective at takeoff/landing waypoint"
        waypoints.append(
            {
                "index": waypoint.get("index"),
                "action": action,
                "arrive_raw": waypoint.get("arrive"),
                "arrive_hhmm": format_clock(waypoint.get("arrive"), clock),
                "depart_raw": waypoint.get("depart"),
                "grid_x": waypoint.get("grid_x"),
                "grid_y": waypoint.get("grid_y"),
                "grid_z": waypoint.get("grid_z"),
                "target": target,
            }
        )
    return waypoints


def planning_point_label(point: dict[str, Any]) -> str:
    kind = point.get("kind")
    label = str(point.get("label") or "").strip()
    if kind == "ppt":
        return label or f"PPT {point.get('index')}"
    if kind == "target":
        if label and label.lower() != "not set":
            return label
        return f"TGT {point.get('index')}"
    if kind == "wpntarget":
        if label and label.lower() != "not set":
            return label
        return f"WPN {point.get('index')}"
    if kind == "linestpt":
        return f"LINE {point.get('index')}"
    return f"{str(kind or 'point').upper()} {point.get('index')}"


def planning_kind_rank(kind: str | None) -> int:
    return {"target": 0, "ppt": 1, "wpntarget": 2, "linestpt": 3}.get(kind or "", 9)


def action_label(action: str | None) -> str:
    return str(action or "WP").replace("WP_", "")


def action_summary_rank(action_short: str | None) -> int:
    return {
        "TIMING": 0,
        "PUSH": 1,
        "SPLIT": 2,
        "CAP": 3,
        "SAD": 4,
        "STRIKE": 5,
        "BOMB": 6,
        "SEAD": 7,
        "GNDSTRIKE": 8,
        "NAVSTRIKE": 9,
        "TAKEOFF": 10,
        "LAND": 11,
    }.get(action_short or "", 50)


def grid_distance_nm(distance_grid: float) -> float:
    return distance_grid * FEET_PER_GRID / FEET_PER_NM


def normalize_bullseye(cam_decode: dict[str, Any]) -> dict[str, Any] | None:
    raw = cam_decode.get("bullseye")
    if not isinstance(raw, dict):
        raw = (cam_decode.get("campaign_clock") or {}).get("bullseye")
    if not isinstance(raw, dict):
        return None
    grid_x = raw.get("grid_x", raw.get("x"))
    grid_y = raw.get("grid_y", raw.get("y"))
    if grid_x is None or grid_y is None:
        return None
    return {
        "name": raw.get("name"),
        "grid_x": safe_float(grid_x),
        "grid_y": safe_float(grid_y),
        "x": safe_float(raw.get("x", grid_x)),
        "y": safe_float(raw.get("y", grid_y)),
        "source": raw.get("source") or ".cmp bullseye",
    }


def ini_grid_transform_basis(ini_grid_offset_x: float, ini_grid_offset_y: float) -> str:
    def offset_text(value: float) -> str:
        if abs(value) < 0.000001:
            return ""
        if value < 0:
            return f" - {abs(value):g}"
        return f" + {value:g}"

    return (
        f"grid_x = (ini_y / {FEET_PER_GRID:g}){offset_text(ini_grid_offset_x)}; "
        f"grid_y = (ini_x / {FEET_PER_GRID:g}){offset_text(ini_grid_offset_y)}"
    )


def normalize_planning_point(
    point: dict[str, Any],
    ini_grid_offset_x: float,
    ini_grid_offset_y: float,
) -> dict[str, Any] | None:
    x = float(point.get("x") or 0)
    y = float(point.get("y") or 0)
    if abs(x) < 0.0001 and abs(y) < 0.0001:
        return None
    grid_x, grid_y = source_feet_to_campaign_grid(x, y, FEET_PER_GRID, ini_grid_offset_x, ini_grid_offset_y)
    converted = dict(point)
    converted["display"] = planning_point_label(point)
    converted["campaign_grid"] = {
        "grid_x": round(grid_x, 1),
        "grid_y": round(grid_y, 1),
        "source": f"Converted from INI world feet using {ini_grid_transform_basis(ini_grid_offset_x, ini_grid_offset_y)}.",
    }
    return converted


def normalized_planning_points(
    ini: dict[str, Any],
    ini_grid_offset_x: float,
    ini_grid_offset_y: float,
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    by_kind = ini.get("by_kind", {})
    for kind in ("target", "ppt", "wpntarget", "linestpt"):
        for point in by_kind.get(kind, []):
            converted = normalize_planning_point(point, ini_grid_offset_x, ini_grid_offset_y)
            if converted:
                points.append(converted)
    return points


def package_route_points(flight_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    route_points: list[dict[str, Any]] = []
    for flight in flight_summaries:
        for waypoint in flight.get("key_waypoints", []):
            if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
                continue
            route_points.append(
                {
                    "callsign": flight.get("callsign"),
                    "mission": flight.get("mission"),
                    "action": waypoint.get("action"),
                    "action_short": action_label(waypoint.get("action")),
                    "arrive_hhmm": waypoint.get("arrive_hhmm"),
                    "grid_x": waypoint.get("grid_x"),
                    "grid_y": waypoint.get("grid_y"),
                    "waypoint_index": waypoint.get("index"),
                }
            )
    return route_points


def nearest_route_point(point: dict[str, Any], route_points: list[dict[str, Any]]) -> dict[str, Any] | None:
    grid = point.get("campaign_grid") or {}
    grid_x = grid.get("grid_x")
    grid_y = grid.get("grid_y")
    if grid_x is None or grid_y is None or not route_points:
        return None
    nearest = min(
        route_points,
        key=lambda route: math.hypot(float(grid_x) - float(route["grid_x"]), float(grid_y) - float(route["grid_y"])),
    )
    distance_grid = math.hypot(float(grid_x) - float(nearest["grid_x"]), float(grid_y) - float(nearest["grid_y"]))
    return {
        "distance_grid": round(distance_grid, 1),
        "distance_nm": round(grid_distance_nm(distance_grid), 1),
        "route_point": nearest,
    }


def dedupe_plan_labels(points: list[dict[str, Any]], limit: int = 6) -> list[str]:
    labels: list[str] = []
    for point in sorted(points, key=lambda item: (planning_kind_rank(item.get("kind")), item.get("distance_grid") or 9999, item.get("index") or 0)):
        label = point.get("display")
        if label and label not in labels:
            labels.append(label)
    return labels[:limit]


def flight_plan_summary(
    flight: dict[str, Any],
    planning_points: list[dict[str, Any]],
    max_distance_grid: float = PLAN_MATCH_DISTANCE_GRID,
) -> tuple[str, list[dict[str, Any]]]:
    waypoint_matches_by_key: dict[tuple[Any, Any, Any], dict[str, Any]] = {}
    waypoints = [
        waypoint
        for waypoint in flight.get("key_waypoints", [])
        if waypoint.get("grid_x") is not None and waypoint.get("grid_y") is not None
    ]
    for point in planning_points:
        if point.get("kind") == "linestpt":
            continue
        grid = point.get("campaign_grid") or {}
        if grid.get("grid_x") is None or grid.get("grid_y") is None or not waypoints:
            continue
        nearest = min(
            waypoints,
            key=lambda waypoint: math.hypot(
                float(grid["grid_x"]) - float(waypoint["grid_x"]),
                float(grid["grid_y"]) - float(waypoint["grid_y"]),
            ),
        )
        distance_grid = math.hypot(float(grid["grid_x"]) - float(nearest["grid_x"]), float(grid["grid_y"]) - float(nearest["grid_y"]))
        if distance_grid > max_distance_grid:
            continue
        key = (nearest.get("index"), nearest.get("action"), nearest.get("arrive_hhmm"))
        if key not in waypoint_matches_by_key:
            waypoint_matches_by_key[key] = {
                "waypoint_index": nearest.get("index"),
                "action": nearest.get("action"),
                "action_short": action_label(nearest.get("action")),
                "arrive_hhmm": nearest.get("arrive_hhmm"),
                "grid_x": nearest.get("grid_x"),
                "grid_y": nearest.get("grid_y"),
                "matches": [],
            }
        waypoint_matches_by_key[key]["matches"].append(
            {
                "kind": point.get("kind"),
                "index": point.get("index"),
                "display": point.get("display"),
                "distance_grid": round(distance_grid, 1),
                "distance_nm": round(grid_distance_nm(distance_grid), 1),
                "campaign_grid": point.get("campaign_grid"),
            }
        )

    waypoint_order = {
        (waypoint.get("index"), waypoint.get("action"), waypoint.get("arrive_hhmm")): index
        for index, waypoint in enumerate(waypoints)
    }
    waypoint_matches = sorted(
        waypoint_matches_by_key.values(),
        key=lambda item: waypoint_order.get((item.get("waypoint_index"), item.get("action"), item.get("arrive_hhmm")), 999),
    )
    for waypoint_match in waypoint_matches:
        waypoint_match["matches"].sort(
            key=lambda item: (planning_kind_rank(item.get("kind")), item["distance_grid"], item.get("index") or 0)
        )

    summary_parts: list[str] = []
    for waypoint_match in sorted(waypoint_matches, key=lambda item: action_summary_rank(item.get("action_short"))):
        labels = dedupe_plan_labels(waypoint_match["matches"], limit=5)
        if labels:
            summary_parts.append(f"{waypoint_match['action_short']}: {', '.join(labels)}")
    if not summary_parts:
        return "No close data-cartridge planning marks", waypoint_matches
    return "; ".join(summary_parts[:3]), waypoint_matches


def package_plan_interpretation(correlation: dict[str, Any]) -> str:
    action_to_labels: dict[str, list[str]] = defaultdict(list)
    for match in correlation.get("point_matches", []):
        if match.get("kind") == "linestpt":
            continue
        action = (match.get("nearest_route") or {}).get("action_short")
        label = match.get("display")
        if action and label and label not in action_to_labels[action]:
            action_to_labels[action].append(label)
    phrases: list[str] = []
    if action_to_labels.get("TIMING"):
        phrases.append("TIMING is bracketed by " + ", ".join(action_to_labels["TIMING"][:6]))
    if action_to_labels.get("PUSH"):
        phrases.append("PUSH is marked by " + ", ".join(action_to_labels["PUSH"][:4]))
    if action_to_labels.get("SPLIT"):
        phrases.append("SPLIT/recovery is nearest " + ", ".join(action_to_labels["SPLIT"][:4]))
    line_summary = correlation.get("line_summary") or {}
    if line_summary.get("point_count"):
        phrases.append(
            f"the drawn line has {line_summary['point_count']} points nearest {line_summary.get('dominant_action', 'the route')}"
        )
    return "; ".join(phrases) if phrases else "INI planning marks did not correlate closely to this package route."


def correlate_package_plan(
    package_id: int,
    flight_summaries: list[dict[str, Any]],
    planning_points: list[dict[str, Any]],
    theater_grid_rows: float,
    ini_grid_offset_x: float,
    ini_grid_offset_y: float,
) -> dict[str, Any]:
    route_points = package_route_points(flight_summaries)
    point_matches: list[dict[str, Any]] = []
    line_distances: list[dict[str, Any]] = []
    for point in planning_points:
        nearest = nearest_route_point(point, route_points)
        if not nearest:
            continue
        route_point = nearest["route_point"]
        match = {
            "kind": point.get("kind"),
            "index": point.get("index"),
            "display": point.get("display"),
            "code": point.get("code"),
            "label": point.get("label"),
            "campaign_grid": point.get("campaign_grid"),
            "distance_grid": nearest["distance_grid"],
            "distance_nm": nearest["distance_nm"],
            "nearest_route": route_point,
        }
        if point.get("kind") == "linestpt":
            line_distances.append(match)
        elif nearest["distance_grid"] <= PLAN_MATCH_DISTANCE_GRID:
            point_matches.append(match)

    point_matches.sort(key=lambda item: (planning_kind_rank(item.get("kind")), item["distance_grid"], item.get("index") or 0))
    line_summary: dict[str, Any] = {"point_count": len(line_distances)}
    if line_distances:
        nearest_line = min(line_distances, key=lambda item: item["distance_grid"])
        actions = Counter((item.get("nearest_route") or {}).get("action_short") for item in line_distances)
        dominant_action = actions.most_common(1)[0][0]
        distances = [float(item["distance_nm"]) for item in line_distances]
        line_summary.update(
            {
                "dominant_action": dominant_action,
                "nearest": nearest_line,
                "min_distance_nm": round(min(distances), 1),
                "max_distance_nm": round(max(distances), 1),
                "interpretation": f"Drawn INI lineSTPT geometry tracks closest to {dominant_action} rather than the CAP/SAD station points.",
            }
        )
        line_distances.sort(key=lambda item: (item["distance_grid"], item.get("index") or 0))

    correlation = {
        "package_id": package_id,
        "grid_basis": {
            "feet_per_grid": FEET_PER_GRID,
            "feet_per_nm": FEET_PER_NM,
            "theater_grid_rows": theater_grid_rows,
            "ini_grid_offset_x": ini_grid_offset_x,
            "ini_grid_offset_y": ini_grid_offset_y,
            "ini_to_campaign_grid": ini_grid_transform_basis(ini_grid_offset_x, ini_grid_offset_y),
        },
        "max_match_distance_grid": PLAN_MATCH_DISTANCE_GRID,
        "max_match_distance_nm": round(grid_distance_nm(PLAN_MATCH_DISTANCE_GRID), 1),
        "point_matches": point_matches,
        "line_matches": line_distances,
        "line_summary": line_summary,
    }
    correlation["interpretation"] = package_plan_interpretation(correlation)
    return correlation


def package_score(package: dict[str, Any], flights: list[dict[str, Any]], deck_mentions: dict[int, list[dict[str, Any]]]) -> int:
    score = 0
    package_id = int(package.get("camp_id") or 0)
    mission = mission_key((package.get("mission_request") or {}).get("mission_short"))
    flight_missions = {mission_key(flight.get("mission_short")) for flight in flights}
    if package_id in deck_mentions:
        score += 100
    if mission in STRIKE_MISSIONS:
        score += 35
    if mission in CAP_MISSIONS:
        score += 20
    if mission in SUPPORT_MISSIONS:
        score += 18
    if flight_missions & STRIKE_MISSIONS:
        score += 30
    if flight_missions & CAP_MISSIONS:
        score += 15
    if flight_missions & SUPPORT_MISSIONS:
        score += 10
    score += min(len(flights) * 5, 30)
    return score


def package_flight_order(package: dict[str, Any], flight: dict[str, Any]) -> tuple[Any, ...]:
    element_order = {
        element.get("key"): index
        for index, element in enumerate(package.get("element_ids", []))
        if element.get("key")
    }
    flight_key = flight.get("id", {}).get("key")
    if flight_key in element_order:
        return (0, element_order[flight_key])
    return (1, flight.get("time_on_target") or 0, flight.get("callsign") or "")


def class_vehicle_records(unit_class: dict[str, Any], object_catalog: dict[str, Any]) -> list[dict[str, Any]]:
    vcd_by_ct = object_catalog.get("vcd_by_ct") or {}
    vehicles: list[dict[str, Any]] = []
    seen: set[int] = set()
    for key, value in sorted(unit_class.items()):
        if not key.startswith("VehicleCtIdx_"):
            continue
        ct_idx = safe_int(value)
        if ct_idx <= 0 or ct_idx in seen:
            continue
        seen.add(ct_idx)
        vehicle = vcd_by_ct.get(ct_idx)
        if vehicle:
            vehicles.append(vehicle)
    return vehicles


def resolve_unit_class(entity_type: Any, object_catalog: dict[str, Any]) -> dict[str, Any]:
    entity_id = safe_int(entity_type)
    ucd = object_catalog.get("ucd") or {}
    ct = object_catalog.get("ct") or {}

    def class_from_ct(ct_index: int, source_label: str) -> dict[str, Any]:
        ct_record = ct.get(ct_index, {})
        entity_idx = safe_int(ct_record.get("EntityIdx"), -1)
        unit = dict(ucd.get(entity_idx, {}))
        if unit:
            unit["source"] = f"{source_label} -> CT {ct_index} -> UCD {entity_idx}"
            return unit
        if ct_record:
            unit = dict(ct_record)
            unit["Name"] = f"CT {ct_index}"
            unit["source"] = f"{source_label} -> CT"
            return unit
        return {}

    # Campaign unit/objective entityType values are stored as class-table index
    # plus 100. Resolve through CT first so raw values do not collide with UCD
    # ids and produce impossible equipment labels.
    unit_class = {}
    if entity_id >= 100:
        unit_class = class_from_ct(entity_id - 100, f"entity {entity_id}")
    if not unit_class:
        unit_class = class_from_ct(entity_id, f"entity {entity_id}")
    if not unit_class and entity_id in ucd:
        unit_class = dict(ucd[entity_id])
        unit_class["source"] = "UCD"
    if not unit_class:
        unit_class = {"Name": f"Class {entity_id}", "source": "raw"}
    unit_class["entity_type"] = entity_id
    vehicles = class_vehicle_records(unit_class, object_catalog)
    unit_class["vehicles"] = vehicles
    unit_class["vehicle_names"] = [
        str(vehicle.get("Name") or "").strip()
        for vehicle in vehicles
        if str(vehicle.get("Name") or "").strip()
    ]
    return unit_class


def unit_class_name(unit_class: dict[str, Any]) -> str:
    return str(unit_class.get("Name") or f"Class {unit_class.get('entity_type')}").strip()


def is_air_defense_class(unit_class: dict[str, Any]) -> bool:
    name = unit_class_name(unit_class).lower()
    vehicle_text = " ".join(unit_class.get("vehicle_names") or []).lower()
    if name in AIR_DEFENSE_NAMES:
        return True
    return any(keyword in vehicle_text for keyword in AIR_DEFENSE_KEYWORDS)


def is_strategic_air_defense_unit(unit: dict[str, Any]) -> bool:
    class_name = str(unit.get("class_name") or "").strip().lower()
    return class_name == "air defense"


def enemy_category(unit_class: dict[str, Any]) -> str:
    name = unit_class_name(unit_class).lower()
    if is_air_defense_class(unit_class):
        return "air defense"
    if name in AIR_UNIT_NAMES:
        return "air unit"
    if any(token in name for token in ("armor", "mech", "infantry", "artillery", "recon", "engineer")):
        return "maneuver"
    return "other"


def threat_anchor_points(flight_summaries: list[dict[str, Any]], plan_correlation: dict[str, Any]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for flight in flight_summaries:
        for waypoint in flight.get("key_waypoints", []):
            if waypoint.get("action") not in THREAT_AREA_ACTIONS:
                continue
            if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
                continue
            anchors.append(
                {
                    "kind": "flight",
                    "label": f"{flight.get('callsign')} {action_label(waypoint.get('action'))} STPT {waypoint.get('index')}",
                    "callsign": flight.get("callsign"),
                    "action": action_label(waypoint.get("action")),
                    "time": waypoint.get("arrive_hhmm"),
                    "grid_x": waypoint.get("grid_x"),
                    "grid_y": waypoint.get("grid_y"),
                }
            )
    for match in [*plan_correlation.get("point_matches", []), *plan_correlation.get("line_matches", [])]:
        grid = match.get("campaign_grid") or {}
        if grid.get("grid_x") is None or grid.get("grid_y") is None:
            continue
        anchors.append(
            {
                "kind": "ini",
                "label": f"INI {match.get('display')}",
                "grid_x": grid.get("grid_x"),
                "grid_y": grid.get("grid_y"),
            }
        )
    return anchors


def nearest_anchor(unit: dict[str, Any], anchors: list[dict[str, Any]]) -> dict[str, Any] | None:
    if unit.get("x") is None or unit.get("y") is None or not anchors:
        return None
    nearest = min(
        anchors,
        key=lambda anchor: math.hypot(float(unit["x"]) - float(anchor["grid_x"]), float(unit["y"]) - float(anchor["grid_y"])),
    )
    distance_grid = math.hypot(float(unit["x"]) - float(nearest["grid_x"]), float(unit["y"]) - float(nearest["grid_y"]))
    return {
        "anchor": nearest,
        "distance_grid": round(distance_grid, 1),
        "distance_nm": round(grid_distance_nm(distance_grid), 1),
    }


def campaign_time_ms(clock: dict[str, Any] | None) -> int | None:
    if not clock:
        return None
    value = clock.get("campaign_time_ms")
    if value is None:
        return None
    return safe_int(value)


def raw_time_delta_minutes(a: Any, b: Any) -> int | None:
    if a is None or b is None:
        return None
    delta_ms = abs(safe_int(a) - safe_int(b))
    return int(round(delta_ms / 60000.0))


def flight_takeoff_land_times(flight: dict[str, Any]) -> tuple[int | None, int | None]:
    takeoffs = [
        safe_int(waypoint.get("arrive"))
        for waypoint in flight.get("waypoints", [])
        if waypoint.get("action_name") == "WP_TAKEOFF" and waypoint.get("arrive") is not None
    ]
    lands = [
        safe_int(waypoint.get("arrive"))
        for waypoint in flight.get("waypoints", [])
        if waypoint.get("action_name") == "WP_LAND" and waypoint.get("arrive") is not None
    ]
    return (min(takeoffs) if takeoffs else None, max(lands) if lands else None)


def flight_is_airborne_at_campaign_time(flight: dict[str, Any], clock: dict[str, Any] | None) -> bool:
    now = campaign_time_ms(clock)
    if now is None:
        return False
    takeoff, land = flight_takeoff_land_times(flight)
    if takeoff is None or land is None or not (takeoff <= now <= land):
        return False
    # BMS stores airborne altitude as negative Z in decoded CAM records. Keep
    # the route-time gate as primary, and use altitude/current_wp to reject
    # dormant records that still carry old or home-base coordinates.
    return abs(safe_float(flight.get("z"))) > 100.0 or safe_int(flight.get("current_wp")) > 1


def upcoming_waypoint_for_contact(
    flight: dict[str, Any],
    clock: dict[str, Any] | None,
    lookahead_min: int = ACTIVE_AIR_CONTACT_VECTOR_LOOKAHEAD_MIN,
) -> dict[str, Any] | None:
    now = campaign_time_ms(clock)
    if now is None:
        return None
    current_wp = safe_int(flight.get("current_wp"), -1)
    candidates = []
    for waypoint in flight.get("waypoints", []):
        arrive = waypoint.get("arrive")
        if arrive is None:
            continue
        arrive_int = safe_int(arrive)
        if arrive_int < now:
            continue
        index = safe_int(waypoint.get("index"), -1)
        if current_wp >= 0 and index < current_wp:
            continue
        delta = raw_time_delta_minutes(arrive_int, now)
        if delta is not None and delta <= lookahead_min:
            candidates.append((arrive_int, waypoint))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def point_segment_distance_grid(
    point: dict[str, Any],
    start: dict[str, Any],
    end: dict[str, Any],
) -> float | None:
    px, py = point.get("grid_x"), point.get("grid_y")
    sx, sy = start.get("grid_x"), start.get("grid_y")
    ex, ey = end.get("grid_x"), end.get("grid_y")
    if None in {px, py, sx, sy, ex, ey}:
        return None
    px_f, py_f = safe_float(px), safe_float(py)
    sx_f, sy_f = safe_float(sx), safe_float(sy)
    ex_f, ey_f = safe_float(ex), safe_float(ey)
    dx = ex_f - sx_f
    dy = ey_f - sy_f
    length_sq = dx * dx + dy * dy
    if length_sq <= 0.000001:
        return math.hypot(px_f - sx_f, py_f - sy_f)
    t = max(0.0, min(1.0, ((px_f - sx_f) * dx + (py_f - sy_f) * dy) / length_sq))
    closest_x = sx_f + t * dx
    closest_y = sy_f + t * dy
    return math.hypot(px_f - closest_x, py_f - closest_y)


def contact_vector_intercept(
    flight: dict[str, Any],
    anchors: list[dict[str, Any]],
    clock: dict[str, Any] | None,
) -> dict[str, Any] | None:
    waypoint = upcoming_waypoint_for_contact(flight, clock)
    if not waypoint:
        return None
    start = {"grid_x": flight.get("x"), "grid_y": flight.get("y")}
    end = {"grid_x": waypoint.get("grid_x"), "grid_y": waypoint.get("grid_y")}
    candidates: list[dict[str, Any]] = []
    for anchor in anchors:
        segment_distance = point_segment_distance_grid(anchor, start, end)
        if segment_distance is None:
            continue
        current_distance = math.hypot(
            safe_float(flight.get("x")) - safe_float(anchor.get("grid_x")),
            safe_float(flight.get("y")) - safe_float(anchor.get("grid_y")),
        )
        end_distance = math.hypot(
            safe_float(waypoint.get("grid_x")) - safe_float(anchor.get("grid_x")),
            safe_float(waypoint.get("grid_y")) - safe_float(anchor.get("grid_y")),
        )
        if end_distance >= current_distance:
            continue
        candidates.append(
            {
                "anchor": anchor,
                "distance_grid": round(segment_distance, 1),
                "distance_nm": round(grid_distance_nm(segment_distance), 1),
                "waypoint": waypoint,
                "waypoint_hhmm": format_clock(waypoint.get("arrive"), clock),
            }
        )
    if not candidates:
        return None
    return min(candidates, key=lambda item: item["distance_nm"])


def air_contact_capability(aircraft_label: str) -> str:
    fighters, strike = split_aircraft_summary(aircraft_label)
    if fighters:
        return "fighter-capable"
    if strike:
        return "strike-capable"
    return "air contact"


def analyze_active_enemy_air_contacts(
    cam_decode: dict[str, Any],
    object_catalog: dict[str, Any],
    teams_by_id: dict[int, dict[str, Any]],
    enemies: set[int],
    anchors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    clock = cam_decode.get("campaign_clock")
    contacts: list[dict[str, Any]] = []
    for flight in cam_decode.get("flights", []):
        owner = safe_int(flight.get("owner"), -1)
        if owner not in enemies or not flight_is_airborne_at_campaign_time(flight, clock):
            continue
        nearest = nearest_anchor(flight, anchors)
        vector = contact_vector_intercept(flight, anchors, clock)
        qualifies_by_position = bool(nearest and nearest["distance_nm"] <= ACTIVE_AIR_CONTACT_RADIUS_NM)
        qualifies_by_vector = bool(
            vector
            and vector["distance_nm"] <= ACTIVE_AIR_CONTACT_RADIUS_NM
            and nearest
            and nearest["distance_nm"] <= ACTIVE_AIR_CONTACT_VECTOR_SOURCE_RADIUS_NM
        )
        if not qualifies_by_position and not qualifies_by_vector:
            continue
        basis = "airborne now within 30 NM of target-area anchor"
        contact_anchor = nearest
        distance_nm = nearest["distance_nm"] if nearest else None
        if qualifies_by_vector and (not qualifies_by_position or safe_float(vector.get("distance_nm")) < safe_float(distance_nm, 9999.0)):
            basis = f"airborne now; next leg vectors inside 30 NM by {vector.get('waypoint_hhmm') or 'next steerpoint'}"
            contact_anchor = {"anchor": vector["anchor"], "distance_nm": vector["distance_nm"]}
            distance_nm = vector["distance_nm"]
        aircraft_type, aircraft_class = aircraft_label_for_unit(flight, object_catalog)
        aircraft = aircraft_type or aircraft_class or "unresolved aircraft"
        anchor = (contact_anchor or {}).get("anchor") or {}
        sector = compass_sector(bearing_degrees_from_to(anchor, {"grid_x": flight.get("x"), "grid_y": flight.get("y")}))
        contacts.append(
            {
                "team": teams_by_id.get(owner, {}).get("name") or str(owner),
                "aircraft_count": flight.get("aircraft_count") or aircraft_count_from_roster(flight.get("roster")),
                "aircraft_type": aircraft,
                "aircraft_class": aircraft_class,
                "capability": air_contact_capability(aircraft),
                "sector": sector,
                "grid_x": flight.get("x"),
                "grid_y": flight.get("y"),
                "altitude_ft": abs(safe_float(flight.get("z"))),
                "nearest_anchor": anchor,
                "distance_nm": round(safe_float(distance_nm), 1) if distance_nm is not None else None,
                "basis": basis,
            }
        )
    contacts.sort(key=lambda item: (safe_float(item.get("distance_nm"), 9999.0), str(item.get("aircraft_type") or "")))
    return contacts


def enemy_owner_ids(package: dict[str, Any], teams_by_id: dict[int, dict[str, Any]]) -> set[int]:
    friendly_owners = {safe_int(flight.get("owner"), -1) for flight in package.get("flights", [])}
    friendly_cteams = {
        safe_int(teams_by_id.get(owner, {}).get("cteam"), -1)
        for owner in friendly_owners
        if owner in teams_by_id
    }
    enemies = set()
    for team_id, team in teams_by_id.items():
        cteam = safe_int(team.get("cteam"), -1)
        if team_id in friendly_owners:
            continue
        if cteam in friendly_cteams or cteam in {0, 7, -1}:
            continue
        enemies.add(team_id)
    return enemies


def summarize_unit_classes(units: list[dict[str, Any]], limit: int = 4) -> str:
    counts = Counter(unit.get("class_name") for unit in units if unit.get("class_name"))
    if not counts:
        return "none"
    return ", ".join(f"{name} x{count}" for name, count in counts.most_common(limit))


def equipment_summary(unit_class: dict[str, Any], limit: int = 5) -> str:
    names = []
    for name in unit_class.get("vehicle_names") or []:
        if name and name not in names:
            names.append(name)
    return "; ".join(names[:limit])


def aircraft_count_from_roster(roster: Any) -> int:
    roster_value = safe_int(roster) & 0xFFFFFFFF
    return sum((roster_value >> (2 * index)) & 0x03 for index in range(16))


def aircraft_label_for_unit(unit: dict[str, Any], object_catalog: dict[str, Any]) -> tuple[str, str]:
    if not object_catalog:
        return "", ""
    unit_class = resolve_unit_class(unit.get("entity_type"), object_catalog)
    aircraft_type = equipment_summary(unit_class, limit=2) or unit_class_name(unit_class)
    return aircraft_type, unit_class_name(unit_class)


def weapon_name(weapon_id: Any, object_catalog: dict[str, Any]) -> str:
    weapon_id_int = safe_int(weapon_id)
    if weapon_id_int <= 0:
        return ""
    record = (object_catalog.get("wcd") or {}).get(weapon_id_int, {})
    name = str(record.get("Name") or "").strip()
    if not name or name == "- No Weapon":
        return f"WPN {weapon_id_int}"
    return name


def loadout_pairs_from_arrays(
    weapon_ids: list[Any],
    weapon_counts: list[Any],
    object_catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    pairs: dict[int, dict[str, Any]] = {}
    for weapon_id, count in zip(weapon_ids or [], weapon_counts or []):
        weapon_id_int = safe_int(weapon_id)
        count_int = safe_int(count)
        if weapon_id_int <= 0 or count_int <= 0:
            continue
        if weapon_id_int not in pairs:
            pairs[weapon_id_int] = {
                "weapon_id": weapon_id_int,
                "name": weapon_name(weapon_id_int, object_catalog),
                "count": 0,
            }
        pairs[weapon_id_int]["count"] += count_int
    return sorted(pairs.values(), key=lambda item: (str(item["name"]), item["weapon_id"]))


def selected_loadout_pairs(flight: dict[str, Any], object_catalog: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    loadouts = flight.get("loadouts") or []
    use_loadout = safe_int(flight.get("use_loadout"), -1)
    candidates: list[tuple[str, dict[str, Any]]] = []
    if 0 <= use_loadout < len(loadouts):
        candidates.append((f"loadout {use_loadout}", loadouts[use_loadout]))
    candidates.extend((f"loadout {index}", loadout) for index, loadout in enumerate(loadouts))
    for source, loadout in candidates:
        pairs = loadout_pairs_from_arrays(loadout.get("weapon_ids") or [], loadout.get("weapon_counts") or [], object_catalog)
        if pairs:
            return pairs, source
    fallback_pairs = loadout_pairs_from_arrays(flight.get("weapon_ids") or [], flight.get("weapon_counts") or [], object_catalog)
    if fallback_pairs:
        return fallback_pairs, "weapon arrays"
    return [], "not listed"


def weapons_summary(flight: dict[str, Any], object_catalog: dict[str, Any]) -> dict[str, Any]:
    pairs, source = selected_loadout_pairs(flight, object_catalog)
    if not pairs:
        return {
            "source": source,
            "items": [],
            "summary": "not listed",
        }
    text = ", ".join(f"{item['name']} x{item['count']}" for item in pairs[:8])
    if len(pairs) > 8:
        text += f", +{len(pairs) - 8} more"
    return {
        "source": source,
        "items": pairs,
        "summary": text,
    }


def laser_code_summary(flight: dict[str, Any]) -> str:
    codes: list[int] = []
    for code in flight.get("laser_codes") or []:
        code_int = safe_int(code)
        if code_int > 0 and code_int not in codes:
            codes.append(code_int)
    return ", ".join(str(code) for code in codes) if codes else "not set"


def tacan_summary(tacan: list[dict[str, Any]] | None) -> str:
    if not tacan:
        return "not assigned"
    entries = []
    for item in tacan:
        channel = safe_int(item.get("channel"))
        if channel <= 0:
            continue
        band = "Y" if safe_int(item.get("band")) else "X"
        slot = item.get("slot")
        entries.append(f"{channel}{band} slot {slot}")
    return ", ".join(entries) if entries else "not assigned"


def l16_records_by_flight_number(briefing_data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    records = {}
    for record in (briefing_data.get("l16") or {}).get("flights", []):
        flight_number = safe_int(record.get("flight_number"), -1)
        if flight_number >= 0:
            records[flight_number] = record
    return records


def correlate_l16_record(flight: dict[str, Any], l16_by_number: dict[int, dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        safe_int(flight.get("camp_id"), -1),
        safe_int(flight.get("name_id"), -1),
        vu_num(flight.get("id") or {}),
    ]
    for candidate in candidates:
        if candidate in l16_by_number:
            record = dict(l16_by_number[candidate])
            record["match_basis"] = "camp/name/VU number"
            return record
    return {
        "match_basis": "unresolved",
        "note": "No .l16 flight_number matched CAM camp_id, name_id, or VU num.",
    }


def station_waypoints(key_waypoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        waypoint
        for waypoint in key_waypoints
        if waypoint.get("action") in {"WP_TANKER", "WP_ELINT", "WP_AWACS", "WP_JAM", "WP_CAP"}
    ]


def station_summary(key_waypoints: list[dict[str, Any]]) -> str:
    points = station_waypoints(key_waypoints)
    if not points:
        points = [
            waypoint
            for waypoint in key_waypoints
            if waypoint.get("action") not in {"WP_TAKEOFF", "WP_LAND", "WP_NOTHING"}
        ]
    if not points:
        return "No station waypoint listed"
    labels = []
    for waypoint in points[:4]:
        action = action_label(waypoint.get("action"))
        time = waypoint.get("arrive_hhmm") or ""
        grid = f"{number_cell(waypoint.get('grid_x'), 0)}/{number_cell(waypoint.get('grid_y'), 0)}"
        labels.append(f"{action} STPT {waypoint.get('index')} {time} grid {grid}".strip())
    return "; ".join(labels)


def support_flight_summary(
    role: str,
    flight: dict[str, Any],
    clock: dict[str, Any] | None,
    objectives: dict[int, dict[str, Any]],
    deltas_by_num: dict[int, dict[str, Any]],
    deltas_by_key: dict[str, dict[str, Any]],
    unit_index: dict[str, dict[Any, list[dict[str, Any]]]],
    teams: dict[Any, Any],
    object_catalog: dict[str, Any],
    l16_by_number: dict[int, dict[str, Any]],
    airbase_objectives: list[dict[str, Any]],
) -> dict[str, Any]:
    key_waypoints = waypoint_summary(
        flight,
        clock,
        objectives,
        deltas_by_num,
        deltas_by_key,
        unit_index,
        airbase_objectives,
    )
    aircraft_type, aircraft_class = aircraft_label_for_unit(flight, object_catalog)
    weapon_info = weapons_summary(flight, object_catalog)
    if role in {"AWACS", "JSTAR", "TANKER"} and not weapon_info.get("items"):
        weapon_info = dict(weapon_info)
        weapon_info["summary"] = "none"
    return {
        "role": role,
        "camp_id": flight.get("camp_id"),
        "vu_id": flight.get("id"),
        "callsign": flight.get("callsign"),
        "mission": flight.get("mission_short"),
        "owner": flight.get("owner"),
        "team": teams.get(flight.get("owner")),
        "aircraft_count": flight.get("aircraft_count") or aircraft_count_from_roster(flight.get("roster")),
        "aircraft_type": aircraft_type,
        "aircraft_class": aircraft_class,
        "weapons": weapon_info,
        "weapons_summary": weapon_info["summary"],
        "laser_code_summary": "n/a" if role in {"AWACS", "JSTAR", "TANKER"} else laser_code_summary(flight),
        "tacan": flight.get("tacan", []),
        "tacan_summary": tacan_summary(flight.get("tacan", [])),
        "tot_raw": flight.get("time_on_target"),
        "tot_hhmm": format_clock(flight.get("time_on_target"), clock),
        "key_waypoints": key_waypoints,
        "waypoint_count": len(flight.get("waypoints", [])),
        "station_summary": station_summary(key_waypoints),
        "link16": correlate_l16_record(flight, l16_by_number),
    }


def load_fmap_from_briefing_data(briefing_data: dict[str, Any]) -> tuple[FMap | None, str | None, str | None]:
    fmap_info = (briefing_data.get("files") or {}).get(".fmap")
    fmap_path_raw = fmap_info.get("path") if isinstance(fmap_info, dict) else None
    if not fmap_path_raw:
        return None, None, None
    fmap_path = Path(fmap_path_raw)
    if not fmap_path.exists():
        return None, str(fmap_path), "FMAP sidecar path is missing on disk."
    try:
        return FMap.from_path(fmap_path), str(fmap_path), None
    except Exception as exc:
        return None, str(fmap_path), str(exc)


def first_waypoint_with_action(flight_summaries: list[dict[str, Any]], action: str) -> dict[str, Any] | None:
    for flight in flight_summaries:
        for waypoint in flight.get("key_waypoints", []):
            if waypoint.get("action") == action:
                item = dict(waypoint)
                item["callsign"] = flight.get("callsign")
                return item
    return None


def main_landing_waypoint(flight_summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    for flight in flight_summaries:
        tactical_indexes = [
            safe_int(waypoint.get("index"), -1)
            for waypoint in flight.get("key_waypoints", [])
            if waypoint.get("action") in THREAT_AREA_ACTIONS
        ]
        after_index = max(tactical_indexes) if tactical_indexes else -1
        for waypoint in flight.get("key_waypoints", []):
            if waypoint.get("action") == "WP_LAND" and safe_int(waypoint.get("index"), -1) > after_index:
                item = dict(waypoint)
                item["callsign"] = flight.get("callsign")
                return item
    return first_waypoint_with_action(flight_summaries, "WP_LAND")


def target_area_point(plan_correlation: dict[str, Any], flight_summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    excluded_labels = {"GRD", "GUARDPOST", "GUARD POST", "BAR", "BARRIER"}
    grids: list[tuple[float, float]] = []
    labels: list[str] = []
    for match in plan_correlation.get("point_matches", []):
        label = str(match.get("display") or match.get("label") or "").strip().upper()
        if not label or label in excluded_labels or label == "NOT SET":
            continue
        grid = match.get("campaign_grid") or {}
        if grid.get("grid_x") is None or grid.get("grid_y") is None:
            continue
        grids.append((safe_float(grid.get("grid_x")), safe_float(grid.get("grid_y"))))
        labels.append(label)
    if grids:
        return {
            "action": "TARGET_AREA",
            "arrive_hhmm": None,
            "grid_x": round(sum(item[0] for item in grids) / len(grids), 1),
            "grid_y": round(sum(item[1] for item in grids) / len(grids), 1),
            "basis": "Centroid of correlated INI objective PPTs " + ", ".join(labels[:8]),
        }

    tactical_points = []
    for flight in flight_summaries:
        for waypoint in flight.get("key_waypoints", []):
            if waypoint.get("action") in THREAT_AREA_ACTIONS and waypoint.get("grid_x") is not None and waypoint.get("grid_y") is not None:
                tactical_points.append(waypoint)
    if tactical_points:
        return {
            "action": "TARGET_AREA",
            "arrive_hhmm": None,
            "grid_x": round(sum(safe_float(item.get("grid_x")) for item in tactical_points) / len(tactical_points), 1),
            "grid_y": round(sum(safe_float(item.get("grid_y")) for item in tactical_points) / len(tactical_points), 1),
            "basis": "Centroid of decoded tactical package waypoints.",
        }
    return None


def package_time_window(flight_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    takeoffs = [flight.get("takeoff_hhmm") for flight in flight_summaries if flight.get("takeoff_hhmm")]
    tots = [flight.get("tot_hhmm") for flight in flight_summaries if flight.get("tot_hhmm")]
    return {
        "takeoff": min(takeoffs) if takeoffs else None,
        "target": min(tots) if tots else None,
    }


def package_weather_summary(
    fmap: FMap | None,
    fmap_path: str | None,
    fmap_error: str | None,
    flight_summaries: list[dict[str, Any]],
    plan_correlation: dict[str, Any],
) -> dict[str, Any]:
    if not fmap:
        return {
            "available": False,
            "source": fmap_path,
            "error": fmap_error or "No FMAP sidecar was found.",
        }

    time_window = package_time_window(flight_summaries)
    takeoff = first_waypoint_with_action(flight_summaries, "WP_TAKEOFF")
    target = target_area_point(plan_correlation, flight_summaries)
    landing = main_landing_waypoint(flight_summaries)
    sample_defs = [
        ("Takeoff", takeoff, time_window.get("takeoff")),
        ("Target Area", target, time_window.get("target")),
        ("Landing", landing, landing.get("arrive_hhmm") if landing else None),
    ]
    samples = []
    for label, point, fallback_time in sample_defs:
        if not point or point.get("grid_x") is None or point.get("grid_y") is None:
            continue
        sample = fmap.sample_grid(point.get("grid_x"), point.get("grid_y"), level=0)
        sample["label"] = label
        sample["time_hhmm"] = point.get("arrive_hhmm") or fallback_time
        sample["time_of_day"] = time_of_day_label(sample.get("time_hhmm"))
        sample["basis"] = point.get("basis") or (
            f"{point.get('callsign')} {action_label(point.get('action'))} STPT {point.get('index')}"
            if point.get("callsign")
            else action_label(point.get("action"))
        )
        samples.append(sample)
    return {
        "available": True,
        "source": fmap_path,
        "basis": "FMAP row 0 is north; campaign grid Y is inverted into weather row space before sampling.",
        "summary": fmap.summary(),
        "samples": samples,
    }


def unit_vehicle_template_slots(unit_class: dict[str, Any], object_catalog: dict[str, Any]) -> list[dict[str, Any]]:
    vcd_by_ct = object_catalog.get("vcd_by_ct") or {}
    slots: list[dict[str, Any]] = []
    for index in range(16):
        ct_idx = safe_int(unit_class.get(f"VehicleCtIdx_{index}"), 0)
        count_raw = unit_class.get(f"ElementCount_{index}")
        max_count = None if count_raw is None or str(count_raw).strip() == "" else safe_int(count_raw)
        vehicle = vcd_by_ct.get(ct_idx)
        slots.append(
            {
                "slot": index,
                "vehicle_ct_index": ct_idx if ct_idx > 0 else None,
                "vehicle_name": vehicle.get("Name") if vehicle else None,
                "max_count": max_count,
            }
        )
    return slots


def unit_roster_slots(
    unit: dict[str, Any],
    unit_class: dict[str, Any],
    object_catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    roster = safe_int(unit.get("roster")) & 0xFFFFFFFF
    slots = []
    for slot in unit_vehicle_template_slots(unit_class, object_catalog):
        index = safe_int(slot.get("slot"), 0)
        status_code = (roster >> (2 * index)) & 0x03
        item = dict(slot)
        item["status_code"] = status_code
        item["current_count"] = status_code
        slots.append(item)
    return slots


def tracking_radar_status(
    unit: dict[str, Any],
    unit_class: dict[str, Any],
    object_catalog: dict[str, Any],
) -> dict[str, Any]:
    radar_slot = safe_int(unit_class.get("RadarVehicle"), 255)
    if radar_slot < 0 or radar_slot >= 16 or radar_slot == 255:
        return {
            "slot": radar_slot,
            "active": False,
            "reason": "No tracking radar slot defined in UCD",
        }
    slots = unit_roster_slots(unit, unit_class, object_catalog)
    slot = next((item for item in slots if safe_int(item.get("slot"), -1) == radar_slot), None)
    if not slot:
        return {
            "slot": radar_slot,
            "active": False,
            "reason": "Radar slot not present in vehicle template",
        }
    active = safe_int(slot.get("current_count")) > 0
    return {
        "slot": radar_slot,
        "vehicle_ct_index": slot.get("vehicle_ct_index"),
        "vehicle_name": slot.get("vehicle_name"),
        "current_count": slot.get("current_count"),
        "max_count": slot.get("max_count"),
        "status_code": slot.get("status_code"),
        "active": active,
        "reason": "active roster slot" if active else "radar roster slot empty",
    }


def objective_grid(
    objective: dict[str, Any],
    ini_grid_offset_x: float,
    ini_grid_offset_y: float,
) -> dict[str, float]:
    grid_x, grid_y = source_feet_to_campaign_grid(
        safe_float(objective.get("x")),
        safe_float(objective.get("y")),
        FEET_PER_GRID,
        ini_grid_offset_x,
        ini_grid_offset_y,
    )
    return {
        "grid_x": round(grid_x, 1),
        "grid_y": round(grid_y, 1),
    }


def objective_class(objective: dict[str, Any], object_catalog: dict[str, Any]) -> dict[str, Any]:
    ocd = object_catalog.get("ocd") or {}
    return ocd.get(safe_int(objective.get("ocd_index")), {})


def is_squadron_base_objective(objective: dict[str, Any], object_catalog: dict[str, Any]) -> bool:
    ocd = objective_class(objective, object_catalog)
    text = f"{objective.get('name') or ''} {ocd.get('Name') or ''}".lower()
    return any(keyword in text for keyword in AIRBASE_OBJECTIVE_KEYWORDS)


def airbase_objective_rank(objective: dict[str, Any]) -> int:
    text = f"{objective.get('name') or ''} {objective.get('objective_class') or ''}".lower()
    if any(token in text for token in ("admn", "scny", "ammo")):
        return 10
    if "highway" in text or "airstrip" in text:
        return 2
    return 0


def build_airbase_objective_refs(
    objectives: dict[int, dict[str, Any]],
    object_catalog: dict[str, Any],
    ini_grid_offset_x: float,
    ini_grid_offset_y: float,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for objective in objectives.values():
        if not is_squadron_base_objective(objective, object_catalog):
            continue
        ocd = objective_class(objective, object_catalog)
        grid = objective_grid(objective, ini_grid_offset_x, ini_grid_offset_y)
        refs.append(
            {
                **objective,
                "kind": "objective",
                "resolved": True,
                "grid_x": grid["grid_x"],
                "grid_y": grid["grid_y"],
                "objective_class": ocd.get("Name") or "",
            }
        )
    return refs


def target_is_airbase(target: dict[str, Any] | None, airbase_objectives: list[dict[str, Any]]) -> bool:
    if not target:
        return False
    camp_id = safe_int(target.get("camp_id"))
    if camp_id and any(safe_int(airbase.get("camp_id")) == camp_id for airbase in airbase_objectives):
        return True
    text = f"{target.get('name') or ''} {target.get('objective_class') or ''}".lower()
    return any(keyword in text for keyword in AIRBASE_OBJECTIVE_KEYWORDS)


def nearest_airbase_objective_for_waypoint(
    waypoint: dict[str, Any],
    airbase_objectives: list[dict[str, Any]],
) -> dict[str, Any] | None:
    grid_x = waypoint.get("grid_x")
    grid_y = waypoint.get("grid_y")
    if grid_x is None or grid_y is None:
        return None
    candidates = []
    for airbase in airbase_objectives:
        distance = math.hypot(
            safe_float(airbase.get("grid_x")) - safe_float(grid_x),
            safe_float(airbase.get("grid_y")) - safe_float(grid_y),
        )
        if distance <= AIRBASE_WAYPOINT_MATCH_DISTANCE_GRID:
            candidates.append(
                (
                    round(distance, 3),
                    airbase_objective_rank(airbase),
                    safe_int(airbase.get("camp_id")),
                    airbase,
                )
            )
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[:3])[3]


def objective_destroyed(delta: dict[str, Any] | None) -> bool:
    if not delta:
        return False
    if safe_int(delta.get("losses")) >= 100:
        return True
    statuses = [safe_int(status, -1) for status in delta.get("fstatus", [])]
    meaningful = [status for status in statuses if status >= 0]
    return bool(meaningful) and all(status >= 3 for status in meaningful)


def objective_operational_percent(delta: dict[str, Any] | None) -> int | None:
    if not delta:
        return None
    if objective_destroyed(delta):
        return 0
    losses_raw = delta.get("losses")
    if losses_raw is not None and str(losses_raw).strip() != "":
        return max(0, min(100, 100 - safe_int(losses_raw)))
    return None


def objective_operational(delta: dict[str, Any] | None) -> bool:
    percent = objective_operational_percent(delta)
    if percent is not None and percent <= 0:
        return False
    return not objective_destroyed(delta)


def objective_status_summary(delta: dict[str, Any] | None) -> str:
    if not delta:
        return "No damage delta"
    statuses = [safe_int(status, -1) for status in delta.get("fstatus", [])]
    destroyed = sum(1 for status in statuses if status >= 3)
    damaged = sum(1 for status in statuses if status in {1, 2})
    if objective_destroyed(delta):
        return "Destroyed"
    if destroyed or damaged:
        return f"Usable, damaged ({destroyed} destroyed / {damaged} damaged facilities)"
    return "Usable"


def active_squadron(squadron: dict[str, Any]) -> bool:
    airframes = squadron.get("airframes")
    if isinstance(airframes, dict) and airframes.get("available") is not None:
        return vu_num(squadron.get("airbase_id")) > 0 and safe_int(airframes.get("available")) > 0
    return vu_num(squadron.get("airbase_id")) > 0 and safe_int(squadron.get("roster")) != 0


def summarize_airbase_aircraft(squadrons: list[dict[str, Any]], limit: int = 5) -> str:
    names: list[str] = []
    for squadron in squadrons:
        label = squadron.get("equipment")
        if label and label not in names:
            names.append(label)
    return "; ".join(names[:limit])


def summarize_airbase_threats(bases: list[dict[str, Any]], limit: int = 4) -> str:
    if not bases:
        return "none"
    summaries = []
    for base in bases[:limit]:
        aircraft = str(base.get("aircraft_summary") or "").strip()
        sqn_count = base.get("squadron_count")
        if aircraft:
            summaries.append(f"{base.get('name') or base.get('airbase_id')} ({sqn_count} sqn: {aircraft})")
        else:
            summaries.append(f"{base.get('name') or base.get('airbase_id')} ({sqn_count} sqn)")
    return ", ".join(summaries)


def analyze_enemy_airbase_threats(
    cam_decode: dict[str, Any],
    objectives: dict[int, dict[str, Any]],
    deltas_by_num: dict[int, dict[str, Any]],
    object_catalog: dict[str, Any],
    teams_by_id: dict[int, dict[str, Any]],
    enemies: set[int],
    anchors: list[dict[str, Any]],
    theater_grid_rows: float,
    ini_grid_offset_x: float,
    ini_grid_offset_y: float,
) -> list[dict[str, Any]]:
    bases: dict[int, dict[str, Any]] = {}
    for squadron in cam_decode.get("squadrons", []):
        owner = safe_int(squadron.get("owner"), -1)
        if owner not in enemies or not active_squadron(squadron):
            continue
        airbase_id = vu_num(squadron.get("airbase_id"))
        objective = objectives.get(airbase_id)
        if not objective:
            continue
        if not is_squadron_base_objective(objective, object_catalog):
            continue
        delta = deltas_by_num.get(airbase_id)
        if not objective_operational(delta):
            continue
        grid = objective_grid(objective, ini_grid_offset_x, ini_grid_offset_y)
        nearest = nearest_anchor({"x": grid["grid_x"], "y": grid["grid_y"]}, anchors)
        if not nearest or nearest["distance_nm"] > ENEMY_AIRBASE_RADIUS_NM:
            continue

        unit_class = resolve_unit_class(squadron.get("entity_type"), object_catalog)
        if enemy_category(unit_class) != "air unit":
            continue
        equipment = equipment_summary(unit_class, limit=3)
        squadron_summary = {
            "camp_id": squadron.get("camp_id"),
            "owner": owner,
            "team": teams_by_id.get(owner, {}).get("name") or str(owner),
            "class_id": squadron.get("entity_type"),
            "class_name": unit_class_name(unit_class),
            "class_source": unit_class.get("source"),
            "equipment": equipment,
            "missions_flown": squadron.get("missions_flown"),
            "total_losses": squadron.get("total_losses"),
            "fuel": squadron.get("fuel"),
            "roster": squadron.get("roster"),
            "available_airframes": (squadron.get("airframes") or {}).get("available")
            if isinstance(squadron.get("airframes"), dict)
            else None,
            "max_airframes": (squadron.get("airframes") or {}).get("max")
            if isinstance(squadron.get("airframes"), dict)
            else None,
        }
        if airbase_id not in bases:
            ocd = objective_class(objective, object_catalog)
            operational_percent = objective_operational_percent(delta)
            bases[airbase_id] = {
                "airbase_id": airbase_id,
                "name": objective.get("name") or f"Objective {airbase_id}",
                "team": teams_by_id.get(owner, {}).get("name") or str(owner),
                "teams": [],
                "ocd_index": objective.get("ocd_index"),
                "objective_class": ocd.get("Name") or "",
                "is_airbase_class": is_squadron_base_objective(objective, object_catalog),
                "source_x": objective.get("x"),
                "source_y": objective.get("y"),
                "source_z": objective.get("z"),
                "grid_x": grid["grid_x"],
                "grid_y": grid["grid_y"],
                "distance_nm": nearest["distance_nm"],
                "distance_grid": nearest["distance_grid"],
                "nearest_anchor": nearest["anchor"],
                "status": objective_status_summary(delta),
                "operational_percent": operational_percent,
                "operational_status": "unknown" if operational_percent is None else f"{operational_percent}%",
                "supply": delta.get("supply") if delta else None,
                "fuel": delta.get("fuel") if delta else None,
                "losses": delta.get("losses") if delta else None,
                "squadrons": [],
            }
        base = bases[airbase_id]
        if squadron_summary["team"] not in base["teams"]:
            base["teams"].append(squadron_summary["team"])
        base["squadrons"].append(squadron_summary)

    for base in bases.values():
        base["squadrons"].sort(key=lambda item: (str(item.get("class_name") or ""), item.get("camp_id") or 0))
        base["squadron_count"] = len(base["squadrons"])
        base["team"] = ", ".join(base["teams"])
        base["aircraft_summary"] = summarize_airbase_aircraft(base["squadrons"])
        base["squadron_ids"] = ", ".join(str(item.get("camp_id")) for item in base["squadrons"] if item.get("camp_id"))
    return sorted(bases.values(), key=lambda item: (item["distance_nm"], item["airbase_id"]))


def analyze_enemy_situation(
    package: dict[str, Any],
    cam_decode: dict[str, Any],
    objectives: dict[int, dict[str, Any]],
    deltas_by_num: dict[int, dict[str, Any]],
    object_catalog: dict[str, Any],
    teams_by_id: dict[int, dict[str, Any]],
    plan_correlation: dict[str, Any],
    theater_grid_rows: float,
    ini_grid_offset_x: float,
    ini_grid_offset_y: float,
) -> dict[str, Any]:
    if not object_catalog:
        return {}
    anchors = threat_anchor_points(package.get("flights", []), plan_correlation)
    if not anchors:
        return {}
    enemies = enemy_owner_ids(package, teams_by_id)
    if not enemies:
        return {}

    threat_units: list[dict[str, Any]] = []
    air_defenses: list[dict[str, Any]] = []
    inactive_air_defenses: list[dict[str, Any]] = []
    for battalion in cam_decode.get("battalions", []):
        owner = safe_int(battalion.get("owner"), -1)
        if owner not in enemies:
            continue
        nearest = nearest_anchor(battalion, anchors)
        if not nearest:
            continue
        unit_class = resolve_unit_class(battalion.get("entity_type"), object_catalog)
        category = enemy_category(unit_class)
        tracking_radar = tracking_radar_status(battalion, unit_class, object_catalog)
        unit = {
            "camp_id": battalion.get("camp_id"),
            "owner": owner,
            "team": teams_by_id.get(owner, {}).get("name") or str(owner),
            "class_id": battalion.get("entity_type"),
            "class_name": unit_class_name(unit_class),
            "class_source": unit_class.get("source"),
            "category": category,
            "grid_x": battalion.get("x"),
            "grid_y": battalion.get("y"),
            "distance_nm": nearest["distance_nm"],
            "distance_grid": nearest["distance_grid"],
            "nearest_anchor": nearest["anchor"],
            "supply": battalion.get("supply"),
            "morale": battalion.get("morale"),
            "air_range": safe_int(unit_class.get("Rng_Air")),
            "low_air_range": safe_int(unit_class.get("Rng_LowAir")),
            "air_strength": safe_int(unit_class.get("Str_Air")),
            "low_air_strength": safe_int(unit_class.get("Str_LowAir")),
            "radar_vehicle": safe_int(unit_class.get("RadarVehicle"), 255),
            "tracking_radar": tracking_radar,
            "active_tracking_radar": bool(tracking_radar.get("active")),
            "equipment": equipment_summary(unit_class),
        }
        strategic_air_defense_candidate = category == "air defense" and is_strategic_air_defense_unit(unit)
        strategic_air_defense = strategic_air_defense_candidate and bool(tracking_radar.get("active"))
        if (
            category != "air unit"
            and nearest["distance_nm"] <= ENEMY_SITUATION_RADIUS_NM
            and (category != "air defense" or strategic_air_defense)
        ):
            threat_units.append(unit)
        if strategic_air_defense and nearest["distance_nm"] <= AIR_DEFENSE_RADIUS_NM:
            air_defenses.append(unit)
        elif strategic_air_defense_candidate and nearest["distance_nm"] <= AIR_DEFENSE_RADIUS_NM:
            inactive_air_defenses.append(unit)

    threat_units.sort(key=lambda item: (item["distance_nm"], item.get("camp_id") or 0))
    air_defenses.sort(key=lambda item: (item["distance_nm"], item.get("camp_id") or 0))
    inactive_air_defenses.sort(key=lambda item: (item["distance_nm"], item.get("camp_id") or 0))
    airbases = analyze_enemy_airbase_threats(
        cam_decode,
        objectives,
        deltas_by_num,
        object_catalog,
        teams_by_id,
        enemies,
        anchors,
        theater_grid_rows,
        ini_grid_offset_x,
        ini_grid_offset_y,
    )
    active_air_contacts = analyze_active_enemy_air_contacts(cam_decode, object_catalog, teams_by_id, enemies, anchors)
    enemy_team_names = sorted({teams_by_id.get(owner, {}).get("name") or str(owner) for owner in enemies})
    airbase_squadron_count = sum(safe_int(base.get("squadron_count")) for base in airbases)
    summary = (
        f"{len(threat_units)} enemy non-air unit records within {ENEMY_SITUATION_RADIUS_NM:.0f} NM of package/INI tactical anchors; "
        f"dominant nearby classes: {summarize_unit_classes(threat_units)}. "
        f"{len(air_defenses)} strategic air-defense records with active tracking radars within {AIR_DEFENSE_RADIUS_NM:.0f} NM; "
        f"strategic AD classes: {summarize_unit_classes(air_defenses)}. "
        f"{len(inactive_air_defenses)} strategic ADA candidates filtered for inactive/missing tracking radars. "
        f"{len(airbases)} enemy squadron bases within {ENEMY_AIRBASE_RADIUS_NM:.0f} NM hosting {airbase_squadron_count} active squadrons. "
        f"{len(active_air_contacts)} active enemy air contact(s) at campaign time within or vectoring into {ACTIVE_AIR_CONTACT_RADIUS_NM:.0f} NM of the target area."
    )
    return {
        "basis": "Distances are from enemy battalion grid positions to decoded package route/CAP/SAD anchors and correlated INI marks. Strategic ADA requires an active decoded tracking-radar roster slot.",
        "enemy_teams": enemy_team_names,
        "anchor_count": len(anchors),
        "unit_radius_nm": ENEMY_SITUATION_RADIUS_NM,
        "air_defense_radius_nm": AIR_DEFENSE_RADIUS_NM,
        "airbase_radius_nm": ENEMY_AIRBASE_RADIUS_NM,
        "active_air_contact_radius_nm": ACTIVE_AIR_CONTACT_RADIUS_NM,
        "summary": summary,
        "airbase_summary": f"Closest squadron bases: {summarize_airbase_threats(airbases)}.",
        "counts_by_class": dict(Counter(unit.get("class_name") for unit in threat_units if unit.get("class_name"))),
        "air_defense_counts_by_class": dict(
            Counter(unit.get("class_name") for unit in air_defenses if unit.get("class_name"))
        ),
        "closest_units": threat_units[:16],
        "air_defenses": air_defenses[:16],
        "air_defense_locations": air_defenses[:64],
        "inactive_air_defenses": inactive_air_defenses[:16],
        "inactive_air_defense_locations": inactive_air_defenses[:64],
        "airbases": airbases[:24],
        "airbase_locations": airbases[:64],
        "active_air_contacts": active_air_contacts[:16],
    }


def synthesize(
    briefing_data: dict[str, Any],
    cam_decode: dict[str, Any],
    objectives: dict[int, dict[str, Any]],
    focus_package_id: int | None = None,
    theater_grid_rows: float = DEFAULT_THEATER_GRID_ROWS,
    ini_grid_offset_x: float = DEFAULT_INI_GRID_OFFSET_X,
    ini_grid_offset_y: float = DEFAULT_INI_GRID_OFFSET_Y,
    mission_context: dict[str, Any] | None = None,
    object_catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    deltas = objective_delta_map(cam_decode)
    deltas_by_key = objective_delta_key_map(cam_decode)
    unit_index = build_unit_index(cam_decode)
    mentions = deck_package_mentions(briefing_data)
    clock = cam_decode.get("campaign_clock")
    bullseye = normalize_bullseye(cam_decode)
    teams = {team.get("who"): team.get("name") for team in cam_decode.get("teams", [])}
    teams_by_id = {safe_int(team.get("who"), -1): team for team in cam_decode.get("teams", [])}
    ini = briefing_data.get("ini") or {}
    planning_points = normalized_planning_points(ini, ini_grid_offset_x, ini_grid_offset_y)
    l16_by_number = l16_records_by_flight_number(briefing_data)
    fmap, fmap_path, fmap_error = load_fmap_from_briefing_data(briefing_data)
    context_by_package = mission_context_by_package(mission_context or {})
    airbase_objectives = build_airbase_objective_refs(
        objectives,
        object_catalog or {},
        ini_grid_offset_x,
        ini_grid_offset_y,
    )
    flights_by_package: dict[str, list[dict[str, Any]]] = defaultdict(list)
    flights_by_vu_key: dict[str, dict[str, Any]] = {}
    for flight in cam_decode.get("flights", []):
        flights_by_package[flight.get("package_id", {}).get("key")].append(flight)
        flight_key = flight.get("id", {}).get("key")
        if flight_key:
            flights_by_vu_key[flight_key] = flight

    package_summaries: list[dict[str, Any]] = []
    for package in cam_decode.get("packages", []):
        key = package.get("id", {}).get("key")
        flights = sorted(flights_by_package.get(key, []), key=lambda item: package_flight_order(package, item))
        if not flights:
            continue
        target_refs: list[dict[str, Any]] = []
        for flight in flights:
            target_refs.extend(flight_targets(flight, objectives, deltas, deltas_by_key, unit_index, tactical_only=True))
        target_refs = unique_preserve(target_refs)
        mission_counter = Counter(flight.get("mission_short") for flight in flights if flight.get("mission_short"))
        package_id = int(package.get("camp_id") or 0)
        package_context = context_by_package.get(package_id, {})
        contract_by_callsign = context_contract_map(package_context)
        attach_plan = focus_package_id is None or package_id == focus_package_id or package_id in mentions
        package_planning_points = planning_points if attach_plan else []
        flight_summaries: list[dict[str, Any]] = []
        for flight in flights:
            key_waypoints = waypoint_summary(
                flight,
                clock,
                objectives,
                deltas,
                deltas_by_key,
                unit_index,
                airbase_objectives,
            )
            aircraft_type, aircraft_class = aircraft_label_for_unit(flight, object_catalog or {})
            weapon_info = weapons_summary(flight, object_catalog or {})
            flight_summary = {
                "camp_id": flight.get("camp_id"),
                "vu_id": flight.get("id"),
                "callsign": flight.get("callsign"),
                "mission": flight.get("mission_short"),
                "owner": flight.get("owner"),
                "team": teams.get(flight.get("owner")),
                "aircraft_count": flight.get("aircraft_count") or aircraft_count_from_roster(flight.get("roster")),
                "aircraft_type": aircraft_type,
                "aircraft_class": aircraft_class,
                "weapons": weapon_info,
                "weapons_summary": weapon_info["summary"],
                "laser_code_summary": laser_code_summary(flight),
                "takeoff_raw": next((wp.get("arrive") for wp in flight.get("waypoints", []) if wp.get("action_name") == "WP_TAKEOFF"), None),
                "takeoff_hhmm": format_clock(
                    next((wp.get("arrive") for wp in flight.get("waypoints", []) if wp.get("action_name") == "WP_TAKEOFF"), None),
                    clock,
                ),
                "tot_raw": flight.get("time_on_target"),
                "tot_hhmm": format_clock(flight.get("time_on_target"), clock),
                "tacan": flight.get("tacan", []),
                "tacan_summary": tacan_summary(flight.get("tacan", [])),
                "link16": correlate_l16_record(flight, l16_by_number),
                "target_refs": flight_targets(flight, objectives, deltas, deltas_by_key, unit_index, tactical_only=True),
                "key_waypoints": key_waypoints,
                "waypoint_count": len(flight.get("waypoints", [])),
            }
            plan_summary, plan_matches = flight_plan_summary(flight_summary, package_planning_points)
            flight_summary["plan_summary"] = plan_summary
            flight_summary["plan_matches"] = plan_matches
            contract = contract_by_callsign.get(str(flight_summary.get("callsign") or ""))
            if contract:
                flight_summary["human_contract"] = contract
                contract_name = contract.get("contract") or ""
                contract_intent = contract.get("intent") or ""
                contract_sector = contract.get("sector") or ""
                if contract_sector:
                    flight_summary["contract_summary"] = f"{contract_name}: {contract_sector} - {contract_intent}"
                else:
                    flight_summary["contract_summary"] = f"{contract_name}: {contract_intent}"
                flight_summary["target_description"] = contract_name
                flight_summary["remarks"] = contract_intent
            if not flight_summary.get("target_description"):
                flight_summary["target_description"] = brief_target_text(flight_summary.get("target_refs", []), limit=2)
            if not flight_summary.get("remarks"):
                flight_summary["remarks"] = flight_summary.get("plan_summary") or ""
            flight_summaries.append(flight_summary)

        plan_correlation = (
            correlate_package_plan(
                package_id,
                flight_summaries,
                package_planning_points,
                theater_grid_rows,
                ini_grid_offset_x,
                ini_grid_offset_y,
            )
            if attach_plan
            else {}
        )
        enemy_situation = (
            analyze_enemy_situation(
                {"package_id": package_id, "flights": flight_summaries},
                cam_decode,
                objectives,
                deltas,
                object_catalog or {},
                teams_by_id,
                plan_correlation,
                theater_grid_rows,
                ini_grid_offset_x,
                ini_grid_offset_y,
            )
            if attach_plan and object_catalog
            else {}
        )
        support_flights: list[dict[str, Any]] = []
        seen_support_keys: set[str] = set()
        for field, role in SUPPORT_ID_FIELDS:
            support_key = vu_key(package.get(field))
            if not support_key or support_key == "0:0" or support_key in seen_support_keys:
                continue
            support_raw = flights_by_vu_key.get(support_key)
            if not support_raw:
                continue
            seen_support_keys.add(support_key)
            support_flights.append(
                support_flight_summary(
                    role,
                    support_raw,
                    clock,
                    objectives,
                    deltas,
                    deltas_by_key,
                    unit_index,
                    teams,
                    object_catalog or {},
                    l16_by_number,
                    airbase_objectives,
                )
            )
        weather = package_weather_summary(fmap, fmap_path, fmap_error, flight_summaries, plan_correlation) if attach_plan else {}
        package_summaries.append(
            {
                "package_id": package_id,
                "vu_id": package.get("id"),
                "mission": (package.get("mission_request") or {}).get("mission_short"),
                "support_ids": {
                    field.removesuffix("_id"): package.get(field)
                    for field, _ in SUPPORT_ID_FIELDS
                    if package.get(field)
                },
                "deck_mentions": mentions.get(package_id, []),
                "score": package_score(package, flights, mentions),
                "flight_count": len(flights),
                "flight_missions": dict(mission_counter),
                "targets": target_refs,
                "flights": flight_summaries,
                "support_flights": support_flights,
                "weather": weather,
                "plan_correlation": plan_correlation,
                "plan_interpretation": plan_correlation.get("interpretation") if plan_correlation else None,
                "enemy_situation": enemy_situation,
                "human_context": package_context,
            }
        )

    package_summaries.sort(key=lambda item: (-item["score"], item["package_id"]))
    if focus_package_id is not None:
        package_summaries.sort(key=lambda item: (0 if item["package_id"] == focus_package_id else 1, -item["score"], item["package_id"]))
    mentioned_ids = sorted(mentions)
    present_ids = sorted({package["package_id"] for package in package_summaries if package["package_id"] in mentions})
    missing_ids = sorted(set(mentioned_ids) - set(present_ids))
    planning = {
        "ppts": ini.get("by_kind", {}).get("ppt", []),
        "targets": ini.get("by_kind", {}).get("target", []),
        "line_stpts": ini.get("by_kind", {}).get("linestpt", []),
        "transformed_points": planning_points,
        "grid_basis": {
            "feet_per_grid": FEET_PER_GRID,
            "theater_grid_rows": theater_grid_rows,
            "ini_grid_offset_x": ini_grid_offset_x,
            "ini_grid_offset_y": ini_grid_offset_y,
            "ini_to_campaign_grid": ini_grid_transform_basis(ini_grid_offset_x, ini_grid_offset_y),
        },
    }
    return {
        "prefix": briefing_data.get("prefix"),
        "focus_package_id": focus_package_id,
        "campaign_clock": clock,
        "bullseye": bullseye,
        "objective_source": {
            "count": len(objectives),
            "matched_deltas": sum(1 for objective_id in deltas if objective_id in objectives),
            "delta_count": len(deltas),
        },
        "unit_source": {
            "keyed_unit_refs": sum(len(items) for items in unit_index["by_key"].values()),
            "numeric_unit_refs": sum(len(items) for items in unit_index["by_num"].values()),
        },
        "unit_counts": cam_decode.get("unit_counts", {}),
        "object_catalog": {
            "object_dir": (object_catalog or {}).get("object_dir"),
            "ucd_count": len((object_catalog or {}).get("ucd") or {}),
            "ct_count": len((object_catalog or {}).get("ct") or {}),
            "vcd_count": len((object_catalog or {}).get("vcd_by_ct") or {}),
            "wcd_count": len((object_catalog or {}).get("wcd") or {}),
            "ocd_count": len((object_catalog or {}).get("ocd") or {}),
        },
        "weather_source": {
            "fmap_path": fmap_path,
            "available": fmap is not None,
            "error": fmap_error,
            "summary": fmap.summary() if fmap else None,
        },
        "l16_source": {
            "flight_count": len(l16_by_number),
            "correlation_basis": "Matched by CAM camp_id/name_id/VU num when possible.",
        },
        "mission_counts": cam_decode.get("mission_counts", {}),
        "mission_context": {
            key: value
            for key, value in (mission_context or {}).items()
            if key not in {"packages"}
        },
        "deck_package_mentions": mentions,
        "deck_package_status": {
            "mentioned": mentioned_ids,
            "present_in_cam": present_ids,
            "missing_from_cam": missing_ids,
        },
        "planning": planning,
        "packages": package_summaries,
    }


def brief_target_text(targets: list[dict[str, Any]], limit: int = 4) -> str:
    names = []
    for target in targets:
        kind = target.get("kind")
        name = target.get("display") or target.get("name")
        if not name:
            if kind == "unresolved":
                name = f"Unresolved target {target.get('camp_id')}"
            elif kind and kind != "objective":
                name = f"{str(kind).title()} {target.get('camp_id')}"
            else:
                name = f"Objective {target.get('camp_id')}"
        if name not in names:
            names.append(name)
    if not names:
        return "No named tactical target listed"
    suffix = "" if len(names) <= limit else f" +{len(names) - limit} more"
    return ", ".join(names[:limit]) + suffix


def markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("|", "/").strip()
    return text


def number_cell(value: Any, digits: int = 1) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return markdown_cell(value)


def weather_altitude_cell(value: Any, *, increment: int = 1000) -> str:
    if value is None:
        return ""
    try:
        altitude = float(value)
    except (TypeError, ValueError):
        return markdown_cell(value)
    if increment > 0:
        altitude = round(altitude / increment) * increment
    return f"{int(altitude):,} ft"


def target_ref_cell(target: dict[str, Any] | None) -> str:
    if not target:
        return ""
    name = target.get("display") or target.get("name") or ""
    kind = target.get("kind") or "target"
    camp_id = target.get("camp_id")
    if name and camp_id:
        return f"{name} ({kind} {camp_id})"
    if name:
        return f"{name} ({kind})"
    if camp_id:
        return f"{kind} {camp_id}"
    return str(kind)


def match_lookup(package: dict[str, Any]) -> dict[tuple[str, Any, str], dict[str, Any]]:
    lookup: dict[tuple[str, Any, str], dict[str, Any]] = {}
    correlation = package.get("plan_correlation") or {}
    for match in [*correlation.get("point_matches", []), *correlation.get("line_matches", [])]:
        key = (str(match.get("kind") or ""), match.get("index"), str(match.get("display") or ""))
        lookup[key] = match
    return lookup


def nearest_route_cell(match: dict[str, Any] | None) -> str:
    if not match:
        return ""
    route = match.get("nearest_route") or {}
    callsign = route.get("callsign") or ""
    action = route.get("action_short") or action_label(route.get("action"))
    waypoint_index = route.get("waypoint_index")
    time = route.get("arrive_hhmm") or ""
    bits = [str(item) for item in (callsign, action) if item]
    if waypoint_index is not None:
        bits.append(f"STPT {waypoint_index}")
    if time:
        bits.append(f"@ {time}")
    if match.get("distance_nm") is not None:
        bits.append(f"{match['distance_nm']} NM")
    return " ".join(bits)


def planning_point_by_label(synthesis: dict[str, Any], label: str) -> dict[str, Any] | None:
    wanted = str(label or "").strip().upper()
    if not wanted:
        return None
    for point in synthesis.get("planning", {}).get("transformed_points", []):
        point_label = str(point.get("display") or point.get("label") or "").strip().upper()
        if point_label == wanted:
            return point
    return None


def enemy_anchor_cell(unit: dict[str, Any]) -> str:
    anchor = unit.get("nearest_anchor") or {}
    label = str(anchor.get("label") or "").strip()
    time = str(anchor.get("time") or "").strip()
    if time and time not in label:
        return f"{label} @ {time}"
    return label


def player_enemy_summary(summary: str | None) -> str:
    if not summary:
        return ""
    parts = [part.strip() for part in str(summary).split(".") if part.strip()]
    visible_parts = []
    for part in parts:
        lower = part.lower()
        if "candidates filtered" in lower:
            continue
        visible_parts.append(
            part.replace("enemy non-air unit records", "enemy ground/naval units")
            .replace("strategic air-defense records", "strategic air-defense sites")
            .replace("enemy squadron bases", "enemy squadron base areas")
        )
    return ". ".join(visible_parts) + ("." if visible_parts else "")


def bearing_degrees_from_to(origin: dict[str, Any], point: dict[str, Any]) -> float | None:
    ox = origin.get("grid_x")
    oy = origin.get("grid_y")
    px = point.get("grid_x")
    py = point.get("grid_y")
    if ox is None or oy is None or px is None or py is None:
        return None
    dx = safe_float(px) - safe_float(ox)
    dy = safe_float(py) - safe_float(oy)
    if abs(dx) < 0.000001 and abs(dy) < 0.000001:
        return None
    return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0


def compass_sector(degrees: float | None) -> str:
    if degrees is None:
        return "unknown"
    sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return sectors[int((degrees + 22.5) // 45) % len(sectors)]


def bullseye_reference(synthesis: dict[str, Any], point: dict[str, Any] | None) -> str:
    bullseye = synthesis.get("bullseye") or {}
    if not bullseye or not point:
        return ""
    if point.get("grid_x") is None or point.get("grid_y") is None:
        return ""
    bearing = bearing_degrees_from_to(bullseye, point)
    if bearing is None:
        return "BE 000/0"
    distance_grid = math.hypot(
        safe_float(point.get("grid_x")) - safe_float(bullseye.get("grid_x")),
        safe_float(point.get("grid_y")) - safe_float(bullseye.get("grid_y")),
    )
    return f"BE {int(round(bearing)) % 360:03d}/{int(round(grid_distance_nm(distance_grid)))}"


def bullseye_brief_refs(synthesis: dict[str, Any], package: dict[str, Any], limit: int = 10) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for match in (package.get("plan_correlation") or {}).get("point_matches") or []:
        label = str(match.get("display") or match.get("label") or "").strip()
        grid = match.get("campaign_grid") or {}
        if not label or label.lower() in {"not set", "ini not set"} or grid.get("grid_x") is None or grid.get("grid_y") is None:
            continue
        if label.upper().startswith("TGT "):
            continue
        key = label.upper()
        if key in seen:
            continue
        seen.add(key)
        ref = bullseye_reference(synthesis, grid)
        if ref:
            refs.append(f"{label} {ref}")
        if len(refs) >= limit:
            break
    return refs


FIGHTER_AIRFRAME_TOKENS = (
    "mig-29",
    "mig-25",
    "mig-23",
    "mig-21",
    "mig-19",
    "j-6",
    "j-7",
    "su-27",
    "su-30",
)

STRIKE_AIRFRAME_TOKENS = (
    "q-5",
    "su-7",
    "su-17",
    "su-22",
    "il-28",
)


def split_aircraft_summary(summary: str) -> tuple[list[str], list[str]]:
    fighters: list[str] = []
    strike: list[str] = []
    for aircraft in [item.strip() for item in str(summary or "").split(";") if item.strip()]:
        lower = aircraft.lower()
        if any(token in lower for token in FIGHTER_AIRFRAME_TOKENS):
            if aircraft not in fighters:
                fighters.append(aircraft)
        elif any(token in lower for token in STRIKE_AIRFRAME_TOKENS):
            if aircraft not in strike:
                strike.append(aircraft)
    return fighters, strike


def airbase_origin_label(base: dict[str, Any]) -> str:
    name = str(base.get("name") or base.get("airbase_id") or "Enemy base").strip()
    distance = base.get("distance_nm")
    if distance is None:
        return name
    return f"{name} ({number_cell(distance, 1)} NM)"


def airbase_origin_label_distance(label: str) -> float:
    match = re.search(r"\(([\d.]+) NM\)", label)
    return safe_float(match.group(1), 9999.0) if match else 9999.0


def enemy_air_threat_axes(package: dict[str, Any]) -> list[dict[str, Any]]:
    enemy = package.get("enemy_situation") or {}
    axes: dict[str, dict[str, Any]] = {}
    for base in enemy.get("airbases") or []:
        anchor = base.get("nearest_anchor") or {}
        fighters, strike = split_aircraft_summary(str(base.get("aircraft_summary") or ""))
        if not fighters and not strike:
            continue
        sector = compass_sector(bearing_degrees_from_to(anchor, base))
        axis = axes.setdefault(
            sector,
            {
                "sector": sector,
                "fighter_types": [],
                "strike_types": [],
                "base_count": 0,
                "closest_distance_nm": None,
                "nearest_anchor": None,
                "origin_bases": [],
                "basis": [],
            },
        )
        axis["base_count"] += 1
        origin = airbase_origin_label(base)
        if origin not in axis["origin_bases"]:
            axis["origin_bases"].append(origin)
        distance = safe_float(base.get("distance_nm"), 9999.0)
        if axis["closest_distance_nm"] is None or distance < safe_float(axis["closest_distance_nm"], 9999.0):
            axis["closest_distance_nm"] = base.get("distance_nm")
            axis["nearest_anchor"] = enemy_anchor_cell(base)
        for aircraft in fighters:
            if aircraft not in axis["fighter_types"]:
                axis["fighter_types"].append(aircraft)
        for aircraft in strike:
            if aircraft not in axis["strike_types"]:
                axis["strike_types"].append(aircraft)
    return sorted(
        (
            {
                **axis,
                "origin_bases": sorted(axis.get("origin_bases") or [], key=airbase_origin_label_distance),
            }
            for axis in axes.values()
        ),
        key=lambda item: (safe_float(item.get("closest_distance_nm"), 9999.0), str(item.get("sector") or "")),
    )


def tracking_radar_cell(unit: dict[str, Any]) -> str:
    radar = unit.get("tracking_radar") or {}
    name = str(radar.get("vehicle_name") or "").strip()
    slot = radar.get("slot")
    current = radar.get("current_count")
    max_count = radar.get("max_count")
    if not name:
        reason = str(radar.get("reason") or "").strip()
        return reason or ""
    count = ""
    if current is not None:
        count = f", {current}/{max_count}" if max_count is not None else f", {current}"
    return f"{name} (slot {slot}{count})"


def active_cell(value: Any) -> str:
    return "yes" if bool(value) else "no"


def operational_cell(base: dict[str, Any]) -> str:
    percent = base.get("operational_percent")
    if percent is None:
        return "unknown"
    return f"{number_cell(percent, 0)}%"


def focus_package(synthesis: dict[str, Any]) -> dict[str, Any] | None:
    focus_id = synthesis.get("focus_package_id")
    if focus_id is None:
        return None
    return next((item for item in synthesis.get("packages", []) if item.get("package_id") == focus_id), None)


def hhmm_to_minutes(hhmm: Any) -> int | None:
    text = str(hhmm or "").strip()
    if len(text) < 4 or not text[:4].isdigit():
        return None
    hour = safe_int(text[:2], -1)
    minute = safe_int(text[2:4], -1)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def time_delta_minutes(a: Any, b: Any) -> int | None:
    minutes_a = hhmm_to_minutes(a)
    minutes_b = hhmm_to_minutes(b)
    if minutes_a is None or minutes_b is None:
        return None
    delta = abs(minutes_a - minutes_b)
    return min(delta, 1440 - delta)


def package_team_names(package: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for flight in package.get("flights", []):
        name = str(flight.get("team") or flight.get("owner") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def package_callsigns(package: dict[str, Any], limit: int = 4) -> str:
    callsigns = [
        str(flight.get("callsign") or f"Flight {flight.get('camp_id')}").strip()
        for flight in package.get("flights", [])
    ]
    callsigns = [callsign for callsign in callsigns if callsign]
    suffix = "" if len(callsigns) <= limit else f" +{len(callsigns) - limit} more"
    return ", ".join(callsigns[:limit]) + suffix


def package_mission_summary(package: dict[str, Any]) -> str:
    missions = package.get("flight_missions") or {}
    if missions:
        return ", ".join(f"{mission} x{count}" for mission, count in sorted(missions.items()))
    return str(package.get("mission") or "UNKNOWN")


def focus_relevance_anchors(package: dict[str, Any]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for flight in package.get("flights", []):
        for waypoint in flight.get("key_waypoints", []):
            if waypoint.get("action") not in THREAT_AREA_ACTIONS and waypoint.get("action") != "WP_REFUEL":
                continue
            if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
                continue
            anchors.append(
                {
                    "label": f"{flight.get('callsign')} {action_label(waypoint.get('action'))} STPT {waypoint.get('index')}",
                    "time": waypoint.get("arrive_hhmm"),
                    "grid_x": waypoint.get("grid_x"),
                    "grid_y": waypoint.get("grid_y"),
                }
            )
    for match in [*(package.get("plan_correlation") or {}).get("point_matches", []), *(package.get("plan_correlation") or {}).get("line_matches", [])]:
        grid = match.get("campaign_grid") or {}
        if grid.get("grid_x") is None or grid.get("grid_y") is None:
            continue
        anchors.append(
            {
                "label": f"INI {match.get('display')}",
                "time": (match.get("nearest_route") or {}).get("arrive_hhmm"),
                "grid_x": grid.get("grid_x"),
                "grid_y": grid.get("grid_y"),
            }
        )
    return anchors


def package_relevance_points(package: dict[str, Any]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for flight in package.get("flights", []):
        for waypoint in flight.get("key_waypoints", []):
            if waypoint.get("grid_x") is None or waypoint.get("grid_y") is None:
                continue
            action = waypoint.get("action")
            if action not in THREAT_AREA_ACTIONS and action not in {"WP_TANKER", "WP_ELINT", "WP_JAM", "WP_REFUEL"}:
                continue
            points.append(
                {
                    "callsign": flight.get("callsign"),
                    "mission": flight.get("mission"),
                    "action": action_label(action),
                    "time": waypoint.get("arrive_hhmm") or flight.get("tot_hhmm"),
                    "grid_x": waypoint.get("grid_x"),
                    "grid_y": waypoint.get("grid_y"),
                    "label": f"{flight.get('callsign')} {action_label(action)} STPT {waypoint.get('index')}",
                }
            )
    return points


def nearest_package_factor(
    package: dict[str, Any],
    anchors: list[dict[str, Any]],
) -> dict[str, Any] | None:
    points = package_relevance_points(package)
    if not points or not anchors:
        return None
    best: dict[str, Any] | None = None
    for point in points:
        for anchor in anchors:
            distance_grid = math.hypot(
                safe_float(point.get("grid_x")) - safe_float(anchor.get("grid_x")),
                safe_float(point.get("grid_y")) - safe_float(anchor.get("grid_y")),
            )
            distance_nm = grid_distance_nm(distance_grid)
            delta = time_delta_minutes(point.get("time"), anchor.get("time"))
            score = distance_nm + ((delta or 0) / 8.0)
            candidate = {
                "point": point,
                "anchor": anchor,
                "distance_nm": round(distance_nm, 1),
                "distance_grid": round(distance_grid, 1),
                "time_delta_min": delta,
                "score": score,
            }
            if best is None or candidate["score"] < best["score"]:
                best = candidate
    return best


def other_package_factor(package: dict[str, Any], focus: dict[str, Any], anchors: list[dict[str, Any]]) -> dict[str, Any] | None:
    nearest = nearest_package_factor(package, anchors)
    if not nearest:
        return None
    focus_teams = set(package_team_names(focus))
    package_teams = set(package_team_names(package))
    enemy_teams = set((focus.get("enemy_situation") or {}).get("enemy_teams") or [])
    relation = "enemy" if package_teams & enemy_teams else "friendly" if package_teams & focus_teams else "other"
    radius = OTHER_PACKAGE_ENEMY_RADIUS_NM if relation == "enemy" else OTHER_PACKAGE_FRIENDLY_RADIUS_NM
    time_delta = nearest.get("time_delta_min")
    if nearest["distance_nm"] > radius:
        return None
    if time_delta is not None and time_delta > OTHER_PACKAGE_TIME_WINDOW_MIN:
        return None

    point = nearest["point"]
    anchor = nearest["anchor"]
    if relation == "enemy":
        why = (
            f"Enemy {point.get('mission')} element near the player target/CAP area; "
            f"closest to {anchor.get('label')}."
        )
    elif relation == "friendly":
        why = (
            f"Friendly package close enough to matter for deconfliction; "
            f"closest to {anchor.get('label')}."
        )
    else:
        why = f"Non-player package close to {anchor.get('label')}."

    return {
        "package_id": package.get("package_id"),
        "relation": relation,
        "teams": ", ".join(package_team_names(package)),
        "missions": package_mission_summary(package),
        "callsigns": package_callsigns(package),
        "nearest_package_point": point.get("label"),
        "nearest_focus_anchor": anchor.get("label"),
        "distance_nm": nearest.get("distance_nm"),
        "time_delta_min": time_delta,
        "why": why,
    }


def other_package_factors(synthesis: dict[str, Any], focus: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    anchors = focus_relevance_anchors(focus)
    factors = []
    for package in synthesis.get("packages", []):
        if package.get("package_id") == focus.get("package_id"):
            continue
        factor = other_package_factor(package, focus, anchors)
        if factor:
            factors.append(factor)
    factors.sort(key=lambda item: (item.get("relation") != "enemy", safe_float(item.get("distance_nm")), safe_int(item.get("time_delta_min"), 9999)))
    return factors[:limit]


def weather_sample_text(sample: dict[str, Any]) -> str:
    cloud_base = weather_cloud_base_text(sample)
    contrail_text = weather_contrail_text(sample)
    return (
        f"{sample.get('condition')} {sample.get('cloud_cover')} {cloud_base}; "
        f"vis {number_cell(sample.get('visibility_km'), 1)} km; "
        f"temp {number_cell(sample.get('temperature_c'), 1)} C; "
        f"wind {sample.get('wind')}; con {contrail_text}"
    )


def weather_cloud_base_text(sample: dict[str, Any]) -> str:
    return weather_altitude_cell(sample.get("stratus_base_ft"))


def weather_contrail_text(sample: dict[str, Any]) -> str:
    return weather_altitude_cell(sample.get("contrail_layer_ft"))


def append_meteorology(lines: list[str], synthesis: dict[str, Any]) -> None:
    package = focus_package(synthesis)
    if not package:
        return
    weather = package.get("weather") or {}
    if not weather.get("available"):
        return

    lines.append("## Meteorology")
    lines.append("| Area | Local time | Day/Night | Conditions | Cloud base | Contrail layer | Temp C | Visibility km | Wind | Grid X | Grid Y |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for sample in weather.get("samples") or []:
        lines.append(
            "| {area} | {time} | {tod} | {conditions} | {cloud_base} | {contrail} | {temp} | {vis} | {wind} | {grid_x} | {grid_y} |".format(
                area=markdown_cell(sample.get("label")),
                time=markdown_cell(sample.get("time_hhmm")),
                tod=markdown_cell(sample.get("time_of_day")),
                conditions=markdown_cell(f"{sample.get('condition')} {sample.get('cloud_cover')}"),
                cloud_base=markdown_cell(weather_cloud_base_text(sample)),
                contrail=markdown_cell(weather_contrail_text(sample)),
                temp=number_cell(sample.get("temperature_c"), 1),
                vis=number_cell(sample.get("visibility_km"), 1),
                wind=markdown_cell(sample.get("wind")),
                grid_x=number_cell(sample.get("grid_x"), 1),
                grid_y=number_cell(sample.get("grid_y"), 1),
            )
        )
    lines.append("")


def append_bullseye(lines: list[str], synthesis: dict[str, Any]) -> None:
    bullseye = synthesis.get("bullseye") or {}
    if bullseye.get("grid_x") is None or bullseye.get("grid_y") is None:
        return
    lines.append("## Bullseye")
    lines.append(f"- Bullseye: grid {number_cell(bullseye.get('grid_x'), 1)} / {number_cell(bullseye.get('grid_y'), 1)}")
    package = focus_package(synthesis)
    if package:
        refs = bullseye_brief_refs(synthesis, package)
        if refs:
            lines.append("- Named references: " + "; ".join(refs))
    lines.append("")


def package_support_summary(package: dict[str, Any]) -> str:
    support = package.get("support_flights") or []
    if not support:
        return "No AWACS/tanker support flight linked from package support IDs."
    return "; ".join(
        f"{item.get('role')}: {item.get('callsign')} ({item.get('aircraft_count')}x {item.get('aircraft_type') or item.get('mission')}, {item.get('station_summary')})"
        for item in support
    )


def append_friendly_package_composition(lines: list[str], package: dict[str, Any]) -> None:
    lines.append("### Friendly Package Composition")
    lines.append(f"- Support: {package_support_summary(package)}")
    lines.append("")
    lines.append("| C/S | Aircraft | Role | Weapons | Laser | TACAN | T/O | TOT | Target/Area | Remarks |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for flight in package.get("flights", []):
        aircraft = f"{flight.get('aircraft_count') or ''}x {flight.get('aircraft_type') or flight.get('aircraft_class') or ''}".strip()
        lines.append(
            "| {callsign} | {aircraft} | {mission} | {weapons} | {laser} | {tacan} | {takeoff} | {tot} | {target} | {remarks} |".format(
                callsign=markdown_cell(flight.get("callsign") or f"Flight {flight.get('camp_id')}"),
                aircraft=markdown_cell(aircraft),
                mission=markdown_cell(flight.get("mission")),
                weapons=markdown_cell(flight.get("weapons_summary")),
                laser=markdown_cell(flight.get("laser_code_summary")),
                tacan=markdown_cell(flight.get("tacan_summary")),
                takeoff=markdown_cell(flight.get("takeoff_hhmm")),
                tot=markdown_cell(flight.get("tot_hhmm")),
                target=markdown_cell(flight.get("target_description")),
                remarks=markdown_cell(flight.get("remarks")),
            )
        )
    lines.append("")


def append_support_assets(lines: list[str], package: dict[str, Any]) -> None:
    support = package.get("support_flights") or []
    if not support:
        return
    lines.append("### AWACS / Tanker Tracks")
    lines.append("| Role | C/S | Aircraft | TOT | Station / Track | TACAN | Weapons |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for item in support:
        aircraft = f"{item.get('aircraft_count') or ''}x {item.get('aircraft_type') or item.get('aircraft_class') or ''}".strip()
        lines.append(
            "| {role} | {callsign} | {aircraft} | {tot} | {station} | {tacan} | {weapons} |".format(
                role=markdown_cell(item.get("role")),
                callsign=markdown_cell(item.get("callsign")),
                aircraft=markdown_cell(aircraft),
                tot=markdown_cell(item.get("tot_hhmm")),
                station=markdown_cell(item.get("station_summary")),
                tacan=markdown_cell(item.get("tacan_summary")),
                weapons=markdown_cell(item.get("weapons_summary")),
            )
        )
    lines.append("")


def append_other_package_factors(lines: list[str], synthesis: dict[str, Any]) -> None:
    package = focus_package(synthesis)
    if not package:
        return
    factors = [factor for factor in other_package_factors(synthesis, package) if factor.get("relation") == "friendly"]
    lines.append("## Other Package Factors")
    if factors:
        lines.append(
            "Friendly non-player packages are only listed here when their tactical waypoints are close enough in "
            "space and time to require deconfliction or to materially affect the player package."
        )
        lines.append("")
        lines.append("| PKG | Teams | Missions | Callsigns | Closest point | Player anchor | Dist NM | Time delta | Why it matters |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for factor in factors:
            delta = factor.get("time_delta_min")
            delta_text = "" if delta is None else f"{delta} min"
            lines.append(
                "| {pkg} | {teams} | {missions} | {callsigns} | {point} | {anchor} | {distance} | {delta} | {why} |".format(
                    pkg=markdown_cell(factor.get("package_id")),
                    teams=markdown_cell(factor.get("teams")),
                    missions=markdown_cell(factor.get("missions")),
                    callsigns=markdown_cell(factor.get("callsigns")),
                    point=markdown_cell(factor.get("nearest_package_point")),
                    anchor=markdown_cell(factor.get("nearest_focus_anchor")),
                    distance=number_cell(factor.get("distance_nm"), 1),
                    delta=markdown_cell(delta_text),
                    why=markdown_cell(factor.get("why")),
                )
            )
        lines.append("")
    else:
        lines.append("- No additional friendly packages are expected to affect the target area.")
        lines.append("")

    axes = enemy_air_threat_axes(package)
    lines.append("## Enemy Air Threat Estimate")
    lines.append(
        "This section avoids enemy ATO/package tasking. It is based on active enemy squadron bases "
        "within the threat radius, known aircraft types, and bearing from those bases to the package/INI target-area anchors. "
        "Treat it as likely fighter threat axes, not a prediction of specific launches, callsigns, package IDs, or timings."
    )
    lines.append("")
    if not axes:
        lines.append("- No active enemy fighter-capable airbases were identified within the current airbase threat radius.")
        lines.append("")
    else:
        lines.append("| Possible source sector | Likely origin bases | Fighter-capable types | Other strike-capable types | Closest package area | Closest base range | Basis |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for axis in axes:
            basis = f"{axis.get('base_count')} active enemy squadron base(s) in sector; home-base location and aircraft capability only."
            lines.append(
                "| {sector} | {origins} | {fighters} | {strike} | {anchor} | {distance} NM | {basis} |".format(
                    sector=markdown_cell(axis.get("sector")),
                    origins=markdown_cell("; ".join(axis.get("origin_bases") or []) or "none identified"),
                    fighters=markdown_cell("; ".join(axis.get("fighter_types") or []) or "none identified"),
                    strike=markdown_cell("; ".join(axis.get("strike_types") or []) or "none identified"),
                    anchor=markdown_cell(axis.get("nearest_anchor")),
                    distance=number_cell(axis.get("closest_distance_nm"), 1),
                    basis=markdown_cell(basis),
                )
            )
        lines.append("")

    enemy = package.get("enemy_situation") or {}
    contacts = enemy.get("active_air_contacts") or []
    lines.append(f"### Active Air Contacts At Campaign Time")
    if not contacts:
        lines.append(
            f"- No airborne enemy contacts were resolved within or clearly vectoring into {number_cell(enemy.get('active_air_contact_radius_nm'), 0)} NM of the target-area anchors at campaign time."
        )
        lines.append("")
        return
    lines.append(
        "These are current-position contacts only. Callsigns and enemy package/tasking IDs are intentionally omitted; "
        "the brief only exposes aircraft type, rough sector, range, and the observed reason they matter."
    )
    lines.append("")
    lines.append("| Sector from AO | Aircraft | Capability | Count | Nearest area | Range | Basis |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for contact in contacts:
        lines.append(
            "| {sector} | {aircraft} | {capability} | {count} | {anchor} | {distance} NM | {basis} |".format(
                sector=markdown_cell(contact.get("sector")),
                aircraft=markdown_cell(contact.get("aircraft_type")),
                capability=markdown_cell(contact.get("capability")),
                count=markdown_cell(contact.get("aircraft_count")),
                anchor=markdown_cell(enemy_anchor_cell(contact)),
                distance=number_cell(contact.get("distance_nm"), 1),
                basis=markdown_cell(contact.get("basis")),
            )
        )
    lines.append("")


def append_friendly_surface_defense(lines: list[str], synthesis: dict[str, Any]) -> None:
    friendly_surface = (synthesis.get("mission_context") or {}).get("friendly_surface_defense") or {}
    if not friendly_surface:
        return
    label = str(friendly_surface.get("label") or "").strip()
    point = planning_point_by_label(synthesis, label)
    grid = (point or {}).get("campaign_grid") or {}
    name = friendly_surface.get("name") or "Friendly surface fallback"

    lines.append("## Friendly Surface Fallback")
    anchor = f"- Anchor: {markdown_cell(name)}"
    if label:
        anchor += f" (`{markdown_cell(label)}`)"
    lines.append(anchor)
    if grid.get("grid_x") is not None and grid.get("grid_y") is not None:
        lines.append(f"- Coordinates: grid {number_cell(grid.get('grid_x'), 1)} / {number_cell(grid.get('grid_y'), 1)}")
    if friendly_surface.get("description"):
        lines.append(f"- Description: {markdown_cell(friendly_surface.get('description'))}")
    if friendly_surface.get("intent"):
        lines.append(f"- Use: {markdown_cell(friendly_surface.get('intent'))}")
    lines.append("")


def l16_cell(record: dict[str, Any], key: str) -> str:
    if record.get("match_basis") == "unresolved":
        return ""
    value = record.get(key)
    if value is None:
        return ""
    return str(value)


def append_comm_ladder(lines: list[str], synthesis: dict[str, Any]) -> None:
    package = focus_package(synthesis)
    if not package:
        return
    lines.append("## Comm Ladder")
    lines.append("| Element | Role | TACAN | Laser | Link 16 STN | F2F | Mission | EW | Notes |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    elements = [
        *[
            {
                "element": flight.get("callsign"),
                "role": flight.get("mission"),
                "tacan": flight.get("tacan_summary"),
                "laser": flight.get("laser_code_summary"),
                "link16": flight.get("link16") or {},
                "notes": flight.get("contract_summary") or "",
            }
            for flight in package.get("flights", [])
        ],
        *[
            {
                "element": item.get("callsign"),
                "role": item.get("role"),
                "tacan": item.get("tacan_summary"),
                "laser": item.get("laser_code_summary"),
                "link16": item.get("link16") or {},
                "notes": item.get("station_summary") or "",
            }
            for item in package.get("support_flights", [])
        ],
    ]
    for item in elements:
        link16 = item.get("link16") or {}
        lines.append(
            "| {element} | {role} | {tacan} | {laser} | {stn} | {f2f} | {mission} | {ew} | {notes} |".format(
                element=markdown_cell(item.get("element")),
                role=markdown_cell(item.get("role")),
                tacan=markdown_cell(item.get("tacan")),
                laser=markdown_cell(item.get("laser")),
                stn=markdown_cell(l16_cell(link16, "stn_number")),
                f2f=markdown_cell(l16_cell(link16, "f2f_channel")),
                mission=markdown_cell(l16_cell(link16, "mission_channel")),
                ew=markdown_cell(l16_cell(link16, "ew_channel")),
                notes=markdown_cell(item.get("notes")),
            )
        )
    lines.append("")


def append_enemy_situation(lines: list[str], synthesis: dict[str, Any]) -> None:
    focus_id = synthesis.get("focus_package_id")
    if focus_id is None:
        return
    package = next((item for item in synthesis.get("packages", []) if item.get("package_id") == focus_id), None)
    if not package:
        return
    enemy = package.get("enemy_situation") or {}
    if not enemy:
        return

    lines.append("## Enemy Situation And Air Defense Estimate")
    lines.append(
        "Threats below are focused on the package route, CAP/SAD areas, and named data-cartridge anchors. "
        "Strategic air-defense rows only include enemy Air Defense class systems with active tracking radars."
    )
    lines.append(f"- Enemy teams considered: {', '.join(enemy.get('enemy_teams') or []) or 'none'}")
    summary = player_enemy_summary(enemy.get("summary"))
    if summary:
        lines.append(f"- Summary: {summary}")
    if enemy.get("airbase_summary"):
        lines.append(f"- Airbase threat: {enemy['airbase_summary']}")
    lines.append("")

    air_defenses = enemy.get("air_defenses") or []
    if air_defenses:
        lines.append("### Strategic Air Defense Units Near Package Route")
        lines.append("| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Nearest anchor | Dist NM | Air range | Low-alt range | Strength air/low |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for unit in air_defenses:
            lines.append(
                "| {camp_id} | {team} | {class_name} | {equipment} | {tracking_radar} | {grid_x} | {grid_y} | {anchor} | {distance} | {air_range} | {low_air_range} | {strength} |".format(
                    camp_id=markdown_cell(unit.get("camp_id")),
                    team=markdown_cell(unit.get("team")),
                    class_name=markdown_cell(unit.get("class_name")),
                    equipment=markdown_cell(unit.get("equipment")),
                    tracking_radar=markdown_cell(tracking_radar_cell(unit)),
                    grid_x=number_cell(unit.get("grid_x"), 1),
                    grid_y=number_cell(unit.get("grid_y"), 1),
                    anchor=markdown_cell(enemy_anchor_cell(unit)),
                    distance=number_cell(unit.get("distance_nm"), 1),
                    air_range=markdown_cell(unit.get("air_range")),
                    low_air_range=markdown_cell(unit.get("low_air_range")),
                    strength=markdown_cell(f"{unit.get('air_strength')}/{unit.get('low_air_strength')}"),
                )
            )
        lines.append("")

    airbases = enemy.get("airbases") or []
    if airbases:
        lines.append(f"### Enemy Squadron Bases Within {number_cell(enemy.get('airbase_radius_nm'), 0)} NM")
        lines.append("| Airbase ID | Name | Team | Active sqns | Aircraft | Operational | Grid X | Grid Y | Nearest anchor | Dist NM | Status |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for base in airbases:
            lines.append(
                "| {airbase_id} | {name} | {team} | {squadron_count} | {aircraft} | {operational} | {grid_x} | {grid_y} | {anchor} | {distance} | {status} |".format(
                    airbase_id=markdown_cell(base.get("airbase_id")),
                    name=markdown_cell(base.get("name")),
                    team=markdown_cell(base.get("team")),
                    squadron_count=markdown_cell(base.get("squadron_count")),
                    aircraft=markdown_cell(base.get("aircraft_summary")),
                    operational=markdown_cell(operational_cell(base)),
                    grid_x=number_cell(base.get("grid_x"), 1),
                    grid_y=number_cell(base.get("grid_y"), 1),
                    anchor=markdown_cell(enemy_anchor_cell(base)),
                    distance=number_cell(base.get("distance_nm"), 1),
                    status=markdown_cell(base.get("status")),
                )
            )
        lines.append("")

    nearby_units = enemy.get("closest_units") or []
    if nearby_units:
        lines.append("### Nearby Enemy Ground/Naval Units")
        lines.append("| ID | Team | Class | Category | Equipment | Grid X | Grid Y | Nearest anchor | Dist NM |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for unit in nearby_units:
            lines.append(
                "| {camp_id} | {team} | {class_name} | {category} | {equipment} | {grid_x} | {grid_y} | {anchor} | {distance} |".format(
                    camp_id=markdown_cell(unit.get("camp_id")),
                    team=markdown_cell(unit.get("team")),
                    class_name=markdown_cell(unit.get("class_name")),
                    category=markdown_cell(unit.get("category")),
                    equipment=markdown_cell(unit.get("equipment")),
                    grid_x=number_cell(unit.get("grid_x"), 1),
                    grid_y=number_cell(unit.get("grid_y"), 1),
                    anchor=markdown_cell(enemy_anchor_cell(unit)),
                    distance=number_cell(unit.get("distance_nm"), 1),
                )
            )
        lines.append("")


def append_location_appendix(lines: list[str], synthesis: dict[str, Any], *, include_raw_weather: bool = False) -> None:
    focus_id = synthesis.get("focus_package_id")
    if focus_id is None:
        return
    package = next((item for item in synthesis.get("packages", []) if item.get("package_id") == focus_id), None)
    if not package:
        return

    lines.append("## Coordinate Appendix")
    lines.append(
        "Location data is separated here so the main brief stays readable."
    )
    bullseye = synthesis.get("bullseye") or {}
    if bullseye.get("grid_x") is not None and bullseye.get("grid_y") is not None:
        lines.append(f"- Bullseye: grid {number_cell(bullseye.get('grid_x'), 1)} / {number_cell(bullseye.get('grid_y'), 1)}")
    lines.append("")
    lines.append(f"### PKG {focus_id} Flight Steerpoints")
    lines.append("| C/S | STPT | Action | Arrive | Grid X | Grid Y | Bullseye | Grid Z | Target/object |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for flight in package.get("flights", []):
        for waypoint in flight.get("key_waypoints", []):
            lines.append(
                "| {callsign} | {stpt} | {action} | {arrive} | {grid_x} | {grid_y} | {bullseye} | {grid_z} | {target} |".format(
                    callsign=markdown_cell(flight.get("callsign") or f"Flight {flight.get('camp_id')}"),
                    stpt=markdown_cell(waypoint.get("index")),
                    action=markdown_cell(action_label(waypoint.get("action"))),
                    arrive=markdown_cell(waypoint.get("arrive_hhmm")),
                    grid_x=number_cell(waypoint.get("grid_x"), 1),
                    grid_y=number_cell(waypoint.get("grid_y"), 1),
                    bullseye=markdown_cell(bullseye_reference(synthesis, waypoint)),
                    grid_z=number_cell(waypoint.get("grid_z"), 1),
                    target=markdown_cell(target_ref_cell(waypoint.get("target"))),
                )
            )
    lines.append("")

    support_flights = package.get("support_flights") or []
    if support_flights:
        lines.append("### Linked Support Flight Coordinates")
        lines.append("| Role | C/S | STPT | Action | Arrive | Grid X | Grid Y | Bullseye | Grid Z | Target/object |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for support in support_flights:
            for waypoint in support.get("key_waypoints", []):
                lines.append(
                    "| {role} | {callsign} | {stpt} | {action} | {arrive} | {grid_x} | {grid_y} | {bullseye} | {grid_z} | {target} |".format(
                        role=markdown_cell(support.get("role")),
                        callsign=markdown_cell(support.get("callsign")),
                        stpt=markdown_cell(waypoint.get("index")),
                        action=markdown_cell(action_label(waypoint.get("action"))),
                        arrive=markdown_cell(waypoint.get("arrive_hhmm")),
                        grid_x=number_cell(waypoint.get("grid_x"), 1),
                        grid_y=number_cell(waypoint.get("grid_y"), 1),
                        bullseye=markdown_cell(bullseye_reference(synthesis, waypoint)),
                        grid_z=number_cell(waypoint.get("grid_z"), 1),
                        target=markdown_cell(target_ref_cell(waypoint.get("target"))),
                    )
                )
        lines.append("")

    weather = package.get("weather") or {}
    if weather.get("available"):
        lines.append("### Weather Sample Coordinates")
        if include_raw_weather:
            lines.append("| Area | Time | FMAP Row | FMAP Col | Grid X | Grid Y | Conditions | Wind | Visibility km | Briefed cloud base | Raw cumulus field ft | Contrail |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        else:
            lines.append("| Area | Time | FMAP Row | FMAP Col | Grid X | Grid Y | Conditions | Wind | Visibility km | Cloud base | Contrail |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for sample in weather.get("samples") or []:
            row_values = {
                "area": markdown_cell(sample.get("label")),
                "time": markdown_cell(sample.get("time_hhmm")),
                "row": markdown_cell(sample.get("row")),
                "col": markdown_cell(sample.get("col")),
                "grid_x": number_cell(sample.get("grid_x"), 1),
                "grid_y": number_cell(sample.get("grid_y"), 1),
                "conditions": markdown_cell(f"{sample.get('condition')} {sample.get('cloud_cover')}"),
                "wind": markdown_cell(sample.get("wind")),
                "vis": number_cell(sample.get("visibility_km"), 1),
                "cloud_base": markdown_cell(weather_cloud_base_text(sample)),
                "raw_cloud_base": number_cell(sample.get("cumulus_base_ft"), 0),
                "contrail": markdown_cell(weather_contrail_text(sample)),
            }
            if include_raw_weather:
                lines.append(
                    "| {area} | {time} | {row} | {col} | {grid_x} | {grid_y} | {conditions} | {wind} | {vis} | {cloud_base} | {raw_cloud_base} | {contrail} |".format(
                        **row_values
                    )
                )
            else:
                lines.append(
                    "| {area} | {time} | {row} | {col} | {grid_x} | {grid_y} | {conditions} | {wind} | {vis} | {cloud_base} | {contrail} |".format(
                        **row_values
                    )
                )
        lines.append("")

    transformed_points = synthesis.get("planning", {}).get("transformed_points", [])
    if transformed_points:
        lookup = match_lookup(package)
        lines.append("### INI Planning Steerpoints")
        lines.append("| Kind | Label | Code | INI X ft | INI Y ft | Grid X | Grid Y | Bullseye | Nearest package route point |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for point in sorted(
            transformed_points,
            key=lambda item: (planning_kind_rank(item.get("kind")), item.get("index") or 0),
        ):
            key = (str(point.get("kind") or ""), point.get("index"), str(point.get("display") or ""))
            grid = point.get("campaign_grid") or {}
            lines.append(
                "| {kind} | {label} | {code} | {ini_x} | {ini_y} | {grid_x} | {grid_y} | {bullseye} | {nearest} |".format(
                    kind=markdown_cell(point.get("kind")),
                    label=markdown_cell(point.get("display") or point.get("label")),
                    code=markdown_cell(point.get("code")),
                    ini_x=number_cell(point.get("x"), 1),
                    ini_y=number_cell(point.get("y"), 1),
                    grid_x=number_cell(grid.get("grid_x"), 1),
                    grid_y=number_cell(grid.get("grid_y"), 1),
                    bullseye=markdown_cell(bullseye_reference(synthesis, grid)),
                    nearest=markdown_cell(nearest_route_cell(lookup.get(key))),
                )
            )
        lines.append("")

    enemy = package.get("enemy_situation") or {}
    air_defense_locations = enemy.get("air_defense_locations") or enemy.get("air_defenses") or []
    if air_defense_locations:
        lines.append("### Strategic Air Defense Coordinates")
        lines.append(
            "Air-defense rows use saved campaign battalion/unit grid coordinates and exclude embedded short-range point/base defenses. "
            "They are enemy strategic sites with active tracking radars."
        )
        lines.append("| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Bullseye | Nearest package/INI anchor | Dist NM | Air range | Low-alt range |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for unit in air_defense_locations:
            lines.append(
                "| {camp_id} | {team} | {class_name} | {equipment} | {tracking_radar} | {grid_x} | {grid_y} | {bullseye} | {anchor} | {distance} | {air_range} | {low_air_range} |".format(
                    camp_id=markdown_cell(unit.get("camp_id")),
                    team=markdown_cell(unit.get("team")),
                    class_name=markdown_cell(unit.get("class_name")),
                    equipment=markdown_cell(unit.get("equipment")),
                    tracking_radar=markdown_cell(tracking_radar_cell(unit)),
                    grid_x=number_cell(unit.get("grid_x"), 1),
                    grid_y=number_cell(unit.get("grid_y"), 1),
                    bullseye=markdown_cell(bullseye_reference(synthesis, unit)),
                    anchor=markdown_cell(enemy_anchor_cell(unit)),
                    distance=number_cell(unit.get("distance_nm"), 1),
                    air_range=markdown_cell(unit.get("air_range")),
                    low_air_range=markdown_cell(unit.get("low_air_range")),
                )
            )
        lines.append("")

    active_air_contacts = enemy.get("active_air_contacts") or []
    if active_air_contacts:
        lines.append("### Active Enemy Air Contact Coordinates")
        lines.append(
            "Rows use current campaign-time positions. Enemy callsigns and package IDs are omitted."
        )
        lines.append("| Sector | Aircraft | Capability | Count | Grid X | Grid Y | Bullseye | Alt ft | Nearest package/INI anchor | Dist NM | Basis |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for contact in active_air_contacts:
            lines.append(
                "| {sector} | {aircraft} | {capability} | {count} | {grid_x} | {grid_y} | {bullseye} | {altitude} | {anchor} | {distance} | {basis} |".format(
                    sector=markdown_cell(contact.get("sector")),
                    aircraft=markdown_cell(contact.get("aircraft_type")),
                    capability=markdown_cell(contact.get("capability")),
                    count=markdown_cell(contact.get("aircraft_count")),
                    grid_x=number_cell(contact.get("grid_x"), 1),
                    grid_y=number_cell(contact.get("grid_y"), 1),
                    bullseye=markdown_cell(bullseye_reference(synthesis, contact)),
                    altitude=number_cell(contact.get("altitude_ft"), 0),
                    anchor=markdown_cell(enemy_anchor_cell(contact)),
                    distance=number_cell(contact.get("distance_nm"), 1),
                    basis=markdown_cell(contact.get("basis")),
                )
            )
        lines.append("")

    airbase_locations = enemy.get("airbase_locations") or enemy.get("airbases") or []
    if airbase_locations:
        lines.append("### Enemy Airbase Coordinates")
        lines.append(
            "Airbase rows are enemy squadron base objectives with active squadron rosters, greater than 0 percent operational state, "
            f"and within {number_cell(enemy.get('airbase_radius_nm'), 0)} NM of package/INI anchors."
        )
        lines.append("| Airbase ID | Name | Objective class | Team | Active sqns | Aircraft | Operational | Grid X | Grid Y | Bullseye | Nearest package/INI anchor | Dist NM | Status |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for base in airbase_locations:
            lines.append(
                "| {airbase_id} | {name} | {objective_class} | {team} | {squadron_count} | {aircraft} | {operational} | {grid_x} | {grid_y} | {bullseye} | {anchor} | {distance} | {status} |".format(
                    airbase_id=markdown_cell(base.get("airbase_id")),
                    name=markdown_cell(base.get("name")),
                    objective_class=markdown_cell(base.get("objective_class")),
                    team=markdown_cell(base.get("team")),
                    squadron_count=markdown_cell(base.get("squadron_count")),
                    aircraft=markdown_cell(base.get("aircraft_summary")),
                    operational=markdown_cell(operational_cell(base)),
                    grid_x=number_cell(base.get("grid_x"), 1),
                    grid_y=number_cell(base.get("grid_y"), 1),
                    bullseye=markdown_cell(bullseye_reference(synthesis, base)),
                    anchor=markdown_cell(enemy_anchor_cell(base)),
                    distance=number_cell(base.get("distance_nm"), 1),
                    status=markdown_cell(base.get("status")),
                )
            )
        lines.append("")

    resolved_targets: dict[tuple[str, Any, str], dict[str, Any]] = {}
    for flight in package.get("flights", []):
        for target in flight.get("target_refs", []):
            resolved_targets[(str(target.get("kind") or ""), target.get("camp_id"), str(target.get("name") or target.get("display") or ""))] = target
        for waypoint in flight.get("key_waypoints", []):
            target = waypoint.get("target")
            if target:
                resolved_targets[(str(target.get("kind") or ""), target.get("camp_id"), str(target.get("name") or target.get("display") or ""))] = target
    if resolved_targets:
        lines.append("### Resolved Location Objects")
        lines.append("| Kind | ID | Name | Source X | Source Y | Source Z |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for target in sorted(resolved_targets.values(), key=lambda item: (str(item.get("kind") or ""), item.get("camp_id") or 0)):
            lines.append(
                "| {kind} | {camp_id} | {name} | {x} | {y} | {z} |".format(
                    kind=markdown_cell(target.get("kind")),
                    camp_id=markdown_cell(target.get("camp_id")),
                    name=markdown_cell(target.get("display") or target.get("name")),
                    x=number_cell(target.get("x"), 1),
                    y=number_cell(target.get("y"), 1),
                    z=number_cell(target.get("z"), 1),
                )
            )
        lines.append("")


def append_map_products(lines: list[str], synthesis: dict[str, Any]) -> None:
    focus_id = synthesis.get("focus_package_id")
    if focus_id is None:
        return
    package = focus_package(synthesis)
    lines.append("## Map Products")
    lines.append(f"- Full-route chart map: `package_{focus_id}_route_threat_map_skyvector.png`")
    lines.append(f"- Tactical target-area chart: `package_{focus_id}_target_area_zoom_skyvector.png`")
    lines.append(f"- Objective-area close-up chart: `package_{focus_id}_objective_area_zoom_skyvector.png`")
    lines.append(f"- Weather review chart: `package_{focus_id}_weather_map_skyvector.png`")
    if package:
        cap_contracts = (package.get("human_context") or {}).get("cap_contracts", [])
        cap_labels = [
            f"{item.get('area') or item.get('label')} ({item.get('label')})"
            for item in cap_contracts
            if item.get("area") or item.get("label")
        ]
        if cap_labels:
            lines.append(
                "- Close-up map note: objective-area charts preserve CAP anchors "
                + ", ".join(cap_labels)
                + " alongside the target and INI route geometry."
            )
    lines.append("")
    lines.append(f"![PKG {focus_id} objective-area zoom](package_{focus_id}_objective_area_zoom_skyvector.png)")
    lines.append("")


def write_markdown(synthesis: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# BMS Mission Briefing: {synthesis['prefix']}")
    lines.append("")

    append_meteorology(lines, synthesis)
    append_bullseye(lines, synthesis)

    lines.append("## Package Coordination")
    primary_package = focus_package(synthesis)
    packages_to_print = [primary_package] if primary_package else synthesis["packages"][:1]
    for package in [item for item in packages_to_print if item]:
        lines.append(
            f"### PKG {package['package_id']} - {package.get('mission') or 'UNKNOWN'} "
            f"({package['flight_count']} flights)"
        )
        lines.append(f"- Targets: {brief_target_text(package.get('targets', []))}")
        enemy = package.get("enemy_situation") or {}
        enemy_summary = player_enemy_summary(enemy.get("summary"))
        if enemy_summary:
            lines.append(f"- Enemy situation: {enemy_summary}")
        if package.get("plan_interpretation"):
            lines.append(f"- Data-cartridge plan: {package['plan_interpretation']}")
            correlation = package.get("plan_correlation") or {}
            close_points = [
                match
                for match in correlation.get("point_matches", [])
                if match.get("distance_grid") is not None
            ][:10]
            if close_points:
                point_text = "; ".join(
                    "{label} -> {action} {time} ({distance_nm} NM)".format(
                        label=match.get("display"),
                        action=(match.get("nearest_route") or {}).get("action_short"),
                        time=(match.get("nearest_route") or {}).get("arrive_hhmm") or "",
                        distance_nm=match.get("distance_nm"),
                    )
                    for match in close_points
                )
                lines.append(f"- Close planning marks: {point_text}")
            line_summary = correlation.get("line_summary") or {}
            if line_summary.get("interpretation"):
                lines.append(f"- Drawn-line read: {line_summary['interpretation']}")
        context = package.get("human_context") or {}
        if context:
            if context.get("briefing_read"):
                lines.append(f"- Commander context: {context['briefing_read']}")
            if context.get("route_note"):
                lines.append(f"- Route context: {context['route_note']}")
            if context.get("fallback_logic"):
                lines.append(f"- Fallback logic: {context['fallback_logic']}")
            contracts = context.get("sad_contracts", [])
            if contracts:
                lines.append(
                    "- SAD contracts: "
                    + "; ".join(
                        f"{item.get('callsign')}: {item.get('contract')} ({item.get('intent')})"
                        for item in contracts
                    )
                )
            cap_contracts = context.get("cap_contracts", [])
            if cap_contracts:
                lines.append(
                    "- CAP contracts: "
                    + "; ".join(
                        f"{item.get('callsign')}: {item.get('area') or item.get('label')} ({item.get('sector')}) - {item.get('intent')}"
                        for item in cap_contracts
                    )
                )
            opportunities = context.get("target_opportunities", [])
            if opportunities:
                lines.append(
                    "- Target opportunities: "
                    + "; ".join(
                        f"{item.get('label')} {item.get('name')}: {item.get('type')} - {item.get('intent')}"
                        for item in opportunities
                    )
                )
        lines.append("")
        if package.get("package_id") == synthesis.get("focus_package_id"):
            append_friendly_package_composition(lines, package)
            append_support_assets(lines, package)
        else:
            lines.append("| C/S | Team | Role | T/O | TOT | Targets | Planning mark | Human contract |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for flight in package["flights"]:
                lines.append(
                    "| {callsign} | {team} | {mission} | {takeoff} | {tot} | {targets} | {plan} | {contract} |".format(
                        callsign=flight.get("callsign") or f"Flight {flight.get('camp_id')}",
                        team=flight.get("team") or flight.get("owner"),
                        mission=flight.get("mission") or "",
                        takeoff=flight.get("takeoff_hhmm") or "",
                        tot=flight.get("tot_hhmm") or "",
                        targets=brief_target_text(flight.get("target_refs", []), limit=3),
                        plan=flight.get("plan_summary") or "",
                        contract=flight.get("contract_summary") or "",
                    )
                )
            lines.append("")

    append_friendly_surface_defense(lines, synthesis)
    append_other_package_factors(lines, synthesis)
    append_comm_ladder(lines, synthesis)
    append_enemy_situation(lines, synthesis)
    append_location_appendix(lines, synthesis, include_raw_weather=False)
    append_map_products(lines, synthesis)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_workup_meteorology(lines: list[str], synthesis: dict[str, Any]) -> None:
    package = focus_package(synthesis)
    if not package:
        return
    weather = package.get("weather") or {}
    lines.append("## Meteorology Workup")
    if not weather.get("available"):
        lines.append(f"- Weather data unavailable: {weather.get('error') or 'no FMAP data resolved'}.")
        lines.append("")
        return
    summary = weather.get("summary") or {}
    grid = summary.get("grid") or {}
    lines.append(
        f"- Source: `{weather.get('source')}` ({summary.get('layout')}, "
        f"{grid.get('rows')}x{grid.get('cols')} cells). Map wind {summary.get('map_wind')}."
    )
    lines.append(f"- Sampling basis: {weather.get('basis')}")
    counts = summary.get("weather_counts") or {}
    if counts:
        lines.append("- Theater mix: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    lines.append("")
    append_meteorology(lines, synthesis)


def write_workup_markdown(synthesis: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# BMS Briefing Workup: {synthesis['prefix']}")
    lines.append("")
    lines.append(
        "Internal transitional artifact for briefing iteration. Keep provenance, gaps, and correlation notes here; "
        "`generated_briefing.md` is the player-facing mission brief."
    )
    lines.append("")

    clock = synthesis.get("campaign_clock") or {}
    if clock:
        lines.append("## Timing Source")
        lines.append(
            f"- HHMM values use clock base `{clock.get('clock_base_hhmm')}` and campaign time `{clock.get('campaign_time_ms')}`."
        )
        lines.append("")

    status = synthesis.get("deck_package_status") or {}
    lines.append("## Reference Deck Package Check")
    lines.append(f"- Mentioned in deck: {', '.join(map(str, status.get('mentioned') or [])) or 'none'}")
    lines.append(f"- Present in local CAM: {', '.join(map(str, status.get('present_in_cam') or [])) or 'none'}")
    lines.append(f"- Missing from local CAM: {', '.join(map(str, status.get('missing_from_cam') or [])) or 'none'}")
    lines.append("")

    planning = synthesis.get("planning", {})
    ppts = planning.get("ppts", [])
    targets = planning.get("targets", [])
    line_stpts = planning.get("line_stpts", [])
    lines.append("## Operating Area Inputs")
    if ppts:
        lines.append("- PPT labels and rings: " + "; ".join(
            f"{point['index']} {point['label']}" + (f" ({point['radius_nm']} NM)" if point.get("radius_nm") else "")
            for point in ppts[:24]
        ))
    if line_stpts:
        lines.append(f"- Drawn line STPTs: {len(line_stpts)} points")
    named_targets = [
        point["label"].strip()
        for point in targets
        if point.get("label") and point["label"].strip().lower() != "not set"
    ]
    if named_targets:
        lines.append("- DTC target labels: " + "; ".join(named_targets[:24]))
    if planning.get("grid_basis"):
        lines.append(f"- INI grid transform: `{planning['grid_basis']['ini_to_campaign_grid']}`")
    lines.append("")

    append_workup_meteorology(lines, synthesis)
    append_bullseye(lines, synthesis)

    lines.append("## Package Correlation Workup")
    primary_package = focus_package(synthesis)
    packages_to_print = [primary_package] if primary_package else synthesis.get("packages", [])[:1]
    for package in [item for item in packages_to_print if item]:
        mention = "explicit request" if package.get("package_id") == synthesis.get("focus_package_id") else (
            "reference deck" if package.get("deck_mentions") else "score"
        )
        lines.append(
            f"### PKG {package['package_id']} - {package.get('mission') or 'UNKNOWN'} "
            f"({package['flight_count']} flights, selected by {mention})"
        )
        lines.append(f"- Targets: {brief_target_text(package.get('targets', []))}")
        enemy = package.get("enemy_situation") or {}
        if enemy.get("summary"):
            lines.append(f"- Enemy situation: {enemy['summary']}")
        if package.get("deck_mentions"):
            deck_refs = ", ".join(f"slide {item['slide']}: {item['title']}" for item in package["deck_mentions"])
            lines.append(f"- Reference deck mentions: {deck_refs}")
        if package.get("plan_interpretation"):
            lines.append(f"- INI plan correlation: {package['plan_interpretation']}")
        context = package.get("human_context") or {}
        if context:
            if context.get("briefing_read"):
                lines.append(f"- Commander context: {context['briefing_read']}")
            if context.get("route_note"):
                lines.append(f"- Route context: {context['route_note']}")
            if context.get("fallback_logic"):
                lines.append(f"- Fallback logic: {context['fallback_logic']}")
        lines.append("")

    l16 = synthesis.get("l16_source") or {}
    lines.append("## Comm Data Workup")
    lines.append(f"- Link 16 rows available: {l16.get('flight_count', 0)}.")
    lines.append(f"- Correlation basis: {l16.get('correlation_basis') or 'not recorded'}.")
    lines.append("- UHF/VHF preset channel decoding is not yet available from the campaign bundle.")
    lines.append("")

    append_friendly_surface_defense(lines, synthesis)
    append_other_package_factors(lines, synthesis)
    append_comm_ladder(lines, synthesis)
    append_enemy_situation(lines, synthesis)
    append_location_appendix(lines, synthesis, include_raw_weather=True)
    append_map_products(lines, synthesis)

    lines.append("## Review Items")
    lines.append("- Confirm package inclusion and tasking against the mission commander's intent.")
    lines.append("- Validate aircraft/loadout/laser/TACAN values against the BMS UI before publishing a live mission brief.")
    lines.append("- Validate inferred HHMM times against the BMS UI or human mission card before treating them as authoritative.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--briefing-data", required=True)
    parser.add_argument("--cam-decode", required=True)
    parser.add_argument("--camp-obj-data", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--focus-package", type=int)
    parser.add_argument("--theater-grid-rows", type=float, default=DEFAULT_THEATER_GRID_ROWS)
    parser.add_argument(
        "--feet-per-grid",
        type=float,
        default=None,
        help="Override INI/objective world-foot to campaign-grid scale. Default is BMS 4.38 real-life feet: 3280.84 ft/grid.",
    )
    parser.add_argument("--ini-grid-offset-x", type=float, default=DEFAULT_INI_GRID_OFFSET_X)
    parser.add_argument("--ini-grid-offset-y", type=float, default=DEFAULT_INI_GRID_OFFSET_Y)
    parser.add_argument("--mission-context")
    parser.add_argument("--object-dir")
    args = parser.parse_args()

    global FEET_PER_GRID
    if args.feet_per_grid is not None:
        FEET_PER_GRID = args.feet_per_grid

    briefing_data = load_json(Path(args.briefing_data))
    cam_decode = load_json(Path(args.cam_decode))
    objectives = load_objectives(Path(args.camp_obj_data))
    mission_context = load_mission_context(Path(args.mission_context)) if args.mission_context else {}
    object_catalog = load_object_catalog(Path(args.object_dir)) if args.object_dir else {}
    synthesis = synthesize(
        briefing_data,
        cam_decode,
        objectives,
        args.focus_package,
        args.theater_grid_rows,
        args.ini_grid_offset_x,
        args.ini_grid_offset_y,
        mission_context,
        object_catalog,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "briefing_synthesis.json").write_text(json.dumps(synthesis, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(synthesis, out_dir / "generated_briefing.md")
    write_workup_markdown(synthesis, out_dir / "briefing_workup.md")
    print(f"Wrote {out_dir / 'briefing_synthesis.json'}")
    print(f"Wrote {out_dir / 'generated_briefing.md'}")
    print(f"Wrote {out_dir / 'briefing_workup.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
