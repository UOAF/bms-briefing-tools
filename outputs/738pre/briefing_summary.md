# Briefing extraction: 738pre

## Files
- `.cam`: 200790 bytes, head int32=[200615, 9774, 44005, -1890107137]
- `.fmap`: 417764 bytes, head int32=[8, 59, 59, 236]
- `.frc`: 19564 bytes, head int32=[32130314, 8, 0, 0]
- `.his`: 248126 bytes, head int32=[32130314, 1543897460, 100801537, 36634984]
- `.iff`: 10272 bytes, head int32=[1179011419, 1819234336, 544826217, 1835099476]
- `.ini`: 9965 bytes, head int32=[1397312859, 1313818963, 1946815837, 1701606505]
- `.l16.txtpb`: 4248 bytes, head int32=[2004116846, 543912559, 537529723, 1634038816]
- `.twx`: 728 bytes, head int32=[8, 1988, 2, 8]

## CAM Container
- Director offset: 200615 / file size 200790 bytes
- Embedded files: 9 declared=9
- Save version: `110`
- `738pre.cmp`: offset 4, size 9778, head int32=[9774, 44005, -1890107137]
- `738pre.obd`: offset 9782, size 13315, head int32=[13311, -476837306, -2009661440]
- `738pre.uni`: offset 23097, size 156091, head int32=[156087, -583859381, 866058246]
- `738pre.tea`: offset 179188, size 13434, head int32=[1832845320, 0, 57999360]
- `738pre.evt`: offset 192622, size 90, head int32=[22, 65536, 131072]
- `738pre.plt`: offset 192712, size 3373, head int32=[800, 0, 9984]
- `738pre.pst`: offset 196085, size 2956, head int32=[123, 1242563356, 1237645191]
- `738pre.pol`: offset 199041, size 1571, head int32=[201339391, 10, -16777216]
- `738pre.ver`: offset 200612, size 3, version `110`

## Planning Points
- Title: `738pre`
- target: 8
- ppt: 9
- linestpt: 10

### PPT Labels
- 0: A
- 1: B
- 2: C
- 3: D
- 4: WCH
- 5: E
- 6: GRD
- 7: BAR
- 8: F

## Link 16
- Flights: 27
- ew_channel:-1: 27
- f2f_channel:-1: 27
- mission_channel:-1: 27

## CAM Decode
- Full decode: `outputs\738pre\cam_decode.json`
- Save version: `110`, class table entries: 5294
- Campaign clock: campaign_time_ms=261052224, clock_base=1400
- Objective deltas: 2630
- Units: Battalion=312, Brigade=15, Flight=210, Package=159, Squadron=136, TaskForce=11
- Teams: XX, U.S., ROK, Japan, USSR, PRC, DPRK, NATO
- Mission counts: BARCAP=26, SCAR=24, QRA=17, TARCAP=15, TASMO=15, HAVCAP=14, PATROL=13, AIRLIFT=12, ESCORT=12, CAS=11, ABORTED=10, BAI=9
- Sample flights:
  - 1247: Dart 5 BAI pkg=1245 wpts=8
  - 1255: Gunhog 2 SCAR pkg=1253 wpts=9
  - 1289: Tomcat 4 PATROL pkg=1287 wpts=10
  - 1293: Cowboy 1 CAS pkg=1291 wpts=8
  - 1295: Spectre 7 TARCAP pkg=1291 wpts=11
  - 1333: Buff 6 PATROL pkg=1297 wpts=8
  - 1349: Snake 1 SCAR pkg=1341 wpts=8
  - 1373: Snake 7 BARCAP pkg=1355 wpts=7

## Current Status
The `.cam` container, teams, objective deltas, units, packages, flights, squadrons, missions, callsigns, package support IDs, flight loadouts, laser codes, TACAN values, waypoint target refs, current-unit altitude, and waypoints are now decoded for briefing synthesis. Remaining non-CAM work is radio/channel sidecar correlation for saves whose Link 16 identifiers do not match CAM flight IDs.
