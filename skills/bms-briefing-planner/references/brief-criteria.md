# Brief Criteria

## Overall Brief

A good BMS player brief is a commander-facing interpretation of the mission, backed by decoded data. It is not a transcript of every campaign object.

Required sections when data is available:

- Title with event number and operation/event name when known, for example `Event 740: Operation Glass Anvil Player Briefing`.
- Mission summary: two to four sentences.
- Commander intent and flight contracts.
- Player package composition.
- AWACS/tanker support that matters to the package.
- Meteorology for takeoff, target, and landing.
- Bullseye and key named references.
- Strategic air defense.
- Enemy air threat estimate.
- Other package factors only when they affect or interact with the player target area.
- Comm ladder.
- Coordinate appendix.
- Map products list.

## Player-Facing Voice

Use clear tactical language:

- Say what the package must do, where, and why.
- Use the operation/event name as an identity marker, but keep the tactical brief clear and concrete.
- Name the flight responsible for each task.
- Use planner terms when provided, but expand ambiguous labels once.
- Use concise tables for loadout, timing, comms, and coordinates.

Avoid:

- Development comments such as `weather unavailable`, `decoder failed`, `no FMAP sidecar`, or script caveats.
- Omniscient enemy ATO details, package IDs, callsigns, or exact enemy tasking unless they are active/current contacts already in the battlespace.
- Old mission context.
- Raw labels such as `mark 15` without explanation. Prefer `PPT 15`, `SA-6 mark`, `western objective reference`, or a planner-provided name.

## Package Composition Criteria

Include for player packages:

- Callsign.
- Number and aircraft type.
- Mission role.
- Takeoff time and TOT in Zulu. Use a `Z` suffix and label columns as `T/O (Z)` and `TOT (Z)`.
- Loadout summarized by useful weapons, sensors, tanks.
- Laser codes where decoded/applicable.
- A-A TACAN channels per ship when supplied by the planner, formatted compactly in package composition, for example `15X / 78X / 78Y / 15Y` for ships #1-#4.
- Tanker/package TACAN channels where decoded/applicable. Do not merge tanker TACAN and per-ship A-A TACAN into one ambiguous field.
- Tactical assignment and remarks.

Include non-player packages only if they matter:

- AWACS/tanker supporting the package.
- Express AWACS/tanker station tracks as bullseye references when bullseye is available, for example `BE 298/118 to BE 311/111`; keep raw grids in the coordinate appendix/workup rather than the player-facing support table.
- Escorts/screens tied to the package.
- Friendly package activity that crosses, deconflicts with, or affects the target area.
- Other flights overhead or clearly vectoring toward the target area within relevant time/range.

Do not include irrelevant friendly package clutter.

## Communications Criteria

Comm ladder means the radio plan first:

- Frequencies/nets when supplied: agency/net, primary frequency, primary preset, backup preset, and callsign/remarks.
- Check-in content: flight callsign, number/type as required, position, ordnance, playtime, capabilities, abort code, and a sample ABM check-in call when useful.
- Comm priority: normally fighter engagement first, contract/package-critical calls second, then SEAD/strike coordination or other mission-specific priorities.
- ABM/AWACS picture rule: state whether player packages share one ABM picture and where cross-package calls should go.

Keep Link 16 data separate as `Link 16 & Nets`. Link 16 STN/F2F/Mission/EW data is useful, but it must not replace the radio frequency/check-in/priority ladder. Do not invent current-mission frequencies from a prior event; put missing frequency-plan needs in the workup/review notes, not as fake player-facing frequencies.

## Enemy Situation Criteria

Separate three concepts:

- Strategic ADA: player-facing known SAM threats with active tracking radars.
- Enemy air threat estimate: likely origin axes from active enemy airbases/squadrons and aircraft capability.
- Active air contacts: current campaign-time contacts within or vectoring into 30 NM of the target area.

Strategic ADA:

- Include enemy strategic SAMs only.
- Exclude friendly air defenses.
- Require active tracking radar where applicable: SA-2 Fan Song, SA-3 Low Blow, SA-5 Square Pair, SA-6 Straight Flush, SA-10 Flap Lid, SA-11/17 relevant fire-control radar.
- Show type, radar, grid, bullseye, nearest tactical anchor, range, and strength/status when decoded.
- Avoid tactical SHORAD unless the planner specifically asks for tactical/low-altitude threats.

Enemy airbases:

- Include active enemy airbases within the agreed radius, normally 100 NM.
- Exclude airbases that are 0% operational/destroyed.
- Include likely aircraft types and origin direction.
- Use human-readable airbase names, not `AB ###`.
- Do not infer specific launches from inactive runway/base data.

Enemy air:

- Generalize airbase threat axes by capability and origin direction.
- Do not reveal enemy package IDs, callsigns, exact ATO, or exact mission timing from decoded enemy packages.
- Mention active overhead/vectoring contacts within 30 NM of target-area anchors as current tactical contacts, with aircraft type, sector, range, and why they matter.

## Weather Criteria

Include weather at takeoff, target area, and landing:

- Local time and day/night. Weather is the one player-facing section that should use local time because it supports daylight and weather interpretation.
- Conditions.
- Cloud base. Use the BMS/UI weather-layer value from FMAP stratus base, rounded to the nearest thousand feet. Do not substitute the raw per-cell cumulus-base/fog-like field as cloud base; in `739pre`, that bad substitution produced 4,241/3,781 ft when the BMS UI showed 38,000 ft.
- Contrail layer.
- Temperature.
- Visibility.
- Wind.
- Basis point used for sampling.

Keep raw FMAP weather fields, such as raw cumulus base, in the transitional workup/JSON when useful for traceability. Do not expose them as player-facing cloud base unless the field has been confirmed to match the BMS UI.

Generate a weather map when the FMAP/weather data is available. If weather data is absent, omit the player-facing weather map rather than adding a dev note to the player brief.

## Timing Criteria

Use Zulu for mission execution timing:

- Package composition T/O and TOT.
- Flight steerpoint/coordinate appendix arrival times.
- AWACS/tanker station timing.
- Active contact vector timing and other package deconfliction timing.

Use local time only for meteorology/day-night assessment. For KTO/Bear Trap style Korea missions, convert local mission HHMM to Zulu by subtracting 9 hours unless the campaign data provides a more specific UTC offset.

## Coordinates Criteria

Use coordinates to support planning without cluttering the human read:

- Put detailed coordinates in a separate appendix.
- Include grid and bullseye where available.
- Include flight steerpoints, INI/PPT marks, strategic ADA, active enemy airbase origins, AWACS/tanker tracks, and relevant support anchors.
- For AWACS/tanker/support tracks, use bullseye as the primary player-facing reference and include grids only as appendix/provenance data.
- Explain ambiguous marks once. Example: `PPT 15 is an unnamed data-cartridge mark near the SA-6/Joule objective area.`
