# file: scripts/blood_vessels.py
"""Necromantic blood-vessel bindings. Hidden: Python backend only, never Foundry.

PLACEHOLDER numbers in rules/blood_vessels.json. A caster may bind up to `cap` living
people (willing or not). Blood costs of Bloodweaver spells may be paid from a vessel
in range; stamina, corruption and any other caster costs stay on the caster.
Each bound vessel adds a little hidden corruption every day.
"""
import json
import os
import random

import magic_costs
import magic_backlash

ROOT = os.path.join(os.path.dirname(__file__), "..")
VITAL_ZONES = ("head", "throat", "chest")


def data():
    with open(os.path.join(ROOT, "rules", "blood_vessels.json"), encoding="utf-8-sig") as f:
        return json.load(f)


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


def _name(obj):
    return str(_get(obj, "name", None) or _get(obj, "id", "") or id(obj))


def vessels_of(caster):
    found = _get(caster, "blood_vessels", None)
    if found is None:
        found = []
        _set(caster, "blood_vessels", found)
    return found


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
    flag = _get(obj, "alive", None)
    if flag is False:
        return False
    return _hp(obj) > 0 if _max_hp(obj) or _hp(obj) else flag is not False


def _id_of(obj):
    return _get(obj, "vessel_id", None) or _get(obj, "id", None) or _name(obj)


def find_bond(caster, target):
    tid = _id_of(target)
    for b in vessels_of(caster):
        if b.get("vessel_id") == tid or b.get("name") == _name(target):
            return b
    return None


def opposed_willpower(caster, target, rng=None):
    """PLACEHOLDER: d100 + Willpower. Ties go to the defender (the unwilling target resists)."""
    rng = rng or random
    c = rng.randint(1, 100) + int(_get(caster, "willpower", 0) or 0)
    t = rng.randint(1, 100) + int(_get(target, "willpower", 0) or 0)
    return {"caster_total": c, "target_total": t, "success": c > t}


def bind(caster, target, willing=True, rng=None):
    """Bind a living person as a blood vessel. Pays ritual stamina, own HP, and hidden corruption."""
    cfg = data()
    out = {"ok": False}
    if target is None or caster is None:
        out["reason"] = "missing target"
        return out
    if _id_of(caster) == _id_of(target) or caster is target:
        out["reason"] = "cannot bind yourself"
        return out
    if not _alive(target):
        out["reason"] = "target is dead"
        return out
    bonds = vessels_of(caster)
    if find_bond(caster, target):
        out["reason"] = "already bound"
        return out
    if len(bonds) >= int(cfg["cap"]):
        out["reason"] = f"vessel cap is {cfg['cap']}"
        return out
    cost_s = int(cfg["bind"]["stamina"])
    cost_hp = int(cfg["bind"]["hp"])
    if _stamina(caster) < cost_s:
        out["reason"] = "not enough stamina"
        return out
    if _hp(caster) <= cost_hp:
        out["reason"] = "not enough blood"
        return out
    if not willing:
        roll = opposed_willpower(caster, target, rng)
        out["opposed"] = roll
        if not roll["success"]:
            _set_stamina(caster, _stamina(caster) - cost_s)
            _set_hp(caster, _hp(caster) - cost_hp)
            added = magic_costs.add_corruption(caster, int(cfg["bind"]["corruption_unwilling"]))
            out["reason"] = "willpower resisted"
            out["corruption_added"] = added
            out["paid"] = True
            return out
    _set_stamina(caster, _stamina(caster) - cost_s)
    _set_hp(caster, _hp(caster) - cost_hp)
    corr = int(cfg["bind"]["corruption_willing"] if willing else cfg["bind"]["corruption_unwilling"])
    added = magic_costs.add_corruption(caster, corr)
    bond = {
        "vessel_id": _id_of(target),
        "name": _name(target),
        "willing": bool(willing),
    }
    bonds.append(bond)
    out.update({"ok": True, "bond": bond, "corruption_added": added, "vessels": len(bonds)})
    return out


def unbind(caster, target=None, vessel_id=None, reason="released"):
    bonds = vessels_of(caster)
    want = vessel_id or (None if target is None else _id_of(target))
    kept, removed = [], None
    for b in bonds:
        if removed is None and (b.get("vessel_id") == want or (target is not None and b.get("name") == _name(target))):
            removed = b
        else:
            kept.append(b)
    _set(caster, "blood_vessels", kept)
    return {"ok": removed is not None, "removed": removed, "reason": reason, "vessels": len(kept)}


def vessel_died(caster, target):
    """Bond snaps: stamina shock and hidden corruption on the caster."""
    cfg = data()
    found = find_bond(caster, target)
    if not found:
        return {"ok": False, "reason": "not bound"}
    unbind(caster, target, reason="vessel_died")
    _set_stamina(caster, max(0, _stamina(caster) - int(cfg["on_vessel_death"]["stamina"])))
    added = magic_costs.add_corruption(caster, int(cfg["on_vessel_death"]["corruption"]))
    return {"ok": True, "reason": "vessel_died", "corruption_added": added}


def in_range(distance_metres):
    if distance_metres is None:
        return True
    return float(distance_metres) <= float(data()["range_metres"])


def pay_blood(caster, amount, vessel=None, distance_metres=None):
    """Take HP from a bound, in-range vessel, or from the caster if that is not possible.

    Does not spend the caster's stamina. Returns who paid and whether the vessel died.
    """
    amount = int(amount)
    out = {"ok": False, "amount": amount, "from": "caster"}
    use_vessel = (
        vessel is not None
        and find_bond(caster, vessel) is not None
        and _alive(vessel)
        and in_range(distance_metres)
    )
    if use_vessel and _hp(vessel) > 0:
        before = _hp(vessel)
        taken = min(before, amount)
        _set_hp(vessel, before - taken)
        out.update({"ok": True, "from": "vessel", "taken": taken, "vessel_hp": _hp(vessel)})
        if not _alive(vessel) or _hp(vessel) <= 0:
            _set(vessel, "alive", False)
            snap = vessel_died(caster, vessel)
            out["vessel_died"] = snap
        return out
    if _hp(caster) <= 0:
        out["reason"] = "no blood left"
        return out
    before = _hp(caster)
    taken = min(before, amount)
    # refuse to pay a vital zone to zero is enforced by callers with a zone manager;
    # the pool path will not drop the last hit point if that would be all they have
    # and amount is a spell cost — still allow payment down to 1 if possible.
    if before - taken <= 0 and before > 1:
        taken = before - 1
    _set_hp(caster, before - taken)
    out.update({"ok": taken > 0, "from": "caster", "taken": taken, "reason": None if use_vessel is False else "vessel unavailable"})
    if use_vessel is False and vessel is not None and not in_range(distance_metres):
        out["reason"] = "vessel out of range"
        out["ok"] = taken > 0
    if taken > 0:
        out["stigmata"] = magic_backlash.note_blood_spent(caster, taken)
    return out


def day_tick(caster):
    """Each bound vessel adds a little hidden corruption, even if she casts nothing."""
    n = len(vessels_of(caster))
    if n <= 0:
        return {"vessels": 0, "corruption_added": 0}
    amount = n * int(data()["daily_corruption_per_vessel"])
    added = magic_costs.add_corruption(caster, amount)
    return {"vessels": n, "corruption_added": added}
