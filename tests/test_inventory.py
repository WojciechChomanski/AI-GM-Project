"""Inventory and carried load (Foundry 0.3). Ported numbers must match scripts/strength.py.
Run: pytest -q tests/test_inventory.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import inventory as I
import strength as S

ROOT = os.path.join(os.path.dirname(__file__), "..")
approx = lambda a, b, tol=1e-6: abs(a - b) <= tol


def _item(**kwargs):
    base = {"id": kwargs.get("id") or kwargs.get("name") or "x", "type": "gear", "weight": 0,
            "flags": {"breath-and-the-veil": {}}}
    flags = kwargs.pop("flags", None)
    loc = kwargs.pop("location", None)
    cid = kwargs.pop("container_id", None)
    equipped = kwargs.pop("equipped", None)
    base.update(kwargs)
    breath = base["flags"].setdefault("breath-and-the-veil", {})
    if flags:
        breath.update(flags)
    if loc:
        breath["location"] = loc
    if cid:
        breath["container_id"] = cid
    if equipped is not None:
        base["equipped"] = equipped
        breath["equipped"] = equipped
    return base


def pack(pid="travellers_backpack", location="body", **kwargs):
    src = next(p for p in I.RULES["backpacks"]["items"] if p["id"] == pid)
    data = dict(src)
    data.update(kwargs)
    return _item(
        id=data["id"], name=data["name"], type="gear", weight=data["weight"],
        slot=data["slot"], is_container=True, capacity_kg=data["capacity_kg"],
        location=location, equipped=(location == "body"), source_id=data["id"],
    )


def weapon(wid, weight, wtype="1H_sword", location="body", **kwargs):
    return _item(id=wid, name=wid, type="weapon", weight=weight, weapon_type=wtype,
                 location=location, equipped=(location == "body"), source_id=wid, **kwargs)


def armor(aid, weight, coverage, location="body", **kwargs):
    return _item(id=aid, name=aid, type="armor", weight=weight, coverage=coverage,
                 location=location, equipped=(location == "body"), source_id=aid, **kwargs)


def test_capacity_matches_strength_module():
    # Average man, trained woman, dwarf, ogre: same formula as scripts/strength.py.
    assert approx(I.carry_capacity(35, "M", "Human"), S.carry_capacity(35, "M", 1.0))
    assert approx(I.carry_capacity(35, "Male", "Human"), (20 + 35 * 1.5) * 1.15)
    assert approx(I.carry_capacity(25, "F", "Human"), 20 + 25 * 1.5)
    assert approx(I.carry_capacity(40, "M", "Dwarf"), S.carry_capacity(40, "M", 1.5))
    assert approx(I.carry_capacity(70, "M", "Ogre"), S.carry_capacity(70, "M", 3.0))
    assert approx(I.carry_capacity(30, "M", "Elf"), S.carry_capacity(30, "M", 1.0))
    # Worked numbers
    assert approx(I.carry_capacity(35, "M", "Human"), 83.375)
    assert approx(I.carry_capacity(50, "M", "Human"), 109.25)
    assert approx(I.carry_capacity(40, "M", "Dwarf"), 138.0)
    assert approx(I.carry_capacity(70, "M", "Ogre"), 431.25)


def test_ox_back_multiplies_capacity():
    base = I.carry_capacity(35, "M", "Human")
    boosted = I.carry_capacity(35, "M", "Human", talents=["ox_back"])
    assert approx(boosted, base * 1.15)
    assert approx(I.carry_capacity(35, "M", "Human", talents=["iron_thewed"]), base)


def test_load_tiers_from_combat_rules():
    # Average man, capacity 83.375 kg
    cap = I.carry_capacity(35, "M", "Human")
    assert I.load_tier(I.load_ratio(0, cap)) == "light"
    assert I.load_tier(I.load_ratio(cap * 0.2, cap)) == "light"
    assert I.load_tier(I.load_ratio(cap * 0.2 + 0.01, cap)) == "medium"
    assert I.load_tier(I.load_ratio(cap * 0.5, cap)) == "medium"
    assert I.load_tier(I.load_ratio(cap * 0.5 + 0.01, cap)) == "heavy"
    assert I.load_tier(I.load_ratio(cap, cap)) == "heavy"
    assert I.load_tier(I.load_ratio(cap + 0.01, cap)) == "overloaded"


def test_band_penalties_ported():
    light_f = I.tier_penalties("light", "F")
    assert light_f["stamina_regen_pct"] == 20
    light_m = I.tier_penalties("light", "M")
    assert light_m["stamina_regen_pct"] == 0
    heavy_f = I.tier_penalties("heavy", "F")
    assert heavy_f["stamina_drain_pct"] == 30 and heavy_f["dex_aim_penalty"] == -10
    heavy_m = I.tier_penalties("heavy", "M")
    assert heavy_m["stamina_drain_pct"] == 15 and heavy_m["agility_penalty"] == -5


def test_overloaded_blocks_sprint_acrobatics_and_unaided_rope():
    for action in ("sprint", "acrobatics", "rope_climb_unaided"):
        assert I.action_allowed("heavy", action)
        assert not I.action_allowed("overloaded", action)
    assert I.action_allowed("overloaded", "climb") is True  # harder, not blocked
    assert I.action_penalty("overloaded", "climb")["athletics_penalty"] == -40
    assert I.action_penalty("heavy", "climb")["athletics_penalty"] == -20


def test_user_example_average_man_with_70kg():
    """A STR 35 man has 83.375 kg capacity, so 60-70 kg is still 'heavy', not overloaded.
    That mismatch is a design question; the formula is not changed here."""
    ev = I.evaluate(35, "M", "Human", [_item(id="gear", name="kit", type="gear", weight=70,
                                             location="backpack", container_id="none")])
    # 70 kg with no pack weight
    assert ev["tier"] == "heavy"
    assert ev["actions"]["sprint"]["allowed"]
    assert ev["actions"]["rope_climb_unaided"]["allowed"]
    ev_over = I.evaluate(35, "M", "Human", [_item(id="gear", name="kit", type="gear", weight=90,
                                                  location="backpack")])
    assert ev_over["tier"] == "overloaded"
    assert not ev_over["actions"]["sprint"]["allowed"]
    assert not ev_over["actions"]["rope_climb_unaided"]["allowed"]
    assert ev_over["actions"]["walk"]["allowed"]


def test_clinch_mass_counts_as_carried_load():
    ev = I.evaluate(35, "M", "Human", [], clinch_mass_kg=80)
    assert ev["carried_kg"] == 80
    assert ev["tier"] == "heavy"  # 80 / 83.375
    ev2 = I.evaluate(35, "M", "Human", [], clinch_mass_kg=90)
    assert ev2["tier"] == "overloaded"


def test_past_half_load_flag_matches_march_cliff():
    cap = I.carry_capacity(35, "M", "Human")
    light = I.evaluate(35, "M", "Human", [_item(id="a", type="gear", weight=10, location="body")])
    assert not light["past_half_load"]
    heavyish = I.evaluate(35, "M", "Human", [_item(id="a", type="gear", weight=cap * 0.6, location="body")])
    assert heavyish["past_half_load"]
    assert S.march_cost_per_km(cap * 0.6, cap) > S.march_cost_per_km(cap * 0.4, cap)


def test_action_economy_penalties_by_ratio():
    # Separate from named load bands: 0.5 / 0.8 / 1.0
    assert I.action_economy_penalties(0.4)["ap_penalty"] == 0
    assert I.action_economy_penalties(0.7)["ap_penalty"] == 1
    assert I.action_economy_penalties(0.9)["ap_penalty"] == 2
    over = I.action_economy_penalties(1.2)
    assert over["ap_penalty"] == 3 and over["placeholder"]


def test_drop_weapon_onto_free_hand():
    result = I.place_item([], weapon("arming_sword", 5, location=""))
    assert result["ok"] and result["location"] == "body" and result["equipped"]
    assert "main_hand" in result["slots"]


def test_drop_two_hander_occupies_both_hands():
    result = I.place_item([], weapon("claymore", 12, wtype="2H_sword", location=""))
    assert result["ok"] and set(result["slots"]) == {"main_hand", "off_hand"}


def test_second_weapon_goes_to_backpack():
    held = weapon("arming_sword", 5)
    bp = pack()
    second = weapon("messer", 5, location="")
    result = I.place_item([held, bp], second)
    assert result["ok"] and result["location"] == "backpack"
    assert result["container_id"] == "travellers_backpack"
    assert not result["equipped"]


def test_refuse_when_hands_full_and_no_pack():
    held = weapon("arming_sword", 5)
    second = weapon("messer", 5, location="")
    result = I.place_item([held], second)
    assert not result["ok"]
    assert "pack" in result["message"].lower()


def test_refuse_when_backpack_is_full():
    bp = pack("satchel")  # 8 kg capacity
    stuffed = _item(id="rocks", name="Rocks", type="gear", weight=8,
                    location="backpack", container_id="satchel")
    extra = _item(id="apple", name="Apple", type="gear", weight=0.5, location="")
    result = I.place_item([bp, stuffed], extra)
    assert not result["ok"]
    assert "No room" in result["message"]


def test_item_fits_in_pack_with_remaining_space():
    bp = pack("satchel")
    stuffed = _item(id="rocks", name="Rocks", type="gear", weight=7,
                    location="backpack", container_id="satchel")
    extra = _item(id="apple", name="Apple", type="gear", weight=0.5, location="")
    result = I.place_item([bp, stuffed], extra)
    assert result["ok"] and result["location"] == "backpack"


def test_armor_coverage_conflict_goes_to_pack():
    plate = armor("full_plate", 32.2, ["chest", "stomach", "head"])
    bp = pack()
    padded = armor("padded", 5, ["chest"], location="")
    result = I.place_item([plate, bp], padded)
    assert result["ok"] and result["location"] == "backpack"


def test_non_overlapping_armor_equips():
    helm = armor("helm", 2, ["head"])
    chest = armor("padded", 5, ["chest"], location="")
    result = I.place_item([helm], chest)
    assert result["ok"] and result["location"] == "body"


def test_second_backpack_is_refused():
    first = pack("satchel")
    second = pack("travellers_backpack", location="")
    result = I.place_item([first], second)
    assert not result["ok"]
    assert "back" in result["message"].lower()


def test_class_and_race_are_not_inventory():
    klass = {"id": "knight", "type": "class", "name": "Knight"}
    result = I.place_item([], klass)
    assert result["ok"] and result["physical"] is False


def test_carried_weight_sums_body_and_backpack():
    bp = pack("satchel")  # 0.8 kg
    sword = weapon("arming_sword", 5)
    stones = _item(id="stones", type="gear", weight=3, location="backpack", container_id="satchel")
    leftover = _item(id="left", type="gear", weight=99, location="")  # not yet accepted
    assert approx(I.carried_weight([bp, sword, stones, leftover]), 0.8 + 5 + 3)


def test_missing_weapon_weights_are_flagged_and_count_as_zero():
    missing = weapon("longsword", None, wtype="sword")
    missing.pop("weight", None)
    # force no weight
    missing["weight"] = None
    missing["system"] = {"source_id": "longsword"}
    assert I.item_weight(missing) == 0
    ev = I.evaluate(35, "M", "Human", [missing])
    assert "longsword" in ev["missing_weight_items"]


def test_rules_file_placeholders_are_labelled():
    r = I.RULES
    assert r["backpacks"]["placeholder"] is True
    assert r["action_restrictions"]["placeholder"] is True
    assert "warhammer" in r["missing_weights"]["weapons"]
    # Capacity constants match combat_rules.json
    cr = json.load(open(os.path.join(ROOT, "rules", "combat_rules.json"), encoding="utf-8"))
    assert r["carry_capacity"]["male_multiplier"] == cr["carry_capacity"]["male_multiplier"]
    assert r["carry_capacity"]["per_strength"] == 1.5
    dwarves = json.load(open(os.path.join(ROOT, "rules", "lore", "dwarves.json"), encoding="utf-8-sig"))
    assert r["carry_capacity"]["race_multipliers"]["Dwarf"] == dwarves["mechanics"]["base_modifiers"]["carry_capacity_multiplier"]


def test_foundry_copy_matches_rules():
    src = json.load(open(os.path.join(ROOT, "rules", "inventory.json"), encoding="utf-8"))
    copy = os.path.join(ROOT, "foundry", "system", "breath-and-the-veil", "module", "inventory-rules.json")
    dst = json.load(open(copy, encoding="utf-8"))
    assert src == dst


def test_no_hidden_stats_in_inventory_modules():
    hidden = ("faith", "virtue", "piety", "holy_fury", "corruption", "stress", "reputation")
    for rel in (
        "scripts/inventory.py",
        "foundry/system/breath-and-the-veil/module/inventory.mjs",
        "foundry/system/breath-and-the-veil/module/inventory-rules.json",
        "rules/inventory.json",
        "foundry/system/docs/INVENTORY.md",
    ):
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read().lower()
        # Allow the words only in a sentence that says they are absent / not used.
        for word in hidden:
            if word in text:
                for line in text.splitlines():
                    if word in line:
                        assert any(s in line for s in ("not used", "not in", "absent", "hidden stats are not",
                                                       "are not used", "never", "stripped", "must not")), (
                            f"{rel} mentions {word}: {line}"
                        )


def test_actor_inventory_state_mirrors_model():
    bp = pack()
    sword = weapon("arming_sword", 5)
    stones = _item(id="stones", type="gear", weight=3, location="backpack", container_id="travellers_backpack")
    state = I.actor_inventory_state([bp, sword, stones], 35, "M", "Human")
    assert state["equipped"]["main_hand"] == "arming_sword"
    assert state["equipped"]["back"] == "travellers_backpack"
    assert state["backpack"]["itemId"] == "travellers_backpack"
    assert state["backpack"]["contents"] == ["stones"]
    assert abs(state["carried_weight"] - (1.5 + 5 + 3)) < 1e-9
    assert abs(state["carry_capacity"] - I.carry_capacity(35, "M", "Human")) < 1e-9
    assert "chest" in state["equipped"] and state["equipped"]["chest"] == ""
