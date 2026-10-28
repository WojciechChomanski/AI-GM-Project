"""Bleeding tests (docs/BLEEDING.md). Run: python tests/test_bleeding.py  (or pytest)"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import bleeding
from zone_hp import BASE_ZONES, scaled_zones, spread_damage, SPREAD_EXCLUDED
from character import Character
from combat_health import CombatHealthManager
from healing_system import HealingSystem
from first_aid import FirstAidSystem


def fresh(mult=1.0):
    c = Character(); c.name = "Test"; c.dexterity = 0; c.pain_penalty = 0
    c.body_parts = scaled_zones(mult); c.max_body_parts = dict(c.body_parts)
    c.total_hp = sum(c.body_parts.values())
    h = CombatHealthManager(c)
    h.morale_check = lambda: True
    return c, h


def with_total(h, total):
    """Wear the body down (spread, throat/groin untouched) until `total` HP is left."""
    split = spread_damage(h.health, h.initial_health, h.total_hp - total, SPREAD_EXCLUDED, {z: 1 for z in h.health})
    for z, d in split.items():
        h.health[z] -= d
    h._sync_total()
    assert h.total_hp == total
    return h


def wound(zone, kind):
    dmg = {"cut": 3, "deep": 8}.get(kind, 8)
    return bleeding.make_wound(zone, dmg, "slashing", critical=False, artery=(kind == "artery"))


def run(zone, kind, hp, bandage_round=None, stop=3, max_rounds=100):
    """Rounds of bleeding from one wound. Returns (dead_round or None, HP lost)."""
    c, h = fresh()
    with_total(h, hp)
    start = h.total_hp
    h.bleeding_wounds.append(wound(zone, kind)); h.refresh_bleeding()
    for r in range(1, max_rounds + 1):
        if bandage_round == r:
            bleeding.stop_wounds(h.bleeding_wounds, stop)   # a successful bandage
            h.refresh_bleeding()
        if not any(w["rate"] > 0 for w in h.bleeding_wounds):
            return None, start - h.total_hp
        h.apply_bleeding()
        if not c.alive:
            return r, start - h.total_hp
    return None, start - h.total_hp


# ---------- rates ----------
def test_rate_table():
    exp = {"left_upper_arm": (1, 2, 3), "left_lower_leg": (1, 2, 3), "head": (1, 2, 3), "chest": (1, 2, 3), "stomach": (1, 2, 3),
           "right_upper_leg": (2, 3, 4), "groin": (2, 3, 4), "throat": (3, 4, 5)}
    for zone, rates in exp.items():
        got = tuple(wound(zone, k)["rate"] for k in ("cut", "deep", "artery"))
        assert got == rates, (zone, got)
    assert all(isinstance(wound(z, "deep")["rate"], int) for z in BASE_ZONES)


def test_kind_from_damage_and_crit():
    mk = bleeding.make_wound
    assert mk("chest", 5, "slashing")["kind"] == "cut"
    assert mk("chest", 6, "piercing")["kind"] == "deep"
    assert mk("chest", 2, "slashing", critical=True)["kind"] == "deep"
    assert mk("chest", 2, "slashing", critical=True, artery=True)["kind"] == "artery"
    assert mk("chest", 0, "slashing") is None   # nothing got through armour -> no bleeding


def test_rounding_bug_fixed_bleeding_really_drains():
    c, h = fresh()
    h.take_damage_to_zone("left_upper_arm", 3, "piercing")   # old code: amount 0.03 -> int() -> 0 HP
    before = h.total_hp
    assert len(h.bleeding_wounds) == 1 and h.character.bleeding == 1
    h.apply_bleeding()
    assert h.total_hp == before - 1


# ---------- blunt ----------
def test_blunt_non_crit_does_not_bleed_but_blunt_crit_does():
    c, h = fresh()
    h.take_damage_to_zone("chest", 12, "blunt")
    h.distribute_damage(15, "blunt")
    assert h.bleeding_wounds == [] and c.bleeding == 0
    h.take_damage_to_zone("stomach", 5, "blunt", critical=True)
    assert len(h.bleeding_wounds) == 1 and h.bleeding_wounds[0]["kind"] == "deep"
    assert bleeding.make_wound("chest", 9, "blunt", critical=True, artery=True)["kind"] == "deep"  # never an artery


def test_only_damage_through_armour_bleeds():
    import json
    from armor_system import ArmorPiece
    plate = json.load(open(os.path.join(os.path.dirname(__file__), "..", "rules", "armors.json")))["Heavy_Medium"]["standard"]
    c, h = fresh()
    c.armor = [ArmorPiece(plate["name"], plate["coverage"], plate["armor_rating"], plate["stamina_penalty"],
                          plate["max_durability"], plate["weight"])]
    h.take_damage_to_zone("chest", 10, "slashing")   # Full Plate absorbs 10: nothing gets through
    h.distribute_damage(10, "slashing")
    assert h.bleeding_wounds == [] and c.bleeding == 0
    c2, h2 = fresh()
    c2.armor = [ArmorPiece(plate["name"], plate["coverage"], plate["armor_rating"], plate["stamina_penalty"],
                           plate["max_durability"], plate["weight"])]
    h2.take_damage_to_zone("chest", 14, "slashing")  # 4 gets through -> a cut
    assert [w["kind"] for w in h2.bleeding_wounds] == ["cut"]


# ---------- clotting ----------
def test_cut_stops_after_three_rounds_deep_slows_artery_throat_never():
    w = wound("left_upper_arm", "cut")
    seen = []
    for _ in range(5):
        seen.append(w["rate"]); bleeding.tick_wound(w)
    assert seen == [1, 1, 1, 0, 0]
    w = wound("right_upper_leg", "deep")   # 3 for 4 rounds, 2 for 4, 1 for 4, then stops
    seen = []
    for _ in range(14):
        seen.append(w["rate"]); bleeding.tick_wound(w)
    assert seen == [3]*4 + [2]*4 + [1]*4 + [0]*2
    for z, k in (("right_upper_leg", "artery"), ("throat", "cut"), ("throat", "deep")):
        w = wound(z, k); r0 = w["rate"]
        for _ in range(60): bleeding.tick_wound(w)
        assert w["rate"] == r0


def test_perk_hooks_dwarf_clot_and_bear_rate():
    w = wound("left_upper_arm", "cut")
    for _ in range(2): bleeding.tick_wound(w, 0.8)       # -20% clot time: 3 -> 2 rounds
    assert w["rate"] == 0
    assert bleeding.make_wound("throat", 8, "slashing", rate_mult=0.5)["rate"] == 2   # 4 * 0.5
    assert bleeding.make_wound("chest", 3, "slashing", rate_mult=0.5)["rate"] == 1    # round up, minimum 1


# ---------- cap ----------
def test_cap_five_per_round_no_stacking_beyond():
    c, h = fresh()
    for z, k in (("right_upper_leg", "deep"), ("chest", "deep"), ("left_upper_arm", "cut"), ("right_lower_arm", "cut")):
        h.bleeding_wounds.append(wound(z, k))
    assert sum(w["rate"] for w in h.bleeding_wounds) == 7
    assert h.refresh_bleeding() == 5
    before = h.total_hp
    assert h.apply_bleeding() == 5 and h.total_hp == before - 5
    # 50 more wounds still cost 5 per round
    for _ in range(50):
        h.bleeding_wounds.append(wound("throat", "artery"))
    before = h.total_hp
    assert bleeding.current_rate(h.bleeding_wounds) == 5
    assert h.apply_bleeding() == 5 and h.total_hp == before - 5


# ---------- spread rules / limbs ----------
def test_bleeding_spread_rules_and_never_destroys_a_limb():
    c, h = fresh()
    for _ in range(40):
        h.bleeding_wounds.append(wound("throat", "artery"))
    for _ in range(40):
        h.apply_bleeding()
        if not c.alive:
            break
    assert h.health["throat"] == 3 and h.health["groin"] == 3     # excluded from spread
    assert all(v >= 1 for v in h.health.values())                 # no zone below 1: no limb destroyed
    assert not h.character.compromised_limbs   # nothing crippled / destroyed by blood loss
    assert not any(v == 0 for v in h.health.values())


def test_bleeding_rolls_no_crits():
    c, h = fresh()
    h.apply_critical_wound = lambda *a, **k: (_ for _ in ()).throw(AssertionError("crit rolled by bleeding"))
    h.consequences.apply_consequence = lambda *a, **k: (_ for _ in ()).throw(AssertionError("consequence rolled by bleeding"))
    h.bleeding_wounds.append(wound("throat", "artery"))
    for _ in range(60):
        h.apply_bleeding()
        if not c.alive: break
    assert not c.alive


def test_bleed_out_when_everything_that_can_bleed_is_at_one():
    c, h = fresh()
    h.bleeding_wounds.append(wound("throat", "artery"))
    rounds = 0
    while c.alive and rounds < 100:
        h.apply_bleeding(); rounds += 1
    assert not c.alive
    # all 11 eligible zones are at 1 (+ throat 3 + groin 3 untouched) = 17 HP: death by blood loss, never by 0 zones
    assert h.total_hp == 17 and h.health["chest"] == 1
    assert rounds == 17   # 83 HP can bleed away: 16 rounds of 5, then only 3 of the next 5 can be absorbed -> dies in round 17


# ---------- the draft's worked examples (placeholders) ----------
def test_example_1_arm_stab_cut():
    assert run("left_upper_arm", "cut", 100) == (None, 3)                    # stops by itself, lose 3
    assert run("left_upper_arm", "cut", 30) == (None, 3)
    assert run("left_upper_arm", "cut", 100, bandage_round=3, stop=3) == (None, 2)   # bandaged: lose 2


def test_example_2_thigh_slash_deep():
    assert run("right_upper_leg", "deep", 100) == (None, 24)                 # 3,2,1 over 12 rounds
    # only 30 HP left: 13 HP can bleed away (zones stop at 1, throat/groin untouched) -> bleeds out in round 5.
    # (The draft said "survives with 6": the floor of 1 per zone makes the real limit ~17 HP, see docs/BLEEDING.md)
    assert run("right_upper_leg", "deep", 30) == (5, 13)
    assert run("right_upper_leg", "deep", 100, bandage_round=3, stop=3) == (None, 6)   # Basic: lose 6


def test_example_2b_thigh_artery_untreated_vs_improved():
    dead_100, _ = run("right_upper_leg", "artery", 100)
    dead_30, _ = run("right_upper_leg", "artery", 30)
    assert dead_100 == 21 and dead_30 == 4        # untreated: death by blood loss (see docs for why earlier than the draft)
    assert run("right_upper_leg", "artery", 100, bandage_round=3, stop=3) == (21, 83)        # Basic cannot stop a 4/round artery
    assert run("right_upper_leg", "artery", 30, bandage_round=3, stop=3) == (4, 13)
    assert run("right_upper_leg", "artery", 100, bandage_round=3, stop=6) == (None, 8)       # Improved: lose 8
    assert run("right_upper_leg", "artery", 30, bandage_round=3, stop=6) == (None, 8)


def test_example_3_throat_cut():
    dead_100, _ = run("throat", "cut", 100)
    dead_30, _ = run("throat", "cut", 30)
    assert dead_100 == 28 and dead_30 == 5        # throat never clots: untreated = death
    assert run("throat", "cut", 100, bandage_round=3, stop=3) == (None, 6)   # Basic: lose 6
    assert run("throat", "cut", 30, bandage_round=3, stop=3) == (None, 6)


# ---------- bandage on the real wound list ----------
class Rng:
    def __init__(self, v): self.v = v
    def randint(self, a, b): return self.v


def test_bandage_uses_real_wound_list_and_tiers():
    c, h = fresh()
    healer = Character(); healer.name = "Medic"; healer.dexterity = 10; healer.pain_penalty = 0
    for z, k in (("left_upper_arm", "cut"), ("chest", "deep"), ("right_upper_leg", "artery")):  # rates 1, 2, 4
        h.bleeding_wounds.append(wound(z, k))
    assert h.refresh_bleeding() == 5 and c.bleeding == 5 and c.bleeding_rate == 5
    hs = HealingSystem()
    assert bleeding.attempt_bandage(healer, c, hs.healing_items["basic_bandage"], rng=Rng(99))   # stops 1+2 (3)
    assert [w["kind"] for w in h.bleeding_wounds] == ["artery"] and c.bleeding == 4
    assert bleeding.attempt_bandage(healer, c, hs.healing_items["improved_bandage"], rng=Rng(99))
    assert h.bleeding_wounds == [] and c.bleeding == 0


def test_bandage_failure_and_dc():
    c, h = fresh()
    healer = Character(); healer.name = "Medic"; healer.dexterity = 0; healer.pain_penalty = 0
    h.bleeding_wounds.append(wound("chest", "cut")); h.refresh_bleeding()
    item = HealingSystem().healing_items["basic_bandage"]
    assert bleeding.attempt_bandage(healer, c, item, rng=Rng(29)) is False and c.bleeding == 1   # 29 < DC 30
    item = HealingSystem().healing_items["basic_bandage"]
    healer.dexterity = 5    # +1
    assert bleeding.attempt_bandage(healer, c, item, rng=Rng(29)) is True and c.bleeding == 0     # 30 >= 30


def test_both_bandage_scripts_use_the_same_wound_list():
    saved, bleeding.random = bleeding.random, Rng(80)   # fixed d100 = 80 (DC 40 passes)
    try:
        _both_scripts()
    finally:
        bleeding.random = saved


def _both_scripts():
    for attempt in (lambda hl, c: HealingSystem().attempt_bandage(hl, c, "herbal_poultice"),
                    lambda hl, c: FirstAidSystem().attempt_bandage(hl, c, "herbal_poultice")):
        c, h = fresh()
        healer = Character(); healer.name = "M"; healer.dexterity = 0; healer.pain_penalty = 0
        h.bleeding_wounds.append(wound("chest", "deep")); h.refresh_bleeding()
        assert attempt(healer, c) is True
        assert h.bleeding_wounds == [] and c.bleeding == 0


def test_rules_json_mirrors_code():
    import json
    r = json.load(open(os.path.join(os.path.dirname(__file__), "..", "rules", "combat_rules.json")))["bleeding"]
    assert r["cap_per_round"] == bleeding.BLEED_CAP and r["cut_stops_after_rounds"] == bleeding.CUT_ROUNDS
    assert r["deep_loses_1_rate_every_rounds"] == bleeding.DEEP_STEP and r["cut_max_damage_through_armour"] == bleeding.CUT_MAX_DAMAGE
    rates = list(r["rates_per_round"].values())
    for group, row in zip(("base", "thigh_groin", "throat"), rates):
        assert bleeding.RATE_TABLE[group] == (row["cut"], row["deep"], row["artery"])
    hs = HealingSystem().healing_items
    for k, v in r["bandage_stops_hp_per_round"].items():
        assert hs[k].bleed_stop_amount == v and hs[k].difficulty_threshold == r["bandage_dc"][k]


def test_crit_table_artery_makes_artery_wound_never_for_blunt():
    c, h = fresh()
    h.apply_critical_wound = lambda *a, **k: "Artery cut, rapid blood loss, -20% all rolls"
    h.take_damage_to_zone("right_lower_arm", 3, "slashing")   # zone destroyed -> crit table says artery
    assert any(w["kind"] == "artery" and w["zone"] == "right_lower_arm" for w in h.bleeding_wounds)
    assert len([w for w in h.bleeding_wounds if w["zone"] == "right_lower_arm"]) == 1   # no extra wound on top
    c, h = fresh()
    h.apply_critical_wound = lambda *a, **k: "Artery cut, rapid blood loss, -20% all rolls"
    h.take_damage_to_zone("right_lower_arm", 3, "blunt")
    assert h.bleeding_wounds == []


# ---------- integration: hit -> wound ----------
def test_hits_create_wounds_after_armour():
    random.seed(3)
    c, h = fresh()
    h.take_damage_to_zone("right_upper_leg", 8, "slashing")
    w = h.bleeding_wounds[0]
    assert (w["zone"], w["kind"], w["rate"]) == ("right_upper_leg", "deep", 3)
    h.take_damage_to_zone("throat", 1, "piercing")     # throat dies at 3 only when 3; 1 dmg = cut, rate 3
    assert [x["rate"] for x in h.bleeding_wounds] == [3, 3] and c.bleeding == 5   # capped
    c2, h2 = fresh()
    h2.distribute_damage(4, "slashing")
    assert len(h2.bleeding_wounds) == 1 and h2.bleeding_wounds[0]["kind"] == "cut"


if __name__ == "__main__":
    import logging; logging.disable(logging.CRITICAL)
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f(); print("PASS", f.__name__)
    print(f"{len(fns)} tests passed")
