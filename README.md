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
- Optionally decodes `.cam` sections through the legacy read-only Mission
  Commander/BMSUtils compatibility path:
  - `.tea`: teams.
  - `.obd`: objective deltas.
  - `.uni`: units, packages, flights, squadrons, callsigns, mission codes,
    battalions, brigades, task forces, TACAN arrays, and waypoints.
  - Package support IDs for AWACS/JSTAR/ECM/tanker/interceptor links.
  - Flight aircraft counts, plane stats, loadouts, weapon IDs/counts, laser
    codes, and TACAN channels.
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

Example:

```powershell
python .\scripts\extract_bms_briefing.py `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Campaign" `
  --prefix 718pre `
  --deck-url "https://docs.google.com/presentation/d/1sV9xxCRPyaAeumhVlZdfAq7CFWqq8Ch9Gk0d7h3EnTc/edit" `
  --decode-cam `
  --bms-root "C:\Falcon BMS 4.38" `
  --out-dir .\outputs\718pre
```

The main output is `briefing_data.json`; `briefing_summary.md` is a human-readable
sanity check. When `--decode-cam` is used, the full BMS object dump is written to
`cam_decode.json` beside those files. The helper script auto-runs under 32-bit
PowerShell because `BMSUtils.dll` is a 32-bit assembly. Treat this path as a
read-only legacy fallback and cross-check provider only; known Mission
Commander/BMSUtils write-back bugs make it unsuitable as the foundation for
future campaign-writing features.

Build the synthesis layer:

```powershell
python .\scripts\synthesize_bms_briefing.py `
  --briefing-data .\outputs\718pre\briefing_data.json `
  --cam-decode .\outputs\718pre\cam_decode.json `
  --camp-obj-data "C:\Falcon BMS 4.38\Data\Campaign\CampObjData.XML" `
  --out-dir .\outputs\718pre `
  --focus-package 2515
```

That writes `briefing_synthesis.json` and `generated_briefing.md`. The
synthesizer resolves tactical waypoint targets to objectives, flights, packages,
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
active enemy squadron bases and airframe capability. It can also list sanitized
active enemy air contacts at campaign time when decoded current positions are
within, or immediately vectoring into, 30 NM of the target-area anchors; those
rows omit enemy callsigns, package IDs, and tasking IDs.
For exact latitude/longitude conversion, use the `Theater.txt` projection string
through PROJ/`pyproj`; `scripts\bms_projection.py` contains the local helper and
keeps the grid transform tied to theater metadata rather than hand-fitted
offsets.

Build the editable briefing deck:

```powershell
node `
  .\scripts\build_bms_briefing_deck.mjs `
  --synthesis .\outputs\718pre\briefing_synthesis.json `
  --out-dir .\outputs\718pre `
  --package-id 2515
```

That writes a package-specific deck, for example
`procedural-bms-718pre-pkg-2515-briefing.pptx`, showing the decode pipeline,
package snapshot, package coordination table, route/timing read, scored follow-on
package queue, and remaining decoder gaps.

For the UOAF 80s add-on sample:

```powershell
python .\scripts\extract_bms_briefing.py `
  --campaign-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign" `
  --prefix 738pre `
  --decode-cam `
  --bms-root "C:\Falcon BMS 4.38" `
  --object-dir "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\TerrData\Objects" `
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
  --show-airbases `
  --out .\outputs\738pre\package_1883_target_area_zoom_skyvector.png
```

For a closer target-file view around the INI objective geometry itself, use
`--crop-mode objective-area`. This crop keeps the objective labels and
mission-context CAP anchors, such as Guardpost/GRD and BARRIER/BAR, so the
BARCAP stations remain visible with the target-area geometry. It uses a tighter
default crop than the target-area view and suppresses overlapping decoded flight
route lines so Route Black, named objectives, ADA WEZs, and enemy airbase
markers are easier to inspect:

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
  --out .\outputs\738pre\package_1883_weather_map_skyvector.png
```

## Decoder Comparison

Decoder policy:

- Prefer `pyopencam` as the future primary CAM parser once its adapter emits the
  full canonical `cam_decode` shape.
- Keep BMSUtils as a read-only compatibility fallback and regression oracle, not
  a write-back dependency.
- Use `falcon-bms-tacview-converter` concepts for theater discovery,
  projection, heightmaps, and airbase/runway metadata rather than importing its
  Tacview-specific CLI shape.
- Do not vendor either upstream project blindly; preserve attribution, check
  licenses, and keep this repo's synthesis schema provider-neutral.

`pyopencam` is not vendored into this repo. When a pyopencam JSON export exists,
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

The current 718/738 comparison passes unit counts. Package 1883 is only present
in 738, where flight IDs, callsigns, and waypoint counts also match.
