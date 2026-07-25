# Briefing extraction: 718pre

## Files
- `.cam`: 238420 bytes, head int32=[238245, 8279, 35929, 1969200383]
- `.fmap`: 417764 bytes, head int32=[8, 59, 59, 307]
- `.frc`: 49446 bytes, head int32=[3600034, 8, 0, 0]
- `.his`: 849734 bytes, head int32=[3600034, 1745224150, 100806401, 25952740]
- `.iff`: 10272 bytes, head int32=[1179011419, 1819234336, 544826217, 1835099476]
- `.ini`: 10123 bytes, head int32=[1397312859, 1313818963, 1946815837, 1701606505]
- `.l16.txtpb`: 27768 bytes, head int32=[2004116846, 543912559, 537529723, 1634038816]
- `.twx`: 728 bytes, head int32=[8, 2025, 10, 7]

## CAM Container
- Director offset: 238245 / file size 238420 bytes
- Embedded files: 9 declared=9
- Save version: `109`
- `718pre.cmp`: offset 4, size 8283, head int32=[8279, 35929, 1969200383]
- `718pre.obd`: offset 8287, size 11016, head int32=[11012, -1192032926, -1195966464]
- `718pre.uni`: offset 19303, size 195251, head int32=[195247, -1085602624, -1348534265]
- `718pre.tea`: offset 214554, size 14738, head int32=[1832845320, 0, 57999360]
- `718pre.evt`: offset 229292, size 90, head int32=[22, 65536, 131072]
- `718pre.plt`: offset 229382, size 3373, head int32=[800, 1, 9984]
- `718pre.pst`: offset 232755, size 3916, head int32=[163, 1234073587, 1237080850]
- `718pre.pol`: offset 236671, size 1571, head int32=[201339391, 10, -16777216]
- `718pre.ver`: offset 238242, size 3, version `109`

## Planning Points
- Title: `718pre`
- target: 9
- ppt: 15

### PPT Labels
- 0: A
- 1: B
- 2: C
- 3: SA2, 27.0 NM
- 4: 11, 20.0 NM
- 5: 15, 6.5 NM
- 6: 10, 50.0 NM
- 7: 11, 20.0 NM
- 8: 10, 50.0 NM
- 9: 11, 20.0 NM
- 10: 10, 50.0 NM
- 11: 20, 75.0 NM
- 12: D
- 13: IP1
- 14: SA2, 27.0 NM

## Link 16
- Flights: 189
- ew_channel:-1: 171
- ew_channel:2: 18
- f2f_channel:-1: 20
- f2f_channel:2: 76
- f2f_channel:6: 93
- mission_channel:-1: 20
- mission_channel:2: 72
- mission_channel:6: 20
- mission_channel:76: 77

## CAM Decode
- Full decode: `outputs\718pre\cam_decode.json`
- Save version: `109`, class table entries: 5261
- Campaign clock: campaign_time_ms=343236508, clock_base=1400
- Objective deltas: 1378
- Units: Battalion=435, Brigade=43, Flight=331, Package=301, Squadron=95, TaskForce=11
- Teams: XX, U.S., ROK, Japan, CIS, PRC, DPRK, NATO
- Mission counts: BARCAP2=78, ALERT=38, AIRLIFT=37, SAD=29, ABORT=24, CAS=21, ASHIP=19, SEADSTRIKE=13, BAI=12, TARCAP=10, RELOCATE=7, HAVCAP=6
- Sample flights:
  - 7270: Viking 4 RELOCATE pkg=7269 wpts=4
  - 2839: Sherpa 3 BARCAP2 pkg=2825 wpts=7
  - 2619: Slick 4 ALERT pkg=2617 wpts=3
  - 7039: Nightmare 2 SAD pkg=7038 wpts=10
  - 2023: Vulture 7 HAVCAP pkg=2002 wpts=8
  - 3731: Wildcat 5 BARCAP2 pkg=3730 wpts=7
  - 2141: Garbo 6 HAVCAP pkg=7094 wpts=8
  - 2683: Mongo 4 ALERT pkg=2681 wpts=3

## Deck
- HTML view: https://docs.google.com/presentation/d/1sV9xxCRPyaAeumhVlZdfAq7CFWqq8Ch9Gk0d7h3EnTc/htmlpresent
- Slides indexed: 79
- Relevant slides:
  - 7: Operating Area
  - 8: Meteorology
  - 10: Threats (South)
  - 11: Threats
  - 14: Game Plan: Phase 1 (Establish Airspace)
  - 15: Game Plan: Phase 2 (STRIKES)
  - 16: Coordination
  - 17: Contracts
  - 18: Comm Ladder
  - 21: Friendly OOB
  - 24: Gameplan - DEAD
  - 28: Gameplan - AI
  - 29: Gameplan - CAS (WIP)
  - 33: Package Flow and Push
  - 34: Gameplan - SEAD / DEAD
  - 38: A/A Tactics
  - 41: Target File - Package 4827 (1)
  - 42: Gameplan - Package 2905 - BARCAP
  - 43: Target File - Package 4827 (2)
  - 50: Push
  - 53: Friendly OOB
  - 54: Gameplan - Target Area Center AOR
  - 57: Target File - Package 1491 (3)
  - 58: Target File - Package 1491 (4)
  - 59: Target File - Package 1491 (5)
  - 61: Target File - Package 1434 (1)

## Current Gap
The `.cam` container, teams, objective deltas, units, packages, flights, squadrons, missions, callsigns, TACAN values, and waypoints are now decoded. Remaining work is briefing synthesis: resolve objective names/base objective data, convert BMS campaign times into briefing times, identify the human-relevant packages, and infer tactics/intent.
