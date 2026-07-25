# Generated BMS Briefing Draft: 738pre

Timing is provisional: HHMM values use the inferred `.cmp` clock base `1400` and campaign time `261052224`.

## Reference Deck Package Check
- Mentioned in deck: none
- Present in local CAM: none
- Missing from local CAM: none

## Operating Area Inputs
- PPT labels and rings: 0 A; 1 B; 2 C; 3 D; 4 WCH; 5 E; 6 GRD; 7 BAR; 8 F
- Drawn line STPTs: 10 points
- INI grid transform: `grid_x = (ini_y / 3280.84); grid_y = (ini_x / 3280.84)`

## Meteorology
- Source: `C:\Falcon BMS 4.38\Data\Add-On UOAF 80s\Campaign\738pre.fmap` (v8+, 59x59 cells). Map wind 236/32 kt.
- Basis: FMAP row 0 is north; campaign grid Y is inverted into weather row space before sampling.
- Theater mix: Sunny=2, Fair=2667, Poor=425, Inclement=387

| Area | Local time | Day/Night | Conditions | Cloud base | Contrail layer | Temp C | Visibility km | Wind | Grid X | Grid Y | Basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Takeoff | 1424 | Day | Fair OVC | 10000 | FL240 | 12.7 | 59.5 | 181/3 kt | 511.0 | 313.0 | Cyborg 3 TAKEOFF STPT 0 |
| Target Area | 1438 | Day | Fair OVC | 10000 | FL240 | 7.6 | 59.5 | 263/1 kt | 520.9 | 481.0 | Centroid of correlated INI objective PPTs A, C, B, WCH, E, D, F |
| Landing | 1518 | Day | Fair OVC | 10000 | FL240 | 12.7 | 59.5 | 181/3 kt | 511.0 | 313.0 | Cyborg 3 LAND STPT 8 |

## Package Coordination Draft
### PKG 1883 - INT (5 flights, selected by explicit request)
- Targets: No named tactical target resolved
- Enemy situation: 10 enemy non-air unit records within 35 NM of Route Black/CAP anchors; dominant nearby classes: Towed Gun x4, Engineer x4, Air Defense x1, Rocket x1. 7 strategic air-defense records with active tracking radars within 60 NM; strategic AD classes: Air Defense x7. 3 strategic ADA candidates filtered for inactive/missing tracking radars. 7 enemy squadron bases within 100 NM hosting 15 active squadrons.
- INI plan correlation: TIMING is bracketed by TGT 1; the drawn line has 10 points nearest SAD
- Close INI marks: TGT 0 -> TAKEOFF 1424 (0.3 NM); TGT 2 -> CAP 1434 (0.3 NM); TGT 3 -> CAP 1436 (0.3 NM); TGT 5 -> TAKEOFF 1424 (0.3 NM); TGT 6 -> REFUEL 1334 (0.3 NM); TGT 7 -> LAND 1334 (0.3 NM); TGT 1 -> TIMING 1431 (3.5 NM); BAR -> CAP 1436 (0.1 NM); GRD -> CAP 1436 (0.2 NM); A -> SAD 1445 (0.6 NM)
- Drawn-line read: Drawn INI lineSTPT geometry tracks closest to SAD rather than the CAP/SAD station points.
- Commander context: Three INT flights divide SAD responsibilities across A-B, B-A, and B-C-D while Mudhen holds Guardpost in the west and Cobra holds BARRIER in the east. Watchtower/WCH is an EWR target of opportunity; A-E are supply depots feeding maneuver forces; Foxtrot is the alternate target if the route is cold.
- Route context: Route Black is represented by the pre-planned threat steerpoints in the mission INI.
- Fallback logic: If there are no movers on Route Black, shift to Foxtrot as the alternate target.
- SAD contracts: Cyborg 3: SAD A-B (Search and prosecute movers between A and B.); Warhawk 3: SAD B-A (Reverse the first search lane, working movers from B back toward A.); Panther 3: SAD B-C-D (Extend the search through B, C, and D.)
- CAP contracts: Mudhen 3: Guardpost (west CAP area) - Hold the western BARCAP station.; Cobra 3: BARRIER (east CAP area) - Hold the eastern BARCAP station.
- Target opportunities: WCH Watchtower: EWR site - Target of opportunity.; A-E Depot set: Enemy supply depots - A through E include depots supplying enemy maneuver forces.; F Foxtrot: Alternate target - Use if no movers are found on Route Black.

### Friendly Package Composition
- Support: AWACS: Chalice 1 (1x E-3, ELINT STPT 3 1404 grid 698/357; ELINT STPT 4 1409 grid 659/327); TANKER: Sentry 3 (1x KC-135R, TANKER STPT 4 1405 grid 451/348; TANKER STPT 5 1415 grid 470/250)

| C/S | Aircraft | Role | Weapons | Laser | TACAN | T/O | TOT | Target/Area | Remarks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cyborg 3 | 4x F-16C-32 ROKAF | INT | 20mm M61 x51, AIM-9M Sidewinder x4, AN/ALQ-131(v)1 x1, Mk-82 x6, Tank 370gal x2 | 1688 | not assigned | 1424 | 1445 | SAD A-B | Search and prosecute movers between A and B. |
| Warhawk 3 | 4x F-16C-32 ROKAF | INT | 20mm M61 x51, AIM-9M Sidewinder x4, AN/ALQ-131(v)1 x1, Mk-82 SE x6, Tank 370gal x2 | 1688 | not assigned | 1423 | 1441 | SAD B-A | Reverse the first search lane, working movers from B back toward A. |
| Panther 3 | 4x F-16C-32 ROKAF | INT | 20mm M61 x51, AIM-9M Sidewinder x4, AN/ALQ-131(v)1 x1, Mk-82 SE x6, Tank 370gal x2 | 1688 | not assigned | 1422 | 1441 | SAD B-C-D | Extend the search through B, C, and D. |
| Mudhen 3 | 4x F-16C-30 | BARCAP2 | 20mm M61 x51, AIM-7M Sparrow x2, AIM-9M Sidewinder x4, AN/ALQ-131(v)1 x1, Tank 370gal x2 | 1688 | not assigned | 1420 | 1438 | CAP Guardpost | Hold the western BARCAP station. |
| Cobra 3 | 4x F-16C-30 | BARCAP2 | 20mm M61 x51, AIM-7M Sparrow x2, AIM-9M Sidewinder x4, AN/ALQ-131(v)1 x1, Tank 370gal x2 | 1688 | not assigned | 1419 | 1438 | CAP BARRIER | Hold the eastern BARCAP station. |

### AWACS / Tanker Tracks
| Role | C/S | Aircraft | TOT | Station / Track | TACAN | Weapons |
| --- | --- | --- | --- | --- | --- | --- |
| AWACS | Chalice 1 | 1x E-3 | 1249 | ELINT STPT 3 1404 grid 698/357; ELINT STPT 4 1409 grid 659/327 | not assigned | none |
| TANKER | Sentry 3 | 1x KC-135R | 1343 | TANKER STPT 4 1405 grid 451/348; TANKER STPT 5 1415 grid 470/250 | 117Y slot 0 | none |

## Other Package Factors
Non-player packages are only listed here when their decoded tactical waypoints are close enough in space and time to interact with the player package, affect the target area, or require deconfliction.

| PKG | Relation | Teams | Missions | Callsigns | Closest point | Player anchor | Dist NM | Time delta | Why it matters |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2059 | enemy | DPRK | BAI x1, TARCAP x2 | Mauler 7, Nightwing 4, Blood 4 | Nightwing 4 CAP STPT 3 | Cyborg 3 SAD STPT 5 | 2.4 | 5 min | Enemy TARCAP element near the player target/CAP area; closest to Cyborg 3 SAD STPT 5. |
| 1757 | enemy | DPRK | BAI x1, TARCAP x2 | Mack 6, Blade 2, Hopper 2 | Blade 2 CAP STPT 4 | Cyborg 3 SAD STPT 5 | 2.4 | 16 min | Enemy TARCAP element near the player target/CAP area; closest to Cyborg 3 SAD STPT 5. |
| 2431 | enemy | DPRK | BAI x1, TARCAP x2 | Eyeball 2, Stonecat 2, Jump 2 | Stonecat 2 CAP STPT 4 | Cyborg 3 SAD STPT 5 | 2.4 | 27 min | Enemy TARCAP element near the player target/CAP area; closest to Cyborg 3 SAD STPT 5. |
| 2071 | enemy | DPRK | CAS x1, TARCAP x1 | Chowder 5, Eyeball 3 | Chowder 5 SAD STPT 4 | Cyborg 3 SAD STPT 5 | 3.8 | 61 min | Enemy CAS element near the player target/CAP area; closest to Cyborg 3 SAD STPT 5. |
| 1801 | enemy | DPRK | CAS x1, TARCAP x1 | Dipper 1, Satan 4 | Dipper 1 SAD STPT 6 | INI F | 4.2 | 46 min | Enemy CAS element near the player target/CAP area; closest to INI F. |
| 1795 | enemy | DPRK, USSR | BAI x1, TARCAP x1 | Hog 4, Rafale 4 | Rafale 4 CAP STPT 4 | INI TGT 3 | 5.4 | 48 min | Enemy TARCAP element near the player target/CAP area; closest to INI TGT 3. |
| 1793 | enemy | DPRK | BARCAP2 x1 | Jaguar 3 | Jaguar 3 CAP STPT 2 | INI F | 6.0 | 37 min | Enemy BARCAP2 element near the player target/CAP area; closest to INI F. |
| 1453 | enemy | DPRK | BARCAP2 x1 | Buzzsaw 6 | Buzzsaw 6 CAP STPT 2 | INI F | 6.0 | 60 min | Enemy BARCAP2 element near the player target/CAP area; closest to INI F. |

## Comm Ladder
Campaign comm sidecars currently expose Link 16 rows, but this save's `.l16` flight numbers do not match the CAM camp IDs/name IDs/VU numbers for package 1883. UHF/VHF preset channels are not decoded from the campaign bundle yet.

| Element | Role | TACAN | Laser | Link 16 STN | F2F | Mission | EW | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cyborg 3 | INT | not assigned | 1688 | unresolved | unresolved | unresolved | unresolved | SAD A-B: Search and prosecute movers between A and B. |
| Warhawk 3 | INT | not assigned | 1688 | unresolved | unresolved | unresolved | unresolved | SAD B-A: Reverse the first search lane, working movers from B back toward A. |
| Panther 3 | INT | not assigned | 1688 | unresolved | unresolved | unresolved | unresolved | SAD B-C-D: Extend the search through B, C, and D. |
| Mudhen 3 | BARCAP2 | not assigned | 1688 | unresolved | unresolved | unresolved | unresolved | CAP Guardpost: west CAP area - Hold the western BARCAP station. |
| Cobra 3 | BARCAP2 | not assigned | 1688 | unresolved | unresolved | unresolved | unresolved | CAP BARRIER: east CAP area - Hold the eastern BARCAP station. |
| Chalice 1 | AWACS | not assigned | n/a | unresolved | unresolved | unresolved | unresolved | ELINT STPT 3 1404 grid 698/357; ELINT STPT 4 1409 grid 659/327 |
| Sentry 3 | TANKER | 117Y slot 0 | n/a | unresolved | unresolved | unresolved | unresolved | TANKER STPT 4 1405 grid 451/348; TANKER STPT 5 1415 grid 470/250 |

## Enemy Situation And Air Defense Estimate
This is a campaign-data estimate: enemy battalion/unit positions are measured against the decoded Route Black, CAP, SAD, and correlated INI anchors. The air-defense section is strategic-only: fixed Air Defense classes or units with at least 15 campaign-grid cells of air/low-air range, and each listed site has a nonzero decoded roster slot for its tracking radar. Class names and equipment come from Falcon object tables.
- Enemy teams considered: DPRK, PRC, USSR
- Basis: Distances are from enemy battalion grid positions to decoded package route/CAP/SAD anchors and correlated INI marks. Strategic ADA requires an active decoded tracking-radar roster slot. Anchor count: 45.
- Summary: 10 enemy non-air unit records within 35 NM of Route Black/CAP anchors; dominant nearby classes: Towed Gun x4, Engineer x4, Air Defense x1, Rocket x1. 7 strategic air-defense records with active tracking radars within 60 NM; strategic AD classes: Air Defense x7. 3 strategic ADA candidates filtered for inactive/missing tracking radars. 7 enemy squadron bases within 100 NM hosting 15 active squadrons.
- Airbase threat: Closest squadron bases: Hyon-Ni Airbase (4 sqn: Q-5II; MiG-19PM; J-6; MiG-21bis), Koksan Airbase (2 sqn: Il-28; MiG-29A), Okpyongni Highwaystrip (1 sqn: MiG-21bis), Sangwon Highwaystrip (2 sqn: Q-5II; MiG-21MF).

### Strategic Air Defense Units Near Route Black
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Nearest anchor | Dist NM | UCD air rng | UCD low rng | Strength air/low |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1689 | DPRK | Air Defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | Fan Song F (slot 3, 1/1) | 490.0 | 512.0 | INI GRD | 7.1 | 30 | 25 | 70/70 |
| 1627 | DPRK | Air Defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | Fan Song F (slot 3, 1/1) | 520.0 | 583.0 | INI TGT 3 | 38.1 | 30 | 25 | 70/70 |
| 2935 | DPRK | Air Defense | SA-3 (S-125); Low Blow; ZPU-2; KrAz T 255B; Flat Face | Low Blow (slot 2, 1/1) | 414.0 | 501.0 | Mudhen 3 CAP STPT 3 @ 1436 | 42.7 | 17 | 15 | 70/70 |
| 2953 | DPRK | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 469.0 | 586.0 | INI GRD | 48.7 | 18 | 15 | 60/60 |
| 1759 | DPRK | Air Defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | Fan Song F (slot 3, 1/1) | 401.0 | 507.0 | Mudhen 3 CAP STPT 3 @ 1436 | 49.9 | 30 | 25 | 70/70 |
| 2951 | DPRK | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 397.0 | 505.0 | Mudhen 3 CAP STPT 3 @ 1436 | 51.9 | 18 | 15 | 60/60 |
| 1751 | DPRK | Air Defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | Fan Song F (slot 3, 1/1) | 399.0 | 556.0 | Mudhen 3 CAP STPT 3 @ 1436 | 59.4 | 30 | 25 | 70/70 |

### Enemy Squadron Bases Within 100 NM
| Airbase ID | Name | Team | Active sqns | Aircraft | Operational | Grid X | Grid Y | Nearest anchor | Dist NM | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 952 | Hyon-Ni Airbase | DPRK | 4 | Q-5II; MiG-19PM; J-6; MiG-21bis | 100% | 507.8 | 524.6 | INI GRD | 15.8 | Usable, damaged (20 destroyed / 3 damaged facilities) |
| 949 | Koksan Airbase | DPRK | 2 | Il-28; MiG-29A | 100% | 434.1 | 533.4 | Mudhen 3 CAP STPT 3 @ 1436 | 36.8 | Usable |
| 965 | Okpyongni Highwaystrip | DPRK | 1 | MiG-21bis | 100% | 496.5 | 597.5 | INI TGT 3 | 50.3 | Usable, damaged (0 destroyed / 7 damaged facilities) |
| 947 | Sangwon Highwaystrip | DPRK | 2 | Q-5II; MiG-21MF | 100% | 388.6 | 541.9 | Mudhen 3 CAP STPT 3 @ 1436 | 60.9 | Usable, damaged (18 destroyed / 16 damaged facilities) |
| 950 | Kangdong Airstrip | DPRK | 2 | MiG-23ML; J-6 | unknown | 385.9 | 586.1 | Mudhen 3 CAP STPT 3 @ 1436 | 74.5 | No damage delta |
| 955 | Yonpo Airbase | DPRK | 3 | Su-7BMK; J-6; MiG-21MF | 100% | 515.0 | 655.4 | INI TGT 3 | 76.8 | Usable, damaged (13 destroyed / 12 damaged facilities) |
| 972 | Sunchon  (ZKSC) | DPRK | 1 | MiG-29A | unknown | 373.4 | 614.5 | Mudhen 3 CAP STPT 3 @ 1436 | 89.8 | No damage delta |

### Nearby Enemy Unit Records
| ID | Team | Class | Category | Equipment | Grid X | Grid Y | Nearest anchor | Dist NM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2873 | DPRK | Towed Gun | other | 2A18 (D-30); KrAz F 255B; KrAz T 255B; UAZ-469 | 505.0 | 479.0 | INI F | 0.2 |
| 2453 | DPRK | Towed Gun | other | 2A18 (D-30); KrAz F 255B; KrAz T 255B; UAZ-469 | 492.0 | 481.0 | Mudhen 3 CAP STPT 2 @ 1435 | 6.9 |
| 2505 | DPRK | Towed Gun | other | 2A18 (D-30); KrAz F 255B; KrAz T 255B; UAZ-469 | 492.0 | 481.0 | Mudhen 3 CAP STPT 2 @ 1435 | 6.9 |
| 1689 | DPRK | Air Defense | air defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | 490.0 | 512.0 | INI GRD | 7.1 |
| 1433 | DPRK | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 527.0 | 530.0 | INI BAR | 10.7 |
| 1435 | DPRK | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 507.0 | 524.0 | INI GRD | 15.3 |
| 2445 | DPRK | Towed Gun | other | 2A18 (D-30); KrAz F 255B; KrAz T 255B; UAZ-469 | 470.0 | 480.0 | Mudhen 3 CAP STPT 3 @ 1436 | 16.1 |
| 2867 | DPRK | Rocket | other | BM-21; KrAz T 255B; UAZ-469 | 463.0 | 483.0 | Mudhen 3 CAP STPT 3 @ 1436 | 18.4 |
| 1427 | DPRK | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 459.0 | 480.0 | Mudhen 3 CAP STPT 3 @ 1436 | 21.0 |
| 1429 | DPRK | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 440.0 | 491.0 | Mudhen 3 CAP STPT 3 @ 1436 | 28.9 |

## Coordinate Appendix
Location data is intentionally separated from the commander-facing read. Flight steerpoints use decoded campaign grid coordinates; INI points also show source world-foot coordinates and the converted campaign grid.

### PKG 1883 Flight Steerpoints
| C/S | STPT | Action | Arrive | Grid X | Grid Y | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cyborg 3 | 0 | TAKEOFF | 1424 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Cyborg 3 | 2 | TIMING | 1431 | 507.0 | 396.0 | 2200.0 |  |
| Cyborg 3 | 3 | PUSH | 1439 | 514.0 | 413.0 | 2200.0 |  |
| Cyborg 3 | 4 | SAD | 1445 | 516.0 | 486.0 | 1600.0 |  |
| Cyborg 3 | 5 | SAD | 1447 | 538.0 | 475.0 | 1600.0 |  |
| Cyborg 3 | 6 | SPLIT | 1512 | 526.0 | 402.0 | 2100.0 |  |
| Cyborg 3 | 8 | LAND | 1518 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Cyborg 3 | 9 | REFUEL | 1334 | 460.0 | 299.0 | 2000.0 |  |
| Cyborg 3 | 10 | LAND | 1334 | 484.0 | 333.0 | 0.0 | Yecheon AB (RKTY) (objective 928) |
| Warhawk 3 | 0 | TAKEOFF | 1423 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Warhawk 3 | 2 | TIMING | 1431 | 507.0 | 396.0 | 2200.0 |  |
| Warhawk 3 | 3 | PUSH | 1438 | 514.0 | 413.0 | 2200.0 |  |
| Warhawk 3 | 4 | SAD | 1444 | 516.0 | 486.0 | 1600.0 |  |
| Warhawk 3 | 5 | SAD | 1447 | 538.0 | 475.0 | 1600.0 |  |
| Warhawk 3 | 6 | SPLIT | 1512 | 526.0 | 402.0 | 2100.0 |  |
| Warhawk 3 | 8 | LAND | 1518 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Warhawk 3 | 9 | REFUEL | 1518 | 460.0 | 299.0 | 2000.0 |  |
| Warhawk 3 | 10 | LAND | 1518 | 484.0 | 333.0 | 0.0 | Yecheon AB (RKTY) (objective 928) |
| Panther 3 | 0 | TAKEOFF | 1422 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Panther 3 | 2 | TIMING | 1430 | 507.0 | 396.0 | 2200.0 |  |
| Panther 3 | 3 | PUSH | 1437 | 514.0 | 413.0 | 2200.0 |  |
| Panther 3 | 4 | SAD | 1443 | 516.0 | 486.0 | 1600.0 |  |
| Panther 3 | 5 | SAD | 1445 | 529.0 | 479.0 | 1600.0 |  |
| Panther 3 | 6 | SPLIT | 1510 | 526.0 | 402.0 | 2100.0 |  |
| Panther 3 | 8 | LAND | 1516 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Panther 3 | 9 | REFUEL | 1516 | 460.0 | 299.0 | 2000.0 |  |
| Panther 3 | 10 | LAND | 1516 | 484.0 | 333.0 | 0.0 | Yecheon AB (RKTY) (objective 928) |
| Mudhen 3 | 0 | TAKEOFF | 1420 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Mudhen 3 | 2 | CAP | 1435 | 502.0 | 489.0 | 2100.0 |  |
| Mudhen 3 | 3 | CAP | 1436 | 493.0 | 499.0 | 2100.0 |  |
| Mudhen 3 | 5 | LAND | 1508 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Mudhen 3 | 6 | REFUEL | 1508 | 460.0 | 299.0 | 2000.0 |  |
| Mudhen 3 | 7 | LAND | 1508 | 484.0 | 333.0 | 0.0 | Yecheon AB (RKTY) (objective 928) |
| Cobra 3 | 0 | TAKEOFF | 1419 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Cobra 3 | 2 | CAP | 1434 | 527.0 | 498.0 | 2100.0 |  |
| Cobra 3 | 3 | CAP | 1436 | 540.0 | 515.0 | 2100.0 |  |
| Cobra 3 | 5 | LAND | 1510 | 511.0 | 313.0 | 0.0 | Depot #4 (objective 1000) |
| Cobra 3 | 6 | REFUEL | 1510 | 460.0 | 299.0 | 2000.0 |  |
| Cobra 3 | 7 | LAND | 1510 | 484.0 | 333.0 | 0.0 | Yecheon AB (RKTY) (objective 928) |

### Linked Support Flight Coordinates
| Role | C/S | STPT | Action | Arrive | Grid X | Grid Y | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWACS | Chalice 1 | 0 | TAKEOFF | 1210 | 1023.0 | 105.0 | 2500.0 | Squadron 1549 (squadron 1549) |
| AWACS | Chalice 1 | 1 | TIMING | 1218 | 941.0 | 169.0 | 2800.0 |  |
| AWACS | Chalice 1 | 3 | ELINT | 1404 | 698.0 | 357.0 | 2600.0 |  |
| AWACS | Chalice 1 | 4 | ELINT | 1409 | 659.0 | 327.0 | 2600.0 |  |
| AWACS | Chalice 1 | 6 | LAND | 1838 | 1023.0 | 105.0 | 2600.0 | Squadron 1549 (squadron 1549) |
| AWACS | Chalice 1 | 7 | LAND | 1329 | 1009.0 | 75.0 | 0.0 | Rakwon-up Town (objective 2302) |
| TANKER | Sentry 3 | 0 | TAKEOFF | 1319 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| TANKER | Sentry 3 | 2 | TIMING | 1332 | 450.0 | 290.0 | 2400.0 |  |
| TANKER | Sentry 3 | 4 | TANKER | 1405 | 451.0 | 348.0 | 2400.0 |  |
| TANKER | Sentry 3 | 5 | TANKER | 1415 | 470.0 | 250.0 | 2400.0 |  |
| TANKER | Sentry 3 | 7 | LAND | 1902 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| TANKER | Sentry 3 | 8 | LAND | 1329 | 410.0 | 124.0 | 0.0 | unresolved 2301 |

### Weather Sample Coordinates
| Area | Time | FMAP Row | FMAP Col | Grid X | Grid Y | Conditions | Wind | Visibility km | Cloud base ft | Contrail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Takeoff | 1424 | 40 | 29 | 511.0 | 313.0 | Fair OVC | 181/3 kt | 59.5 | 10000 | FL240 |
| Target Area | 1438 | 31 | 30 | 520.9 | 481.0 | Fair OVC | 263/1 kt | 59.5 | 10000 | FL240 |
| Landing | 1518 | 40 | 29 | 511.0 | 313.0 | Fair OVC | 181/3 kt | 59.5 | 10000 | FL240 |

### INI Planning Steerpoints
| Kind | Label | Code | INI X ft | INI Y ft | Grid X | Grid Y | Nearest package route point |
| --- | --- | --- | --- | --- | --- | --- | --- |
| target | TGT 0 | 1 | 1028273.8 | 1677709.8 | 511.4 | 313.4 | Cyborg 3 TAKEOFF STPT 0 @ 1424 0.3 NM |
| target | TGT 1 | 0 | 1297232.1 | 1684269.8 | 513.4 | 395.4 | Cyborg 3 TIMING STPT 2 @ 1431 3.5 NM |
| target | TGT 2 | 12 | 1635070.0 | 1730189.5 | 527.4 | 498.4 | Cobra 3 CAP STPT 2 @ 1434 0.3 NM |
| target | TGT 3 | 12 | 1690829.8 | 1772829.2 | 540.4 | 515.4 | Cobra 3 CAP STPT 3 @ 1436 0.3 NM |
| target | TGT 4 | 0 | 1208672.6 | 1710509.6 | 521.4 | 368.4 |  |
| target | TGT 5 | 7 | 1028273.8 | 1677709.8 | 511.4 | 313.4 | Cyborg 3 TAKEOFF STPT 0 @ 1424 0.3 NM |
| target | TGT 6 | 4 | 982354.0 | 1510430.8 | 460.4 | 299.4 | Cyborg 3 REFUEL STPT 9 @ 1334 0.3 NM |
| target | TGT 7 | 7 | 1093873.4 | 1589150.2 | 484.4 | 333.4 | Cyborg 3 LAND STPT 10 @ 1334 0.3 NM |
| ppt | A |  | 1595510.1 | 1696149.9 | 517.0 | 486.3 | Cyborg 3 SAD STPT 4 @ 1445 0.6 NM |
| ppt | B |  | 1577613.6 | 1724295.2 | 525.6 | 480.9 | Panther 3 SAD STPT 5 @ 1445 2.1 NM |
| ppt | C |  | 1575556.0 | 1732800.1 | 528.2 | 480.2 | Panther 3 SAD STPT 5 @ 1445 0.8 NM |
| ppt | D |  | 1603677.0 | 1724432.4 | 525.6 | 488.8 | Cobra 3 CAP STPT 2 @ 1434 5.0 NM |
| ppt | WCH |  | 1581587.2 | 1692430.9 | 515.9 | 482.1 | Cyborg 3 SAD STPT 4 @ 1445 2.1 NM |
| ppt | E |  | 1541396.6 | 1733525.6 | 528.4 | 469.8 | Panther 3 SAD STPT 5 @ 1445 5.0 NM |
| ppt | GRD |  | 1637815.2 | 1618389.4 | 493.3 | 499.2 | Mudhen 3 CAP STPT 3 @ 1436 0.2 NM |
| ppt | BAR |  | 1689865.2 | 1771742.2 | 540.0 | 515.1 | Cobra 3 CAP STPT 3 @ 1436 0.1 NM |
| ppt | F |  | 1571495.4 | 1657793.0 | 505.3 | 479.0 | Mudhen 3 CAP STPT 2 @ 1435 5.7 NM |
| linestpt | LINE 0 |  | 1595291.9 | 1696414.0 | 517.1 | 486.2 | Cyborg 3 SAD STPT 4 @ 1445 0.6 NM |
| linestpt | LINE 1 |  | 1593588.6 | 1704248.9 | 519.5 | 485.7 | Cyborg 3 SAD STPT 4 @ 1445 1.9 NM |
| linestpt | LINE 2 |  | 1587457.0 | 1703908.2 | 519.4 | 483.9 | Cyborg 3 SAD STPT 4 @ 1445 2.2 NM |
| linestpt | LINE 3 |  | 1584845.4 | 1710607.6 | 521.4 | 483.1 | Cyborg 3 SAD STPT 4 @ 1445 3.3 NM |
| linestpt | LINE 4 |  | 1584164.1 | 1717534.0 | 523.5 | 482.9 | Panther 3 SAD STPT 5 @ 1445 3.6 NM |
| linestpt | LINE 5 |  | 1572042.1 | 1727310.9 | 526.5 | 479.2 | Panther 3 SAD STPT 5 @ 1445 1.4 NM |
| linestpt | LINE 6 |  | 1571356.8 | 1727145.1 | 526.4 | 478.9 | Panther 3 SAD STPT 5 @ 1445 1.4 NM |
| linestpt | LINE 7 |  | 1561231.2 | 1728948.4 | 527.0 | 475.9 | Panther 3 SAD STPT 5 @ 1445 2.0 NM |
| linestpt | LINE 8 |  | 1548886.6 | 1725064.6 | 525.8 | 472.1 | Panther 3 SAD STPT 5 @ 1445 4.1 NM |
| linestpt | LINE 9 |  | 1538899.9 | 1732554.6 | 528.1 | 469.1 | Panther 3 SAD STPT 5 @ 1445 5.4 NM |

### Strategic Air Defense Coordinates
Air-defense rows use saved campaign battalion/unit grid coordinates and exclude short-range point/base defenses. They are enemy strategic sites with active decoded tracking-radar roster slots.
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Nearest package/INI anchor | Dist NM | UCD air rng | UCD low rng |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1689 | DPRK | Air Defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | Fan Song F (slot 3, 1/1) | 490.0 | 512.0 | INI GRD | 7.1 | 30 | 25 |
| 1627 | DPRK | Air Defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | Fan Song F (slot 3, 1/1) | 520.0 | 583.0 | INI TGT 3 | 38.1 | 30 | 25 |
| 2935 | DPRK | Air Defense | SA-3 (S-125); Low Blow; ZPU-2; KrAz T 255B; Flat Face | Low Blow (slot 2, 1/1) | 414.0 | 501.0 | Mudhen 3 CAP STPT 3 @ 1436 | 42.7 | 17 | 15 |
| 2953 | DPRK | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 469.0 | 586.0 | INI GRD | 48.7 | 18 | 15 |
| 1759 | DPRK | Air Defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | Fan Song F (slot 3, 1/1) | 401.0 | 507.0 | Mudhen 3 CAP STPT 3 @ 1436 | 49.9 | 30 | 25 |
| 2951 | DPRK | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 397.0 | 505.0 | Mudhen 3 CAP STPT 3 @ 1436 | 51.9 | 18 | 15 |
| 1751 | DPRK | Air Defense | SA-2 (S-75); Fan Song F; ZSU-23-4; ZIL-131; KrAz T 255B | Fan Song F (slot 3, 1/1) | 399.0 | 556.0 | Mudhen 3 CAP STPT 3 @ 1436 | 59.4 | 30 | 25 |

### Enemy Airbase Coordinates
Airbase rows are enemy squadron base objectives with active squadron rosters, greater than 0 percent decoded operational state, and within 100 NM of package/INI anchors.
| Airbase ID | Name | Objective class | Team | Active sqns | Aircraft | Operational | Source X ft | Source Y ft | Grid X | Grid Y | Nearest package/INI anchor | Dist NM | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 952 | Hyon-Ni Airbase | Hyon-ni AB | DPRK | 4 | Q-5II; MiG-19PM; J-6; MiG-21bis | 100% | 1721192.5 | 1665990.4 | 507.8 | 524.6 | INI GRD | 15.8 | Usable, damaged (20 destroyed / 3 damaged facilities) |
| 949 | Koksan Airbase | Koksan AB | DPRK | 2 | Il-28; MiG-29A | 100% | 1750033.3 | 1424108.3 | 434.1 | 533.4 | Mudhen 3 CAP STPT 3 @ 1436 | 36.8 | Usable |
| 965 | Okpyongni Highwaystrip | Okpyong-ni AS | DPRK | 1 | MiG-21bis | 100% | 1960332.6 | 1629100.4 | 496.5 | 597.5 | INI TGT 3 | 50.3 | Usable, damaged (0 destroyed / 7 damaged facilities) |
| 947 | Sangwon Highwaystrip | Sangwon AS | DPRK | 2 | Q-5II; MiG-21MF | 100% | 1777962.4 | 1274803.5 | 388.6 | 541.9 | Mudhen 3 CAP STPT 3 @ 1436 | 60.9 | Usable, damaged (18 destroyed / 16 damaged facilities) |
| 950 | Kangdong Airstrip | Kangdong AS | DPRK | 2 | MiG-23ML; J-6 | unknown | 1922737.3 | 1266157.6 | 385.9 | 586.1 | Mudhen 3 CAP STPT 3 @ 1436 | 74.5 | No damage delta |
| 955 | Yonpo Airbase | Yonpo AB | DPRK | 3 | Su-7BMK; J-6; MiG-21MF | 100% | 2150249.9 | 1689616.1 | 515.0 | 655.4 | INI TGT 3 | 76.8 | Usable, damaged (13 destroyed / 12 damaged facilities) |
| 972 | Sunchon  (ZKSC) | Sunchon AB | DPRK | 1 | MiG-29A | unknown | 2016003.5 | 1225118.5 | 373.4 | 614.5 | Mudhen 3 CAP STPT 3 @ 1436 | 89.8 | No damage delta |

### Resolved Location Objects
| Kind | ID | Name | Source X | Source Y | Source Z |
| --- | --- | --- | --- | --- | --- |
| objective | 928 | Yecheon AB (RKTY) | 999560.8 | 1926975.0 | 0.0 |
| objective | 1000 | Depot #4 | 1570611.8 | 1659453.4 | 0.0 |

## Map Products
- Full-route chart map: `package_1883_route_threat_map_skyvector.png`
- Tactical target-area chart: `package_1883_target_area_zoom_skyvector.png`
- Objective-area close-up chart: `package_1883_objective_area_zoom_skyvector.png`
- Weather review chart: `package_1883_weather_map_skyvector.png`
- Close-up map note: objective-area charts preserve CAP anchors Guardpost (GRD), BARRIER (BAR) alongside the target and Route Black geometry.

![PKG 1883 objective-area zoom](package_1883_objective_area_zoom_skyvector.png)

## Human Interpretation Needed
- Confirm package inclusion against the actual mission commander's intent.
- Convert package tables into contracts, push flow, and target-file slides.
- Validate decoded aircraft/loadout/laser/TACAN values against the BMS UI before publishing a live mission brief.
- Validate inferred HHMM times against BMS UI or the human deck before treating them as authoritative.
