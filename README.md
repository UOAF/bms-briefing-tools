# BMS Briefing Tools

Turn a Falcon BMS campaign save into a fact-grounded player briefing, a
slide-ready map pack, and—when requested—a complete UOAF community event
package.

The tooling is Windows-first and targets Falcon BMS 4.38 campaign data. It
uses `pyopencam` as the primary read-only CAM decoder and keeps BMSUtils as a
compatibility fallback only.

## What It Does

- Decodes campaign save bundles and matching sidecars (`.cam`, `.ini`, `.fmap`,
  `.l16.txtpb`, and more) by campaign prefix.
- Produces player-facing briefs with package, flight, loadout, timing, comms,
  TACAN, threat, and weather information.
- Renders a canonical map pack: route/threat, target area, objective area, and
  optional weather and 3D target views.
- Validates that the final briefing is current, internally consistent, and
  free of stale map variants or missing player stores.
- Prepares UOAF event publishing: an exact mission-file inventory, signup-sheet
  flight rows, a Discord-ready announcement, and a branded event banner.

## Quick Start

### 1. Check the local toolchain

Follow [standalone setup](docs/standalone-setup.md) first. Then run:

```powershell
python .\scripts\check_standalone.py
```

### 2. Decode a campaign

```powershell
python .\scripts\extract_bms_briefing.py `
  --campaign-dir "<campaign-dir>" `
  --prefix "<prefix>" `
  --out-dir ".\outputs\<prefix>" `
  --decode-cam `
  --cam-decoder pyopencam `
  --pyopencam-root "<pyopencam-source>" `
  --theater-folder "<theater-folder>"
```

This creates `briefing_data.json`, `briefing_summary.md`, and—when CAM decode
is enabled—`cam_decode.json`.

### 3. Build the player brief

```powershell
python .\scripts\synthesize_bms_briefing.py `
  --briefing-data ".\outputs\<prefix>\briefing_data.json" `
  --cam-decode ".\outputs\<prefix>\cam_decode.json" `
  --camp-obj-data "<campaign-dir>\CampObjData.XML" `
  --out-dir ".\outputs\<prefix>" `
  --focus-package <package-id> `
  --mission-context ".\inputs\<prefix>-player-packages-context.json" `
  --object-dir "<theater-folder>\TerrData\Objects"
```

For a multi-package player event, synthesize each player package, then create
one combined root brief:

```powershell
python .\scripts\build_combined_player_brief.py `
  --out ".\outputs\<prefix>\generated_briefing.md" `
  --copy-to ".\outputs\<prefix>\player_briefing_combined.md" `
  --synthesis ".\outputs\<prefix>\briefing_synthesis.json" --package-id <primary-package-id> `
  --synthesis ".\outputs\<prefix>\pkg<second-package-id>\briefing_synthesis.json" --package-id <second-package-id>
```

### 4. Render and validate the map pack

```powershell
python .\scripts\render_bms_slide_image_pack.py `
  --synthesis ".\outputs\<prefix>\briefing_synthesis.json" --package-id <package-id> `
  --cam-decode ".\outputs\<prefix>\cam_decode.json" `
  --campaign-dir "<campaign-dir>" `
  --out-dir ".\outputs\<prefix>\briefing_images" `
  --object-dir "<theater-folder>\TerrData\Objects" `
  --camp-obj-data "<campaign-dir>\CampObjData.XML" `
  --map-source "<map-image>"

python .\scripts\validate_bms_briefing_outputs.py `
  ".\outputs\<prefix>" --package-id <package-id>
```

The renderer stages candidates before promotion, archives replaced canonical
images under `_image_history`, and records the selected files in
`briefing_images/manifest.json`.

## Outputs

| Path | Purpose |
| --- | --- |
| `briefing_data.json` | Extracted campaign and sidecar data. |
| `cam_decode.json` | Canonical decoded CAM data. |
| `briefing_synthesis.json` | Structured mission source of truth. |
| `briefing_workup.md` | Detailed transitional analysis and provenance. |
| `generated_briefing.md` | Clean player-facing mission brief. |
| `player_briefing_combined.md` | Combined player brief for multi-package events. |
| `briefing_images/` | Canonical slide-ready map pack and manifest. |

## Community Event Publishing

Once the briefing is approved, prepare the deterministic event-publishing plan:

```powershell
python .\scripts\prepare_bms_community_publish.py `
  --campaign-dir "<campaign-dir>" `
  --prefix "<prefix>" `
  --output-dir ".\outputs\<prefix>\community_publish" `
  --synthesis ".\outputs\<prefix>\briefing_synthesis.json" `
  --package-id <package-id> `
  --event-number <event-number> `
  --operation-name "<operation-name>" `
  --event-date YYYY-MM-DD `
  --briefing-time 1800 --marshal-time 1745 `
  --theater "<theater>" --bms-version "4.38.1" `
  --mission-objectives "<concise player-facing objective summary>"
```

This command makes no network writes. It creates a checksummed mission-file
inventory, signup-sheet package and flight rows, and `discord_post.txt` with a
calculated Discord timestamp. The BMS Briefing Planner skill then performs the
explicitly requested Google Drive/Sheets, sharing, banner, and final-post steps.

## Codex Workflow

The reusable production skill lives at
[`skills/bms-briefing-planner`](skills/bms-briefing-planner). Copy or symlink
it into `$CODEX_HOME/skills/bms-briefing-planner` on a new workstation.

The skill keeps planner intent and current campaign data as mission truth. It
also defines the required checks for map freshness, player loadouts, signup
sheets, public-edit access, Discord posts, and UOAF event banners.

## Further Reading

- [Standalone setup and dependency checks](docs/standalone-setup.md)
- [Scalable tooling strategy](docs/scalable-tooling-strategy.md)
- [Local LLM app](docs/local-llm-app.md)
- [Full BMS briefing workflow](skills/bms-briefing-planner/references/workflow.md)
- [Community event publishing](skills/bms-briefing-planner/references/community-publishing.md)
- [Event banner criteria](skills/bms-briefing-planner/references/event-banner-criteria.md)

## Development Checks

Run these before contributing changes:

```powershell
python -m unittest discover -s tests
python .\scripts\check_standalone.py
```

For changes to the reusable skill:

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" `
  ".\skills\bms-briefing-planner"
```
