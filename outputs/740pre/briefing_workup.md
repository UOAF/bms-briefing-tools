# Event 740 Briefing Workup

## Source Inputs
- Campaign prefix: `740pre`
- Campaign directory: `C:\Falcon BMS 4.38\Data\Campaign`
- Player packages: `7016`, `7040`
- Mission context: `inputs/740pre-player-packages-context.json`
- CAM decoder: pyopencam provider against local extracted `pyopencam-main`
- Map source: `C:\Falcon BMS 4.38\Docs\05 Maps\8_KTO_16k_Skyvector.png`
- Weather source: `C:\Falcon BMS 4.38\Data\Campaign\740pre.fmap`

## Planner Intent Captured
- Event 739 result carried forward only because the planner stated it: SA-10 South was killed; SA-10 East and SA-10 West remain.
- Package 7016: Panther 1 strikes Orion/Gimhae; Jaguar 4 kills SA-10 West from Blues; Hawkeye 2 escorts Jaguar 4; Jaguar 5 escorts Panther 1; Sawbuck 2 works high from Tiger-Crown against Gimhae-origin fighters.
- Package 7040: Hammer 2 kills SA-10 East from Wolf, with Bando as the pop-up CBU alternate; Devil 5 and Devil 6 cap around Wolf against north/north-northeast fighters.
- Retrograde: southwest toward Tiger, return to medium altitude, RTB after SA-10 West, SA-10 East, and Orion/Gimhae are solved.

## Decode / Correlation Notes
- `740pre.ini` includes valid PPT anchors `TIG`, `CRO`, `BLU`, `WWO`, `BAN`, `SA6`, `SA5`, and three numeric `10` rings.
- The save also includes two out-of-theater PPT transforms: `ORO` and one duplicate `BAN`, both with grid Y above the 1024-map range. These are now flagged as invalid in synthesis and excluded from map crops/labels.
- Orion/Gimhae is still represented by the OCA/strike target around grid `642 / 145`; player-facing brief uses Orion/Gimhae there rather than exposing the invalid PPT coordinate.
- The map renderer found active enemy air-origin axes from Gimhae, Pohang, and an offshore east group. The package-level generated drafts still under-report active enemy airbases through the older airbase-objective summary path, so the combined player brief uses the squadron-origin axis logic reflected on the maps.

## Generated Outputs
- Combined player brief: `outputs/740pre/player_briefing_combined.md`
- Package 7016 detailed draft/workup: `outputs/740pre/pkg7016/`
- Package 7040 detailed draft/workup: `outputs/740pre/pkg7040/`
- Canonical image pack: `outputs/740pre/briefing_images/`
- Slide-size preview/contact sheet: `outputs/740pre/slide_v1_0/preview/contact_sheet.jpg`

## Image QA
- `01_route_threat_map.png`: route overview includes Cheongju/Gunsan departure bases, aggregated package flow, strategic WEZs, and enemy air-origin axes.
- `02_target_area_map.png`: target-area view keeps named anchors, package flow, enemy axes, and threat rings together.
- `03_objective_area_map.png`: tighter Gimhae/SA-10 close-up suppresses route text labels to reduce clutter.
- `04_weather_map.png`: weather overlay uses save-specific FMAP and grey dotted package AO box.
- Route map size is under 20 MB.

## Validation Commands
- `python scripts\extract_bms_briefing.py --campaign-dir "C:\Falcon BMS 4.38\Data\Campaign" --prefix 740pre --out-dir outputs\740pre --decode-cam --cam-decoder pyopencam --pyopencam-root "<local pyopencam-main>" --bms-root "C:\Falcon BMS 4.38" --object-dir "C:\Falcon BMS 4.38\Data\TerrData\Objects"`
- `python scripts\synthesize_bms_briefing.py ... --focus-package 7016 --mission-context inputs\740pre-player-packages-context.json`
- `python scripts\synthesize_bms_briefing.py ... --focus-package 7040 --mission-context inputs\740pre-player-packages-context.json`
- `python scripts\render_bms_enemy_air_threat_map.py ... --combined-out outputs\740pre\slide_v1_0\briefing_images\01_route_threat_map.png`
- `python scripts\render_bms_weather_map.py ... --out outputs\740pre\slide_v1_0\briefing_images\04_weather_map.png`
- `python scripts\collect_bms_image_pack.py outputs\740pre`
