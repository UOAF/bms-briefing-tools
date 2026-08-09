# BMS Briefing Workflow

## 1. Reset Mission Context

Treat the current mission as a clean room:

- Identify campaign prefix, theater/campaign directory, BMS root, map source, package IDs, and player package scope.
- Capture the event number and operation/event name. If no name exists and the user asks for one, propose a short evocative operation title and store it in mission context, not only in the final markdown.
- If the mission maker names multiple human/player packages, default to one unified operation and one combined player-facing brief/deck. Only split briefs when the mission maker explicitly asks for package-separated outputs.
- Check whether old output folders are style references or current mission inputs.
- Prevent prior-mission leakage. Examples of forbidden carryover unless restated: `Route Black`, `Guardpost`, `Barrier`, `Tiger`, `Joule`, `Crown`, named SA-10 geometry, or old package IDs.
- Put user-provided planner intent into a mission-context JSON file under `inputs/`, not directly into renderer code.
- Store planner-approved objective-map framing in `map_objective_crop_labels` (and optional `map_objective_crop_label_margin_grid`) so guarded image-pack rebuilds preserve the chosen tactical box.
- Canonicalize target/threat aliases in mission context. A physical site should not survive as both a raw mark and a planner label (`SA5` plus `5`, duplicate `11`, prior-event `SA-10 East` plus current `SA-10 Alpha`). Planner `map_mark_overrides` win.
- For phased missions, store mandatory objectives, optional follow-on objectives, movement gates, hold criteria, and named attack points explicitly. If a subset of an ordered flight list branches to another CAP, name those callsigns directly instead of encoding the instruction as an unstable ordinal.
- When editing an INI/PPT threat point, verify that its numeric type matches the actual system (`11` for SA-11). A display label is not a substitute for the correct threat type.

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

For multiple player packages in one operation, synthesize package-specific folders for evidence and package tables, then build the combined root player brief:

```powershell
python .\scripts\build_combined_player_brief.py `
  --out ".\outputs\<prefix>\generated_briefing.md" `
  --copy-to ".\outputs\<prefix>\player_briefing_combined.md" `
  --synthesis ".\outputs\<prefix>\briefing_synthesis.json" --package-id <primary-package-id> `
  --synthesis ".\outputs\<prefix>\pkg<second-package-id>\briefing_synthesis.json" --package-id <second-package-id>
```

Then render combined deck-facing products with repeated `--synthesis`; promote the final root `player_briefing_combined.md`, `generated_briefing.md`, and numbered `briefing_images` as the unified operation.

After regenerating package syntheses, explicitly re-sync the deck-facing root briefs. Package-specific markdown is evidence only; the root `player_briefing_combined.md` and `generated_briefing.md` are what the slide designer normally consumes. Do not let old hand-edited package tables survive after synthesis changes. Validate the root package composition table against the regenerated synthesis and BMS-equivalent timing before delivery.

Use the guarded slide image pack renderer for current final assets:

```powershell
python .\scripts\render_bms_slide_image_pack.py `
  --synthesis ".\outputs\<prefix>\briefing_synthesis.json" --package-id <primary-package-id> `
  --synthesis ".\outputs\<prefix>\pkg<second-package-id>\briefing_synthesis.json" --package-id <second-package-id> `
  --cam-decode ".\outputs\<prefix>\cam_decode.json" `
  --campaign-dir "<campaign-dir>" `
  --out-dir ".\outputs\<prefix>\briefing_images" `
  --object-dir "<theater-folder>\TerrData\Objects" `
  --camp-obj-data "<campaign-dir>\CampObjData.XML" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png"
```

Finish with validation:

```powershell
python .\scripts\validate_bms_briefing_outputs.py ".\outputs\<prefix>" `
  --package-id <primary-package-id> `
  --package-id <second-package-id>
```

Do not rely on a fresh `manifest.json` alone as proof that images are current; it must point at the current canonical files, not stale `slide_v*` or package-specific paths.

During iteration, render only the product being corrected. For example, add `--product weather` to the guarded pack command for a weather-only change. The pack renderer stages candidates in a temporary directory, promotes them only after the selected render succeeds, and archives every changed canonical predecessor under `outputs/<prefix>/_image_history/<UTC timestamp>`. Do not bypass this with manual deletion or a whole-pack rerender when only one product failed.

## 3. Correlate Planner Intent

Correlate the planner prompt with decoded data:

- Package IDs and flights.
- Event name/codename and how it should appear in the player-facing title.
- Callsigns, aircraft count/type, role, takeoff, TOT, loadout, laser codes, TACAN. Display mission execution timing as Zulu in player-facing briefs; reserve local time for weather/daylight assessment.
- Current save clock from extraction. The pyopencam provider should decode `.cmp current_time`, derive current Zulu from campaign time modulo day, and derive local time from the theater UTC offset. Use BMS UI clock screenshots only as a sanity check or `clock_override` fallback, not as the normal source.
- Package-list target timing by role. Match BMS `Tgt` semantics from the tactical waypoint (`WP_STRIKE`/`WP_SEAD`/`WP_ESCORT`/first `WP_CAP`) instead of assuming raw package `time_on_target` is always display-equivalent.
- Radio comm plan: TACTICAL 1/2 or package nets, ABM/AWACS net, primary/backup presets, check-in sequence, and comm priority. Store it in mission context as `comm_plan`; do not infer it from prior events unless the planner explicitly says to reuse it.
- For generated BMS radio frequencies, join decoded current-save package callsigns to the current campaign theater `RadioMap.dat`. Use `UHF 1` as the callsign/package tactical source, `VHF` as intra-flight, and `UHF 2` as backup unless a decoded `.frc`/DTC preset source provides more precise numbered presets. Never copy frequency values from a previous event deck as current-mission data.
- Per-ship A-A TACAN assignments. Generate them deterministically in player-package order unless the planner explicitly overrides a flight: package 1 reserves flight bases `15-19`, package 2 reserves `25-29`, and later packages continue with a package stride of 10. Within a four-ship flight whose base is `N`, assign `N X / (N+63) X / (N+63) Y / N Y` to ships #1-#4. Thus package 1 flight 1 is `15X / 78X / 78Y / 15Y`, flight 2 is `16X / 79X / 79Y / 16Y`, and package 2 flight 1 is `25X / 88X / 88Y / 25Y`. Store the scheme under top-level `a2a_tacan_scheme`; explicit package-level `a2a_tacan_assignments` may override generated values but must not leave other flights blank.
- AWACS/tanker callsigns, aircraft, TACAN, tracks, and whether they matter to the player package. Use bullseye track references in the player-facing brief when available; reserve raw grid tracks for appendices/workups.
- Flight plan steerpoints and mission actions.
- INI/PPT marks, named marks, drawn lines, route labels, threat steerpoints, and bullseye.
- Main-brief prose should use planner names such as `Wolf`, `Honey`, `IP1`, and `EAST`, not flight-relative steerpoint numbers. Steerpoint indices belong in the coordinate/flight-plan appendix because they differ by flight and change during planning.
- Weather at takeoff, target, and landing: local time/day-night, conditions, cloud base, contrail layer, temp, visibility, wind.
- Weather target anchors. When the campaign package has no reliable decoded tactical target, store explicit package-level `weather_target_labels` that resolve through mission-context `map_mark_overrides`. For a phased mission, sample the mission-essential first target gate; never average ingress, IP, CAP, optional-target, and support marks into one artificial target point.
- Enemy situation around the actual target area.

For timing-sensitive briefs, inspect `cam_decode.json` after extraction and confirm the decoded campaign clock fields are populated: `current_time_z`, `current_time_local`, `clock_base_hhmm`, and `clock_source`. Normal saves should synthesize without `clock_override`; use an override only as a documented fallback or regression check when extraction is missing/wrong. Package table `T/O` and `TOT/Tgt` values in the root player brief must match the regenerated synthesis, not stale markdown.

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

When the planner asks for 3D target imagery, offer it as an optional add-on after the 2D mission-truth maps are stable. Use 3D to explain terrain, runway/target geometry, low-level ingress, and ADA placement; do not let it replace the route/threat/target/objective maps unless the user explicitly chooses it for the deck.

3D render baseline:

```powershell
python .\scripts\render_bms_3d_target_area.py `
  --synthesis ".\outputs\<prefix>\pkg<package-id>\briefing_synthesis.json" `
  --cam-decode ".\outputs\<prefix>\cam_decode.json" `
  --package-id <package-id> `
  --heightmap "C:\Falcon BMS 4.38\Data\TerrData\Korea\NewTerrain\HeightMaps\HeightMap.raw" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --crop-label BLU ORION 10W 10E SA6 `
  --camp-obj-data "<campaign-dir>\CampObjData.XML" `
  --object-dir "C:\Falcon BMS 4.38\Data\TerrData\Objects" `
  --view-preset attack-geometry `
  --show-objective-features `
  --objective-feature-filter "Gimhae Intl Airport|Gimhae VOR" `
  --objective-feature-mode runway-and-buildings `
  --out ".\outputs\<prefix>\briefing_images\05_3d_objective_area_close_labels.png"
```

`attack-geometry` is the normal player-facing preset. It encodes the accepted Event 740 close terrain/camera treatment and automatically adds a projected N/E compass plus a `FRIENDLY PACKAGE FROM <sector>` pointer derived from the selected package routes. If route data is unavailable, supply `--friendly-origin-grid GRID_X GRID_Y`; do not silently ship a player-facing 3D view without approach direction. The `diagnostic` preset and `--no-compass`/`--no-friendly-approach` switches are for troubleshooting only.

Standard 2D route, target, objective, and weather products are north-up and should omit a compass while retaining their distance scale. A compass is mandatory only when orientation is not implicit, such as the oblique 3D attack-geometry products above or a deliberately rotated special-purpose 2D map.

For broader ingress/target-area building context, do not render every objective feature blindly. Use an exclude filter for roads/bridges/clutter, a per-objective cap, and lower opacity/height:

```powershell
--objective-feature-exclude "Bridge|Overpass|Road|Highway|Exp|VOR|HAWK" `
--objective-feature-max-per-objective 10 `
--objective-feature-limit 520 `
--objective-feature-alpha 0.58 `
--objective-feature-height-scale 0.72
```

If the close-up contains irrelevant edge marks, suppress them with `--hide-mark-label <label>` instead of changing the crop until the target geometry is lost. Keep ADA pins, red ground squares, labels, and rings tied to decoded active-radar battalion coordinates, not just INI/PPT centers.

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
  --synthesis ".\outputs\<prefix>\pkg<primary-package-id>\briefing_synthesis.json" --package-id <primary-package-id> `
  --synthesis ".\outputs\<prefix>\pkg<second-package-id>\briefing_synthesis.json" --package-id <second-package-id> `
  --cam-decode ".\outputs\<prefix>\cam_decode.json" `
  --campaign-dir "<campaign-dir>" `
  --fmap "<campaign-dir>\<prefix>.fmap" `
  --map-source "C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png" `
  --feet-per-grid 3280.84 `
  --margin-grid 24 `
  --scale 8 `
  --aspect-ratio 16:9 `
  --no-show-footer `
  --weather-alpha 112 `
  --player-route-opacity 0.20 `
  --ao-label "PACKAGE AO" `
  --route-label-font-size 36 `
  --ini-label-font-size 54 `
  --weather-label-font-size 42 `
  --ao-label-font-size 44 `
  --scale-label-font-size 52 `
  --out ".\outputs\<prefix>\slide_v1_3\briefing_images\04_weather_map.png"
```

The weather renderer uses consolidated mission-context `map_flow_groups` by default, matching the route overview. It falls back to all player flight plans only when no valid consolidated groups exist; use `--no-consolidated-routes` only when a full per-flight weather reference is genuinely required. AWACS and tanker routes remain a separate always-on layer and are deduplicated across repeated packages. Preserve the original primary-package flight-plan bounds: additional packages and support routes must not participate in crop calculation, and their geometry should be clipped so the consolidated layer never causes a surprise zoom change.

Keep `--player-route-opacity 0.20` as the normal weather-map default. It fades only player package arrows and their labels; do not fade support tracks or weather annotations with the same control.

For multi-package decks, pass every player package to the weather renderer as shown above and promote one deck-facing `04_weather_map.png` unless the user asks for separate weather slides.

## 8. Package And Publish

Collect final images:

```powershell
python .\scripts\collect_bms_image_pack.py ".\outputs\<prefix>"
```

Do not export Claude/design bundles, commit, or push until explicitly prompted.

## 9. Easter Egg: Morale/Hype Video

This is not part of the normal briefing workflow. Only make a pre-sortie hype
video when the user explicitly asks for a hype/video/Ace Combat style artifact,
asks for something ridiculous, or is clearly frustrated after the serious brief
and map assets are stable enough that a morale cut is the best next action.

Use the current mission brief and numbered image pack as source truth. Do not
reuse narration from a prior event. For best results, write a mission-specific
JSON script in the output folder with short scene subtitles and a separate
voice-line JSON file. Keep it theatrical, but do not introduce tactical facts
that are not in the current brief or planner context.

Render the silent video:

```powershell
python .\scripts\render_pre_sortie_video.py `
  --brief ".\outputs\<prefix>\player_briefing_combined.md" `
  --image-dir ".\outputs\<prefix>\briefing_images" `
  --script ".\outputs\<prefix>\hype_video_script.json" `
  --arcade-chaos `
  --out ".\outputs\<prefix>\briefing_images\<prefix>_pre_sortie_hype_silent.mp4"
```

Add voice, music, and SFX. Prefer a user-provided/cleared music file when
available; otherwise use generated SFX/music only. Keep voices spaced by the
script's automatic placement and inspect `voice_placements.txt` if lines feel
crowded.

```powershell
python .\scripts\add_pre_sortie_audio.py `
  --video ".\outputs\<prefix>\briefing_images\<prefix>_pre_sortie_hype_silent.mp4" `
  --voice-lines ".\outputs\<prefix>\hype_voice_lines.json" `
  --music-file ".\assets\music\<cleared-track>.mp3" `
  --voice-provider edge `
  --keep-work ".\outputs\<prefix>\briefing_images\audio_stems_hype" `
  --out ".\outputs\<prefix>\briefing_images\<prefix>_pre_sortie_hype.mp4"
```

If a platform needs a sub-10 MB file, make a separate compressed derivative
instead of overwriting the source render:

```powershell
ffmpeg -y -i ".\outputs\<prefix>\briefing_images\<prefix>_pre_sortie_hype.mp4" `
  -vf "scale=1280:-2" -c:v libx264 -b:v 1100k -preset slow `
  -c:a aac -b:a 96k -movflags +faststart `
  ".\outputs\<prefix>\briefing_images\<prefix>_pre_sortie_hype_under10mb.mp4"
```
