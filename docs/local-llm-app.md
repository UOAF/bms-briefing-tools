# Local LLM App

The local app is a thin wrapper over the existing BMS briefing tools. It does
not fork or duplicate the mission pipeline.

## What It Reuses

- `scripts/extract_bms_briefing.py`
- `scripts/synthesize_bms_briefing.py`
- `scripts/render_bms_map_set.py`
- `scripts/collect_bms_image_pack.py`
- `skills/bms-briefing-planner` as the LLM workflow/policy prompt
- Existing mission-context JSON shape under `inputs/`
- Existing output contract under `outputs/<prefix>`

## Install

Run:

```powershell
.\Install-UOAF-BriefingTool.bat
```

The installer creates `.venv`, installs Python dependencies, checks FFmpeg, and
installs or detects pyopencam for CAM decoding. It also optionally installs
Ollama plus `llama3.1:8b` for local fallback.

## Start

Run:

```powershell
.\Start-UOAF-BriefingTool.bat
```

Then open:

```text
http://127.0.0.1:7400
```

## Provider Order

In `auto` mode the app tries:

1. OpenAI, when `OPENAI_API_KEY` is set.
2. Ollama, when the local OpenAI-compatible endpoint is reachable.
3. LM Studio, when the local OpenAI-compatible endpoint is reachable.
4. Offline template mode.

Useful environment variables:

```powershell
$env:OPENAI_API_KEY = "..."
$env:OPENAI_MODEL = "gpt-4.1-mini"
$env:OLLAMA_MODEL = "llama3.1:8b"
$env:LMSTUDIO_MODEL = "local-model"
$env:PYOPENCAM_ROOT = "C:\path\to\pyopencam"
```

The app auto-detects pyopencam in this order:

1. The `pyopencam root` field in the UI.
2. `PYOPENCAM_ROOT`.
3. `.tools\pyopencam` under this repo.
4. `tmp\pyopencam-main` under this repo.
5. `Desktop\pyopencam-main`.

If none are found, rerun `Install-UOAF-BriefingTool.bat` or fill the advanced
`pyopencam root` field before starting the workflow.

## Security Model

The web app only exposes allowlisted workflow actions. The LLM does not get
free shell access. It can help draft mission-context JSON, and the backend then
runs the existing deterministic scripts with explicit arguments.

Keep the app bound to `127.0.0.1` unless you deliberately harden it for a LAN or
hosted deployment.

## Current Scope

The first app workflow is intentionally conservative:

- It supports one primary package for root synthesis/map-set rendering.
- Additional package IDs are preserved in mission context and package-specific
  synthesis folders.
- Advanced combined multi-package slide maps still belong to the existing
  expert renderer workflow until we promote those controls into the app.
