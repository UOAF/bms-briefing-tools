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

## Package Correlation Workup
### PKG 3465 - SEAD (5 flights, selected by explicit request)
- Targets: No named tactical target listed
- Enemy situation: 20 enemy non-air unit records within 35 NM of package/INI tactical anchors; dominant nearby classes: Supply x8, Air Defense x7, Engineer x4, Motor Rifle x1. 15 strategic air-defense records with active tracking radars within 60 NM; strategic AD classes: Air Defense x15. 0 strategic ADA candidates filtered for inactive/missing tracking radars. 0 enemy squadron bases within 100 NM hosting 0 active squadrons. 11 active enemy air contact(s) at campaign time within or vectoring into 30 NM of the target area.
- INI plan correlation: TIMING is bracketed by TGT 2; PUSH is marked by TGT 3, TIG; SPLIT/recovery is nearest TGT 7, TGT 8
- Commander context: Primary SEAD/DEAD package. Cyborg 1 attacks the newly identified SA-6 north of Joule and SA-10 West; Jackal 2 attacks SA-10 East and SA-10 South while Cobra 2, Cajun 1, and Cobra 4 protect the package.
- Fallback logic: If either SEAD flight becomes pressured, drag enemy fighters toward Tiger, the friendly SAG/Burke air-defense umbrella near common STPT 3. Cyborg 1 should prioritize survival and confirmation on the SA-6/SA-10 West targets; Jackal 2 stays focused on SA-10 East/South unless retasked.

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
| E | Ka-52K | air contact | 1 | INI JEW | 0.1 NM | airborne now; next leg vectors inside 30 NM by 1411 |
| SW | Su-33 | air contact | 2 | Cajun 1 CAP STPT 4 @ 1439 | 2.5 NM | airborne now; next leg vectors inside 30 NM by 1406 |
| SW | Mi-8 | air contact | 2 | INI 15 | 3.4 NM | airborne now within 30 NM of target-area anchor |
| W | Mi-28 | air contact | 2 | INI 15 | 4.6 NM | airborne now within 30 NM of target-area anchor |
| SW | Su-39 | air contact | 2 | Cyborg 1 PUSH STPT 3 @ 1435 | 5.8 NM | airborne now; next leg vectors inside 30 NM by 1404 |
| E | MiG-31 | air contact | 2 | INI SA6 | 12.3 NM | airborne now within 30 NM of target-area anchor |
| NE | Su-35S | air contact | 2 | INI SA6 | 17.1 NM | airborne now; next leg vectors inside 30 NM by 1401 |
| E | MiG-29S | fighter-capable | 2 | INI SA6 | 18.5 NM | airborne now within 30 NM of target-area anchor |
| E | MiG-29S | fighter-capable | 2 | INI SA6 | 18.5 NM | airborne now within 30 NM of target-area anchor |
| N | MiG-27 | air contact | 2 | Cobra 4 CAP STPT 4 @ 1440 | 27.2 NM | airborne now within 30 NM of target-area anchor |
| NE | Mi-28 | air contact | 2 | INI SA6 | 27.3 NM | airborne now within 30 NM of target-area anchor |

## Comm Ladder
| Element | Role | TACAN | Laser | Link 16 STN | F2F | Mission | EW | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Cyborg 1 | SEAD | not assigned | 1688 | 2343 | 65 | 65 | 1 | SEAD/DEAD SA-6 North of Joule and SA-10 West: Joule - Work from Joule, destroy the SA-6 north of Joule first if it is factor, then prosecute SA-10 West. Confirm positive destruction of each target before egress. |
| Jackal 2 | SEAD | not assigned | 1688 | 1114 | 65 | 65 | 1 | SEAD/DEAD SA-10 East and SA-10 South: Crown - Work from Crown, prosecute SA-10 East and SA-10 South, and confirm positive destruction of both targets before egress. |
| Cobra 2 | BARCAP | not assigned | 1688 | 5572 | 1 | 65 | -1 | Escort Cyborg 1: Cyborg 1 lane - Protect Cyborg 1 during the Joule-side SA-6 and SA-10 West prosecution. |
| Cajun 1 | BARCAP | not assigned | 1688 | 3776 | 1 | 65 | -1 | Escort Jackal 2: Jackal 2 lane - Protect Jackal 2 during the Crown-side SA-10 prosecution. |
| Cobra 4 | BARCAP | not assigned | 1688 | 4107 | 1 | 65 | -1 | Northern flank BARCAP: western/northern flank oriented NNE - Hold the northern flank against fighters arriving from the north-northeast. |
| Dragnet 1 | AWACS | not assigned | n/a | 1153 | 1 | 1 | -1 | ELINT STPT 4 1357 grid 462/255; ELINT STPT 5 1401 grid 504/281 |
| Copper 5 | TANKER | 125Y slot 0 | n/a |  |  |  |  | TANKER STPT 4 1524 grid 435/277; TANKER STPT 5 1533 grid 360/342 |

## Enemy Situation And Air Defense Estimate
Threats below are focused on the package route, CAP/SAD areas, and named data-cartridge anchors. Strategic air-defense rows only include enemy Air Defense class systems with active tracking radars.
- Enemy teams considered: DPRK, Japan, PRC, USSR
- Summary: 20 enemy ground/naval units within 35 NM of package/INI tactical anchors; dominant nearby classes: Supply x8, Air Defense x7, Engineer x4, Motor Rifle x1. 15 strategic air-defense sites with active tracking radars within 60 NM; strategic AD classes: Air Defense x15. 0 enemy squadron base areas within 100 NM hosting 0 active squadrons. 11 active enemy air contact(s) at campaign time within or vectoring into 30 NM of the target area.
- Airbase threat: Closest squadron bases: none.

### Strategic Air Defense Units Near Package Route
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Nearest anchor | Dist NM | Air range | Low-alt range | Strength air/low |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1785 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 619.0 | 147.0 | INI SA6 | 0.3 | 18 | 15 | 60/60 |
| 1779 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 642.0 | 145.0 | INI SA6 | 12.3 | 85 | 71 | 150/150 |
| 1753 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 656.0 | 131.0 | Cobra 2 CAP STPT 4 @ 1438 | 17.5 | 85 | 71 | 150/150 |
| 1757 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 656.0 | 131.0 | Cobra 2 CAP STPT 4 @ 1438 | 17.5 | 85 | 71 | 150/150 |
| 1783 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 660.0 | 148.0 | INI SA6 | 22.0 | 85 | 71 | 150/150 |
| 1787 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 660.0 | 148.0 | INI SA6 | 22.0 | 18 | 15 | 60/60 |
| 1759 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 674.0 | 160.0 | INI SA6 | 30.3 | 99 | 83 | 50/50 |
| 1767 | USSR | Air Defense | SA-11 (9K37M1); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-11 (9K37M1) (slot 0, 3/3) | 677.0 | 179.0 | INI SA6 | 35.5 | 22 | 19 | 100/100 |
| 1781 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | INI 15 | 40.8 | 85 | 71 | 150/150 |
| 2235 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | INI 15 | 40.8 | 85 | 71 | 150/150 |
| 1773 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 687.0 | 182.0 | INI SA6 | 41.0 | 85 | 71 | 150/150 |
| 1763 | USSR | Air Defense | SA-2 (S-75); Fan Song E; ZU-23; ZIL-131; KrAz T 255B | Fan Song E (slot 3, 1/1) | 643.0 | 229.0 | INI 15 | 45.3 | 30 | 25 | 70/70 |
| 1769 | USSR | Air Defense | SA-17 (9K37M2); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-17 (9K37M2) (slot 0, 3/3) | 646.0 | 234.0 | INI 15 | 48.4 | 30 | 25 | 100/100 |
| 1761 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 690.0 | 204.0 | INI SA6 | 48.9 | 99 | 83 | 50/50 |
| 1774 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 690.0 | 204.0 | INI SA6 | 48.9 | 85 | 71 | 150/150 |

### Nearby Enemy Ground/Naval Units
| ID | Team | Class | Category | Equipment | Grid X | Grid Y | Nearest anchor | Dist NM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1785 | USSR | Air Defense | air defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | 619.0 | 147.0 | INI SA6 | 0.3 |
| 2309 | USSR | Motor Rifle | other | BTR-60; T-55; BRDM-2AT; M-1992; ZIL-131 | 614.0 | 167.0 | INI 15 | 9.5 |
| 1779 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 642.0 | 145.0 | INI SA6 | 12.3 |
| 1753 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 656.0 | 131.0 | Cobra 2 CAP STPT 4 @ 1438 | 17.5 |
| 1757 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 656.0 | 131.0 | Cobra 2 CAP STPT 4 @ 1438 | 17.5 |
| 1783 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 660.0 | 148.0 | INI SA6 | 22.0 |
| 1787 | USSR | Air Defense | air defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | 660.0 | 148.0 | INI SA6 | 22.0 |
| 1417 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 663.0 | 157.0 | INI SA6 | 24.1 |
| 1419 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 663.0 | 157.0 | INI SA6 | 24.1 |
| 2347 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 663.0 | 157.0 | INI SA6 | 24.1 |
| 1421 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 669.0 | 154.0 | INI SA6 | 27.1 |
| 1423 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 669.0 | 154.0 | INI SA6 | 27.1 |
| 2351 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 669.0 | 154.0 | INI SA6 | 27.1 |
| 1759 | USSR | Air Defense | air defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | 674.0 | 160.0 | INI SA6 | 30.3 |
| 1409 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 676.0 | 160.0 | INI SA6 | 31.4 |
| 1411 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 676.0 | 160.0 | INI SA6 | 31.4 |

## Coordinate Appendix
Location data is separated here so the main brief stays readable.

### PKG 3465 Flight Steerpoints
| C/S | STPT | Action | Arrive | Grid X | Grid Y | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Cyborg 1 | 0 | TAKEOFF | 1420 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Cyborg 1 | 2 | TIMING | 1427 | 514.0 | 107.0 | 2200.0 |  |
| Cyborg 1 | 3 | PUSH | 1435 | 570.0 | 98.0 | 2200.0 |  |
| Cyborg 1 | 5 | SEAD | 1439 | 613.0 | 133.0 | 2000.0 |  |
| Cyborg 1 | 6 | SPLIT | 1445 | 528.0 | 131.0 | 2100.0 |  |
| Cyborg 1 | 8 | LAND | 1450 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Cyborg 1 | 9 | LAND | 1450 | 410.0 | 124.0 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |
| Jackal 2 | 0 | TAKEOFF | 1421 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Jackal 2 | 2 | TIMING | 1428 | 511.0 | 103.0 | 2200.0 |  |
| Jackal 2 | 3 | PUSH | 1435 | 570.0 | 99.0 | 2200.0 |  |
| Jackal 2 | 6 | SEAD | 1439 | 621.0 | 119.0 | 2000.0 |  |
| Jackal 2 | 7 | SPLIT | 1445 | 530.0 | 133.0 | 2100.0 |  |
| Jackal 2 | 9 | LAND | 1451 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Jackal 2 | 10 | LAND | 1451 | 410.0 | 124.0 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |
| Cobra 2 | 0 | TAKEOFF | 1422 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Cobra 2 | 3 | CAP | 1436 | 596.0 | 118.0 | 2100.0 |  |
| Cobra 2 | 4 | CAP | 1438 | 624.0 | 126.0 | 2100.0 |  |
| Cobra 2 | 6 | LAND | 1520 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Cobra 2 | 7 | LAND | 1520 | 410.0 | 124.0 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |
| Cajun 1 | 0 | TAKEOFF | 1423 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Cajun 1 | 3 | CAP | 1437 | 597.0 | 108.0 | 2100.0 |  |
| Cajun 1 | 4 | CAP | 1439 | 621.0 | 110.0 | 2100.0 |  |
| Cajun 1 | 6 | LAND | 1520 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Cajun 1 | 7 | LAND | 1520 | 410.0 | 124.0 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |
| Cobra 4 | 0 | TAKEOFF | 1424 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Cobra 4 | 3 | CAP | 1438 | 579.0 | 129.0 | 2100.0 |  |
| Cobra 4 | 4 | CAP | 1440 | 596.0 | 141.0 | 2100.0 |  |
| Cobra 4 | 6 | LAND | 1520 | 448.0 | 138.0 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Cobra 4 | 7 | LAND | 1520 | 410.0 | 124.0 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |

### Linked Support Flight Coordinates
| Role | C/S | STPT | Action | Arrive | Grid X | Grid Y | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWACS | Dragnet 1 | 0 | TAKEOFF | 1332 | 449.0 | 407.0 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |
| AWACS | Dragnet 1 | 2 | TIMING | 1346 | 443.0 | 309.0 | 2800.0 |  |
| AWACS | Dragnet 1 | 3 | PUSH | 1353 | 458.0 | 298.0 | 2800.0 |  |
| AWACS | Dragnet 1 | 4 | ELINT | 1357 | 462.0 | 255.0 | 2600.0 |  |
| AWACS | Dragnet 1 | 5 | ELINT | 1401 | 504.0 | 281.0 | 2600.0 |  |
| AWACS | Dragnet 1 | 6 | SPLIT | 1905 | 485.0 | 326.0 | 2700.0 |  |
| AWACS | Dragnet 1 | 7 | LAND | 1911 | 449.0 | 407.0 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |
| AWACS | Dragnet 1 | 8 | LAND | 1040 | 477.0 | 395.0 | 0.0 | Seoul AB (RKSM) (objective 1484) |
| TANKER | Copper 5 | 0 | TAKEOFF | 1510 | 421.0 | 313.0 | 0.0 | Pyeongtaek AAF (RKSG) (objective 924) |
| TANKER | Copper 5 | 2 | TIMING | 1514 | 406.0 | 302.0 | 530.0 |  |
| TANKER | Copper 5 | 4 | TANKER | 1524 | 435.0 | 277.0 | 2400.0 |  |
| TANKER | Copper 5 | 5 | TANKER | 1533 | 360.0 | 342.0 | 2400.0 |  |
| TANKER | Copper 5 | 7 | LAND | 2037 | 421.0 | 313.0 | 0.0 | Pyeongtaek AAF (RKSG) (objective 924) |
| TANKER | Copper 5 | 8 | LAND | 1027 | 470.0 | 341.0 | 0.0 | Gumi Highway Strip (objective 927) |

### INI Planning Steerpoints
| Kind | Label | Code | INI X ft | INI Y ft | Grid X | Grid Y | Nearest package route point |
| --- | --- | --- | --- | --- | --- | --- | --- |
| target | TGT 0 | 1 | 454277.2 | 1471071.0 | 448.4 | 138.5 | Cyborg 1 TAKEOFF STPT 0 @ 1420 0.3 NM |
| target | TGT 1 | 0 | 359157.8 | 1589150.2 | 484.4 | 109.5 |  |
| target | TGT 2 | 8 | 339477.9 | 1677709.8 | 511.4 | 103.5 | Jackal 2 TIMING STPT 2 @ 1428 0.3 NM |
| target | TGT 3 | 2 | 326358.0 | 1871228.6 | 570.4 | 99.5 | Jackal 2 PUSH STPT 3 @ 1435 0.3 NM |
| target | TGT 4 | 0 | 355877.8 | 1926988.2 | 587.3 | 108.5 | Cajun 1 CAP STPT 3 @ 1437 5.2 NM |
| target | TGT 5 | 0 | 378837.7 | 1992587.9 | 607.3 | 115.5 | Cobra 2 CAP STPT 3 @ 1436 6.2 NM |
| target | TGT 6 | 19 | 391957.6 | 2038507.6 | 621.3 | 119.5 | Jackal 2 SEAD STPT 6 @ 1439 0.3 NM |
| target | TGT 7 | 3 | 437877.3 | 1740029.4 | 530.4 | 133.5 | Jackal 2 SPLIT STPT 7 @ 1445 0.3 NM |
| target | TGT 8 | 0 | 428037.4 | 1651469.9 | 503.4 | 130.5 | Cyborg 1 SPLIT STPT 6 @ 1445 13.3 NM |
| target | TGT 9 | 7 | 454277.2 | 1471071.0 | 448.4 | 138.5 | Cyborg 1 TAKEOFF STPT 0 @ 1420 0.3 NM |
| target | TGT 10 | 7 | 408357.5 | 1346431.8 | 410.4 | 124.5 | Cyborg 1 LAND STPT 9 @ 1450 0.3 NM |
| ppt | 10 |  | 430439.5 | 2152718.8 | 656.1 | 131.2 |  |
| ppt | 10 |  | 477053.2 | 2107703.2 | 642.4 | 145.4 |  |
| ppt | 15 |  | 490476.2 | 2021947.5 | 616.3 | 149.5 | Cyborg 1 SEAD STPT 5 @ 1439 9.1 NM |
| ppt | 10 |  | 486715.5 | 2165976.5 | 660.2 | 148.4 |  |
| ppt | SA5 |  | 526853.8 | 2211818.5 | 674.2 | 160.6 |  |
| ppt | CRO |  | 390471.2 | 2038726.6 | 621.4 | 119.0 | Jackal 2 SEAD STPT 6 @ 1439 0.2 NM |
| ppt | JEW |  | 438672.2 | 2013361.9 | 613.7 | 133.7 | Cyborg 1 SEAD STPT 5 @ 1439 0.5 NM |
| ppt | SA6 |  | 483899.2 | 2031964.2 | 619.3 | 147.5 | Cyborg 1 SEAD STPT 5 @ 1439 8.5 NM |
| ppt | 10 |  | 598985.8 | 2254517.0 | 687.2 | 182.6 |  |
| ppt | TIG |  | 322750.0 | 1871245.2 | 570.4 | 98.4 | Cyborg 1 PUSH STPT 3 @ 1435 0.3 NM |

### Strategic Air Defense Coordinates
Air-defense rows use saved campaign battalion/unit grid coordinates and exclude embedded short-range point/base defenses. They are enemy strategic sites with active tracking radars.
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Nearest package/INI anchor | Dist NM | Air range | Low-alt range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1785 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 619.0 | 147.0 | INI SA6 | 0.3 | 18 | 15 |
| 1779 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 642.0 | 145.0 | INI SA6 | 12.3 | 85 | 71 |
| 1753 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 656.0 | 131.0 | Cobra 2 CAP STPT 4 @ 1438 | 17.5 | 85 | 71 |
| 1757 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 656.0 | 131.0 | Cobra 2 CAP STPT 4 @ 1438 | 17.5 | 85 | 71 |
| 1783 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 660.0 | 148.0 | INI SA6 | 22.0 | 85 | 71 |
| 1787 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 660.0 | 148.0 | INI SA6 | 22.0 | 18 | 15 |
| 1759 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 674.0 | 160.0 | INI SA6 | 30.3 | 99 | 83 |
| 1767 | USSR | Air Defense | SA-11 (9K37M1); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-11 (9K37M1) (slot 0, 3/3) | 677.0 | 179.0 | INI SA6 | 35.5 | 22 | 19 |
| 1781 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | INI 15 | 40.8 | 85 | 71 |
| 2235 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | INI 15 | 40.8 | 85 | 71 |
| 1773 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 687.0 | 182.0 | INI SA6 | 41.0 | 85 | 71 |
| 1763 | USSR | Air Defense | SA-2 (S-75); Fan Song E; ZU-23; ZIL-131; KrAz T 255B | Fan Song E (slot 3, 1/1) | 643.0 | 229.0 | INI 15 | 45.3 | 30 | 25 |
| 1769 | USSR | Air Defense | SA-17 (9K37M2); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-17 (9K37M2) (slot 0, 3/3) | 646.0 | 234.0 | INI 15 | 48.4 | 30 | 25 |
| 1761 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 690.0 | 204.0 | INI SA6 | 48.9 | 99 | 83 |
| 1774 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 690.0 | 204.0 | INI SA6 | 48.9 | 85 | 71 |

### Active Enemy Air Contact Coordinates
Rows use current campaign-time positions. Enemy callsigns and package IDs are omitted.
| Sector | Aircraft | Capability | Count | Grid X | Grid Y | Alt ft | Nearest package/INI anchor | Dist NM | Basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E | Ka-52K | air contact | 1 | 650.0 | 146.0 | 7761 | INI JEW | 0.1 | airborne now; next leg vectors inside 30 NM by 1411 |
| SW | Su-33 | air contact | 2 | 554.0 | 80.0 | 26000 | Cajun 1 CAP STPT 4 @ 1439 | 2.5 | airborne now; next leg vectors inside 30 NM by 1406 |
| SW | Mi-8 | air contact | 2 | 611.0 | 146.0 | 4869 | INI 15 | 3.4 | airborne now within 30 NM of target-area anchor |
| W | Mi-28 | air contact | 2 | 608.0 | 148.0 | 6000 | INI 15 | 4.6 | airborne now within 30 NM of target-area anchor |
| SW | Su-39 | air contact | 2 | 529.0 | 71.0 | 16000 | Cyborg 1 PUSH STPT 3 @ 1435 | 5.8 | airborne now; next leg vectors inside 30 NM by 1404 |
| E | MiG-31 | air contact | 2 | 642.0 | 145.0 | 0 | INI SA6 | 12.3 | airborne now within 30 NM of target-area anchor |
| NE | Su-35S | air contact | 2 | 658.0 | 164.0 | 26000 | INI SA6 | 17.1 | airborne now; next leg vectors inside 30 NM by 1401 |
| E | MiG-29S | fighter-capable | 2 | 653.0 | 154.0 | 14300 | INI SA6 | 18.5 | airborne now within 30 NM of target-area anchor |
| E | MiG-29S | fighter-capable | 2 | 653.0 | 154.0 | 16300 | INI SA6 | 18.5 | airborne now within 30 NM of target-area anchor |
| N | MiG-27 | air contact | 2 | 578.0 | 188.0 | 15000 | Cobra 4 CAP STPT 4 @ 1440 | 27.2 | airborne now within 30 NM of target-area anchor |
| NE | Mi-28 | air contact | 2 | 666.0 | 167.0 | 6000 | INI SA6 | 27.3 | airborne now within 30 NM of target-area anchor |

### Resolved Location Objects
| Kind | ID | Name | Source X | Source Y | Source Z |
| --- | --- | --- | --- | --- | --- |
| objective | 997 | Cheongju Intl Airport (RKTU) | 1029703.8 | 1677316.2 | 0.0 |
| objective | 3299 | Muan Intl Airport (RKJB) | 408114.8 | 1346431.8 | 0.0 |

## Map Products
- Full-route chart map: `package_3465_route_threat_map_skyvector.png`
- Tactical target-area chart: `package_3465_target_area_zoom_skyvector.png`
- Objective-area close-up chart: `package_3465_objective_area_zoom_skyvector.png`
- Weather review chart: `package_3465_weather_map_skyvector.png`

![PKG 3465 objective-area zoom](package_3465_objective_area_zoom_skyvector.png)

## Review Items
- Confirm package inclusion and tasking against the mission commander's intent.
- Validate aircraft/loadout/laser/TACAN values against the BMS UI before publishing a live mission brief.
- Validate inferred HHMM times against the BMS UI or human mission card before treating them as authoritative.
