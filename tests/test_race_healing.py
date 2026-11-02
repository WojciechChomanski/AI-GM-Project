import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import character_store as CS  # noqa: E402
import creation as C  # noqa: E402
import limb_repair as L  # noqa: E402
import time_loop as TL  # noqa: E402
import wound_recovery as WR  # noqa: E402
from test_bleeding import fresh  # noqa: E402
from test_time_loop import Person, Rng  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def body(race):
    c, h = fresh()
    c.race = race
    return c, h


def test_dwarf_heals_1_5x_with_carry_and_loses_it_unfed():
    assert WR.heal_mult("Dwarf") == 1.5 and WR.heal_mult("Dwarf", fed=False) == 1.0
    c, h = body("Dwarf")
    h.health["chest"] -= 10; h._sync_total()
    got = [TL.day_tick(h)["healed"] for _ in range(4)]
    assert got == [1, 2, 1, 2]  # 1.5/day carried over
    assert TL.day_tick(h, fed=False)["healed"] == 1  # unfed: normal rate


def test_medicine_skill_and_talent():
    doc = Person(intelligence=40, dexterity=40, skills={"medicine": 3}, talents=["field_surgeon"])
    assert L.surgery_skill(doc) == 40 + 15 + 10
    assert L.surgery_skill(Person(intelligence=40, dexterity=40, skills={"medicine": 9})) == 65  # rank max 5
    assert L.surgery_skill(Person(skills={"surgery": 30, "medicine": 5})) == 30  # legacy absolute override


def test_cleric_is_mundane_medic():
    with open(os.path.join(ROOT, "rules/classes/cleric.json"), encoding="utf-8-sig") as f:
        cl = json.load(f)["Cleric"]
    assert "healing_bonus" not in cl["stats"] and cl["skills"]["medicine"] == 3
    assert "heal" not in json.dumps(cl.get("abilities", {})).lower()


def test_rune_prosthesis():
    c, h = body("Human")
    h.health["right_lower_arm"] = 0; L.mark_severed(h, "right_lower_arm")
    smith = {"race": "Dwarf", "master_smith": True}
    assert not L.rune_prosthesis(h, "right_lower_arm", "iron", {"race": "Human", "master_smith": True})["ok"]
    r = L.rune_prosthesis(h, "right_lower_arm", "adamantine", smith, weapon="hidden_blade")
    assert r["ok"] and r["cost_gold"] == 2650 and r["weeks"] == 10
    assert h.health["right_lower_arm"] == 6 and h.zone_armor_bonus["right_lower_arm"] == 5
    assert L.prosthesis_penalty("right_lower_arm") and h.limb_state["right_lower_arm"] == "rune_prosthesis"
    # armour on the metal limb, and metal does not bleed
    assert h.take_damage_to_zone("right_lower_arm", 4, "slashing", use_armor=False) == 0
    h.take_damage_to_zone("right_lower_arm", 8, "slashing", use_armor=False)
    assert not h.bleeding_wounds
    e, eh = body("Elf")
    eh.health["left_lower_leg"] = 0; L.mark_severed(eh, "left_lower_leg")
    assert not L.rune_prosthesis(eh, "left_lower_leg", "iron", smith)["ok"]
    assert not L.rune_prosthesis(eh, "left_lower_leg", "iron", smith, weapon="hand_gun")["ok"]


def test_ogre_can_buy_and_leg_cannot_hold_gun():
    o, oh = body("Ogre")
    oh.health["left_lower_leg"] = 0; L.mark_severed(oh, "left_lower_leg")
    smith = {"race": "Dwarf", "master_smith": True}
    assert not L.rune_prosthesis(oh, "left_lower_leg", "iron", smith, weapon="hand_gun")["ok"]
    assert L.rune_prosthesis(oh, "left_lower_leg", "iron", smith)["ok"]


def test_elven_restoration():
    d, dh = body("Dwarf")
    dh.health["left_upper_arm"] = 0; L.mark_severed(dh, "left_upper_arm")
    assert not L.elven_restoration(dh, "left_upper_arm")["ok"]
    c, h = body("Human")
    h.health["left_upper_arm"] = 0; L.mark_severed(h, "left_upper_arm")
    r = L.elven_restoration(h, "left_upper_arm")
    assert r["ok"] and r["days"] == 30 and r["cost_gold"] == 3000
    for _ in range(29):
        TL.day_tick(h)
    assert h.health["left_upper_arm"] == 0
    assert TL.day_tick(h)["regrown"] == ["left_upper_arm"] and h.health["left_upper_arm"] == 6
    assert "left_upper_arm" not in h.limb_state


def test_elves_cannot_take_scarred():
    assert "scarred" not in C.options_for("Elf", "Male")["disadvantages"]
    assert "scarred" in C.options_for("Human", "Male")["disadvantages"]
    assert C.create_character("Elf", "Male", flaws={"scarred": 2})["errors"]


def test_save_load_and_console(tmp_path):
    c, h = body("Dwarf")
    c.name = "Borin"
    h.health["chest"] -= 6; h.health["left_lower_arm"] = 0; L.mark_severed(h, "left_lower_arm"); h._sync_total()
    loaded = {"Borin": h}
    assert "Borin.json" in CS.console_command("save Borin", loaded, str(tmp_path))
    loaded2 = {}
    assert CS.console_command("load Borin", loaded2, str(tmp_path)) == "loaded Borin"
    m = loaded2["Borin"]
    assert m.health == h.health and m.limb_state == {"left_lower_arm": "severed"} and m.character.race == "Dwarf"
    out = CS.console_command("tick day 2 bed_rest_with_care", loaded2, str(tmp_path))
    assert "Borin" in out and m.health["chest"] == h.health["chest"] + 6
    assert "Borin" in CS.console_command("list", loaded2, str(tmp_path))
    assert "no save" in CS.console_command("load Nobody", {}, str(tmp_path))
