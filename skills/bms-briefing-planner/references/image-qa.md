# Image QA Criteria

## Standard Image Pack

The final deck-facing folder should contain:

- `01_route_threat_map.png`
- `02_target_area_map.png`
- `03_objective_area_map.png`
- `manifest.json`
- Optional `04_weather_map.png`

Use consistent names so the user can find images quickly. Avoid requiring the user to hunt through package folders, design folders, or diagnostic variants.

## Map Purpose

Each map must answer a different question:

- Route & Threat Map: How does the whole player package flow from departure bases to target, and where are major threats?
- Target Area Map: What is the package flow, named positions, enemy air axes, and SAM geometry near the target area?
- Objective Area Map: What is happening immediately around the objective, at the highest useful zoom?
- Weather Map: What weather patterns affect takeoff, target, landing, and route?

If two maps show the same zoom level or same information density, one of them is wrong.

## Route & Threat Map Criteria

The route overview must:

- Show friendly departure airbases and flow from those origins to the target area.
- Aggregate route flow when individual flight plans clutter the slide.
- Label aggregated route arrows with compact role and callsigns, for example `SEAD (Cyborg1, Jackal2)`, `CAP (Cobra2, Cajun1, Cobra4)`, `Eagles (Hog5, Ramrod3)`.
- Show strategic ADA WEZ rings with readable outlines and subdued fill.
- Show active enemy airbase origins and enemy air axes, using human-readable airbase names and abbreviated aircraft where needed.
- Avoid over-wide crops that include irrelevant terrain no player would reasonably care about.

The route overview should not:

- Show every tactical waypoint if it makes the slide unreadable.
- Use tiny labels that only work at full PNG size.
- Put labels under route arrows.
- Use generic `AB ###` labels.

## Target Area Map Criteria

The target map must:

- Use the same tactical content stack as the route map: package flow, named marks, enemy air axes, and strategic ADA rings.
- Crop tighter around the target area and tactical flow.
- Include enemy airbases/air origins if they are inside or edge-relevant to the crop.
- Use smaller airbase labels than the route overview.
- Use distinct visual language for enemy airbases, separate from generic threat markers.

The target map should not:

- Show friendly departure airbase labels.
- Let support tracks or origin airbases force an over-wide crop.
- Over-label the map until terrain and tactical geometry disappear.

## Objective Area Map Criteria

The objective map must:

- Be the most zoomed-in view.
- Use the same marker/threat content as the target map, but tighter.
- Prioritize terrain, named objective marks, ADA sites/rings, and immediate prosecution geometry.
- Use smaller fonts than the target map.
- Suppress or minimize flow labels if they obscure the objective.

The objective map should not:

- Become a horizontal route ingress map.
- Show the whole route from departure.
- Show friendly departure airbase labels.
- Use route-overview font sizes.

## Visual Language

Use consistent visual semantics:

- Friendly/package flow: blue/green/yellow by role, with transparency when busy.
- Named INI/PPT marks: green diamonds.
- Strategic SAM WEZ: red ring with near-solid outside edge and lower-opacity interior/fill.
- Enemy airbase origins: dedicated airbase marker/label, not the same plain red square as other threats.
- Offshore/non-airbase enemy origins: separate marker such as red diamond or arrow-source marker.
- Friendly departure bases on route map: friendly-colored airbase marker/label.

Use compact labels on slide maps:

- `SA-10 West`, `SA-10 East`, `SA-10 South` -> `10W`, `10E`, `10S`.
- `SA-6` -> `6`.
- `MiG-29S`, `MiG-27`, `MiG-31` -> `M29S`, `M27`, `M31`.
- `Su-33`, `Su-35S`, `Su-39` -> `S33`, `S35S`, `S39`.
- Drop `Offshore group` when the aircraft label is enough.

## Readability Checks

Always inspect final maps at slide-like size, not only full resolution.

Check:

- At 16:9 slide placement, major labels are readable without zooming.
- No label is hidden under an arrow or ring.
- Labels are staggered so their associated line/marker is clear.
- Threat rings are visible but do not wash out the chart.
- The map base remains legible under overlays.
- The crop fits the intended purpose.
- Objective map fonts are smaller than target map fonts.
- Route map remains under 20 MB unless the user says otherwise.

If a preview reveals crowding, rerender with changed crop/font/opacity. Do not declare success based only on command success.

## Pass/Fail Gates

Use these gates before presenting images as final:

| Product | Pass | Fail |
| --- | --- | --- |
| Route | Friendly origin bases visible; package flow readable from origin to target; strategic WEZs legible; enemy origin labels readable at slide size. | Crop extends far beyond plausible package flow; labels too small on slide; every discrete flight route is shown when aggregate flow would be clearer; route PNG exceeds 20 MB. |
| Target | Target complex, package flows, named marks, enemy origins, and ADA rings share one readable tactical view. | Same zoom as route map; departure bases labeled; airbase label font dominates terrain; enemy airbase marker is indistinguishable from generic threat marker. |
| Objective | Most zoomed-in product; target/objective geometry is clear; labels are subordinate to terrain and tactical markers. | Shows full ingress route; uses target/route font sizes; flow labels cover the objective; key named marks or ADA rings are missing. |
| Weather | Weather cells/patterns can be compared against route and target areas; takeoff/target/landing conditions are supported. | Weather map is decorative only; no relation to route/target points; missing data is printed as a player-facing apology. |

When a map fails, name the failed gate and rerender that product only when possible. Avoid regenerating the whole pack unless the underlying data changed.

## Common Fixes

- Labels too small on route: increase slide label multipliers or crop tighter, then preview at slide size.
- Labels too large on objective: reduce objective label multipliers first; then suppress flow labels if needed.
- Threat rings invisible: increase outline opacity or switch route overview to `route-reference` style.
- Threat rings overpower terrain: lower fill opacity, keep the outer WEZ edge visible.
- Airbase labels collide with arrows: stagger labels, add leader lines, or move labels to crop edge.
- Wrong map geography: verify projection, feet-per-grid, and whether the crop is based on flight routes, INI marks, or objective marks.
- Out-of-theater INI/PPT transforms: preserve them in the workup, but exclude them from map crops and labels. A single bad PPT can explode a map crop.
- Missing named marks at zoom: ensure crop bounds include the named positions independently of route points.
- Wrong airbase names or aircraft types: recheck objective/object-table joins and active squadron filtering.

## Practical Render Defaults

For combined slide maps, use `--presentation-profile slide` and `--no-show-map-title` when the deck already has a title rail.

Route overview:

- Include `--combined-include-flow-origins-in-bounds`.
- Include `--show-flow-origin-labels`.
- Use `--combined-threat-style route-reference`.
- Use larger labels and strokes.
- Compress the PNG if it exceeds 20 MB.
- When aggregated flow groups have mixed departure bases, render explicit friendly departure-base markers for each unique takeoff airbase; do not leave only a generic `Mixed Origins` label.

Target area:

- Do not include flow origins in bounds.
- Do not show flow origin labels.
- Use moderate label sizes.
- Keep threat opacity readable but lower than route outlines.

Objective area:

- Use `--combined-crop-mode objective-area`.
- Set an objective north bound and padding when the planner gives a useful anchor.
- Use smaller label multipliers than target.
- If flow labels obscure terrain, reduce label multipliers or render flow lines without text.
- Treat route labels on objective maps as optional. The objective map may rely on the slide legend or sidebar text for flow names if labels block the prosecution area.
- Suppress off-crop named-position labels; edge-clamped transit/fallback labels can make a close-up read like a route map.

Weather:

- Use the same map source and route geometry as the package maps.
- Use the save-specific `<prefix>.fmap` sidecar after F4Wx output has been installed.
- For F4Wx sequences, keep `WeatherMapsUpdates` synchronized with the root `<prefix>.fmap` starting frame.
- If the user wants Weather Commander comparison, render a full-Korea weather map as a diagnostic, then return to package-cropped weather for the deck.
- Sample weather at takeoff, target, and landing points; do not infer one area from another when FMAP cells differ.
- Use a chunky enough weather overlay for the cells to read as an actual weather product on slides; `--weather-alpha 112` is the current baseline.
- Draw a neutral grey dotted `PACKAGE AO` box around the player route from departure to target/INI work area. Exclude support tracks and recovery alternates from this AO box unless the user asks otherwise. Avoid cyan/green AO styling because it competes with weather cells.
- Author weather labels for slide-scale viewing, not full-PNG inspection. Current baseline full-resolution sizes are route `36`, INI `54`, weather samples `72`, AO label `76`, and scale/north `52`; increase only if slide preview text is still unreadable.
- Promote the deck-facing weather image as `04_weather_map.png`.

## Final Asset Hygiene

After choosing a variant:

1. Run `python .\scripts\collect_bms_image_pack.py .\outputs\<prefix>`.
2. Confirm `briefing_images/manifest.json` references the selected variant folder.
3. Confirm only the useful deliverable images are in `briefing_images`.
4. Create optional slide-size preview images for human review, but do not treat previews as canonical deliverables.
