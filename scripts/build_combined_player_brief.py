#!/usr/bin/env python3
"""Build one player-facing BMS brief from package-specific synthesis files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import synthesize_bms_briefing as synth


RAW_TRANSCRIPT_PATTERNS = (
    r"\bOkay,\s+it's time to make another briefing\b",
    r"\blet me go over the plan\b",
    r"\bhold on,\s+let me\b",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_package(synthesis: dict[str, Any], package_id: int | None = None) -> dict[str, Any]:
    focus_id = package_id or int(synthesis.get("focus_package_id") or 0)
    for package in synthesis.get("packages") or []:
        if int(package.get("package_id") or 0) == focus_id:
            return package
    raise SystemExit(f"Package {focus_id} not found in {synthesis.get('prefix')} synthesis.")


def clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 380:
        return ""
    if any(re.search(pattern, text, re.I) for pattern in RAW_TRANSCRIPT_PATTERNS):
        return ""
    return text


def markdown_cell(value: Any) -> str:
    return synth.markdown_cell(value)


def number_cell(value: Any, digits: int = 1) -> str:
    return synth.number_cell(value, digits)


def operation_title(syntheses: list[dict[str, Any]], prefix: str) -> str:
    context = syntheses[0].get("mission_context") or {}
    event = clean_text(context.get("event")) or re.sub(r"\D+$", "", prefix)
    operation = clean_text(context.get("operation_name"))
    if operation:
        op = operation.title()
        if not op.lower().startswith("operation"):
            op = f"Operation {op}"
        return f"Event {event}: {op} Player Briefing" if event else f"{op} Player Briefing"
    return f"Event {event} Player Briefing" if event else f"BMS Mission Briefing: {prefix}"


def combined_synthesis(base: dict[str, Any], packages: list[dict[str, Any]]) -> dict[str, Any]:
    result = dict(base)
    result["focus_package_id"] = packages[0].get("package_id") if packages else base.get("focus_package_id")
    result["packages"] = packages
    return result


def package_target_summary(package: dict[str, Any]) -> str:
    targets = synth.brief_target_text(package.get("targets") or [])
    lowered = targets.lower()
    if targets and not lowered.startswith("no named") and "unresolved" not in lowered:
        return targets
    useful = [
        flight.get("target_description")
        for flight in package.get("flights") or []
        if clean_text(flight.get("target_description")) and "unresolved" not in str(flight.get("target_description")).lower()
    ]
    mission = clean_text(package.get("mission"))
    if mission:
        return f"{mission} target area per DTC/waypoint tasking"
    return "Tactical target area per DTC/waypoint tasking"


def mission_summary(packages: list[dict[str, Any]]) -> str:
    package_ids = ", ".join(str(package.get("package_id")) for package in packages)
    roles = sorted({str(flight.get("mission") or "").upper() for package in packages for flight in package.get("flights") or [] if flight.get("mission")})
    target_bits = [package_target_summary(package) for package in packages]
    return (
        f"Player packages {package_ids} are treated as one integrated operation. "
        f"Primary roles: {', '.join(roles) or 'package tasking'}; target focus: {'; '.join(target_bits)}."
    )


def append_game_plan(lines: list[str], packages: list[dict[str, Any]]) -> None:
    lines.append("## Game Plan")
    lines.append(mission_summary(packages))
    lines.append("")
    for package in packages:
        lines.append(f"### PKG {package.get('package_id')} - {package.get('mission') or 'Package'}")
        plan = clean_text(package.get("plan_interpretation"))
        target = package_target_summary(package)
        lines.append(f"- Target focus: {target}")
        if plan:
            lines.append(f"- DTC/route read: {plan}")
        context = package.get("human_context") or {}
        for key, label in (
            ("route_note", "Route"),
            ("fallback_logic", "Fallback"),
            ("deconfliction", "Deconfliction"),
        ):
            item = clean_text(context.get(key))
            if item:
                lines.append(f"- {label}: {item}")
        contracts = []
        for contract in [*(context.get("sad_contracts") or []), *(context.get("strike_contracts") or []), *(context.get("cap_contracts") or [])]:
            if not isinstance(contract, dict):
                continue
            callsign = clean_text(contract.get("callsign"))
            task = clean_text(contract.get("contract") or contract.get("area") or contract.get("intent"))
            if callsign and task:
                contracts.append(f"{callsign}: {task}")
        if contracts:
            lines.append("- Planner contracts: " + "; ".join(contracts))
        lines.append("")


def fallback_a2a_tacan(package_index: int, flight_index: int) -> str:
    low = 15 + package_index * 10 + flight_index
    high = 78 + package_index * 10 + flight_index
    return f"{low}X / {high}X / {high}Y / {low}Y"


def flight_a2a_tacan(flight: dict[str, Any], package_index: int, flight_index: int) -> str:
    value = clean_text(flight.get("a2a_tacan_summary"))
    if value and value.lower() != "not assigned":
        return value
    return fallback_a2a_tacan(package_index, flight_index)


def player_tacan_cell(flight: dict[str, Any], package_index: int, flight_index: int) -> str:
    value = clean_text(flight.get("tacan_summary"))
    if value and value.lower() != "not assigned":
        return value
    return flight_a2a_tacan(flight, package_index, flight_index)


def append_package_composition(lines: list[str], packages: list[dict[str, Any]]) -> None:
    lines.append("## Friendly Package Composition")
    lines.append("| C/S | PKG | Aircraft | Role | Weapons | Laser | A-A TACAN | TACAN | T/O (Z) | TOT (Z) | Target/Area | Remarks |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for package_index, package in enumerate(packages):
        for flight_index, flight in enumerate(package.get("flights") or []):
            aircraft = f"{flight.get('aircraft_count') or ''}x {flight.get('aircraft_type') or flight.get('aircraft_class') or ''}".strip()
            target = clean_text(flight.get("target_description"))
            if not target or "unresolved" in target.lower() or target.lower().startswith("no named"):
                target = package_target_summary(package)
            lines.append(
                "| {callsign} | {pkg} | {aircraft} | {role} | {weapons} | {laser} | {a2a} | {tacan} | {takeoff} | {tot} | {target} | {remarks} |".format(
                    callsign=markdown_cell(flight.get("callsign") or f"Flight {flight.get('camp_id')}"),
                    pkg=markdown_cell(package.get("package_id")),
                    aircraft=markdown_cell(aircraft),
                    role=markdown_cell(flight.get("mission")),
                    weapons=markdown_cell(flight.get("weapons_summary")),
                    laser=markdown_cell(flight.get("laser_code_summary")),
                    a2a=markdown_cell(flight_a2a_tacan(flight, package_index, flight_index)),
                    tacan=markdown_cell(flight.get("tacan_summary")),
                    takeoff=markdown_cell(flight.get("takeoff_hhmm")),
                    tot=markdown_cell(flight.get("tot_hhmm")),
                    target=markdown_cell(target),
                    remarks=markdown_cell(flight.get("remarks")),
                )
            )
    lines.append("")


def append_combined_weather(lines: list[str], packages: list[dict[str, Any]]) -> None:
    samples: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for package in packages:
        weather = package.get("weather") or {}
        if weather.get("available"):
            samples.extend((package, sample) for sample in weather.get("samples") or [])
    if not samples:
        return
    lines.append("## Meteorology")
    lines.append("| Area | Local time | Day/Night | Conditions | Cloud base | Con layer | Temp | Visibility | Wind | Grid |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    seen: set[tuple[str, str, str, str]] = set()
    for package, sample in samples:
        key = (
            str(package.get("package_id")),
            str(sample.get("label")),
            str(round(float(sample.get("grid_x") or 0), 1)),
            str(round(float(sample.get("grid_y") or 0), 1)),
        )
        if key in seen:
            continue
        seen.add(key)
        area = f"PKG {package.get('package_id')} {sample.get('label')}"
        lines.append(
            "| {area} | {time} | {tod} | {conditions} | {cloud} | {con} | {temp} C | {vis} km | {wind} | {grid_x} / {grid_y} |".format(
                area=markdown_cell(area),
                time=markdown_cell(sample.get("time_hhmm")),
                tod=markdown_cell(sample.get("time_of_day")),
                conditions=markdown_cell(f"{sample.get('condition')} {sample.get('cloud_cover')}"),
                cloud=markdown_cell(synth.weather_cloud_base_text(sample)),
                con=markdown_cell(synth.weather_contrail_text(sample)),
                temp=number_cell(sample.get("temperature_c"), 1),
                vis=number_cell(sample.get("visibility_km"), 1),
                wind=markdown_cell(sample.get("wind")),
                grid_x=number_cell(sample.get("grid_x"), 1),
                grid_y=number_cell(sample.get("grid_y"), 1),
            )
        )
    lines.append("")


def append_combined_bullseye(lines: list[str], synthesis: dict[str, Any], packages: list[dict[str, Any]]) -> None:
    bullseye = synthesis.get("bullseye") or {}
    if bullseye.get("grid_x") is None or bullseye.get("grid_y") is None:
        return
    lines.append("## Bullseye")
    lines.append(f"- Bullseye: grid {number_cell(bullseye.get('grid_x'), 1)} / {number_cell(bullseye.get('grid_y'), 1)}")
    refs: list[str] = []
    for package in packages:
        refs.extend(synth.bullseye_brief_refs(synthesis, package))
    refs = list(dict.fromkeys(refs))
    if refs:
        lines.append("- Named references: " + "; ".join(refs[:16]))
    lines.append("")


def append_combined_support(lines: list[str], packages: list[dict[str, Any]]) -> None:
    support_rows = []
    seen: set[str] = set()
    for package in packages:
        for support in package.get("support_flights") or []:
            key = str(support.get("callsign") or support.get("camp_id"))
            if key in seen:
                continue
            seen.add(key)
            support_rows.append(support)
    if not support_rows:
        return
    lines.append("## AWACS / Tanker Tracks")
    lines.append("| Role | C/S | Aircraft | TOT (Z) | Station / Track | TACAN | Weapons |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for item in support_rows:
        aircraft = f"{item.get('aircraft_count') or ''}x {item.get('aircraft_type') or item.get('aircraft_class') or ''}".strip()
        station = clean_text(item.get("station_summary")) or synth.bullseye_reference({"bullseye": {}}, item)
        lines.append(
            "| {role} | {callsign} | {aircraft} | {tot} | {station} | {tacan} | {weapons} |".format(
                role=markdown_cell(item.get("role")),
                callsign=markdown_cell(item.get("callsign")),
                aircraft=markdown_cell(aircraft),
                tot=markdown_cell(item.get("tot_hhmm")),
                station=markdown_cell(station),
                tacan=markdown_cell(item.get("tacan_summary")),
                weapons=markdown_cell(item.get("weapons_summary")),
            )
        )
    lines.append("")


def append_combined_comm(lines: list[str], syntheses: list[dict[str, Any]], packages: list[dict[str, Any]]) -> None:
    frequencies: list[dict[str, str]] = []
    seen_nets: set[str] = set()
    for synthesis, package in zip(syntheses, packages):
        plan = synth.merge_comm_plan(synth.mission_comm_plan(synthesis), synth.derived_package_comm_plan(synthesis, package))
        for item in plan.get("frequencies") or []:
            net = str(item.get("net") or item.get("name") or "")
            key = f"{net}|{item.get('frequency')}"
            if key not in seen_nets:
                seen_nets.add(key)
                frequencies.append(item)
    comm_plan = {
        "frequencies": frequencies,
        "check_in": [
            {"step": "Package check-in", "call": "Package tactical", "notes": "Check flight status, fuel, sensors, and timing before push."},
            {"step": "Picture", "call": "ABM / AWACS", "notes": "Use bullseye references for cross-package air picture."},
        ],
        "priority": [
            "Knock-it-off / safety",
            "Spike, launch, defensive, and commit calls",
            "Target destroyed / unable / re-attack status",
            "Package push, abort, and retrograde calls",
        ],
    }
    lines.append("## Comm Ladder")
    synth.append_radio_comm_plan(lines, comm_plan)
    lines.append("### Link 16 & Nets")
    lines.append("| Element | PKG | Role | TACAN | Laser | Link 16 STN | F2F | Mission | EW | Notes |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for package_index, package in enumerate(packages):
        for flight_index, flight in enumerate(package.get("flights") or []):
            link16 = flight.get("link16") or {}
            lines.append(
                "| {element} | {pkg} | {role} | {tacan} | {laser} | {stn} | {f2f} | {mission} | {ew} | {notes} |".format(
                    element=markdown_cell(flight.get("callsign")),
                    pkg=markdown_cell(package.get("package_id")),
                    role=markdown_cell(flight.get("mission")),
                    tacan=markdown_cell(player_tacan_cell(flight, package_index, flight_index)),
                    laser=markdown_cell(flight.get("laser_code_summary")),
                    stn=markdown_cell(synth.l16_cell(link16, "stn_number")),
                    f2f=markdown_cell(synth.l16_cell(link16, "f2f_channel")),
                    mission=markdown_cell(synth.l16_cell(link16, "mission_channel")),
                    ew=markdown_cell(synth.l16_cell(link16, "ew_channel")),
                    notes=markdown_cell(flight.get("contract_summary") or ""),
                )
            )
    lines.append("")


def unique_by(items: list[dict[str, Any]], key_name: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get(key_name) or item.get("camp_id") or item.get("airbase_id") or json.dumps(item, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def append_combined_enemy(lines: list[str], packages: list[dict[str, Any]]) -> None:
    enemies = [package.get("enemy_situation") or {} for package in packages if package.get("enemy_situation")]
    if not enemies:
        return
    teams = sorted({team for enemy in enemies for team in enemy.get("enemy_teams") or []})
    air_defenses = unique_by([unit for enemy in enemies for unit in enemy.get("air_defenses") or []], "camp_id")
    airbases = unique_by([base for enemy in enemies for base in enemy.get("airbases") or []], "airbase_id")
    contacts = unique_by([contact for enemy in enemies for contact in enemy.get("active_air_contacts") or []], "camp_id")
    lines.append("## Enemy Situation And Air Defense Estimate")
    lines.append(
        "Threats are scoped to the combined player route, CAP/SAD areas, and named data-cartridge anchors. "
        "Strategic air-defense rows only include systems with active tracking radars."
    )
    lines.append(f"- Enemy teams considered: {', '.join(teams) or 'none'}")
    if air_defenses:
        lines.append(f"- Strategic ADA: {len(air_defenses)} radar-active strategic air-defense records inside the combined area.")
    if airbases:
        lines.append(f"- Enemy airbases: {len(airbases)} active enemy squadron base(s) inside the threat radius.")
    else:
        lines.append("- Enemy airbases: no active enemy squadron bases resolved inside the threat radius.")
    if contacts:
        lines.append(f"- Current airborne factor: {len(contacts)} active enemy air contact record(s) within or vectoring into the target area.")
    lines.append("")
    if air_defenses:
        lines.append("### Strategic Air Defense Units Near Package Route")
        lines.append("| ID | Team | Equipment | Tracking radar | Grid | Nearest anchor | Dist NM | Air range | Low-alt range |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for unit in air_defenses:
            lines.append(
                "| {id} | {team} | {equipment} | {radar} | {grid_x} / {grid_y} | {anchor} | {dist} | {air} | {low} |".format(
                    id=markdown_cell(unit.get("camp_id")),
                    team=markdown_cell(unit.get("team")),
                    equipment=markdown_cell(unit.get("equipment")),
                    radar=markdown_cell(synth.tracking_radar_cell(unit)),
                    grid_x=number_cell(unit.get("grid_x"), 1),
                    grid_y=number_cell(unit.get("grid_y"), 1),
                    anchor=markdown_cell(synth.enemy_anchor_cell(unit)),
                    dist=number_cell(unit.get("distance_nm"), 1),
                    air=markdown_cell(unit.get("air_range")),
                    low=markdown_cell(unit.get("low_air_range")),
                )
            )
        lines.append("")
    if airbases:
        lines.append("### Enemy Squadron Bases Within Threat Radius")
        lines.append("| Airbase | Team | Active sqns | Aircraft | Operational | Grid | Nearest anchor | Dist NM |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for base in airbases:
            lines.append(
                "| {name} | {team} | {sqns} | {aircraft} | {op} | {grid_x} / {grid_y} | {anchor} | {dist} |".format(
                    name=markdown_cell(base.get("name") or base.get("airbase_id")),
                    team=markdown_cell(base.get("team")),
                    sqns=markdown_cell(base.get("squadron_count")),
                    aircraft=markdown_cell(base.get("aircraft_summary")),
                    op=markdown_cell(synth.operational_cell(base)),
                    grid_x=number_cell(base.get("grid_x"), 1),
                    grid_y=number_cell(base.get("grid_y"), 1),
                    anchor=markdown_cell(synth.enemy_anchor_cell(base)),
                    dist=number_cell(base.get("distance_nm"), 1),
                )
            )
        lines.append("")
    if contacts:
        lines.append("### Active Air Contacts At Campaign Time")
        lines.append("Current-position contacts only; enemy callsigns and package/tasking IDs are intentionally omitted.")
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
                    anchor=markdown_cell(synth.enemy_anchor_cell(contact)),
                    distance=number_cell(contact.get("distance_nm"), 1),
                    basis=markdown_cell(contact.get("basis")),
                )
            )
        lines.append("")


def append_map_products(lines: list[str]) -> None:
    lines.append("## Map Products")
    lines.append("- `briefing_images/01_route_threat_map.png` - route/threat overview from player departure bases to the target area.")
    lines.append("- `briefing_images/02_target_area_map.png` - target-area flow, named anchors, enemy air axes, and strategic rings.")
    lines.append("- `briefing_images/03_objective_area_map.png` - close objective view for target prosecution details.")
    lines.append("- `briefing_images/04_weather_map.png` - weather overlay for the package AO when weather data is available.")
    lines.append("")


def append_coordinate_appendix(lines: list[str], synthesis: dict[str, Any], packages: list[dict[str, Any]]) -> None:
    lines.append("## Coordinate Appendix")
    lines.append("Location data is separated here so the main brief stays readable.")
    bullseye = synthesis.get("bullseye") or {}
    if bullseye.get("grid_x") is not None and bullseye.get("grid_y") is not None:
        lines.append(f"- Bullseye: grid {number_cell(bullseye.get('grid_x'), 1)} / {number_cell(bullseye.get('grid_y'), 1)}")
    lines.append("")
    for package in packages:
        lines.append(f"### PKG {package.get('package_id')} Flight Steerpoints")
        lines.append("| C/S | STPT | Action | Arrive (Z) | Grid | Bullseye | Alt/Grid Z | Target/object |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for flight in package.get("flights") or []:
            for waypoint in flight.get("key_waypoints") or []:
                target = synth.target_ref_cell(waypoint.get("target"))
                if "unresolved" in str(target).lower():
                    target = ""
                lines.append(
                    "| {callsign} | {stpt} | {action} | {arrive} | {grid_x} / {grid_y} | {be} | {z} | {target} |".format(
                        callsign=markdown_cell(flight.get("callsign")),
                        stpt=markdown_cell(waypoint.get("index")),
                        action=markdown_cell(synth.action_label(waypoint.get("action"))),
                        arrive=markdown_cell(waypoint.get("arrive_hhmm")),
                        grid_x=number_cell(waypoint.get("grid_x"), 1),
                        grid_y=number_cell(waypoint.get("grid_y"), 1),
                        be=markdown_cell(synth.bullseye_reference(synthesis, waypoint)),
                        z=number_cell(waypoint.get("grid_z"), 1),
                        target=markdown_cell(target),
                    )
                )
        lines.append("")


def build_brief(syntheses: list[dict[str, Any]], package_ids: list[int], out_path: Path) -> None:
    packages = [selected_package(synthesis, package_id) for synthesis, package_id in zip(syntheses, package_ids)]
    root = combined_synthesis(syntheses[0], packages)
    lines: list[str] = [f"# {operation_title(syntheses, root.get('prefix') or 'mission')}", ""]
    append_game_plan(lines, packages)
    append_package_composition(lines, packages)
    append_combined_weather(lines, packages)
    append_combined_bullseye(lines, root, packages)
    append_combined_support(lines, packages)
    append_combined_comm(lines, syntheses, packages)
    append_combined_enemy(lines, packages)
    append_map_products(lines)
    append_coordinate_appendix(lines, root, packages)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, action="append", required=True, help="Package synthesis path. Repeat in package order.")
    parser.add_argument("--package-id", type=int, action="append", required=True, help="Package ID matching each synthesis. Repeat in package order.")
    parser.add_argument("--out", type=Path, required=True, help="Combined player-facing markdown output.")
    parser.add_argument("--copy-to", type=Path, action="append", default=[], help="Additional path to copy the same markdown to.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.package_id) != len(args.synthesis):
        raise SystemExit("Pass one --package-id per --synthesis.")
    syntheses = [load_json(path) for path in args.synthesis]
    build_brief(syntheses, args.package_id, args.out)
    content = args.out.read_text(encoding="utf-8")
    for target in args.copy_to:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(target)
    print(args.out)


if __name__ == "__main__":
    main()
