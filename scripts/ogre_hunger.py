"""Ogre hunger (rules/ogre_hunger.json, docs/OGRES.md). Backend only: hidden numbers, felt text out.

State on the character: c.hunger = {points, kcal_today}. The legacy fields calories_consumed and
hunger_level mirror it. day_end() runs from time_loop.day_tick for every ogre.
"""
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "rules", "ogre_hunger.json"), encoding="utf-8") as _f:
    H = json.load(_f)


def is_ogre(c):
    return getattr(c, "race", None) == H["applies_to_race"]


def state(c):
    st = getattr(c, "hunger", None)
    if not isinstance(st, dict):
        st = {"points": 0, "kcal_today": 0}
        c.hunger = st
    return st


def _mirror(c):
    st = state(c)
    c.calories_consumed, c.hunger_level = st["kcal_today"], st["points"]


def hunger_state(c):
    pts = state(c)["points"]
    return [s for s in H["states"] if pts >= s["min"]][-1]


def felt(c):
    return hunger_state(c)["felt"]


def eat(c, kcal):
    if not is_ogre(c):
        return
    state(c)["kcal_today"] += kcal
    _mirror(c)


def is_fed(c):
    """For healing: ogres heal as fed only while not ravenous/starving."""
    return not is_ogre(c) or hunger_state(c)["fed"]


def _hurt(manager, n):
    import limb_repair
    return limb_repair._hurt(manager, n)


def rage_target_number(c):
    R = H["rage_check"]
    st = hunger_state(c)
    flaw = 0
    fl = getattr(c, "flaws", None)
    if isinstance(fl, dict) and "ogre_hunger" in fl:
        flaw = fl["ogre_hunger"] if isinstance(fl["ogre_hunger"], int) else 1
    elif isinstance(fl, (list, tuple)) and "ogre_hunger" in fl:
        flaw = 1
    talent = 0
    try:
        import talents as T
        for t in getattr(c, "talents", []) or []:
            talent += (T.get_talent(t) or {}).get("effects", {}).get(R["talent_bonus_key"], 0)
    except Exception:
        pass
    return getattr(c, R["stat"], 0) + R["base_bonus"] + st["wil_mod"] + flaw * R["per_flaw_intensity"] + talent


def bite(ogre_c, victim_manager, rng=None):
    """A failed hunger check: the ogre bites the nearest companion like a starving bear."""
    rng = rng or random
    F = H["rage_check"]["on_fail"]
    zone = rng.choice([z for z in F["zone_choice"] if z in victim_manager.health] or list(victim_manager.health))
    victim_manager.take_damage_to_zone(zone, F["damage"], F["damage_type"], use_armor=False)
    vc = victim_manager.character
    vc.stress_level = getattr(vc, "stress_level", 0) + F["victim_stress"]
    eat(ogre_c, F["eats_kcal"])
    return {"victim": getattr(vc, "name", "?"), "zone": zone, "damage": F["damage"],
            "felt_ogre": F["felt_ogre"], "felt_victim": F["felt_victim"]}


def day_end(manager, companions=(), rng=None):
    """End of day for an ogre: settle today's food into hunger points, apply the state, and
    run the hidden willpower check (ravenous+) against the nearest companion (companions[0])."""
    c = manager.character
    if not is_ogre(c):
        return None
    rng = rng or random
    P, st = H["hunger_points"], state(c)
    short = H["daily_need_kcal"] - st["kcal_today"]
    if short > 0:
        st["points"] += -(-short // 1000) * P["per_1000_kcal_short"]
    else:
        st["points"] -= P["full_day_fed_recovers"] + (-short // 1000) * P["per_1000_kcal_surplus_recovers"]
    st["points"] = max(0, min(P["max"], st["points"]))
    st["kcal_today"] = 0
    s = hunger_state(c)
    c.stress_level = getattr(c, "stress_level", 0) + s["stress_per_day"]
    out = {"felt": s["felt"], "bite": None}
    if s.get("damage_per_day"):
        _hurt(manager, s["damage_per_day"])
    if s.get("check") and companions:
        if rng.randint(1, 100) > rage_target_number(c):
            out["bite"] = bite(c, companions[0], rng)
    _mirror(c)
    out["gm"] = {"points": st["points"], "state": s["id"]}
    return out


def can_devour(c):
    return getattr(c, "class_name", None) in H["devour"]["classes"]


def devour(eater_manager, victim_manager, victim_grabbed_or_downed):
    """Flesh Eater only: eat a foe alive mid-combat. Heals, feeds, costs corruption and stamina."""
    D, c = H["devour"], eater_manager.character
    if not can_devour(c):
        return {"ok": False, "result": "only the Ogre Flesh Eater can devour foes"}
    if not victim_grabbed_or_downed:
        return {"ok": False, "result": "victim must be grabbed or downed"}
    if getattr(c, "stamina", D["stamina_cost"]) < D["stamina_cost"]:
        return {"ok": False, "result": "too exhausted"}
    if hasattr(c, "stamina"):
        c.stamina -= D["stamina_cost"]
    zone = next(z for z, hp in victim_manager.health.items() if hp > 0) if any(
        hp > 0 for hp in victim_manager.health.values()) else None
    if zone:
        victim_manager.take_damage_to_zone(zone, D["damage"], "bite", use_armor=False)
    healed = 0
    for z in eater_manager.health:
        room = eater_manager.initial_health[z] - eater_manager.health[z]
        if room > 0 and healed < D["heal_hp"]:
            add = min(room, D["heal_hp"] - healed)
            eater_manager.health[z] += add
            healed += add
    eater_manager._sync_total()
    import limb_repair
    limb_repair._add_corruption(c, D["corruption"])
    eat(c, D["eats_kcal"])
    return {"ok": True, "healed": healed, "corruption": D["corruption"], "felt": D["felt"]}
