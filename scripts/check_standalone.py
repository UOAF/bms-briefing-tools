#!/usr/bin/env python3
"""Check whether the standalone BMS briefing toolchain is ready to run."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from pyopencam_provider import record_loadouts


REQUIRED_IMPORTS = {
    "PIL": "Pillow",
    "pyproj": "pyproj",
}


def status(label: str, ok: bool, detail: str, warning: bool = False) -> bool:
    prefix = "OK" if ok else ("WARN" if warning else "FAIL")
    print(f"[{prefix}] {label}: {detail}")
    return ok or warning


def check_import(module: str, package: str) -> bool:
    found = importlib.util.find_spec(module) is not None
    detail = "installed" if found else f"missing; run `{sys.executable} -m pip install -r requirements.txt`"
    return status(package, found, detail)


def check_command(command: str, label: str, required: bool = False) -> bool:
    found = shutil.which(command) is not None
    detail = shutil.which(command) or "not on PATH"
    return status(label, found, detail, warning=not required)


def check_path(path: Path, label: str, required: bool = False) -> bool:
    found = path.exists()
    detail = str(path) if found else f"missing: {path}"
    return status(label, found, detail, warning=not required)


def check_script_help(script: Path) -> bool:
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=script.parent.parent,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    detail = "help command works" if result.returncode == 0 else result.stderr.strip()[:240]
    return status(script.name, result.returncode == 0, detail)


def check_structured_loadout_adapter() -> bool:
    record = {
        "loadouts": 1,
        "loadout_entries": (
            SimpleNamespace(weapon_ids=(0, 101, 202), weapon_counts=(0, 2, 4)),
        ),
    }
    count, loadouts = record_loadouts(record)
    ok = count == 1 and loadouts == [{"weapon_ids": [0, 101, 202], "weapon_counts": [0, 2, 4]}]
    return status("pyopencam structured loadouts", ok, "adapter preserved IDs/counts" if ok else repr(loadouts))


def default_presentations_skill_dir() -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or "")
    return home / ".codex" / "plugins" / "cache" / "openai-primary-runtime" / "presentations" / "26.506.11943" / "skills" / "presentations"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bms-root", type=Path, help="Optional Falcon BMS install root to validate legacy BMSUtils decode support.")
    parser.add_argument("--object-dir", type=Path, help="Optional Falcon object table directory to validate object lookups.")
    parser.add_argument("--pyopencam-json-dir", type=Path, help="Optional pyopencam JSON export directory to validate adapter input availability.")
    parser.add_argument("--pyopencam-root", type=Path, help="Optional pyopencam checkout/source directory to validate direct provider support.")
    parser.add_argument("--require-deck", action="store_true", help="Fail if the optional Codex presentation skill deck builder is unavailable.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    checks: list[bool] = []

    checks.append(status("Python", sys.version_info >= (3, 10), sys.version.split()[0]))
    for module, package in REQUIRED_IMPORTS.items():
        checks.append(check_import(module, package))
    checks.append(check_structured_loadout_adapter())

    checks.append(check_command("node", "Node.js", required=False))
    checks.append(check_command("powershell", "PowerShell", required=False))

    for relative in (
        "scripts/extract_bms_briefing.py",
        "scripts/synthesize_bms_briefing.py",
        "scripts/render_bms_package_map.py",
        "scripts/render_bms_map_set.py",
        "scripts/render_bms_enemy_air_threat_map.py",
        "scripts/render_bms_weather_map.py",
        "scripts/render_bms_slide_image_pack.py",
        "scripts/validate_bms_briefing_outputs.py",
        "scripts/pyopencam_adapter.py",
        "scripts/pyopencam_provider.py",
        "scripts/ab_test_cam_decoders.py",
        "scripts/compare_decoders.py",
        "scripts/export_claude_design_bundle.py",
        "scripts/upload_claude_design_bundle.py",
    ):
        checks.append(check_script_help(repo_root / relative))

    if args.bms_root:
        checks.append(check_path(args.bms_root, "Falcon BMS root", required=True))
        checks.append(check_path(args.bms_root / "mc" / "BMSUtils.dll", "Legacy BMSUtils.dll", required=False))
        checks.append(check_path(args.bms_root / "mc" / "LzssManaged.dll", "Legacy LzssManaged.dll", required=False))

    if args.object_dir:
        checks.append(check_path(args.object_dir / "Falcon4_UCD.xml", "Falcon4_UCD.xml", required=True))
        checks.append(check_path(args.object_dir / "Falcon4_CT.xml", "Falcon4_CT.xml", required=True))
        checks.append(check_path(args.object_dir / "Falcon4_VCD.xml", "Falcon4_VCD.xml", required=True))

    if args.pyopencam_json_dir:
        checks.append(check_path(args.pyopencam_json_dir, "pyopencam JSON export dir", required=True))
        checks.append(
            status(
                "pyopencam *.uni.json",
                bool(list(args.pyopencam_json_dir.glob("*.uni.json"))),
                "found" if list(args.pyopencam_json_dir.glob("*.uni.json")) else "missing *.uni.json export",
            )
        )

    if args.pyopencam_root:
        checks.append(check_path(args.pyopencam_root / "cam_to_json.py", "pyopencam provider cam_to_json.py", required=True))
        checks.append(check_path(args.pyopencam_root / "lib" / "uni_parser.py", "pyopencam provider uni_parser.py", required=True))

    skill_dir = Path(os.environ.get("PRESENTATIONS_SKILL_DIR") or default_presentations_skill_dir())
    builder = skill_dir / "scripts" / "build_artifact_deck.mjs"
    checks.append(check_path(builder, "Optional PPTX deck builder", required=args.require_deck))

    if all(checks):
        print("\nStandalone check passed.")
        return
    print("\nStandalone check failed. Install missing required dependencies and rerun this script.")
    sys.exit(1)


if __name__ == "__main__":
    main()
