// Character creation and derived numbers for Breath and the Veil.
// Pure functions: no Foundry globals. Node tests import this file directly.
// Hidden stats are never copied onto an actor.

export const ATTRIBUTES = ["strength", "toughness", "agility", "mobility", "dexterity", "endurance",
  "intelligence", "willpower", "perception", "charisma", "weapon_skill", "ballistic_skill"];

export const HIDDEN_STAT = /^(faith|virtue|piety|holy_?fury\w*|corruption\w*|stress\w*|reputation\w*)$/i;

const LEGACY_CLASS_SCALE = 3; // matches scripts/character_loader.py
const SYS = "systems/breath-and-the-veil";

export function isHiddenStat(key) {
  return HIDDEN_STAT.test(String(key));
}

export function omitHidden(node) {
  if (Array.isArray(node)) return node.map(omitHidden).filter((v) => !(typeof v === "string" && HIDDEN_STAT.test(v)));
  if (node && typeof node === "object") {
    const out = {};
    for (const [k, v] of Object.entries(node)) {
      if (HIDDEN_STAT.test(k) || k === "hidden" || k === "hidden_start") continue;
      out[k] = omitHidden(v);
    }
    return out;
  }
  return node;
}

function asList(value) {
  if (value == null || value === "") return [];
  if (Array.isArray(value)) return value.filter((x) => x != null && x !== "");
  return [value];
}

function eq(a, b) {
  return String(a || "").trim().toLowerCase() === String(b || "").trim().toLowerCase();
}

function itemRules(item) {
  return (item && (item.system?.rules || item.rules)) || {};
}

export function playableGenders(raceItem) {
  const listed = asList(itemRules(raceItem).playable_genders);
  return listed.length ? listed : null;
}

export function classLocks(classItem) {
  const r = itemRules(classItem);
  const sys = classItem?.system || {};
  const rest = r.restrictions || {};
  return {
    races: asList(sys.allowed_races?.length ? sys.allowed_races : (r.allowed_races || r.race_lock || rest.race || rest.races)),
    genders: asList(sys.allowed_genders?.length ? sys.allowed_genders : (r.allowed_genders || r.gender_lock || rest.gender || rest.genders)),
  };
}

export function canAssign({ race, gender, classItem, raceItem } = {}) {
  const reasons = [];
  if (race && gender && raceItem) {
    const allowed = playableGenders(raceItem);
    if (allowed && !allowed.some((g) => eq(g, gender))) {
      reasons.push(`${race} is ${allowed.join("/")} only.`);
    }
  }
  if (classItem) {
    const locks = classLocks(classItem);
    const cname = classItem.name || classItem.system?.source_id || "This class";
    if (race && locks.races.length && !locks.races.some((r) => eq(r, race))) {
      reasons.push(`${cname} is for ${locks.races.join(", ")} only.`);
    }
    if (gender && locks.genders.length && !locks.genders.some((g) => eq(g, gender))) {
      reasons.push(`${cname} is for ${locks.genders.join(", ")} only.`);
    }
  }
  return { ok: reasons.length === 0, reasons };
}

export function classStatBonuses(rules = {}) {
  const out = {};
  const mods = rules.stat_modifiers;
  if (mods && typeof mods === "object") {
    for (const [k, v] of Object.entries(mods)) {
      if (ATTRIBUTES.includes(k) && typeof v === "number") out[k] = (out[k] || 0) + v;
    }
    return out;
  }
  for (const [k, v] of Object.entries(rules.stats || {})) {
    if (k.endsWith("_modifier") && typeof v === "number") {
      const stat = k.slice(0, -"_modifier".length);
      if (ATTRIBUTES.includes(stat)) out[stat] = (out[stat] || 0) + v * LEGACY_CLASS_SCALE;
    }
  }
  return out;
}

export function classHpPercent(rules = {}) {
  const a = rules.stat_modifiers?.hp_percent;
  const b = rules.stats?.hp_percent_bonus;
  return Number(a ?? b ?? 0) || 0;
}

export function computeHp({ raceHpBonus = 0, classHpPercent = 0 } = {}) {
  // scripts/zone_hp.hp_multiplier, then a single total (zone split is combat work).
  const multiplier = (1 + (raceHpBonus || 0) / 100) * (1 + (classHpPercent || 0) / 100);
  return Math.round(100 * multiplier);
}

export function computeStamina({ raceBonus = 0, classFlat = 0 } = {}) {
  // Inferred from the rules fields (the Python loader currently leaves file max_stamina at 100).
  return 100 + (raceBonus || 0) + (classFlat || 0);
}

export function carryCapacity({ strength = 0, gender = "", race = "", talents = [] } = {}) {
  const sex = String(gender).toLowerCase().startsWith("m") ? 1.15 : 1.0;
  const raceKey = String(race || "").trim();
  const raceMult = raceKey.toLowerCase() === "dwarf" ? 1.5 : raceKey.toLowerCase() === "ogre" ? 3.0 : 1.0;
  const names = new Set((talents || []).map((t) => String(t).toLowerCase().replace(/\s+/g, "_")));
  const talentMult = names.has("ox_back") || names.has("ox-back") ? 1.15 : 1.0;
  return (20 + Number(strength || 0) * 1.5) * sex * raceMult * talentMult;
}

export function portraitPath(race, gender, { exists } = {}) {
  const fallback = `${SYS}/assets/portraits/_fallback.webp`;
  if (!race || !gender) return fallback;
  const specific = `${SYS}/assets/portraits/${String(race).toLowerCase()}-${String(gender).toLowerCase()}.webp`;
  if (typeof exists === "function") return exists(specific) ? specific : fallback;
  return { preferred: specific, fallback };
}

export function classIconPath(classId, { exists } = {}) {
  const fallback = `${SYS}/assets/icons/classes/_fallback.webp`;
  const id = String(classId || "").toLowerCase().replace(/\s+/g, "_");
  if (!id) return fallback;
  const specific = `${SYS}/assets/icons/classes/${id}.webp`;
  if (typeof exists === "function") return exists(specific) ? specific : fallback;
  return { preferred: specific, fallback };
}

export function startingSkills(classItem) {
  const skills = itemRules(classItem).skills || {};
  return Object.entries(skills)
    .filter(([k]) => !isHiddenStat(k))
    .map(([id, rank]) => ({ source_id: id, rank: typeof rank === "number" ? rank : 0 }));
}

export function grantedFeatures(raceItem, classItem) {
  const features = [];
  for (const a of asList(itemRules(raceItem).abilities)) {
    if (a && typeof a === "object") features.push({ source: "race", name: a.name || "Ability", text: a.description || "" });
    else if (a) features.push({ source: "race", name: String(a), text: "" });
  }
  for (const t of asList(itemRules(classItem).traits)) {
    if (t && typeof t === "object") features.push({ source: "class", name: t.name || "Trait", text: t.description || t.effect || "" });
    else if (t) features.push({ source: "class", name: String(t), text: "" });
  }
  // Tier-1 abilities (the ones a starting character actually has).
  const progression = asList(itemRules(classItem).progression);
  const tier1 = progression.find((p) => p && p.tier === 1) || progression[0];
  const gained = asList(tier1?.abilities_gain);
  const abilities = itemRules(classItem).abilities || {};
  for (const id of gained) {
    const info = abilities[id] || {};
    features.push({
      source: "class",
      name: String(id).replace(/_/g, " "),
      text: info.effect || info.note || info.type || "",
    });
  }
  return features;
}

export function computeCharacter({ raceItem, genderItem, classItem, talents = [] } = {}) {
  const race = raceItem?.system?.source_id || raceItem?.name || genderItem?.system?.race || "";
  const gender = genderItem?.system?.gender || "";
  const className = classItem?.system?.source_id || classItem?.name || "";
  const check = canAssign({ race, gender, classItem, raceItem });
  const genderRules = itemRules(genderItem);
  const starting = omitHidden(genderRules.starting_stats || {});
  const maxes = omitHidden(genderRules.max_stats || {});
  const bonuses = classStatBonuses(itemRules(classItem));
  const attributes = {};
  for (const key of ATTRIBUTES) {
    const cap = Number(maxes[key] ?? 100);
    const raw = Number(starting[key] ?? 30) + Number(bonuses[key] ?? 0);
    attributes[key] = { value: Math.min(raw, cap), max: cap };
  }
  const raceRules = itemRules(raceItem);
  const hpMax = computeHp({
    raceHpBonus: raceRules.stats?.hp_bonus || 0,
    classHpPercent: classHpPercent(itemRules(classItem)),
  });
  const staMax = computeStamina({
    raceBonus: raceRules.stats?.stamina_bonus || 0,
    classFlat: itemRules(classItem).stat_modifiers?.stamina_max_flat || 0,
  });
  const mass = Number(raceRules.mass || 0);
  const capacity = carryCapacity({
    strength: attributes.strength.value,
    gender,
    race,
    talents,
  });
  return {
    ok: check.ok,
    reasons: check.reasons,
    details: { race, gender, class_name: className, mass },
    attributes,
    resources: {
      hp: { value: hpMax, max: hpMax },
      stamina: { value: staMax, max: staMax },
    },
    inventory: { carry_capacity: capacity },
    skills: startingSkills(classItem),
    features: grantedFeatures(raceItem, classItem),
  };
}

function prettyReq(node) {
  if (node == null) return [];
  if (typeof node !== "object") return [String(node)];
  const out = [];
  for (const [k, v] of Object.entries(omitHidden(node))) {
    if (v && typeof v === "object" && !Array.isArray(v)) {
      out.push(`${k}: ${Object.entries(v).map(([a, b]) => `${a} ${b}`).join(", ")}`);
    } else if (Array.isArray(v)) out.push(`${k}: ${v.join(", ")}`);
    else if (typeof v === "boolean") { if (v) out.push(k.replace(/_/g, " ")); }
    else out.push(`${k.replace(/_/g, " ")}: ${v}`);
  }
  return out;
}

export function classPageView(classItem) {
  const r = omitHidden(itemRules(classItem));
  const locks = classLocks(classItem);
  const progression = asList(r.progression).map((tier) => ({
    tier: tier.tier,
    name: tier.name,
    abilities: asList(tier.abilities_gain).map((id) => String(id).replace(/_/g, " ")),
    pathAbilities: tier.abilities_gain_by_path || {},
    skillTrees: asList(tier.skill_tree_choice),
    requirements: prettyReq(tier.requirements),
  }));
  const career = r.career || {};
  const evolutions = asList(career.evolutions).map((e) => ({
    id: e.id,
    name: e.name,
    description: e.description || "",
    requires: prettyReq(e.requires),
    gains: e.gains || {},
    placeholder: Boolean(e.placeholder),
  }));
  const path = r.order_path || {};
  const ranks = asList(path.ranks).map((rank) => ({
    rank: rank.rank,
    name: rank.name,
    requires: prettyReq(rank.requires),
    gives: asList(rank.gives),
    costs: asList(rank.costs),
  }));
  const honours = Object.entries(path.honours || {}).map(([id, h]) => ({
    id,
    name: h.name || id,
    kind: h.kind || "",
    description: h.why_rank_2 || h.replaces || "",
    min_rank: h.min_rank,
    requires: prettyReq(h.requires),
    gives: asList(h.gives),
  }));
  const skills = startingSkills(classItem);
  const trees = Object.entries(r.skill_trees || {}).map(([id, info]) => ({
    id,
    name: id.replace(/_/g, " "),
    focus: info?.focus || "",
    mastery: info?.mastery_bonus || "",
  }));
  return {
    name: classItem?.name || r.label || "",
    description: classItem?.system?.description || "",
    locks,
    powerSource: r.power_source || "",
    obligations: r.obligations || null,
    proficiencies: r.proficiencies || null,
    progression,
    skills,
    trees,
    stay: career.stay || "",
    onHold: Boolean(career.on_hold),
    evolutions,
    pathName: path.name || "",
    ranks,
    honours,
    flaws: Object.entries(r.flaws || {}).map(([id, info]) => ({
      id,
      name: (info && info.name) || id.replace(/_/g, " "),
      text: (info && (info.effect || info.description || info.type)) || "",
    })),
  };
}

export function actorSystemPatch(computed) {
  return {
    "system.details.race": computed.details.race,
    "system.details.gender": computed.details.gender,
    "system.details.class_name": computed.details.class_name,
    "system.details.mass": computed.details.mass,
    "system.attributes": computed.attributes,
    "system.resources.hp": computed.resources.hp,
    "system.resources.stamina": computed.resources.stamina,
    "system.inventory.carry_capacity": computed.inventory.carry_capacity,
  };
}

/** Carry-weight preview until workstream B owns the live sum. Physical items only. */
export function sumCarriedWeight(items = []) {
  let total = 0;
  for (const it of items) {
    const type = it.type || "";
    if (type !== "weapon" && type !== "armor" && type !== "gear") continue;
    const w = it.system?.weight ?? it.weight ?? 0;
    const n = Number(w);
    if (!Number.isNaN(n)) total += n;
  }
  return total;
}
