# BMS Briefing Workup: 740pre

Internal transitional artifact for briefing iteration. Keep provenance, gaps, and correlation notes here; `generated_briefing.md` is the player-facing mission brief.

## Timing Source
- HHMM values use clock base `1400` and campaign time `19745032`.

## Reference Deck Package Check
- Mentioned in deck: none
- Present in local CAM: none
- Missing from local CAM: none

## Operating Area Inputs
- PPT labels and rings: 0 ORO; 1 10 (50.0 NM); 2 15 (6.5 NM); 3 10 (50.0 NM); 4 SA5 (54.0 NM); 5 CRO; 6 BLU; 7 SA6 (12.5 NM); 8 10 (50.0 NM); 9 TIG; 10 WWO; 11 BAN; 12 BAN
- INI grid transform: `grid_x = (ini_y / 3280.84); grid_y = (ini_x / 3280.84)`

## Meteorology Workup
- Source: `C:\Falcon BMS 4.38\Data\Campaign\740pre.fmap` (v8+, 59x59 cells). Map wind 284/18 kt.
- Sampling basis: FMAP row 0 is north; campaign grid Y is inverted into weather row space before sampling.
- Theater mix: Sunny=2541, Fair=658, Poor=282

## Meteorology
| Area | Local time | Day/Night | Conditions | Cloud base | Contrail layer | Temp C | Visibility km | Wind | Grid X | Grid Y |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Takeoff | 1419 | Day | Sunny CLR | 38,000 ft | 34,000 ft | 26.7 | 59.9 | 183/3 kt | 432.0 | 224.0 |
| Target Area | 1432 | Day | Sunny CLR | 38,000 ft | 34,000 ft | 28.2 | 59.9 | 293/3 kt | 543.3 | 176.8 |
| Landing | 1504 | Day | Sunny CLR | 38,000 ft | 34,000 ft | 26.7 | 59.9 | 183/3 kt | 432.0 | 224.0 |

## Bullseye
- Bullseye: grid 643.0 / 145.0
- Named references: 10 BE 079/9; BAN BE 102/10; SA5 BE 061/19; WWO BE 139/18

## Package Correlation Workup
### PKG 7040 - SEAD (3 flights, selected by explicit request)
- Targets: No named tactical target listed
- Enemy situation: 22 enemy non-air unit records within 35 NM of package/INI tactical anchors; dominant nearby classes: Air Defense x9, Supply x8, Engineer x4, Motor Rifle x1. 14 strategic air-defense records with active tracking radars within 60 NM; strategic AD classes: Air Defense x14. 2 strategic ADA candidates filtered for inactive/missing tracking radars. 0 enemy squadron bases within 100 NM hosting 0 active squadrons. 15 active enemy air contact(s) at campaign time within or vectoring into 30 NM of the target area.
- INI plan correlation: INI planning marks did not correlate closely to this package route.
- Commander context: Low-altitude SA-10 East attack package from Gunsan. Hammer 2 crosses Crown low, then pops from Wolf to attack SA-10 East at short range with HARMs; if unable, Hammer 2 uses Bando for a pop-up CBU attack. Devil 5 and Devil 6 cap around Wolf and intercept bandits from the north or north-northeast.
- Fallback logic: Once SA-10 East, SA-10 West, and Orion/Gimhae are solved, retrograde southwest toward Tiger, return to medium altitude, and RTB.

## Comm Data Workup
- Link 16 rows available: 97.
- Correlation basis: Matched by CAM camp_id/name_id/VU num when possible..
- UHF/VHF preset channel decoding is not yet available from the campaign bundle.

## Other Package Factors
- No additional friendly packages are expected to affect the target area.

## Enemy Air Threat Estimate
This section avoids enemy ATO/package tasking. It is based on active enemy squadron bases within the threat radius, known aircraft types, and bearing from those bases to the package/INI target-area anchors. Treat it as likely fighter threat axes, not a prediction of specific launches, callsigns, package IDs, or timings.

- No active enemy fighter-capable airbases were identified within the current airbase threat radius.

### Active Air Contacts At Campaign Time
These are current-position contacts only. Callsigns and enemy package/tasking IDs are intentionally omitted; the brief only exposes aircraft type, rough sector, range, and the observed reason they matter.

| Sector from AO | Aircraft | Capability | Count | Nearest area | Range | Basis |
| --- | --- | --- | --- | --- | --- | --- |
| E | MiG-27 | air contact | 2 | Hammer 2 PUSH STPT 3 @ 1431 | 0.6 NM | airborne now; next leg vectors inside 30 NM by 1412 |
| NE | MiG-27 | air contact | 2 | INI TGT 6 | 1.9 NM | airborne now; next leg vectors inside 30 NM by 1403 |
| N | MiG-29S | fighter-capable | 2 | INI TGT 6 | 7.8 NM | airborne now within 30 NM of target-area anchor |
| NW | Mi-28 | air contact | 2 | Devil 5 CAP STPT 5 @ 1445 | 9.2 NM | airborne now within 30 NM of target-area anchor |
| W | Mi-8 | air contact | 2 | INI TGT 6 | 11.2 NM | airborne now within 30 NM of target-area anchor |
| W | Ka-52K | air contact | 1 | INI TGT 6 | 15.4 NM | airborne now within 30 NM of target-area anchor |
| W | Mi-8 | air contact | 2 | INI TGT 6 | 15.8 NM | airborne now within 30 NM of target-area anchor |
| NE | MiG-27 | air contact | 2 | Hammer 2 PUSH STPT 3 @ 1431 | 19.9 NM | airborne now within 30 NM of target-area anchor |
| NW | MiG-27 | air contact | 2 | Devil 5 CAP STPT 5 @ 1445 | 20.2 NM | airborne now within 30 NM of target-area anchor |
| NW | Mi-8 | air contact | 2 | INI TGT 6 | 21.3 NM | airborne now within 30 NM of target-area anchor |
| NE | Su-39 | air contact | 2 | INI SA5 | 22.0 NM | airborne now; next leg vectors inside 30 NM by 1412 |
| N | Mi-8 | air contact | 2 | INI TGT 6 | 24.4 NM | airborne now within 30 NM of target-area anchor |
| NW | MiG-31 | air contact | 2 | INI TGT 6 | 24.5 NM | airborne now within 30 NM of target-area anchor |
| NW | Su-39 | air contact | 2 | INI SA5 | 26.4 NM | airborne now; next leg vectors inside 30 NM by 1408 |
| NW | Ka-52K | air contact | 2 | INI SA5 | 28.0 NM | airborne now within 30 NM of target-area anchor |

## Comm Ladder
| Element | Role | TACAN | Laser | Link 16 STN | F2F | Mission | EW | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hammer 2 | SEAD | not assigned | 1688 | 2666 | 65 | 65 | 1 | SEAD/DEAD SA-10 East from Wolf: Wolf / Bando - Cross Crown low, pop from Wolf to shoot SA-10 East at short range with HARMs, and if unable execute the Bando pop-up CBU option. |
| Devil 5 | BARCAP | not assigned | 1688 | 2750 | 1 | 65 | -1 | Wolf CAP / north threat intercept: Wolf - CAP around Wolf and intercept fighters from the north or north-northeast. |
| Devil 6 | BARCAP | not assigned | 1688 | 3154 | 1 | 65 | -1 | Wolf CAP / north threat intercept: Wolf - Support Devil 5 around Wolf and intercept fighters from the north or north-northeast. |
| Sentry 1 | AWACS | not assigned | n/a | 1577 | 65 | 68 | -1 | ELINT STPT 4 1357 BE 298/118; ELINT STPT 5 1401 BE 311/111 |
| Copper 5 | TANKER | 124Y slot 0 | n/a |  |  |  |  | TANKER STPT 4 1403 BE 302/133; TANKER STPT 5 1413 BE 305/186 |

## Enemy Situation And Air Defense Estimate
Threats below are focused on the package route, CAP/SAD areas, and named data-cartridge anchors. Strategic air-defense rows only include enemy Air Defense class systems with active tracking radars.
- Enemy teams considered: DPRK, Japan, PRC, USSR
- Summary: 22 enemy ground/naval units within 35 NM of package/INI tactical anchors; dominant nearby classes: Air Defense x9, Supply x8, Engineer x4, Motor Rifle x1. 14 strategic air-defense sites with active tracking radars within 60 NM; strategic AD classes: Air Defense x14. 0 enemy squadron base areas within 100 NM hosting 0 active squadrons. 15 active enemy air contact(s) at campaign time within or vectoring into 30 NM of the target area.
- Airbase threat: Closest squadron bases: none.

### Strategic Air Defense Units Near Package Route
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Nearest anchor | Dist NM | Air range | Low-alt range | Strength air/low |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1783 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 660.0 | 148.0 | Hammer 2 SEAD STPT 7 @ 1444 | 0.0 | 85 | 71 | 150/150 |
| 1787 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 660.0 | 148.0 | Hammer 2 SEAD STPT 7 @ 1444 | 0.0 | 18 | 15 | 60/60 |
| 1759 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 674.0 | 162.0 | INI SA5 | 0.3 | 99 | 83 | 50/50 |
| 1779 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 642.0 | 145.0 | INI 10 | 0.3 | 85 | 71 | 150/150 |
| 1767 | USSR | Air Defense | SA-11 (9K37M1); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-11 (9K37M1) (slot 0, 3/3) | 677.0 | 179.0 | INI SA5 | 9.1 | 22 | 19 | 100/100 |
| 1773 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 687.0 | 182.0 | INI SA5 | 12.6 | 85 | 71 | 150/150 |
| 1785 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 619.0 | 147.0 | INI TGT 6 | 12.6 | 18 | 15 | 60/60 |
| 1761 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 690.0 | 204.0 | INI SA5 | 24.0 | 99 | 83 | 50/50 |
| 1774 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 690.0 | 204.0 | INI SA5 | 24.0 | 85 | 71 | 150/150 |
| 1763 | USSR | Air Defense | SA-2 (S-75); Fan Song E; ZU-23; ZIL-131; KrAz T 255B | Fan Song E (slot 3, 1/1) | 643.0 | 229.0 | INI SA5 | 39.8 | 30 | 25 | 70/70 |
| 1769 | USSR | Air Defense | SA-17 (9K37M2); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-17 (9K37M2) (slot 0, 3/3) | 646.0 | 234.0 | INI SA5 | 41.6 | 30 | 25 | 100/100 |
| 1781 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | INI TGT 6 | 45.0 | 85 | 71 | 150/150 |
| 2235 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | INI TGT 6 | 45.0 | 85 | 71 | 150/150 |
| 1765 | USSR | Air Defense | SA-3 (S-125); Low Blow; ZPU-2; KrAz T 255B; Flat Face | Low Blow (slot 2, 1/1) | 686.0 | 248.0 | INI SA5 | 46.6 | 17 | 15 | 70/70 |

### Nearby Enemy Ground/Naval Units
| ID | Team | Class | Category | Equipment | Grid X | Grid Y | Nearest anchor | Dist NM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1783 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 660.0 | 148.0 | Hammer 2 SEAD STPT 7 @ 1444 | 0.0 |
| 1787 | USSR | Air Defense | air defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | 660.0 | 148.0 | Hammer 2 SEAD STPT 7 @ 1444 | 0.0 |
| 1759 | USSR | Air Defense | air defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | 674.0 | 162.0 | INI SA5 | 0.3 |
| 1779 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 642.0 | 145.0 | INI 10 | 0.3 |
| 1417 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 663.0 | 157.0 | Devil 5 CAP STPT 5 @ 1445 | 1.1 |
| 1419 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 663.0 | 157.0 | Devil 5 CAP STPT 5 @ 1445 | 1.1 |
| 2347 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 663.0 | 157.0 | Devil 5 CAP STPT 5 @ 1445 | 1.1 |
| 1409 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 676.0 | 160.0 | INI SA5 | 1.6 |
| 1411 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 676.0 | 160.0 | INI SA5 | 1.6 |
| 2339 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 676.0 | 160.0 | INI SA5 | 1.6 |
| 1421 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 669.0 | 154.0 | Devil 5 CAP STPT 5 @ 1445 | 3.3 |
| 1423 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 669.0 | 154.0 | Devil 5 CAP STPT 5 @ 1445 | 3.3 |
| 2351 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 669.0 | 154.0 | Devil 5 CAP STPT 5 @ 1445 | 3.3 |
| 1413 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 679.0 | 171.0 | INI SA5 | 5.3 |
| 1415 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 679.0 | 171.0 | INI SA5 | 5.3 |
| 2343 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 679.0 | 171.0 | INI SA5 | 5.3 |

## Coordinate Appendix
Location data is separated here so the main brief stays readable.
- Bullseye: grid 643.0 / 145.0

### PKG 7040 Flight Steerpoints
| C/S | STPT | Action | Arrive | Grid X | Grid Y | Bullseye | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hammer 2 | 0 | TAKEOFF | 1419 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Hammer 2 | 2 | TIMING | 1426 | 508.0 | 190.0 | BE 288/77 | 2200.0 |  |
| Hammer 2 | 3 | PUSH | 1431 | 530.0 | 175.0 | BE 285/63 | 2200.0 |  |
| Hammer 2 | 7 | SEAD | 1444 | 660.0 | 148.0 | BE 080/9 | 2000.0 |  |
| Hammer 2 | 10 | SPLIT | 1502 | 464.0 | 220.0 | BE 293/105 | 2100.0 |  |
| Hammer 2 | 11 | LAND | 1504 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Hammer 2 | 12 | REFUEL | 1504 | 398.0 | 309.0 | BE 304/159 | 2000.0 |  |
| Hammer 2 | 13 | LAND | 1504 | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Devil 5 | 0 | TAKEOFF | 1419 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Devil 5 | 4 | CAP | 1442 | 665.0 | 109.0 | BE 149/23 | 2100.0 |  |
| Devil 5 | 5 | CAP | 1445 | 663.0 | 155.0 | BE 063/12 | 2100.0 |  |
| Devil 5 | 7 | LAND | 1530 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Devil 5 | 8 | REFUEL | 1530 | 438.0 | 352.0 | BE 315/157 | 2000.0 |  |
| Devil 5 | 9 | LAND | 1530 | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Devil 6 | 0 | TAKEOFF | 1419 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Devil 6 | 4 | CAP | 1442 | 677.0 | 106.0 | BE 139/28 | 2100.0 |  |
| Devil 6 | 5 | CAP | 1446 | 677.0 | 154.0 | BE 075/19 | 2100.0 |  |
| Devil 6 | 7 | LAND | 1532 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Devil 6 | 8 | REFUEL | 1532 | 438.0 | 352.0 | BE 315/157 | 2000.0 |  |
| Devil 6 | 9 | LAND | 1532 | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |

### Linked Support Flight Coordinates
| Role | C/S | STPT | Action | Arrive | Grid X | Grid Y | Bullseye | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWACS | Sentry 1 | 0 | TAKEOFF | 1333 | 449.0 | 407.0 | BE 323/176 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |
| AWACS | Sentry 1 | 2 | TIMING | 1347 | 437.0 | 300.0 | BE 307/139 | 2800.0 |  |
| AWACS | Sentry 1 | 3 | PUSH | 1354 | 450.0 | 288.0 | BE 307/130 | 2800.0 |  |
| AWACS | Sentry 1 | 4 | ELINT | 1357 | 450.0 | 248.0 | BE 298/118 | 2600.0 |  |
| AWACS | Sentry 1 | 5 | ELINT | 1401 | 487.0 | 280.0 | BE 311/111 | 2600.0 |  |
| AWACS | Sentry 1 | 6 | SPLIT | 1905 | 475.0 | 322.0 | BE 316/132 | 2700.0 |  |
| AWACS | Sentry 1 | 7 | LAND | 1911 | 449.0 | 407.0 | BE 323/176 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |
| AWACS | Sentry 1 | 8 | REFUEL | 0842 | 398.0 | 309.0 | BE 304/159 | 2000.0 |  |
| AWACS | Sentry 1 | 9 | LAND | 0842 | 477.0 | 395.0 | BE 326/162 | 0.0 | Seoul AB (RKSM) (objective 1484) |
| TANKER | Copper 5 | 0 | TAKEOFF | 1313 | 421.0 | 313.0 | BE 307/150 | 0.0 | Pyeongtaek AAF (RKSG) (objective 924) |
| TANKER | Copper 5 | 2 | TIMING | 1317 | 406.0 | 302.0 | BE 304/154 | 530.0 |  |
| TANKER | Copper 5 | 4 | TANKER | 1403 | 435.0 | 277.0 | BE 302/133 | 2400.0 |  |
| TANKER | Copper 5 | 5 | TANKER | 1413 | 360.0 | 342.0 | BE 305/186 | 2400.0 |  |
| TANKER | Copper 5 | 7 | LAND | 1842 | 421.0 | 313.0 | BE 307/150 | 0.0 | Pyeongtaek AAF (RKSG) (objective 924) |
| TANKER | Copper 5 | 8 | LAND | 0830 | 470.0 | 341.0 | BE 319/141 | 0.0 | Gumi Highway Strip (objective 927) |

### Weather Sample Coordinates
| Area | Time | FMAP Row | FMAP Col | Grid X | Grid Y | Conditions | Wind | Visibility km | Briefed cloud base | Raw cumulus field ft | Contrail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Takeoff | 1419 | 46 | 24 | 432.0 | 224.0 | Sunny CLR | 183/3 kt | 59.9 | 38,000 ft | 4412 | 34,000 ft |
| Target Area | 1432 | 48 | 31 | 543.3 | 176.8 | Sunny CLR | 293/3 kt | 59.9 | 38,000 ft | 3707 | 34,000 ft |
| Landing | 1504 | 46 | 24 | 432.0 | 224.0 | Sunny CLR | 183/3 kt | 59.9 | 38,000 ft | 4412 | 34,000 ft |

### INI Planning Steerpoints
| Kind | Label | Code | INI X ft | INI Y ft | Grid X | Grid Y | Map status | Bullseye | Nearest package route point |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target | TGT 0 | 1 | 454277.2 | 1471071.0 | 448.4 | 138.5 | usable | BE 268/105 | Hammer 2 LAND STPT 13 @ 1504 0.3 NM |
| target | TGT 1 | 0 | 434597.3 | 1579310.4 | 481.4 | 132.5 | usable | BE 266/88 |  |
| target | TGT 2 | 8 | 424757.4 | 1658029.9 | 505.4 | 129.5 | usable | BE 264/75 |  |
| target | TGT 3 | 2 | 323078.0 | 1871228.6 | 570.4 | 98.5 | usable | BE 237/47 |  |
| target | TGT 4 | 0 | 401797.6 | 2015547.8 | 614.3 | 122.5 | usable | BE 232/20 |  |
| target | TGT 5 | 0 | 457557.2 | 2071307.4 | 631.3 | 139.5 | usable | BE 245/7 |  |
| target | TGT 6 | 17 | 477237.1 | 2107387.2 | 642.3 | 145.5 | usable | BE 306/0 | Hammer 2 SEAD STPT 7 @ 1444 9.7 NM |
| target | TGT 7 | 3 | 450997.2 | 1700669.6 | 518.4 | 137.5 | usable | BE 267/67 |  |
| target | TGT 8 | 7 | 454277.2 | 1471071.0 | 448.4 | 138.5 | usable | BE 268/105 | Hammer 2 LAND STPT 13 @ 1504 0.3 NM |
| target | TGT 9 | 4 | 1015153.8 | 1307072.0 | 398.4 | 309.4 | usable | BE 304/159 | Hammer 2 REFUEL STPT 12 @ 1504 0.3 NM |
| target | TGT 10 | 7 | 408357.5 | 1346431.8 | 410.4 | 124.5 | usable | BE 265/126 |  |
| target | TGT 11 | 7 | 736355.5 | 1418591.4 | 432.4 | 224.4 | usable | BE 291/122 | Hammer 2 TAKEOFF STPT 0 @ 1419 0.3 NM |
| target | TGT 12 | 4 | 1015153.8 | 1307072.0 | 398.4 | 309.4 | usable | BE 304/159 | Hammer 2 REFUEL STPT 12 @ 1504 0.3 NM |
| target | TGT 13 | 7 | 454277.2 | 1471071.0 | 448.4 | 138.5 | usable | BE 268/105 | Hammer 2 LAND STPT 13 @ 1504 0.3 NM |
| ppt | ORO |  | 5139024.0 | 2108082.0 | 642.5 | 1566.4 | out of theater; excluded from map crops |  |  |
| ppt | 10 |  | 477053.2 | 2107703.2 | 642.4 | 145.4 | usable | BE 304/0 | Hammer 2 SEAD STPT 7 @ 1444 9.6 NM |
| ppt | 15 |  | 490476.2 | 2021947.5 | 616.3 | 149.5 | usable | BE 280/15 |  |
| ppt | 10 |  | 486715.5 | 2165976.5 | 660.2 | 148.4 | usable | BE 079/9 | Hammer 2 SEAD STPT 7 @ 1444 0.2 NM |
| ppt | SA5 |  | 532862.0 | 2212552.2 | 674.4 | 162.4 | usable | BE 061/19 | Devil 6 CAP STPT 5 @ 1446 4.7 NM |
| ppt | CRO |  | 390471.2 | 2038726.6 | 621.4 | 119.0 | usable | BE 220/18 |  |
| ppt | BLU |  | 450066.0 | 2076887.6 | 633.0 | 137.2 | usable | BE 232/7 |  |
| ppt | SA6 |  | 483899.2 | 2031964.2 | 619.3 | 147.5 | usable | BE 276/13 |  |
| ppt | 10 |  | 598985.8 | 2254517.0 | 687.2 | 182.6 | usable | BE 050/31 |  |
| ppt | TIG |  | 322750.0 | 1871245.2 | 570.4 | 98.4 | usable | BE 237/47 |  |
| ppt | WWO |  | 394908.8 | 2180357.8 | 664.6 | 120.4 | usable | BE 139/18 | Devil 5 CAP STPT 4 @ 1442 6.2 NM |
| ppt | BAN |  | 5774994.5 | 2166003.8 | 660.2 | 1760.2 | out of theater; excluded from map crops |  |  |
| ppt | BAN |  | 463551.8 | 2168588.2 | 661.0 | 141.3 | usable | BE 102/10 | Hammer 2 SEAD STPT 7 @ 1444 3.7 NM |

### Strategic Air Defense Coordinates
Air-defense rows use saved campaign battalion/unit grid coordinates and exclude embedded short-range point/base defenses. They are enemy strategic sites with active tracking radars.
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Bullseye | Nearest package/INI anchor | Dist NM | Air range | Low-alt range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1783 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 660.0 | 148.0 | BE 080/9 | Hammer 2 SEAD STPT 7 @ 1444 | 0.0 | 85 | 71 |
| 1787 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 660.0 | 148.0 | BE 080/9 | Hammer 2 SEAD STPT 7 @ 1444 | 0.0 | 18 | 15 |
| 1759 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 674.0 | 162.0 | BE 061/19 | INI SA5 | 0.3 | 99 | 83 |
| 1779 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 642.0 | 145.0 | BE 270/1 | INI 10 | 0.3 | 85 | 71 |
| 1767 | USSR | Air Defense | SA-11 (9K37M1); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-11 (9K37M1) (slot 0, 3/3) | 677.0 | 179.0 | BE 045/26 | INI SA5 | 9.1 | 22 | 19 |
| 1773 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 687.0 | 182.0 | BE 050/31 | INI SA5 | 12.6 | 85 | 71 |
| 1785 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 619.0 | 147.0 | BE 275/13 | INI TGT 6 | 12.6 | 18 | 15 |
| 1761 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 690.0 | 204.0 | BE 039/41 | INI SA5 | 24.0 | 99 | 83 |
| 1774 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 690.0 | 204.0 | BE 039/41 | INI SA5 | 24.0 | 85 | 71 |
| 1763 | USSR | Air Defense | SA-2 (S-75); Fan Song E; ZU-23; ZIL-131; KrAz T 255B | Fan Song E (slot 3, 1/1) | 643.0 | 229.0 | BE 000/45 | INI SA5 | 39.8 | 30 | 25 |
| 1769 | USSR | Air Defense | SA-17 (9K37M2); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-17 (9K37M2) (slot 0, 3/3) | 646.0 | 234.0 | BE 002/48 | INI SA5 | 41.6 | 30 | 25 |
| 1781 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | BE 342/45 | INI TGT 6 | 45.0 | 85 | 71 |
| 2235 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | BE 342/45 | INI TGT 6 | 45.0 | 85 | 71 |
| 1765 | USSR | Air Defense | SA-3 (S-125); Low Blow; ZPU-2; KrAz T 255B; Flat Face | Low Blow (slot 2, 1/1) | 686.0 | 248.0 | BE 023/60 | INI SA5 | 46.6 | 17 | 15 |

### Active Enemy Air Contact Coordinates
Rows use current campaign-time positions. Enemy callsigns and package IDs are omitted.
| Sector | Aircraft | Capability | Count | Grid X | Grid Y | Bullseye | Alt ft | Nearest package/INI anchor | Dist NM | Basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E | MiG-27 | air contact | 2 | 639.0 | 145.0 | BE 270/2 | 9843 | Hammer 2 PUSH STPT 3 @ 1431 | 0.6 | airborne now; next leg vectors inside 30 NM by 1412 |
| NE | MiG-27 | air contact | 2 | 650.0 | 162.0 | BE 022/10 | 12080 | INI TGT 6 | 1.9 | airborne now; next leg vectors inside 30 NM by 1403 |
| N | MiG-29S | fighter-capable | 2 | 637.0 | 159.0 | BE 337/8 | 21000 | INI TGT 6 | 7.8 | airborne now within 30 NM of target-area anchor |
| NW | Mi-28 | air contact | 2 | 655.0 | 170.0 | BE 026/15 | 6000 | Devil 5 CAP STPT 5 @ 1445 | 9.2 | airborne now within 30 NM of target-area anchor |
| W | Mi-8 | air contact | 2 | 623.0 | 153.0 | BE 292/12 | 15000 | INI TGT 6 | 11.2 | airborne now within 30 NM of target-area anchor |
| W | Ka-52K | air contact | 1 | 615.0 | 137.0 | BE 254/16 | 4902 | INI TGT 6 | 15.4 | airborne now within 30 NM of target-area anchor |
| W | Mi-8 | air contact | 2 | 613.0 | 147.0 | BE 274/16 | 4869 | INI TGT 6 | 15.8 | airborne now within 30 NM of target-area anchor |
| NE | MiG-27 | air contact | 2 | 554.0 | 203.0 | BE 303/57 | 15000 | Hammer 2 PUSH STPT 3 @ 1431 | 19.9 | airborne now within 30 NM of target-area anchor |
| NW | MiG-27 | air contact | 2 | 642.0 | 186.0 | BE 359/22 | 16000 | Devil 5 CAP STPT 5 @ 1445 | 20.2 | airborne now within 30 NM of target-area anchor |
| NW | Mi-8 | air contact | 2 | 623.0 | 180.0 | BE 330/22 | 5394 | INI TGT 6 | 21.3 | airborne now within 30 NM of target-area anchor |
| NE | Su-39 | air contact | 2 | 743.0 | 208.0 | BE 058/64 | 18000 | INI SA5 | 22.0 | airborne now; next leg vectors inside 30 NM by 1412 |
| N | Mi-8 | air contact | 2 | 627.0 | 188.0 | BE 340/25 | 4489 | INI TGT 6 | 24.4 | airborne now within 30 NM of target-area anchor |
| NW | MiG-31 | air contact | 2 | 620.0 | 185.0 | BE 330/25 | 21000 | INI TGT 6 | 24.5 | airborne now within 30 NM of target-area anchor |
| NW | Su-39 | air contact | 2 | 588.0 | 222.0 | BE 324/51 | 15000 | INI SA5 | 26.4 | airborne now; next leg vectors inside 30 NM by 1408 |
| NW | Ka-52K | air contact | 2 | 641.0 | 202.0 | BE 358/31 | 4552 | INI SA5 | 28.0 | airborne now within 30 NM of target-area anchor |

### Resolved Location Objects
| Kind | ID | Name | Source X | Source Y | Source Z |
| --- | --- | --- | --- | --- | --- |
| objective | 995 | Gunsan AB (RKJK) | 736355.5 | 1418591.3 | 0.0 |
| objective | 997 | Cheongju Intl Airport (RKTU) | 1029703.8 | 1677316.2 | 0.0 |

## Map Products
- Full-route chart map: `package_7040_route_threat_map_skyvector.png`
- Tactical target-area chart: `package_7040_target_area_zoom_skyvector.png`
- Objective-area close-up chart: `package_7040_objective_area_zoom_skyvector.png`
- Weather review chart: `package_7040_weather_map_skyvector.png`
- Close-up map note: objective-area charts preserve CAP anchors Wolf CAP / north threat intercept (Wolf), Wolf CAP / north threat intercept (Wolf) alongside the target and INI route geometry.

![PKG 7040 objective-area zoom](package_7040_objective_area_zoom_skyvector.png)

## Review Items
- Confirm package inclusion and tasking against the mission commander's intent.
- Validate aircraft/loadout/laser/TACAN values against the BMS UI before publishing a live mission brief.
- Validate inferred HHMM times against the BMS UI or human mission card before treating them as authoritative.
