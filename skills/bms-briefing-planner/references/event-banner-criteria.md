# UOAF Event Banner Criteria

Use these criteria for every new or revised UOAF event banner unless the user
explicitly asks for a different visual direction.

## Default Art Direction: Subtle Cinematic Realism

Aim for a banner that is cool because it feels plausible, not because it is
loud. Preserve a tense, atmospheric military-aviation mood through composition,
weather, moonlight, haze, scale, and restrained contrast. The image may feel
cinematic, but the world should still look physically believable.

## Terrain And Ground Detail

- Use terrain appropriate to the mission theater: credible ridgelines, valleys,
  coastline, farmland, roads, settlements, and natural atmospheric depth.
- Keep towns and roads at believable scale. At night, use sparse practical
  lighting rather than a blanket of decorative glow.
- Depict radar, SAM, armor, or objective sites as small installations integrated
  into the terrain. Use plausible equipment silhouettes, camouflage, berms,
  service roads, and faint task lighting when useful.
- Ground targets must not appear as giant towers, fantasy fortresses, glowing
  monuments, or oversized game objectives.
- Do not use concentric target rings, blue targeting beams, dashed route lines,
  grid overlays, or other HUD/map graphics in the finished banner.

## Aircraft And Weapon Effects

- Keep aircraft geometry, stores, scale, perspective, lighting, and formation
  believable. Reject malformed wings, duplicated tails, impossible pylons, or
  aircraft that do not fit the mission character.
- When stores must be recognizable, read and use
  [aircraft-loadout-visual-contract.md](aircraft-loadout-visual-contract.md).
  Extract the current flight's ordered BMS loadout slots, including empty slots,
  then translate them through the applicable airframe mapping. Do not ask the
  planner to reconstruct routine station assignments.
- Default to aircraft in formation or tactically suggestive flight rather than
  visible weapons impacts.
- Do not include purple or neon missiles, energy projectiles, glowing exhaust
  trails, laser-like weapons, or science-fiction effects.
- Do not show missiles in flight by default. If the user explicitly asks for an
  active weapons-release scene, keep the weapon, smoke, lighting, and scale
  physically credible and visually subordinate to the event identity.
- Restrained blue or purple may remain as a typography accent, but never as a
  weapon, target, terrain, or atmospheric glow effect.

## Brand And Text Invariants

- Use `assets/uoaf-roundel.png` as the canonical logo source.
- Preserve the crest's exact identity, wording, compass/aircraft motif,
  proportions, and colors. Do not invent unit markings or reinterpret the logo.
- Render the operation title and `UOAF EVENT <number>` exactly as supplied.
- Keep the title readable at Discord preview size. Do not add slogans, tactical
  labels, watermarks, or other unrequested text.
- Keep branding prominent but integrated; it should not look pasted onto an
  unrelated image.

## Editing An Existing Banner

Treat an approved banner as the edit target, not merely a loose inspiration.
List its invariants explicitly in the image-edit prompt: logo, exact text,
typography placement, aircraft composition, aspect ratio, palette, lighting,
and atmosphere. Change only the elements the user rejected.

For an over-the-top source image, preserve the mood and composition while
removing spectacle layers such as neon projectiles, HUD graphics, giant targets,
and fantasy structures. Replace them with realistic terrain and subtle military
detail. Save the revision under a new sibling filename unless the user clearly
asks to replace the original.

## Approval Checklist

Inspect the full-resolution image and a Discord-sized preview. Approve only when:

- Terrain and ground installations look credible at their depicted distance.
- No neon/purple weapon effects, energy trails, HUD overlays, giant targets, or
  unexplained glowing structures remain.
- Aircraft silhouettes and stores are coherent.
- UOAF crest fidelity is acceptable and no unrelated insignia appears.
- Event number and operation title are exact and legible.
- The banner still has atmosphere and visual impact without relying on
  exaggerated effects.

If any one of these checks fails, make one targeted revision and inspect again.
