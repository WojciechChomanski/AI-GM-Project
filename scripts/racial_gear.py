# file: scripts/racial_gear.py
"""Hard racial equipment blocks and ogre size rules (rules/racial_gear.json).

A race cannot equip a forbidden item. These are visible rules, not hidden stats.
Kinbreaker / stress / reputation taboos are not used.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = None
_WEAPONS = None


def data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(ROOT, "rules", "racial_gear.json"), encoding="utf-8-sig") as f:
            _DATA = json.load(f)
    return _DATA


def reload():
    global _DATA, _WEAPONS
    _DATA = None
    _WEAPONS = None
    return data()


def weapons():
    global _WEAPONS
    if _WEAPONS is None:
        with open(os.path.join(ROOT, "rules", "weapons.json"), encoding="utf-8-sig") as f:
            _WEAPONS = json.load(f)
    return _WEAPONS


def resolve_alias(key):
    if not key:
        return key
    return data()["aliases"].get(str(key), str(key))


def _get(obj, name, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def item_key(item):
    if item is None:
        return ""
    if isinstance(item, str):
        return resolve_alias(item)
    for name in ("source_id", "key", "id", "weapon", "weapon_id"):
        val = _get(item, name)
        if val:
            return resolve_alias(val)
    sys = _get(item, "system") or {}
    if isinstance(sys, dict):
        for name in ("source_id", "key"):
            if sys.get(name):
                return resolve_alias(sys[name])
    return resolve_alias(_get(item, "name") or "")


def item_type_name(item):
    if item is None:
        return ""
    if isinstance(item, str):
        return ""
    typ = _get(item, "type") or _get(item, "weapon_type") or ""
    if typ in ("weapon", "armor", "gear", "item"):
        typ = ""
    sys = _get(item, "system") or {}
    if isinstance(sys, dict):
        typ = typ or sys.get("weapon_type") or sys.get("type") or ""
        if typ in ("weapon", "armor", "gear", "item"):
            typ = typ  # keep item document type only as a fallback below
    # Foundry document type
    doc_type = _get(item, "type") or (sys.get("item_kind") if isinstance(sys, dict) else "")
    return typ or ""


def item_kind(item):
    if item is None or isinstance(item, str):
        return ""
    kind = _get(item, "item_kind") or ""
    sys = _get(item, "system") or {}
    if isinstance(sys, dict):
        kind = kind or sys.get("item_kind") or sys.get("rules", {}).get("item_kind") or ""
    return str(kind or "")


def is_shield(item):
    if item is None:
        return False
    if isinstance(item, str):
        key = item.lower()
        return key in ("shield",) or "shield" in key
    typ = str(_get(item, "type") or "").lower()
    if typ == "shield":
        return True
    if item_kind(item).lower() == "shield":
        return True
    sys = _get(item, "system") or {}
    if isinstance(sys, dict):
        if str(sys.get("type") or "").lower() == "shield":
            return True
        if str(sys.get("item_kind") or "").lower() == "shield":
            return True
        if str(sys.get("weapon_type") or "").lower() == "shield":
            return True
    return typ == "shield"


def catalog_row(item):
    """Merge a live item with its weapons.json row when the key is known."""
    key = item_key(item)
    row = dict(weapons().get(key) or {})
    if isinstance(item, dict):
        row.update({k: v for k, v in item.items() if v is not None and k != "system"})
        sys = item.get("system") or {}
        if isinstance(sys, dict):
            if sys.get("weapon_type"):
                row.setdefault("type", sys["weapon_type"])
            if sys.get("item_kind"):
                row["item_kind"] = sys["item_kind"]
            if sys.get("size_class"):
                row["size_class"] = sys["size_class"]
    elif item is not None and not isinstance(item, str):
        for name in ("type", "weapon_type", "size_class", "item_kind", "min_STR", "min_str"):
            val = getattr(item, name, None)
            if val is not None:
                row[name] = val
    if key:
        row.setdefault("key", key)
    return row


def in_group(item, group_id):
    cfg = data()["groups"][group_id]
    if group_id == "shield" and is_shield(item):
        return True
    row = catalog_row(item)
    key = str(row.get("key") or item_key(item) or "").lower()
    typ = str(row.get("type") or row.get("weapon_type") or item_type_name(item) or "").lower()
    if typ in {t.lower() for t in cfg.get("exclude_types") or []}:
        return False
    if key in {k.lower() for k in cfg.get("exclude_keys") or []}:
        return False
    for sub in cfg.get("exclude_substrings") or []:
        if sub.lower() in key:
            return False
    if typ in {t.lower() for t in cfg.get("types") or []}:
        # sword group must not swallow shortsword keys of type "sword"
        if group_id == "sword" and key == "shortsword":
            return False
        return True
    if key in {k.lower() for k in cfg.get("keys") or []}:
        return True
    for sub in cfg.get("key_substrings") or []:
        if sub.lower() in key:
            return True
    kinds = {k.lower() for k in cfg.get("item_kinds") or []}
    if item_kind(item).lower() in kinds:
        return True
    return False


def item_groups(item):
    return [g for g in data()["groups"] if in_group(item, g)]


def size_class(item):
    row = catalog_row(item)
    val = row.get("size_class")
    if not val and isinstance(item, dict):
        sys = item.get("system") or {}
        if isinstance(sys, dict):
            val = sys.get("size_class")
    return str(val or data()["size"]["default"]).lower()


def race_name(race):
    if race is None:
        return ""
    if isinstance(race, str):
        return race
    return str(_get(race, "race") or _get(race, "name") or "")


def mass_of(character, default=80):
    try:
        return float(_get(character, "mass", default) or default)
    except (TypeError, ValueError):
        return default


def strength_of(character, default=0):
    try:
        return int(_get(character, "strength", default) or default)
    except (TypeError, ValueError):
        return default


def forbidden_groups(race):
    name = race_name(race)
    row = data()["races"].get(name) or {}
    return list(row.get("forbidden_groups") or [])


def refuse_reason(race, item, character=None):
    """Why this race cannot have the item, or None if allowed.

    Cultural bans are hard blocks. A large weapon is also refused to anyone
    of mass 150 or less (ogre-scale). min_STR still applies separately via
    too_weak / can_wield_weapon.
    """
    name = race_name(race)
    if not name or item is None:
        return None
    cfg = data()
    for group in forbidden_groups(name):
        if in_group(item, group):
            if group in ("sword", "shortsword", "dagger", "spear"):
                return cfg["messages"]["dwarf_blade"]
            if group == "bow":
                return cfg["messages"]["dwarf_bow"]
            if group in ("hammer", "axe"):
                return cfg["messages"]["elf_hammer_or_axe"]
            if group == "crossbow":
                return cfg["messages"]["elf_crossbow"]
            if group == "gunpowder":
                return cfg["messages"]["elf_gunpowder"]
            if group == "shield":
                return cfg["messages"]["elf_shield"]
            return f"{name} will not use this."
    # size: large gear is for ogre-scale bodies
    if size_class(item) == "large":
        mass = mass_of(character, 80 if name != "Ogre" else 600)
        if name != "Ogre" and mass <= cfg["size"]["large_mass_threshold"]:
            return cfg["messages"]["too_large"]
    return None


def can_equip(race, item, character=None):
    return refuse_reason(race, item, character) is None


def can_ride(race):
    name = race_name(race)
    row = data()["races"].get(name) or {}
    return bool(row.get("may_ride", True))


def ride_error(race):
    if can_ride(race):
        return None
    name = race_name(race)
    if (data()["races"].get(name) or {}).get("ride_reason") == "mass":
        return "An ogre crushes any standard mount."
    return data()["messages"]["dwarf_ride"]


def is_ogre(character_or_race):
    name = race_name(character_or_race)
    if name == "Ogre":
        return True
    return race_name(_get(character_or_race, "race")) == "Ogre" or _get(character_or_race, "race") == "Ogre"


def ogre_uses_improvised(character, item):
    """True when an ogre is fighting with a medium (human-scale) weapon."""
    if not character:
        return False
    race = race_name(_get(character, "race") or character)
    if race != "Ogre":
        return False
    if is_shield(item):
        return size_class(item) != "large"
    return size_class(item) == "medium"


def improvised_modifiers(character, item):
    """Skill penalty and durability multiplier for an ogre with a medium weapon."""
    if not ogre_uses_improvised(character, item):
        return {"active": False, "skill_penalty": 0, "durability_loss_mult": 1,
                "no_stances": False, "no_maneuvers": False, "no_mastery": False}
    cfg = data()["ogre_improvised"]
    penalty = int(cfg["skill_penalty"])
    if in_group(item, "dagger"):
        penalty += int(cfg["dagger_extra_penalty"])
    return {
        "active": True,
        "skill_penalty": penalty,
        "durability_loss_mult": int(cfg["durability_loss_mult"]),
        "no_stances": True,
        "no_maneuvers": True,
        "no_mastery": True,
    }


def min_str_of(item):
    row = catalog_row(item)
    for name in ("min_STR", "min_str"):
        if row.get(name) not in (None, ""):
            try:
                return int(row[name])
            except (TypeError, ValueError):
                pass
    return 0


def too_weak(character, item):
    """Existing grip rule: more than 15 below min_STR cannot fight with it."""
    need = min_str_of(item)
    if not need:
        return False
    return strength_of(character) < need - 15


def can_wield(character, item):
    """Cultural ban, size, and the existing min_STR hard floor."""
    race = _get(character, "race") or character
    reason = refuse_reason(race, item, character)
    if reason:
        return False, reason
    if too_weak(character, item):
        return False, data()["messages"]["too_weak"]
    return True, None


def filter_armor_coverage(character, armor):
    race = race_name(_get(character, "race") or character)
    if race != "Ogre":
        return list((_get(armor, "coverage") if not isinstance(armor, dict)
                     else armor.get("coverage")) or _get(armor, "coverage") or [])
    # get coverage and size from armor
    if isinstance(armor, dict):
        coverage = list(armor.get("coverage") or (armor.get("system") or {}).get("coverage") or [])
        size = (armor.get("size_class") or (armor.get("system") or {}).get("size_class") or "medium")
    else:
        coverage = list(_get(armor, "coverage") or [])
        size = _get(armor, "size_class") or "medium"
    if str(size).lower() == "large":
        return coverage
    cfg = data()["ogre_armor"]
    keep_n = int(len(coverage) * float(cfg["medium_coverage_fraction"]))
    if cfg.get("round") == "down":
        keep_n = len(coverage) // 2
    keep_n = max(0, keep_n)
    priority = [z.lower() for z in cfg["keep_priority"]]
    ranked = sorted(coverage, key=lambda z: (priority.index(z.lower()) if z.lower() in priority else 99))
    return ranked[:keep_n]


def axe_edge(weapon_state, default=None):
    cfg = data()["axe_edge"]
    if default is None:
        default = int(cfg["max"])
    if isinstance(weapon_state, dict) and "edge" in weapon_state:
        return int(weapon_state["edge"])
    return default


def is_axe_item(item):
    return in_group(item, "axe")


def after_fight_without_smith(weapon_state, item=None):
    """Reduce edge by 1. At 0 the axe is blunt and counts as a club."""
    if item is not None and not is_axe_item(item) and not (
        isinstance(weapon_state, dict) and weapon_state.get("is_axe")
    ):
        return weapon_state
    cfg = data()["axe_edge"]
    state = dict(weapon_state or {})
    if "edge" not in state:
        state["edge"] = int(cfg["max"])
    state["edge"] = max(0, int(state["edge"]) - int(cfg["loss_per_fight_without_smith"]))
    state["is_axe"] = True
    if state["edge"] <= 0:
        state["counts_as"] = cfg["at_zero"]
        state["type"] = "improvised"
        state["damage_type"] = "blunt"
        state["guard_set"] = None
        state["stance_tree"] = []
    return state


def counts_as_club(weapon_state):
    return bool(weapon_state) and weapon_state.get("counts_as") == "club"


def load_weapon(key):
    """Resolve aliases and return a weapons.json row (copy) with key set."""
    resolved = resolve_alias(key)
    row = weapons().get(resolved)
    if not row:
        return None
    out = dict(row)
    out["key"] = resolved
    out.setdefault("size_class", data()["size"]["default"])
    return out
