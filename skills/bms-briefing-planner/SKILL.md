---
name: bms-briefing-planner
description: Produce Falcon BMS mission briefing workups, player-facing briefs, slide-ready map image packs, weather maps, and optional 3D target-area imagery from a campaign save, package IDs, mission INI/data-cartridge marks, and mission-planner intent. Use when the user asks to make, revise, QA, or package a BMS briefing/deck, especially for UOAF-style BMS campaign saves, package flow maps, threat maps, objective maps, 3D ingress/target views, weather maps, Claude/design handoff bundles, or repeatable BMS briefing generation.
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
- A-A TACAN plan or generation pattern for player flights, when provided. Keep per-ship A-A TACAN separate from tanker/package TACAN.
- Named INI/data-cartridge marks and their tactical meaning.
- Commander intent, priorities, alternates, fallback logic, and deconfliction notes.
- Any deck/design constraints, but do not generate the design handoff until requested.

If the user narrates corrections after an initial render, incorporate them as planner intent and update the mission-context file. Do not hard-code those facts into reusable code.

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

Keep useful outputs in the standard `briefing_images` folder. Avoid scattering final assets across diagnostic folders. Use variant folders such as `slide_v1_3` only as versioned working sources, then collect/promote the selected set.

## Required Validation

Before final delivery:

- Run syntax checks on touched Python scripts: `python -m py_compile scripts\*.py` or the specific files changed.
- Run the relevant render/collection command again after changing renderer behavior.
- Confirm extracted campaign clock data is present in `cam_decode.json` when timing appears in the brief: `current_time_z`, `current_time_local`, `clock_base_hhmm`, and `clock_source`.
- Confirm root deck-facing brief files are synchronized with regenerated package synthesis, especially package composition `T/O (Z)` and `TOT (Z)` tables.
- Open or preview every final map at slide-like size.
- Confirm `01_route_threat_map.png` is below the user/platform size limit when one exists; keep it below 20 MB by default.
- Confirm `briefing_images/manifest.json` points to the selected current variant, not stale assets.
- For optional 3D target imagery, confirm the view is slide-readable and that ADA pins, ground markers, labels, and WEZ rings use the same decoded active-radar coordinate.
- State clearly if a section could not be generated because required source data is absent.

## Design Handoff Gate

Do not create or upload Claude/design packages during initial briefing iteration. The first phase is mission truth and map readability. Only run design bundle/export/upload tools when the user explicitly asks for the Claude/design handoff.
