# Briefing extraction: 744pre

## Files
- `.cam`: 212087 bytes, head int32=[211912, 5211, 25731, -917372161]
- `.cam.backup-20260830-172205`: 207593 bytes, head int32=[207418, 5328, 26013, -919491329]
- `.fmap`: 417764 bytes, head int32=[8, 59, 59, 277]
- `.frc`: 10586 bytes, head int32=[10802176, 8, 0, 0]
- `.his`: 165269 bytes, head int32=[10802176, -1492909606, 67200258, 30868025]
- `.iff`: 10272 bytes, head int32=[1179011419, 1819234336, 544826217, 1835099476]
- `.ini`: 10230 bytes, head int32=[1397312859, 1313818963, 1946815837, 1701606505]
- `.l16.txtpb`: 10991 bytes, head int32=[2004116846, 543912559, 537529723, 1634038816]
- `.stores-audit-20260830-172205.json`: 1294 bytes, head int32=[537529723, 1633886752, 1767993453, 975335015]
- `.twx`: 728 bytes, head int32=[8, 2026, 8, 29]

## CAM Container
- Director offset: 211912 / file size 212087 bytes
- Embedded files: 9 declared=9
- Save version: `109`
- `744pre.cmp`: offset 4, size 5215, head int32=[5211, 25731, -917372161]
- `744pre.obd`: offset 5219, size 1735, head int32=[1731, 491389104, -1311309824]
- `744pre.uni`: offset 6954, size 171627, head int32=[171623, 755368959, -1163984890]
- `744pre.tea`: offset 178581, size 9738, head int32=[2015166472, 0, 57999360]
- `744pre.evt`: offset 188319, size 90, head int32=[22, 65536, 131080]
- `744pre.plt`: offset 188409, size 3373, head int32=[800, 1, 9984]
- `744pre.pst`: offset 191782, size 18556, head int32=[773, 1235096577, 1239249551]
- `744pre.pol`: offset 210338, size 1571, head int32=[201339391, 10, -16777216]
- `744pre.ver`: offset 211909, size 3, version `109`

## Planning Points
- Title: `744pre`
- target: 12
- ppt: 15
- linestpt: 19

### PPT Labels
- 0: ORO
- 1: SA6, 12.5 NM
- 2: BAN
- 3: 10, 50.0 NM
- 4: 10, 50.0 NM
- 5: 10, 50.0 NM
- 6: A
- 7: 17, 24.0 NM
- 8: 10, 50.0 NM
- 9: B
- 10: 17, 24.0 NM
- 11: KI1
- 12: KI2
- 13: KI3
- 14: 11, 20.0 NM

## Link 16
- Flights: 71
- ew_channel:-1: 67
- ew_channel:1: 4
- f2f_channel:-1: 7
- f2f_channel:1: 8
- f2f_channel:65: 56
- mission_channel:-1: 7
- mission_channel:1: 4
- mission_channel:65: 7
- mission_channel:68: 53

## CAM Decode
- Full decode: `outputs\744pre\cam_decode.json`
- Save version: `109`, class table entries: 5261
- Campaign clock: campaign_time_ms=63525378, clock_base=0238
- Objective deltas: 176
- Units: Battalion=367, Brigade=91, Flight=261, Package=230, Squadron=43, TaskForce=31
- Teams: XX, U.S., ROK, Japan, USSR, PRC, DPRK, NATO
- Mission counts: BARCAP=62, PRE-PLAN CAS=28, AIRLIFT=24, BAI=19, TARCAP=19, CAS=15, RECCE PATROL=13, SCAR=13, QRA=12, ABORTED=11, AEW/ABCCC=6, AIR REFUEL=6
- Sample flights:
  - 1227: Spartan 1 RECCE PATROL pkg=1225 wpts=6
  - 1257: Weasel 2 ABORTED pkg=1255 wpts=10
  - 1313: Sparky 5 RECCE PATROL pkg=1297 wpts=6
  - 1323: Snake 4 BAI pkg=1321 wpts=10
  - 1337: Rescue 5 RECCE PATROL pkg=1335 wpts=6
  - 1345: Cowboy 3 SCAR pkg=1339 wpts=10
  - 1353: Warhog 2 BARCAP pkg=1349 wpts=7
  - 1357: Sparky 1 RECCE PATROL pkg=1355 wpts=6

## Current Status
The `.cam` container, teams, objective deltas, units, packages, flights, squadrons, missions, callsigns, package support IDs, flight loadouts, laser codes, TACAN values, waypoint target refs, current-unit altitude, and waypoints are now decoded for briefing synthesis. Remaining non-CAM work is radio/channel sidecar correlation for saves whose Link 16 identifiers do not match CAM flight IDs.
