# Event 744 Briefing Iteration Postmortem

## Outcome

Event 744 exposed a workflow problem more than a drawing problem: approved visual decisions were not being captured as durable render inputs, stale source data could be reused without failing, and diagnostic 3D variants lived beside canonical deliverables. The final package now has one manifest-listed image set, current 2D products rebuilt from the latest `744pre.cam`, and reusable guards for the failure modes encountered during this thread.

## User Feedback Audit

### Scope and authority

- The requested deliverable was briefing content and standard image products, not a rendered slide deck.
- Event 743 was context only; Event 744 mission truth came from `744pre.cam`, packages 6939/6957, planner intent, and current INI/weather data.
- Image work had to follow the established BMS/Skyvector style rather than introduce a new generated-art look or substitute texture.

Durable response:

- Deck generation remains behind an explicit handoff gate in the briefing skill.
- Map texture and approved crop are now treated as preserved render contracts during overlay corrections.
- Mission-specific choices live in `inputs/744pre-player-packages-context.json`, not reusable renderer constants.

### Mission semantics

- Plasma 3 is player-facing `DEAD`, despite the campaign-planning artifact that classified it as SEAD.
- Alpha/Bravo missile state is `RED`; SA-10 North is `BLACK`; no exact percentages are exposed.
- Alpha/Bravo use suspected/mobile dotted rings with no broad fill; SA-10 North remains a normal solid threat ring.
- Hawkeye 6 may reliably attack SA-10 North from altitude while still respecting observed radiation/launches.
- Eagles start on the safe STPT 3–4 patrol and advance to STPT 5–6 only after the SA-10 gates are open.
- Plasma 3 must hook south of Killbox 3 and attack north; Hawkeye 6 must follow its coastal 10N attack geometry.
- AI flights execute regardless of Alpha/Bravo status and use low-altitude pop-up/standoff profiles if required.

Durable response:

- Role, supply language, ring state, route geometry, CAP gates, HOLD points, and package colors are stored in mission context.
- The target map uses a dedicated `map_target_flow_groups` contract instead of trying to infer commander intent from mission-type labels.
- The remaining `SEAD` wording in package-flow timing was corrected to `DEAD`.

### Crop, zoom, and clutter

- Package 6939 and 6957 needed stable, separate colors.
- The target map had to use the approved screenshot-like crop and preserve the established Skyvector texture.
- Target labels needed a major reduction and route strokes needed thinning.
- The objective map had to include all extents of KI1/KI2/KI3, west to the AI IPs and east to 10A/10B, with 10N, Pohang, and the offshore group treated as edge cues.
- Cropping was to increase tactical detail, not create blank sidebars, irrelevant eastern terrain, or truncated killboxes.
- Weather had to follow the corrected route/threat geometry without becoming another route-spaghetti chart.

Durable response:

- Exact bounds and label/line multipliers now live under `map_render_profiles`.
- The Event 744 target bounds were removed from reusable Python code.
- The guarded renderer consumes the per-mission profile and embeds its hash in each 2D PNG.
- Weather retains the established player-route crop, uses consolidated flows at 20% opacity, and keeps support tracks from expanding the frame.

### MIL-STD-2525 symbols and unit placement

- Ground units had to be individual battalions at decoded BMS positions, with both enemy and friendly forces visible.
- Unit type text was unnecessary because the symbol itself should communicate type.
- Symbols needed to remain readable, tolerate limited overlap, and use slight staggering only where necessary.
- Mechanized infantry was repeatedly malformed when the X and armor oval were drawn as separate/stacked marks.
- Transparency had to reveal terrain without making the frames or tactical glyphs illegible.
- An apparent hostile tank on the friendly side was unacceptable; affiliation and position required source-level checking.

Durable response:

- `scripts/bms_milstd2525.py` is now the shared normalized glyph source for 2D and 3D.
- Mechanized infantry is contract-tested as one oval plus two diagonals inside the same frame.
- HQ uses the frame staff rather than invented `HQ` interior text.
- Battalion grid coordinates remain decoded coordinates; any display staggering is screen-space with leaders.
- The objective map was rebuilt from the refreshed pyopencam decode and the corrected shared symbols.

### 3D imagery

- Required views were north-up southwest KI1 context and a west-to-east attack perspective from IP C5.
- The views needed IP symbols, decoded units, straight killbox edges, terrain relief, city/building context, and bridges.
- The user rejected style drift, washed-out textures, malformed icons, blur bands, stretched sides, and background-filled gutters.
- Cheongpyeong and bridge/building geometry had to be present when requested.
- The accepted 3D views were not to be replaced by visually worse rerenders merely because a command succeeded.

Durable response:

- A feature-enabled 3D render now requires both CampObjData and the object directory and fails if no features match.
- New 3D PNGs record the complete command, tactical/terrain bounds, current CAM/context hashes, projection, unit count, feature count, and background-fill status.
- Final validation rejects new 3D deliverables that use background fill to disguise side gutters.
- The two accepted Event 744 3D images were preserved. Their missing historical command metadata is explicitly recorded as approved legacy provenance; staged current-save experiments remained in diagnostics because they were visually inferior.

### Source freshness, timing, weather, and airbase identity

- File timestamps were confusing because generated workups/briefs and the combined player brief were not obviously synchronized.
- Local time and meteorology required direct validation from the current save and FMAP fields.
- `Pyeongtaek` was inconsistent with what the planner saw at the departure location.

Root cause and durable response:

- The new freshness gate caught that `744pre.cam` was newer than `cam_decode.json`; the CAM was re-extracted with pyopencam before the final rebuild.
- Current campaign clock after refresh: `173845Z` / `023845 local`, UTC+9, sourced from `.cmp current_time`.
- Root `generated_briefing.md` and `player_briefing_combined.md` are hash-synchronized and validation now fails if they diverge.
- Takeoff/landing objective identity now compares target ID with waypoint geography. The stale ID 924/Pyeongtaek reference is retained as an `identity_conflict`, while player products correctly use coordinate-aligned `Seosan AB (RKTP)`, objective 921.

## Final Image Evaluation

| Product | Evaluation |
| --- | --- |
| `01_route_threat_map.png` | Current-save route overview. Seosan is corrected; package flows are color-separated; DEAD, Eagles, AI, TARCAP, Pohang/air axes, and strategic rings remain readable without changing the established texture. |
| `02_target_area_map.png` | Approved target crop is preserved. Plasma 3 takes the southern hook; Hawkeye 6 runs to 10N; three Eagle tracks show callsigns, reciprocal SAFE/FWD CAP circuits, and distinct HOLD gates; Spade 7 TARCAP is labeled. |
| `03_objective_area_map.png` | Highest-useful zoom with all three killboxes, four AI IPs, 10A/10B, and edge cues for 10N/Pohang/offshore. Current-save friendly/hostile battalions use the shared coherent symbols. |
| `04_weather_map.png` | Current FMAP and clock data, consolidated package flow at 20% opacity, readable T/O/LNDG and target samples, and separate Sentry/Copper support tracks. |
| `05_3d_killbox1_southwest.png` | User-approved north-up terrain/context view retained. No replacement candidate matched its framing/style quality. Legacy provenance is explicit rather than implied. |
| `06_3d_killbox1_southwest_west_to_east.png` | User-approved IP C5 attack-perspective view retained with seamless terrain edges. Legacy provenance is explicit; future equivalents will be fully self-recording. |

## New Enforcement Layers

1. Current CAM must not be newer than its pyopencam decode.
2. Synthesis must not be older than CAM/context inputs.
3. Root combined brief files must be identical and newer than synthesis.
4. Canonical 2D images must be 16:9, manifest-hashed, and tagged with CAM/context/profile provenance.
5. Canonical `briefing_images` may contain only manifest-listed PNGs.
6. Diagnostic `candidate`/`check` images live under `_map_diagnostics`; predecessors live under `_image_history`.
7. Mission-specific bounds and style values belong in `map_render_profiles`.
8. Shared MIL-STD glyph invariants and coordinate-aligned airbase resolution have executable regression tests.
9. New 3D images must record their exact render inputs and may not hide side gutters with background fill.

## Remaining Human QA

Automated checks can prove freshness, hashes, geometry contracts, symbol construction, and canonical inventory. They cannot reliably prove that every label is aesthetically optimal at the exact deck placement or that a commander prefers one valid 3D camera over another. Slide-size visual inspection therefore remains a required promotion gate, but it now starts from reproducible candidates and cannot silently mutate already approved products.
