"""Career paths for every class (rules/careers.json, docs/CAREER_PATHS.md).

Evolutions add skills (learned at base value, no XP) and abilities; they never re-apply
class stat modifiers and never raise caps. Plausibility: Order paths, Order classes and
preacher evolutions need raised_by_order; everyone else gets order_contractor at most.
"""
import json
import os

import order_paths as O
import progression as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "rules", "careers.json"), encoding="utf-8") as _f:
    DATA = json.load(_f)
_get, _set = P._get, P._set


def is_order_raised(class_name):
    return class_name in DATA["origins"]["order_raised"]


def evolutions(class_name):
    return DATA["classes"].get(class_name, {}).get("evolutions", [])


def find(class_name, evo_id):
    return next((e for e in evolutions(class_name) if e["id"] == evo_id), None)


def evolve_errors(c, evo_id):
    cls = _get(c, "class_name")
    e = find(cls, evo_id)
    if e is None:
        return [f"{evo_id} is not an evolution of {cls}"]
    st, q, out = O.state(c), e["requires"], []
    gated = DATA["order_gated"]
    if (e.get("to_class") in gated["classes"] or q.get("order_path") in gated["paths"]
            or e.get("kind") in gated["evolution_kinds"]) and not st["raised_by_order"]:
        return ["not raised by the Order: only order_contractor is open"]
    if q.get("order_path"):
        out += O.entry_errors(c, q["order_path"])
    if st["sessions_at_rank"] < q.get("sessions_min", 0):
        out.append("sessions")
    if st["class_tier"] < q.get("class_tier_min", 0):
        out.append("class tier")
    if st["reputation"] < q.get("reputation", -100) or st["reputation"] < q.get("noble_reputation", -100):
        out.append("reputation")
    if not O._deeds_ok(st, q.get("deeds")):
        out.append("deeds")
    if not O._hidden_ok(c, q.get("hidden")):
        out.append("hidden")
    if q.get("race") and _get(c, "race") not in q["race"]:
        out.append("race")
    if q.get("order_contractor_rank") and not (st["path"] == "order_contractor" and st["rank"] >= q["order_contractor_rank"]):
        out.append("order contractor rank")
    if q.get("granted_land") and not st["deeds"].get("granted_land"):
        out.append("land")
    return out


def evolve(c, evo_id):
    """Apply an evolution: open skills/abilities; change class name only for to_class evolutions
    (stats untouched). Order-path evolutions go through order_paths.convert."""
    errs = evolve_errors(c, evo_id)
    if errs:
        return {"ok": False, "errors": errs}
    import skills as SK
    cls = _get(c, "class_name")
    e = find(cls, evo_id)
    if e["requires"].get("order_path"):
        O.convert(c, e["requires"]["order_path"])
    for sid in e["gains"]["skills"]:
        if not SK.has(c, sid) and SK.lock_error(sid, _get(c, "race"), _get(c, "gender")) is None:
            SK.learn(c, sid)
    abil = _get(c, "abilities", None)
    if isinstance(abil, list):
        abil.extend(a for a in e["gains"]["abilities"] if a not in abil)
    st = P.state(c).setdefault("career", {"history": []})
    st["history"].append({"from": cls, "evolution": evo_id})
    if e.get("to_class"):
        _set(c, "class_name", e["to_class"])
    return {"ok": True, "evolution": e["name"], "class": _get(c, "class_name"), "placeholder": e["placeholder"]}


def become_contractor(c):
    """Anyone may work for the Order for pay or favours: no vows, no Breath."""
    st = O.state(c)
    if st["raised_by_order"]:
        return False
    O.join(c, "order_contractor")
    return True
