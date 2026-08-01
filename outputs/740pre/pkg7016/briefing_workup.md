# BMS Briefing Workup: 740pre

Internal transitional artifact for briefing iteration. Keep provenance, gaps, and correlation notes here; `generated_briefing.md` is the player-facing mission brief.

## Timing Source
- Mission execution HHMM values are displayed as Zulu after converting local clock base `1429` with UTC+09:00; campaign time `19745032`.
- Clock source: .cmp current_time modulo day via pyopencam.
- Weather tables intentionally keep local time for daylight and meteorology interpretation.

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
| Takeoff | 1449 | Day | Sunny CLR | 38,000 ft | 34,000 ft | 31.1 | 59.9 | 336/4 kt | 448.0 | 138.0 |
| Target Area | 1507 | Day | Sunny CLR | 38,000 ft | 34,000 ft | 27.4 | 59.9 | 315/5 kt | 540.8 | 153.6 |
| Landing | 1524 | Day | Sunny CLR | 38,000 ft | 34,000 ft | 31.1 | 59.9 | 336/4 kt | 448.0 | 138.0 |

## Bullseye
- Bullseye: grid 643.0 / 145.0
- Named references: 10 BE 304/0; TIG BE 237/47; BLU BE 232/7; CRO BE 220/18; BAN BE 102/10; SA6 BE 276/13

## Package Correlation Workup
### PKG 7016 - OCA STRIKE (5 flights, selected by explicit request)
- Targets: Unresolved target 2035
- Enemy situation: 22 enemy non-air unit records within 35 NM of package/INI tactical anchors; dominant nearby classes: Air Defense x9, Supply x8, Engineer x4, Motor Rifle x1. 14 strategic air-defense records with active tracking radars within 60 NM; strategic AD classes: Air Defense x14. 2 strategic ADA candidates filtered for inactive/missing tracking radars. 0 enemy squadron bases within 100 NM hosting 0 active squadrons. 11 active enemy air contact(s) at campaign time within or vectoring into 30 NM of the target area.
- INI plan correlation: TIMING is bracketed by TGT 2, TGT 1; PUSH is marked by TGT 3, TIG; SPLIT/recovery is nearest TGT 7
- Commander context: Low-altitude Gimhae / SA-10 West attack package. Jaguar 4 kills SA-10 West from Blues and attacks any surviving air-defense or parked-aircraft opportunity around Orion/Gimhae. Panther 1 strikes Orion/Gimhae while Hawkeye 2 escorts Jaguar 4, Jaguar 5 escorts Panther 1, and Sawbuck 2 provides high-altitude AMRAAM pressure between Tiger and Crown against fighters launching from Gimhae.
- Fallback logic: After SA-10 West, SA-10 East, and Orion/Gimhae are destroyed or the package is forced off, retrograde southwest toward Tiger, return to medium altitude, and RTB.

## Comm Data Workup
- Link 16 rows available: 97.
- Correlation basis: Matched by CAM camp_id/name_id/VU num when possible..
- Radio frequencies: derived from current campaign `RadioMap.dat` at `C:\Falcon BMS 4.38\Data\Campaign\RadioMap.dat` and joined to decoded package callsigns.
- UHF/VHF numbered preset decoding from `.frc` is not yet available; RadioMap bands are labeled by source field (`UHF 1`, `VHF`, `UHF 2`).

## Other Package Factors
- No additional friendly packages are expected to affect the target area.

## Enemy Air Threat Estimate
This section avoids enemy ATO/package tasking. It is based on active enemy squadron bases within the threat radius, known aircraft types, and bearing from those bases to the package/INI target-area anchors. Treat it as likely fighter threat axes, not a prediction of specific launches, callsigns, package IDs, or timings.

- No active enemy fighter-capable airbases were identified within the current airbase threat radius.

### Active Air Contacts At Campaign Time
These are current-position contacts only. Callsigns and enemy package/tasking IDs are intentionally omitted; the brief only exposes aircraft type, rough sector, range, and the observed reason they matter.

| Sector from AO | Aircraft | Capability | Count | Nearest area | Range | Basis |
| --- | --- | --- | --- | --- | --- | --- |
| W | MiG-27 | air contact | 2 | Panther 1 STRIKE STPT 6 @ 0611Z | 1.6 NM | airborne now within 30 NM of target-area anchor |
| NE | MiG-27 | air contact | 2 | Panther 1 STRIKE STPT 6 @ 0611Z | 1.9 NM | airborne now; next leg vectors inside 30 NM by 0532Z |
| W | Mi-8 | air contact | 2 | INI SA6 | 3.4 NM | airborne now within 30 NM of target-area anchor |
| NE | Mi-8 | air contact | 2 | INI SA6 | 3.6 NM | airborne now within 30 NM of target-area anchor |
| N | Ka-52K | air contact | 1 | INI TGT 4 | 5.8 NM | airborne now; next leg vectors inside 30 NM by 0533Z |
| N | MiG-29S | fighter-capable | 2 | INI TGT 6 | 7.8 NM | airborne now within 30 NM of target-area anchor |
| N | Mi-28 | air contact | 2 | INI 10 | 12.0 NM | airborne now within 30 NM of target-area anchor |
| N | Mi-8 | air contact | 2 | INI SA6 | 17.7 NM | airborne now within 30 NM of target-area anchor |
| N | MiG-31 | air contact | 2 | INI SA6 | 20.3 NM | airborne now within 30 NM of target-area anchor |
| N | MiG-27 | air contact | 2 | INI TGT 6 | 21.9 NM | airborne now within 30 NM of target-area anchor |
| N | Mi-8 | air contact | 2 | INI SA6 | 22.3 NM | airborne now within 30 NM of target-area anchor |

## Comm Ladder
### Frequencies
| Net | Frequency | Primary preset | Backup preset | Use |
| --- | --- | --- | --- | --- |
| TACTICAL PKG 7016 | 230.175 MHz | UHF 1 | UHF 2 | Panther 1 package tactical; backup 299.500 MHz; intra-flight VHF 141.075 MHz |
| ABM / AWACS | 378.500 MHz | UHF 1 | UHF 2 | Sentry 1 picture; backup 336.050 MHz |

### Check-In
| Step | Call | Notes |
| --- | --- | --- |
| Flight C/S | Callsign |  |
| Number / Type | As required |  |
| Position | Bullseye or tactical anchor as required |  |
| Ordnance | As required |  |
| Playtime | As required |  |
| Capabilities | As required |  |
| Abort Code | As required |  |

### Comm Priority
1. Fighter Engagement - A live engagement owns the net.
2. Contract Comm - Target killed, unable, abort, package timing, or lane deconfliction.
3. SEAD / Strike Coordination - Intra-package target sorting and prosecution updates.

### Comm Notes
- Example: Sentry, Panther 1, checking in as fragged, request ALPHA CHECK BULLSEYE.
- Use one ABM picture for both player packages; cross-package calls go to ABM, not package tactical.

### Link 16 & Nets
| Element | Role | TACAN | Laser | Link 16 STN | F2F | Mission | EW | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Panther 1 | OCA STRIKE | not assigned | 1688 | 2546 | 65 | 65 | 1 |  |
| Jaguar 4 | SEAD | not assigned | 1688 | 2717 | 65 | 65 | 1 | SEAD/DEAD SA-10 West from Blues: Blues / Orion - Flow from Tiger nap-of-the-earth past Crown, use Blues as the IP, then destroy SA-10 West with HARMs/CBUs. If able, prosecute any remaining air defenses or aircraft on top of Orion/Gimhae. |
| Hawkeye 2 | ESCORT | not assigned | 1688 | 1403 | 65 | 65 | -1 | Escort Jaguar 4: Jaguar 4 lane - Protect Jaguar 4 through the low-altitude SA-10 West attack. |
| Jaguar 5 | ESCORT | not assigned | 1688 | 4137 | 65 | 65 | -1 | Escort Panther 1: Panther 1 lane - Protect Panther 1 during ingress, Orion/Gimhae attack, and initial egress. |
| Sawbuck 2 | BARCAP | not assigned | 1688 | 1125 | 1 | 65 | -1 | High-altitude AMRAAM screen: Tiger to Crown - Work high around Tiger to Crown and shoot AMRAAMs at bandits coming out of Gimhae/Orion before they pressure the low-altitude strikers. |
| Sentry 1 | AWACS | not assigned | n/a | 1577 | 65 | 68 | -1 | ELINT STPT 4 0526Z BE 298/118; ELINT STPT 5 0530Z BE 311/111 |
| Copper 2 | TANKER | 123Y slot 0 | n/a | 6676 | 65 | 68 | -1 | TANKER STPT 4 0651Z BE 254/105; TANKER STPT 5 0659Z BE 238/148 |

## Enemy Situation And Air Defense Estimate
Threats below are focused on the package route, CAP/SAD areas, and named data-cartridge anchors. Strategic air-defense rows only include enemy Air Defense class systems with active tracking radars.
- Enemy teams considered: DPRK, Japan, PRC, USSR
- Summary: 22 enemy ground/naval units within 35 NM of package/INI tactical anchors; dominant nearby classes: Air Defense x9, Supply x8, Engineer x4, Motor Rifle x1. 14 strategic air-defense sites with active tracking radars within 60 NM; strategic AD classes: Air Defense x14. 0 enemy squadron base areas within 100 NM hosting 0 active squadrons. 11 active enemy air contact(s) at campaign time within or vectoring into 30 NM of the target area.
- Airbase threat: Closest squadron bases: none.

### Strategic Air Defense Units Near Package Route
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Nearest anchor | Dist NM | Air range | Low-alt range | Strength air/low |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1779 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 642.0 | 145.0 | Panther 1 STRIKE STPT 6 @ 0611Z | 0.0 | 85 | 71 | 150/150 |
| 1783 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 660.0 | 148.0 | INI 10 | 0.2 | 85 | 71 | 150/150 |
| 1787 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 660.0 | 148.0 | INI 10 | 0.2 | 18 | 15 | 60/60 |
| 1785 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 619.0 | 147.0 | INI SA6 | 0.3 | 18 | 15 | 60/60 |
| 1759 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 674.0 | 162.0 | INI 10 | 10.5 | 99 | 83 | 50/50 |
| 1767 | USSR | Air Defense | SA-11 (9K37M1); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-11 (9K37M1) (slot 0, 3/3) | 677.0 | 179.0 | INI 10 | 18.8 | 22 | 19 | 100/100 |
| 1773 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 687.0 | 182.0 | INI 10 | 23.2 | 85 | 71 | 150/150 |
| 1761 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 690.0 | 204.0 | INI 10 | 34.1 | 99 | 83 | 50/50 |
| 1774 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 690.0 | 204.0 | INI 10 | 34.1 | 85 | 71 | 150/150 |
| 1781 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | INI SA6 | 41.9 | 85 | 71 | 150/150 |
| 2235 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | INI SA6 | 41.9 | 85 | 71 | 150/150 |
| 1763 | USSR | Air Defense | SA-2 (S-75); Fan Song E; ZU-23; ZIL-131; KrAz T 255B | Fan Song E (slot 3, 1/1) | 643.0 | 229.0 | INI 10 | 44.5 | 30 | 25 | 70/70 |
| 1769 | USSR | Air Defense | SA-17 (9K37M2); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-17 (9K37M2) (slot 0, 3/3) | 646.0 | 234.0 | INI 10 | 46.9 | 30 | 25 | 100/100 |
| 1765 | USSR | Air Defense | SA-3 (S-125); Low Blow; ZPU-2; KrAz T 255B; Flat Face | Low Blow (slot 2, 1/1) | 686.0 | 248.0 | INI 10 | 55.6 | 17 | 15 | 70/70 |

### Nearby Enemy Ground/Naval Units
| ID | Team | Class | Category | Equipment | Grid X | Grid Y | Nearest anchor | Dist NM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1779 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 642.0 | 145.0 | Panther 1 STRIKE STPT 6 @ 0611Z | 0.0 |
| 1783 | USSR | Air Defense | air defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | 660.0 | 148.0 | INI 10 | 0.2 |
| 1787 | USSR | Air Defense | air defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | 660.0 | 148.0 | INI 10 | 0.2 |
| 1785 | USSR | Air Defense | air defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | 619.0 | 147.0 | INI SA6 | 0.3 |
| 1417 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 663.0 | 157.0 | INI 10 | 4.9 |
| 1419 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 663.0 | 157.0 | INI 10 | 4.9 |
| 2347 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 663.0 | 157.0 | INI 10 | 4.9 |
| 1421 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 669.0 | 154.0 | INI 10 | 5.6 |
| 1423 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 669.0 | 154.0 | INI 10 | 5.6 |
| 2351 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 669.0 | 154.0 | INI 10 | 5.6 |
| 1759 | USSR | Air Defense | air defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | 674.0 | 162.0 | INI 10 | 10.5 |
| 1409 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 676.0 | 160.0 | INI 10 | 10.6 |
| 1411 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 676.0 | 160.0 | INI 10 | 10.6 |
| 2339 | USSR | Supply | other | M978 HEMMT; M977 HEMMT | 676.0 | 160.0 | INI 10 | 10.6 |
| 2309 | USSR | Motor Rifle | other | BTR-60; T-55; BRDM-2AT; M-1992; ZIL-131 | 614.0 | 167.0 | INI SA6 | 10.9 |
| 1413 | USSR | Engineer | maneuver | MDK-2M; BTR-80; KrAz T 255B | 679.0 | 171.0 | INI 10 | 15.9 |

## Coordinate Appendix
Location data is separated here so the main brief stays readable.
- Bullseye: grid 643.0 / 145.0

### PKG 7016 Flight Steerpoints
| C/S | STPT | Action | Arrive (Z) | Grid X | Grid Y | Bullseye | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Panther 1 | 0 | TAKEOFF | 0549Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Panther 1 | 2 | TIMING | 0553Z | 505.0 | 129.0 | BE 263/75 | 2200.0 |  |
| Panther 1 | 3 | PUSH | 0605Z | 570.0 | 98.0 | BE 237/47 | 2200.0 |  |
| Panther 1 | 6 | STRIKE | 0611Z | 642.0 | 145.0 | BE 270/1 | 1800.0 | unresolved 2035 |
| Panther 1 | 7 | SPLIT | 0619Z | 518.0 | 137.0 | BE 266/68 | 2100.0 |  |
| Panther 1 | 8 | LAND | 0624Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Panther 1 | 9 | REFUEL | 0624Z | 398.0 | 309.0 | BE 304/159 | 2000.0 |  |
| Panther 1 | 10 | LAND | 0624Z | 410.0 | 124.0 | BE 265/126 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |
| Jaguar 4 | 0 | TAKEOFF | 0545Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Jaguar 4 | 2 | TIMING | 0550Z | 507.0 | 123.0 | BE 261/74 | 2200.0 |  |
| Jaguar 4 | 3 | PUSH | 0601Z | 569.0 | 98.0 | BE 238/47 | 2200.0 |  |
| Jaguar 4 | 5 | SEAD | 0607Z | 642.0 | 145.0 | BE 270/1 | 2000.0 |  |
| Jaguar 4 | 6 | SPLIT | 0615Z | 518.0 | 137.0 | BE 266/68 | 2100.0 |  |
| Jaguar 4 | 7 | LAND | 0620Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Jaguar 4 | 8 | REFUEL | 0620Z | 398.0 | 309.0 | BE 304/159 | 2000.0 |  |
| Jaguar 4 | 9 | LAND | 0620Z | 410.0 | 124.0 | BE 265/126 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |
| Hawkeye 2 | 0 | TAKEOFF | 0546Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Hawkeye 2 | 2 | TIMING | 0550Z | 505.0 | 129.0 | BE 263/75 | 2200.0 |  |
| Hawkeye 2 | 3 | PUSH | 0602Z | 570.0 | 97.0 | BE 237/47 | 2200.0 |  |
| Hawkeye 2 | 6 | SPLIT | 0616Z | 518.0 | 137.0 | BE 266/68 | 2100.0 |  |
| Hawkeye 2 | 7 | LAND | 0621Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Hawkeye 2 | 8 | REFUEL | 0621Z | 398.0 | 309.0 | BE 304/159 | 2000.0 |  |
| Hawkeye 2 | 9 | LAND | 0621Z | 410.0 | 124.0 | BE 265/126 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |
| Jaguar 5 | 0 | TAKEOFF | 0547Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Jaguar 5 | 2 | TIMING | 0551Z | 505.0 | 129.0 | BE 263/75 | 2200.0 |  |
| Jaguar 5 | 3 | PUSH | 0603Z | 570.0 | 98.0 | BE 237/47 | 2200.0 |  |
| Jaguar 5 | 6 | SPLIT | 0617Z | 518.0 | 137.0 | BE 266/68 | 2100.0 |  |
| Jaguar 5 | 7 | LAND | 0622Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |
| Jaguar 5 | 8 | REFUEL | 0622Z | 398.0 | 309.0 | BE 304/159 | 2000.0 |  |
| Jaguar 5 | 9 | LAND | 0622Z | 410.0 | 124.0 | BE 265/126 | 0.0 | Muan Intl Airport (RKJB) (objective 3299) |
| Sawbuck 2 | 0 | TAKEOFF | 0549Z | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Sawbuck 2 | 3 | CAP | 0607Z | 611.0 | 113.0 | BE 225/24 | 2100.0 |  |
| Sawbuck 2 | 4 | CAP | 0610Z | 642.0 | 145.0 | BE 270/1 | 2100.0 |  |
| Sawbuck 2 | 6 | LAND | 0654Z | 432.0 | 224.0 | BE 291/122 | 0.0 | Gunsan AB (RKJK) (objective 995) |
| Sawbuck 2 | 7 | REFUEL | 0654Z | 438.0 | 352.0 | BE 315/157 | 2000.0 |  |
| Sawbuck 2 | 8 | LAND | 0654Z | 448.0 | 138.0 | BE 268/105 | 0.0 | Cheongju Intl Airport (RKTU) (objective 997) |

### Linked Support Flight Coordinates
| Role | C/S | STPT | Action | Arrive (Z) | Grid X | Grid Y | Bullseye | Grid Z | Target/object |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWACS | Sentry 1 | 0 | TAKEOFF | 0502Z | 449.0 | 407.0 | BE 323/176 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |
| AWACS | Sentry 1 | 2 | TIMING | 0516Z | 437.0 | 300.0 | BE 307/139 | 2800.0 |  |
| AWACS | Sentry 1 | 3 | PUSH | 0523Z | 450.0 | 288.0 | BE 307/130 | 2800.0 |  |
| AWACS | Sentry 1 | 4 | ELINT | 0526Z | 450.0 | 248.0 | BE 298/118 | 2600.0 |  |
| AWACS | Sentry 1 | 5 | ELINT | 0530Z | 487.0 | 280.0 | BE 311/111 | 2600.0 |  |
| AWACS | Sentry 1 | 6 | SPLIT | 1034Z | 475.0 | 322.0 | BE 316/132 | 2700.0 |  |
| AWACS | Sentry 1 | 7 | LAND | 1041Z | 449.0 | 407.0 | BE 323/176 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |
| AWACS | Sentry 1 | 8 | REFUEL | 0011Z | 398.0 | 309.0 | BE 304/159 | 2000.0 |  |
| AWACS | Sentry 1 | 9 | LAND | 0011Z | 477.0 | 395.0 | BE 326/162 | 0.0 | Seoul AB (RKSM) (objective 1484) |
| TANKER | Copper 2 | 0 | TAKEOFF | 0619Z | 419.0 | 398.0 | BE 318/182 | 0.0 | Incheon Intl Airport (RKSI) (objective 3298) |
| TANKER | Copper 2 | 2 | TIMING | 0640Z | 450.0 | 149.0 | BE 271/104 | 2400.0 |  |
| TANKER | Copper 2 | 4 | TANKER | 0651Z | 457.0 | 90.0 | BE 254/105 | 2400.0 |  |
| TANKER | Copper 2 | 5 | TANKER | 0659Z | 410.0 | 2.0 | BE 238/148 | 2400.0 |  |
| TANKER | Copper 2 | 8 | LAND | 1226Z | 419.0 | 398.0 | BE 318/182 | 0.0 | Incheon Intl Airport (RKSI) (objective 3298) |
| TANKER | Copper 2 | 9 | LAND | 0000Z | 449.0 | 407.0 | BE 323/176 | 0.0 | Gimpo Intl Airport (RKSS) (objective 1486) |

### Weather Sample Coordinates
| Area | Local time | FMAP Row | FMAP Col | Grid X | Grid Y | Conditions | Wind | Visibility km | Briefed cloud base | Raw cumulus field ft | Contrail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Takeoff | 1449 | 51 | 25 | 448.0 | 138.0 | Sunny CLR | 336/4 kt | 59.9 | 38,000 ft | 4420 | 34,000 ft |
| Target Area | 1507 | 50 | 31 | 540.8 | 153.6 | Sunny CLR | 315/5 kt | 59.9 | 38,000 ft | 3797 | 34,000 ft |
| Landing | 1524 | 51 | 25 | 448.0 | 138.0 | Sunny CLR | 336/4 kt | 59.9 | 38,000 ft | 4420 | 34,000 ft |

### INI Planning Steerpoints
| Kind | Label | Code | INI X ft | INI Y ft | Grid X | Grid Y | Map status | Bullseye | Nearest package route point |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| target | TGT 0 | 1 | 454277.2 | 1471071.0 | 448.4 | 138.5 | usable | BE 268/105 | Panther 1 TAKEOFF STPT 0 @ 0549Z 0.3 NM |
| target | TGT 1 | 0 | 434597.3 | 1579310.4 | 481.4 | 132.5 | usable | BE 266/88 | Panther 1 TIMING STPT 2 @ 0553Z 12.9 NM |
| target | TGT 2 | 8 | 424757.4 | 1658029.9 | 505.4 | 129.5 | usable | BE 264/75 | Panther 1 TIMING STPT 2 @ 0553Z 0.3 NM |
| target | TGT 3 | 2 | 323078.0 | 1871228.6 | 570.4 | 98.5 | usable | BE 237/47 | Panther 1 PUSH STPT 3 @ 0605Z 0.3 NM |
| target | TGT 4 | 0 | 401797.6 | 2015547.8 | 614.3 | 122.5 | usable | BE 232/20 | Sawbuck 2 CAP STPT 3 @ 0607Z 5.4 NM |
| target | TGT 5 | 0 | 457557.2 | 2071307.4 | 631.3 | 139.5 | usable | BE 245/7 | Panther 1 STRIKE STPT 6 @ 0611Z 6.5 NM |
| target | TGT 6 | 17 | 477237.1 | 2107387.2 | 642.3 | 145.5 | usable | BE 306/0 | Panther 1 STRIKE STPT 6 @ 0611Z 0.3 NM |
| target | TGT 7 | 3 | 450997.2 | 1700669.6 | 518.4 | 137.5 | usable | BE 267/67 | Panther 1 SPLIT STPT 7 @ 0619Z 0.3 NM |
| target | TGT 8 | 7 | 454277.2 | 1471071.0 | 448.4 | 138.5 | usable | BE 268/105 | Panther 1 TAKEOFF STPT 0 @ 0549Z 0.3 NM |
| target | TGT 9 | 4 | 1015153.8 | 1307072.0 | 398.4 | 309.4 | usable | BE 304/159 | Panther 1 REFUEL STPT 9 @ 0624Z 0.3 NM |
| target | TGT 10 | 7 | 408357.5 | 1346431.8 | 410.4 | 124.5 | usable | BE 265/126 | Panther 1 LAND STPT 10 @ 0624Z 0.3 NM |
| target | TGT 11 | 7 | 736355.5 | 1418591.4 | 432.4 | 224.4 | usable | BE 291/122 | Sawbuck 2 TAKEOFF STPT 0 @ 0549Z 0.3 NM |
| target | TGT 12 | 4 | 1015153.8 | 1307072.0 | 398.4 | 309.4 | usable | BE 304/159 | Panther 1 REFUEL STPT 9 @ 0624Z 0.3 NM |
| target | TGT 13 | 7 | 454277.2 | 1471071.0 | 448.4 | 138.5 | usable | BE 268/105 | Panther 1 TAKEOFF STPT 0 @ 0549Z 0.3 NM |
| ppt | ORO |  | 5139024.0 | 2108082.0 | 642.5 | 1566.4 | out of theater; excluded from map crops |  |  |
| ppt | 10 |  | 477053.2 | 2107703.2 | 642.4 | 145.4 | usable | BE 304/0 | Panther 1 STRIKE STPT 6 @ 0611Z 0.3 NM |
| ppt | 15 |  | 490476.2 | 2021947.5 | 616.3 | 149.5 | usable | BE 280/15 |  |
| ppt | 10 |  | 486715.5 | 2165976.5 | 660.2 | 148.4 | usable | BE 079/9 | Panther 1 STRIKE STPT 6 @ 0611Z 10.0 NM |
| ppt | SA5 |  | 532862.0 | 2212552.2 | 674.4 | 162.4 | usable | BE 061/19 |  |
| ppt | CRO |  | 390471.2 | 2038726.6 | 621.4 | 119.0 | usable | BE 220/18 | Sawbuck 2 CAP STPT 3 @ 0607Z 6.5 NM |
| ppt | BLU |  | 450066.0 | 2076887.6 | 633.0 | 137.2 | usable | BE 232/7 | Panther 1 STRIKE STPT 6 @ 0611Z 6.4 NM |
| ppt | SA6 |  | 483899.2 | 2031964.2 | 619.3 | 147.5 | usable | BE 276/13 | Panther 1 STRIKE STPT 6 @ 0611Z 12.3 NM |
| ppt | 10 |  | 598985.8 | 2254517.0 | 687.2 | 182.6 | usable | BE 050/31 |  |
| ppt | TIG |  | 322750.0 | 1871245.2 | 570.4 | 98.4 | usable | BE 237/47 | Panther 1 PUSH STPT 3 @ 0605Z 0.3 NM |
| ppt | WWO |  | 394908.8 | 2180357.8 | 664.6 | 120.4 | usable | BE 139/18 |  |
| ppt | BAN |  | 5774994.5 | 2166003.8 | 660.2 | 1760.2 | out of theater; excluded from map crops |  |  |
| ppt | BAN |  | 463551.8 | 2168588.2 | 661.0 | 141.3 | usable | BE 102/10 | Panther 1 STRIKE STPT 6 @ 0611Z 10.5 NM |

### Strategic Air Defense Coordinates
Air-defense rows use saved campaign battalion/unit grid coordinates and exclude embedded short-range point/base defenses. They are enemy strategic sites with active tracking radars.
| ID | Team | Class | Equipment | Tracking radar | Grid X | Grid Y | Bullseye | Nearest package/INI anchor | Dist NM | Air range | Low-alt range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1779 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 642.0 | 145.0 | BE 270/1 | Panther 1 STRIKE STPT 6 @ 0611Z | 0.0 | 85 | 71 |
| 1783 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 660.0 | 148.0 | BE 080/9 | INI 10 | 0.2 | 85 | 71 |
| 1787 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 660.0 | 148.0 | BE 080/9 | INI 10 | 0.2 | 18 | 15 |
| 1785 | USSR | Air Defense | SA-6 (2K12); KrAz F 255B; Straight Flush; ACRV MT-LBu; Flat Face | Straight Flush (slot 3, 1/1) | 619.0 | 147.0 | BE 275/13 | INI SA6 | 0.3 | 18 | 15 |
| 1759 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 674.0 | 162.0 | BE 061/19 | INI 10 | 10.5 | 99 | 83 |
| 1767 | USSR | Air Defense | SA-11 (9K37M1); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-11 (9K37M1) (slot 0, 3/3) | 677.0 | 179.0 | BE 045/26 | INI 10 | 18.8 | 22 | 19 |
| 1773 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 687.0 | 182.0 | BE 050/31 | INI 10 | 23.2 | 85 | 71 |
| 1761 | USSR | Air Defense | SA-5 (S-200); Square Pair; ZIL-131; KrAz T 255B; Bar Lock B | Square Pair (slot 3, 1/1) | 690.0 | 204.0 | BE 039/41 | INI 10 | 34.1 | 99 | 83 |
| 1774 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 690.0 | 204.0 | BE 039/41 | INI 10 | 34.1 | 85 | 71 |
| 1781 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | BE 342/45 | INI SA6 | 41.9 | 85 | 71 |
| 2235 | USSR | Air Defense | SA-10 (S-300P); Flap Lid; 54K6E CP; ZPU-2; KrAz T 255B | Flap Lid (slot 2, 1/1) | 617.0 | 225.0 | BE 342/45 | INI SA6 | 41.9 | 85 | 71 |
| 1763 | USSR | Air Defense | SA-2 (S-75); Fan Song E; ZU-23; ZIL-131; KrAz T 255B | Fan Song E (slot 3, 1/1) | 643.0 | 229.0 | BE 000/45 | INI 10 | 44.5 | 30 | 25 |
| 1769 | USSR | Air Defense | SA-17 (9K37M2); KrAz T 255B; Snow Drift; BMP-1KSh; ACRV MT-LBu | SA-17 (9K37M2) (slot 0, 3/3) | 646.0 | 234.0 | BE 002/48 | INI 10 | 46.9 | 30 | 25 |
| 1765 | USSR | Air Defense | SA-3 (S-125); Low Blow; ZPU-2; KrAz T 255B; Flat Face | Low Blow (slot 2, 1/1) | 686.0 | 248.0 | BE 023/60 | INI 10 | 55.6 | 17 | 15 |

### Active Enemy Air Contact Coordinates
Rows use current campaign-time positions. Enemy callsigns and package IDs are omitted.
| Sector | Aircraft | Capability | Count | Grid X | Grid Y | Bullseye | Alt ft | Nearest package/INI anchor | Dist NM | Basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W | MiG-27 | air contact | 2 | 639.0 | 145.0 | BE 270/2 | 9843 | Panther 1 STRIKE STPT 6 @ 0611Z | 1.6 | airborne now within 30 NM of target-area anchor |
| NE | MiG-27 | air contact | 2 | 650.0 | 162.0 | BE 022/10 | 12080 | Panther 1 STRIKE STPT 6 @ 0611Z | 1.9 | airborne now; next leg vectors inside 30 NM by 0532Z |
| W | Mi-8 | air contact | 2 | 613.0 | 147.0 | BE 274/16 | 4869 | INI SA6 | 3.4 | airborne now within 30 NM of target-area anchor |
| NE | Mi-8 | air contact | 2 | 623.0 | 153.0 | BE 292/12 | 15000 | INI SA6 | 3.6 | airborne now within 30 NM of target-area anchor |
| N | Ka-52K | air contact | 1 | 615.0 | 137.0 | BE 254/16 | 4902 | INI TGT 4 | 5.8 | airborne now; next leg vectors inside 30 NM by 0533Z |
| N | MiG-29S | fighter-capable | 2 | 637.0 | 159.0 | BE 337/8 | 21000 | INI TGT 6 | 7.8 | airborne now within 30 NM of target-area anchor |
| N | Mi-28 | air contact | 2 | 655.0 | 170.0 | BE 026/15 | 6000 | INI 10 | 12.0 | airborne now within 30 NM of target-area anchor |
| N | Mi-8 | air contact | 2 | 623.0 | 180.0 | BE 330/22 | 5394 | INI SA6 | 17.7 | airborne now within 30 NM of target-area anchor |
| N | MiG-31 | air contact | 2 | 620.0 | 185.0 | BE 330/25 | 21000 | INI SA6 | 20.3 | airborne now within 30 NM of target-area anchor |
| N | MiG-27 | air contact | 2 | 642.0 | 186.0 | BE 359/22 | 16000 | INI TGT 6 | 21.9 | airborne now within 30 NM of target-area anchor |
| N | Mi-8 | air contact | 2 | 627.0 | 188.0 | BE 340/25 | 4489 | INI SA6 | 22.3 | airborne now within 30 NM of target-area anchor |

### Resolved Location Objects
| Kind | ID | Name | Source X | Source Y | Source Z |
| --- | --- | --- | --- | --- | --- |
| objective | 995 | Gunsan AB (RKJK) | 736355.5 | 1418591.3 | 0.0 |
| objective | 997 | Cheongju Intl Airport (RKTU) | 1029703.8 | 1677316.2 | 0.0 |
| objective | 3299 | Muan Intl Airport (RKJB) | 408114.8 | 1346431.8 | 0.0 |
| unresolved | 2035 |  |  |  |  |

## Map Products
- Full-route chart map: `package_7016_route_threat_map_skyvector.png`
- Tactical target-area chart: `package_7016_target_area_zoom_skyvector.png`
- Objective-area close-up chart: `package_7016_objective_area_zoom_skyvector.png`
- Weather review chart: `package_7016_weather_map_skyvector.png`
- Close-up map note: objective-area charts preserve CAP anchors Escort Jaguar 4 (Jaguar 4 lane), Escort Panther 1 (Panther 1 lane), High-altitude AMRAAM screen (Tiger to Crown) alongside the target and INI route geometry.

![PKG 7016 objective-area zoom](package_7016_objective_area_zoom_skyvector.png)

## Review Items
- Confirm package inclusion and tasking against the mission commander's intent.
- Validate aircraft/loadout/laser/TACAN values against the BMS UI before publishing a live mission brief.
- Validate inferred HHMM times against the BMS UI or human mission card before treating them as authoritative.
