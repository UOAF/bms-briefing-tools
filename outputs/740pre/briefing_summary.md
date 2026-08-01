# Briefing extraction: 740pre

## Files
- `.cam`: 244024 bytes, head int32=[243849, 5537, 26717, 759761151]
- `.fmap`: 417764 bytes, head int32=[8, 59, 59, 284]
- `.frc`: 1206 bytes, head int32=[10802176, 8, 0, 0]
- `.his`: 21279 bytes, head int32=[10802176, -1492909606, 67200258, 30868025]
- `.iff`: 10272 bytes, head int32=[1179011419, 1819234336, 544826217, 1835099476]
- `.ini`: 9993 bytes, head int32=[1397312859, 1313818963, 1946815837, 1701606505]
- `.l16.txtpb`: 14684 bytes, head int32=[2004116846, 543912559, 537529723, 1634038816]
- `.twx`: 728 bytes, head int32=[8, 2026, 7, 29]

## CAM Container
- Director offset: 243849 / file size 244024 bytes
- Embedded files: 9 declared=9
- Save version: `109`
- `740pre.cmp`: offset 4, size 5541, head int32=[5537, 26717, 759761151]
- `740pre.obd`: offset 5545, size 725, head int32=[721, 204669015, -1311309824]
- `740pre.uni`: offset 6270, size 188176, head int32=[188172, -1397947319, 2057240582]
- `740pre.tea`: offset 194446, size 9778, head int32=[2015166472, 0, 57999360]
- `740pre.evt`: offset 204224, size 90, head int32=[22, 65536, 131080]
- `740pre.plt`: offset 204314, size 3373, head int32=[800, 1, 9984]
- `740pre.pst`: offset 207687, size 34588, head int32=[1441, 1230205435, 1240177778]
- `740pre.pol`: offset 242275, size 1571, head int32=[201339391, 10, -16777216]
- `740pre.ver`: offset 243846, size 3, version `109`

## Planning Points
- Title: `740pre`
- target: 14
- ppt: 13

### PPT Labels
- 0: ORO
- 1: 10, 50.0 NM
- 2: 15, 6.5 NM
- 3: 10, 50.0 NM
- 4: SA5, 54.0 NM
- 5: CRO
- 6: BLU
- 7: SA6, 12.5 NM
- 8: 10, 50.0 NM
- 9: TIG
- 10: WWO
- 11: BAN
- 12: BAN

## Link 16
- Flights: 97
- ew_channel:-1: 91
- ew_channel:1: 6
- f2f_channel:-1: 15
- f2f_channel:1: 36
- f2f_channel:65: 46
- mission_channel:-1: 15
- mission_channel:1: 25
- mission_channel:65: 12
- mission_channel:68: 45

## CAM Decode
- Full decode: `outputs\740pre\cam_decode.json`
- Save version: `109`, class table entries: 5261
- Campaign clock: campaign_time_ms=19745032, clock_base=1429
- Objective deltas: 87
- Units: Battalion=464, Brigade=100, Flight=258, Package=196, Squadron=47, TaskForce=32
- Teams: XX, U.S., ROK, Japan, USSR, PRC, DPRK, NATO
- Mission counts: BARCAP=46, BAI=25, PRE-PLAN CAS=24, TARCAP=24, SCAR=19, ABORTED=16, HAVCAP=16, CAS=15, ESCORT=14, RECCE PATROL=10, AIRLIFT=8, OCA STRIKE=6
- Sample flights:
  - 943: Sawbuck 4 ABORTED pkg=13 wpts=10
  - 1222: Dart 5 SCAR pkg=1190 wpts=11
  - 1227: Troll 4 BAI pkg=1225 wpts=10
  - 1231: Mohawk 1 CAS pkg=1230 wpts=11
  - 1313: Zipper 4 TARCAP pkg=1225 wpts=11
  - 1531: Devil 4 SCAR pkg=1511 wpts=9
  - 1927: Banshee 1 BARCAP pkg=1545 wpts=7
  - 1951: Mako 2 ABORTED pkg=1855 wpts=13

## Current Status
The `.cam` container, teams, objective deltas, units, packages, flights, squadrons, missions, callsigns, package support IDs, flight loadouts, laser codes, TACAN values, waypoint target refs, current-unit altitude, and waypoints are now decoded for briefing synthesis. Remaining non-CAM work is radio/channel sidecar correlation for saves whose Link 16 identifiers do not match CAM flight IDs.
