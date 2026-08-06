from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .mission_context import parse_package_ids, save_context


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Job:
    id: str
    status: str = "queued"
    logs: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    error: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.logs.append(f"[{stamp}] {message}")
        self.updated_at = time.time()


class JobStore:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def create(self) -> Job:
        with self.lock:
            job = Job(id=uuid.uuid4().hex[:12])
            self.jobs[job.id] = job
            return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)


class WorkflowError(RuntimeError):
    pass


def as_path(value: Any) -> Path:
    return Path(str(value)).expanduser()


def is_blank_path(value: Any) -> bool:
    if value in (None, ""):
        return True
    return str(value).strip() in {"", "."}


def explicit_existing_path(value: Any) -> Path | None:
    if is_blank_path(value):
        return None
    path = as_path(value)
    if not path.is_absolute() or not path.exists():
        return None
    return path


def append_if_value(command: list[str], flag: str, value: Any) -> None:
    if value not in (None, ""):
        command.extend([flag, str(value)])


def run_command(command: list[str], job: Job, env: dict[str, str] | None = None) -> None:
    job.log("> " + " ".join(f'"{part}"' if " " in part else part for part in command))
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert process.stdout is not None
    for line in process.stdout:
        job.log(line.rstrip())
    code = process.wait()
    if code != 0:
        raise WorkflowError(f"Command failed with exit code {code}: {' '.join(command)}")


def default_object_dir(campaign_dir: Path, theater_folder: Path | None, bms_root: Path | None) -> Path:
    candidates = []
    if theater_folder:
        candidates.append(theater_folder / "TerrData" / "Objects")
    candidates.append(campaign_dir.parent / "TerrData" / "Objects")
    if bms_root:
        candidates.append(bms_root / "Data" / "TerrData" / "Objects")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def bms_root_candidates(explicit: Any = None) -> list[Path]:
    candidates: list[Path] = []
    for value in (
        explicit,
        os.environ.get("BMS_ROOT"),
        os.environ.get("FALCON_BMS_ROOT"),
        r"C:\Falcon BMS 4.38",
        r"C:\Falcon BMS 4.37",
    ):
        if not is_blank_path(value):
            candidates.append(as_path(value))
    return candidates


def find_bms_root(explicit: Any = None) -> Path | None:
    for candidate in bms_root_candidates(explicit):
        if (candidate / "Data").is_dir():
            return candidate
    return None


def campaign_dir_candidates(prefix: str, explicit: Any = None, bms_root: Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    if not is_blank_path(explicit):
        candidates.append(as_path(explicit))
    roots = [bms_root] if bms_root else []
    roots.extend(root for root in bms_root_candidates() if root not in roots)
    for root in roots:
        if not root:
            continue
        data = root / "Data"
        candidates.append(data / "Campaign")
        for addon in data.glob("Add-On*"):
            candidates.append(addon / "Campaign")
        for campaign in data.glob("*\\Campaign"):
            candidates.append(campaign)
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate).lower()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def find_campaign_dir(prefix: str, explicit: Any = None, bms_root: Path | None = None) -> Path | None:
    for candidate in campaign_dir_candidates(prefix, explicit, bms_root):
        if (candidate / f"{prefix}.cam").is_file():
            return candidate
    return None


def default_map_source(bms_root: Path | None) -> Path | None:
    if not bms_root:
        return None
    candidate = bms_root / "Docs" / "05 Maps" / "8_KTO_16k_Skyvector.png"
    return candidate if candidate.exists() else None


def is_pyopencam_root(path: Path | None) -> bool:
    if not path:
        return False
    return (path / "cam_to_json.py").is_file() and (path / "lib" / "cam_container.py").is_file()


def pyopencam_candidates(explicit: Any = None) -> list[Path]:
    candidates: list[Path] = []
    for value in (
        explicit,
        os.environ.get("PYOPENCAM_ROOT"),
        ROOT / ".tools" / "pyopencam",
        ROOT / "tmp" / "pyopencam-main",
        Path.home() / "Desktop" / "pyopencam-main",
    ):
        if value not in (None, ""):
            candidates.append(as_path(value))
    return candidates


def find_pyopencam_root(explicit: Any = None) -> Path | None:
    for candidate in pyopencam_candidates(explicit):
        if is_pyopencam_root(candidate):
            return candidate
    return None


def pyopencam_status() -> dict[str, Any]:
    found = find_pyopencam_root()
    return {
        "available": found is not None,
        "path": str(found) if found else "",
        "checked": [str(path) for path in pyopencam_candidates()],
    }


def bms_status(prefix: str = "") -> dict[str, Any]:
    root = find_bms_root()
    campaign = find_campaign_dir(prefix, bms_root=root) if prefix else None
    return {
        "bms_root": str(root) if root else "",
        "campaign_dir": str(campaign) if campaign else "",
        "checked_campaign_dirs": [str(path) for path in campaign_dir_candidates(prefix, bms_root=root)] if prefix else [],
    }


def run_workflow(job: Job, request: dict[str, Any]) -> None:
    job.status = "running"
    try:
        prefix = str(request["prefix"]).strip()
        bms_root = find_bms_root(request.get("bms_root"))
        campaign_dir = find_campaign_dir(prefix, request.get("campaign_dir"), bms_root)
        if not campaign_dir:
            checked = "\n".join(f"  - {path}" for path in campaign_dir_candidates(prefix, request.get("campaign_dir"), bms_root))
            raise WorkflowError(
                f"Cannot find {prefix}.cam in the campaign folder.\n"
                "Fill the Campaign folder field with the folder containing the save, or set BMS root.\n"
                f"Checked:\n{checked}"
            )
        if not bms_root:
            possible_root = campaign_dir
            for _ in range(4):
                if (possible_root / "Data").is_dir():
                    bms_root = possible_root
                    break
                possible_root = possible_root.parent
        theater_folder = explicit_existing_path(request.get("theater_folder")) or campaign_dir.parent
        object_dir = explicit_existing_path(request.get("object_dir")) or default_object_dir(campaign_dir, theater_folder, bms_root)
        out_dir = ROOT / "outputs" / prefix
        context_path = ROOT / "inputs" / f"{prefix}-player-packages-context.json"
        package_ids = parse_package_ids(str(request.get("package_ids", "")))
        primary_package = int(request.get("primary_package") or (package_ids[0] if package_ids else 0))
        if not primary_package:
            raise WorkflowError("At least one package id is required.")
        job.log(f"Using campaign dir: {campaign_dir}")
        if bms_root:
            job.log(f"Using BMS root: {bms_root}")

        mission_context = request.get("mission_context") or {}
        if mission_context:
            save_context(context_path, mission_context)
            job.log(f"Wrote mission context: {context_path}")

        cam_decoder = str(request.get("cam_decoder") or "pyopencam")
        pyopencam_root = find_pyopencam_root(request.get("pyopencam_root"))
        if cam_decoder == "pyopencam" and not pyopencam_root:
            checked = "\n".join(f"  - {path}" for path in pyopencam_candidates(request.get("pyopencam_root")))
            raise WorkflowError(
                "pyopencam decoder requested but no pyopencam checkout was found.\n"
                "Run Install-UOAF-BriefingTool.bat again, set PYOPENCAM_ROOT, or fill the pyopencam root field.\n"
                f"Checked:\n{checked}"
            )
        if pyopencam_root:
            job.log(f"Using pyopencam root: {pyopencam_root}")

        out_dir.mkdir(parents=True, exist_ok=True)
        extract = [
            sys.executable,
            "scripts\\extract_bms_briefing.py",
            "--campaign-dir",
            str(campaign_dir),
            "--prefix",
            prefix,
            "--out-dir",
            str(out_dir),
            "--decode-cam",
            "--cam-decoder",
            cam_decoder,
        ]
        append_if_value(extract, "--pyopencam-root", pyopencam_root)
        append_if_value(extract, "--theater-folder", theater_folder)
        append_if_value(extract, "--bms-root", bms_root)
        append_if_value(extract, "--object-dir", object_dir)
        run_command(extract, job)

        package_ids = package_ids or [primary_package]
        camp_obj_data = campaign_dir / "CampObjData.XML"
        synthesis_paths: list[Path] = []
        for package_id in package_ids:
            synth_out = out_dir if package_id == primary_package else out_dir / f"pkg{package_id}"
            synth_out.mkdir(parents=True, exist_ok=True)
            synth = [
                sys.executable,
                "scripts\\synthesize_bms_briefing.py",
                "--briefing-data",
                str(out_dir / "briefing_data.json"),
                "--cam-decode",
                str(out_dir / "cam_decode.json"),
                "--camp-obj-data",
                str(camp_obj_data),
                "--out-dir",
                str(synth_out),
                "--focus-package",
                str(package_id),
                "--mission-context",
                str(context_path),
                "--object-dir",
                str(object_dir),
            ]
            append_if_value(synth, "--feet-per-grid", request.get("feet_per_grid") or "3280.84")
            run_command(synth, job)
            synthesis_paths.append(synth_out / "briefing_synthesis.json")

        combined_brief = [
            sys.executable,
            "scripts\\build_combined_player_brief.py",
            "--out",
            str(out_dir / "generated_briefing.md"),
            "--copy-to",
            str(out_dir / "player_briefing_combined.md"),
        ]
        for package_id, synthesis_path in zip(package_ids, synthesis_paths):
            combined_brief.extend(["--synthesis", str(synthesis_path), "--package-id", str(package_id)])
        run_command(combined_brief, job)

        if request.get("render_maps", True):
            map_source = explicit_existing_path(request.get("map_source")) or default_map_source(bms_root)
            image_dir = out_dir / "briefing_images"
            maps = [
                sys.executable,
                "scripts\\render_bms_slide_image_pack.py",
                "--cam-decode",
                str(out_dir / "cam_decode.json"),
                "--campaign-dir",
                str(campaign_dir),
                "--out-dir",
                str(image_dir),
                "--object-dir",
                str(object_dir),
                "--camp-obj-data",
                str(camp_obj_data),
                "--feet-per-grid",
                str(request.get("feet_per_grid") or "3280.84"),
            ]
            for package_id, synthesis_path in zip(package_ids, synthesis_paths):
                maps.extend(["--synthesis", str(synthesis_path), "--package-id", str(package_id)])
            append_if_value(maps, "--map-source", map_source)
            run_command(maps, job)

            validate = [
                sys.executable,
                "scripts\\validate_bms_briefing_outputs.py",
                str(out_dir),
            ]
            for package_id in package_ids:
                validate.extend(["--package-id", str(package_id)])
            run_command(validate, job)

        job.artifacts = {
            "output_dir": str(out_dir),
            "mission_context": str(context_path),
            "workup": str(out_dir / "briefing_workup.md"),
            "player_brief": str(out_dir / "generated_briefing.md"),
            "image_pack": str(out_dir / "briefing_images"),
        }
        job.status = "complete"
        job.log("Workflow complete.")
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.log(f"ERROR: {exc}")


def start_job(store: JobStore, request: dict[str, Any]) -> Job:
    job = store.create()
    thread = threading.Thread(target=run_workflow, args=(job, request), daemon=True)
    thread.start()
    return job
