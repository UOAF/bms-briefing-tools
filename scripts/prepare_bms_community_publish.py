#!/usr/bin/env python3
"""Prepare a deterministic UOAF community-event publishing plan.

The script performs no network writes.  It inventories the exact mission files
that belong to a campaign prefix, extracts player-package rows from briefing
synthesis JSON, calculates the Discord timestamp, and writes the artifacts that
the BMS Briefing Planner skill uses for Drive/Sheets publishing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_mission_files(campaign_dir: Path, prefix: str) -> list[dict[str, Any]]:
    if not campaign_dir.is_dir():
        raise ValueError(f"Campaign directory does not exist: {campaign_dir}")

    prefix_folded = prefix.casefold()
    files = [
        path
        for path in campaign_dir.iterdir()
        if path.is_file()
        and (
            path.name.casefold() == prefix_folded
            or path.name.casefold().startswith(prefix_folded + ".")
        )
    ]
    files.sort(key=lambda path: path.name.casefold())
    if not files:
        raise ValueError(f"No files matching {prefix!r} were found in {campaign_dir}")
    if not any(path.name.casefold() == f"{prefix_folded}.ini" for path in files):
        raise ValueError(f"Required mission INI is missing: {prefix}.ini")

    return [
        {
            "name": path.name,
            "source_path": str(path.resolve()),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "is_ini": path.name.casefold() == f"{prefix_folded}.ini",
        }
        for path in files
    ]


def _package_by_id(synthesis: dict[str, Any], package_id: int) -> dict[str, Any] | None:
    for package in synthesis.get("packages", []):
        if int(package.get("package_id", -1)) == package_id:
            return package
    return None


def load_signup_packages(
    synthesis_paths: Iterable[Path], package_ids: list[int]
) -> list[dict[str, Any]]:
    syntheses: list[tuple[Path, dict[str, Any]]] = []
    for path in synthesis_paths:
        if not path.is_file():
            raise ValueError(f"Synthesis file does not exist: {path}")
        syntheses.append((path, json.loads(path.read_text(encoding="utf-8"))))

    requested_ids = list(dict.fromkeys(package_ids))
    if not requested_ids:
        requested_ids = [
            int(data["focus_package_id"])
            for _, data in syntheses
            if data.get("focus_package_id") is not None
        ]
        requested_ids = list(dict.fromkeys(requested_ids))

    packages: list[dict[str, Any]] = []
    for package_id in requested_ids:
        match: dict[str, Any] | None = None
        source_path: Path | None = None
        for path, synthesis in syntheses:
            candidate = _package_by_id(synthesis, package_id)
            if candidate is not None:
                match = candidate
                source_path = path
                break
        if match is None or source_path is None:
            raise ValueError(f"Package {package_id} was not found in the supplied synthesis files")

        flights = []
        for flight in match.get("flights", []):
            flights.append(
                {
                    "callsign": str(flight.get("callsign") or "").strip(),
                    "role": str(flight.get("mission") or "").strip(),
                    "aircraft_type": str(flight.get("aircraft_type") or "").strip(),
                    "seats": int(flight.get("aircraft_count") or 0),
                    "takeoff_z": str(flight.get("takeoff_hhmm") or "").strip(),
                    "tot_z": str(flight.get("tot_hhmm") or "").strip(),
                }
            )

        packages.append(
            {
                "package_id": package_id,
                "role": str(match.get("mission") or "").strip(),
                "flight_count": len(flights),
                "seat_count": sum(row["seats"] for row in flights),
                "flights": flights,
                "source_synthesis": str(source_path.resolve()),
            }
        )
    return packages


def parse_hhmm(value: str) -> time:
    match = re.fullmatch(r"(\d{1,2}):?(\d{2})(?:Z)?", value.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"Expected an HH:MM or HHMM time, got {value!r}")
    hour, minute = (int(part) for part in match.groups())
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time: {value!r}")
    return time(hour, minute, tzinfo=timezone.utc)


def discord_post(
    *,
    event_number: str,
    operation_name: str,
    event_date: date,
    briefing_time: time,
    theater: str,
    bms_version: str,
    objectives: str,
    marshal_time: time,
    signup_url: str | None,
) -> tuple[str, int, bool]:
    briefing_datetime = datetime.combine(event_date, briefing_time)
    timestamp = int(briefing_datetime.timestamp())
    date_label = f"{event_date.strftime('%A')}, {event_date.day} {event_date.strftime('%B')} {event_date.year}"
    signup_value = signup_url or "<SIGNUP_SHEET_URL>"
    objective_text = " ".join(objectives.split())
    text = (
        "@BMS Events\n"
        f"You are invited to UOAF BMS Event #{event_number}!\n"
        f"**{operation_name}**\n\n"
        f"When: {date_label}, <t:{timestamp}:t>\n"
        f"Theater: {theater}\n"
        f"Version: BMS {bms_version}\n\n"
        "Mission objectives:\n"
        f"{objective_text}\n\n"
        f"Marshal: {marshal_time.strftime('%H%M')}z. Briefing: {briefing_time.strftime('%H%M')}z.\n\n"
        "ALL INFORMATION (including Discord link, Briefing, INI file, and Theater) "
        "is available at the bottom of the RSVP link:\n"
        f"{signup_value}\n"
    )
    return text, timestamp, signup_url is not None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--synthesis", type=Path, action="append", default=[])
    parser.add_argument("--package-id", type=int, action="append", default=[])
    parser.add_argument("--event-number", required=True)
    parser.add_argument("--operation-name", required=True)
    parser.add_argument("--event-date", type=date.fromisoformat, required=True)
    parser.add_argument("--briefing-time", default="1800")
    parser.add_argument("--marshal-time", default="1745")
    parser.add_argument("--theater", required=True)
    parser.add_argument("--bms-version", required=True)
    parser.add_argument("--mission-objectives", required=True)
    parser.add_argument("--event-folder-url")
    parser.add_argument("--signup-url")
    parser.add_argument("--briefing-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        mission_files = discover_mission_files(args.campaign_dir.resolve(), args.prefix)
        packages = load_signup_packages(args.synthesis, args.package_id) if args.synthesis else []
        briefing_time = parse_hhmm(args.briefing_time)
        marshal_time = parse_hhmm(args.marshal_time)
        post, timestamp, ready_to_post = discord_post(
            event_number=args.event_number,
            operation_name=args.operation_name,
            event_date=args.event_date,
            briefing_time=briefing_time,
            theater=args.theater,
            bms_version=args.bms_version,
            objectives=args.mission_objectives,
            marshal_time=marshal_time,
            signup_url=args.signup_url,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ini_file = next(item for item in mission_files if item["is_ini"])
    plan = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "event": {
            "number": str(args.event_number),
            "operation_name": args.operation_name,
            "date": args.event_date.isoformat(),
            "marshal_time_z": marshal_time.strftime("%H%M"),
            "briefing_time_z": briefing_time.strftime("%H%M"),
            "discord_timestamp": timestamp,
            "theater": args.theater,
            "bms_version": args.bms_version,
            "mission_objectives": " ".join(args.mission_objectives.split()),
        },
        "destinations": {
            "event_folder_url": args.event_folder_url,
            "signup_url": args.signup_url,
            "briefing_url": args.briefing_url,
        },
        "mission_files": mission_files,
        "ini_file": ini_file,
        "signup_sheet": {
            "packages": packages,
            "clear_previous_pilot_signups": True,
            "reset_signup_checkboxes": True,
            "preserve_formatting_formulas_and_validation": True,
            "required_link_role": "anyone_with_link_writer",
        },
        "discord": {
            "ready_to_post": ready_to_post,
            "post_path": str((output_dir / "discord_post.txt").resolve()),
        },
        "completion_contract": [
            "Every mission file in mission_files is present in the event folder with the same name.",
            "The signup sheet is a native copy of the latest prior event template.",
            "Current flights, briefing link, INI link, and theater are verified in the copied sheet.",
            "Prior pilot names are blank and signup checkboxes are reset without damaging template controls.",
            "The signup sheet permission is verified as anyone-with-link writer.",
            "The returned Discord post uses the generated timestamp and the final signup URL.",
            "A current-event banner preserves the UOAF logo and uses subtle cinematic realism: credible terrain and target scale, with no neon weapons, HUD overlays, or oversized glowing ground targets.",
        ],
    }

    (output_dir / "community_publish_plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "discord_post.txt").write_text(post, encoding="utf-8")
    print(f"Prepared {len(mission_files)} mission files and {len(packages)} signup packages.")
    print(output_dir / "community_publish_plan.json")
    print(output_dir / "discord_post.txt")
    if not ready_to_post:
        print("Discord post contains <SIGNUP_SHEET_URL>; rerun after the sheet is created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
