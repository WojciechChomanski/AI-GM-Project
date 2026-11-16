# file: scripts/inventory.py
"""Drag-and-drop inventory and carried load for Breath and the Veil (Foundry 0.3).

Carry capacity and light/medium/heavy bands are ported from existing rules.
Overloaded action blocks, backpack sizes and some slot assumptions are PLACEHOLDERS
(see rules/inventory.json). Do not invent numbers here: if a value is missing, it is
labelled in that file.

Hidden stats are not used.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import strength as S  # noqa: E402

RULES_PATH = os.path.join(ROOT, "rules", "inventory.json")


def load_rules():
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


RULES = load_rules()
CARRY = RULES["carry_capacity"]
PHYSICAL_TYPES = tuple(RULES["physical_item_types"])
NON_PHYSICAL_TYPES = tuple(RULES["non_physical_item_types"])


def race_multiplier(race):
    """Dwarf x1.5 (lore/dwarves.json), Ogre x3 (Logistics Beast), others x1."""
    key = str(race or "").strip() or "Human"
    return float(CARRY["race_multipliers"].get(key, 1.0))


def talent_multiplier(talents=()):
    """Product of known talent carry multipliers (Ox-Back x1.15)."""
    mult = 1.0
    names = {str(t).lower() for t in (talents or ())}
    for talent, value in CARRY["talent_multipliers"].items():
        if talent.lower() in names:
            mult *= float(value)
    return mult


def carry_capacity(strength, gender, race="Human", talents=()):
    """Kilograms the character can carry.

    Formula from rules/combat_rules.json and scripts/strength.py:
        (20 + STR * 1.5) * sex * race * talents
    Male sex factor is 1.15 (carry), not the 1.6 compound Power factor.
    """
    base = S.carry_capacity(strength, gender, race_multiplier(race))
    return base * talent_multiplier(talents)


def item_weight(item):
    """Weight in kg. Missing weight counts as 0 (see rules/inventory.json missing_weights)."""
    if item is None:
        return 0.0
    if isinstance(item, dict):
        w = item.get("weight", item.get("system", {}).get("weight") if isinstance(item.get("system"), dict) else None)
        if w is None:
            return 0.0
        try:
            return float(w)
        except (TypeError, ValueError):
            return 0.0
    return float(getattr(item, "weight", 0) or 0)


def item_type(item):
    if isinstance(item, dict):
        return str(item.get("type") or "")
    return str(getattr(item, "type", "") or "")


def item_id(item):
    if isinstance(item, dict):
        return str(item.get("id") or item.get("_id") or item.get("source_id") or item.get("name") or "")
    return str(getattr(item, "id", None) or getattr(item, "source_id", None) or getattr(item, "name", "") or "")


def item_name(item):
    if isinstance(item, dict):
        return str(item.get("name") or item_id(item) or "item")
    return str(getattr(item, "name", None) or item_id(item) or "item")


def item_flag(item, key, default=None):
    """Read a breath-and-the-veil flag, or the same key on the item / system."""
    if not isinstance(item, dict):
        flags = getattr(item, "flags", {}) or {}
        breath = flags.get("breath-and-the-veil") or flags.get("breath") or {}
        if key in breath:
            return breath[key]
        return getattr(item, key, default)
    flags = item.get("flags") or {}
    breath = flags.get("breath-and-the-veil") or flags.get("breath") or {}
    if key in breath:
        return breath[key]
    system = item.get("system") if isinstance(item.get("system"), dict) else {}
    if key in item:
        return item[key]
    if key in system:
        return system[key]
    # camelCase in Foundry flags
    camel = {"container_id": "containerId", "is_container": "isContainer"}.get(key, key)
    if camel in breath:
        return breath[camel]
    if camel in system:
        return system[camel]
    return default


def is_physical(item):
    return item_type(item) in PHYSICAL_TYPES


def is_container(item):
    if item_flag(item, "is_container") or item_flag(item, "isContainer"):
        return True
    cap = item_flag(item, "capacity_kg", item_flag(item, "capacityKg"))
    return cap is not None and float(cap or 0) > 0 and item_type(item) == "gear"


def container_capacity_kg(item):
    cap = item_flag(item, "capacity_kg", item_flag(item, "capacityKg"))
    if cap is None and isinstance(item, dict):
        rules = (item.get("system") or {}).get("rules") if isinstance(item.get("system"), dict) else item.get("rules")
        if isinstance(rules, dict):
            cap = rules.get("capacity_kg")
    try:
        return float(cap or 0)
    except (TypeError, ValueError):
        return 0.0


def location_of(item):
    loc = item_flag(item, "location")
    if loc:
        return str(loc)
    if item_flag(item, "equipped"):
        return "body"
    return ""


def source_id(item):
    if isinstance(item, dict):
        system = item.get("system") if isinstance(item.get("system"), dict) else {}
        return str(item.get("source_id") or system.get("source_id") or item.get("id") or "")
    return str(getattr(item, "source_id", None) or "")


def coverage_of(item):
    if isinstance(item, dict):
        system = item.get("system") if isinstance(item.get("system"), dict) else {}
        cov = item.get("coverage") or system.get("coverage") or []
        return list(cov)
    return list(getattr(item, "coverage", None) or [])


def worn_slot(item):
    """Explicit worn slot for gear (back, belt)."""
    return item_flag(item, "slot") or (item.get("slot") if isinstance(item, dict) else None) or ""


def weapon_type_of(item):
    if isinstance(item, dict):
        system = item.get("system") if isinstance(item.get("system"), dict) else {}
        return str(item.get("weapon_type") or system.get("weapon_type") or "")
    return str(getattr(item, "weapon_type", "") or "")


def is_two_handed(item, grip="two_hands"):
    """See rules/inventory.json two_handed. Some entries are placeholders."""
    if item_type(item) != "weapon":
        return False
    sid = source_id(item)
    wtype = weapon_type_of(item)
    cfg = RULES["two_handed"]
    if sid == "longsword":
        return str(grip).lower() != "one_hand"
    for prefix in cfg["type_prefixes"]:
        if wtype.startswith(prefix):
            return True
    if wtype in cfg["assumed_types"]:
        return True
    if sid in cfg["assumed_source_ids"]:
        return True
    return False


def body_slots_for(item, grip="two_hands"):
    """Slots this item would occupy if worn or wielded on the body."""
    typ = item_type(item)
    if typ == "armor":
        return list(coverage_of(item))
    if typ == "weapon":
        if is_two_handed(item, grip):
            return ["main_hand", "off_hand"]
        return ["main_hand"]
    if typ == "gear":
        slot = worn_slot(item)
        return [slot] if slot else []
    return []


def occupied_body_slots(items, excluding_id=None, grip="two_hands"):
    taken = {}
    for it in items:
        if not is_physical(it):
            continue
        if excluding_id and item_id(it) == excluding_id:
            continue
        if location_of(it) != "body":
            continue
        for slot in body_slots_for(it, grip):
            taken[slot] = item_id(it)
    return taken


def contents_weight(container, items):
    cid = item_id(container)
    total = 0.0
    for it in items:
        if location_of(it) == "backpack" and str(item_flag(it, "container_id") or "") == cid:
            total += item_weight(it)
    return total


def carried_weight(items, clinch_mass_kg=0):
    """Everything the person is physically carrying: worn, packs, pack contents, plus clinch mass."""
    total = 0.0
    for it in items:
        if is_physical(it) and location_of(it) in ("body", "backpack"):
            total += item_weight(it)
    return total + float(clinch_mass_kg or 0)


def load_ratio(weight_kg, capacity_kg):
    if not capacity_kg or capacity_kg <= 0:
        return float("inf") if weight_kg else 0.0
    return weight_kg / capacity_kg


def load_tier(ratio):
    """Named band from combat_rules.json load_bands, plus placeholder 'overloaded' above 1.0."""
    if ratio > 1.0:
        return "overloaded"
    for band in RULES["load_bands"]:
        max_r = band.get("max_ratio")
        if max_r is not None and ratio <= max_r:
            return band["name"]
    return "overloaded"


def band_by_name(name):
    for band in RULES["load_bands"]:
        if band["name"] == name:
            return band
    return {}


def action_economy_penalties(ratio):
    """AP and speed from action_economy_v0_1.json, looked up by load ratio (not by named load_band)."""
    for band in RULES["action_economy_encumbrance"]["bands"]:
        max_r = band.get("max_ratio")
        if max_r is None or ratio <= max_r:
            return {
                "ap_penalty": band["ap_penalty"],
                "speed_penalty_pct": band["speed_penalty_pct"],
                "economy_band": band["name"],
                "placeholder": bool(band.get("placeholder")),
            }
    last = RULES["action_economy_encumbrance"]["bands"][-1]
    return {
        "ap_penalty": last["ap_penalty"],
        "speed_penalty_pct": last["speed_penalty_pct"],
        "economy_band": last["name"],
        "placeholder": True,
    }


def tier_penalties(tier, gender="male"):
    """Stamina and stat penalties from the load band, plus placeholder action restrictions."""
    band = band_by_name(tier)
    male = str(gender).lower().startswith("m")
    out = {
        "stamina_regen_pct": band.get("male_stamina_regen_pct" if male else "female_stamina_regen_pct", 0) or 0,
        "stamina_drain_pct": band.get("male_stamina_drain_pct" if male else "female_stamina_drain_pct", 0) or 0,
        "dex_aim_penalty": 0 if male else (band.get("female_dex_aim_penalty") or 0),
        "agility_penalty": (band.get("male_agility_penalty") or 0) if male else 0,
    }
    restrictions = RULES["action_restrictions"]["by_tier"].get(tier, {})
    out["blocked"] = list(restrictions.get("blocked") or [])
    out["action_penalties"] = restrictions.get("penalties") or {}
    out["placeholder_restrictions"] = bool(RULES["action_restrictions"].get("placeholder"))
    return out


def action_allowed(tier, action_id):
    """Whether a movement or skill action may be used at this load tier. Software decides; the UI greys it out."""
    blocked = set(RULES["action_restrictions"]["by_tier"].get(tier, {}).get("blocked") or [])
    return action_id not in blocked


def action_penalty(tier, action_id):
    penalties = RULES["action_restrictions"]["by_tier"].get(tier, {}).get("penalties") or {}
    return penalties.get(action_id) or penalties.get("climb" if action_id.startswith("climb") or action_id == "climb" else action_id)


def missing_weight(item):
    sid = source_id(item)
    typ = item_type(item)
    if typ == "weapon" and sid in RULES["missing_weights"]["weapons"]:
        return True
    if typ in PHYSICAL_TYPES:
        raw = None
        if isinstance(item, dict):
            system = item.get("system") if isinstance(item.get("system"), dict) else {}
            raw = item.get("weight", system.get("weight"))
        else:
            raw = getattr(item, "weight", None)
        return raw is None
    return False


def equipped_containers(items):
    return [it for it in items if is_physical(it) and is_container(it) and location_of(it) == "body"]


def choose_container(items, weight_kg, volume=None):
    """Prefer the worn pack with enough free kg (and volume if both sides have a number)."""
    candidates = []
    for pack in equipped_containers(items):
        cap = container_capacity_kg(pack)
        used = contents_weight(pack, items)
        if used + weight_kg > cap + 1e-9:
            continue
        vol_cap = item_flag(pack, "capacity_volume") or item_flag(pack, "capacityVolume")
        if volume is not None and vol_cap is not None:
            # Volume is a placeholder field; only enforced when both numbers exist.
            used_vol = 0.0
            cid = item_id(pack)
            for it in items:
                if location_of(it) == "backpack" and str(item_flag(it, "container_id") or "") == cid:
                    v = item_flag(it, "volume")
                    if v is not None:
                        used_vol += float(v)
            if used_vol + float(volume) > float(vol_cap) + 1e-9:
                continue
        candidates.append((cap - used, pack))
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def _slots_free(needed, taken):
    return all(slot not in taken for slot in needed)


def place_item(items, new_item, grip="two_hands"):
    """Decide where a dropped physical item goes.

    Body first (if it has a slot and those slots are free), otherwise into a worn
    backpack that has enough free kg. If neither is possible, refuse with a message.
    Class, race, gender and other non-physical items are accepted and ignored here.

    Going over *character* carry capacity is allowed (penalties apply). Refusal is
    only for no free body slot and no room in a pack.
    """
    if not is_physical(new_item):
        typ = item_type(new_item)
        if typ in NON_PHYSICAL_TYPES or typ == "":
            return {"ok": True, "location": None, "slot": None, "container_id": None,
                    "equipped": False, "message": "", "physical": False}
        return {"ok": False, "location": None, "slot": None, "container_id": None,
                "equipped": False, "message": f"{item_name(new_item)} is not a carryable item.",
                "physical": False}

    name = item_name(new_item)
    weight = item_weight(new_item)
    needed = body_slots_for(new_item, grip)
    taken = occupied_body_slots(items, excluding_id=item_id(new_item) or None, grip=grip)

    # Worn containers (backpacks, pouches) try their slot first.
    if is_container(new_item) and needed:
        if _slots_free(needed, taken):
            return {"ok": True, "location": "body", "slot": needed[0], "container_id": None,
                    "equipped": True, "message": f"{name} is worn.", "physical": True,
                    "slots": needed}
        slot = needed[0]
        holder = taken.get(slot)
        return {"ok": False, "location": None, "slot": None, "container_id": None,
                "equipped": False,
                "message": f"You already have something on your {slot.replace('_', ' ')}"
                           + (f" ({holder})" if holder else "") + f", so {name} cannot be worn.",
                "physical": True}

    if needed and _slots_free(needed, taken):
        return {"ok": True, "location": "body", "slot": needed[0], "container_id": None,
                "equipped": True, "message": f"{name} is equipped.", "physical": True,
                "slots": needed}

    pack = choose_container(items, weight, item_flag(new_item, "volume"))
    if pack:
        why = "Those slots are already taken, so" if needed else "There is no body slot for this,"
        return {"ok": True, "location": "backpack", "slot": None, "container_id": item_id(pack),
                "equipped": False,
                "message": f"{why} {name} goes into {item_name(pack)}.",
                "physical": True, "slots": []}

    packs = equipped_containers(items)
    if needed and not packs:
        slots = ", ".join(s.replace("_", " ") for s in needed)
        return {"ok": False, "location": None, "slot": None, "container_id": None,
                "equipped": False,
                "message": f"No free slot ({slots}) for {name}, and you are not wearing a pack to stow it in.",
                "physical": True}
    if not packs:
        return {"ok": False, "location": None, "slot": None, "container_id": None,
                "equipped": False,
                "message": f"You have no backpack or pouch with room for {name}.",
                "physical": True}

    # Packs exist but are full.
    parts = []
    for p in packs:
        cap = container_capacity_kg(p)
        used = contents_weight(p, items)
        parts.append(f"{item_name(p)} {used:.1f}/{cap:.1f} kg")
    return {"ok": False, "location": None, "slot": None, "container_id": None,
            "equipped": False,
            "message": f"No room for {name} ({weight:.1f} kg). " + "; ".join(parts) + ".",
            "physical": True}


def evaluate(strength, gender, race, items, talents=(), clinch_mass_kg=0, grip="two_hands"):
    """Full load picture for a character. This is what Foundry should display."""
    cap = carry_capacity(strength, gender, race, talents)
    weight = carried_weight(items, clinch_mass_kg)
    ratio = load_ratio(weight, cap)
    tier = load_tier(ratio)
    penalties = tier_penalties(tier, gender)
    economy = action_economy_penalties(ratio)
    past_half = ratio > S.MARCH_CLIFF_START
    actions = {}
    for action in ("sprint", "acrobatics", "climb", "rope_climb_unaided", "walk"):
        allowed = True if action == "walk" else action_allowed(tier, action)
        actions[action] = {
            "allowed": allowed,
            "penalty": action_penalty(tier, action),
        }
    return {
        "capacity_kg": cap,
        "carried_kg": weight,
        "clinch_mass_kg": float(clinch_mass_kg or 0),
        "ratio": ratio,
        "tier": tier,
        "past_half_load": past_half,
        "penalties": penalties,
        "action_economy": economy,
        "actions": actions,
        "missing_weight_items": [item_name(it) for it in items if missing_weight(it)],
    }


# Actions the Foundry sheet should show and grey out automatically.
TRACKED_ACTIONS = (
    ("walk", "Walk"),
    ("sprint", "Sprint"),
    ("acrobatics", "Acrobatics"),
    ("climb", "Climb"),
    ("rope_climb_unaided", "Climb a rope (unaided)"),
)


EQUIP_SLOTS = (
    tuple(RULES["equip_slots"]["armor_zones"])
    + tuple(RULES["equip_slots"]["hands"])
    + tuple(RULES["equip_slots"]["worn"])
)


def container_id_of(item):
    if isinstance(item, dict):
        system = item.get("system") if isinstance(item.get("system"), dict) else {}
        return str(system.get("container_id") or item_flag(item, "container_id") or "")
    return str(getattr(getattr(item, "system", None), "container_id", None) or item_flag(item, "container_id") or "")


def actor_inventory_state(items, strength, gender, race="Human", talents=(), clinch_mass_kg=0, grip="two_hands"):
    """Mirror of foundry/system/docs/ACTOR_MODEL.md system.inventory (for tests and the backend)."""
    ev = evaluate(strength, gender, race, items, talents, clinch_mass_kg, grip)
    equipped = {s: "" for s in EQUIP_SLOTS}
    pack = None
    for it in items:
        if not is_physical(it) or location_of(it) != "body":
            continue
        iid = item_id(it)
        for slot in body_slots_for(it, grip):
            if slot in equipped and not equipped[slot]:
                equipped[slot] = iid
        if is_container(it) and "back" in body_slots_for(it, grip):
            pack = it
    if pack is None:
        packs = equipped_containers(items)
        pack = packs[0] if packs else None
    contents = [item_id(it) for it in items
                if location_of(it) == "backpack" and pack and container_id_of(it) == item_id(pack)] if pack else []
    return {
        "equipped": equipped,
        "backpack": {"itemId": item_id(pack) if pack else "", "contents": contents},
        "carried_weight": ev["carried_kg"],
        "carry_capacity": ev["capacity_kg"],
    }
