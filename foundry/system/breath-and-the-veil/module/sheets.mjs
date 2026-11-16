const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ActorSheetV2, ItemSheetV2 } = foundry.applications.sheets;
import { ATTRIBUTES } from "./data.mjs";
import {
  classPageView, grantedFeatures, portraitPath, classIconPath, startingSkills,
  carryCapacity, sumCarriedWeight, computeCharacter, canAssign,
  ZONE_LAYOUT, zonesAtZero, COLLAPSE_ZONES_AT_ZERO, VITAL_ZONES, sumZones,
} from "./character.mjs";

const ITEM_GROUPS = ["weapon", "armor", "class", "race", "gender", "talent", "advantage", "flaw", "skill"];
const IDENTITY = new Set(["race", "gender", "class"]);
const SYS = "systems/breath-and-the-veil";

async function resolveArt(preferred, fallback) {
  if (preferred && typeof foundry?.utils?.srcExists === "function") {
    try {
      if (await foundry.utils.srcExists(preferred)) return preferred;
    } catch (_) { /* fall through */ }
  }
  return fallback;
}

function identityItems(actor) {
  const of = (type) => actor.items.find((i) => i.type === type);
  return { raceItem: of("race"), genderItem: of("gender"), classItem: of("class") };
}

function talentIds(actor) {
  return actor.items.filter((i) => i.type === "talent").map((i) => i.system?.source_id || i.name);
}

export async function applyIdentity(actor) {
  const parts = identityItems(actor);
  const computed = computeCharacter({ ...parts, talents: talentIds(actor) });
  const race = parts.genderItem?.system?.race || computed.details.race;
  const gender = computed.details.gender;
  const art = portraitPath(race, gender);
  const img = typeof art === "string" ? art : await resolveArt(art.preferred, art.fallback);
  const currentImg = actor.img || "";
  const isOurs = !currentImg || currentImg.includes(`${SYS}/assets/portraits/`) || currentImg.includes("icons/svg/mystery-man");
  const patch = {
    "system.details.race": computed.details.race,
    "system.details.gender": computed.details.gender,
    "system.details.class_name": computed.details.class_name,
    "system.details.mass": computed.details.mass,
    "system.attributes": computed.attributes,
    "system.resources.hp": computed.resources.hp,
    "system.resources.stamina": computed.resources.stamina,
    "system.resources.zones": computed.resources.zones,
    "system.inventory.carry_capacity": computed.inventory.carry_capacity,
  };
  if (isOurs) patch.img = img;
  await actor.update(patch);
  await syncSkills(actor, computed.skills);
  return computed;
}

async function syncSkills(actor, wanted) {
  const have = new Map(actor.items.filter((i) => i.type === "skill").map((i) => [i.system?.source_id || i.name, i]));
  const updates = [];
  const create = [];
  for (const s of wanted) {
    const existing = have.get(s.source_id);
    if (existing) {
      if (existing.system.rank !== s.rank) updates.push({ _id: existing.id, "system.rank": s.rank });
    } else {
      create.push({
        name: s.source_id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        type: "skill",
        img: "icons/svg/book.svg",
        system: { source_id: s.source_id, source_file: "rules/skills.json", rank: s.rank, rules: {} },
      });
    }
  }
  if (updates.length) await actor.updateEmbeddedDocuments("Item", updates);
  if (create.length) await actor.createEmbeddedDocuments("Item", create, { breathApply: true });
}

export function previewAssignment(actor, incoming) {
  const parts = identityItems(actor);
  if (incoming?.type === "race") parts.raceItem = incoming;
  if (incoming?.type === "gender") {
    parts.genderItem = incoming;
    // Gender items are race-specific: a Human Male drop implies Human.
    if (incoming.system?.race && parts.raceItem && parts.raceItem.system?.source_id
        && incoming.system.race !== parts.raceItem.system.source_id
        && incoming.system.race !== parts.raceItem.name) {
      parts.raceItem = { name: incoming.system.race, type: "race", system: { source_id: incoming.system.race, rules: {} } };
    }
  }
  if (incoming?.type === "class") parts.classItem = incoming;
  const race = parts.raceItem?.system?.source_id || parts.raceItem?.name || parts.genderItem?.system?.race || "";
  const gender = parts.genderItem?.system?.gender || "";
  return canAssign({
    race, gender, classItem: parts.classItem, raceItem: parts.raceItem, genderItem: parts.genderItem,
    requireIdentityItems: incoming?.type === "class",
  });
}

export class BreathActorSheet extends HandlebarsApplicationMixin(ActorSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["breath", "sheet", "actor"],
    position: { width: 920, height: 920 },
    form: { submitOnChange: true },
    window: { resizable: true },
    actions: {
      openItem: BreathActorSheet.#openItem,
      deleteItem: BreathActorSheet.#deleteItem,
    },
  };
  static PARTS = { sheet: { template: "systems/breath-and-the-veil/templates/actor-sheet.hbs" } };

  async _prepareContext(options) {
    const ctx = await super._prepareContext(options);
    const actor = this.document;
    ctx.actor = actor;
    ctx.system = actor.system;
    ctx.gripChoices = { two_hands: "BREATH.TwoHands", one_hand: "BREATH.OneHand" };
    ctx.isCharacter = actor.type === "character";
    ctx.attributes = ATTRIBUTES.map((key) => ({
      key, label: game.i18n.localize(`BREATH.Attr.${key}`),
      ...actor.system.attributes[key],
    }));
    ctx.groups = ITEM_GROUPS.map((type) => ({
      type, label: game.i18n.localize(`TYPES.Item.${type}`),
      items: actor.items.filter((i) => i.type === type),
    })).filter((g) => g.items.length);
    ctx.biography = await foundry.applications.ux.TextEditor.implementation.enrichHTML(actor.system.biography, { relativeTo: actor });
    const parts = identityItems(actor);
    const computed = computeCharacter({ ...parts, talents: talentIds(actor) });
    ctx.features = computed.features;
    ctx.skills = actor.items.filter((i) => i.type === "skill").map((i) => ({
      id: i.id, name: i.name, rank: i.system?.rank ?? 0,
    }));
    if (!ctx.skills.length) ctx.skills = startingSkills(parts.classItem).map((s) => ({
      id: "", name: s.source_id.replace(/_/g, " "), rank: s.rank,
    }));
    const zones = actor.system.resources.zones || computed.resources.zones || {};
    const summed = sumZones(zones);
    const hp = summed.max ? summed : actor.system.resources.hp;
    const sta = actor.system.resources.stamina;
    ctx.hpPct = hp.max ? Math.max(0, Math.min(100, (100 * hp.value) / hp.max)) : 0;
    ctx.staPct = sta.max ? Math.max(0, Math.min(100, (100 * sta.value) / sta.max)) : 0;
    ctx.hpValue = hp.value;
    ctx.hpMax = hp.max;
    const zero = zonesAtZero(zones);
    ctx.zonesAtZero = zero.length;
    ctx.collapseAt = COLLAPSE_ZONES_AT_ZERO;
    ctx.vitalDown = zero.filter((id) => VITAL_ZONES.includes(id));
    ctx.zoneBoxes = ZONE_LAYOUT.map((box) => {
      const z = zones[box.id] || { value: 0, max: 0 };
      const pct = z.max ? Math.max(0, Math.min(100, (100 * z.value) / z.max)) : 0;
      return {
        ...box,
        label: game.i18n.localize(`BREATH.Zone.${box.id}`),
        value: z.value,
        max: z.max,
        pct,
        dead: z.value <= 0,
      };
    });
    const cap = actor.system.inventory?.carry_capacity
      || carryCapacity({
        strength: actor.system.attributes.strength?.value,
        gender: actor.system.details?.gender,
        race: actor.system.details?.race,
        talents: talentIds(actor),
      });
    ctx.carryCapacity = Math.round(cap * 10) / 10;
    const live = sumCarriedWeight(actor.items);
    ctx.carriedWeight = Math.round((live || actor.system.inventory?.carried_weight || 0) * 10) / 10;
    const art = portraitPath(actor.system.details?.race, actor.system.details?.gender);
    ctx.portrait = typeof art === "string" ? art : await resolveArt(art.preferred, actor.img || art.fallback);
    ctx.lockNotice = computed.ok ? "" : computed.reasons.join(" ");
    return ctx;
  }

  static #openItem(event, target) {
    this.document.items.get(target.closest("[data-item-id]")?.dataset.itemId)?.sheet.render(true);
  }
  static async #deleteItem(event, target) {
    await this.document.items.get(target.closest("[data-item-id]")?.dataset.itemId)?.delete();
  }
}

export class BreathItemSheet extends HandlebarsApplicationMixin(ItemSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["breath", "sheet", "item"],
    position: { width: 640, height: 720 },
    form: { submitOnChange: true },
    window: { resizable: true },
  };
  static PARTS = { sheet: { template: "systems/breath-and-the-veil/templates/item-sheet.hbs" } };

  async _prepareContext(options) {
    const ctx = await super._prepareContext(options);
    const item = this.document;
    ctx.item = item;
    ctx.system = item.system;
    ctx.typeLabel = game.i18n.localize(`TYPES.Item.${item.type}`);
    ctx.isWeapon = item.type === "weapon";
    ctx.isArmor = item.type === "armor";
    ctx.isClass = item.type === "class";
    ctx.description = await foundry.applications.ux.TextEditor.implementation.enrichHTML(item.system.description, { relativeTo: item });
    ctx.page = ctx.isClass ? classPageView(item) : null;
    if (item.type === "class") {
      const art = classIconPath(item.system.source_id || item.name);
      ctx.icon = typeof art === "string" ? art : await resolveArt(art.preferred, item.img || art.fallback);
    } else {
      ctx.icon = item.img;
    }
    return ctx;
  }
}

export { IDENTITY, identityItems };
