---
name: bms-briefing-design
description: Turn a UOAF BMS briefing bundle into a polished mission briefing deck using uploaded markdown, JSON, and map images.
---

# BMS Briefing Design

Use this skill when the user uploads a bundle produced by
`scripts/export_claude_design_bundle.py` and asks for a BMS mission briefing
deck.

## Inputs

Expect these files:

- `source/generated_briefing.md`
- `source/briefing_synthesis.json`
- map images in `assets/`, usually package overview, target area, objective
  area, and weather map
- `claude_design_prompt.md`
- `manifest.json`

## Rules

- Create the final briefing, not a pipeline explanation.
- Treat `generated_briefing.md` and `briefing_synthesis.json` as source of
  truth.
- Rewrite generated prose into human tactical briefing language.
- Use map images as major slide visuals.
- Do not reveal decoded enemy callsigns, package IDs, or specific future enemy
  ATO tasking.
- Do not include friendly air-defense data.
- Include friendly package composition, weather, mission execution plan, support
  picture, comm ladder, enemy strategic ADA, enemy airbase threat axes, and
  active air contacts when present.
- Keep coordinate-heavy tables in backup/appendix slides unless the user asks
  for them in the main brief.
- The legacy in-repo PPTX builder is deprecated fallback context only.

## Suggested Deck Shape

1. Mission overview and intent.
2. Package composition and timing.
3. Route overview map with support tracks and threat context.
4. Target/objective area close-up with A/B/C/D/E/WCH/GRD/BAR.
5. Weather and environmental factors.
6. Threat estimate: strategic ADA, enemy airbase axes, active contacts.
7. Communications and coordination.
8. Execution notes and contingencies.
9. Backup: coordinates and source caveats.
