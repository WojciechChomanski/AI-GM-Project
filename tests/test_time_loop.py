import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import bleeding  # noqa: E402
import corruption as K  # noqa: E402
import limb_repair as L  # noqa: E402
import time_loop as TL  # noqa: E402
from test_bleeding import fresh  # noqa: E402


class Rng:
    """Deterministic rolls in order."""
    def __init__(self, *rolls):
        self.r = list(rolls)

    def randint(self, a, b):
        return self.r.pop(0)


class Person:
    def __init__(self, **kw):
        self.name = "P"; self.pain_penalty = 0; self.skills = {}
        self.__dict__.update(kw)


def test_round_tick_bleeds_clots_and_regenerates():
    c, h = fresh()
    h.bleeding_wounds.append(bleeding.make_wound("left_lower_arm", 3, "slashing"))
    lost = sum(TL.round_tick(manager=h)["bled"] for _ in range(5))
    assert lost == 3 and not h.bleeding_wounds  # cut clots after 3 rounds
    cc = K.CorruptedCreature(40); cc.take(10)
    assert TL.round_tick(creature=cc)["regenerated"] == 2 and cc.effective == 8


def test_day_tick_modes_and_rules():
    c, h = fresh()
    h.health["chest"] -= 6; h.health["left_lower_arm"] = 0; h._sync_total()
    assert TL.day_tick(h)["healed"] == 1 + 0  # chest +1; zone at 0 stays
    assert h.health["left_lower_arm"] == 0 and L.states(h)["left_lower_arm"] == "crippled"
    assert TL.day_tick(h, "bed_rest_with_care")["healed"] == 2
    h.bleeding_wounds.append(bleeding.make_wound("chest", 8, "slashing"))
    assert TL.day_tick(h)["healed"] == 0
    import pytest
    with pytest.raises(ValueError):
        TL.day_tick(h, "dancing")


def test_gm_command():
    c, h = fresh()
    h.health["chest"] -= 5; h._sync_total()
    out = TL.gm_command("tick day 3 bed_rest_with_care", {"Anna": h})
    assert [r["healed"] for r in out["Anna"]] == [2, 2, 1]
    assert "error" in TL.gm_command("tock", {})
    assert len(TL.gm_command("tick round 4", {"Anna": h})["Anna"]) == 4


def test_surgery_repairs_crippled():
    c, h = fresh()
    h.health["left_lower_arm"] = 0; c.compromised_limbs = ["left_lower_arm"]; h._sync_total()
    doc = Person(intelligence=50, dexterity=40)
    assert L.surgery_skill(doc) == 45
    r = L.surgery(doc, h, "left_lower_arm", tools="surgeon_kit", rng=Rng(40))
    assert r["ok"] and h.health["left_lower_arm"] == 1 and "left_lower_arm" not in c.compromised_limbs
    assert "left_lower_arm" not in L.states(h)


def test_surgery_failure_hurts_and_infects_but_cannot_kill():
    c, h = fresh()
    h.health["left_lower_arm"] = 0; h._sync_total()
    before = h.total_hp
    r = L.surgery(Person(skills={"surgery": 30}), h, "left_lower_arm", tools=None, rng=Rng(98, 10))
    assert not r["ok"] and r["infected"] and r["extra_damage"] == 3 and h.total_hp == before - 3
    c.toughness = 0; c.stress_level = 0
    assert TL.day_tick(h, rng=Rng(99))["healed"] == 0 and c.stress_level == 2  # infection blocks healing
    c.toughness = 100
    TL.day_tick(h, rng=Rng(1)); TL.day_tick(h, rng=Rng(1))
    assert h.infection is None and c.alive


def test_severed_cannot_be_reattached_by_surgery():
    c, h = fresh()
    h.health["right_lower_arm"] = 0; L.mark_severed(h, "right_lower_arm")
    doc = Person(skills={"surgery": 90})
    assert not L.surgery(doc, h, "right_lower_arm", "repair", rng=Rng(1))["ok"]
    h.bleeding_wounds.append(bleeding.make_wound("right_lower_arm", 8, "slashing", artery=True))
    assert L.surgery(doc, h, "right_lower_arm", "stabilise", rng=Rng(1))["ok"] and h.limb_state["right_lower_arm"] == "stabilised"
    assert not h.bleeding_wounds
    assert L.surgery(doc, h, "right_lower_arm", "prosthesis", rng=Rng(1))["ok"]
    assert h.limb_state["right_lower_arm"] == "prosthesis" and L.prosthesis_penalty("right_lower_arm")["weapon_skill"] < 0


def test_veil_healing_is_female_only_and_costs_corruption():
    c, h = fresh()
    h.health["left_upper_arm"] = 0; h._sync_total(); c.corruption_level = 0
    assert not L.veil_healing(Person(gender="Male", race="Human", willpower=99), h, "left_upper_arm")["ok"]
    sor = Person(gender="Female", race="Human", skills={"spellcraft": 60}, corruption_level=0)
    r = L.veil_healing(sor, h, "left_upper_arm", rng=Rng(10))
    assert r["ok"] and sor.corruption_level == 5 and c.corruption_level == 2 and h.health["left_upper_arm"] == 1
    h.health["head"] = 0; L.mark_severed(h, "head")  # regrowth is hard: 60-40=20
    r = L.veil_healing(sor, h, "head", rng=Rng(30))
    assert not r["ok"] and sor.corruption_level == 20  # price paid anyway


def test_relic_rules():
    c, h = fresh()
    h.health["left_lower_leg"] = 0; L.mark_severed(h, "left_lower_leg")
    assert not L.relic_heal(h, "left_lower_leg", {"id": "healing_potion", "charges": 1})["ok"]
    relic = {"id": "saint_relic", "charges": 1}
    assert L.relic_heal(h, "left_lower_leg", relic)["ok"] and relic["charges"] == 0
    h.health["left_lower_arm"] = 0
    assert not L.relic_heal(h, "left_lower_arm", relic)["ok"]  # no charges
