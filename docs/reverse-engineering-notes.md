# Reverse-Engineering Notes

## Framing

The human-made Google Slides briefings are not canonical serializations of the
campaign save. They are human interpretations of the mission state in the
campaign file, with additional commander intent, tactics, contracts, risk
judgment, and editorial choices layered on top.

That means the extraction pipeline should separate:

- raw BMS facts: packages, flights, waypoints, timings, targets, bases,
  loadouts, comms, Link 16, weather, and planning overlays;
- inferred briefing structure: operating area, package flow, coordination
  tables, threat summaries, and route/target diagrams;
- human-authored judgment: commander intent, ALR, contracts, priorities,
  tactical recommendations, and narrative context.

The existing decks are best used as labeled examples for what humans care about
and how they present it, not as byte-for-byte ground truth.

## Matched 718 sample

The useful matched pair is:

- Campaign bundle: `C:\Falcon BMS 4.38\Data\Campaign\718pre.*`
- Reference briefing: `https://docs.google.com/presentation/d/1sV9xxCRPyaAeumhVlZdfAq7CFWqq8Ch9Gk0d7h3EnTc/edit`

`723PRE.ini` exists locally, but the matching `723pre.cam/.frc/.his/.l16.txtpb`
bundle is not present.

## File roles observed so far

- `*.ini`: BMS DTC/planning data. Contains steerpoint targets, preplanned target
  rings, map labels, and drawn line points. For 718 this directly explains the
  briefing map labels A/B/C/D/IP and SAM rings.
- `*.l16.txtpb`: Text protobuf-like Link 16 network. Contains team nets plus
  per-flight numeric identifiers, STN numbers, mission/fighter-to-fighter
  channels, EW channel, and team.
- `*.twx`: Binary weather/time sidecar. Header starts with small integers; for
  718 the first four are `8, 2025, 10, 7`.
- `*.cam`: Primary campaign container. For 718 the embedded directory starts at
  byte `238245` and contains `.cmp`, `.obd`, `.uni`, `.tea`, `.evt`, `.plt`,
  `.pst`, `.pol`, and `.ver`. The `.ver` section is ASCII `109`.
- embedded `.tea`: Team state. `BMSUtils.TeaFile` decodes it directly once the
  section is isolated.
- embedded `.uni`: Unit/package/flight graph. `BMSUtils.UniFile` decodes it with
  the Korea `Falcon4_CT.xml` class table.
- embedded `.obd`: Objective delta state, not the base objective table.
  `BMSUtils.ObdFile` decodes owner/supply/fuel/loss/status deltas for objective
  VU IDs.
- embedded `.cmp`: Campaign metadata. Still needs structured extraction.
- embedded `.obj`: Objective table reader exists in Mission Commander, but this
  718 save does not embed a `.obj` section.
- `*.frc` and `*.his`: Binary sidecars. `.his` likely includes campaign history
  and events; `.frc` likely force/roster state.
- `*.fmap`: Binary weather map.
- `*.iff`: Binary/text-ish IFF data.

## BMSUtils/Mission Commander findings

The installed Mission Commander build includes useful parser classes in:

`C:\Falcon BMS 4.38\mc\BMSUtils.dll`

It is 32-bit, so it must be inspected from the 32-bit PowerShell host:

`C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe`

Relevant public classes and fields found by reflection:

- `BMSUtils.Package`: has `elements`, `element[]`, `flights`, package takeoff
  and target point fields, ingress/egress waypoint arrays, `package_flags`, and
  base unit fields.
- `BMSUtils.Flight`: has `time_on_target`, `mission_over_time`, `mission`,
  `package`, `squadron`, `callsign_id`, `callsign_num`, `TacanChannel`,
  `TacanBand`, loadout/weapon fields, and waypoint arrays.
- `BMSUtils.Waypoint`: has `GridX`, `GridY`, `GridZ`, `Arrive`, `Action`,
  `RouteAction`, `Speed`, `TargetID`, and `Depart`.
- `BMSUtils.UniFile`, `ObjFile`, and `TeaFile` are likely the embedded readers
  for unit, objective, and team sections.

Directly feeding the whole `.cam` bytes to `TeaFile`, `ObjFile`, `ObdFile`, or
`UniFile` is unsafe. The top-level `.cam` must be split by its embedded
directory first.

The first little-endian DWORD in `718pre.cam` is the directory offset. Directory
layout:

- DWORD `directorOffset` at file offset 0.
- DWORD embedded-file count at `directorOffset`.
- Repeated entries: 1-byte name length, filename bytes, DWORD file offset, DWORD
  file size.

For 718:

- `718pre.cmp`: offset `4`, size `8283`
- `718pre.obd`: offset `8287`, size `11016`
- `718pre.uni`: offset `19303`, size `195251`
- `718pre.tea`: offset `214554`, size `14738`
- `718pre.evt`: offset `229292`, size `90`
- `718pre.plt`: offset `229382`, size `3373`
- `718pre.pst`: offset `232755`, size `3916`
- `718pre.pol`: offset `236671`, size `1571`
- `718pre.ver`: offset `238242`, size `3`

Structured decode results for 718:

- Teams: 8 (`XX`, `U.S.`, `ROK`, `Japan`, `CIS`, `PRC`, `DPRK`, `NATO`)
- Objective deltas: 1378
- Units: 1216 total
- Flights: 331
- Packages: 301
- Squadrons: 95
- Battalions: 435
- Brigades: 43
- Task forces: 11

## Current synthesis layer

The working synthesis path is:

1. `extract_bms_briefing.py` collects sidecars, DTC/planning data, deck text
   signals, and optional decoded CAM data.
2. `extract_bms_cam.ps1` splits the `.cam` container, decodes BMSUtils-supported
   sections, and exports teams, objective deltas, squadrons, packages, flights,
   battalions, brigades, and task forces.
3. `synthesize_bms_briefing.py` joins CAM data with `CampObjData.XML`, resolves
   tactical waypoint targets, scores packages, and writes both machine-readable
   synthesis JSON and a Markdown briefing draft.
4. `build_bms_briefing_deck.mjs` turns the synthesis JSON into an editable PPTX
   procedural briefing draft.

For the 718 local save, the reference deck mentions package IDs:

`798, 862, 1434, 1491, 2223, 2455, 2515, 2551, 2905, 4827`

Only `2515` and `2551` are present in the local `718pre.cam`, so the generator
treats the other deck IDs as reference-deck/commander-intent evidence rather
than local package facts.

The target resolver now handles more than objective IDs. A waypoint target can
resolve to:

- a named objective from `CampObjData.XML`;
- a flight, package, squadron, battalion, brigade, or task force from the `.uni`
  unit graph;
- an unresolved target placeholder when no objective/unit match exists.

The synthesis layer also correlates `*.ini` planning geometry to package route
waypoints. INI point coordinates are stored as world feet; for the Korea/UOAF
map, the current practical transform into decoded campaign waypoint grid is:

`grid_x = ini_y / feet_per_grid; grid_y = ini_x / feet_per_grid`

For KTO, `feet_per_grid` is derived from `Theater.txt`: 1024 km over 1024
campaign grid cells. For BMS 4.38, use real-life/international feet:
`3280.84` ft per grid cell. The older 4.37-era BMS-foot conversion was about
`3279.98` ft per grid cell, so keep that only as a legacy compatibility knob.
This follows oakdesign's `falcon-bms-tacview-converter` approach: use the
theater metadata and PROJ projection for exact lat/lon conversion, not
hand-fitted offsets. Reference implementation:
`https://github.com/oakdesign/falcon-bms-tacview-converter/blob/main/src/falcon_toolset.py`.

The `738pretest` save validates the direct theater-derived transform. Panther 3
was moved onto known INI marks: BMS steerpoint 5 through 13 map to
`A/B/C/D/E/F/WCH/GRD/BAR`, and steerpoints 14 through 23 map to the ten
`lineSTPT` Route Black points. The decoder reports zero-based waypoint indices,
so BMS steerpoint 5 is decoder waypoint index 4. Direct theater-grid conversion
lands in the same integer CAM cells for the calibration points, within the
precision expected from decoded integer waypoints. For UOAF 80s `738pre` package
`1883`, this places the human planning marks over the Route Black target area:

- PPTs `A/B/C/D/WCH/E` sit in the target-area cluster.
- `WCH` marks Watchtower, the EWR target of opportunity.
- `F` marks Foxtrot, the alternate target west of the main cluster.
- `GRD` and `BAR` sit outside the objective cluster as west/east CAP references.
- The drawn `lineSTPT` chain is Route Black.

Human commander interpretation can be layered from a mission-context JSON. For
UOAF 80s `738pre` package `1883`, the current context file states:

- Route Black is represented by the pre-planned threat steerpoints.
- The three INT flights divide SAD responsibilities across `A-B`, `B-A`, and
  `B-C-D`.
- `WCH` is Watchtower, an EWR target of opportunity.
- `A-E` include depots supplying enemy maneuver forces.
- `F` / Foxtrot is the alternate target if Route Black has no movers.
- `GRD` / Guardpost is the west CAP area, assigned to Mudhen 3.
- `BAR` / BARRIER is the east CAP area, assigned to Cobra 3.

The package map renderer uses the campaign `Korea.tm` file as a 1024x1024
theater raster. `Korea.tm` is north-up and correlates to decoded campaign
waypoint grid coordinates as `pixel_x = grid_x`,
`pixel_y = 1024 - grid_y`. This matches the in-game Panther 3 route screenshot,
with the package departing Cheongju from the south and running north. That lets
the map script draw full CAM waypoint chains, converted INI PPTs and `lineSTPT`
routes, commander-assigned SAD/CAP geometry, and enemy-only AD rings directly on
the BMS terrain image.

The bundled chart image `Docs\05 Maps\8_KTO_16k_Skyvector.png` uses the same
full-theater extent at 16384x16384, so the same transform applies with a
16-pixels-per-grid source scale.

The map renderer also has zoom modes for briefing graphics. `--crop-mode
target-area` frames the tactical waypoint subset while still drawing the
correlated INI route geometry and enemy-only threat overlays. `--crop-mode
objective-area` frames the INI objective geometry itself, omitting CAP-only PPTs
from the crop and labels so the A-F/WCH target cluster reads as a close-up.

The generated markdown keeps raw spatial evidence in a separate coordinate
appendix. For the focus package, it prints decoded flight steerpoints in campaign
grid coordinates, INI target/PPT/line steerpoints in both source world feet and
converted campaign grid coordinates, nearest package route matches, and resolved
air-defense unit grid coordinates before the resolved location-object
coordinates.

The synthesis layer can also add a first-pass enemy situation and air-defense
estimate when given the theater object directory. It filters enemy battalion/unit
records near Route Black, CAP, SAD, and correlated INI anchors, resolves classes
through `Falcon4_UCD.xml` with `Falcon4_CT.xml` fallback, and resolves vehicle
names through `Falcon4_VCD.xml`. Treat this as a target-area estimate from saved
campaign unit records.

Campaign unit `entityType` values are class-table indices plus 100. Resolve as
`entityType - 100 -> Falcon4_CT.xml -> Falcon4_UCD.xml` before any raw UCD
fallback. This fixed a real false-positive threat bug where DPRK squadrons were
mislabelled as Mirage 2000, F-16, MV-22, and RC-135 records because raw
`entityType` values collided with unrelated UCD ids.

The same threat pass treats enemy airbases as air threats when an enemy squadron
has a nonzero roster, the squadron class resolves as an air unit, its assigned
base objective is an airbase/airstrip/highway-strip class, the base is greater
than 0 percent operational by the decoded objective delta, and the base lies
within the configured 100 NM ring around package/INI anchors. Missing objective
deltas are treated as unknown/assumed usable rather than destroyed. These are
aggregated by base objective so the brief can show which usable enemy bases host
active squadrons near the target area.

Strategic air-defense rows are now gated on live tracking radar equipment in the
unit roster. Resolve the battalion class, read the UCD `RadarVehicle` slot, map
that slot through `VehicleCtIdx_N` to the vehicle name, then decode the
battalion roster as two-bit slots. Only include strategic SAM units when that
radar slot has `current_count > 0`. For the UOAF 80s 738pre package 1883
sample, this keeps seven strategic ADA sites and filters three inactive radar
candidates:

- SA-2 requires Fan Song F.
- SA-3 requires Low Blow.
- SA-6 requires Straight Flush.

## Callsign resolution

Flight records store `callsign_id` plus `callsign_num`. Mission Commander
includes `OldCallsigns.txt`, but theater add-ons can override callsigns in
their campaign `Strings.txt` file. The current decoder reads numeric string ids
`2000 + callsign_id` from `Campaign\Strings.txt` first, then falls back to
`mc\OldCallsigns.txt`.

Useful ids for the 718 briefing:

- `25 Blade`
- `27 Dragon`
- `57 Voodoo`
- `77 Buff`

For UOAF 80s `738pre` package `1883`, the add-on string table resolves the
flight callsigns as:

- `5 Cyborg`
- `4 Warhawk`
- `13 Panther`
- `6 Mudhen`
- `20 Cobra`

## Next parser step

The scalable parser/tooling decision record is
[`scalable-tooling-strategy.md`](scalable-tooling-strategy.md). In short,
`pyopencam` should be treated as the strongest candidate for a future pure-Python
decoder provider, while the Tacview converter is most useful as theater and
projection prior art. Do not vendor either wholesale until licensing,
attribution, adapter boundaries, and regression tests are settled.

The next high-value tasks are richer mission semantics on top of the decoded and
synthesized objects:

- Replace nonzero squadron roster checks with decoded available-airframe counts.
- Aircraft type and squadron/base.
- Loadout/stores and role fit.
- Radio channel assignments; TACAN is decoded from the CAM flight records.
- Push, target, and egress timing validation against BMS UI.
- Target-file details: SAM type, radar names, expected defenses, and target
  building/component status.
- Waypoint-derived map overlays and route diagrams.
- Human-style filtering: identify the packages that matter to the briefing and
  infer commander intent, game plan, contracts, and tactical risk.
