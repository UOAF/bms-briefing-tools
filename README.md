# BMS briefing extractor

This workspace is for reverse-engineering Falcon BMS campaign save bundles into
structured briefing inputs.

For the scalability plan and upstream parser/tooling assessment, see
[`docs/scalable-tooling-strategy.md`](docs/scalable-tooling-strategy.md).
For clean-machine setup and dependency checks, see
[`docs/standalone-setup.md`](docs/standalone-setup.md).

Current prototype:

- Parses campaign sidecars by prefix, for example `718pre.*`.
- Parses the embedded `.cam` container directory and save version.
- Optionally decodes `.cam` sections through the direct `pyopencam` provider, or
  through the legacy read-only Mission Commander/BMSUtils compatibility path:
  - `.tea`: teams.
  - `.obd`: objective deltas.
  - `.uni`: units, packages, flights, squadrons, callsigns, mission codes,
    battalions, brigades, task forces, TACAN arrays, and waypoints.
  - Package support IDs for AWACS/JSTAR/ECM/tanker/interceptor links.
  - Flight aircraft counts, plane stats, loadouts, weapon IDs/counts, laser
    codes, TACAN channels, CFT flags, and waypoints.
- Extracts DTC/planning points from `*.ini`.
  - `target_*`, `ppt_*`, `wpntarget_*`, and drawn `lineSTPT_*` plan geometry.
- Extracts Link 16 network and flight channel assignments from `*.l16.txtpb`.
- Parses `*.fmap` weather maps into sampled package meteorology: condition,
  cloud base, contrail layer, temperature, visibility, and winds.
- Captures binary file inventory/header hints for `.cam`, `.frc`, `.his`,
  `.twx`, `.fmap`, and `.iff`.
- Optionally reads a public Google Slides `htmlpresent` view and indexes likely
  briefing-source slides such as coordination, friendly OOB, meteorology, and
  operating-area slides.

Default workflow:

1. Decode the campaign save.
2. Generate and review the briefing markdown.
3. Render and review briefing maps.
4. Iterate on mission context, briefing text, threat logic, and maps.
5. Export a Claude design handoff bundle only when explicitly requested for
   final deck production.

Example:

```powershell
python .\scripts\extract_bms_briefing.py `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Campaign" `
  --prefix 718pre `
  --deck-url "https://docs.google.com/presentation/d/1sV9xxCRPyaAeumhVlZdfAq7CFWqq8Ch9Gk0d7h3EnTc/edit" `
  --decode-cam `
  --cam-decoder pyopencam `
  --pyopencam-root "$env:PYOPENCAM_ROOT" `
  --out-dir .\outputs\718pre
```

The main output is `briefing_data.json`; `briefing_summary.md` is a human-readable
sanity check. When `--decode-cam` is used, the full BMS object dump is written to
`cam_decode.json` beside those files. The default decoder is
`--cam-decoder pyopencam`, which imports a local pyopencam checkout/source
directory and emits the same canonical `cam_decode.json` shape used by
synthesis. The `bmsutils` decoder remains a read-only legacy fallback and
cross-check provider only; known Mission Commander/BMSUtils write-back bugs make
it unsuitable as the foundation for future campaign-writing features.

Build the synthesis layer:

```powershell
python .\scripts\synthesize_bms_briefing.py `
  --briefing-data .\outputs\718pre\briefing_data.json `
  --cam-decode .\outputs\718pre\cam_decode.json `
  --camp-obj-data "C:\Falcon BMS 4.38\Data\Campaign\CampObjData.XML" `
  --out-dir .\outputs\718pre `
  --focus-package 2515
```

That writes three briefing artifacts:

- `briefing_synthesis.json`: structured source of truth for follow-on tooling.
- `briefing_workup.md`: transitional analysis with provenance, gaps, and
  correlation notes for human/Codex iteration.
- `generated_briefing.md`: clean player-facing mission brief that omits
  development notes and missing-data chatter.

The synthesizer resolves tactical waypoint targets to objectives, flights, packages,
squadrons, and ground/naval units when the CAM exposes matching VU IDs. It also
converts mission INI plan points into campaign grid coordinates and correlates
them to package route waypoints. Korea/UOAF currently defaults to
`--theater-grid-rows 928`, with INI world-foot points converted through the
KTO theater size from `Theater.txt`: 1024 km over 1024 campaign grid cells.
For BMS 4.38 the default is real-life feet, `3280.84` ft per grid cell; use
`--feet-per-grid 3279.98` only when intentionally reproducing older 4.37-style
conversion behavior. A mission-context JSON can add human
interpretation such as SAD contracts, CAP assignments, target opportunities, and
fallback logic.
Top-level mission context can also define a `friendly_surface_defense` anchor
with a named INI/PPT label, allowing the generated brief to show a friendly
surface fallback point without including friendly air defenses in the threat
estimate.
An optional `--object-dir` lets the synthesizer resolve unit classes and vehicles
from `Falcon4_UCD.xml`, `Falcon4_CT.xml`, and `Falcon4_VCD.xml` so it can add a
local enemy-situation, air-defense estimate, and enemy squadron-base threat
estimate.
The generated markdown ends with a coordinate appendix for the focus package,
including flight steerpoints, INI planning marks, nearest-route matches, and
air-defense and enemy squadron-base coordinates, plus resolved location objects.
The commander-facing package section is scoped to the requested player/focus
package. Other packages are only summarized when their decoded tactical
waypoints are friendly, close enough in space and time to affect the target
area or require deconfliction, and each such row includes the reason it was
included. Enemy air packages are not exposed from decoded ATO knowledge in the
player-facing brief; the brief instead derives likely enemy fighter axes from
active enemy squadron bases, likely origin-base names/ranges, and airframe
capability. It can also list sanitized active enemy air contacts at campaign
time when decoded current positions are within, or immediately vectoring into,
30 NM of the target-area anchors; those rows omit enemy callsigns, package IDs,
and tasking IDs.
For exact latitude/longitude conversion, use the `Theater.txt` projection string
through PROJ/`pyproj`; `scripts\bms_projection.py` contains the local helper and
keeps the grid transform tied to theater metadata rather than hand-fitted
offsets.

When the briefing text and maps are reviewed and ready for deck production,
export the supported Claude design handoff bundle as an explicit final step:

```powershell
python .\scripts\export_claude_design_bundle.py `
  --synthesis .\outputs\718pre\briefing_synthesis.json `
  --package-id 2515 `
  --ready-for-claude `
  --out-dir .\outputs\718pre\claude_design_pkg_2515
```

That writes `manifest.json`, `claude_design_prompt.md`, source markdown/JSON,
and briefing images into a single upload-ready directory. Upload the bundle to
Claude with the included `.claude/skills/bms-briefing-design` instructions, or
use the optional Files API helper when `ANTHROPIC_API_KEY` is set:

```powershell
python .\scripts\upload_claude_design_bundle.py `
  --bundle-dir .\outputs\718pre\claude_design_pkg_2515
```

The legacy in-repo PPTX generator remains as a fallback/debug path only. It is
not the supported deck-production flow:

```powershell
node `
  .\scripts\build_bms_briefing_deck.mjs `
  --synthesis .\outputs\718pre\briefing_synthesis.json `
  --out-dir .\outputs\718pre `
  --package-id 2515
```

The fallback writes a package-specific deck, for example
`procedural-bms-718pre-pkg-2515-briefing.pptx`, showing the decode pipeline,
package snapshot, package coordination table, route/timing read, scored follow-on
package queue, and remaining decoder gaps.

For the UOAF 80s add-on sample:

```powershell
python .\scripts\extract_bms_briefing.py `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --prefix 738pre `
  --decode-cam `
  --cam-decoder pyopencam `
  --pyopencam-root "$env:PYOPENCAM_ROOT" `
  --theater-folder "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s" `
  --out-dir .\outputs\738pre

python .\scripts\synthesize_bms_briefing.py `
  --briefing-data .\outputs\738pre\briefing_data.json `
  --cam-decode .\outputs\738pre\cam_decode.json `
  --camp-obj-data "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign\CampObjData.XML" `
  --out-dir .\outputs\738pre `
  --focus-package 1883 `
  --theater-grid-rows 928 `
  --feet-per-grid 3280.84 `
  --mission-context .\inputs\738pre-pkg-1883-context.json `
  --object-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\TerrData\Objects"
```

Stop here for briefing iteration. Render/review maps, adjust mission context, and
rerun synthesis as needed. Use `briefing_workup.md` to preserve analysis context
while keeping `generated_briefing.md` clean for players. Do not export a Claude
bundle until final deck production is explicitly requested.

Deprecated fallback deck render:

```powershell
node `
  .\scripts\build_bms_briefing_deck.mjs `
  --synthesis .\outputs\738pre\briefing_synthesis.json `
  --out-dir .\outputs\738pre `
  --package-id 1883
```

Render a package map from the same synthesis data:

```powershell
python .\scripts\render_bms_package_map.py `
  --synthesis .\outputs\738pre\briefing_synthesis.json `
  --cam-decode .\outputs\738pre\cam_decode.json `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --package-id 1883 `
  --out .\outputs\738pre\package_1883_route_threat_map.png
```

The map renderer uses `Korea.tm` from the campaign directory as a 1024x1024
theater raster and plots campaign grid coordinates with
`x=grid_x, y=1024-grid_y`.
It overlays full decoded flight waypoint chains, named INI PPTs, the drawn INI
`lineSTPT` route, human SAD/CAP assignments, package-linked AWACS/tanker support
station tracks, and enemy-only air-defense rings from the synthesis threat
estimate. Strategic air-defense overlays require an active tracking-radar roster
slot, for example Fan Song for SA-2, Low Blow for SA-3, and Straight Flush for
SA-6. Add `--show-airbases` to include active enemy squadron bases that are not
decoded as 0 percent operational; zoomed target views keep airbase labels off
the map so the target geometry remains readable.
Overlay readability can be tuned with `--route-opacity`, `--marker-opacity`,
`--label-opacity`, and `--threat-opacity` in the range `0.0` to `1.0`. The
defaults are deliberately semi-transparent so dense target areas remain readable
against the chart base.

For deck work, prefer the slide-ready map-set renderer. It writes the standard
overview, target-area, and objective-area PNGs at high resolution, expands each
crop to a 16:9 map area, suppresses the footer so the map fills the slide, and
keeps support tracks from forcing the package overview to zoom too far out:

```powershell
python .\scripts\render_bms_map_set.py `
  --synthesis .\outputs\738pre\briefing_synthesis.json `
  --cam-decode .\outputs\738pre\cam_decode.json `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --package-id 1883 `
  --feet-per-grid 3280.84 `
  --out-dir .\outputs\738pre
```

Use the low-level renderer below when you need a custom crop, a footer for QA, or
a one-off diagnostic map.

For enemy air-threat slides, render a map of likely origin axes instead of a
text-heavy table. This uses active enemy fighter/strike squadron home positions
and aircraft capability, then draws red arrows from those bases toward the
player tactical AO. The default crop is AO-focused: labels for origins outside
the crop are pinned to the map edge, which keeps the slide readable while still
showing threat direction. Airbase origins use the campaign objective name when
`CampObjData.XML` is available. Repeat `--synthesis` for combined
player-package decks. Add `--combined-out` for the deck-facing map that layers
package flow from friendly origins, named positions, low-opacity strategic ADA
rings, and enemy air axes into one image. `--flow-out` is still available when
you want to inspect the package-flow layer by itself:

```powershell
python .\scripts\render_bms_enemy_air_threat_map.py `
  --synthesis .\outputs\739pre\pkg3465\briefing_synthesis.json `
  --synthesis .\outputs\739pre\pkg3494\briefing_synthesis.json `
  --cam-decode .\outputs\739pre\cam_decode.json `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Campaign" `
  --object-dir "C:\Falcon BMS 4.38\Data\TerrData\Objects" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --radius-nm 100 `
  --out .\outputs\739pre\enemy_air_threat_axes_skyvector.png `
  --combined-out .\outputs\739pre\package_flow_enemy_air_axes_skyvector.png `
  --combined-threat-opacity 0.26 `
  --flow-out .\outputs\739pre\package_flow_overview_skyvector.png
```

Render a full origin-to-target route/threat overview for the first map slot by
using the same combined renderer with friendly flow origins included in the crop:

```powershell
python .\scripts\render_bms_enemy_air_threat_map.py `
  --synthesis .\outputs\739pre\pkg3465\briefing_synthesis.json `
  --synthesis .\outputs\739pre\pkg3494\briefing_synthesis.json `
  --cam-decode .\outputs\739pre\cam_decode.json `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Campaign" `
  --object-dir "C:\Falcon BMS 4.38\Data\TerrData\Objects" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --radius-nm 100 `
  --out .\outputs\739pre\enemy_air_threat_axes_skyvector.png `
  --combined-out .\outputs\739pre\route_threat_map_skyvector.png `
  --combined-title "Route & Threat Map" `
  --combined-include-flow-origins-in-bounds `
  --combined-threat-opacity 0.34
```

Use `--crop-mode all` when you want the older full-origin crop for diagnostics.
Use `--no-combined-threat-rings` when you need a clean flow/threat-axis image
without ADA WEZ rings.

To review the useful slide images without hunting through package work folders,
collect the mission images into one flat folder:

```powershell
python .\scripts\collect_bms_image_pack.py .\outputs\739pre
```

That writes the standard slide-facing image set into
`.\outputs\739pre\briefing_images`:

- `01_route_threat_map.png`: high-level route/threat overview from origin
  airbases to the target area. Aggregated route arrows include the represented
  flight callsigns in parentheses when discrete flight plans would clutter the
  slide.
- `02_target_area_map.png`: target-area flow map using the combined package
  flow, enemy air axes, named positions, and low-opacity threat rings.
- `03_objective_area_map.png`: close objective-area map for target prosecution
  detail.
- `04_weather_map.png`: optional weather map when a weather render exists.

It also writes `manifest.json`, which records the source image each numbered
file came from. Use `--mode all` when you want the older broad collection of
all canonical map/weather products. Claude bundle asset folders and diagnostic
variants are skipped by default; add `--include-variants` with `--mode all`
when you want those copied too.

For a chart-style base layer, point `--map-source` at the 16k Skyvector map:

```powershell
python .\scripts\render_bms_package_map.py `
  --synthesis .\outputs\738pre\briefing_synthesis.json `
  --cam-decode .\outputs\738pre\cam_decode.json `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --package-id 1883 `
  --feet-per-grid 3280.84 `
  --margin-grid 22 `
  --scale 5 `
  --out .\outputs\738pre\package_1883_route_threat_map_skyvector.png
```

For a tighter target-area view, use the same chart base with
`--crop-mode target-area`. This excludes the home/recovery portions of the
flight plans from the map framing and centers the output on tactical package
waypoints, INI named steerpoints/routes, and enemy-only threat overlays:

```powershell
python .\scripts\render_bms_package_map.py `
  --synthesis .\outputs\738pre\briefing_synthesis.json `
  --cam-decode .\outputs\738pre\cam_decode.json `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --package-id 1883 `
  --feet-per-grid 3280.84 `
  --crop-mode target-area `
  --margin-grid 14 `
  --scale 8 `
  --aspect-ratio 16:9 `
  --no-show-footer `
  --show-airbases `
  --out .\outputs\738pre\package_1883_target_area_zoom_skyvector.png
```

For a closer target-file view around the INI objective geometry itself, use
`--crop-mode objective-area`. This crop keeps the objective labels and
mission-context CAP anchors so BARCAP stations remain visible with the
target-area geometry. It uses a tighter default crop than the target-area view
and suppresses overlapping decoded flight route lines so the current mission's
INI route, named objectives, ADA WEZs, and enemy airbase markers are easier to
inspect:

```powershell
python .\scripts\render_bms_package_map.py `
  --synthesis .\outputs\738pre\briefing_synthesis.json `
  --cam-decode .\outputs\738pre\cam_decode.json `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --package-id 1883 `
  --feet-per-grid 3280.84 `
  --crop-mode objective-area `
  --margin-grid 8 `
  --scale 10 `
  --aspect-ratio 16:9 `
  --no-show-footer `
  --show-airbases `
  --out .\outputs\738pre\package_1883_objective_area_zoom_skyvector.png
```

Render a package weather review map from the FMAP sidecar and the same route
geometry:

```powershell
python .\scripts\render_bms_weather_map.py `
  --synthesis .\outputs\738pre\briefing_synthesis.json `
  --cam-decode .\outputs\738pre\cam_decode.json `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --package-id 1883 `
  --feet-per-grid 3280.84 `
  --margin-grid 24 `
  --scale 5 `
  --aspect-ratio 16:9 `
  --out .\outputs\738pre\package_1883_weather_map_skyvector.png
```

## Decoder Comparison

Decoder policy:

- Prefer `pyopencam` as the primary CAM parser for read-only briefing extraction.
  `scripts/pyopencam_provider.py` imports an external checkout/source directory
  and emits the canonical `cam_decode` shape directly from `.cam` files.
- Keep BMSUtils as a read-only compatibility fallback and regression oracle, not
  a write-back dependency.
- Use `falcon-bms-tacview-converter` concepts for theater discovery,
  projection, heightmaps, and airbase/runway metadata rather than importing its
  Tacview-specific CLI shape.
- Do not vendor either upstream project blindly; preserve attribution, check
  licenses, and keep this repo's synthesis schema provider-neutral.

`pyopencam` is not vendored into this repo because the inspected archive has no
license file or packaging metadata. Point `--pyopencam-root` or
`PYOPENCAM_ROOT` at a local checkout/source directory:

```powershell
python .\scripts\extract_bms_briefing.py `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --prefix 738pre `
  --decode-cam `
  --cam-decoder pyopencam `
  --pyopencam-root "$env:PYOPENCAM_ROOT" `
  --theater-folder "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s" `
  --out-dir .\outputs\738pre
```

When a pyopencam JSON export exists, the older comparison adapter can still
normalize it and compare it against the current BMSUtils decode:

```powershell
python .\scripts\pyopencam_adapter.py `
  --json-dir "$env:TEMP\bms-tooling-research\pyopencam\738pre_json" `
  --out .\outputs\738pre\pyopencam_normalized.json

python .\scripts\compare_decoders.py `
  --case 718pre .\outputs\718pre\cam_decode.json "$env:TEMP\bms-tooling-research\pyopencam\718pre_json" `
  --case 738pre .\outputs\738pre\cam_decode.json "$env:TEMP\bms-tooling-research\pyopencam\738pre_json" `
  --package-id 1883
```

For direct-provider A/B testing, compare pyopencam output against the legacy
BMSUtils decoder without using BMSUtils in the production extraction path:

```powershell
python .\scripts\ab_test_cam_decoders.py `
  --cam "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign\738pre.cam" `
  --theater-folder "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s" `
  --pyopencam-root "$env:PYOPENCAM_ROOT" `
  --bms-root "C:\Falcon BMS 4.38" `
  --object-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\TerrData\Objects" `
  --package-id 1883
```

The current direct-provider 738 comparison matches BMSUtils unit counts, mission
counts, package 1883 flight IDs/callsigns/waypoint counts, flight
loadout/weapon arrays, laser codes, TACAN channels, CFT flags, active strategic
ADA count, inactive ADA exclusions, enemy airbase threats, active air contacts,
enemy airbase airframe labels, waypoint target IDs/building indexes, and
decoded current-unit altitude. The brief-critical CAM fields are now sourced
from pyopencam.

Additional pyopencam smoke coverage currently passes stock `714post`,
`715post`, `715pre`, `717post`, `718pre`, `bear-pre`, `omid-test`, `test`,
`weathertest`, and `weathertest2`, plus UOAF `736post`, `737post`, `737pre`,
`738pre`, and `738pretest`. Stock `736post` currently exposes an upstream
pyopencam parser coverage gap: `unsupported unit kind for CT 2`; do not paper
over that with a campaign-specific exception.
