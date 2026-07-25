#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith("--")) {
      throw new Error(`Unexpected positional argument: ${key}`);
    }
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      args[key.slice(2)] = true;
    } else {
      args[key.slice(2)] = next;
      index += 1;
    }
  }
  return args;
}

function printHelp() {
  console.log(`Usage: node scripts/build_bms_briefing_deck.mjs --synthesis PATH [--out-dir DIR] [--package-id ID]

Deprecated fallback. The supported deck-production path is:
  python scripts/export_claude_design_bundle.py --synthesis PATH --package-id ID --out-dir DIR

Options:
  --synthesis PATH   Path to briefing_synthesis.json.
  --out-dir DIR      Output directory for fallback PPTX.
  --out PATH         Explicit fallback PPTX output path.
  --package-id ID    Package ID to render.
  --workspace DIR    Generated presentation workspace.
  --skill-dir DIR    Codex presentations skill directory.
  --help             Show this help and exit.`);
}

function slug(value) {
  return String(value || "bms-briefing")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function timestampId() {
  const now = new Date();
  const stamp = now.toISOString().replace(/[-:]/g, "").replace(/\..+$/, "").replace("T", "-");
  const suffix = Math.random().toString(36).slice(2, 8);
  return `manual-${stamp}-${suffix}`;
}

function defaultSkillDir() {
  const home = process.env.USERPROFILE || process.env.HOME || "";
  return path.join(
    home,
    ".codex",
    "plugins",
    "cache",
    "openai-primary-runtime",
    "presentations",
    "26.506.11943",
    "skills",
    "presentations",
  );
}

function targetText(target) {
  if (!target) return "";
  if (target.display) return target.display;
  if (target.name) return target.name;
  if (target.kind === "unresolved") return `Unresolved target ${target.camp_id}`;
  if (target.kind && target.kind !== "objective") return `${String(target.kind).toUpperCase()} ${target.camp_id}`;
  return `Objective ${target.camp_id}`;
}

function packageTargetText(pkg, limit = 3) {
  const names = [];
  for (const target of pkg?.targets || []) {
    const name = targetText(target);
    if (name && !names.includes(name)) names.push(name);
  }
  if (!names.length) return "No named tactical target resolved";
  return names.slice(0, limit).join(", ") + (names.length > limit ? ` +${names.length - limit}` : "");
}

function flightTargetText(flight, limit = 2) {
  const names = [];
  for (const target of flight?.target_refs || []) {
    const name = targetText(target);
    if (name && !names.includes(name)) names.push(name);
  }
  if (!names.length) return "No named tactical target resolved";
  return names.slice(0, limit).join(", ") + (names.length > limit ? ` +${names.length - limit}` : "");
}

function roleMix(pkg) {
  return Object.entries(pkg?.flight_missions || {})
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([mission, count]) => `${mission} x${count}`)
    .join(", ");
}

function compactText(value, max = 120) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, Math.max(0, max - 1)).trim()}...`;
}

function routeText(flight) {
  const wanted = new Set(["WP_TIMING", "WP_PUSH", "WP_CAP", "WP_SAD", "WP_SPLIT"]);
  return (flight?.key_waypoints || [])
    .filter((waypoint) => wanted.has(waypoint.action))
    .map((waypoint) => `${String(waypoint.action || "").replace(/^WP_/, "")} ${waypoint.arrive_hhmm || ""} (${waypoint.grid_x},${waypoint.grid_y})`)
    .slice(0, 4)
    .join(" -> ");
}

function enemyAnchorText(unit) {
  const anchor = unit?.nearest_anchor || {};
  const label = String(anchor.label || "").trim();
  const time = String(anchor.time || "").trim();
  if (time && !label.includes(time)) return `${label} @ ${time}`;
  return label;
}

function enemyGridText(unit) {
  if (unit?.grid_x == null || unit?.grid_y == null) return "";
  return `${unit.grid_x},${unit.grid_y}`;
}

function priorityAirDefenses(units, limit = 7) {
  const selected = [];
  const seen = new Set();
  const addMatches = (predicate) => {
    for (const unit of units || []) {
      const id = unit.camp_id ?? `${unit.grid_x},${unit.grid_y},${unit.class_name}`;
      if (seen.has(id) || !predicate(unit)) continue;
      seen.add(id);
      selected.push(unit);
      if (selected.length >= limit) return;
    }
  };
  addMatches((unit) => String(unit.class_name || "").toLowerCase() === "air defense");
  addMatches((unit) => String(unit.class_name || "").toLowerCase() === "aaa");
  addMatches(() => true);
  return selected.slice(0, limit);
}

function packageWindow(pkg) {
  const takeoffs = [];
  const tots = [];
  for (const flight of pkg?.flights || []) {
    if (flight.takeoff_hhmm) takeoffs.push(flight.takeoff_hhmm);
    if (flight.tot_hhmm) tots.push(flight.tot_hhmm);
  }
  return {
    takeoff: takeoffs.length ? `${takeoffs.sort()[0]}-${takeoffs.sort()[takeoffs.length - 1]}` : "",
    tot: tots.length ? `${tots.sort()[0]}-${tots.sort()[tots.length - 1]}` : "",
  };
}

function compactPackage(pkg) {
  if (!pkg) return null;
  const window = packageWindow(pkg);
  const planCorrelation = pkg.plan_correlation || {};
  const lineSummary = planCorrelation.line_summary || {};
  const humanContext = pkg.human_context || {};
  const enemySituation = pkg.enemy_situation || {};
  const slideNotes = humanContext.slide_notes || {};
  const targetOpportunities = humanContext.target_opportunities || [];
  const capContracts = humanContext.cap_contracts || [];
  const capContractText = capContracts
    .map((item) => `${item.callsign || ""}: ${item.area || item.label || ""} ${item.sector || ""}`.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .join("; ");
  return {
    packageId: pkg.package_id,
    mission: pkg.mission || "UNKNOWN",
    score: pkg.score || 0,
    flightCount: pkg.flight_count || 0,
    roleMix: roleMix(pkg),
    takeoffWindow: window.takeoff,
    totWindow: window.tot,
    targetSummary: packageTargetText(pkg),
    planInterpretation: pkg.plan_interpretation || "",
    planSnapshot: pkg.plan_interpretation ? "TIMING/PUSH/SPLIT marks decoded" : "No close INI plan marks",
    planShort: compactText(pkg.plan_interpretation || "No close INI planning correlation decoded", 92),
    planLineSummary: lineSummary?.interpretation || "",
    enemySummary: compactText(enemySituation.summary || "", 125),
    enemyBasis: enemySituation.basis || "",
    enemyTeams: (enemySituation.enemy_teams || []).join(", "),
    enemyAnchorCount: enemySituation.anchor_count || 0,
    airDefenseRadiusNm: enemySituation.air_defense_radius_nm || 0,
    unitRadiusNm: enemySituation.unit_radius_nm || 0,
    airDefenses: priorityAirDefenses(enemySituation.air_defenses || []).map((unit) => ({
      id: unit.camp_id,
      team: unit.team || "",
      className: unit.class_name || "",
      equipment: compactText(unit.equipment || "", 58),
      grid: enemyGridText(unit),
      anchor: compactText(enemyAnchorText(unit), 42),
      distanceNm: unit.distance_nm,
      range: [unit.air_range, unit.low_air_range].filter((value) => value != null).join("/"),
    })),
    airbases: (enemySituation.airbases || []).slice(0, 5).map((base) => ({
      id: base.airbase_id,
      name: base.name || "",
      team: base.team || "",
      activeSquadrons: base.squadron_count || 0,
      aircraft: compactText(base.aircraft_summary || "", 56),
      grid: enemyGridText(base),
      anchor: compactText(enemyAnchorText(base), 38),
      distanceNm: base.distance_nm,
      status: compactText(base.status || "", 52),
    })),
    closestEnemy: (enemySituation.closest_units || []).slice(0, 8).map((unit) => ({
      id: unit.camp_id,
      team: unit.team || "",
      className: unit.class_name || "",
      category: unit.category || "",
      equipment: compactText(unit.equipment || "", 44),
      grid: enemyGridText(unit),
      anchor: compactText(enemyAnchorText(unit), 38),
      distanceNm: unit.distance_nm,
    })),
    humanContext,
    routeName: humanContext.route_name || "Route",
    routeNote: humanContext.route_note || "",
    fallbackLogic: humanContext.fallback_logic || "",
    briefingRead: humanContext.briefing_read || "",
    briefingReadShort: compactText(slideNotes.commander_context || humanContext.briefing_read || "", 185),
    capContractText,
    capContractSnapshot: capContracts
      .map((item) => `${item.area || item.label || ""} ${String(item.sector || "").replace(/\s*CAP area\s*/i, "").trim()}`.replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .join(" / "),
    fallbackShort: compactText(humanContext.fallback_logic || "", 145),
    targetOpportunityText: targetOpportunities
      .map((item) => `${item.label || ""} ${item.name || ""}: ${item.type || ""} - ${item.intent || ""}`.replace(/\s+/g, " ").trim())
      .join("; "),
    targetOpportunityShort: compactText(slideNotes.targets_and_fallback || targetOpportunities
      .map((item) => `${item.label || ""}/${item.name || ""}: ${item.type || ""}; ${item.intent || ""}`.replace(/\s+/g, " ").trim())
      .join(" | "), 170),
    contractText: (humanContext.sad_contracts || [])
      .map((item) => `${item.callsign || ""}: ${item.contract || ""}`)
      .join("; "),
    contractSnapshot: (humanContext.sad_contracts || [])
      .map((item) => item.contract || "")
      .filter(Boolean)
      .join(" / "),
    planPointMatches: (planCorrelation.point_matches || []).slice(0, 12).map((match) => ({
      label: match.display || "",
      action: match.nearest_route?.action_short || "",
      time: match.nearest_route?.arrive_hhmm || "",
      distanceNm: match.distance_nm,
    })),
    deckMentionSlides: (pkg.deck_mentions || []).map((item) => item.slide).filter(Boolean),
    flights: (pkg.flights || []).map((flight) => ({
      callsign: flight.callsign || `Flight ${flight.camp_id || ""}`.trim(),
      team: flight.team || String(flight.owner ?? ""),
      mission: flight.mission || "",
      takeoff: flight.takeoff_hhmm || "",
      tot: flight.tot_hhmm || "",
      targetSummary: flightTargetText(flight),
      route: routeText(flight),
      planSummary: compactText(flight.plan_summary || "", 112),
      contract: flight.human_contract?.contract || "",
      contractIntent: flight.human_contract?.intent || "",
      contractSummary: compactText(flight.contract_summary || flight.human_contract?.contract || flight.targetSummary || "", 120),
      keyWaypoints: flight.key_waypoints || [],
    })),
  };
}

function missionMix(missionCounts) {
  return Object.entries(missionCounts || {})
    .map(([mission, count]) => ({ mission, count: Number(count) || 0 }))
    .sort((left, right) => right.count - left.count || left.mission.localeCompare(right.mission))
    .slice(0, 8);
}

function buildDeckData(synthesis, focusPackageId) {
  const packages = synthesis.packages || [];
  const requestedPackageId = focusPackageId || synthesis.focus_package_id || 2515;
  const focusPackage = packages.find((pkg) => pkg.package_id === requestedPackageId);
  if (!focusPackage) {
    throw new Error(`Package ${requestedPackageId} is not present in the synthesis JSON.`);
  }
  const packageQueue = [focusPackage, ...packages.filter((pkg) => pkg.package_id !== requestedPackageId)];
  const scoredQueue = packages
    .filter((pkg) => pkg.package_id !== requestedPackageId)
    .slice(0, 8)
    .map((pkg) => ({
      packageId: pkg.package_id,
      mission: pkg.mission || "UNKNOWN",
      score: pkg.score || 0,
      flights: pkg.flight_count || 0,
      targets: packageTargetText(pkg, 2),
      kinds: [...new Set((pkg.targets || []).map((target) => target.kind || "unknown"))].join(", ") || "none",
    }));
  const ppts = (synthesis.planning?.ppts || []).slice(0, 16).map((point) => ({
    index: point.index,
    label: point.label,
    radius: point.radius_nm,
  }));
  const dtcTargets = (synthesis.planning?.targets || [])
    .map((point) => String(point.label || "").trim())
    .filter((label) => label && label.toLowerCase() !== "not set");
  const status = synthesis.deck_package_status || {};
  const counts = synthesis.unit_counts || {};
  const objectiveSource = synthesis.objective_source || {};
  const unitSource = synthesis.unit_source || {};
  const stats = [
    { label: "Flights", value: counts.Flight || 0 },
    { label: "Packages", value: counts.Package || 0 },
    { label: "Squadrons", value: counts.Squadron || 0 },
    { label: "Battalions", value: counts.Battalion || 0 },
    { label: "Objective deltas", value: objectiveSource.delta_count || 0 },
    { label: "Objective matches", value: objectiveSource.matched_deltas || 0 },
  ];
  return {
    prefix: synthesis.prefix || "campaign",
    focusPackageId: requestedPackageId,
    generatedAt: new Date().toISOString(),
    clock: synthesis.campaign_clock || {},
    status: {
      mentioned: status.mentioned || [],
      present: status.present_in_cam || [],
      missing: status.missing_from_cam || [],
    },
    stats,
    unitSource,
    missionMix: missionMix(synthesis.mission_counts),
    focusPackage: compactPackage(focusPackage),
    packageQueue: packageQueue.slice(0, 8).map(compactPackage),
    scoredQueue,
    ppts,
    dtcTargets,
  };
}

function commonModule() {
  return String.raw`
export const C = {
  paper: "#F4F0E6",
  paper2: "#ECE5D6",
  ink: "#17211D",
  muted: "#5C635D",
  faint: "#D8CEBB",
  rule: "#B9AA91",
  green: "#5D8B6B",
  greenDark: "#345644",
  red: "#B45345",
  amber: "#C58B2C",
  steel: "#40575A",
  black: "#101512",
  white: "#FFFFFF",
};

export function slideBase(presentation, ctx, opts = {}) {
  const slide = presentation.slides.add();
  const dark = Boolean(opts.dark);
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: dark ? C.black : C.paper });
  ctx.addShape(slide, { x: 0, y: 0, w: 18, h: ctx.H, fill: opts.accent || C.green });
  if (!dark) {
    for (let x = 118; x < ctx.W; x += 118) {
      ctx.addShape(slide, { x, y: 92, w: 1, h: ctx.H - 150, fill: "#E8DFD0" });
    }
  }
  return slide;
}

export function addFooter(slide, ctx, data, text = "Decoded CAM + DTC + reference deck text") {
  addText(slide, ctx, 58, 682, 520, 20, text, { size: 12, color: C.muted });
  addText(slide, ctx, 1125, 682, 95, 20, String(ctx.slideNumber || ""), { size: 12, color: C.muted, align: "right" });
}

export function addText(slide, ctx, x, y, w, h, text, opts = {}) {
  return ctx.addText(slide, {
    x, y, w, h,
    text: text == null ? "" : String(text),
    fontSize: opts.size || 20,
    color: opts.color || C.ink,
    bold: Boolean(opts.bold),
    typeface: opts.face || (opts.mono ? ctx.fonts.mono : ctx.fonts.body),
    align: opts.align || "left",
    valign: opts.valign || "top",
    fill: opts.fill || "#00000000",
    line: opts.line || ctx.line("#00000000", 0),
    insets: opts.insets || { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function kicker(slide, ctx, text, color = C.greenDark) {
  addText(slide, ctx, 58, 46, 400, 24, text.toUpperCase(), { size: 14, color, bold: true });
}

export function title(slide, ctx, text, opts = {}) {
  addText(slide, ctx, 58, opts.y || 78, opts.w || 850, opts.h || 92, text, {
    size: opts.size || 37,
    color: opts.color || C.ink,
    bold: true,
    face: ctx.fonts.title,
  });
}

export function support(slide, ctx, text, opts = {}) {
  addText(slide, ctx, opts.x || 58, opts.y || 185, opts.w || 710, opts.h || 54, text, {
    size: opts.size || 17,
    color: opts.color || C.muted,
  });
}

export function pill(slide, ctx, x, y, w, text, opts = {}) {
  ctx.addShape(slide, { x, y, w, h: 30, fill: opts.fill || C.paper2, line: ctx.line(opts.line || C.rule, 1) });
  addText(slide, ctx, x + 10, y + 7, w - 20, 16, text, { size: 13, color: opts.color || C.ink, bold: Boolean(opts.bold) });
}

export function stat(slide, ctx, x, y, w, label, value, opts = {}) {
  ctx.addShape(slide, { x, y, w, h: 94, fill: opts.fill || C.paper2, line: ctx.line(opts.line || C.rule, 1) });
  addText(slide, ctx, x + 18, y + 18, w - 36, 34, value, { size: 31, color: opts.color || C.ink, bold: true, face: ctx.fonts.title });
  addText(slide, ctx, x + 18, y + 58, w - 36, 20, label, { size: 13, color: C.muted, bold: true });
}

export function table(slide, ctx, spec) {
  const { x, y, columns, rows, rowH = 38, header = [], widths, dark = false } = spec;
  const totalW = widths.reduce((sum, value) => sum + value, 0);
  ctx.addShape(slide, { x, y, w: totalW, h: rowH, fill: dark ? C.greenDark : C.ink, line: ctx.line("#00000000", 0) });
  let cursor = x;
  header.forEach((label, index) => {
    addText(slide, ctx, cursor + 8, y + 9, widths[index] - 16, rowH - 22, label, { size: 12, color: C.white, bold: true });
    cursor += widths[index];
  });
  rows.forEach((row, rowIndex) => {
    const top = y + rowH * (rowIndex + 1);
    const fill = rowIndex % 2 === 0 ? "#FBF7EE" : C.paper2;
    ctx.addShape(slide, { x, y: top, w: totalW, h: rowH, fill, line: ctx.line(C.faint, 1) });
    cursor = x;
    row.forEach((cell, index) => {
      addText(slide, ctx, cursor + 8, top + 6, widths[index] - 16, rowH - 22, cell, {
        size: columns[index]?.size || 14,
        color: columns[index]?.color || C.ink,
        bold: Boolean(columns[index]?.bold),
      });
      cursor += widths[index];
    });
  });
}

export function bar(slide, ctx, x, y, w, label, value, max, opts = {}) {
  const pct = max > 0 ? Math.max(0.04, Math.min(1, value / max)) : 0;
  addText(slide, ctx, x, y, 130, 18, label, { size: 13, color: C.ink, bold: true });
  ctx.addShape(slide, { x: x + 140, y: y + 3, w, h: 14, fill: "#DFD4C2", line: ctx.line("#00000000", 0) });
  ctx.addShape(slide, { x: x + 140, y: y + 3, w: Math.round(w * pct), h: 14, fill: opts.fill || C.green, line: ctx.line("#00000000", 0) });
  addText(slide, ctx, x + 148 + w, y, 48, 18, String(value), { size: 13, color: C.muted, align: "right" });
}

export function noteBox(slide, ctx, x, y, w, h, titleText, body, opts = {}) {
  ctx.addShape(slide, { x, y, w, h, fill: opts.fill || "#FBF7EE", line: ctx.line(opts.line || C.rule, 1) });
  addText(slide, ctx, x + 16, y + 14, w - 32, 20, titleText, { size: 14, color: opts.titleColor || C.ink, bold: true });
  addText(slide, ctx, x + 16, y + 40, w - 32, h - 52, body, { size: opts.size || 14, color: opts.color || C.muted });
}
`;
}

function slide01() {
  return String.raw`
import data from "./deck-data.mjs";
import { C, slideBase, addFooter, addText, kicker, title, support, stat, pill } from "./common.mjs";

export async function slide01(presentation, ctx) {
  const pkg = data.focusPackage;
  const slide = slideBase(presentation, ctx, { dark: true, accent: C.amber });
  kicker(slide, ctx, "Procedural BMS Brief", C.amber);
  title(slide, ctx, data.prefix + " PKG " + pkg.packageId + " is decoded into a commander-facing draft.", { color: C.white, size: 39, w: 720, h: 118 });
  support(slide, ctx, "The CAM container, DTC planning points, objective deltas, package/flight graph, and selected-package waypoints are joined into a repeatable briefing pipeline.", { color: "#C7CBBF", y: 202, w: 720, h: 72, size: 18 });
  pill(slide, ctx, 58, 300, 220, "Mission: " + pkg.mission, { fill: "#22322A", line: "#4D765E", color: C.white, bold: true });
  pill(slide, ctx, 296, 300, 220, "Flights: " + pkg.flightCount, { fill: "#22322A", line: "#4D765E", color: C.white, bold: true });
  pill(slide, ctx, 534, 300, 260, "TOT window: " + (pkg.totWindow || "unknown"), { fill: "#382821", line: C.amber, color: C.white, bold: true });
  const stats = data.stats.slice(0, 6);
  const positions = [[58,382],[268,382],[478,382],[58,500],[268,500],[478,500]];
  stats.forEach((item, index) => stat(slide, ctx, positions[index][0], positions[index][1], 182, item.label, String(item.value), { fill: "#1D2722", line: "#40534A", color: C.white }));
  addText(slide, ctx, 810, 88, 330, 30, "What changed", { size: 20, color: C.amber, bold: true });
  const bullets = [
    "Nested .cam sections are extracted and decoded.",
    "BMSUtils loads teams, packages, flights, squadrons, and ground units.",
    "Waypoints now carry route timing and grid evidence.",
    "This deck is pinned to the requested package, not the generic scorer."
  ];
  bullets.forEach((text, index) => {
    ctx.addShape(slide, { x: 816, y: 142 + index * 66, w: 9, h: 9, fill: index < 2 ? C.green : C.amber, line: ctx.line("#00000000", 0) });
    addText(slide, ctx, 838, 132 + index * 66, 350, 42, text, { size: 16, color: "#D9DDCF" });
  });
  addFooter(slide, ctx, data, "Falcon BMS 4.38 campaign save reverse-engineering");
  return slide;
}
`;
}

function slide02() {
  return String.raw`
import data from "./deck-data.mjs";
import { C, slideBase, addFooter, addText, kicker, title, support, noteBox } from "./common.mjs";

export async function slide02(presentation, ctx) {
  const slide = slideBase(presentation, ctx, { accent: C.green });
  kicker(slide, ctx, "Pipeline");
  title(slide, ctx, "The repeatable path is decode, normalize, score, then brief.");
  support(slide, ctx, "The procedural deck is not treating the human deck as truth. It uses the deck as commander-intent evidence and the local campaign save as the source of force structure and timing.");
  const steps = [
    ["1", "CAM container", "Read directory table; isolate .cmp, .tea, .obd, .uni, and .ver sections."],
    ["2", "BMS decode", "Load BMSUtils in 32-bit PowerShell; decode teams, unit graph, packages, and waypoints."],
    ["3", "Objective join", "Map objective deltas to CampObjData.XML and resolve VU target IDs to flights/units."],
    ["4", "Brief synthesis", "Score packages and correlate INI planning marks to decoded package route points."],
    ["5", "Deck export", "Render editable PowerPoint slides and review PNG previews/contact sheet."],
  ];
  steps.forEach((step, index) => {
    const x = 70 + index * 232;
    const fill = index === 3 ? "#E5DCC8" : "#FBF7EE";
    ctx.addShape(slide, { x, y: 270, w: 188, h: 210, fill, line: ctx.line(index === 3 ? C.amber : C.rule, 1.5) });
    addText(slide, ctx, x + 18, 288, 34, 34, step[0], { size: 27, color: index === 3 ? C.amber : C.greenDark, bold: true, face: ctx.fonts.title });
    addText(slide, ctx, x + 18, 336, 150, 26, step[1], { size: 18, color: C.ink, bold: true });
    addText(slide, ctx, x + 18, 376, 150, 76, step[2], { size: 13.5, color: C.muted });
    if (index < steps.length - 1) {
      ctx.addShape(slide, { x: x + 196, y: 370, w: 22, h: 5, fill: C.green, line: ctx.line("#00000000", 0) });
    }
  });
  noteBox(slide, ctx, 70, 525, 500, 92, "Clock caveat", "HHMM values currently use inferred .cmp base " + (data.clock.clock_base_hhmm || "unknown") + " and campaign time " + (data.clock.campaign_time_ms || "unknown") + ". Validate against BMS UI before calling timing authoritative.");
  noteBox(slide, ctx, 612, 525, 520, 92, "Interpretation caveat", "The human decks summarize commander intent. The save data provides force, target, and timing evidence; the final narrative still needs mission commander judgment.");
  addFooter(slide, ctx, data);
  return slide;
}
`;
}

function slide03() {
  return String.raw`
import data from "./deck-data.mjs";
import { C, slideBase, addFooter, addText, kicker, title, support, table, noteBox, bar } from "./common.mjs";

export async function slide03(presentation, ctx) {
  const pkg = data.focusPackage;
  const slide = slideBase(presentation, ctx, { accent: C.red });
  kicker(slide, ctx, "Package Snapshot", C.red);
  title(slide, ctx, "PKG " + pkg.packageId + " is an INT package with a mixed BARCAP screen.");
  support(slide, ctx, "The requested package is present in the local save. It has no named fixed target, so the useful briefing evidence is role mix, takeoff/TOT flow, and route geometry.");
  const rows = [
    ["Requested PKG", String(pkg.packageId), pkg.mission],
    ["Role mix", pkg.roleMix || "unknown", String(pkg.flightCount) + " flights"],
    ["Takeoff window", pkg.takeoffWindow || "unknown", "base refs pending"],
    ["TOT/on-station", pkg.totWindow || "unknown", "clock inferred"],
    ["Target read", pkg.targetSummary, "airspace/intercept profile"],
    ["INI plan", pkg.planSnapshot, "mission.ini correlated"],
    ["Tasking", pkg.contractSnapshot || "contracts pending", pkg.routeName || "Route Black"],
    ["CAP split", pkg.capContractSnapshot || "CAP split pending", "BARCAP screen"],
  ];
  table(slide, ctx, {
    x: 70, y: 260,
    widths: [170, 260, 250],
    columns: [{ bold: true }, {}, {}],
    header: ["Field", "Decoded value", "Briefing read"],
    rows,
    rowH: 34,
  });
  noteBox(slide, ctx, 790, 260, 350, 100, "INT interpretation", "Mudhen holds Guardpost west; Cobra holds BARRIER east. ROK INT flights push into Route Black.", { line: C.red });
  noteBox(slide, ctx, 790, 392, 350, 98, "Known caveat", "Aircraft type, loadout, and airbase names are not fully resolved yet. The timing/grid picture is decoded from the save.", { line: C.amber });
  const max = Math.max(...data.missionMix.map((item) => item.count), 1);
  addText(slide, ctx, 790, 526, 300, 22, "Mission mix in local CAM", { size: 18, color: C.ink, bold: true });
  data.missionMix.slice(0, 5).forEach((item, index) => bar(slide, ctx, 790, 562 + index * 24, 220, item.mission, item.count, max, { fill: index === 0 ? C.red : C.green }));
  addFooter(slide, ctx, data, "Requested package resolved from local CAM synthesis");
  return slide;
}
`;
}

function slide04() {
  return String.raw`
import data from "./deck-data.mjs";
import { C, slideBase, addFooter, addText, kicker, title, support, table, noteBox, pill } from "./common.mjs";

export async function slide04(presentation, ctx) {
  const pkg = data.focusPackage;
  const slide = slideBase(presentation, ctx, { accent: C.green });
  kicker(slide, ctx, "Package Coordination");
  title(slide, ctx, "PKG " + pkg.packageId + " coordination centers on five flights.");
  support(slide, ctx, pkg.mission + " package, " + pkg.flightCount + " flights. Role mix: " + (pkg.roleMix || "unknown") + ". Target evidence: " + (pkg.targetSummary || "none") + ".");
  pill(slide, ctx, 70, 246, 185, "Mission: " + pkg.mission, { bold: true, fill: "#E6EEDC", line: C.green });
  pill(slide, ctx, 276, 246, 250, "Role mix: " + (pkg.roleMix || "unknown"), { bold: true });
  pill(slide, ctx, 548, 246, 250, "TOT: " + (pkg.totWindow || "unknown"), { bold: true, fill: "#F3E3C6", line: C.amber });
  table(slide, ctx, {
    x: 70, y: 310,
    widths: [150, 100, 138, 70, 70, 412],
    columns: [{ bold: true }, {}, { bold: true }, {}, {}, { size: 12.6 }],
    header: ["Callsign", "Team", "Role", "T/O", "TOT", "Contract / target read"],
    rows: (pkg?.flights || []).map((flight) => [flight.callsign, flight.team, flight.mission, flight.takeoff, flight.tot, flight.contractSummary || flight.targetSummary]),
    rowH: 44,
  });
  noteBox(slide, ctx, 70, 585, 446, 84, "Procedural read", "Callsign, coalition, role, T/O, and TOT are decoded directly from package membership and flight waypoints.", { line: C.green, size: 12.5 });
  noteBox(slide, ctx, 548, 585, 454, 84, "Human layer", [pkg.contractText, pkg.capContractText].filter(Boolean).join(" | ") || "Commander intent should set commit criteria, abort criteria, threat response, and package lead responsibilities.", { line: C.amber, size: 12.5 });
  addFooter(slide, ctx, data);
  return slide;
}
`;
}

function slide05() {
  return String.raw`
import data from "./deck-data.mjs";
import { C, slideBase, addFooter, addText, kicker, title, support, table, noteBox } from "./common.mjs";

export async function slide05(presentation, ctx) {
  const pkg = data.focusPackage;
  const slide = slideBase(presentation, ctx, { accent: C.steel });
  kicker(slide, ctx, "Route And Timing", C.steel);
  title(slide, ctx, (pkg.routeName || "Route Black") + " turns INI marks into target logic.");
  support(slide, ctx, "Package " + pkg.packageId + " has no fixed target ID, so mission.ini geometry plus commander context defines search lanes, target opportunities, and fallback targeting.");
  table(slide, ctx, {
    x: 70, y: 242,
    widths: [122, 82, 58, 58, 420, 312],
    columns: [{ bold: true }, { bold: true }, {}, {}, { size: 10.8 }, { size: 10.8 }],
    header: ["Callsign", "Role", "T/O", "TOT", "Decoded route", "Nearest INI plan marks"],
    rows: (pkg?.flights || []).map((flight) => [flight.callsign, flight.mission, flight.takeoff, flight.tot, flight.route || "No route actions decoded", flight.planSummary || "No close INI marks"]),
    rowH: 52,
  });
  noteBox(slide, ctx, 70, 572, 510, 86, "Commander context", pkg.briefingReadShort || pkg.planInterpretation || "No close INI planning correlation decoded.", { line: C.steel, size: 12.2 });
  noteBox(slide, ctx, 610, 572, 442, 86, "Targets and fallback", pkg.targetOpportunityShort || pkg.fallbackShort || pkg.planLineSummary || "No target-opportunity context supplied.", { line: C.green, size: 12.2 });
  addFooter(slide, ctx, data);
  return slide;
}
`;
}

function slide06() {
  return String.raw`
import data from "./deck-data.mjs";
import { C, slideBase, addFooter, addText, kicker, title, support, table, noteBox } from "./common.mjs";

export async function slide06(presentation, ctx) {
  const pkg = data.focusPackage;
  const slide = slideBase(presentation, ctx, { accent: C.red });
  kicker(slide, ctx, "Target Area Threats", C.red);
  title(slide, ctx, "Route Black now carries a saved-campaign threat estimate.");
  support(slide, ctx, pkg.enemySummary || "Enemy situation was not available in the synthesis JSON.", { w: 900, h: 42, size: 14.5 });
  const adRows = (pkg.airDefenses || []).slice(0, 7).map((unit) => [
    String(unit.id || ""),
    unit.className,
    unit.equipment,
    unit.grid,
    unit.anchor,
    String(unit.distanceNm ?? ""),
    unit.range || "",
  ]);
  table(slide, ctx, {
    x: 58, y: 254,
    widths: [62, 118, 268, 82, 238, 72, 74],
    columns: [{ bold: true }, { bold: true }, { size: 11 }, { size: 11 }, { size: 10.5 }, {}, {}],
    header: ["ID", "Class", "Equipment", "Grid", "Nearest anchor", "Dist", "Air/low"],
    rows: adRows,
    rowH: 34,
  });
  const airbaseRows = (pkg.airbases || []).slice(0, 4).map((base) => [
    base.name || String(base.id || ""),
    String(base.activeSquadrons || ""),
    base.aircraft,
    base.grid,
    String(base.distanceNm ?? ""),
    base.status,
  ]);
  table(slide, ctx, {
    x: 58, y: 548,
    widths: [178, 58, 236, 82, 58, 116],
    columns: [{ bold: true, size: 11.5 }, {}, { size: 10.5 }, { size: 11 }, {}, { size: 10.2 }],
    header: ["Airbase", "Sqns", "Aircraft/classes", "Grid", "Dist", "Status"],
    rows: airbaseRows,
    rowH: 26,
  });
  noteBox(slide, ctx, 816, 548, 300, 112, "Confidence caveat", "Airbase rows require an active enemy squadron, an airbase/airstrip objective, and no decoded fully-destroyed base state. Emitter and runway usability still need deeper validation.", { line: C.amber, size: 12.1 });
  addFooter(slide, ctx, data, "Threat estimate from CAM battalions, squadrons, objectives + Falcon object tables");
  return slide;
}
`;
}

function slide07() {
  return String.raw`
import data from "./deck-data.mjs";
import { C, slideBase, addFooter, addText, kicker, title, support, table, bar } from "./common.mjs";

export async function slide07(presentation, ctx) {
  const slide = slideBase(presentation, ctx, { accent: C.amber });
  kicker(slide, ctx, "Package Queue", C.amber);
  title(slide, ctx, "The scorer still surfaces nearby work after the requested package.");
  support(slide, ctx, "Package " + data.focusPackageId + " is pinned by request. The queue below shows what the generic mission scorer would surface next using mission type, package breadth, and resolved tactical targets.");
  const rows = data.scoredQueue.map((pkg) => [String(pkg.packageId), pkg.mission, String(pkg.score), String(pkg.flights), pkg.targets, pkg.kinds]);
  table(slide, ctx, {
    x: 70, y: 250,
    widths: [76, 120, 70, 70, 405, 160],
    columns: [{ bold: true }, { bold: true }, {}, {}, { size: 12.5 }, { size: 12.5 }],
    header: ["PKG", "Mission", "Score", "Flights", "Resolved target read", "Target kind"],
    rows,
    rowH: 38,
  });
  const max = Math.max(...data.scoredQueue.map((pkg) => pkg.score), 1);
  addText(slide, ctx, 1000, 250, 190, 20, "Top scores", { size: 16, color: C.ink, bold: true });
  data.scoredQueue.slice(0, 4).forEach((pkg, index) => bar(slide, ctx, 1000, 286 + index * 28, 80, "PKG " + pkg.packageId, pkg.score, max, { fill: index === 0 ? C.amber : C.green }));
  addFooter(slide, ctx, data);
  return slide;
}
`;
}

function slide08() {
  return String.raw`
import data from "./deck-data.mjs";
import { C, slideBase, addFooter, addText, kicker, title, support, noteBox, stat } from "./common.mjs";

export async function slide08(presentation, ctx) {
  const slide = slideBase(presentation, ctx, { accent: C.greenDark });
  kicker(slide, ctx, "Next Decoder Layer");
  title(slide, ctx, "The system can draft the brief; the next lift is richer mission semantics.");
  support(slide, ctx, "This pass proves the campaign-save path. The next improvements should target the fields human briefer slides care about but the first decoder does not yet expose.");
  const done = [
    ["CAM", "Sections and version decoded"],
    ["Teams", "Coalition names loaded"],
    [(data.unitSource.numeric_unit_refs || 0) + " VU", "Unit refs indexed"],
    ["Targets", "Objectives, flights, battalions resolved"],
  ];
  done.forEach((item, index) => {
    const x = 70 + index * 230;
    ctx.addShape(slide, { x, y: 250, w: 190, h: 112, fill: "#FBF7EE", line: ctx.line(C.green, 1) });
    addText(slide, ctx, x + 18, 274, 154, 32, item[0], { size: 27, color: C.greenDark, bold: true, face: ctx.fonts.title });
    addText(slide, ctx, x + 18, 318, 154, 26, item[1], { size: 13, color: C.muted, bold: true });
  });
  noteBox(slide, ctx, 70, 414, 305, 122, "1. Aircraft and loadouts", "Join class-table IDs, aircraft stores, and squadron data so coordination tables can include aircraft type, role fit, weapons, and threats.", { line: C.amber });
  noteBox(slide, ctx, 405, 414, 305, 122, "2. Threat refinement", "Join objective/facility status and live-sim state so the threat slide can distinguish possible defenses from active emitters and damaged sites.", { line: C.red });
  noteBox(slide, ctx, 740, 414, 305, 122, "3. Commander intent", "Use reference-deck structure as style/intent training data, while keeping CAM facts as the auditable source of truth.", { line: C.green });
  addText(slide, ctx, 70, 590, 865, 50, "Current output: briefing_data.json -> cam_decode.json -> briefing_synthesis.json -> generated briefing Markdown + editable PPTX.", { size: 17, color: C.ink, bold: true });
  addFooter(slide, ctx, data);
  return slide;
}
`;
}

function slideModules() {
  return [
    ["slide-01.mjs", slide01()],
    ["slide-02.mjs", slide02()],
    ["slide-03.mjs", slide03()],
    ["slide-04.mjs", slide04()],
    ["slide-05.mjs", slide05()],
    ["slide-06.mjs", slide06()],
    ["slide-07.mjs", slide07()],
    ["slide-08.mjs", slide08()],
  ];
}

async function writeNotes(workspace, deckData, synthesisPath) {
  const hasDeckSignals = (deckData.status.mentioned || []).length > 0;
  await fs.writeFile(
    path.join(workspace, "profile-plan.txt"),
    [
      "task mode: create",
      "primary deck-profile: engineering-platform",
      "secondary gates: appendix-heavy/source-density discipline for decoded package tables",
      "required proof objects: CAM decode pipeline, requested package snapshot, package coordination tables, route/timing table, target-area threat estimate, scorer queue, next decoder roadmap",
      "source/asset requirements: local BMS campaign save, CampObjData.XML" + (hasDeckSignals ? ", Google Slides text extraction" : "") + "; no external identity assets used",
      "brand authenticity constraints: no unofficial logos or pseudo-BMS marks created",
      "profile-specific QA gates: technical labels must stay precise; tables must remain legible; no connector ambiguity",
      "known missing inputs: aircraft/loadout resolution, active emitter state, objective/facility damage, and BMS UI clock validation",
    ].join("\n") + "\n",
    "utf8",
  );
  await fs.writeFile(
    path.join(workspace, "source-notes.txt"),
    [
      `synthesis: ${path.resolve(synthesisPath)}`,
      `prefix: ${deckData.prefix}`,
      `focus package: ${deckData.focusPackageId}`,
      `generated: ${deckData.generatedAt}`,
      "source provenance: local Falcon BMS 4.38 campaign files" + (hasDeckSignals ? " plus Google Slides text exported by extract_bms_briefing.py" : ""),
      "identity assets: none embedded",
    ].join("\n") + "\n",
    "utf8",
  );
  await fs.writeFile(
    path.join(workspace, "reference-audit.txt"),
    [
      "reference source: " + (hasDeckSignals ? "Google Slides text supplied through extraction" : "no reference deck supplied for this package run"),
      "source handling: " + (hasDeckSignals ? "deck text was fetched through htmlpresent and used for package mention detection" : "local CAM and sidecars drive the package-specific briefing"),
      "visual target: human military briefing rhythm, not a cloned template",
      "anti-pattern avoided: treating absent or unresolved IDs as confirmed local package facts",
    ].join("\n") + "\n",
    "utf8",
  );
  await fs.writeFile(
    path.join(workspace, "qa", "comeback-scorecard.txt"),
    [
      "story: 4 - clear source-to-brief arc",
      "specificity: 5 - BMS package IDs, callsigns, and targets are concrete",
      "rhythm: 4 - cover, pipeline, matrix, tables, threat estimate, queue, roadmap",
      "whitespace: 4 - dense but readable mission-planning style",
      "chart clarity: 4 - scorer bars and tables have direct labels",
      "typography: 4 - consistent tactical editorial system",
      "restraint: 5 - no decorative logos or filler art",
      "precision: 4 - source caveats explicitly labeled",
      "coherence: 4 - unified palette and table grammar",
      "reference delta: 3 - procedural draft is cleaner than raw extraction, not yet a full human target-file deck",
    ].join("\n") + "\n",
    "utf8",
  );
}

async function main() {
  if (process.argv.includes("--help") || process.argv.includes("-h")) {
    printHelp();
    return;
  }
  console.warn(
    "Deprecated fallback: build_bms_briefing_deck.mjs is no longer the supported deck-production path. " +
      "Use scripts/export_claude_design_bundle.py and the Claude design bundle workflow instead.",
  );
  const args = parseArgs(process.argv.slice(2));
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const repoRoot = path.resolve(scriptDir, "..");
  const synthesisPath = path.resolve(args.synthesis || path.join(repoRoot, "outputs", "718pre", "briefing_synthesis.json"));
  const synthesis = JSON.parse(await fs.readFile(synthesisPath, "utf8"));
  const packageId = args["package-id"] ? Number.parseInt(args["package-id"], 10) : undefined;
  const deckData = buildDeckData(synthesis, packageId);
  const prefixSlug = slug(deckData.prefix);
  const packageSlug = `pkg-${deckData.focusPackageId}`;
  const outDir = path.resolve(args["out-dir"] || path.join(repoRoot, "outputs", deckData.prefix));
  const outPath = path.resolve(args.out || path.join(outDir, `procedural-bms-${prefixSlug}-${packageSlug}-briefing.pptx`));
  const threadId = process.env.CODEX_THREAD_ID || timestampId();
  const workspace = path.resolve(args.workspace || path.join(repoRoot, "outputs", threadId, "presentations", `bms-${prefixSlug}-${packageSlug}-briefing`));
  const skillDir = path.resolve(args["skill-dir"] || process.env.PRESENTATIONS_SKILL_DIR || defaultSkillDir());
  const slidesDir = path.join(workspace, "slides");
  const previewDir = path.join(workspace, "preview");
  const layoutDir = path.join(workspace, "layout", "final");
  const qaDir = path.join(workspace, "qa");

  await fs.mkdir(slidesDir, { recursive: true });
  await fs.mkdir(previewDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });
  await fs.mkdir(qaDir, { recursive: true });
  await fs.mkdir(outDir, { recursive: true });

  await fs.writeFile(path.join(slidesDir, "common.mjs"), commonModule(), "utf8");
  await fs.writeFile(path.join(slidesDir, "deck-data.mjs"), `export default ${JSON.stringify(deckData, null, 2)};\n`, "utf8");
  for (const [fileName, contents] of slideModules()) {
    await fs.writeFile(path.join(slidesDir, fileName), contents, "utf8");
  }
  await fs.writeFile(path.join(workspace, "data.json"), `${JSON.stringify(deckData, null, 2)}\n`, "utf8");
  await writeNotes(workspace, deckData, synthesisPath);

  const builder = path.join(skillDir, "scripts", "build_artifact_deck.mjs");
  const build = spawnSync(
    process.execPath,
    [
      builder,
      "--workspace", workspace,
      "--slides-dir", slidesDir,
      "--out", outPath,
      "--preview-dir", previewDir,
      "--layout-dir", layoutDir,
      "--contact-sheet", path.join(previewDir, "contact-sheet.png"),
      "--manifest", path.join(outDir, "procedural-bms-briefing-manifest.json"),
      "--slide-count", "8",
      "--scale", "1",
    ],
    {
      cwd: repoRoot,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: process.env.USERPROFILE || process.env.HOME,
        USERPROFILE: process.env.USERPROFILE || process.env.HOME,
        PYTHON: process.env.PYTHON || "python",
      },
    },
  );

  if (build.status !== 0) {
    throw new Error([build.stdout.trim(), build.stderr.trim()].filter(Boolean).join("\n"));
  }

  const manifest = JSON.parse(await fs.readFile(path.join(outDir, "procedural-bms-briefing-manifest.json"), "utf8"));
  console.log(JSON.stringify({
    output: outPath,
    workspace,
    previewDir,
    contactSheet: manifest.contactSheet,
    slideCount: manifest.slideCount,
    outputBytes: manifest.outputBytes,
  }, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
