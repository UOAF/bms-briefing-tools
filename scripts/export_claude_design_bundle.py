#!/usr/bin/env python3
"""Export a BMS briefing handoff bundle for Claude-based deck design."""

from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IMAGE_ROLE_HINTS = (
    ("enemy_air_threat", "enemy air-threat axis map"),
    ("objective_area", "objective-area close map"),
    ("target_area", "target-area tactical map"),
    ("route_threat", "package overview route/threat map"),
    ("weather", "weather review map"),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_slug(value: Any) -> str:
    text = str(value or "briefing").lower()
    chars = [char if char.isalnum() else "-" for char in text]
    return "-".join("".join(chars).split("-")).strip("-") or "briefing"


def find_package(synthesis: dict[str, Any], package_id: int | None) -> dict[str, Any]:
    packages = synthesis.get("packages") or []
    if not packages:
        raise SystemExit("Synthesis contains no packages.")
    if package_id is None:
        focus = synthesis.get("focus_package_id")
        package_id = int(focus) if focus is not None else int(packages[0].get("package_id") or 0)
    for package in packages:
        if int(package.get("package_id") or -1) == package_id:
            return package
    raise SystemExit(f"Package {package_id} not found in synthesis.")


def role_for_image(path: Path) -> str:
    stem = path.stem.lower()
    for token, role in IMAGE_ROLE_HINTS:
        if token in stem:
            return role
    return "supporting briefing image"


def default_image_paths(base_dir: Path, package_id: int) -> list[Path]:
    preferred = [
        base_dir / f"package_{package_id}_route_threat_map_skyvector.png",
        base_dir / f"package_{package_id}_target_area_zoom_skyvector.png",
        base_dir / f"package_{package_id}_objective_area_zoom_skyvector.png",
        base_dir / f"package_{package_id}_enemy_air_threat_axes_skyvector.png",
        base_dir / f"package_{package_id}_weather_map_skyvector.png",
    ]
    return [path for path in preferred if path.exists()]


def copy_asset(path: Path, assets_dir: Path) -> dict[str, Any]:
    target = assets_dir / path.name
    if path.resolve() != target.resolve():
        shutil.copy2(path, target)
    mime_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return {
        "name": target.name,
        "path": str(target.relative_to(assets_dir.parent)).replace("\\", "/"),
        "mime_type": mime_type,
        "size_bytes": target.stat().st_size,
        "role": role_for_image(target) if mime_type.startswith("image/") else "source document",
    }


def package_summary(package: dict[str, Any]) -> dict[str, Any]:
    flights = []
    for flight in package.get("flights") or []:
        flights.append(
            {
                "callsign": flight.get("callsign"),
                "mission": flight.get("mission"),
                "aircraft": f"{flight.get('aircraft_count') or ''}x {flight.get('aircraft_type') or flight.get('aircraft_class') or ''}".strip(),
                "takeoff": flight.get("takeoff_hhmm"),
                "tot": flight.get("tot_hhmm"),
                "target": flight.get("target_description"),
                "remarks": flight.get("remarks"),
            }
        )
    return {
        "package_id": package.get("package_id"),
        "mission": package.get("mission"),
        "flight_count": package.get("flight_count"),
        "flights": flights,
        "support": [
            {
                "role": item.get("role"),
                "callsign": item.get("callsign"),
                "aircraft": item.get("aircraft_type") or item.get("aircraft_class"),
                "station": item.get("station_summary"),
            }
            for item in package.get("support_flights") or []
        ],
    }


def build_design_prompt(manifest: dict[str, Any], template_text: str | None = None) -> str:
    package = manifest["package"]
    assets = manifest["assets"]
    image_lines = "\n".join(f"- `{asset['path']}`: {asset['role']}" for asset in assets if asset["mime_type"].startswith("image/"))
    template_section = f"\n## Design Template\n\n{template_text.strip()}\n" if template_text else ""
    return f"""# Claude Design Briefing Request

Create a polished, squadron-ready mission briefing deck from the uploaded BMS source bundle.

## Source Files

- `source/generated_briefing.md`: authoritative briefing content.
- `source/briefing_synthesis.json`: structured source of truth for package, flight, weather, threat, and coordinate data.
{image_lines}

## Package

- Package: {package.get('package_id')}
- Mission: {package.get('mission') or 'not decoded'}
- Flight count: {package.get('flight_count')}

## Design Intent

- Build the final briefing, not a process explainer.
- Use the generated markdown as authoritative, but rewrite for a human tactical briefing voice.
- Preserve operational facts: package composition, weather, comm ladder, mission plan, enemy situation, strategic ADA, active air contacts, enemy airbase threat axes, and coordinates only where helpful.
- Use the maps as first-class briefing visuals. The package overview should explain the route and support picture; the target/objective-area map should explain what is happening around Route Black and A/B/C/D/E/WCH/GRD/BAR.
- Do not expose decoded enemy callsigns, package IDs, or specific future enemy ATO tasking.
- Do not show friendly air defenses.
- Treat the old repo PPTX generator as deprecated fallback context only.

## Expected Output

- A downloadable PowerPoint `.pptx`.
- A concise slide list before file creation.
- Include map slides with readable labels and uncluttered callouts.
- Include a final appendix or backup slide for detailed coordinates if needed.
{template_section}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthesis", type=Path, required=True, help="Path to briefing_synthesis.json.")
    parser.add_argument("--briefing-md", type=Path, help="Path to generated_briefing.md. Defaults beside synthesis.")
    parser.add_argument("--package-id", type=int, help="Package ID. Defaults to synthesis focus package.")
    parser.add_argument("--image", action="append", type=Path, default=[], help="Image to include. May be repeated.")
    parser.add_argument("--template", type=Path, help="Optional markdown design-template instructions for Claude.")
    parser.add_argument("--out-dir", type=Path, help="Output bundle directory.")
    parser.add_argument(
        "--ready-for-claude",
        action="store_true",
        help="Required final-step acknowledgement. Export only after briefing text and map products have been reviewed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.ready_for_claude:
        raise SystemExit(
            "Claude design bundle export is a final opt-in step. Iterate on the briefing/maps first, then rerun with "
            "--ready-for-claude when the package is ready for deck production."
        )
    synthesis_path = args.synthesis.resolve()
    synthesis = load_json(synthesis_path)
    package = find_package(synthesis, args.package_id)
    package_id = int(package.get("package_id") or args.package_id or synthesis.get("focus_package_id") or 0)
    briefing_md = (args.briefing_md or (synthesis_path.parent / "generated_briefing.md")).resolve()
    if not briefing_md.exists():
        raise SystemExit(f"Missing briefing markdown: {briefing_md}")
    out_dir = args.out_dir or (synthesis_path.parent / f"claude_design_pkg_{package_id}")
    out_dir = out_dir.resolve()
    source_dir = out_dir / "source"
    assets_dir = out_dir / "assets"
    for managed_dir in (source_dir, assets_dir):
        if managed_dir.exists():
            shutil.rmtree(managed_dir)
    source_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(briefing_md, source_dir / "generated_briefing.md")
    shutil.copy2(synthesis_path, source_dir / "briefing_synthesis.json")

    image_paths = [path.resolve() for path in args.image]
    if not image_paths:
        image_paths = [path.resolve() for path in default_image_paths(synthesis_path.parent, package_id)]
    assets = [copy_asset(path, assets_dir) for path in image_paths if path.exists()]

    source_assets = [
        {
            "name": "generated_briefing.md",
            "path": "source/generated_briefing.md",
            "mime_type": "text/plain",
            "size_bytes": (source_dir / "generated_briefing.md").stat().st_size,
            "role": "authoritative markdown briefing",
        },
        {
            "name": "briefing_synthesis.json",
            "path": "source/briefing_synthesis.json",
            "mime_type": "text/plain",
            "size_bytes": (source_dir / "briefing_synthesis.json").stat().st_size,
            "role": "structured source data",
        },
    ]
    template_text = args.template.read_text(encoding="utf-8") if args.template else None
    manifest = {
        "schema": "uoaf.bms.claude_design_bundle.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "synthesis": str(synthesis_path),
            "briefing_md": str(briefing_md),
        },
        "package": package_summary(package),
        "assets": [*source_assets, *assets],
        "notes": [
            "This bundle is a final deck-production handoff after briefing text and map products have been reviewed.",
            "Upload all files in this directory to Claude or use scripts/upload_claude_design_bundle.py with ANTHROPIC_API_KEY only when ready to generate the final deck.",
            "Images should be placed before text in API message content where possible.",
        ],
    }
    prompt = build_design_prompt(manifest, template_text)
    manifest["prompt_file"] = "claude_design_prompt.md"
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out_dir / "claude_design_prompt.md").write_text(prompt + "\n", encoding="utf-8")
    print(out_dir)


if __name__ == "__main__":
    main()
