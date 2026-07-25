# Briefing extraction: 738pretest

## Files
- `.cam`: 201221 bytes, head int32=[201010, 9683, 43972, -1888709377]
- `.fmap`: 417764 bytes, head int32=[8, 59, 59, 236]
- `.frc`: 19698 bytes, head int32=[32130314, 8, 0, 0]
- `.his`: 249692 bytes, head int32=[32130314, 1543897460, 100801537, 36634984]
- `.iff`: 10272 bytes, head int32=[1179011419, 1819234336, 544826217, 1835099476]
- `.ini`: 10013 bytes, head int32=[1397312859, 1313818963, 1946815837, 1701606505]
- `.l16.txtpb`: 4248 bytes, head int32=[2004116846, 543912559, 537529723, 1634038816]
- `.twx`: 728 bytes, head int32=[8, 1988, 2, 8]

## CAM Container
- Director offset: 201010 / file size 201221 bytes
- Embedded files: 9 declared=9
- Save version: `110`
- `738pretest.cmp`: offset 4, size 9687, head int32=[9683, 43972, -1888709377]
- `738pretest.obd`: offset 9691, size 13315, head int32=[13311, -476837306, -2009661440]
- `738pretest.uni`: offset 23006, size 156425, head int32=[156421, -503119025, 312410118]
- `738pretest.tea`: offset 179431, size 13586, head int32=[1832845320, 0, 57999360]
- `738pretest.evt`: offset 193017, size 90, head int32=[22, 65536, 131072]
- `738pretest.plt`: offset 193107, size 3373, head int32=[800, 0, 9984]
- `738pretest.pst`: offset 196480, size 2956, head int32=[123, 1242563356, 1237645191]
- `738pretest.pol`: offset 199436, size 1571, head int32=[201339391, 10, -16777216]
- `738pretest.ver`: offset 201007, size 3, version `110`

## Planning Points
- Title: `738pretest`
- target: 11
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
- Full decode: `outputs\738pretest\cam_decode.json`
- Save version: `110`, class table entries: 5294
- Campaign clock: campaign_time_ms=261057684, clock_base=1400
- Objective deltas: 2630
- Units: Battalion=312, Brigade=15, Flight=212, Package=161, Squadron=136, TaskForce=11
- Teams: XX, U.S., ROK, Japan, USSR, PRC, DPRK, NATO
- Mission counts: BARCAP2=26, SAD=24, ALERT=17, ASHIP=15, TARCAP=15, HAVCAP=14, PATROL=13, CAS=12, AIRLIFT=12, ESCORT=12, ABORT=10, BAI=10
- Sample flights:
  - 1459: Eagle 6 RECONPATROL pkg=1457 wpts=5
  - 1401: Cheetah 2 ABORT pkg=1397 wpts=12
  - 1727: Gypsy 2 PATROL pkg=1725 wpts=8
  - 1939: Satan 3 BARCAP2 pkg=1937 wpts=6
  - 1803: Dipper 1 CAS pkg=1801 wpts=11
  - 1885: Cyborg 3 INT pkg=1883 wpts=11
  - 2871: Trojan 7 ALERT pkg=2869 wpts=3
  - 3320: Hornet 3 HAVCAP pkg=2995 wpts=8

## Current Gap
The `.cam` container, teams, objective deltas, units, packages, flights, squadrons, missions, callsigns, TACAN values, and waypoints are now decoded. Remaining work is briefing synthesis: resolve objective names/base objective data, convert BMS campaign times into briefing times, identify the human-relevant packages, and infer tactics/intent.
