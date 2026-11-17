# file: scripts/magic_backlash.py
"""Elemental and necromantic backlash tracks, sigils, ritual debt.

PLACEHOLDER numbers: rules/magic_backlash.json. All tracks, scar points and debt
live only in the Python backend. Foundry may show symptom text from symptoms(),
never the numbers.

Opposite-element cancelling is banned as a provisional default.
Witch hunters are ordinary trained men who spot signs (scars, sigils, frost/scorch evidence,
behaviour) by mundane inspection. They use no magic. A magic-using female witch hunter may
come later as a special NPC only.
"""
from __future__ import annotations

import json
import os
import random

import magic_costs

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCHOOLS_WITH_SIGILS = ("frost", "fire", "necromancy")


def data():
    with open(os.path.join(ROOT, "rules", "magic_backlash.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def frost_fire_spells():
    with open(os.path.join(ROOT, "rules", "spells_frost_fire.json"), encoding="utf-8-sig") as f:
        return json.load(f)["spells"]


def all_spells():
    with open(os.path.join(ROOT, "rules", "spells.json"), encoding="utf-8-sig") as f:
        spells = json.load(f)
    spells.update(frost_fire_spells())
    return spells


def _get(obj, name, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _set(obj, name, value):
    if isinstance(obj, dict):
        obj[name] = value
    else:
        setattr(obj, name, value)


def _hp(obj):
    cur = _get(obj, "current_hp", None)
    if cur is not None:
        return int(cur)
    return int(_get(obj, "hp", _get(obj, "total_hp", 0)) or 0)


def _max_hp(obj):
    return int(_get(obj, "total_hp", _get(obj, "max_hp", _hp(obj))) or 0)


def _set_hp(obj, value):
    value = max(0, int(value))
    if isinstance(obj, dict):
        if "current_hp" in obj or "total_hp" in obj:
            obj["current_hp"] = value
        elif "hp" in obj:
            obj["hp"] = value
        else:
            obj["current_hp"] = value
    else:
        if hasattr(obj, "current_hp"):
            obj.current_hp = value
        elif hasattr(obj, "hp"):
            obj.hp = value
        else:
            obj.current_hp = value


def _stamina(obj):
    return int(_get(obj, "stamina", _get(obj, "current_stamina", 0)) or 0)


def _set_stamina(obj, value):
    if isinstance(obj, dict):
        if "current_stamina" in obj:
            obj["current_stamina"] = int(value)
        else:
            obj["stamina"] = int(value)
    else:
        if hasattr(obj, "stamina"):
            obj.stamina = int(value)
        else:
            obj.current_stamina = int(value)


def _alive(obj):
    if obj is None:
        return False
    if _get(obj, "alive", None) is False:
        return False
    return True


def _die(obj, reason="backlash"):
    _set(obj, "alive", False)
    if _hp(obj) > 0:
        _set_hp(obj, 0)
    return {"died": True, "reason": reason}


def state(caster):
    """Hidden backlash blob on the character (never a Foundry field)."""
    s = _get(caster, "backlash", None)
    if not isinstance(s, dict):
        s = {}
        _set(caster, "backlash", s)
    s.setdefault("thermal", 0)
    s.setdefault("grave_chill", 0)
    s.setdefault("blood_hp_this_scene", 0)
    s.setdefault("sigil_points", {k: 0 for k in SCHOOLS_WITH_SIGILS})
    s.setdefault("glamour_sigils_scene", False)
    s.setdefault("thermal_death_rounds", None)
    s.setdefault("collapsed", False)
    s.setdefault("grave_hp_penalty_active", False)
    s.setdefault("lost_appendage", None)
    s.setdefault("permanent_penalty", 0)
    s.setdefault("ritual_debts", [])
    s.setdefault("fever_night", False)
    s.setdefault("warming", None)
    s.setdefault("stigmata_rounds", 0)
    s.setdefault("ice_bath_rounds", 0)
    return s


def band_gain(track, band):
    cfg = data()[track if track != "thermal" else "thermal"]
    if track == "grave_chill":
        cfg = data()["grave_chill"]
    return int(cfg["gains"][band])


def sigil_tier(points):
    tiers = data()["sigils"]["tiers"]
    best = None
    for key in sorted(tiers, key=lambda k: int(k)):
        info = tiers[key]
        if int(points) >= int(info["at"]):
            best = dict(info)
            best["tier"] = int(key)
    return best


def sigil_tier_for(caster, school):
    pts = int(state(caster)["sigil_points"].get(school, 0) or 0)
    return sigil_tier(pts), pts


def add_sigil(caster, school, n=1):
    if school not in SCHOOLS_WITH_SIGILS or n <= 0:
        return 0
    s = state(caster)
    s["sigil_points"][school] = int(s["sigil_points"].get(school, 0) or 0) + int(n)
    return n


def _heavy_discount(caster, school, band):
    cfg = data()["sigils"]
    if band != cfg.get("sigil_ii_applies_to", "heavy"):
        return 0
    tier, _ = sigil_tier_for(caster, school)
    if tier and int(tier.get("heavy_discount") or 0):
        return int(cfg.get("sigil_ii_heavy_discount", 1))
    return 0


def _crosses(before, after, marks, signed=False):
    """Which threshold values were crossed (by absolute value unless signed)."""
    hit = []
    for m in marks:
        m = int(m)
        if signed:
            if (before < m <= after) or (before > -m >= after) or (before > m >= after) or (before < -m <= after):
                # crossed +m or -m in either direction of travel
                if (before < m <= after) or (before > m >= after):
                    hit.append(m)
                if (before > -m >= after) or (before < -m <= after):
                    hit.append(-m)
        else:
            # unsigned tracks (grave-chill 0..10) or thermal by abs
            if abs(before) < m <= abs(after) or (before < m <= after):
                hit.append(m)
    # unique, preserve order
    out, seen = [], set()
    for x in hit:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _thermal_crosses(before, after, marks):
    hit = []
    for m in marks:
        m = int(m)
        if abs(before) < m <= abs(after):
            hit.append(m)
    return hit


def move_thermal(caster, delta, school=None):
    """Shift Thermal, apply threshold symptoms, sigil-on-cross, and the ±10 death window.

    Health is lost only when a threshold is crossed or already at a damaging
    threshold on a round tick — not as a flat cost of the shift itself.
    """
    cfg = data()["thermal"]
    s = state(caster)
    lo, hi = int(cfg["min"]), int(cfg["max"])
    before = int(s["thermal"])
    after = max(lo, min(hi, before + int(delta)))
    s["thermal"] = after
    rep = {"before": before, "after": after, "crossed": _thermal_crosses(before, after, data()["sigils"]["points_on_track_cross"])}
    if school:
        for _ in rep["crossed"]:
            add_sigil(caster, school, 1)
    if abs(after) >= 7 and abs(before) < 7:
        rep["threshold_7"] = True
    if abs(after) >= 5 and abs(before) < 5:
        rep["threshold_5"] = True
        # area evidence begins; no flat HP here
    if abs(after) >= 10:
        if s["thermal_death_rounds"] is None:
            s["thermal_death_rounds"] = int(cfg["thresholds"]["10"]["death_rounds"])
            s["_thermal_death_warned"] = False
            rep["death_window"] = s["thermal_death_rounds"]
    else:
        s["thermal_death_rounds"] = None
        s["_thermal_death_warned"] = False
    return rep


def move_grave_chill(caster, delta, school="necromancy", rng=None):
    cfg = data()["grave_chill"]
    s = state(caster)
    lo, hi = int(cfg["min"]), int(cfg["max"])
    before = int(s["grave_chill"])
    after = max(lo, min(hi, before + int(delta)))
    s["grave_chill"] = after
    rep = {"before": before, "after": after, "crossed": []}
    for m in data()["sigils"]["points_on_track_cross"]:
        if before < m <= after:
            rep["crossed"].append(m)
            add_sigil(caster, school, 1)
    if after >= 7:
        s["grave_hp_penalty_active"] = True
        rep["max_hp_penalty_pct"] = cfg["thresholds"]["7"]["max_hp_pct_until_long_rest"]
    if after >= 10 and before < 10 and not s["lost_appendage"]:
        rng = rng or random
        choice = rng.choice(list(cfg["thresholds"]["10"]["lose"]))
        s["lost_appendage"] = choice
        s["permanent_penalty"] = int(cfg["thresholds"]["10"]["permanent_penalty"])
        rep["lost"] = choice
        rep["permanent_penalty"] = s["permanent_penalty"]
    return rep


def toward_zero(value, steps):
    steps = int(steps)
    if value > 0:
        return max(0, value - steps)
    if value < 0:
        return min(0, value + steps)
    return 0


def can_cast(caster, spell):
    """Refuse a Frost/Fire spell that would cancel the other element (provisional default)."""
    strain = (spell or {}).get("strain") or {}
    if strain.get("track") != "thermal":
        return {"ok": True}
    school = strain.get("school")
    cfg = data()
    if cfg["opposite_element_cancelling"]["allowed"]:
        return {"ok": True}
    t = int(state(caster)["thermal"])
    if t < 0 and school == "fire":
        return {"ok": False, "reason": "opposite-element cancelling is banned (provisional)", "provisional": True}
    if t > 0 and school == "frost":
        return {"ok": False, "reason": "opposite-element cancelling is banned (provisional)", "provisional": True}
    return {"ok": True}


def apply_cast_strain(caster, spell, failed=False):
    """Apply track gain for a successful (or requested) cast. No flat HP.

    failed casts do not move tracks (placeholder). Opposite-element cancelling is
    refused as a provisional default.
    """
    if failed:
        return {"ok": True, "skipped": "failed_cast"}
    strain = (spell or {}).get("strain") or {}
    if not strain:
        return {"ok": True, "skipped": "no_strain"}
    track = strain.get("track")
    school = strain.get("school")
    band = strain.get("band")
    if not track or not band:
        return {"ok": True, "skipped": "no_strain"}
    s = state(caster)
    cfg = data()
    if track == "thermal":
        direction = -1 if school == "frost" else 1 if school == "fire" else 0
        if direction == 0:
            return {"ok": False, "reason": "thermal spell needs school frost or fire"}
        # Provisional default: cannot cancel the other element by casting.
        if not cfg["opposite_element_cancelling"]["allowed"]:
            if s["thermal"] < 0 and direction > 0:
                return {"ok": False, "reason": "opposite-element cancelling is banned (provisional)", "provisional": True}
            if s["thermal"] > 0 and direction < 0:
                return {"ok": False, "reason": "opposite-element cancelling is banned (provisional)", "provisional": True}
        gain = band_gain("thermal", band)
        gain -= _heavy_discount(caster, school, band)
        gain = max(0, gain)
        if band in ("heavy", "greater"):
            add_sigil(caster, school, int(cfg["sigils"]["points_per_heavy_or_greater_cast"]))
        moved = move_thermal(caster, direction * gain, school=school)
        return {"ok": True, "track": "thermal", "gain": direction * gain, "moved": moved}
    if track == "grave_chill":
        gain = band_gain("grave_chill", band)
        gain -= _heavy_discount(caster, "necromancy", band)
        gain = max(0, gain)
        if band in ("heavy", "greater"):
            add_sigil(caster, "necromancy", int(cfg["sigils"]["points_per_heavy_or_greater_cast"]))
        moved = move_grave_chill(caster, gain)
        return {"ok": True, "track": "grave_chill", "gain": gain, "moved": moved}
    if track == "blood":
        # Blood HP is paid by the spell's existing health cost, not here.
        return {"ok": True, "track": "blood", "note": " stigmata is tracked in note_blood_spent"}
    return {"ok": True, "skipped": "unknown_track"}


def note_blood_spent(caster, amount):
    """Count blood/HP paid this scene (own blood or a vessel's). Stigmata if the total reaches 16+."""
    amount = int(amount)
    if amount <= 0:
        return {"ok": True, "total": state(caster)["blood_hp_this_scene"]}
    s = state(caster)
    s["blood_hp_this_scene"] += amount
    rep = {"ok": True, "total": s["blood_hp_this_scene"], "stigmata": False}
    threshold = int(data()["blood"]["stigmata_hp_in_scene"])
    if s["blood_hp_this_scene"] >= threshold and s["stigmata_rounds"] <= 0:
        s["stigmata_rounds"] = int(data()["blood"]["stigmata_rounds"])
        rep["stigmata"] = True
        rep["bleed_rate"] = int(data()["blood"]["stigmata_bleed_rate"])
        rep["rounds"] = s["stigmata_rounds"]
    return rep


def scene_end(caster):
    s = state(caster)
    s["blood_hp_this_scene"] = 0
    s["glamour_sigils_scene"] = False
    return {"ok": True}


def penalties(caster):
    """Mechanical penalties derived from current tracks. No hidden numbers leaked in text."""
    s = state(caster)
    t = abs(int(s["thermal"]))
    th = data()["thermal"]["thresholds"]
    out = {
        "fine_tasks": 0,
        "spellcraft": 0,
        "all": 0,
        "stamina_regen_mult": 1.0,
        "hp_per_round": 0,
        "agility": int(s.get("permanent_penalty") or 0),
        "numb_hand": False,
        "collapsed": bool(s["collapsed"]),
        "max_hp_pct": -10 if s["grave_hp_penalty_active"] else 0,
        "lost_appendage": s["lost_appendage"],
    }
    if t >= 3:
        out["fine_tasks"] += int(th["3"]["fine_tasks"])
        out["spellcraft"] += int(th["3"]["spellcraft"])
    if t >= 5:
        out["all"] += int(th["5"]["all"])
        out["stamina_regen_mult"] = float(th["5"]["stamina_regen_mult"])
        out["hp_per_round"] = int(th["5"]["hp_per_round"])
    if t >= 7:
        out["stamina_regen_mult"] = float(th["7"]["stamina_regen_mult"])
        out["hp_per_round"] = int(th["7"]["hp_per_round"])
    g = int(s["grave_chill"])
    if g >= 4:
        out["agility"] += int(data()["grave_chill"]["thresholds"]["4"]["agility"])
        out["numb_hand"] = True
    return out


def area_evidence(caster):
    s = state(caster)
    t = int(s["thermal"])
    radius = int(data()["thermal"]["thresholds"]["5"]["area_evidence_metres"])
    if t <= -5:
        return {"kind": "frost", "radius_metres": radius}
    if t >= 5:
        return {"kind": "scorching", "radius_metres": radius}
    return None


def symptoms(caster):
    """Player-facing felt text only. No track numbers, no corruption numbers."""
    s = state(caster)
    t = int(s["thermal"])
    felt = []
    if t <= -10:
        felt.append({"topic": "cold", "text": "The cold is in your marrow. You have a moment, perhaps, if something warms you now."})
    elif t <= -7:
        felt.append({"topic": "cold", "text": "The cold has gone into the bone. Standing is a labour. You cannot get warm."})
    elif t <= -5:
        felt.append({"topic": "cold", "text": "You cannot get warm. A rime spreads on things near you. Each breath costs a little more."})
    elif t <= -3:
        felt.append({"topic": "cold", "text": "Your hands shake on fine work, and the air around you feels a few degrees too low."})
    elif t >= 10:
        felt.append({"topic": "heat", "text": "The heat is eating you from the inside. You have a moment, perhaps, if something cools you now."})
    elif t >= 7:
        felt.append({"topic": "heat", "text": "Your skin feels tight and dry. The air shimmers. You can barely stand the heat in your own blood."})
    elif t >= 5:
        felt.append({"topic": "heat", "text": "A dry heat radiates from you. Paper and cloth nearby want to curl. You are weakening."})
    elif t >= 3:
        felt.append({"topic": "heat", "text": "Your hands tremble, flushed, and fine work slips. You feel a fever you did not earn."})
    g = int(s["grave_chill"])
    if g >= 10 and s["lost_appendage"]:
        felt.append({"topic": "grave", "text": f"The grave took a {s['lost_appendage']} from you. That loss will not grow back."})
    elif g >= 7:
        felt.append({"topic": "grave", "text": "You feel hollowed and thinner, as if some of your life had been set aside and not returned."})
    elif g >= 4:
        felt.append({"topic": "grave", "text": "One hand is numb and clumsy, as if you had slept on it in a cold room."})
    if s["stigmata_rounds"] > 0:
        felt.append({"topic": "blood", "text": "The wounds in your palms will not stay closed."})
    if s["fever_night"]:
        felt.append({"topic": "debt", "text": "A fever sits on you. Sleep will not restore you tonight."})
    if s["collapsed"]:
        felt.append({"topic": "collapse", "text": "Your legs have gone. You cannot act until you are warmed, cooled, or carried."})
    # Visible sigils as felt only if actually showing
    showing = visible_sigils(caster)
    if showing:
        names = ", ".join(x["name"] + " (" + x["school"] + ")" for x in showing)
        felt.append({"topic": "sigil", "text": f"Marks of the work show on your skin unless you cover them: {names}."})
    return felt


def visible_sigils(caster, close_inspection=False, cover=None):
    """Sigils an ordinary observer can see. Glamour hides them for a scene from casual sight.

    It fails against close physical inspection (undressing, or a trained hunter's mundane exam).
    Witch hunters use no magic; they only look carefully at scars, sigils, frost or scorch
    evidence, and behaviour. A magic-using female witch hunter may come later as a special NPC.
    """
    s = state(caster)
    glamoured = bool(s["glamour_sigils_scene"]) and not close_inspection
    if glamoured:
        return []
    cover = cover or []
    out = []
    for school in SCHOOLS_WITH_SIGILS:
        tier, pts = sigil_tier_for(caster, school)
        if not tier or not tier.get("visible"):
            continue
        concealable = tier.get("concealable")
        if concealable and isinstance(concealable, list) and any(c in concealable for c in cover):
            continue
        # Branded (concealable false) always shows to ordinary sight unless glamoured (and not closely inspected)
        out.append({"school": school, "name": tier["name"], "tier": tier["tier"]})
    return out


def glamour_hide_sigils(caster):
    """Hide visible sigils for one scene at +5 Corruption.

    Fails against close physical inspection (undressing or a trained hunter's mundane exam).
    """
    cost = int(data()["sigils"]["glamour"]["corruption"])
    added = magic_costs.add_corruption(caster, cost)
    state(caster)["glamour_sigils_scene"] = True
    return {"ok": True, "corruption_added": added, "hides_from": "casual_sight",
            "fails_against": "close_physical_inspection"}


def _apply_steps_toward_zero_thermal(caster, steps):
    s = state(caster)
    new = toward_zero(int(s["thermal"]), steps)
    return move_thermal(caster, new - int(s["thermal"]))


def counter_hot_iron(caster):
    cfg = data()["thermal"]["counters"]["hot_iron"]
    if _hp(caster) <= int(cfg["hp_cost"]):
        return {"ok": False, "reason": "not enough health"}
    _set_hp(caster, _hp(caster) - int(cfg["hp_cost"]))
    add_sigil(caster, "fire", int(cfg["fire_scar"]))
    moved = _apply_steps_toward_zero_thermal(caster, int(cfg["steps_toward_zero"]))
    s = state(caster)
    if abs(int(s["thermal"])) < 10:
        s["thermal_death_rounds"] = None
    return {"ok": True, "moved": moved, "fire_scar": int(cfg["fire_scar"])}


def counter_ice_bath(caster):
    cfg = data()["thermal"]["counters"]["ice_bath"]
    if _stamina(caster) < int(cfg["stamina_cost"]):
        return {"ok": False, "reason": "not enough stamina"}
    _set_stamina(caster, _stamina(caster) - int(cfg["stamina_cost"]))
    moved = _apply_steps_toward_zero_thermal(caster, int(cfg["steps_toward_zero"]))
    state(caster)["ice_bath_rounds"] = int(cfg["rounds"])
    s = state(caster)
    if abs(int(s["thermal"])) < 10:
        s["thermal_death_rounds"] = None
    return {"ok": True, "moved": moved, "rounds": int(cfg["rounds"])}


def start_brazier_or_snow(caster, kind="brazier"):
    if kind not in ("brazier", "snow"):
        return {"ok": False, "reason": "kind must be brazier or snow"}
    state(caster)["warming"] = kind
    # The first step can land in this same moment if used as a death-round counter.
    moved = _apply_steps_toward_zero_thermal(caster, int(data()["thermal"]["counters"]["brazier_or_snow"]["steps_toward_zero_per_round"]))
    s = state(caster)
    if abs(int(s["thermal"])) < 10:
        s["thermal_death_rounds"] = None
    return {"ok": True, "warming": kind, "moved": moved}


def stop_warming(caster):
    state(caster)["warming"] = None
    return {"ok": True}


def counter_warm_blood(caster):
    cfg = data()["grave_chill"]["counters"]["warm_blood"]
    added = magic_costs.add_corruption(caster, int(cfg["corruption"]))
    s = state(caster)
    before = int(s["grave_chill"])
    s["grave_chill"] = toward_zero(before, int(cfg["steps_toward_zero"]))
    return {"ok": True, "before": before, "after": s["grave_chill"], "corruption_added": added}


def counter_salt_and_ash(caster):
    cfg = data()["grave_chill"]["counters"]["salt_and_ash"]
    if _hp(caster) <= int(cfg["hp_cost"]):
        return {"ok": False, "reason": "not enough health"}
    _set_hp(caster, _hp(caster) - int(cfg["hp_cost"]))
    s = state(caster)
    before = int(s["grave_chill"])
    s["grave_chill"] = toward_zero(before, int(cfg["steps_toward_zero"]))
    return {"ok": True, "before": before, "after": s["grave_chill"]}


def counter_cautery(caster):
    cfg = data()["blood"]["counters"]["cautery"]
    if _hp(caster) <= int(cfg["hp_cost"]):
        return {"ok": False, "reason": "not enough health"}
    _set_hp(caster, _hp(caster) - int(cfg["hp_cost"]))
    add_sigil(caster, "fire", int(cfg["fire_scar"]))
    state(caster)["stigmata_rounds"] = 0
    return {"ok": True, "fire_scar": int(cfg["fire_scar"])}


def counter_tourniquet(caster):
    state(caster)["stigmata_rounds"] = 0
    return {"ok": True, "rounds_rest": int(data()["blood"]["counters"]["tourniquet"]["rounds_rest"])}


def rest(caster, minutes, kind="resting"):
    """Recovery while actually resting. Thermal: 1 step per 10 minutes. Grave-Chill: 1 per hour.

    This is too slow to save someone already in the ±10 death window (one combat round).
    """
    minutes = int(minutes)
    s = state(caster)
    th_steps = minutes // int(data()["thermal"]["recovery_step_per_minutes_rest"])
    gc_steps = minutes // int(data()["grave_chill"]["recovery_step_per_minutes_rest"])
    moved = None
    if th_steps:
        moved = _apply_steps_toward_zero_thermal(caster, th_steps)
    if gc_steps:
        s["grave_chill"] = toward_zero(int(s["grave_chill"]), gc_steps)
    return {"ok": True, "thermal": s["thermal"], "grave_chill": s["grave_chill"], "moved": moved}


def _toughness_test(caster, rng):
    dc = int(data()["thermal"]["thresholds"]["7"]["toughness_dc"])
    rng = rng or random
    toughness = int(_get(caster, "toughness", 0) or 0)
    roll = rng.randint(1, 100) + toughness
    return {"roll": roll, "dc": dc, "success": roll >= dc}


def round_tick(caster, rng=None):
    """Combat-round backlash: threshold HP, stigmata bleed, warming, death window, toughness/collapse.

    Health is taken only because a threshold is already crossed, never as a flat spell cost.
    """
    if not _alive(caster):
        return {"alive": False}
    s = state(caster)
    rng = rng or random
    rep = {"hp_lost": 0}
    pens = penalties(caster)
    hp_tick = int(pens["hp_per_round"] or 0)
    if s["stigmata_rounds"] > 0:
        hp_tick += int(data()["blood"]["stigmata_bleed_rate"])
        s["stigmata_rounds"] -= 1
        rep["stigmata_rounds"] = s["stigmata_rounds"]
    if hp_tick:
        _set_hp(caster, max(0, _hp(caster) - hp_tick))
        rep["hp_lost"] = hp_tick
        if _hp(caster) <= 0:
            return {**rep, **_die(caster, "backlash_bleed")}
    if s["warming"]:
        moved = _apply_steps_toward_zero_thermal(
            caster, int(data()["thermal"]["counters"]["brazier_or_snow"]["steps_toward_zero_per_round"])
        )
        rep["warming"] = moved
    if s["ice_bath_rounds"]:
        s["ice_bath_rounds"] = max(0, int(s["ice_bath_rounds"]) - 1)
    # Toughness test while at ±7 or worse, if not already collapsed
    if abs(int(s["thermal"])) >= 7 and not s["collapsed"]:
        test = _toughness_test(caster, rng)
        rep["toughness_test"] = test
        if not test["success"]:
            s["collapsed"] = True
            rep["collapsed"] = True
    if abs(int(s["thermal"])) < 7:
        s["collapsed"] = False
    # Death window: hitting ±10 does not kill at once. The next round_tick does, unless a counter has moved the track off ±10.
    if abs(int(s["thermal"])) >= 10:
        if s.get("_thermal_death_warned"):
            return {**rep, **_die(caster, "thermal_overuse")}
        s["_thermal_death_warned"] = True
        s["thermal_death_rounds"] = 0
        rep["death_window"] = "this_round_to_counter"
    else:
        s["thermal_death_rounds"] = None
        s["_thermal_death_warned"] = False
    return {**rep, "alive": True, "thermal": s["thermal"]}


def start_ritual(casters, band, track, school, lead=None):
    """Begin a ritual: no track cost now. Debt is stored, due at the next dawn, split evenly in a circle."""
    cfg = data()
    if track == "thermal":
        total = band_gain("thermal", band)
    elif track == "grave_chill":
        total = band_gain("grave_chill", band)
    else:
        return {"ok": False, "reason": "ritual debt must be thermal or grave_chill"}
    people = list(casters)
    if not people:
        return {"ok": False, "reason": "no casters"}
    lead = lead or people[0]
    n = len(people)
    share, rem = divmod(int(total), n)
    shares = [(c, share) for c in people]
    if rem:
        for i, (c, a) in enumerate(shares):
            if c is lead:
                shares[i] = (c, a + rem)
                break
        else:
            shares[0] = (shares[0][0], shares[0][1] + rem)
    debts = []
    for c, amount in shares:
        if amount <= 0:
            continue
        st = state(c)
        debt = {"track": track, "school": school, "band": band, "amount": amount}
        st["ritual_debts"].append(debt)
        debts.append({"caster": _get(c, "name", id(c)), "amount": amount})
    return {"ok": True, "total": total, "split": debts, "due": cfg["ritual"]["debt_due"]}


def dawn_tick(caster, rng=None):
    """Pay delayed ritual debt as a Thermal or Grave-Chill hit, and start a fever night (no long-rest benefit)."""
    s = state(caster)
    debts = list(s["ritual_debts"])
    s["ritual_debts"] = []
    rep = {"debts": [], "fever_night": False}
    for d in debts:
        s["fever_night"] = True
        rep["fever_night"] = True
        if d["track"] == "thermal":
            direction = -1 if d.get("school") == "frost" else 1
            moved = move_thermal(caster, direction * int(d["amount"]), school=d.get("school"))
            rep["debts"].append({"track": "thermal", "moved": moved})
        elif d["track"] == "grave_chill":
            moved = move_grave_chill(caster, int(d["amount"]), rng=rng)
            rep["debts"].append({"track": "grave_chill", "moved": moved})
    return rep


def long_rest(caster):
    """A long rest. Refused (no refill, grave HP penalty stays) during a fever night; the fever then breaks."""
    s = state(caster)
    if s["fever_night"]:
        s["fever_night"] = False
        return {"ok": False, "reason": "fever_night", "fever_cleared": True}
    s["grave_hp_penalty_active"] = False
    return {"ok": True, "grave_hp_penalty_cleared": True}


def day_tick(caster, mode="resting", rng=None):
    """A day passing: dawn debt, then rest recovery. Travelling still gets the dawn."""
    dawn = dawn_tick(caster, rng=rng)
    minutes = 0 if mode == "travelling" else (24 * 60 if mode == "bed_rest_with_care" else 8 * 60)
    rec = rest(caster, minutes, kind=mode) if minutes else {"ok": True, "skipped": "travelling"}
    return {"dawn": dawn, "rest": rec}


# Used by magic_system / magic_engine_stub after a successful vein of spells.json or frost/fire.
def resolve_spell(caster, spell, failed=False):
    return apply_cast_strain(caster, spell, failed=failed)
