# file: scripts/bleeding.py
"""Bleeding rules (see docs/BLEEDING.md). ALL NUMBERS ARE PLACEHOLDERS for testing.

A wound is a plain dict: {"zone", "kind", "rate", "age", "noclot"}; `rate` is whole HP per round.
 - kind "cut"    : <= 5 damage got through armour   -> stops by itself after CUT_ROUNDS rounds
 - kind "deep"   : 6+ damage got through, or a crit -> rate drops by 1 every DEEP_STEP rounds
 - kind "artery" : crit result (artery / jugular)   -> never stops by itself
Throat wounds never stop by themselves, whatever their kind.
Blunt hits bleed ONLY on a crit. Only damage that got through armour can cause bleeding.
"""
import math
import random

BLEED_CAP = 5        # max HP lost to bleeding per round, all wounds together
CUT_ROUNDS = 3       # a cut stops after this many rounds
DEEP_STEP = 4        # a deep wound loses 1 HP/round of rate every this many rounds
CUT_MAX_DAMAGE = 5   # damage through armour: <= this = cut, above = deep

# zone group -> (cut, deep, artery) HP per round
RATE_TABLE = {
    "base":       (1, 2, 3),   # arms, lower legs, head, chest, stomach
    "thigh_groin": (2, 3, 4),  # upper legs, groin
    "throat":     (3, 4, 5),
}
KIND_INDEX = {"cut": 0, "deep": 1, "artery": 2}


def zone_group(zone):
    zone = str(zone)
    if zone in ("throat", "neck"):
        return "throat"
    if zone == "groin" or "upper_leg" in zone:
        return "thigh_groin"
    return "base"


def make_wound(zone, damage, damage_type, critical=False, artery=False, rate_mult=1.0):
    """Wound caused by `damage` that got THROUGH armour, or None (no bleeding).
    Blunt bleeds only on a crit (and never as an artery). `rate_mult` < 1 for perks
    such as Bear's Endurance (-50%): rounded up, minimum 1."""
    if damage is None or damage <= 0:
        return None
    blunt = str(damage_type) == "blunt"
    if blunt and not critical:
        return None
    if artery and not blunt:
        kind = "artery"
    elif critical or damage > CUT_MAX_DAMAGE:
        kind = "deep"
    else:
        kind = "cut"
    group = zone_group(zone)
    rate = RATE_TABLE[group][KIND_INDEX[kind]]
    if rate_mult != 1.0:
        rate = max(1, math.ceil(rate * rate_mult - 1e-9))
    return {"zone": zone, "kind": kind, "rate": int(rate), "age": 0,
            "noclot": group == "throat" or kind == "artery"}


def tick_wound(w, clot_mult=1.0):
    """End of a round: the wound ages and may clot. `clot_mult` 0.8 = Dwarf (-20% clot time)."""
    w["age"] += 1
    if w["noclot"] or w["rate"] <= 0:
        return
    clot_mult = clot_mult * w.get("clot_mult", 1.0)  # Breath wounds clot slower (rules/wound_recovery.json)
    if w["kind"] == "cut":
        if w["age"] >= max(1, round(CUT_ROUNDS * clot_mult)):
            w["rate"] = 0
    elif w["kind"] == "deep":
        if w["age"] % max(1, round(DEEP_STEP * clot_mult)) == 0:
            w["rate"] = max(0, w["rate"] - 1)


def current_rate(wounds, cap=BLEED_CAP):
    """HP lost this round: sum of all wound rates, capped."""
    return min(cap, sum(max(0, int(w["rate"])) for w in wounds))


def stop_wounds(wounds, stop_amount):
    """A successful bandage: stop wounds smallest first until `stop_amount` HP/round is used up.
    A wound bigger than what is left is skipped, so a Basic bandage (3) cannot stop a 4/round artery.
    Returns the list of stopped wounds."""
    budget = int(stop_amount)
    stopped = []
    for w in sorted((w for w in wounds if w["rate"] > 0), key=lambda w: w["rate"]):
        if w["rate"] <= budget:
            budget -= w["rate"]
            stopped.append(dict(w))
            w["rate"] = 0
    return stopped


def attempt_bandage(healer, target, item, health=None, rng=None):
    """ONE bandage attempt on the REAL wound list of `target`'s CombatHealthManager.
    `item` is a healing_items.HealingItem (bleed_stop_amount 3/6/9, difficulty 30/35/40).
    roll d100 + healer Dex//5 - min(pain, 20) >= difficulty. Returns True on success."""
    rng = rng or random
    health = health or getattr(target, "health_manager", None)
    if not getattr(target, "alive", True):
        print(f"{target.name} is dead. Bandaging is pointless.")
        return False
    if health is None:
        print(f"❌ {target.name} has no health manager; cannot bandage.")
        return False
    if not any(w["rate"] > 0 for w in health.bleeding_wounds):
        print(f"{target.name} is not bleeding and does not need bandaging.")
        return True
    if not item.use():
        return False
    roll = rng.randint(1, 100)
    dex_bonus = getattr(healer, "dexterity", 0) // 5
    pain = min(getattr(healer, "pain_penalty", 0), 20)
    total = roll + dex_bonus - pain
    print(f"🩹 {healer.name} bandages {target.name} with {item.name} "
          f"(roll {total} = {roll} +{dex_bonus} dex -{pain} pain) vs {item.difficulty_threshold}")
    if total >= item.difficulty_threshold:
        stopped = stop_wounds(health.bleeding_wounds, item.bleed_stop_amount)
        health.refresh_bleeding()
        if stopped:
            print(f"✅ Stopped {len(stopped)} wound(s) ({sum(w['rate'] for w in stopped)} HP/round).")
        else:
            print("✅ Bandage applied, but every wound is too heavy for it.")
        return True
    print(f"❌ Bandaging failed. {target.name} continues bleeding.")
    return False
