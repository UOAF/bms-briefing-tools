# BMS Briefing Workup: 739pre

Internal transitional artifact for briefing iteration. Keep provenance, gaps, and correlation notes here; `generated_briefing.md` is the player-facing mission brief.

## Timing Source
- HHMM values use clock base `1400` and campaign time `12728096`.

## Reference Deck Package Check
- Mentioned in deck: none
- Present in local CAM: none
- Missing from local CAM: none

## Operating Area Inputs
- PPT labels and rings: 0 10 (50.0 NM); 1 10 (50.0 NM); 2 15 (6.5 NM); 3 10 (50.0 NM); 4 SA5 (54.0 NM); 5 CRO; 6 JEW; 7 SA6 (12.5 NM); 8 10 (50.0 NM); 9 TIG
- INI grid transform: `grid_x = (ini_y / 3280.84); grid_y = (ini_x / 3280.84)`

## Meteorology Workup
- Weather data unavailable: No FMAP sidecar was found..

## Bullseye
- Bullseye: grid 643.0 / 145.0

## Package Correlation Workup
### PKG 3494 - BARCAP (2 flights, selected by explicit request)
- Targets: No named tactical target listed
- Enemy situation: 16 enemy non-air unit records within 35 NM of package/INI tactical anchors; dominant nearby classes: Air Defense x7, Supply x6, Engineer x3. 11 strategic air-defense records with active tracking radars within 60 NM; strategic AD classes: Air Defense x11. 0 strategic ADA candidates filtered for inactive/missing tracking radars. 0 enemy squadron bases within 100 NM hosting 0 active squadrons. 7 active enemy air contact(s) at campaign time within or vectoring into 30 NM of the target area.
- INI plan correlation: INI planning marks did not correlate closely to this package route.
- Commander context: F-15C east-flank fighter screen. Intercept Flankers/Fulcrums from the east and shipborne Flankers coming off the ocean before they can pressure the SEAD package.
- Fallback logic: If the fighter picture becomes saturated, drag east-flank threats west toward Tiger, the friendly SAG/Burke air-defense umbrella, and the package BARCAPs.

## Comm Data Workup
- Link 16 rows available: 34.
- Correlation basis: Matched by CAM camp_id/name_id/VU num when possible..
- UHF/VHF preset channel decoding is not yet available from the campaign bundle.

## Friendly Surface Fallback
- Anchor: Tiger - Friendly SAG / Burke umbrella (`TIG`)
- Coordinates: grid 570.4 / 98.4
- Description: Tiger marks the friendly surface action group with an Arleigh Burke and two escorts near the common STPT 3 area. Use as a fallback/drag option if overwhelmed by enemy fighters.
- Use: Do not brief as a primary threat; brief as a friendly fallback air-defense anchor.

## Other Package Factors
- No additional friendly packages are expected to affect the target area.

## Enemy Air Threat Estimate
This section avoids enemy ATO/package tasking. It is based on active enemy squadron bases within the threat radius, known aircraft types, and bearing from those bases to the package/INI target-area anchors. Treat it as likely fighter threat axes, not a prediction of specific launches, callsigns, package IDs, or timings.

- No active enemy fighter-capable airbases were identified within the current airbase threat radius.

### Active Air Contacts At Campaign Time
These are current-position contacts only. Callsigns and enemy package/tasking IDs are intentionally omitted; the brief only exposes aircraft type, rough sector, range, and the observed reason they matter.

| Sector from AO | Aircraft | Capability | Count | Nearest area | Range | Basis |
| --- | --- | --- | --- | --- | --- | --- |
| W | Su-33 | air contact | 2 | Hog 5 CAP STPT 4 @ 1441 | 7.9 NM | airborne now; next leg vectors inside 30 NM by 1406 |
| N | MiG-31 | air contact | 2 | Hog 5 CAP STPT 4 @ 1441 | 21.3 NM | airborne now within 30 NM of target-area anchor |
| N | Ka-52K | air contact | 1 | Hog 5 CAP STPT 4 @ 1441 | 21.6 NM | airborne now within 30 NM of target-area anchor |
| N | Su-35S | air contact | 2 | Hog 5 CAP STPT 4 @ 1441 | 22.2 NM | airborne now; next leg vectors inside 30 NM by 1401 |
| N | MiG-29S | fighter-capable | 2 | Hog 5 CAP STPT 4 @ 1441 | 26.1 NM | airborne now within 30 NM of target-area anchor |
| N | MiG-29S | fighter-capable | 2 | Hog 5 CAP STPT 4 @ 1441 | 26.1 NM | airborne now within 30 NM of target-area anchor |
| NW | Mi-8 | air contact | 2 | Hog 5 CAP STPT 4 @ 1441 | 29.4 NM | airborne now within 30 NM of target-area anchor |

## Comm Ladder
| Element | Role | TACAN | Laser | Link 16 STN | F2F | Mission | EW | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hog 5 | BARCAP | not assigned | 1688 | 5737 | 1 | 1 | -1 | East flank intercept: east of Crown - Push east, commit on Flanker/Fulcrum groups threatening the SEAD package, and sanitize the ocean-side axis. |
| Ramrod 3 | BARCAP | not assigned | 1688 | 1710 | 1 | 1 | -1 | East flank intercept: east of Crown - Support Hog 5 and engage shipborne Flankers or other fighters flowing toward the SA-10 prosecution area. |
| Dragnet 1 | AWACS | not assigned | n/a | 1153 | 1 | 1 | -1 | ELINT STPT 4 1357 grid 462/255; ELINT STPT 5 1401 grid 504/281 |

## Enemy Situation And Air Defense Estimate
Threats below are focused on the package route, CAP/SAD areas, and named data-cartridge anchors. Strategic air-defense rows only include enemy Air Defense class systems with active tracking radars.
- Enemy teams considered: DPRK, Japan, PRC, USSR
- Summary: 16 enemy ground/naval units within 35 NM of package/INI tactical anchors; dominant nearby classes: Air Defense x7, Supply x6, Engineer x3. 11 strategic air-defense sites with active tracking radars within 60 NM; strategic AD classes: Air Defense x11. 0 enemy squadron base areas within 100 NM hosting 0 active squadrons. 7 active enemy air contact(s) at campaign time within or vectoring into 30 NM of the target area.
- Airbase threat: Closest squadron bases: none.

### Strategic Air Defense Units Near Package Route
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Nearest anchor | Dist NM | Air range | Low-alt range | Strength air/low |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1753 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 656.0 | 131.0 | Hog 5 CAP STPT 4 @ 1441 | 14.2 | 85 | 71 | 150/150 |
| 1757 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 656.0 | 131.0 | Hog 5 CAP STPT 4 @ 1441 | 14.2 | 85 | 71 | 150/150 |
| 1779 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 642.0 | 145.0 | Hog 5 CAP STPT 4 @ 1441 | 21.3 | 85 | 71 | 150/150 |
| 1783 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 660.0 | 148.0 | Hog 5 CAP STPT 4 @ 1441 | 23.6 | 85 | 71 | 150/150 |
| 1787 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 660.0 | 148.0 | Hog 5 CAP STPT 4 @ 1441 | 23.6 | 18 | 15 | 60/60 |
| 1785 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 619.0 | 147.0 | Hog 5 CAP STPT 4 @ 1441 | 27.1 | 18 | 15 | 60/60 |
| 1759 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 674.0 | 160.0 | Hog 5 CAP STPT 4 @ 1441 | 32.4 | 99 | 83 | 50/50 |
| 1767 | USSR | Air Defense | SA-11 (9K37M1); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-11 (9K37M1) (slot 0, 3/3) | 677.0 | 179.0 | Hog 5 CAP STPT 4 @ 1441 | 42.4 | 22 | 19 | 100/100 |
| 1773 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 687.0 | 182.0 | Hog 5 CAP STPT 4 @ 1441 | 46.1 | 85 | 71 | 150/150 |
| 1761 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 690.0 | 204.0 | Hog 5 CAP STPT 4 @ 1441 | 57.6 | 99 | 83 | 50/50 |
| 1774 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 690.0 | 204.0 | Hog 5 CAP STPT 4 @ 1441 | 57.6 | 85 | 71 | 150/150 |

### Nearby Enemy Ground/Naval Units
| ID | Team | Class | Category | Equipment | Grid X | Grid Y | Nearest anchor | Dist NM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1753 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 656.0 | 131.0 | Hog 5 CAP STPT 4 @ 1441 | 14.2 |
| 1757 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 656.0 | 131.0 | Hog 5 CAP STPT 4 @ 1441 | 14.2 |
| 1779 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 642.0 | 145.0 | Hog 5 CAP STPT 4 @ 1441 | 21.3 |
| 1783 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 660.0 | 148.0 | Hog 5 CAP STPT 4 @ 1441 | 23.6 |
| 1787 | USSR | Air Defense | air defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | 660.0 | 148.0 | Hog 5 CAP STPT 4 @ 1441 | 23.6 |
| 1785 | USSR | Air Defense | air defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | 619.0 | 147.0 | Hog 5 CAP STPT 4 @ 1441 | 27.1 |
| 1421 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 669.0 | 154.0 | Hog 5 CAP STPT 4 @ 1441 | 28.3 |
| 1423 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 669.0 | 154.0 | Hog 5 CAP STPT 4 @ 1441 | 28.3 |
| 2351 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 669.0 | 154.0 | Hog 5 CAP STPT 4 @ 1441 | 28.3 |
| 1417 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 663.0 | 157.0 | Hog 5 CAP STPT 4 @ 1441 | 28.7 |
| 1419 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 663.0 | 157.0 | Hog 5 CAP STPT 4 @ 1441 | 28.7 |
| 2347 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 663.0 | 157.0 | Hog 5 CAP STPT 4 @ 1441 | 28.7 |
| 1759 | USSR | Air Defense | air defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | 674.0 | 160.0 | Hog 5 CAP STPT 4 @ 1441 | 32.4 |
| 1409 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 676.0 | 160.0 | Hog 5 CAP STPT 4 @ 1441 | 32.8 |
| 1411 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 676.0 | 160.0 | Hog 5 CAP STPT 4 @ 1441 | 32.8 |
| 2339 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 676.0 | 160.0 | Hog 5 CAP STPT 4 @ 1441 | 32.8 |

## Coordinate Appendix
Location data is separated here so the main brief stays readable.
- Bullseye: grid 643.0 / 145.0

### PKG 3494 Flight Steerpoints
| C/S | STPT | Action | Arrive | Grid X | Grid Y | Bullseye | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hog 5 | 0 | TAKEOFF | 1419 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Hog 5 | 3 | CAP | 1438 | 619.0 | 88.0 | BE 203/33 | 2100.0 |  |
| Hog 5 | 4 | CAP | 1441 | 648.0 | 106.0 | BE 173/21 | 2100.0 |  |
| Hog 5 | 6 | LAND | 1526 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Hog 5 | 7 | LAND | 1526 | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Ramrod 3 | 0 | TAKEOFF | 1419 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Ramrod 3 | 3 | CAP | 1440 | 635.0 | 77.0 | BE 187/37 | 2100.0 |  |
| Ramrod 3 | 4 | CAP | 1442 | 659.0 | 98.0 | BE 161/27 | 2100.0 |  |
| Ramrod 3 | 6 | LAND | 1528 | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Ramrod 3 | 7 | LAND | 1528 | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |

### Linked Support Flight Coordinates
| Role | C/S | STPT | Action | Arrive | Grid X | Grid Y | Bullseye | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWACS | Dragnet 1 | 0 | TAKEOFF | 1332 | 449.0 | 407.0 | BE 323/176 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |
| AWACS | Dragnet 1 | 2 | TIMING | 1346 | 443.0 | 309.0 | BE 309/140 | 2800.0 |  |
| AWACS | Dragnet 1 | 3 | PUSH | 1353 | 458.0 | 298.0 | BE 310/130 | 2800.0 |  |
| AWACS | Dragnet 1 | 4 | ELINT | 1357 | 462.0 | 255.0 | BE 301/114 | 2600.0 |  |
| AWACS | Dragnet 1 | 5 | ELINT | 1401 | 504.0 | 281.0 | BE 314/105 | 2600.0 |  |
| AWACS | Dragnet 1 | 6 | SPLIT | 1905 | 485.0 | 326.0 | BE 319/130 | 2700.0 |  |
| AWACS | Dragnet 1 | 7 | LAND | 1911 | 449.0 | 407.0 | BE 323/176 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |
| AWACS | Dragnet 1 | 8 | LAND | 1040 | 477.0 | 395.0 | BE 326/162 | 0.0 | Seoul AB (RKSM) (objective 1484) |

### INI Planning Steerpoints
| Kind | Label | Code | INI X ft | INI Y ft | Grid X | Grid Y | Bullseye | Nearest package route point |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target | TGT 0 | 1 | 454277.2 | 1471071.0 | 448.4 | 138.5 | BE 268/105 | Hog 5 LAND STPT 7 @ 1526 0.3 NM |
| target | TGT 1 | 0 | 359157.8 | 1589150.2 | 484.4 | 109.5 | BE 257/88 |  |
| target | TGT 2 | 8 | 339477.9 | 1677709.8 | 511.4 | 103.5 | BE 252/75 |  |
| target | TGT 3 | 2 | 326358.0 | 1871228.6 | 570.4 | 99.5 | BE 238/46 |  |
| target | TGT 4 | 0 | 355877.8 | 1926988.2 | 587.3 | 108.5 | BE 237/36 |  |
| target | TGT 5 | 0 | 378837.7 | 1992587.9 | 607.3 | 115.5 | BE 230/25 |  |
| target | TGT 6 | 19 | 391957.6 | 2038507.6 | 621.3 | 119.5 | BE 220/18 |  |
| target | TGT 7 | 3 | 437877.3 | 1740029.4 | 530.4 | 133.5 | BE 264/61 |  |
| target | TGT 8 | 0 | 428037.4 | 1651469.9 | 503.4 | 130.5 | BE 264/76 |  |
| target | TGT 9 | 7 | 454277.2 | 1471071.0 | 448.4 | 138.5 | BE 268/105 | Hog 5 LAND STPT 7 @ 1526 0.3 NM |
| target | TGT 10 | 7 | 408357.5 | 1346431.8 | 410.4 | 124.5 | BE 265/126 |  |
| ppt | 10 |  | 430439.5 | 2152718.8 | 656.1 | 131.2 | BE 136/10 |  |
| ppt | 10 |  | 477053.2 | 2107703.2 | 642.4 | 145.4 | BE 304/0 |  |
| ppt | 15 |  | 490476.2 | 2021947.5 | 616.3 | 149.5 | BE 280/15 |  |
| ppt | 10 |  | 486715.5 | 2165976.5 | 660.2 | 148.4 | BE 079/9 |  |
| ppt | SA5 |  | 526853.8 | 2211818.5 | 674.2 | 160.6 | BE 063/19 |  |
| ppt | CRO |  | 390471.2 | 2038726.6 | 621.4 | 119.0 | BE 220/18 |  |
| ppt | JEW |  | 438672.2 | 2013361.9 | 613.7 | 133.7 | BE 249/17 |  |
| ppt | SA6 |  | 483899.2 | 2031964.2 | 619.3 | 147.5 | BE 276/13 |  |
| ppt | 10 |  | 598985.8 | 2254517.0 | 687.2 | 182.6 | BE 050/31 |  |
| ppt | TIG |  | 322750.0 | 1871245.2 | 570.4 | 98.4 | BE 237/47 |  |

### Strategic Air Defense Coordinates
Air-defense rows use saved campaign battalion/unit grid coordinates and exclude embedded short-range point/base defenses. They are enemy strategic sites with active tracking radars.
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Bullseye | Nearest package/INI anchor | Dist NM | Air range | Low-alt range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1753 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 656.0 | 131.0 | BE 137/10 | Hog 5 CAP STPT 4 @ 1441 | 14.2 | 85 | 71 |
| 1757 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 656.0 | 131.0 | BE 137/10 | Hog 5 CAP STPT 4 @ 1441 | 14.2 | 85 | 71 |
| 1779 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 642.0 | 145.0 | BE 270/1 | Hog 5 CAP STPT 4 @ 1441 | 21.3 | 85 | 71 |
| 1783 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 660.0 | 148.0 | BE 080/9 | Hog 5 CAP STPT 4 @ 1441 | 23.6 | 85 | 71 |
| 1787 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 660.0 | 148.0 | BE 080/9 | Hog 5 CAP STPT 4 @ 1441 | 23.6 | 18 | 15 |
| 1785 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 619.0 | 147.0 | BE 275/13 | Hog 5 CAP STPT 4 @ 1441 | 27.1 | 18 | 15 |
| 1759 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 674.0 | 160.0 | BE 064/19 | Hog 5 CAP STPT 4 @ 1441 | 32.4 | 99 | 83 |
| 1767 | USSR | Air Defense | SA-11 (9K37M1); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-11 (9K37M1) (slot 0, 3/3) | 677.0 | 179.0 | BE 045/26 | Hog 5 CAP STPT 4 @ 1441 | 42.4 | 22 | 19 |
| 1773 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 687.0 | 182.0 | BE 050/31 | Hog 5 CAP STPT 4 @ 1441 | 46.1 | 85 | 71 |
| 1761 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 690.0 | 204.0 | BE 039/41 | Hog 5 CAP STPT 4 @ 1441 | 57.6 | 99 | 83 |
| 1774 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 690.0 | 204.0 | BE 039/41 | Hog 5 CAP STPT 4 @ 1441 | 57.6 | 85 | 71 |

### Active Enemy Air Contact Coordinates
Rows use current campaign-time positions. Enemy callsigns and package IDs are omitted.
| Sector | Aircraft | Capability | Count | Grid X | Grid Y | Bullseye | Alt ft | Nearest package/INI anchor | Dist NM | Basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W | Su-33 | air contact | 2 | 554.0 | 80.0 | BE 234/60 | 26000 | Hog 5 CAP STPT 4 @ 1441 | 7.9 | airborne now; next leg vectors inside 30 NM by 1406 |
| N | MiG-31 | air contact | 2 | 642.0 | 145.0 | BE 270/1 | 0 | Hog 5 CAP STPT 4 @ 1441 | 21.3 | airborne now within 30 NM of target-area anchor |
| N | Ka-52K | air contact | 1 | 650.0 | 146.0 | BE 082/4 | 7761 | Hog 5 CAP STPT 4 @ 1441 | 21.6 | airborne now within 30 NM of target-area anchor |
| N | Su-35S | air contact | 2 | 658.0 | 164.0 | BE 038/13 | 26000 | Hog 5 CAP STPT 4 @ 1441 | 22.2 | airborne now; next leg vectors inside 30 NM by 1401 |
| N | MiG-29S | fighter-capable | 2 | 653.0 | 154.0 | BE 048/7 | 14300 | Hog 5 CAP STPT 4 @ 1441 | 26.1 | airborne now within 30 NM of target-area anchor |
| N | MiG-29S | fighter-capable | 2 | 653.0 | 154.0 | BE 048/7 | 16300 | Hog 5 CAP STPT 4 @ 1441 | 26.1 | airborne now within 30 NM of target-area anchor |
| NW | Mi-8 | air contact | 2 | 611.0 | 146.0 | BE 272/17 | 4869 | Hog 5 CAP STPT 4 @ 1441 | 29.4 | airborne now within 30 NM of target-area anchor |

### Resolved Location Objects
| Kind | ID | Name | Source X | Source Y | Source Z |
| --- | --- | --- | --- | --- | --- |
| objective | 995 | Gunsan AB (RKJK) | 736355.5 | 1418591.3 | 0.0 |
| objective | 997 | Cheongju Intl Airport (RKTU) | 1029703.8 | 1677316.2 | 0.0 |

## Map Products
- Full-route chart map: `package_3494_route_threat_map_skyvector.png`
- Tactical target-area chart: `package_3494_target_area_zoom_skyvector.png`
- Objective-area close-up chart: `package_3494_objective_area_zoom_skyvector.png`
- Weather review chart: `package_3494_weather_map_skyvector.png`

![PKG 3494 objective-area zoom](package_3494_objective_area_zoom_skyvector.png)

## Review Items
- Confirm package inclusion and tasking against the mission commander's intent.
- Validate aircraft/loadout/laser/TACAN values against the BMS UI before publishing a live mission brief.
- Validate inferred HHMM times against the BMS UI or human mission card before treating them as authoritative.
