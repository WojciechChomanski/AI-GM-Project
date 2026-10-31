# file: scripts/progression.py
"""Use-based growth, weapon/style mastery and action points (docs/PROGRESSION.md).
State is stored PER CHARACTER in character.progression (a plain dict, JSON-safe).
ALL NUMBERS ARE PLACEHOLDERS."""
import json
import math
import os

import talents as T

ROOT = os.path.join(os.path.dirname(__file__), "..")
with open(os.path.join(ROOT, "rules", "progression.json"), encoding="utf-8-sig") as _f:
    RULES = json.load(_f)
G = RULES["growth"]
M = RULES["mastery"]
CEIL = M["ceiling"]
MELEE_FAMILIES = [f for f in M["weapon_families"] if f not in ("bow", "crossbow", "thrown", "gunpowder")]
RANGED_FAMILIES = ("bow", "crossbow", "thrown", "gunpowder")


def _get(c, key, default=None):
    return c.get(key, default) if isinstance(c, dict) else getattr(c, key, default)


def _set(c, key, value):
    if isinstance(c, dict):
        c[key] = value
    else:
        setattr(c, key, value)


def state(c):
    """Per-character progression dict: {'uses': {}, 'session': {}, 'mastery': {}}."""
    st = _get(c, "progression")
    if not isinstance(st, dict):
        st = {}
        _set(c, "progression", st)
    for k in ("uses", "session", "mastery"):
        st.setdefault(k, {})
    return st


# --- Growth ---------------------------------------------------------------
def uses_needed(current, cap, mult=1.0):
    """30 + (current-30)*12 (min 30); x2 in the last 5 points before the cap; times talent mult."""
    base = max(30, 30 + (current - 30) * 12)
    if current >= cap - G["near_cap_points"]:
        base *= G["near_cap_mult"]
    return math.ceil(base * mult)


def stat_cap_for(c, stat):
    from character import load_stats
    from strength import stat_cap
    base = load_stats(_get(c, "race"), _get(c, "gender"))["max_stats"].get(stat, 50)
    return stat_cap(base, _get(c, "race"), _get(c, "gender"), stat, _get(c, "talents", []) or [])


def record_use(c, stat, amount=1, failed=False):
    st = state(c)
    st["uses"][stat] = st["uses"].get(stat, 0) + amount * (G["failure_counts"] if failed else 1)


def record_action(c, action, failed=False):
    """Record one use of an action from rules/progression.json growth.uses (e.g. 'melee_attack')."""
    for stat, n in G["uses"].get(action, {}).items():
        record_use(c, stat, n, failed)


def check_growth(c, cap_fn=None):
    """+1 to each stat whose uses reached the threshold. Max 1 point per stat per session."""
    cap_fn = cap_fn or stat_cap_for
    st = state(c)
    msgs = []
    race, gender, tal = _get(c, "race"), _get(c, "gender"), _get(c, "talents", []) or []
    for stat, uses in list(st["uses"].items()):
        if st["session"].get(stat, 0) >= G["max_points_per_stat_per_session"]:
            continue
        cur = _get(c, stat, 30) or 0
        cap = cap_fn(c, stat)
        if cur >= cap:
            continue
        need = uses_needed(cur, cap, T.growth_mult(stat, race, gender, tal))
        if uses >= need:
            _set(c, stat, cur + 1)
            st["uses"][stat] = uses - need
            st["session"][stat] = st["session"].get(stat, 0) + 1
            msgs.append(f"{_get(c, 'name', 'Character')}'s {stat.replace('_', ' ')} improved to {cur + 1}!")
    return msgs


def new_session(c):
    state(c)["session"] = {}


# --- Weapons / mastery ----------------------------------------------------
def weapon_family(weapon):
    """Family id for a weapon dict (from rules/weapons.json) or a weapon key."""
    if isinstance(weapon, str):
        key, wtype = weapon, None
    else:
        weapon = weapon or {}
        key, wtype = str(weapon.get("key") or weapon.get("name", "")).lower().replace(" ", "_"), weapon.get("type")
    if key in M["ranged_name_to_family"]:
        return M["ranged_name_to_family"][key]
    if wtype in M["weapon_type_to_family"]:
        return M["weapon_type_to_family"][wtype]
    if wtype == "ranged":
        return "crossbow" if "crossbow" in key or "arbalest" in key else "bow"
    if wtype in ("gun", "firearm", "gunpowder"):
        return "gunpowder"
    return None


def is_ranged(weapon):
    return weapon_family(weapon) in RANGED_FAMILIES


def attack_skill(c, weapon):
    """Ranged and thrown attacks use Ballistic Skill; melee uses Weapon Skill."""
    if is_ranged(weapon):
        return _get(c, "ballistic_skill", 0) or 0
    return _get(c, "weapon_skill", 0) or 0


def rank_for_uses(uses, mult=1.0):
    return sum(1 for need in M["rank_uses"] if uses >= math.ceil(need * mult))


def record_mastery(c, track, amount=1):
    st = state(c)
    st["mastery"][track] = st["mastery"].get(track, 0) + amount


def mastery_rank(c, track):
    mult = T.mastery_uses_mult(track, _get(c, "race"), _get(c, "gender"), _get(c, "talents", []) or [], MELEE_FAMILIES)
    return rank_for_uses(state(c)["mastery"].get(track, 0), mult)


def _gains(rank, table):
    out = {"to_hit": 0, "damage": 0, "stamina": 0, "block": 0, "bash_damage": 0, "trick": False}
    for g in table[:rank]:
        for k, v in g.items():
            out[k] = v if k == "trick" else out[k] + v
    return out


def mastery_modifiers(c, weapon, style=None):
    """Bonuses for one attack. Family and style (two_hander) do not stack: best of each value.
    Hard ceiling: +5 to hit, +1 damage, -2 stamina, one trick."""
    fam = weapon_family(weapon)
    mods = _gains(mastery_rank(c, fam), M["weapon_rank_gains"]) if fam else _gains(0, [])
    if style == "two_hander":
        s = _gains(mastery_rank(c, "two_hander"), M["weapon_rank_gains"])
        for k in ("to_hit", "damage"):
            mods[k] = max(mods[k], s[k])
        mods["stamina"] = min(mods["stamina"], s["stamina"])
        mods["trick"] = mods["trick"] or s["trick"]
    elif style == "shield":
        s = _gains(mastery_rank(c, "shield"), M["shield_rank_gains"])
        mods["block"], mods["bash_damage"] = s["block"], s["bash_damage"]
        mods["shield_stamina"] = max(CEIL["stamina"], s["stamina"])
    mods["to_hit"] = min(mods["to_hit"], CEIL["to_hit"])
    mods["damage"] = min(mods["damage"], CEIL["damage"])
    mods["stamina"] = max(mods["stamina"], CEIL["stamina"])
    mods["family"] = fam
    return mods


def stamina_per_attack(base_cost, mods):
    """Weapon stamina cost after mastery, never below 2 (or the base if it is already lower)."""
    return max(min(base_cost, CEIL["min_stamina_per_attack"]), base_cost + mods.get("stamina", 0))


def dual_wield_offhand_penalty(c, base_penalty=-25):
    return min(0, base_penalty + 5 * mastery_rank(c, "dual_wield"))


# --- Action points (rules/combat/action_economy_v0_1.json v0.2) ------------
def action_points(agility, encumbrance_penalty=0):
    return max(4, 6 + math.floor((agility - 25) / 15) - encumbrance_penalty)
