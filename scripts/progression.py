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
with open(os.path.join(ROOT, "rules", "weapon_perks.json"), encoding="utf-8-sig") as _f:
    PERKS = json.load(_f)
PCAPS = PERKS["_caps"]
LADDERS = PERKS["ladders"]
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
_WEAPONS = None


def _weapons():
    global _WEAPONS
    if _WEAPONS is None:
        with open(os.path.join(ROOT, "rules", "weapons.json"), encoding="utf-8-sig") as f:
            _WEAPONS = json.load(f)
    return _WEAPONS


def weapon_family(weapon):
    """Family id for a weapon dict (from rules/weapons.json) or a weapon key."""
    if isinstance(weapon, str):
        key = weapon.lower().replace(" ", "_")
        wtype = _weapons().get(key, {}).get("type")
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


def _ladder_slots(family):
    """[(rank, slot, [perk options])] for a family's ladder; auto slots have 1 option."""
    out = []
    for rank, entry in (LADDERS.get(family) or {}).items():
        items = entry if isinstance(entry, list) else [entry]
        for i, it in enumerate(items):
            out.append((int(rank), i, it["pick"] if isinstance(it, dict) and "pick" in it else [it]))
    return out


def perk_options(family, rank):
    return [p["id"] for r, _, opts in _ladder_slots(family) if r == rank and len(opts) > 1 for p in opts]


def choose_perk(c, family, rank, perk_id):
    """Pick one of a 'pick 1 of 2' perk. Permanent per family and rank."""
    if perk_id not in perk_options(family, rank):
        raise ValueError(f"{perk_id} is not a pick for {family} rank {rank}")
    st = state(c)
    picks = st.setdefault("perks", {}).setdefault(family, {})
    if str(rank) in picks and picks[str(rank)] != perk_id:
        raise ValueError(f"{family} rank {rank} already chose {picks[str(rank)]}")
    picks[str(rank)] = perk_id


def pending_perk_picks(c):
    """[(family, rank, [option ids])] for every 'pick 1 of 2' the character has reached but not chosen.
    The GM console shows these (`perks <name>`) and records a choice with `pick`."""
    out = []
    for fam in LADDERS:
        rank = mastery_rank(c, fam)
        picks = state(c).get("perks", {}).get(fam, {})
        for r, _, opts in _ladder_slots(fam):
            if r <= rank and len(opts) > 1 and str(r) not in picks:
                out.append((fam, r, [o["id"] for o in opts]))
    return out


def active_perks(c, weapon):
    """Perks of the family of the weapon IN HAND only (no cross-family stacking)."""
    fam = weapon_family(weapon)
    if fam not in LADDERS:
        return []
    rank = mastery_rank(c, fam)
    picks = state(c).get("perks", {}).get(fam, {})
    out = []
    for r, _, opts in _ladder_slots(fam):
        if r > rank:
            continue
        if len(opts) == 1:
            out.append(opts[0])
        else:
            out += [p for p in opts if p["id"] == picks.get(str(r))]
    return out


def perk_effects(c, weapon):
    """Merged perk effects for the weapon in hand, with global caps applied."""
    fx = {"free_guard_changes": 0, "maneuver_extra_stances": {}, "maneuver_extra_triggers": {},
          "maneuver_stamina": {}, "maneuver_attack": {}, "maneuver_aim_relief": {}, "guard_mods": {},
          "damage_vs_light": [], "aim_relief": [], "armor_piercing": 0, "ring_on_head": False, "tricks": [], "ids": []}
    for p in active_perks(c, weapon):
        fx["ids"].append(p["id"])
        for k, v in p["effects"].items():
            if k in ("free_guard_changes", "armor_piercing"):
                fx[k] += v
            elif k in ("maneuver_extra_stances", "maneuver_extra_triggers"):
                for n, lst in v.items():
                    fx[k].setdefault(n, []).extend(lst)
            elif k in ("maneuver_stamina", "maneuver_attack", "maneuver_aim_relief"):
                for n, d in v.items():
                    fx[k][n] = fx[k].get(n, 0) + d
            elif k == "guard_mods":
                for g, mods in v.items():
                    cur = fx[k].setdefault(g, {"attack": 0, "defense": 0})
                    for mk, mv in mods.items():
                        cur[mk] = cur.get(mk, 0) + mv
            elif k in ("damage_vs_light", "aim_relief"):
                fx[k].append(v)
            elif k == "ring_on_head":
                fx[k] = fx[k] or bool(v)
            elif k == "trick":
                fx["tricks"].append(v)
    red = PCAPS["stamina_reduction"]
    fx["maneuver_stamina"] = {n: max(-red, d) for n, d in fx["maneuver_stamina"].items()}
    fx["maneuver_attack"] = {n: min(PCAPS["to_hit"], d) for n, d in fx["maneuver_attack"].items()}
    fx["maneuver_aim_relief"] = {n: min(PCAPS["aim_relief"], d) for n, d in fx["maneuver_aim_relief"].items()}
    for g in fx["guard_mods"].values():
        g["defense"] = min(PCAPS["defense"], g.get("defense", 0))
    fx["tricks"] = fx["tricks"][:PCAPS["tricks_per_fight"]]
    return fx


def mastery_modifiers(c, weapon, style=None):
    """Bonuses for one attack. Families with a perk ladder (rules/weapon_perks.json) get +5 to hit at rank 2
    and their perks; other families keep the generic weapon_rank_gains. Family and style (two_hander) do not
    stack: best of each value. Hard ceiling: +5 to hit, +2 damage, -2 stamina, one trick."""
    fam = weapon_family(weapon)
    if fam in LADDERS:
        rank = mastery_rank(c, fam)
        mods = _gains(0, [])
        for r, g in PERKS["_rank_gains"].items():
            if rank >= int(r):
                for k, v in g.items():
                    mods[k] += v
        fx = perk_effects(c, weapon)
        mods["trick"] = bool(fx["tricks"])
        mods["perks"] = fx["ids"]
    else:
        mods = _gains(mastery_rank(c, fam), M["weapon_rank_gains"]) if fam else _gains(0, [])
        mods["perks"] = []
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
