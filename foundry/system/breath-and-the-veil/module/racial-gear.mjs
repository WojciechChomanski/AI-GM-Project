// Hard racial equipment blocks and ogre size rules. Visible rules, not hidden stats.
import RULES from "./racial-gear-rules.mjs";

export { RULES };

function lower(v) {
  return String(v || "").toLowerCase();
}

export function resolveAlias(key) {
  if (!key) return key;
  return RULES.aliases[key] || String(key);
}

export function itemKey(item) {
  if (item == null) return "";
  if (typeof item === "string") return resolveAlias(item);
  const sys = item.system || {};
  const raw = item.source_id || item.key || item.id || sys.source_id || sys.key || item.name || "";
  return resolveAlias(raw);
}

export function isShield(item) {
  if (item == null) return false;
  if (typeof item === "string") return lower(item) === "shield" || lower(item).includes("shield");
  const typ = lower(item.type);
  const sys = item.system || {};
  const kind = lower(item.item_kind || sys.item_kind || (sys.rules && sys.rules.item_kind) || "");
  return typ === "shield" || kind === "shield" || lower(sys.type) === "shield" || lower(sys.weapon_type) === "shield";
}

export function sizeClass(item) {
  if (item && typeof item === "object") {
    const sys = item.system || {};
    const val = item.size_class || sys.size_class;
    if (val) return lower(val);
  }
  return lower(RULES.size.default);
}

function inGroup(item, groupId) {
  const cfg = RULES.groups[groupId];
  if (!cfg) return false;
  if (groupId === "shield" && isShield(item)) return true;
  const key = lower(itemKey(item));
  const typ = lower((item && (item.weapon_type || item.type || (item.system && (item.system.weapon_type || item.system.type)))) || "");
  if ((cfg.exclude_types || []).some((t) => typ === lower(t))) return false;
  if ((cfg.exclude_keys || []).some((k) => key === lower(k))) return false;
  if ((cfg.exclude_substrings || []).some((s) => key.includes(lower(s)))) return false;
  if ((cfg.types || []).some((t) => typ === lower(t))) {
    if (groupId === "sword" && key === "shortsword") return false;
    return true;
  }
  if ((cfg.keys || []).some((k) => key === lower(k))) return true;
  if ((cfg.key_substrings || []).some((s) => key.includes(lower(s)))) return true;
  const kind = lower((item && (item.item_kind || (item.system && item.system.item_kind))) || "");
  if ((cfg.item_kinds || []).some((k) => kind === lower(k))) return true;
  return false;
}

export function refuseReason(race, item, { mass } = {}) {
  const name = String(race || "");
  if (!name || item == null) return null;
  const row = RULES.races[name] || {};
  for (const group of row.forbidden_groups || []) {
    if (!inGroup(item, group)) continue;
    if (["sword", "shortsword", "dagger", "spear"].includes(group)) return RULES.messages.dwarf_blade;
    if (group === "bow") return RULES.messages.dwarf_bow;
    if (["hammer", "axe"].includes(group)) return RULES.messages.elf_hammer_or_axe;
    if (group === "crossbow") return RULES.messages.elf_crossbow;
    if (group === "gunpowder") return RULES.messages.elf_gunpowder;
    if (group === "shield") return RULES.messages.elf_shield;
    return `${name} will not use this.`;
  }
  if (sizeClass(item) === "large") {
    const body = mass != null ? Number(mass) : (name === "Ogre" ? 600 : 80);
    if (name !== "Ogre" && body <= RULES.size.large_mass_threshold) return RULES.messages.too_large;
  }
  return null;
}

export function canEquip(race, item, opts) {
  return refuseReason(race, item, opts) == null;
}

export function actorRace(actor) {
  return actor?.system?.details?.race || actor?.details?.race || "";
}

export function actorMass(actor) {
  const n = Number(actor?.system?.details?.mass ?? actor?.details?.mass);
  return Number.isFinite(n) ? n : undefined;
}
