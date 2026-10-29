"""Durability / permanent wear tests (placeholder numbers). Run: python tests/test_durability.py (or pytest)"""
import os, sys, json, types, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
logging.disable(logging.CRITICAL)

import durability as D
from durability import Wear, weapon_damage_after_wear, weapon_loss_per_step, armor_rating_after_wear
from armor_system import ArmorPiece, armor_vs_aimed

RULES = json.load(open(os.path.join(os.path.dirname(__file__), "..", "rules", "combat_rules.json")))


def test_mark_at_30_percent_of_current_max_drops_5_percent_of_original():
    w = Wear(100)
    assert w.lose(29) == 0 and w.current_max == 100
    assert w.lose(1) == 1                       # 30 lost -> first mark
    assert w.current_max == 95 and w.marks == 1 and w.counter == 0
    # next mark needs 30% of the CURRENT max (28.5), and drops 5% of the ORIGINAL (not of 95)
    assert w.lose(28) == 0 and w.lose(0.5) == 1
    assert w.current_max == 90
    assert w.lose(27) == 1 and w.current_max == 85


def test_counter_is_cumulative_and_resets_at_a_mark():
    w = Wear(100)
    for _ in range(5):
        w.lose(5)                               # 25: no mark yet
    assert w.marks == 0 and abs(w.counter - 25) < 1e-9
    w.lose(7)                                   # 32 -> mark, 2 carried over
    assert w.marks == 1 and abs(w.counter - 2) < 1e-9


def test_big_hit_can_trigger_several_marks_and_destroy():
    w = Wear(100)
    assert w.lose(200) >= 3 and w.marks >= 3
    w = Wear(100)
    while not w.destroyed:
        w.lose(30)
    assert w.current_max == 0 and w.marks == 20 and w.destroyed
    assert w.lose(10) == 0                      # destroyed items stay destroyed


def test_float_safe():
    w = Wear(11)                                # a plate zone (11 durability)
    assert abs(w.current_max - 11) < 1e-12
    w.lose(3.3)
    assert w.marks == 1 and abs(w.current_max - 10.45) < 1e-9
    assert w.clamp(11) == w.current_max and w.clamp(3) == 3
    while not w.destroyed:
        w.lose(1)
    assert w.current_max == 0


def test_repair_stops_at_current_max_and_keeps_field_cap():
    w = Wear(100); w.lose(30)                   # max 95
    assert w.repair(70, 100) == 95              # never above the current max
    assert w.repair(10, 20, field_cap=0.85) == 30
    assert abs(w.repair(40, 100, field_cap=0.85) - 95 * 0.85) < 1e-9    # >50% missing -> 85% cap
    assert w.repair(60, 100, field_cap=0.85) == 95                      # <50% missing -> full to current max
    d = Wear(100)
    for _ in range(20): d.lose(30)
    assert d.repair(0, 50) == 0                 # destroyed: nothing to repair


def test_quality_steps_per_10_percent_of_original():
    w = Wear(100)
    assert w.quality_steps() == 0
    w.lose(30); assert w.marks == 1 and w.quality_steps() == 0      # 95
    w.lose(28.5); assert w.marks == 2 and w.quality_steps() == 1    # 90 -> 10% lost
    w.lose(27); assert w.quality_steps() == 1                       # 85
    w.lose(25.5); assert w.marks == 4 and w.quality_steps() == 2    # 80


def test_weapon_damage_quality():
    assert weapon_loss_per_step(10) == 1
    assert weapon_loss_per_step(14) == 1          # greatsword
    assert weapon_loss_per_step(6) == 1           # dagger: min 1 for >= 5 damage
    assert weapon_loss_per_step(25) == 3          # 2.5 rounds half up
    assert weapon_loss_per_step(20) == 2
    assert weapon_loss_per_step(4) == 0           # below 5: proportional only
    assert weapon_damage_after_wear(10, 0) == 10
    assert weapon_damage_after_wear(10, 1) == 9
    assert weapon_damage_after_wear(10, 3) == 7
    assert weapon_damage_after_wear(20, 2) == 16
    assert weapon_damage_after_wear(6, 2) == 4
    assert weapon_damage_after_wear(10, 50) == 1  # alive weapons never below 1 (placeholder floor)
    assert weapon_damage_after_wear(10, 3, destroyed=True) == 0


def test_armor_rating_quality():
    assert armor_rating_after_wear(10, 1) == 9 and armor_rating_after_wear(2, 5) == 0


def test_sword_example_from_the_draft():
    """100-durability 10-damage sword losing 12 per fight, repaired every fight (placeholder numbers)."""
    w = Wear(100); cur = 100.0; seen = {}
    for fight in range(1, 60):
        lost = min(12.0, cur)
        cur -= lost
        w.lose(lost)
        cur = w.repair(w.clamp(cur), 1000)          # full repair up to the current max
        seen[fight] = (w.current_max, weapon_damage_after_wear(10, w.quality_steps(), w.destroyed))
        if w.destroyed:
            break
    assert seen[3][0] == 95 and seen[3][1] == 10          # first mark in fight 3, quality still 10
    assert seen[8][1] <= 9
    assert w.destroyed and 20 <= fight <= 40               # scrap after a few dozen fights


def test_constants_match_combat_rules_json():
    d = RULES["durability"]
    assert d["mark_fraction_of_current_max"] == D.MARK_FRACTION
    assert d["mark_loss_fraction_of_original_max"] == D.MARK_LOSS_FRACTION
    assert d["quality_step_fraction_of_original_max"] == D.QUALITY_STEP_FRACTION
    assert d["field_repair_cap"] == D.FIELD_REPAIR_CAP
    assert RULES["weapon_durability"]["loss_per_attack"] == D.WEAPON_LOSS_PER_ATTACK
    assert RULES["weapon_durability"]["loss_on_parry"] == D.WEAPON_LOSS_ON_PARRY


def test_armour_zone_permanent_loss_and_repair_cap():
    p = ArmorPiece("Plate", ["chest", "stomach"], {"slashing": 10}, 0, 200, 1)    # 100 per zone
    # 30 durability lost on the chest (20% of 50 = 10, three hits) -> chest max 95, stomach untouched
    for _ in range(3):
        armor_vs_aimed([p], "chest", 50, "slashing")
    assert p.per_zone_max == {"chest": 95, "stomach": 100} and p.original_zone_max["chest"] == 100
    assert p.current_durability["chest"] == 70
    p.repair(20, "chest")                      # skill 20 -> eff capped 0.9: restores up to the max, not 100
    assert p.current_durability["chest"] == 95
    # a zone worn to 0 is "beyond field repair" (existing rule) and no longer counts
    for _ in range(50):
        armor_vs_aimed([p], "chest", 200, "slashing")
    assert p.current_durability["chest"] == 0 and p.condition_status("chest") == "Broken"
    before = p.per_zone_max["chest"]
    p.repair(20, "chest")
    assert p.current_durability["chest"] == 0 and p.per_zone_max["chest"] == before
    # destruction: keep restoring (e.g. a smith's full repair) and wearing -> max reaches 0
    from armor_system import _wear
    w = p.zone_wear["chest"]
    for _ in range(2000):
        if w.destroyed:
            break
        p.current_durability["chest"] = w.current_max
        _wear(p, "chest", 40)
    assert w.destroyed and p.current_durability["chest"] == 0 and p.per_zone_max["chest"] == 0
    assert p.condition_status("chest") == "Broken"
    p.current_durability["chest"] = 5
    assert p.per_zone_max["stomach"] == 100        # stomach never touched


def _adventure_new():
    """Import adventure_new with a stub for the external combat_engine module."""
    ce = types.ModuleType("AI_GM_Project.scripts.combat_engine")
    ce.CombatEngine = object
    ce.load_rules = lambda path: json.load(open(path, encoding="utf-8-sig"))
    for n in ("enforce_two_handed_and_shield", "spend_stamina", "regen_stamina", "init_morale",
              "morale_event", "check_rout"):
        setattr(ce, n, lambda *a, **k: None)
    ce.aimed_attack_penalty = lambda attacker, rules: 30
    for name, mod in (("AI_GM_Project", types.ModuleType("AI_GM_Project")),
                      ("AI_GM_Project.scripts", types.ModuleType("AI_GM_Project.scripts")),
                      ("AI_GM_Project.scripts.combat_engine", ce)):
        sys.modules.setdefault(name, mod)
    import adventure_new
    return adventure_new


def test_weapon_wiring_attack_parry_and_quality():
    an = _adventure_new()
    unit = {"name": "Tester", "weapon": {"type": "longsword", "durability": 100}}
    an.init_weapon_state(unit)
    assert unit["_weapon_durability"] == 100 and unit["_weapon_wear"].original_max == 100
    base = an.WEAPON_DAMAGE["longsword"]
    assert an.base_damage_for(unit) == base
    log = []
    an.apply_durability_tick(unit, log, kind="attack")
    assert unit["_weapon_durability"] == 99.5            # 0.5 per attack
    an.apply_durability_tick(unit, log, kind="parry")
    assert unit["_weapon_durability"] == 98.5            # 1.0 per parry
    # wear it down: 30 lost -> mark -> max 95; two marks -> quality -1 damage
    while unit["_weapon_wear"].marks < 2:
        an.apply_durability_tick(unit, log, kind="parry")
    assert unit["_weapon_wear"].current_max == 90 and unit["_weapon_durability"] <= 90
    assert an.base_damage_for(unit) == weapon_damage_after_wear(base, 1)
    assert an.base_damage_for(unit) < base
    # worn through (durability 0): broken, deals no weapon damage until repaired
    for _ in range(2000):
        an.apply_durability_tick(unit, log, kind="parry")
        if unit["_weapon_durability"] <= 0:
            break
    assert unit["_weapon_durability"] == 0 and an.base_damage_for(unit) == 0
    assert not unit["_weapon_wear"].destroyed
    cur_max = unit["_weapon_wear"].current_max
    assert an.repair_weapon_durability(unit, 1000) == cur_max and cur_max < 100   # repair stops at the current max
    assert an.base_damage_for(unit) >= 1
    # keep wearing + repairing: the weapon is eventually destroyed for good
    for _ in range(5000):
        an.apply_durability_tick(unit, log, kind="parry")
        an.repair_weapon_durability(unit, 1000)
        if unit["_weapon_wear"].destroyed:
            break
    assert unit["_weapon_wear"].destroyed and an.base_damage_for(unit) == 0
    assert an.repair_weapon_durability(unit, 1000) == 0
    assert any("destroyed" in line for line in log)


def test_aimed_penalty_wired_into_attack_roll():
    an = _adventure_new()
    import random
    a = {"name": "A", "dexterity": 25}; t = {"name": "T", "dexterity": 25}
    random.seed(1); head = an.attack_roll(a, "neutral", t, "neutral", "aimed", aimed_zone="head")
    random.seed(1); arm = an.attack_roll(a, "neutral", t, "neutral", "aimed", aimed_zone="left_upper_arm")
    random.seed(1); norm = an.attack_roll(a, "neutral", t, "neutral", "normal")
    assert head["aimed_pen"] == 40 and arm["aimed_pen"] == 30 and norm["aimed_pen"] == 0
    for z in ("throat", "groin"):
        assert an.attack_roll(a, "neutral", t, "neutral", "aimed", aimed_zone=z)["aimed_pen"] == 40


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f(); print("PASS", f.__name__)
    print(f"{len(fns)} tests passed")
