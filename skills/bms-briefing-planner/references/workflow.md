# BMS Briefing Workflow

## 1. Reset Mission Context

Treat the current mission as a clean room:

- Identify campaign prefix, theater/campaign directory, BMS root, map source, package IDs, and player package scope.
- Check whether old output folders are style references or current mission inputs.
- Prevent prior-mission leakage. Examples of forbidden carryover unless restated: `Route Black`, `Guardpost`, `Barrier`, `Tiger`, `Joule`, `Crown`, named SA-10 geometry, or old package IDs.
- Put user-provided planner intent into a mission-context JSON file under `inputs/`, not directly into renderer code.

## 2. Decode

Use the repo scripts rather than hand-reading binary data.

Typical extraction:

```powershell
python .\scripts\extract_bms_briefing.py `
  --campaign-dir "<campaign-dir>" `
  --prefix "<prefix>" `
  --out-dir ".\outputs\<prefix>" `
  --decode-cam `
  --cam-decoder pyopencam `
  --bms-root "C:\Falcon BMS 4.38" `
  --object-dir "C:\Falcon BMS 4.38\Data\TerrData\Objects"
```

Synthesize each player package or the combined package set:

```powershell
python .\scripts\synthesize_bms_briefing.py `
  --briefing-data ".\outputs\<prefix>\briefing_data.json" `
  --cam-decode ".\outputs\<prefix>\cam_decode.json" `
  --camp-obj-data "<campaign-dir>\CampObjData.XML" `
  --out-dir ".\outputs\<prefix>" `
  --focus-package <package-id> `
  --mission-context ".\inputs\<prefix>-player-packages-context.json" `
  --object-dir "C:\Falcon BMS 4.38\Data\TerrData\Objects"
```

For multiple player packages in one deck, synthesize package-specific folders and then render combined products with repeated `--synthesis`.

## 3. Correlate Planner Intent

Correlate the planner prompt with decoded data:

- Package IDs and flights.
- Callsigns, aircraft count/type, role, takeoff, TOT, loadout, laser codes, TACAN.
- AWACS/tanker callsigns, aircraft, TACAN, tracks, and whether they matter to the player package.
- Flight plan steerpoints and mission actions.
- INI/PPT marks, named marks, drawn lines, route labels, threat steerpoints, and bullseye.
- Weather at takeoff, target, and landing: local time/day-night, conditions, cloud base, contrail layer, temp, visibility, wind.
- Enemy situation around the actual target area.

If a decoded value conflicts with planner/in-game observation, investigate the root cause before accepting either one. Examples from prior missions:

- Bad INI coordinate conversion can place marks far from the in-game map.
- Objective names can be wrong if takeoff/landing target IDs are interpreted as generic objectives instead of airbase objectives.
- Enemy airbases can be misnamed or mis-typed if objective/object tables are not joined correctly.

## 4. Build The Transitional Workup

The transitional workup is allowed to be detailed and technical. Use it to preserve:

- Data provenance and script commands.
- Package and flight tables.
- Coordinate appendices.
- Threat filtering details.
- Decoder gaps.
- User corrections and why they override or reinterpret raw data.

Keep this separate from the player brief. A player should never see generator apologies, missing sidecar notes, script flags, or raw parser caveats unless they represent an actual mission limitation.

## 5. Draft The Player-Facing Brief

Use [brief-criteria.md](brief-criteria.md). The player brief should read like a human mission brief, not a decoder dump. Include coordinates in appendices or compact tables, but keep the main narrative tactical.

## 6. Render Images

Use [image-qa.md](image-qa.md). Generate the numbered image pack and inspect slide-size previews. Rerender until the image answers its assigned question.

## 7. Install And Use F4Wx Weather

When the user generates weather with F4Wx:

- Treat a folder of timestamped files such as `10900.fmap`, `11000.fmap`, `11100.fmap` as an automatic campaign weather sequence.
- Copy the sequence into `<campaign-dir>\WeatherMapsUpdates`.
- Back up an existing `WeatherMapsUpdates` folder before replacing its `.fmap` files.
- Copy the first applicable sequence frame to `<campaign-dir>\<prefix>.fmap` so the save-specific starting weather matches the update sequence.
- Keep the original F4Wx output folder intact.

After installing weather, rerun extraction/synthesis so `briefing_data.json` and `briefing_synthesis.json` see the new `.fmap` sidecar.

When briefing weather, use FMAP stratus base as the BMS/UI cloud-base value and FMAP contrail layer for con layer. If the UI is available, sanity-check those two numbers against it; do not use the raw per-cell cumulus-base field as the player-facing cloud base unless separately validated.

Weather map render example:

```powershell
python .\scripts\render_bms_weather_map.py `
  --synthesis ".\outputs\<prefix>\pkg<package-id>\briefing_synthesis.json" `
  --cam-decode ".\outputs\<prefix>\cam_decode.json" `
  --campaign-dir "<campaign-dir>" `
  --package-id <package-id> `
  --fmap "<campaign-dir>\<prefix>.fmap" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --feet-per-grid 3280.84 `
  --margin-grid 24 `
  --scale 8 `
  --aspect-ratio 16:9 `
  --no-show-footer `
  --weather-alpha 112 `
  --ao-label "PACKAGE AO" `
  --route-label-font-size 36 `
  --ini-label-font-size 54 `
  --weather-label-font-size 72 `
  --ao-label-font-size 76 `
  --scale-label-font-size 52 `
  --out ".\outputs\<prefix>\slide_v1_3\briefing_images\04_weather_map.png"
```

For multi-package decks, render package-specific weather references when useful, but promote one deck-facing `04_weather_map.png` unless the user asks for separate weather slides.

## 8. Package And Publish

Collect final images:

```powershell
python .\scripts\collect_bms_image_pack.py ".\outputs\<prefix>"
```

Do not export Claude/design bundles, commit, or push until explicitly prompted.
