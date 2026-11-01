# file: scripts/wound_recovery.py
"""Per-round regeneration, per-day natural healing, Breath wounds and creature morale vs a full-Breath knight.
Data: rules/wound_recovery.json (docs/RECOVERY.md). PLACEHOLDER numbers."""
import json
import math
import os
import random

ROOT = os.path.join(os.path.dirname(__file__), "..")


def data():
    with open(os.path.join(ROOT, "rules/wound_recovery.json"), encoding="utf-8-sig") as f:
        return json.load(f)


# ---- natural healing (per day) ----
def heal_mult(race, fed=True):
    r = data()["race_healing"].get(race, {})
    if "mult" not in r:
        return 1.0
    if r.get("requires_fed") and not fed:
        return r.get("unfed_mult", 0.0)
    return r["mult"]


def heal_day(health, initial, race=None, fed=True, mode="resting", bleeding=False, extra_mult=1.0):
    """One day of natural healing on a {zone: hp} dict (changed in place).
    Zones at 0 do not heal; no healing while still bleeding. Returns HP healed."""
    nh = data()["natural_healing"]
    if bleeding and nh["bleeding_blocks_healing"]:
        return 0
    per = nh["hp_per_zone_per_day"][mode] * heal_mult(race, fed) * extra_mult
    healed = 0
    for z, hp in health.items():
        top = initial.get(z, hp)
        if hp <= 0 and not nh["destroyed_zone_heals"] or hp >= top or per <= 0:
            continue
        gain = min(top - hp, max(1, math.floor(per)) if per >= 1 else (1 if random.random() < per else 0))
        health[z] = hp + gain
        healed += gain
    return healed


def heal_manager_day(manager, fed=True, mode="resting"):
    """heal_day for a CombatHealthManager (13-zone model; total = sum of zones)."""
    c = manager.character
    got = heal_day(manager.health, manager.initial_health, getattr(c, "race", None), fed, mode,
                   any(w["rate"] > 0 for w in manager.bleeding_wounds))
    manager._sync_total()
    return got


# ---- corrupted creatures (per round) ----
def regen_round(creature):
    """creature: corruption.CorruptedCreature. Regenerates normal damage only; Breath damage stays."""
    cr = data()["corrupted_regeneration"]
    amount = max(cr["min_per_round"], creature.natural_hp * cr["per_round_pct_of_natural_hp"] // 100)
    normal = creature.effective - getattr(creature, "breath_effective", 0)
    healed = min(amount, max(0, normal))
    if cr["heals_breath_damage"]:
        healed = min(amount, creature.effective)
    creature.effective -= healed
    return healed


def creature_heal_day(creature, amount):
    """Natural healing of a corrupted creature: normal damage at x1, Breath damage at x0.5."""
    m = data()["corrupted_regeneration"]["breath_damage_natural_heal_mult"]
    b = getattr(creature, "breath_effective", 0)
    normal = creature.effective - b
    n = min(normal, amount)
    rest = amount - n
    bh = min(b, int(rest * m))
    creature.effective -= n + bh
    creature.breath_effective = b - bh
    return n + bh


# ---- Breath wounds ----
def breath_wound(wound):
    """Turn a bleeding.make_wound dict into a full-Breath wound: bleeds more, clots slower (GM: 'burning')."""
    if not wound:
        return wound
    bw = data()["breath_wounds"]
    wound["rate"] = max(1, math.ceil(wound["rate"] * bw["bleed_rate_mult"]))
    wound["clot_mult"] = bw["clot_time_mult"]
    wound["breath"] = True
    return wound


# ---- morale vs knight ----
def morale_vs_knight(willpower, rng=None):
    """True = holds and may attack the knight. A test, never automatic."""
    m = data()["morale_vs_knight"]
    rng = rng or random
    return rng.randint(1, 100) <= m["base"] + willpower // m["willpower_div"] + m["breath_mod"]


def choose_target(creature_tags, willpower, targets, rng=None):
    """targets: list of (target, breath_state). A Veil-thing facing a full-Breath knight tests morale;
    on a fail it picks another target if any; otherwise it still attacks the knight."""
    tags = set(data()["morale_vs_knight"]["applies_to_tags"])
    if not targets:
        return None
    first, state = targets[0]
    if state != "full" or not (set(creature_tags) & tags):
        return first
    if morale_vs_knight(willpower, rng):
        return first
    others = [t for t, s in targets[1:] if s != "full"]
    return others[0] if others else first
