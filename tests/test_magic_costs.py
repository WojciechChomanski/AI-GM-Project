"""Fixed per-cast corruption, sorceress stamina formula, blood vessels, no active Breath spells."""
import json
import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import magic_costs
import blood_vessels
import character_loader


def _load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8-sig") as f:
        return json.load(f)


def test_spell_lists_use_fixed_integer_corruption():
    spells = _load("rules", "spells.json")
    for name, sp in spells.items():
        assert isinstance(sp["corruption"], int) and sp["corruption"] > 0, name
        assert sp.get("power_source") != "Breath", name
    expected = {
        "blood_lash": 5, "fate_whisper": 2, "shadow_bind": 5,
        "decay_touch": 8, "veil_echo": 5, "soul_leech": 8,
    }
    assert {k: spells[k]["corruption"] for k in expected} == expected

    ab = _load("rules", "abilities_magic.json")["spells"]
    assert ab["veil_fog"]["corruption_gain"] == 5
    assert ab["blood_pact"]["corruption_gain"] == 8
    assert ab["whisper_of_fear"]["corruption_gain"] == 5
    assert ab["fade_step"]["corruption_gain"] == 2
    assert ab["shrouds_embrace"]["corruption_gain"] == 15

    vs = _load("rules", "classes", "veil_sorceress.json")["Veil_Sorceress"]
    assert vs["abilities"]["Fade_Step"]["corruption"] == 2
    assert vs["abilities"]["Blood_Pact"]["corruption"] == 8
    assert vs["abilities"]["Shrouds_Embrace"]["corruption"] == 15
    assert vs["abilities"]["Veil_Apotheosis"]["corruption"] == 30  # capstone exception
    assert vs["corruption_system"]["max"] == 100
    assert vs["corruption_system"]["visible_to_player"] is False


def test_cast_corruption_is_guaranteed_and_caps_at_100():
    caster = SimpleNamespace(corruption_level=0, corruption_peak=0, _casts_this_fight=0)
    added = magic_costs.apply_cast_corruption(caster, {"corruption": 5})
    assert added == 5 and caster.corruption_level == 5
    added = magic_costs.apply_cast_corruption(caster, {"corruption": 5}, failed=True, prior_casts_this_scene=1)
    # 5 base + 2 fail extra + 1 snowball
    assert added == 8 and caster.corruption_level == 13
    caster.corruption_level = 97
    added = magic_costs.apply_cast_corruption(caster, {"corruption_gain": 8})
    assert caster.corruption_level == 100
    assert added == 3
    assert magic_costs.gain_for_cast({"corruption": 5}, current_corruption=75, prior_casts_this_scene=2) == 5 + 4


def test_veil_sorceress_stamina_uses_placeholder_negative_class_bonus():
    races = _load("rules", "races.json")
    vs = character_loader.find_class("Veil_Sorceress")
    mage = character_loader.find_class("Mage")
    knight = character_loader.find_class("Knight")
    assert vs["stat_modifiers"]["stamina_max_flat"] == -40
    assert "stamina_max_flat" not in (mage.get("stat_modifiers") or {})
    # PLACEHOLDER -40: Human 60, Elf 70 (the old ~55-70 feel). Mage stays on the plain formula.
    assert magic_costs.stamina_max(races["Human"], vs) == 60
    assert magic_costs.stamina_max(races["Elf"], vs) == 70
    assert character_loader.stamina_max(races["Human"], mage) == 100
    assert character_loader.stamina_max(races["Elf"], mage) == 110
    assert magic_costs.stamina_max(races["Human"], knight) == 100 + knight["stat_modifiers"]["stamina_max_flat"]
    assert vs.get("base_stats") is None


def _person(name, **kw):
    d = dict(name=name, id=name, willpower=30, stamina=40, current_stamina=40,
             hp=40, current_hp=40, total_hp=40, max_hp=40, alive=True,
             corruption_level=0, blood_vessels=[])
    d.update(kw)
    return d


def test_blood_vessel_bind_cap_pay_and_daily_corruption():
    cfg = blood_vessels.data()
    assert cfg["cap"] == 3
    assert cfg["daily_corruption_per_vessel"] == 2
    assert cfg["meta"]["hidden"] is True
    caster = _person("Isolde", stamina=80, current_stamina=80, hp=50, current_hp=50, total_hp=50)
    v1, v2, v3, v4 = [_person(n, willpower=10) for n in ("A", "B", "C", "D")]

    r = blood_vessels.bind(caster, caster, willing=True)
    assert r["ok"] is False and "yourself" in r["reason"]

    r = blood_vessels.bind(caster, v1, willing=True)
    assert r["ok"] and r["vessels"] == 1
    assert caster["corruption_level"] == cfg["bind"]["corruption_willing"]
    assert caster["current_stamina"] == 80 - cfg["bind"]["stamina"]
    assert caster["current_hp"] == 50 - cfg["bind"]["hp"]

    assert blood_vessels.bind(caster, v2, willing=True)["ok"]
    assert blood_vessels.bind(caster, v3, willing=True)["ok"]
    r = blood_vessels.bind(caster, v4, willing=True)
    assert r["ok"] is False and "cap" in r["reason"]
    assert len(caster["blood_vessels"]) == 3

    # Blood cost is paid by an in-range vessel, not the caster.
    before = caster["current_hp"]
    paid = blood_vessels.pay_blood(caster, 6, vessel=v1, distance_metres=10)
    assert paid["ok"] and paid["from"] == "vessel" and v1["current_hp"] == 40 - 6
    assert caster["current_hp"] == before

    # Out of range: caster pays instead.
    before_c, before_v = caster["current_hp"], v2["current_hp"]
    paid = blood_vessels.pay_blood(caster, 5, vessel=v2, distance_metres=50)
    assert paid["from"] == "caster" and "range" in (paid.get("reason") or "")
    assert caster["current_hp"] == before_c - 5
    assert v2["current_hp"] == before_v

    # Daily tick: each of 3 vessels adds 2, even with no casting.
    before = caster["corruption_level"]
    day = blood_vessels.day_tick(caster)
    assert day["vessels"] == 3 and day["corruption_added"] == 6
    assert caster["corruption_level"] == before + 6

    # Vessel death snaps the bond and shocks the caster.
    v1["current_hp"] = 3
    paid = blood_vessels.pay_blood(caster, 3, vessel=v1, distance_metres=5)
    assert paid.get("vessel_died") and len(caster["blood_vessels"]) == 2
    assert v1["alive"] is False


def test_unwilling_bind_resists_on_a_lost_willpower_contest():
    caster = _person("Isolde", willpower=10, stamina=80, current_stamina=80, hp=50, current_hp=50, total_hp=50)
    victim = _person("Guardsman", willpower=40)

    class AlwaysLow:
        def randint(self, a, b):
            return 1  # both roll 1; higher willpower (the victim) wins the tie-break rules (ties to defender; 11 vs 41)

    r = blood_vessels.bind(caster, victim, willing=False, rng=AlwaysLow())
    assert r["ok"] is False and r["reason"] == "willpower resisted"
    assert r["paid"] is True
    assert caster["blood_vessels"] == []
    assert caster["corruption_level"] == blood_vessels.data()["bind"]["corruption_unwilling"]

    class AlwaysHigh:
        def randint(self, a, b):
            return 100

    caster2 = _person("Lyssa", willpower=50, stamina=80, current_stamina=80, hp=50, current_hp=50, total_hp=50)
    weak = _person("Serf", willpower=10)
    r = blood_vessels.bind(caster2, weak, willing=False, rng=AlwaysHigh())
    # 150 vs 110 — caster wins
    assert r["ok"] is True
    assert caster2["corruption_level"] == blood_vessels.data()["bind"]["corruption_unwilling"]


def test_magic_system_refuses_active_breath_spells():
    from magic_system import MagicSystem
    ms = MagicSystem(spells_file=os.path.join(ROOT, "rules", "spells.json"))
    # inject a forbidden leftover to prove the guard, without writing it to disk
    ms.spells = dict(ms.spells)
    ms.spells["divine_verdict"] = {"type": "breath", "stamina_cost": 8, "corruption": 0}
    assert "divine_verdict" not in _load("rules", "spells.json")
    caster = SimpleNamespace(
        name="Caldran", race="Human", gender="Male", stamina=40, pain_penalty=0,
        corruption_level=0, status_effects=[],
    )
    caster.stamina_penalty = lambda: 0
    ok = ms.cast_spell(caster, SimpleNamespace(name="dummy"), "divine_verdict", None, None)
    assert ok is False
    assert caster.stamina == 40  # not spent


def test_time_loop_day_tick_applies_vessel_corruption(monkeypatch):
    import time_loop as TL
    import limb_repair
    import wound_recovery as WR
    import ogre_hunger

    caster = _person("Isolde", corruption_level=4)
    caster["blood_vessels"] = [{"vessel_id": "A", "name": "A", "willing": True}]
    manager = SimpleNamespace(character=caster, infection=None)
    monkeypatch.setattr(limb_repair, "states", lambda m: None)
    monkeypatch.setattr(limb_repair, "infection_day", lambda m, rng=None: None)
    monkeypatch.setattr(limb_repair, "regrow_day", lambda m: 0)
    monkeypatch.setattr(ogre_hunger, "day_end", lambda m, c, rng=None: None)
    monkeypatch.setattr(ogre_hunger, "is_fed", lambda c: True)
    monkeypatch.setattr(WR, "heal_manager_day", lambda m, fed, mode: 0)
    rep = TL.day_tick(manager, "resting")
    assert rep["vessel_corruption"]["vessels"] == 1
    assert rep["vessel_corruption"]["corruption_added"] == 2
    assert caster["corruption_level"] == 6


def test_foundry_class_rules_keep_stamina_bonus_but_hide_corruption():
    import build_foundry_packs as BP
    vs = _load("rules", "classes", "veil_sorceress.json")["Veil_Sorceress"]
    packed = BP.strip_player({k: v for k, v in vs.items() if k not in ("description", "lore")})
    blob = json.dumps(packed)
    assert packed["stat_modifiers"]["stamina_max_flat"] == -40
    assert "corruption_system" not in packed
    assert "corruption" not in packed["abilities"]["Fade_Step"]
    assert "blood_vessel" not in blob
    assert "blood_vessels" not in blob
