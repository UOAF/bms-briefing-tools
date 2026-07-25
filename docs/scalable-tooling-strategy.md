# Scalable BMS Tooling Strategy

## Goal

The briefing generator should work against any compatible Falcon BMS campaign
save bundle, not just the current 718 and UOAF 80s 738 examples. That requires
a stable internal schema and swappable parsers. The parser layer can learn from
outside projects, but the briefing synthesis layer should remain ours.

## Upstream Repositories Reviewed

| Repository | Commit inspected | Useful layer | Initial result |
| --- | --- | --- | --- |
| `https://github.com/UOAF/pyopencam` | `e213be3` | Pure-Python CAM container and campaign section parsing | Successfully parsed local 718 and 738 `.cam` saves. |
| `https://github.com/oakdesign/falcon-bms-tacview-converter` | `86da078` | Theater discovery, coordinate conversion, airbase/runway export | Confirms theater-file/PROJ based coordinate approach. |

The clones used for inspection were kept outside this repo under the local temp
directory. They should not be committed wholesale without a deliberate license
and ownership decision.

## Recommendation

Do not vendor either project directly yet.

Instead, make this repo own three interfaces:

1. `CampaignDecoder`: produces a normalized campaign graph.
2. `TheaterProvider`: resolves theater paths, object tables, projection, maps,
   heightmaps, and airbase/runway metadata.
3. `BriefingSynthesizer`: turns the normalized graph plus mission context into
   package briefs, threat estimates, maps, and decks.

Outside projects can then back those interfaces:

- Current `extract_bms_cam.ps1` / BMSUtils path remains a legacy read-only
  decoder and regression comparator. Do not build campaign write-back on it.
- `pyopencam` becomes the preferred Python decoder candidate after an adapter
  and regression tests.
- Tacview converter logic informs `TheaterProvider`, especially theater
  discovery and projection/heightmap handling.

This preserves our original reverse-engineering work where it has already been
validated, while giving us a path away from the 32-bit Mission Commander
dependency.

## Findings From `pyopencam`

`pyopencam` is the most relevant upstream project for scalability.

Strengths:

- Pure Python parser for `.cam` containers and `.cmp`, `.obd`, `.obj`, `.tea`,
  and `.uni` sections.
- Lossless container rebuild helpers, not just read-only extraction.
- Handles LZSS formats internally.
- Resolves unit `entityType` explicitly as raw value plus `ct_index`, avoiding
  the UCD collision bug that produced impossible aircraft labels.
- Exposes rich typed views for packages, flights, squadrons, battalions,
  brigades, task forces, waypoints, teams, objective deltas, and objective
  feature layouts.
- Squadron wrapper decodes airframe roster slots and reports available/max
  aircraft counts. That is better than our current nonzero-roster heuristic.
- Squadron wrapper exposes stores and pilot roster data, which are likely useful
  for future loadout and readiness slides.

Local compatibility checks:

- `718pre.cam`: parsed successfully.
  - Battalions: 435
  - Flights: 331
  - Packages: 301
  - Squadrons: 95
  - Brigades: 43
  - Task forces: 11
- UOAF 80s `738pre.cam`: parsed successfully.
  - Battalions: 312
  - Flights: 210
  - Packages: 159
  - Squadrons: 136
  - Brigades: 15
  - Task forces: 11
- For UOAF 80s `738pre`, these counts match our current BMSUtils-based decode.

Example advantage for package-1883 threat analysis:

- Hyon-Ni MiG-21bis squadron: 17 available / 32 max.
- Hyon-Ni Q-5II squadron: 11 available / 18 max.
- Hyon-Ni MiG-19PM squadron: 8 available / 18 max.
- Hyon-Ni J-6 squadron: 2 available / 18 max.

Risks and unknowns:

- Mission Commander/BMSUtils has known write-back bugs. Some are not obvious
  when using it for read-only extraction, so it should not become our canonical
  data model or serialization path.
- No license file was present in the inspected `pyopencam` checkout.
- JSON schema differs from our current `cam_decode.json`; direct replacement
  would break synthesis.
- Its `.cmp` wrapper currently exports only a small human-readable subset even
  though the parser has more fields internally.
- We need regression tests before trusting it as the primary decoder across
  BMS versions and theaters.

## Findings From `falcon-bms-tacview-converter`

The Tacview converter is most valuable for theater and coordinate handling, not
campaign graph decoding.

Useful pieces:

- Theater discovery through `Theater.lst`, `.tdf`, and `Theater.txt`.
- Uses theater projection strings rather than hand-fitted offsets.
- Contains coordinate conversion helpers and heightmap lookup ideas.
- Parses airbase and runway geometry from object-related files, which could
  improve map/deck graphics and airbase threat products.

Risks and unknowns:

- The inspected license is MIT-style but contains a placeholder copyright line.
- The codebase is oriented around Tacview XML output, so we should extract
  concepts rather than import its CLI shape.
- It depends on `pyproj`; some paths optionally use `pygeodesy` even though only
  `pyproj` is listed in requirements.
- Several scripts contain local hard-coded file paths in heightmap helpers.

## Target Architecture

Canonical output should be a stable internal JSON schema, independent of parser
provider. Suggested top-level shape:

```json
{
  "source": {},
  "theater": {},
  "clock": {},
  "teams": [],
  "objectives": [],
  "objective_deltas": [],
  "units": {
    "packages": [],
    "flights": [],
    "squadrons": [],
    "battalions": [],
    "brigades": [],
    "taskforces": []
  },
  "planning": {},
  "links": {}
}
```

Provider-specific data should be preserved under a small `debug` or
`provider_raw` field only when needed, so the synthesis layer never depends on
internal quirks of BMSUtils or `pyopencam`.

## Migration Plan

1. Add decoder comparison tests for 718 and 738. Initial harness:
   `scripts/pyopencam_adapter.py` normalizes pyopencam JSON exports, and
   `scripts/compare_decoders.py` compares them with BMSUtils `cam_decode.json`.
   - Counts by unit kind must match.
   - Package 1883 flight IDs/callsigns/waypoint counts must match.
   - Known enemy airbase aircraft labels must match the corrected class-table
     resolution.
2. Direct `pyopencam` provider adapter.
   - `scripts/pyopencam_provider.py` imports an external pyopencam
     checkout/source directory and emits the canonical `cam_decode` shape
     directly from `.cam` files.
   - `scripts/extract_bms_briefing.py --decode-cam --cam-decoder pyopencam`
     runs this provider without BMSUtils.
   - Preserve BMSUtils as read-only fallback and cross-check provider.
   - Never rely on BMSUtils for campaign write-back; use pyopencam-style
     container/section serialization if write support becomes a goal.
   - Current 738/package 1883 regression matches BMSUtils unit counts, mission
     counts, package flight identities and waypoint counts, strategic ADA
     threats, inactive ADA exclusions, enemy airbase threats, active air
     contacts, and enemy airbase airframe labels.
   - Remaining canonical-field gaps: flight loadout/weapon arrays, laser codes,
     TACAN channels, and decoded current-unit altitude.
3. Move object-table, class-table, and vehicle-table resolution into one shared
   Python module used by both decoders and synthesis.
4. Replace nonzero squadron roster checks with decoded available-airframe counts.
5. Fold theater discovery into `bms_projection.py` or a new `theater_provider.py`.
   - Discover stock and add-on theaters from `Theater.lst` and `.tdf`.
   - Parse `Theater.txt` projection and theater size.
   - Carry the campaign-grid feet scale explicitly; default BMS 4.38 saves to
     real-life feet (`3280.84` ft/grid for 1 km cells), with legacy 4.37
     conversion (`3279.98` ft/grid) available only as an override.
   - Locate `CampObjData.XML`, object tables, map images, `Korea.tm`-style
     rasters, Skyvector charts, stations, and heightmaps.
6. Add a generic command that accepts only a save prefix or `.cam` path and
   resolves the rest:

```powershell
python .\scripts\build_campaign_briefing.py `
  --save "C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign\738pre.cam" `
  --package 1883
```

7. Keep mission-context JSON as an overlay, not a parser input requirement.
   The tool should produce a factual briefing without human context and a richer
   commander-style brief when context is present.

## Pushback

Vendoring the upstream repos now would solve the wrong problem. The hard part is
not owning more parser code; it is owning a reliable, version-tolerant schema
that briefing synthesis can trust. `pyopencam` looks strong enough to become the
future decoder provider, but our validated projection work, INI correlation,
package-role interpretation, threat filtering, and map rendering remain core
assets. Those should stay first-class in this repo.
