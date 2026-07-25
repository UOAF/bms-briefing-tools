# Standalone Setup

This repo should run the briefing synthesis and map pipeline from a clean clone
without `falcon-bms-tacview-converter` as a runtime dependency. Direct CAM
decode uses a local `pyopencam` checkout/source directory until its licensing
and packaging story is settled.

Falcon BMS itself is still an external data dependency: the tools need campaign
save sidecars, theater files, object XML tables, and map rasters from a local BMS
install or from copied BMS data directories.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
npm install
python .\scripts\check_standalone.py
```

For a full local BMS install, validate the optional data paths too:

```powershell
python .\scripts\check_standalone.py `
  --bms-root "C:\Falcon BMS 4.38" `
  --object-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\TerrData\Objects" `
  --pyopencam-root "$env:PYOPENCAM_ROOT"
```

## What Is Standalone

- Campaign sidecar extraction, briefing-data JSON, and markdown summaries.
- Briefing synthesis from `briefing_data.json`, `cam_decode.json`, mission
  context, object tables, and weather maps.
- Route/threat maps and weather maps.
- Claude design handoff bundles containing source markdown, source JSON, map
  images, a manifest, and a prompt/template for deck generation.
- Direct read-only CAM decode through `scripts/pyopencam_provider.py` when a
  local pyopencam checkout/source directory is supplied.
- Decoder comparison against existing pyopencam JSON exports.

## What Is Optional

- Legacy CAM decode through Mission Commander/BMSUtils requires a local Falcon
  BMS install with `mc\BMSUtils.dll` and `mc\LzssManaged.dll`. This is
  read-only compatibility support only and must be selected explicitly with
  `--cam-decoder bmsutils`.
- `pyopencam` is not vendored yet because the inspected archive has no license
  file or packaging metadata. Use `--pyopencam-root` or `PYOPENCAM_ROOT` to
  point at a local checkout/source directory.
- Direct PPTX deck export through `scripts/build_bms_briefing_deck.mjs` is
  deprecated fallback/debug support. The supported deck workflow is to export a
  Claude design bundle and generate the final briefing from that bundle.
- Optional upload through `scripts/upload_claude_design_bundle.py` requires an
  `ANTHROPIC_API_KEY` and Anthropic Files API access. Manual upload of the bundle
  to Claude works without API credentials.

## Upstream Dependency Policy

- Prefer `pyopencam` as the primary read-only CAM parser. Keep the provider
  boundary explicit until licensing, packaging, and canonical-schema coverage
  are fully settled.
- Use `falcon-bms-tacview-converter` for projection/theater ideas and tests, not
  as a required runtime dependency.
- Keep BMSUtils as a read-only fallback and comparison oracle, never as the
  campaign write-back path.
