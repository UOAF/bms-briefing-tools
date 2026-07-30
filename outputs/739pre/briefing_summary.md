# Briefing extraction: 739pre

## Files
- `.cam`: 174994 bytes, head int32=[174819, 5308, 26476, -1036574465]
- `.frc`: 402 bytes, head int32=[10802176, 8, 0, 0]
- `.his`: 7123 bytes, head int32=[10802176, -1492909606, 67200258, 30868025]
- `.iff`: 10272 bytes, head int32=[1179011419, 1819234336, 544826217, 1835099476]
- `.ini`: 9911 bytes, head int32=[1397312859, 1313818963, 1946815837, 1701606505]
- `.l16.txtpb`: 5645 bytes, head int32=[2004116846, 543912559, 537529723, 1634038816]
- `.twx`: 728 bytes, head int32=[8, 2026, 7, 29]

## CAM Container
- Director offset: 174819 / file size 174994 bytes
- Embedded files: 9 declared=9
- Save version: `109`
- `739pre.cmp`: offset 4, size 5312, head int32=[5308, 26476, -1036574465]
- `739pre.obd`: offset 5316, size 391, head int32=[387, 87687233, -1311309824]
- `739pre.uni`: offset 5707, size 142941, head int32=[142937, 1379795867, 2090795013]
- `739pre.tea`: offset 148648, size 9778, head int32=[2015166472, 0, 57999360]
- `739pre.evt`: offset 158426, size 90, head int32=[22, 65536, 131080]
- `739pre.plt`: offset 158516, size 3373, head int32=[800, 1, 9984]
- `739pre.pst`: offset 161889, size 11356, head int32=[473, 1230205435, 1240177778]
- `739pre.pol`: offset 173245, size 1571, head int32=[201339391, 10, -16777216]
- `739pre.ver`: offset 174816, size 3, version `109`

## Planning Points
- Title: `739pre`
- target: 11
- ppt: 10

### PPT Labels
- 0: 10, 50.0 NM
- 1: 10, 50.0 NM
- 2: 15, 6.5 NM
- 3: 10, 50.0 NM
- 4: SA5, 54.0 NM
- 5: CRO
- 6: JEW
- 7: SA6, 12.5 NM
- 8: 10, 50.0 NM
- 9: TIG

## Link 16
- Flights: 34
- ew_channel:-1: 32
- ew_channel:1: 2
- f2f_channel:-1: 8
- f2f_channel:1: 17
- f2f_channel:65: 9
- mission_channel:-1: 8
- mission_channel:1: 14
- mission_channel:65: 5
- mission_channel:68: 7

## CAM Decode
- Full decode: `outputs\739pre\cam_decode.json`
- Save version: `109`, class table entries: 5261
- Campaign clock: campaign_time_ms=12728096, clock_base=1400
- Objective deltas: 65
- Units: Battalion=473, Brigade=100, Flight=159, Package=112, Squadron=47, TaskForce=32
- Teams: XX, U.S., ROK, Japan, USSR, PRC, DPRK, NATO
- Mission counts: TARCAP=26, CAS=19, BAI=17, PRE-PLAN CAS=15, SCAR=14, BARCAP=11, QRA=10, ESCORT=9, RECCE PATROL=8, OCA STRIKE=6, TASMO=4, AEW/ABCCC=3
- Sample flights:
  - 943: Dragnet 3 ELINT pkg=13 wpts=9
  - 1222: Dragnet 1 AEW/ABCCC pkg=1190 wpts=9
  - 1227: Chalice 5 ELINT pkg=1225 wpts=9
  - 1231: Mohawk 1 CAS pkg=1230 wpts=10
  - 1531: Devil 4 SCAR pkg=1511 wpts=9
  - 1945: Rumble 5 ABORTED pkg=1943 wpts=11
  - 1949: Hawkeye 3 CAS pkg=1947 wpts=9
  - 1951: Mako 2 CAS pkg=1855 wpts=12

## Current Status
The `.cam` container, teams, objective deltas, units, packages, flights, squadrons, missions, callsigns, package support IDs, flight loadouts, laser codes, TACAN values, waypoint target refs, current-unit altitude, and waypoints are now decoded for briefing synthesis. Remaining non-CAM work is radio/channel sidecar correlation for saves whose Link 16 identifiers do not match CAM flight IDs.
