// Breath and the Veil — inventory and carried load (version 0.3).
// Pure functions here are safe to unit-test in Node. Foundry hooks live at the bottom
// and only run when Hooks exists. Hidden stats are not used.
import RULES from "./inventory-rules.mjs";

const ID = "breath-and-the-veil";
const PHYSICAL = new Set(RULES.physical_item_types);
const NON_PHYSICAL = new Set(RULES.non_physical_item_types);
const MARCH_CLIFF_START = 0.5;

export { RULES };

const breathFlags = (item) => {
  const flags = item?.flags?.[ID] || item?.flags?.breath || {};
  return flags;
};

export function itemType(item) {
  return String(item?.type || "");
}

export function itemId(item) {
  return String(item?.id || item?._id || item?.source_id || item?.system?.source_id || item?.name || "");
}

export function itemName(item) {
  return String(item?.name || itemId(item) || "item");
}

export function itemFlag(item, key, fallback = undefined) {
  const flags = breathFlags(item);
  const camel = { container_id: "containerId", is_container: "isContainer", capacity_kg: "capacityKg",
    capacity_volume: "capacityVolume" }[key] || key;
  if (flags[key] !== undefined) return flags[key];
  if (flags[camel] !== undefined) return flags[camel];
  const system = item?.system || {};
  if (item && item[key] !== undefined) return item[key];
  if (system[key] !== undefined) return system[key];
  if (system[camel] !== undefined) return system[camel];
  const rules = system.rules || item?.rules || {};
  if (rules[key] !== undefined) return rules[key];
  if (rules[camel] !== undefined) return rules[camel];
  return fallback;
}

export function itemWeight(item) {
  const raw = itemFlag(item, "weight", item?.system?.weight);
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

export function isPhysical(item) {
  return PHYSICAL.has(itemType(item));
}

export function isContainer(item) {
  if (itemFlag(item, "is_container") || itemFlag(item, "isContainer")) return true;
  const cap = itemFlag(item, "capacity_kg", itemFlag(item, "capacityKg"));
  return cap != null && Number(cap) > 0 && itemType(item) === "gear";
}

export function containerCapacityKg(item) {
  const cap = itemFlag(item, "capacity_kg", itemFlag(item, "capacityKg"));
  const n = Number(cap);
  return Number.isFinite(n) ? n : 0;
}

export function locationOf(item) {
  const system = item?.system || {};
  if (system.location) return String(system.location);
  const loc = itemFlag(item, "location");
  if (loc) return String(loc);
  if (itemFlag(item, "equipped") || system.equipped) return "body";
  return "";
}

export function sourceId(item) {
  return String(item?.system?.source_id || item?.source_id || item?.id || "");
}

export function coverageOf(item) {
  const cov = item?.system?.coverage || item?.coverage || [];
  return Array.isArray(cov) ? [...cov] : [];
}

export function raceMultiplier(race) {
  const key = String(race || "").trim() || "Human";
  return Number(RULES.carry_capacity.race_multipliers[key] ?? 1);
}

export function talentMultiplier(talents = []) {
  let mult = 1;
  const names = new Set((talents || []).map((t) => String(t).toLowerCase()));
  for (const [talent, value] of Object.entries(RULES.carry_capacity.talent_multipliers)) {
    if (names.has(talent.toLowerCase())) mult *= Number(value);
  }
  return mult;
}

export function carryCapacity(strength, gender, race = "Human", talents = []) {
  const sexm = String(gender || "").toLowerCase().startsWith("m")
    ? RULES.carry_capacity.male_multiplier
    : RULES.carry_capacity.female_multiplier;
  const base = (RULES.carry_capacity.base + Number(strength) * RULES.carry_capacity.per_strength) * sexm;
  return base * raceMultiplier(race) * talentMultiplier(talents);
}

export function isTwoHanded(item, grip = "two_hands") {
  if (itemType(item) !== "weapon") return false;
  const sid = sourceId(item);
  const wtype = String(item?.system?.weapon_type || item?.weapon_type || "");
  const cfg = RULES.two_handed;
  if (sid === "longsword") return String(grip).toLowerCase() !== "one_hand";
  if (cfg.type_prefixes.some((p) => wtype.startsWith(p))) return true;
  if (cfg.assumed_types.includes(wtype)) return true;
  if (cfg.assumed_source_ids.includes(sid)) return true;
  return false;
}

export function bodySlotsFor(item, grip = "two_hands") {
  const typ = itemType(item);
  if (typ === "armor") return coverageOf(item);
  if (typ === "weapon") return isTwoHanded(item, grip) ? ["main_hand", "off_hand"] : ["main_hand"];
  if (typ === "gear") {
    const slot = itemFlag(item, "slot") || item?.slot || "";
    return slot ? [slot] : [];
  }
  return [];
}

export function occupiedBodySlots(items, excludingId = null, grip = "two_hands") {
  const taken = {};
  for (const it of items) {
    if (!isPhysical(it)) continue;
    if (excludingId && itemId(it) === excludingId) continue;
    if (locationOf(it) !== "body") continue;
    for (const slot of bodySlotsFor(it, grip)) taken[slot] = itemId(it);
  }
  return taken;
}

export function containerIdOf(item) {
  return String(item?.system?.container_id || itemFlag(item, "container_id") || "");
}

export function contentsWeight(container, items) {
  const cid = itemId(container);
  let total = 0;
  for (const it of items) {
    if (locationOf(it) === "backpack" && containerIdOf(it) === cid) {
      total += itemWeight(it);
    }
  }
  return total;
}

export function carriedWeight(items, clinchMassKg = 0) {
  let total = 0;
  for (const it of items) {
    if (isPhysical(it) && (locationOf(it) === "body" || locationOf(it) === "backpack")) total += itemWeight(it);
  }
  return total + Number(clinchMassKg || 0);
}

export function loadRatio(weightKg, capacityKg) {
  if (!capacityKg || capacityKg <= 0) return weightKg ? Infinity : 0;
  return weightKg / capacityKg;
}

export function loadTier(ratio) {
  if (ratio > 1) return "overloaded";
  for (const band of RULES.load_bands) {
    if (band.max_ratio != null && ratio <= band.max_ratio) return band.name;
  }
  return "overloaded";
}

function bandByName(name) {
  return RULES.load_bands.find((b) => b.name === name) || {};
}

export function actionEconomyPenalties(ratio) {
  for (const band of RULES.action_economy_encumbrance.bands) {
    if (band.max_ratio == null || ratio <= band.max_ratio) {
      return { ap_penalty: band.ap_penalty, speed_penalty_pct: band.speed_penalty_pct,
        economy_band: band.name, placeholder: !!band.placeholder };
    }
  }
  const last = RULES.action_economy_encumbrance.bands.at(-1);
  return { ap_penalty: last.ap_penalty, speed_penalty_pct: last.speed_penalty_pct,
    economy_band: last.name, placeholder: true };
}

export function actionAllowed(tier, actionId) {
  const blocked = new Set(RULES.action_restrictions.by_tier[tier]?.blocked || []);
  return !blocked.has(actionId);
}

export function actionPenalty(tier, actionId) {
  const penalties = RULES.action_restrictions.by_tier[tier]?.penalties || {};
  return penalties[actionId] || (actionId === "climb" || actionId === "rope_climb_unaided" ? penalties.climb : undefined);
}

export function tierPenalties(tier, gender = "male") {
  const band = bandByName(tier);
  const male = String(gender).toLowerCase().startsWith("m");
  const restrictions = RULES.action_restrictions.by_tier[tier] || {};
  return {
    stamina_regen_pct: (male ? band.male_stamina_regen_pct : band.female_stamina_regen_pct) || 0,
    stamina_drain_pct: (male ? band.male_stamina_drain_pct : band.female_stamina_drain_pct) || 0,
    dex_aim_penalty: male ? 0 : (band.female_dex_aim_penalty || 0),
    agility_penalty: male ? (band.male_agility_penalty || 0) : 0,
    blocked: [...(restrictions.blocked || [])],
    action_penalties: restrictions.penalties || {},
    placeholder_restrictions: !!RULES.action_restrictions.placeholder,
  };
}

export function missingWeight(item) {
  const sid = sourceId(item);
  const typ = itemType(item);
  if (typ === "weapon" && RULES.missing_weights.weapons.includes(sid)) return true;
  if (!PHYSICAL.has(typ)) return false;
  const raw = item?.weight ?? item?.system?.weight;
  return raw == null;
}

export function equippedContainers(items) {
  return items.filter((it) => isPhysical(it) && isContainer(it) && locationOf(it) === "body");
}

export function chooseContainer(items, weightKg, volume = null) {
  const candidates = [];
  for (const pack of equippedContainers(items)) {
    const cap = containerCapacityKg(pack);
    const used = contentsWeight(pack, items);
    if (used + weightKg > cap + 1e-9) continue;
    const volCap = itemFlag(pack, "capacity_volume") ?? itemFlag(pack, "capacityVolume");
    if (volume != null && volCap != null) {
      const cid = itemId(pack);
      let usedVol = 0;
      for (const it of items) {
        if (locationOf(it) === "backpack" && containerIdOf(it) === cid) {
          const v = itemFlag(it, "volume");
          if (v != null) usedVol += Number(v);
        }
      }
      if (usedVol + Number(volume) > Number(volCap) + 1e-9) continue;
    }
    candidates.push([cap - used, pack]);
  }
  if (!candidates.length) return null;
  candidates.sort((a, b) => b[0] - a[0]);
  return candidates[0][1];
}

const slotsFree = (needed, taken) => needed.every((s) => !(s in taken));

export function placeItem(items, newItem, grip = "two_hands") {
  if (!isPhysical(newItem)) {
    const typ = itemType(newItem);
    if (NON_PHYSICAL.has(typ) || typ === "") {
      return { ok: true, location: null, slot: null, container_id: null, equipped: false, message: "", physical: false };
    }
    return { ok: false, location: null, slot: null, container_id: null, equipped: false,
      message: `${itemName(newItem)} is not a carryable item.`, physical: false };
  }
  const name = itemName(newItem);
  const weight = itemWeight(newItem);
  const needed = bodySlotsFor(newItem, grip);
  const taken = occupiedBodySlots(items, itemId(newItem) || null, grip);

  if (isContainer(newItem) && needed.length) {
    if (slotsFree(needed, taken)) {
      return { ok: true, location: "body", slot: needed[0], container_id: null, equipped: true,
        message: `${name} is worn.`, physical: true, slots: needed };
    }
    const slot = needed[0];
    const holder = taken[slot];
    return { ok: false, location: null, slot: null, container_id: null, equipped: false,
      message: `You already have something on your ${slot.replaceAll("_", " ")}`
        + (holder ? ` (${holder})` : "") + `, so ${name} cannot be worn.`,
      physical: true };
  }

  if (needed.length && slotsFree(needed, taken)) {
    return { ok: true, location: "body", slot: needed[0], container_id: null, equipped: true,
      message: `${name} is equipped.`, physical: true, slots: needed };
  }

  const pack = chooseContainer(items, weight, itemFlag(newItem, "volume"));
  if (pack) {
    const why = needed.length ? "Those slots are already taken, so" : "There is no body slot for this,";
    return { ok: true, location: "backpack", slot: null, container_id: itemId(pack), equipped: false,
      message: `${why} ${name} goes into ${itemName(pack)}.`, physical: true, slots: [] };
  }

  const packs = equippedContainers(items);
  if (needed.length && !packs.length) {
    const slots = needed.map((s) => s.replaceAll("_", " ")).join(", ");
    return { ok: false, location: null, slot: null, container_id: null, equipped: false,
      message: `No free slot (${slots}) for ${name}, and you are not wearing a pack to stow it in.`,
      physical: true };
  }
  if (!packs.length) {
    return { ok: false, location: null, slot: null, container_id: null, equipped: false,
      message: `You have no backpack or pouch with room for ${name}.`, physical: true };
  }
  const parts = packs.map((p) => `${itemName(p)} ${contentsWeight(p, items).toFixed(1)}/${containerCapacityKg(p).toFixed(1)} kg`);
  return { ok: false, location: null, slot: null, container_id: null, equipped: false,
    message: `No room for ${name} (${weight.toFixed(1)} kg). ${parts.join("; ")}.`, physical: true };
}

export const TRACKED_ACTIONS = [
  ["walk", "Walk"],
  ["sprint", "Sprint"],
  ["acrobatics", "Acrobatics"],
  ["climb", "Climb"],
  ["rope_climb_unaided", "Climb a rope (unaided)"],
];

export function evaluate(strength, gender, race, items, talents = [], clinchMassKg = 0, grip = "two_hands") {
  const capacity_kg = carryCapacity(strength, gender, race, talents);
  const carried_kg = carriedWeight(items, clinchMassKg);
  const ratio = loadRatio(carried_kg, capacity_kg);
  const tier = loadTier(ratio);
  const penalties = tierPenalties(tier, gender);
  const action_economy = actionEconomyPenalties(ratio);
  const actions = {};
  for (const [action] of TRACKED_ACTIONS) {
    const allowed = action === "walk" ? true : actionAllowed(tier, action);
    actions[action] = { allowed, penalty: actionPenalty(tier, action) };
  }
  return {
    capacity_kg, carried_kg, clinch_mass_kg: Number(clinchMassKg || 0), ratio, tier,
    past_half_load: ratio > MARCH_CLIFF_START, penalties, action_economy, actions,
    missing_weight_items: items.filter(missingWeight).map(itemName),
    grip,
  };
}

function actorItems(actor) {
  if (!actor) return [];
  const items = actor.items;
  if (!items) return [];
  if (Array.isArray(items)) return items;
  if (typeof items.contents === "object") return Array.from(items.contents ?? items);
  return Array.from(items);
}

function actorTalents(actor) {
  return actorItems(actor)
    .filter((it) => itemType(it) === "talent")
    .map((it) => sourceId(it) || String(it.name || "").toLowerCase().replaceAll(" ", "_"));
}

export function evaluateActor(actor) {
  const system = actor?.system || {};
  const details = system.details || {};
  const attrs = system.attributes || {};
  const strength = Number(attrs.strength?.value ?? 30);
  const gender = details.gender || "";
  const race = details.race || "Human";
  const grip = system.combat?.grip || "two_hands";
  const flags = actor?.flags?.[ID] || {};
  const clinch = Number(flags.clinchMassKg || flags.clinch_mass_kg || 0);
  return evaluate(strength, gender, race, actorItems(actor), actorTalents(actor), clinch, grip);
}

function containerSummary(items) {
  return equippedContainers(items).map((pack) => {
    const cap = containerCapacityKg(pack);
    const used = contentsWeight(pack, items);
    return { id: itemId(pack), name: itemName(pack), used, cap, free: Math.max(0, cap - used) };
  });
}

function slotLabel(slot) {
  return String(slot || "").replaceAll("_", " ");
}

function describeItem(it, grip) {
  const loc = locationOf(it);
  const slots = loc === "body" ? bodySlotsFor(it, grip) : [];
  return {
    id: itemId(it),
    name: itemName(it),
    type: itemType(it),
    img: it.img || "",
    weight: itemWeight(it),
    location: loc,
    equipped: loc === "body",
    slots: slots.map(slotLabel).join(", "),
    container_id: containerIdOf(it),
    missing_weight: missingWeight(it),
    is_container: isContainer(it),
    capacity_kg: isContainer(it) ? containerCapacityKg(it) : 0,
  };
}

export function prepareInventory(actor) {
  const ev = evaluateActor(actor);
  const items = actorItems(actor);
  const grip = ev.grip;
  const physical = items.filter((it) => isPhysical(it) && (locationOf(it) === "body" || locationOf(it) === "backpack"));
  const body = physical.filter((it) => locationOf(it) === "body").map((it) => describeItem(it, grip));
  const packs = equippedContainers(items).map((pack) => {
    const cid = itemId(pack);
    const contents = physical
      .filter((it) => locationOf(it) === "backpack" && containerIdOf(it) === cid)
      .map((it) => describeItem(it, grip));
    return { ...describeItem(pack, grip), used: contentsWeight(pack, items), contents };
  });
  const looseBackpack = physical
    .filter((it) => locationOf(it) === "backpack" && !containerIdOf(it))
    .map((it) => describeItem(it, grip));
  const pct = ev.capacity_kg > 0 ? Math.min(150, (ev.carried_kg / ev.capacity_kg) * 100) : 0;
  const actions = TRACKED_ACTIONS.map(([id, label]) => {
    const state = ev.actions[id];
    const penalty = state?.penalty;
    let note = "";
    if (penalty?.athletics_penalty) note = `${penalty.athletics_penalty} to Athletics (placeholder)`;
    return { id, label, allowed: !!state?.allowed, note };
  });
  return {
    ...ev,
    carried_display: ev.carried_kg.toFixed(1),
    capacity_display: ev.capacity_kg.toFixed(1),
    ratio_display: Number.isFinite(ev.ratio) ? `${Math.round(ev.ratio * 100)}%` : "—",
    bar_pct: pct,
    tier_label: ev.tier.replaceAll("_", " "),
    body,
    packs,
    looseBackpack,
    containers: containerSummary(items),
    actions,
    hasPhysical: physical.length > 0 || packs.length > 0,
  };
}

export function placementFlags(result) {
  if (!result.ok || !result.physical) return null;
  return {
    "system.equipped": !!result.equipped,
    "system.location": result.location || "",
    "system.container_id": result.container_id || "",
  };
}

// ---------------------------------------------------------------------------
// Foundry glue (no-op in Node tests)
// ---------------------------------------------------------------------------
function notify(message, kind = "warn") {
  if (globalThis.ui?.notifications?.[kind]) globalThis.ui.notifications[kind](message);
  else if (globalThis.ui?.notifications?.info) globalThis.ui.notifications.info(message);
}

const EQUIP_SLOTS = [
  ...RULES.equip_slots.armor_zones,
  ...RULES.equip_slots.hands,
  ...RULES.equip_slots.worn,
];

export function actorInventoryState(actor) {
  const ev = evaluateActor(actor);
  const items = actorItems(actor);
  const grip = ev.grip;
  const equipped = Object.fromEntries(EQUIP_SLOTS.map((s) => [s, ""]));
  let pack = null;
  for (const it of items) {
    if (!isPhysical(it) || locationOf(it) !== "body") continue;
    const id = itemId(it);
    for (const slot of bodySlotsFor(it, grip)) {
      if (slot in equipped && !equipped[slot]) equipped[slot] = id;
    }
    if (isContainer(it) && bodySlotsFor(it, grip).includes("back")) pack = it;
  }
  if (!pack) pack = equippedContainers(items)[0] || null;
  const contents = pack
    ? items.filter((it) => locationOf(it) === "backpack" && containerIdOf(it) === itemId(pack)).map(itemId)
    : [];
  return {
    equipped,
    backpack: { itemId: pack ? itemId(pack) : "", contents },
    carried_weight: Math.round(ev.carried_kg * 1000) / 1000,
    carry_capacity: Math.round(ev.capacity_kg * 1000) / 1000,
  };
}

async function syncActorInventory(actor) {
  if (!actor || typeof actor.update !== "function") return;
  const state = actorInventoryState(actor);
  await actor.update({ "system.inventory": state });
}

function hookPreCreate(item, _data, _options, _userId) {
  const actor = item.parent;
  if (!actor || actor.documentName !== "Actor") return;
  const items = actorItems(actor);
  const grip = actor.system?.combat?.grip || "two_hands";
  const result = placeItem(items, item, grip);
  if (!result.physical && result.ok) return;
  if (!result.ok) {
    notify(result.message, "warn");
    return false;
  }
  const updates = placementFlags(result);
  if (updates) item.updateSource(updates);
}

async function stowOrEquip(actor, itemIdToMove, dest) {
  const item = actor.items.get(itemIdToMove);
  if (!item) return;
  const grip = actor.system?.combat?.grip || "two_hands";
  const others = actorItems(actor).filter((it) => itemId(it) !== item.id);
  const ghost = { type: item.type, name: item.name, id: item.id, system: item.system,
    flags: { [ID]: { location: "", slot: itemFlag(item, "slot") } }, weight: itemWeight(item) };
  if (dest === "backpack") {
    const pack = chooseContainer(others, itemWeight(item), itemFlag(item, "volume"));
    if (!pack) {
      notify(placeItem(others, ghost, grip).message || "No room in a pack.", "warn");
      return;
    }
    await item.update({ "system.equipped": false, "system.location": "backpack",
      "system.container_id": itemId(pack) });
    return;
  }
  if (dest === "body") {
    const result = placeItem(others, ghost, grip);
    if (!result.ok || result.location !== "body") {
      notify(result.message || "Those slots are taken.", "warn");
      return;
    }
    await item.update({ "system.equipped": true, "system.location": "body",
      "system.container_id": "" });
  }
}

async function injectPanel(app, element) {
  if (app.document?.documentName !== "Actor") return;
  const root = element instanceof HTMLElement ? element : element?.[0] || app.element;
  if (!root?.querySelector) return;
  root.querySelector(".breath-inventory")?.remove();
  const host = root.querySelector(".breath-sheet") || root;
  const ctx = prepareInventory(app.document);
  let html;
  if (globalThis.foundry?.applications?.handlebars?.renderTemplate) {
    html = await foundry.applications.handlebars.renderTemplate(
      "systems/breath-and-the-veil/templates/parts/inventory.hbs", ctx);
  } else {
    return;
  }
  host.insertAdjacentHTML("beforeend", html);
  const panel = host.querySelector(".breath-inventory");
  panel?.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-inv-action]");
    if (!btn) return;
    const id = btn.dataset.itemId;
    const action = btn.dataset.invAction;
    if (action === "open" && id) app.document.items.get(id)?.sheet?.render(true);
    if (action === "stow" && id) await stowOrEquip(app.document, id, "backpack");
    if (action === "equip" && id) await stowOrEquip(app.document, id, "body");
    if (action === "delete" && id) await app.document.items.get(id)?.delete();
  });
}

export function registerInventory() {
  if (typeof globalThis.Hooks === "undefined") return;
  Hooks.once("init", () => {
    const load = globalThis.foundry?.applications?.handlebars?.loadTemplates;
    load?.(["systems/breath-and-the-veil/templates/parts/inventory.hbs"]);
  });
  Hooks.on("preCreateItem", hookPreCreate);
  Hooks.on("createItem", (item) => { if (item.parent?.documentName === "Actor") syncActorInventory(item.parent); });
  Hooks.on("updateItem", (item) => { if (item.parent?.documentName === "Actor") syncActorInventory(item.parent); });
  Hooks.on("deleteItem", (item) => { if (item.parent?.documentName === "Actor") syncActorInventory(item.parent); });
  Hooks.on("updateActor", (actor, changed) => {
    // Recalculate weight and capacity if strength, race, gender or talents changed,
    // but skip when the only change is the inventory numbers we just wrote.
    const invOnly = changed?.system && Object.keys(changed.system).length === 1 && changed.system.inventory;
    if (!invOnly) syncActorInventory(actor);
  });
  Hooks.on("renderBreathActorSheet", (app, el) => { injectPanel(app, el); });
  // Fallback name used by some Foundry versions
  Hooks.on("renderActorSheet", (app, el) => {
    if (app.constructor?.name === "BreathActorSheet") injectPanel(app, el);
  });
}
