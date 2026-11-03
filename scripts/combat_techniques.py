# file: scripts/combat_techniques.py
"""Guards (stances), weapon maneuvers, damage types and armour defeat - one source of truth.
Reads rules/stances.json, rules/weapon_stances.json, rules/weapon_maneuvers.json, rules/damage_types.json,
rules/weapons.json and rules/armors.json. See docs/COMBAT_STANCES_MANEUVERS.md."""
import json
import os
import random

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _load(name):
    with open(os.path.join(ROOT, "rules", name), encoding="utf-8-sig") as f:
        return json.load(f)


STANCES = _load("stances.json")
_WS = _load("weapon_stances.json")
GUARD_SETS = _WS["guard_sets"]
GUARD_CHANGE_COST = int(_WS["_meta"]["guard_change"]["stamina_cost"])
_WM = _load("weapon_maneuvers.json")
MANEUVERS = {k: v for k, v in _WM.items() if not k.startswith("_")}
DAMAGE_TYPES = _load("damage_types.json")
DAMAGE_TYPE_NAMES = ("slashing", "piercing", "blunt")
_DEFEAT = DAMAGE_TYPES["armor_defeat"]
ARMOR_DEFEAT_MAX = int(_DEFEAT["max"])
ARMOR_DEFEAT_TRICK = int(_DEFEAT["max_once_per_fight"])
WEAPONS = _load("weapons.json")
ARMS = {"left_upper_arm", "left_lower_arm", "right_upper_arm", "right_lower_arm"}
LEGS = {"left_upper_leg", "left_lower_leg", "right_upper_leg", "right_lower_leg"}
GENERIC = ("offensive", "defensive", "neutral")


def as_list(v):
    if v is None:
        return []
    return list(v) if isinstance(v, (list, tuple)) else [v]


def weapon_data(weapon):
    """Weapon dict (from weapons.json, by key or dict). Unknown -> {}."""
    if isinstance(weapon, str):
        return dict(WEAPONS.get(weapon, {}), key=weapon)
    if isinstance(weapon, dict):
        key = weapon.get("key") or str(weapon.get("name", "")).lower().replace(" ", "_")
        base = WEAPONS.get(key, {})
        out = dict(base)
        out.update(weapon)
        out["key"] = key
        return out
    return {}


# --- Guards / stances ------------------------------------------------------
def generic_stance(stype):
    """(attack, defence) for a generic stance type, from rules/stances.json."""
    s = STANCES.get(str(stype or "neutral").lower(), STANCES["neutral"])
    return (s.get("attack_bonus", 0) - s.get("attack_penalty", 0),
            s.get("defense_bonus", 0) - s.get("defense_penalty", 0))


def guard_set(weapon):
    return GUARD_SETS.get(weapon_data(weapon).get("guard_set") or "", None)


def guards_for(weapon):
    """Guards this weapon can reach (its stance_tree, limited to its guard set)."""
    w = weapon_data(weapon)
    gs = guard_set(w)
    if not gs:
        return []
    return [g for g in w.get("stance_tree", []) if g in gs["stances"]]


def guard_info(weapon, stance):
    """Normalized guard: {'id','type','attack','defense','initiative','stamina':{offensive,defensive}}.
    A generic stance name (offensive/defensive/neutral) uses rules/stances.json; an unknown guard falls back
    to the weapon's default guard (or neutral)."""
    stance = str(stance or "").lower() or None
    gs = guard_set(weapon)
    if stance in GENERIC or not gs:
        stype = stance if stance in GENERIC else "neutral"
        a, d = generic_stance(stype)
        sm = STANCES.get(stype, {}).get("stamina_cost_modifier", {})
        return {"id": stype, "type": stype, "attack": a, "defense": d, "initiative": 0,
                "stamina": {"offensive": sm.get("offensive", 0), "defensive": sm.get("defensive", 0)}, "valid": True}
    valid = stance in guards_for(weapon)
    gid = stance if valid else gs["default_stance"]
    g = gs["stances"][gid]
    return {"id": gid, "type": g["type"], "valid": valid, "name": g.get("name", gid),
            "attack": g.get("attack_bonus", 0) - g.get("attack_penalty", 0),
            "defense": g.get("defense_bonus", 0) - g.get("defense_penalty", 0),
            "initiative": g.get("initiative_bonus", 0),
            "stamina": dict(g.get("stamina_modifier", {"offensive": 0, "defensive": 0}))}


def stance_modifiers(stance, weapon=None):
    """(attack, defence) modifiers for a stance or guard. Used by adventure*.py and stance_logic.py."""
    g = guard_info(weapon, stance)
    return g["attack"], g["defense"]


def guard_change_cost(previous, new, free_left=0, free_trick=False):
    """Stamina to change guard (rules/weapon_stances.json _meta.guard_change). 0 if unchanged or free."""
    if not previous or not new or previous == new or free_trick or free_left > 0:
        return 0
    return GUARD_CHANGE_COST


# --- Maneuvers ---------------------------------------------------------------
def maneuvers_for(weapon):
    w = weapon_data(weapon)
    return MANEUVERS.get(w.get("guard_set") or "", [])


def find_maneuver(weapon, name):
    for m in maneuvers_for(weapon):
        if m["name"].lower() == str(name).lower():
            return m
    return None


def maneuver_valid(m, weapon, stance, trigger="always", aimed_zone=None, perks=None, any_guard=False):
    """List-or-string matching for stance_required / trigger / aimed_zone (fixes the old == bug)."""
    perks = perks or {}
    w = weapon_data(weapon)
    need = m["effects"].get("requires_feature")
    if need and need not in w.get("features", []):
        return False
    stances = as_list(m["stance_required"]) + perks.get("maneuver_extra_stances", {}).get(m["name"], [])
    if any_guard:
        stances = guards_for(w)
    if stance not in stances or stance not in guards_for(w):
        return False
    triggers = as_list(m["trigger"]) + perks.get("maneuver_extra_triggers", {}).get(m["name"], [])
    if "always" not in triggers and (trigger or "always") not in triggers:
        return False
    zones = m["effects"].get("aimed_zone")
    if zones:
        return bool(aimed_zone) and aimed_zone in as_list(zones)
    return True


def valid_maneuvers(weapon, stance, trigger="always", aimed_zone=None, perks=None, any_guard=False):
    return [m for m in maneuvers_for(weapon) if maneuver_valid(m, weapon, stance, trigger, aimed_zone, perks, any_guard)]


def maneuver_stamina(m, perks=None):
    """Extra stamina for a maneuver after perks (never below 0)."""
    if not m:
        return 0
    base = m["effects"].get("stamina_cost_modifier", 0)
    return max(0, base + (perks or {}).get("maneuver_stamina", {}).get(m["name"], 0))


def maneuver_perk_reduction(m, perks=None):
    if not m:
        return 0
    base = m["effects"].get("stamina_cost_modifier", 0)
    return base - maneuver_stamina(m, perks)


# --- Damage types and armour -------------------------------------------------
def spec_covers(spec, zone):
    cov = spec.get("coverage")
    return zone is None or not cov or zone in cov


def armor_rating(spec, dtype, percussive=False):
    r = spec.get("armor_rating", {})
    val = r.get(dtype, 0)
    if percussive and dtype == "slashing" and spec.get("rigid"):
        val = min(val, r.get("blunt", val))
    return val


def effective_armor(specs, dtype, zone=None, bypass=0.0, defeat=0, percussive=False):
    """Total armour against one hit: each covering layer = rating x (1-bypass) - defeat, never below 0."""
    total = 0
    for s in specs:
        if not spec_covers(s, zone):
            continue
        val = armor_rating(s, dtype, percussive)
        if val <= 0:
            continue
        total += max(0, int(round(val * (1 - bypass))) - defeat)
    return total


def raw_armor(specs, dtype, zone=None):
    return sum(s.get("armor_rating", {}).get(dtype, 0) for s in specs if spec_covers(s, zone))


def type_damage_mod(dtype, raw_rating):
    """Damage-type trade-offs from rules/damage_types.json."""
    d = DAMAGE_TYPES.get(dtype, {})
    mod = d.get("damage_mod", 0)
    light = d.get("bonus_vs_light")
    if light and raw_rating <= light["max_armor"]:
        mod += light["damage"]
    return mod


def pick_zone(specs, zones, dtype):
    """From a zone or list of zones, the least protected one."""
    zones = as_list(zones)
    if not zones:
        return None
    return min(zones, key=lambda z: raw_armor(specs, dtype, z))


def best_damage_type(weapon, specs, base_damage, zone=None, bypass=0.0, defeat=0, choices=None):
    """The weapon type (or forced choices) that gets the most damage through this armour."""
    w = weapon_data(weapon)
    types = as_list(choices) or w.get("damage_types") or [w.get("damage_type", "blunt")]
    perc = bool(w.get("percussive"))

    def through(t):
        return base_damage + type_damage_mod(t, raw_armor(specs, t, zone)) - effective_armor(specs, t, zone, bypass, defeat, perc)
    return max(types, key=lambda t: (through(t), -types.index(t)))


def score_maneuver(m, weapon, specs, base_damage, defeat=0):
    e = m["effects"]
    zone = pick_zone(specs, e.get("target_zone"), e.get("damage_type") or "slashing")
    t = e.get("damage_type") or best_damage_type(weapon, specs, base_damage, zone, 0, defeat)
    perc = bool(weapon_data(weapon).get("percussive"))
    through = max(0, base_damage + e.get("damage_bonus", 0) + type_damage_mod(t, raw_armor(specs, t, zone))
                  - effective_armor(specs, t, zone, e.get("armor_bypass", 0), defeat, perc))
    return through * 2 + e.get("attack_bonus", 0) + e.get("defense_bonus", 0) / 2 - e.get("stamina_cost_modifier", 0)


def choose_maneuver(weapon, stance, trigger="always", aimed_zone=None, perks=None, name=None,
                    specs=None, base_damage=10, defeat=0, any_guard=False):
    """ONE maneuver per action: the named one if valid, else the best valid one (or None).
    Returns (maneuver or None, note)."""
    opts = valid_maneuvers(weapon, stance, trigger, aimed_zone, perks, any_guard)
    if name:
        for m in opts:
            if m["name"].lower() == str(name).lower():
                return m, "chosen"
        return None, f"{name} is not valid here (guard {stance}, trigger {trigger})"
    if not opts:
        return None, "no valid maneuver"
    return max(opts, key=lambda m: score_maneuver(m, weapon, specs or [], base_damage, defeat)), "best valid"


def roll_chance(pct, rng=random):
    return pct > 0 and rng.randint(1, 100) <= pct
