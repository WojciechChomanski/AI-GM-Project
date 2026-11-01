# file: scripts/limb_repair.py
"""Repair of crippled/severed zones: surgery and magic (rules/limb_repair.json, docs/RECOVERY.md).
Works on a CombatHealthManager (13-zone model). Zone states live in manager.limb_state:
'crippled' (zone at 0), 'severed', 'stabilised' (severed, bleeding stopped), 'prosthesis'. PLACEHOLDER numbers."""
import json
import os
import random

from zone_hp import spread_damage, SPREAD_EXCLUDED

ROOT = os.path.join(os.path.dirname(__file__), "..")
ACTIVE_MAGIC_RACES = ("Human", "Elf")  # rules/core_rules.txt: active magic = female only, human or elf


def data():
    with open(os.path.join(ROOT, "rules/limb_repair.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def states(manager):
    """Current zone states. Any zone at 0 without a recorded state counts as crippled."""
    st = getattr(manager, "limb_state", None)
    if st is None:
        st = manager.limb_state = {}
    for z, hp in manager.health.items():
        if hp <= 0 and z not in st:
            st[z] = "crippled"
    return st


def mark_severed(manager, zone):
    states(manager)[zone] = "severed"


def limb_kind(zone):
    return "arm" if "arm" in zone or "hand" in zone else "leg" if "leg" in zone or "foot" in zone else None


def _restore(manager, zone):
    manager.health[zone] = max(manager.health[zone], data()["surgery"]["success_restore_hp"])
    manager.limb_state.pop(zone, None)
    c = manager.character
    if zone in getattr(c, "compromised_limbs", []):
        c.compromised_limbs.remove(zone)
    manager._sync_total()


def _hurt(manager, amount):
    """Extra damage from a botched job, spread with floor 1 (cannot kill or destroy a zone)."""
    split = spread_damage(manager.health, manager.initial_health, amount, SPREAD_EXCLUDED, {z: 1 for z in manager.health})
    for z, d in split.items():
        manager.health[z] -= d
    manager._sync_total()
    return sum(split.values())


def surgery_skill(surgeon):
    sk = (getattr(surgeon, "skills", None) or {}).get(data()["surgery"]["skill"])
    if sk is not None:
        return sk
    a, b = data()["surgery"]["fallback_stats"]
    return (getattr(surgeon, a, 0) + getattr(surgeon, b, 0)) // 2


def surgery(surgeon, manager, zone, procedure="repair", tools="field_kit", rng=None):
    """procedure: 'repair' (crippled -> restored), 'stabilise' or 'prosthesis' (severed only).
    Roll d100 <= skill + tools - difficulty - pain. Returns dict(ok, result, hours, ...)."""
    S = data()["surgery"]
    rng = rng or random
    st = states(manager).get(zone)
    if st is None:
        return {"ok": False, "result": "zone is not crippled or severed"}
    if procedure == "repair" and st != "crippled":
        return {"ok": False, "result": S["severed"]}
    if procedure in ("stabilise", "prosthesis") and st not in ("severed", "stabilised"):
        return {"ok": False, "result": f"{procedure} is only for severed parts"}
    if procedure == "prosthesis" and not limb_kind(zone):
        return {"ok": False, "result": "no prosthesis for this zone"}
    key = {"repair": "crippled", "stabilise": "severed_stabilise", "prosthesis": "prosthesis_fit"}[procedure]
    mod = S["tools_bonus"].get(tools, 0) if tools else S["no_tools_mod"]
    target = surgery_skill(surgeon) + mod - S["difficulty"][key] - min(getattr(surgeon, "pain_penalty", 0), S["pain_cap"])
    roll = rng.randint(1, 100)
    out = {"roll": roll, "target": target, "hours": S["hours"][key]}
    if roll <= target and roll < S["crit_fail_from"]:
        if procedure == "repair":
            _restore(manager, zone)
        elif procedure == "stabilise":
            manager.limb_state[zone] = "stabilised"
            for w in manager.bleeding_wounds:
                if w["zone"] == zone:
                    w["rate"] = 0
            manager.refresh_bleeding()
        else:
            manager.limb_state[zone] = "prosthesis"
        return dict(out, ok=True, result=procedure + " succeeded")
    extra = _hurt(manager, S["fail_extra_damage"]) if roll >= S["crit_fail_from"] or roll > target + 20 else 0
    infected = rng.randint(1, 100) <= S["fail_infection_chance_pct"]
    if infected:
        manager.infection = {"passes": 0}
    return dict(out, ok=False, result="failed", extra_damage=extra, infected=infected)


def prosthesis_penalty(zone):
    return data()["surgery"]["prosthesis_penalty"].get(limb_kind(zone) or "", {})


def infection_day(manager, rng=None):
    """Daily infection step (called by time_loop.day_tick). TOU test; passes clear it; fails hurt (floor 1)."""
    inf = getattr(manager, "infection", None)
    if not inf:
        return None
    I = data()["surgery"]["infection"]
    rng = rng or random
    c = manager.character
    c.stress_level = getattr(c, "stress_level", 0) + I["daily_stress"]
    if rng.randint(1, 100) <= getattr(c, "toughness", 0):
        inf["passes"] += 1
        if inf["passes"] >= I["clears_after_passes"]:
            manager.infection = None
            return "cleared"
        return "passed"
    _hurt(manager, I["fail_damage_per_day"])
    return "worse"


def _add_corruption(ch, n):
    ch.corruption_level = min(100, getattr(ch, "corruption_level", 0) + n)
    ch.corruption_peak = max(getattr(ch, "corruption_peak", 0), ch.corruption_level)


def veil_healing(caster, manager, zone, rng=None):
    """Active Veil magic (female Human/Elf only). Restores crippled; severed regrowth is rare and costly.
    Caster pays HP and corruption, the patient gains corruption either way the spell lands."""
    V = data()["magic"]["veil_healing"]
    rng = rng or random
    if getattr(caster, "gender", None) != "Female" or getattr(caster, "race", None) not in ACTIVE_MAGIC_RACES:
        return {"ok": False, "result": "only human or elven women wield active magic (core_rules.txt)"}
    st = states(manager).get(zone)
    if st not in ("crippled", "severed", "stabilised"):
        return {"ok": False, "result": "nothing to restore"}
    sev = st != "crippled"
    cfg = V["severed_regrowth"] if sev else V
    if sev and not cfg["allowed"]:
        return {"ok": False, "result": "regrowth not allowed"}
    skill = (getattr(caster, "skills", None) or {}).get(V["skill"], getattr(caster, "willpower", 0))
    roll = rng.randint(1, 100)
    _add_corruption(caster, cfg["caster_corruption"])
    caster.health_cost = getattr(caster, "health_cost", 0) + V["caster_hp_cost"]
    if roll <= skill - cfg["difficulty"]:
        _add_corruption(manager.character, cfg["patient_corruption"])
        _restore(manager, zone)
        return {"ok": True, "roll": roll, "result": "Veil flesh regrows" if sev else "restored"}
    return {"ok": False, "roll": roll, "result": "the Veil takes its price and gives nothing"}


def relic_heal(manager, zone, item):
    """Passive magic anyone may use. item: dict with 'id' and 'charges'. Severed only with a saint relic."""
    R = data()["magic"]["relic_or_potion"]
    st = states(manager).get(zone)
    if st is None or st == "prosthesis":
        return {"ok": False, "result": "nothing to restore"}
    if st != "crippled" and item.get("id") not in R["severed_items"]:
        return {"ok": False, "result": R["severed"]}
    if item.get("charges", 0) <= 0:
        return {"ok": False, "result": "no charges left"}
    item["charges"] -= 1
    _restore(manager, zone)
    return {"ok": True, "result": "restored"}
