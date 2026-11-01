import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import bleeding  # noqa: E402
import corruption as K  # noqa: E402
import wound_recovery as R  # noqa: E402
from test_bleeding import fresh  # noqa: E402


def test_breath_wound_bleeds_more_and_clots_slower_but_still_clots():
    w = R.breath_wound(bleeding.make_wound("left_lower_arm", 3, "slashing"))
    assert w["rate"] == 2 and w["breath"]
    for _ in range(3):
        bleeding.tick_wound(w)
    assert w["rate"] == 2  # a normal cut stops after 3 rounds
    bleeding.tick_wound(w)
    assert w["rate"] == 0  # a scratch never kills


def test_manager_breath_wound_and_dwarf_clot():
    c, h = fresh()
    w = h.add_bleeding_wound("chest", 8, "slashing", breath=True)
    assert w["rate"] == 3
    c2 = type(c)(); c2.name = "D"; c2.race = "Dwarf"; c2.body_parts = dict(c.body_parts); c2.pain_penalty = 0
    from combat_health import CombatHealthManager
    CombatHealthManager(c2)
    assert c2.bleed_clot_mult == 0.8


def test_heal_day_rules():
    init = {"chest": 10, "left_lower_arm": 6}
    hp = {"chest": 5, "left_lower_arm": 0}
    assert R.heal_day(hp, init) == 1 and hp == {"chest": 6, "left_lower_arm": 0}  # destroyed zone does not heal
    assert R.heal_day(hp, init, bleeding=True) == 0
    assert R.heal_day(hp, init, race="Ogre", fed=False) == 0
    assert R.heal_mult("Ogre") == 1.5 and R.heal_mult("Human") == 1.0
    assert R.heal_day(hp, init, mode="bed_rest_with_care", race="Ogre") == 3


def test_heal_manager_day():
    c, h = fresh()
    h.health["chest"] -= 5
    h._sync_total()
    before = h.total_hp
    got = R.heal_manager_day(h)
    assert got >= 1 and h.total_hp == before + got == sum(h.health.values())


def test_regen_skips_breath_damage():
    cc = K.CorruptedCreature(40)
    cc.take(10)
    cc.take(5, breath=True)  # 15 effective
    assert cc.effective == 25 and R.regen_round(cc) == 2 and cc.effective == 23
    for _ in range(20):
        R.regen_round(cc)
    assert cc.effective == 15  # Breath damage stays
    assert R.creature_heal_day(cc, 10) == 5 and cc.breath_effective == 10


def test_morale_is_a_test():
    rng = random.Random(0)
    results = {R.morale_vs_knight(30, rng) for _ in range(200)}
    assert results == {True, False}
    k, other = "knight", "squire"
    picks = {R.choose_target(["veilspawn"], 30, [(k, "full"), (other, "none")], rng) for _ in range(200)}
    assert picks == {k, other}
    assert R.choose_target(["veilspawn"], 0, [(k, "full")], rng) == k  # no one else: still attacks
    assert R.choose_target(["human"], 0, [(k, "full"), (other, "none")], rng) == k


def test_combat_engine_shy_away_is_a_test():
    try:
        import combat_engine as CE
    except Exception:
        import pytest
        pytest.skip("combat_engine deps unavailable")
    base = dict(race="Human", total_hp=20, max_stamina=50, armor_weight=0, inventory_weight=0,
                shield_equipped=False, weapon_equipped=True, weapon="none", armor=[])
    beast = dict(base, name="B", corrupted=True, other_targets_available=True, willpower=30)
    kn = dict(base, name="K", class_name="Crusader_Knight", virtue=80, piety=80)
    random.seed(0)
    res = [CE.CombatEngine().attack_roll(beast, kn).get("shied_away", False) for _ in range(100)]
    assert any(res) and not all(res)
    assert not any(CE.CombatEngine().attack_roll(dict(beast, other_targets_available=False), kn).get("shied_away")
                   for _ in range(30))
