# Aircraft Loadout Visual Contract

Use this reference whenever a banner, briefing image, or other generated visual
must depict recognizable aircraft stores. Its purpose is to prevent a model from
turning a correct BMS inventory into an invented or impossible weapon layout.

## Source Of Truth

Treat these as separate layers, but derive both from the current campaign when
the flight record exposes its loadout:

1. **Campaign slot plan**: the selected current flight's ordered CAM
   `loadouts[loadout_index].store_slots`. Every entry retains its BMS slot,
   weapon ID, quantity, and occupied/empty state. This is the source of truth
   for stores and placement; do not ask the mission planner to transcribe it.
2. **Airframe mapping**: a maintained, versioned map from BMS attachment slots
   to human-readable hardpoints, rack positions, and auxiliary/pod mounts for
   that aircraft type. It translates the campaign plan; it does not replace it.

The campaign decoder now emits both legacy `weapon_ids`/`weapon_counts` arrays
and ordered `store_slots`. For example, the F-16 Event 744 CAM layout reconciles
with its physical left-to-right pylon order: BMS slots 1–9 run from physical
stations 9–1, with slot 0 representing the internal gun. Use the aircraft map
for any auxiliary positions rather than guessing from the array.

Only use an explicit planner override when the planner deliberately changes the
visual from the current mission and records why. If a save lacks usable slot
records or an airframe mapping has not yet been validated, still show realistic
stores matching the current decoded inventory, but describe their placement as
illustrative rather than presenting it as an exact hardpoint diagram.

Put the approved plan in a mission-specific JSON file such as:

`inputs/<prefix>-banner-loadout.json`

Never copy a station plan from an earlier event or a different aircraft type.

## Contract Shape

Use this shape; add platform-specific fields only when they are known:

```json
{
  "schema_version": 1,
  "source": {
    "campaign_decode": "outputs/744pre/cam_decode.json",
    "flight": "Mudhen 7",
    "loadout_index": 0,
    "airframe_station_mapping": "f16c-bms-438-v1"
  },
  "aircraft": {
    "type": "F-16C Block 50",
    "station_reference": "<local reference image or aircraft manual>",
    "station_plan": [
      {"bms_slot": 1, "station": "9", "store": "AIM-120", "quantity": 1, "mount": "single"},
      {"bms_slot": 2, "station": "8", "store": "AIM-120", "quantity": 1, "mount": "single"},
      {"bms_slot": 3, "station": "7", "store": "AGM-65D", "quantity": 2, "mount": "TER", "empty_rack_positions": 1},
      {"bms_slot": 4, "station": "6", "store": "370-gallon fuel tank", "quantity": 1, "mount": "single"},
      {"bms_slot": 5, "station": "5", "store": null, "quantity": 0, "mount": "empty"},
      {"bms_slot": 6, "station": "4", "store": "370-gallon fuel tank", "quantity": 1, "mount": "single"},
      {"bms_slot": 7, "station": "3", "store": "CBU-105", "quantity": 2, "mount": "paired rack"},
      {"bms_slot": 8, "station": "2", "store": "AIM-120", "quantity": 1, "mount": "single"},
      {"bms_slot": 9, "station": "1", "store": "AIM-120", "quantity": 1, "mount": "single"}
    ],
    "forbidden": [
      "centerline pylon",
      "centerline tank",
      "centerline pod",
      "AIM-9",
      "AGM-88",
      "JDAM",
      "targeting pod"
    ]
  },
  "aircraft_instances": [
    {
      "id": "lead_f16",
      "aircraft_type": "F-16C Block 50",
      "loadout_contract": "aircraft.station_plan",
      "detail_level": "fully_countable",
      "edit_lock": false
    },
    {
      "id": "background_f16s",
      "aircraft_type": "F-16C Block 50",
      "loadout_contract": "aircraft.station_plan",
      "detail_level": "recognizable_scaled",
      "edit_lock": false
    },
    {
      "id": "upper_f15_pair",
      "aircraft_type": "F-15",
      "detail_level": "preserve_existing",
      "edit_lock": true
    }
  ]
}
```

The F-16 mapping above is a worked Event 744 example, not a default for other
missions or aircraft. Build it from the selected campaign `store_slots` plus
the current airframe mapping. Every non-empty station needs a store, quantity,
and mount. Every intentionally clear station that matters to the image needs an
explicit `empty` entry. Record `empty_rack_positions` when a multi-position rack
is deliberately only partly loaded.

## Reconciliation Rules

Before image generation:

- Derive `station_plan` from the selected campaign `store_slots`; preserve the
  BMS slot beside every display station. A discrepancy is a blocker unless the
  planner explicitly records a visual override and its reason.
- Verify that the airframe mapping permits the decoded store type at that
  position. Do not replace the campaign arrangement with a generic pylon plan.
- List known exclusions in `forbidden`, especially centerline equipment and
  store types that previous renders commonly invent.
- Name every aircraft in the composition. Mark aircraft that must not change as
  `edit_lock: true`; a request to alter one formation member never authorizes
  re-arming or replacing another type.
- Set a realistic `detail_level`: `fully_countable` for a close hero aircraft,
  `recognizable_scaled` for formation members, and `silhouette_only` for distant
  aircraft. Do not claim that individual rack positions are visible when the
  aircraft is too small to show them.

## Image Prompt Contract

Embed the populated contract into the prompt in unambiguous language. Include:

- Aircraft type, visible-aircraft identity, and the campaign flight/loadout
  index used.
- One exact line per station, including deliberately empty stations.
- Total store counts as a cross-check.
- A list of forbidden stores and effects.
- A `change only` list and a `do not alter` list for existing banners.

For a localized edit, identify locked aircraft by type, position, and visual
role—not merely “background aircraft.” For example: “Do not alter the two
twin-tail F-15s in the upper sky; alter only the two single-tail F-16s at the
right.”

## QA And Fallback

Inspect the generated full-resolution result before saving it:

- Correct aircraft type, tail count, intake, and planform.
- Correct store count, rack occupancy, and station placement for every aircraft
  at `fully_countable` detail, traced back to the campaign BMS slots.
- No centerline equipment when station 5 is empty.
- No forbidden stores, duplicate weapons, or stores intersecting wings/fuselage.
- Locked aircraft are unchanged in silhouette, stores, location, and scale.

Image generation can approximate small formation stores but cannot be trusted as
the sole authority for a technically exact close-up. If a `fully_countable`
aircraft still fails the contract after one targeted correction, stop broad
image-to-image retries. Use a source-grounded Falcon BMS screenshot, an approved
3D render, or a manual composite for the aircraft, then use generated imagery
only for environment and atmosphere.
