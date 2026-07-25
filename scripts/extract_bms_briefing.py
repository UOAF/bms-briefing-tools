#!/usr/bin/env python3
"""Extract repeatable briefing inputs from Falcon BMS campaign sidecars."""

from __future__ import annotations

import argparse
import html
import json
import re
import struct
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


FEET_PER_NM = 6076.11549


@dataclass
class PlanningPoint:
    kind: str
    index: int
    x: float
    y: float
    z: float
    code: int | None
    label: str
    radius_ft: float | None = None
    radius_nm: float | None = None


class GoogleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = normalize_text(data)
        if text:
            self.parts.append(text)


def normalize_text(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\xa0", " ").replace("\u200b", "")
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def int32_head(path: Path, count: int = 8) -> list[int]:
    data = path.read_bytes()
    values = []
    for idx in range(min(count, len(data) // 4)):
        values.append(struct.unpack_from("<i", data, idx * 4)[0])
    return values


def int32_values(data: bytes, offset: int = 0, count: int = 4) -> list[int]:
    values = []
    available = max(0, len(data) - offset)
    for idx in range(min(count, available // 4)):
        values.append(struct.unpack_from("<i", data, offset + idx * 4)[0])
    return values


def ascii_preview(data: bytes) -> str:
    return "".join(chr(value) if 32 <= value <= 126 else "." for value in data)


def file_inventory(campaign_dir: Path, prefix: str) -> dict[str, Any]:
    inventory: dict[str, Any] = {}
    for path in sorted(campaign_dir.glob(f"{prefix}.*")):
        suffix = path.name[len(prefix) :]
        inventory[suffix] = {
            "path": str(path),
            "size": path.stat().st_size,
            "int32_head": int32_head(path),
        }
    return inventory


def parse_cam_container(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    result: dict[str, Any] = {
        "path": str(path),
        "size": len(data),
        "director_offset": None,
        "declared_file_count": None,
        "entry_count": 0,
        "entries": [],
        "errors": [],
    }
    if len(data) < 8:
        result["errors"].append("File is too small to contain a BMS save directory.")
        return result

    director_offset = struct.unpack_from("<I", data, 0)[0]
    result["director_offset"] = director_offset
    if director_offset > len(data) - 4:
        result["errors"].append("Director offset points outside the file.")
        return result

    declared_file_count = struct.unpack_from("<I", data, director_offset)[0]
    entry_count = min(declared_file_count, 12)
    result["declared_file_count"] = declared_file_count
    result["entry_count"] = entry_count
    if declared_file_count > 12:
        result["errors"].append("Embedded file count was capped at 12, matching Mission Commander behavior.")

    pos = director_offset + 4
    payload_end = 0
    save_version = None
    for index in range(entry_count):
        if pos >= len(data):
            result["errors"].append(f"Directory ended before entry {index}.")
            break
        name_len = data[pos]
        pos += 1
        if pos + name_len + 8 > len(data):
            result["errors"].append(f"Directory entry {index} is truncated.")
            break

        name = data[pos : pos + name_len].decode("cp1252", errors="replace")
        pos += name_len
        offset, size = struct.unpack_from("<II", data, pos)
        pos += 8
        end = offset + size
        head = data[offset : min(end, offset + 32)] if offset < len(data) else b""
        extension = Path(name).suffix.lower()
        entry: dict[str, Any] = {
            "index": index,
            "name": name,
            "extension": extension,
            "offset": offset,
            "size": size,
            "end": end,
            "within_bounds": end <= len(data),
            "head_hex": head.hex(" "),
            "head_ascii": ascii_preview(head),
            "head_int32": int32_values(head),
        }
        if extension == ".ver":
            version = data[offset:end].decode("ascii", errors="replace").strip()
            entry["version_text"] = version
            save_version = version
        elif extension == ".cmp" and size >= 8:
            entry["campaign_header"] = {
                "first_int32": struct.unpack_from("<i", data, offset)[0],
                "decompressed_size": struct.unpack_from("<i", data, offset + 4)[0],
            }
        elif extension in (".uni", ".obd") and size >= 10:
            entry["compressed_section_header"] = {
                "first_int32": struct.unpack_from("<i", data, offset)[0],
                "count_or_low_word": struct.unpack_from("<h", data, offset)[0],
                "second_int32": struct.unpack_from("<i", data, offset + 4)[0],
                "decompressed_size_candidate": struct.unpack_from("<i", data, offset + 6)[0],
            }
        result["entries"].append(entry)
        payload_end = max(payload_end, end)

    result["directory_end"] = pos
    result["directory_size"] = len(data) - director_offset
    result["payload_end"] = payload_end
    result["directory_matches_file_end"] = pos == len(data)
    result["save_version"] = save_version
    return result


def parse_point_line(kind: str, index: int, raw: str) -> PlanningPoint | None:
    parts = [part.strip() for part in raw.split(",", 4)]
    if kind == "linestpt":
        if len(parts) < 3:
            return None
        try:
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2])
        except ValueError:
            return None
        return PlanningPoint(kind, index, x, y, z, None, "")

    if len(parts) < 4:
        return None
    try:
        x = float(parts[0])
        y = float(parts[1])
        z = float(parts[2])
    except ValueError:
        return None

    label = parts[4].strip() if len(parts) >= 5 else ""
    if kind == "ppt":
        try:
            radius_ft = float(parts[3])
        except ValueError:
            radius_ft = None
        code = None
        radius_nm = round(radius_ft / FEET_PER_NM, 2) if radius_ft else None
        return PlanningPoint(kind, index, x, y, z, code, label, radius_ft, radius_nm)

    try:
        code = int(float(parts[3]))
    except ValueError:
        code = None
    return PlanningPoint(kind, index, x, y, z, code, label)


def is_nonempty_point(point: PlanningPoint) -> bool:
    if point.label and point.label.lower() != "not set":
        return True
    if any(abs(v) > 0.0001 for v in (point.x, point.y, point.z)):
        return True
    if point.code is not None and point.code != -1:
        return True
    if point.radius_ft is not None and point.radius_ft > 0.1:
        return True
    return False


def parse_ini(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"title": None, "points": []}
    point_re = re.compile(r"^(target|ppt|lineSTPT|wpntarget)_(\d+)=(.*)$", re.I)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("["):
            continue
        if line.lower().startswith("title="):
            result["title"] = line.split("=", 1)[1].strip()
            continue
        match = point_re.match(line)
        if not match:
            continue
        kind, index_raw, raw = match.groups()
        point = parse_point_line(kind.lower(), int(index_raw), raw)
        if point and is_nonempty_point(point):
            result["points"].append(asdict(point))

    by_kind: dict[str, list[dict[str, Any]]] = {}
    for point in result["points"]:
        by_kind.setdefault(point["kind"], []).append(point)
    result["by_kind"] = by_kind
    return result


def parse_key_values(block: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, raw_value in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z0-9_-]+)", block):
        if re.fullmatch(r"-?\d+", raw_value):
            values[key] = int(raw_value)
        else:
            values[key] = raw_value
    return values


def parse_l16(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    flights = [parse_key_values(match.group(1)) for match in re.finditer(r"flights\s*\{(.*?)\n\s*\}", text, re.S)]

    teams: list[dict[str, Any]] = []
    for team_block in re.finditer(r"teams\s*\{(.*?)\n\s*\}", text, re.S):
        block = team_block.group(1)
        team = parse_key_values(block)
        nets = [parse_key_values(net.group(1)) for net in re.finditer(r"nets\s*\{(.*?)\n\s*\}", block, re.S)]
        if nets:
            team["nets"] = nets
        teams.append(team)

    channel_counts: dict[str, int] = {}
    for flight in flights:
        for key in ("f2f_channel", "mission_channel", "ew_channel"):
            value = flight.get(key)
            channel_counts[f"{key}:{value}"] = channel_counts.get(f"{key}:{value}", 0) + 1

    return {
        "teams": teams,
        "flights": flights,
        "flight_count": len(flights),
        "channel_counts": channel_counts,
    }


def parse_twx(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    ints = []
    floats = []
    for idx in range(min(24, len(data) // 4)):
        ints.append(struct.unpack_from("<i", data, idx * 4)[0])
        floats.append(struct.unpack_from("<f", data, idx * 4)[0])
    return {
        "int32_head": ints,
        "float32_head": floats,
        "probable_header": {
            "version": ints[0] if len(ints) > 0 else None,
            "year": ints[1] if len(ints) > 1 else None,
            "month": ints[2] if len(ints) > 2 else None,
            "day": ints[3] if len(ints) > 3 else None,
        },
    }


def run_cam_decoder(cam_path: Path, bms_root: str, object_dir: str | None, output_path: Path) -> None:
    helper = Path(__file__).with_name("extract_bms_cam.ps1")
    if not helper.exists():
        raise FileNotFoundError(f"Missing CAM decoder helper: {helper}")

    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(helper),
        "-CamPath",
        str(cam_path),
        "-BmsRoot",
        bms_root,
        "-OutputPath",
        str(output_path),
    ]
    if object_dir:
        command.extend(["-ObjectDir", object_dir])
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"CAM decoder failed with exit code {result.returncode}: {detail}")


def summarize_cam_decode(path: Path) -> dict[str, Any]:
    decoded = json.loads(path.read_text(encoding="utf-8-sig"))
    flights = decoded.get("flights", [])
    packages = decoded.get("packages", [])
    squadrons = decoded.get("squadrons", [])
    objective_deltas = decoded.get("objective_deltas", [])
    mission_counts = decoded.get("mission_counts", {})
    team_names = [team.get("name") for team in decoded.get("teams", []) if team.get("name")]

    sample_flights = []
    for flight in flights[:20]:
        sample_flights.append(
            {
                "camp_id": flight.get("camp_id"),
                "callsign": flight.get("callsign"),
                "mission": flight.get("mission_short"),
                "package_camp_id": flight.get("package_camp_id"),
                "squadron_camp_id": flight.get("squadron_camp_id"),
                "time_on_target": flight.get("time_on_target"),
                "waypoint_count": len(flight.get("waypoints", [])),
            }
        )

    return {
        "path": str(path),
        "source": decoded.get("source", {}),
        "campaign_clock": decoded.get("campaign_clock"),
        "unit_counts": decoded.get("unit_counts", {}),
        "mission_counts": mission_counts,
        "teams": team_names,
        "flight_count": len(flights),
        "package_count": len(packages),
        "squadron_count": len(squadrons),
        "objective_delta_count": len(objective_deltas),
        "sample_flights": sample_flights,
    }


def htmlpresent_url(url: str) -> str:
    match = re.search(r"/presentation/d/([^/]+)", url)
    if not match:
        raise ValueError(f"Not a Google Slides presentation URL: {url}")
    return f"https://docs.google.com/presentation/d/{match.group(1)}/htmlpresent"


def fetch_deck(url: str) -> dict[str, Any]:
    html_url = htmlpresent_url(url)
    request = urllib.request.Request(html_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="replace")

    parser = GoogleTextParser()
    parser.feed(raw)
    slides: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    marker_re = re.compile(r"^#?\s*(\d+)\s+von\s*(\d+)$")

    for part in parser.parts:
        marker = marker_re.match(part)
        if marker:
            if current:
                slides.append(finalize_slide(current))
            current = {"number": int(marker.group(1)), "total": int(marker.group(2)), "lines": []}
            continue
        if current is not None:
            current["lines"].append(part)
    if current:
        slides.append(finalize_slide(current))

    relevant = [slide for slide in slides if is_relevant_slide(slide)]
    return {
        "source_url": url,
        "htmlpresent_url": html_url,
        "slide_count": len(slides),
        "slide_index": [
            {
                "number": slide["number"],
                "title": slide["title"],
                "line_count": len(slide["lines"]),
            }
            for slide in slides
        ],
        "relevant_slides": relevant,
    }


def finalize_slide(slide: dict[str, Any]) -> dict[str, Any]:
    lines = [line for line in slide["lines"] if line]
    title = ""
    for line in lines:
        if not re.fullmatch(r"\d+", line):
            title = line
            break
    slide["lines"] = lines
    slide["title"] = title
    return slide


def is_relevant_slide(slide: dict[str, Any]) -> bool:
    title = slide.get("title", "").lower()
    joined = "\n".join(slide.get("lines", [])).lower()
    needles = (
        "coordination",
        "friendly oob",
        "meteorology",
        "operating area",
        "game plan",
        "gameplan",
        "pkg ",
        "package ",
        "comm ladder",
    )
    return any(needle in title or needle in joined for needle in needles)


def build_summary(data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Briefing extraction: {data['prefix']}")
    lines.append("")
    lines.append("## Files")
    for suffix, info in data["files"].items():
        lines.append(f"- `{suffix}`: {info['size']} bytes, head int32={info['int32_head'][:4]}")

    cam = data.get("cam_container")
    if cam:
        lines.append("")
        lines.append("## CAM Container")
        lines.append(
            f"- Director offset: {cam['director_offset']} / file size {cam['size']} bytes"
        )
        lines.append(f"- Embedded files: {cam['entry_count']} declared={cam['declared_file_count']}")
        if cam.get("save_version"):
            lines.append(f"- Save version: `{cam['save_version']}`")
        for entry in cam.get("entries", []):
            header = ""
            if entry.get("version_text"):
                header = f", version `{entry['version_text']}`"
            elif entry.get("head_int32"):
                header = f", head int32={entry['head_int32'][:3]}"
            lines.append(
                f"- `{entry['name']}`: offset {entry['offset']}, size {entry['size']}{header}"
            )
        if cam.get("errors"):
            lines.append("- Parser notes: " + "; ".join(cam["errors"]))

    ini = data.get("ini")
    if ini:
        lines.append("")
        lines.append("## Planning Points")
        lines.append(f"- Title: `{ini.get('title')}`")
        for kind in ("target", "ppt", "linestpt", "wpntarget"):
            count = len(ini.get("by_kind", {}).get(kind, []))
            if count:
                lines.append(f"- {kind}: {count}")
        ppts = ini.get("by_kind", {}).get("ppt", [])
        if ppts:
            lines.append("")
            lines.append("### PPT Labels")
            for point in ppts[:30]:
                radius = point.get("radius_nm")
                radius_text = f", {radius} NM" if radius else ""
                lines.append(f"- {point['index']}: {point['label']}{radius_text}")

    l16 = data.get("l16")
    if l16:
        lines.append("")
        lines.append("## Link 16")
        lines.append(f"- Flights: {l16['flight_count']}")
        for key, count in sorted(l16["channel_counts"].items()):
            lines.append(f"- {key}: {count}")

    cam_decode = data.get("cam_decode")
    if cam_decode:
        lines.append("")
        lines.append("## CAM Decode")
        source = cam_decode.get("source", {})
        lines.append(f"- Full decode: `{cam_decode['path']}`")
        lines.append(f"- Save version: `{source.get('save_version')}`, class table entries: {source.get('class_table_entries')}")
        clock = cam_decode.get("campaign_clock")
        if clock:
            lines.append(
                "- Campaign clock: "
                f"campaign_time_ms={clock.get('campaign_time_ms')}, "
                f"clock_base={clock.get('clock_base_hhmm')}"
            )
        if cam_decode.get("objective_delta_count"):
            lines.append(f"- Objective deltas: {cam_decode['objective_delta_count']}")
        unit_counts = cam_decode.get("unit_counts", {})
        if unit_counts:
            counts = ", ".join(f"{key}={value}" for key, value in sorted(unit_counts.items()))
            lines.append(f"- Units: {counts}")
        if cam_decode.get("teams"):
            lines.append("- Teams: " + ", ".join(cam_decode["teams"]))
        mission_counts = cam_decode.get("mission_counts", {})
        if mission_counts:
            top_missions = sorted(mission_counts.items(), key=lambda item: item[1], reverse=True)[:12]
            lines.append("- Mission counts: " + ", ".join(f"{name}={count}" for name, count in top_missions))
        sample_flights = [flight for flight in cam_decode.get("sample_flights", []) if flight.get("callsign")]
        if sample_flights:
            lines.append("- Sample flights:")
            for flight in sample_flights[:8]:
                lines.append(
                    f"  - {flight['camp_id']}: {flight['callsign']} {flight['mission']} "
                    f"pkg={flight['package_camp_id']} wpts={flight['waypoint_count']}"
                )

    deck = data.get("deck")
    if deck:
        lines.append("")
        lines.append("## Deck")
        lines.append(f"- HTML view: {deck['htmlpresent_url']}")
        lines.append(f"- Slides indexed: {deck['slide_count']}")
        lines.append("- Relevant slides:")
        for slide in deck.get("relevant_slides", []):
            lines.append(f"  - {slide['number']}: {slide['title']}")

    lines.append("")
    lines.append("## Current Gap")
    lines.append(
        "The `.cam` container, teams, objective deltas, units, packages, flights, squadrons, "
        "missions, callsigns, package support IDs, flight loadouts, laser codes, TACAN values, "
        "and waypoints are now decoded. Remaining work is "
        "briefing synthesis: resolve objective names/base objective data, convert BMS campaign "
        "times into briefing times, identify the human-relevant packages, and infer tactics/intent."
    )
    return "\n".join(lines) + "\n"


def extract(args: argparse.Namespace) -> dict[str, Any]:
    campaign_dir = Path(args.campaign_dir)
    prefix = args.prefix
    data: dict[str, Any] = {
        "prefix": prefix,
        "campaign_dir": str(campaign_dir),
        "files": file_inventory(campaign_dir, prefix),
    }

    cam_path = campaign_dir / f"{prefix}.cam"
    if cam_path.exists():
        data["cam_container"] = parse_cam_container(cam_path)

    ini_path = campaign_dir / f"{prefix}.ini"
    if not ini_path.exists():
        ini_path = campaign_dir / f"{prefix.upper()}.ini"
    if ini_path.exists():
        data["ini"] = parse_ini(ini_path)

    l16_path = campaign_dir / f"{prefix}.l16.txtpb"
    if l16_path.exists():
        data["l16"] = parse_l16(l16_path)

    twx_path = campaign_dir / f"{prefix}.twx"
    if twx_path.exists():
        data["twx"] = parse_twx(twx_path)

    if args.deck_url:
        data["deck"] = fetch_deck(args.deck_url)

    return data


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-dir", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--deck-url")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--decode-cam",
        action="store_true",
        help=(
            "Decode embedded .tea/.uni sections through the legacy read-only BMSUtils compatibility path. "
            "Use for briefing extraction and decoder comparison only, not campaign write-back."
        ),
    )
    parser.add_argument("--bms-root", default=r"C:\Falcon BMS 4.38")
    parser.add_argument("--object-dir")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = extract(args)
    if args.decode_cam:
        cam_path = Path(args.campaign_dir) / f"{args.prefix}.cam"
        if not cam_path.exists():
            raise FileNotFoundError(f"Cannot decode missing CAM file: {cam_path}")
        cam_decode_path = out_dir / "cam_decode.json"
        run_cam_decoder(cam_path, args.bms_root, args.object_dir, cam_decode_path)
        data["cam_decode"] = summarize_cam_decode(cam_decode_path)

    (out_dir / "briefing_data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "briefing_summary.md").write_text(build_summary(data), encoding="utf-8")
    print(f"Wrote {out_dir / 'briefing_data.json'}")
    print(f"Wrote {out_dir / 'briefing_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
