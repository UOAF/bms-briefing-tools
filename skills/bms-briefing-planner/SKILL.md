---
name: bms-briefing-planner
description: Produce Falcon BMS mission briefing workups, player-facing briefs, slide-ready map image packs, weather maps, optional 3D target-area imagery, and hidden over-the-top pre-sortie hype videos from a campaign save, package IDs, mission INI/data-cartridge marks, and mission-planner intent. Use when the user asks to make, revise, QA, or package a BMS briefing/deck, especially for UOAF-style BMS campaign saves, package flow maps, threat maps, objective maps, 3D ingress/target views, weather maps, Claude/design handoff bundles, morale/hype videos, or repeatable BMS briefing generation.
---

# BMS Briefing Planner

## Operating Rule

Start each mission from the current planner prompt and campaign files. Do not carry tactical facts from a prior mission unless the user explicitly restates them or points to a shared campaign context file. Treat old outputs as style/process references, not mission truth.

Use this skill as a briefing production workflow:

1. Capture planner intent.
2. Decode and correlate campaign/INI/weather data.
3. Build a transitional workup that preserves evidence.
4. Produce a clean player-facing brief.
5. Render and QA the numbered image pack.
6. Wait for explicit user approval before generating Claude/design bundles, committing, or pushing.

Default package scope: when the mission maker identifies more than one human
or player package, treat those packages as one unified operation and one
player-facing briefing unless the mission maker explicitly asks for separate
briefs. Package-specific generated drafts and workups are allowed as evidence,
but the root mission brief and deck-facing image pack should be combined.

## Read These References

- Read [workflow.md](references/workflow.md) before running a new mission from campaign data.
- Read [brief-criteria.md](references/brief-criteria.md) before drafting or revising player-facing brief text.
- Read [image-qa.md](references/image-qa.md) before rendering, rerendering, or judging briefing images.

## Planner Intake

Ask for missing mission-planner context only when it cannot be discovered from files or a reasonable assumption would damage the brief. Prefer one concise question at a time.

Minimum intake:

- Campaign save prefix and campaign directory.
- Event number and operation/event name. If the user has not supplied a name and asks for one, propose a short evocative `Operation: <Name>` title that fits the mission tone.
- Player package ID or package IDs.
- Player flights/callsigns and their intended roles.
- Radio frequency plan: TACTICAL nets, ABM/AWACS net, preset numbers, backup nets, check-in flow, and comm priority when known.
- A-A TACAN for player flights. Apply the deterministic package-block scheme by default: package 1 uses flight bases 15-19, package 2 uses 25-29, and each four-ship flight uses `baseX / (base+63)X / (base+63)Y / baseY`. Keep per-ship A-A TACAN separate from tanker/package TACAN.
- Named INI/data-cartridge marks and their tactical meaning.
- Commander intent, priorities, alternates, fallback logic, and deconfliction notes.
- Explicit `weather_target_labels` for each player package when the tactical target is represented by planner marks rather than a decoded campaign target. Use the mission-essential target complex, not a centroid of route, CAP, IP, or support marks.
- Any deck/design constraints, but do not generate the design handoff until requested.

If the user narrates corrections after an initial render, incorporate them as planner intent and update the mission-context file. Do not hard-code those facts into reusable code.

Normalize tactical aliases before writing or mapping: one physical threat/target gets one current-mission label. Do not show both raw and planner aliases such as `SA5` and `5`, or a prior-event name and its current phase name. Use named tactical points in the main brief; keep flight-relative steerpoint numbers in appendices.

Player-facing briefs should use bullseye references for AWACS/tanker/support
tracks whenever bullseye data is available. Keep raw grid coordinates for those
tracks in appendices or workups, not in the main support table.

## Data Policy

Prefer `pyopencam` for CAM decode. Use BMSUtils only as a read-only compatibility fallback or regression oracle when pyopencam cannot provide a needed field yet. If a required brief field still depends on fallback parsing, say that in the transitional workup, not in the player-facing brief.

Use BMS 4.38 real-life grid scale by default: `3280.84 ft/grid`. Avoid estimated offsets when a proper BMS projection or decoded grid coordinate is available.

## Output Contract

For a mission output folder such as `outputs/<prefix>`, produce:

- `briefing_workup.md`: detailed transitional analysis with data provenance, unresolved issues, and coordinate appendices.
- `player_briefing_combined.md` and `generated_briefing.md`: player-facing mission brief with no dev comments. For multi-package human/player operations, both root files should represent the unified operation rather than one package's draft. Include the operation/event name alongside the event number in the title, for example `Event 740: Operation Glass Anvil Player Briefing`.
- `briefing_images/01_route_threat_map.png`
- `briefing_images/02_target_area_map.png`
- `briefing_images/03_objective_area_map.png`
- `briefing_images/manifest.json`
- Optional `briefing_images/04_weather_map.png` when weather data is available.
- Optional 3D objective imagery when the planner asks for it or when terrain/runway/target geometry is tactically important. Keep 3D imagery as an extra deliverable or named variant unless the deck explicitly wants it promoted into the numbered pack.
- Optional easter-egg pre-sortie video only when the user explicitly wants a hype/video/Ace Combat style artifact, or when the user is clearly frustrated and the serious mission products are already stable enough that a cathartic hype cut is the best next move.

Keep useful outputs in the standard `briefing_images` folder. Avoid scattering final assets across diagnostic folders. Use variant folders such as `slide_v1_3` only as versioned working sources, then collect/promote the selected set.

For normal local/community workflow runs, prefer the guarded scripts:

- `scripts/build_combined_player_brief.py` after package-specific synthesis, so root `generated_briefing.md` and `player_briefing_combined.md` are synchronized and combined.
- `scripts/render_bms_slide_image_pack.py` for the canonical numbered image pack, so final images are written directly into `briefing_images` instead of discovered from stale variant folders.
- `scripts/validate_bms_briefing_outputs.py` before handoff, so raw planner transcript, unresolved decoder labels, stale `slide_v*` manifest sources, missing package IDs, and oversized key images fail the run.

## Required Validation

Before final delivery:

- Run syntax checks on touched Python scripts: `python -m py_compile scripts\*.py` or the specific files changed.
- Run the relevant render/collection command again after changing renderer behavior.
- Rerender only the failed/requested product during image iteration. The guarded pack renderer must stage candidates before promotion and preserve every changed canonical predecessor under `_image_history`; never delete approved images or regenerate unrelated maps for a weather-only/3D-only correction.
- Confirm extracted campaign clock data is present in `cam_decode.json` when timing appears in the brief: `current_time_z`, `current_time_local`, `clock_base_hhmm`, and `clock_source`.
- Confirm each weather `Target Area` sample resolves to the planner-defined primary target anchors when `weather_target_labels` are present; reject a loose centroid of unrelated PPTs.
- Confirm root deck-facing brief files are synchronized with regenerated package synthesis, especially package composition `T/O (Z)` and `TOT (Z)` tables.
- Confirm every player flight has the deterministic four-ship A-A TACAN assignment for its package and flight order; `not assigned` is a validation failure.
- Confirm the root player brief is not just the primary package. Multi-package player operations must mention every requested package ID in both `generated_briefing.md` and `player_briefing_combined.md`.
- Confirm player-facing markdown does not contain raw transcript or decoder/meta phrases such as `Commander context`, `Unresolved target`, `No named tactical target listed`, or weather sidecar warnings.
- Open or preview every final map at slide-like size.
- Keep the weather map operationally legible: when mission-context `map_flow_groups` exist, reuse those consolidated package-flow arrows instead of drawing every player flight plan. Draw all individual flight routes only when consolidated flow is unavailable or explicitly disabled.
- Render weather-map player routes and their route labels at 20% opacity by default so they provide geographic context without competing with weather cells and weather-sample callouts. Keep support tracks and weather annotations on separate layers.
- Show decoded AWACS and tanker routes consistently on the weather map. Deduplicate support assets shared across packages and retain readable callsign/role labels, but never let outlying support tracks expand or otherwise change the established player-route crop.
- Treat standard 2D briefing maps as north-up and omit the compass by default. Preserve the distance scale. Use an orientation graphic only for a deliberately rotated/nonstandard 2D product or an oblique 3D view.
- Confirm `01_route_threat_map.png` is below the user/platform size limit when one exists; keep it below 20 MB by default.
- Confirm `briefing_images/manifest.json` points to the selected current variant, not stale assets.
- For optional 3D target imagery, use the renderer's `attack-geometry` preset unless the planner asks for another style. Confirm edge-to-edge terrain, a readable N/E compass, a friendly-package approach pointer derived from decoded routes, and ADA pins/ground markers/labels/WEZ rings tied to the same decoded active-radar coordinate.
- For optional hype video, keep mission facts derived from the current brief/map pack, use mission-specific voice lines rather than old narration, duck music/SFX under voice, and produce a share-friendly under-10 MB variant when requested.
- State clearly if a section could not be generated because required source data is absent.

## Design Handoff Gate

Do not create or upload Claude/design packages during initial briefing iteration. The first phase is mission truth and map readability. Only run design bundle/export/upload tools when the user explicitly asks for the Claude/design handoff.
