"""Strength system tests (docs/STRENGTH.md). Placeholders; these lock in the approved worked examples.
Run: python tests/test_strength.py  (or pytest)"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import strength as S

ROOT = os.path.join(os.path.dirname(__file__), "..")
approx = lambda a, b, tol=0.02: abs(a - b) <= tol


def test_power_curve():
    for st, p in [(30, 1.0), (50, 2.0), (55, 2.83), (60, 4.0), (70, 8.0), (25, 0.75)]:
        assert approx(S.power(st), p), (st, S.power(st))
    assert approx(S.power(60) / S.power(50), S.power(70) / S.power(60))  # human->dwarf == dwarf->ogre


def test_damage_table():
    assert [S.strength_damage_bonus(s, g) for s, g in
            [(30, "F"), (45, "F"), (50, "M"), (55, "M"), (60, "M"), (70, "M")]] == [2, 3, 4, 6, 9, 18]


def test_clinch_m50_vs_m55():
    a, b = S.effective_power(50, "M"), S.effective_power(55, "M")
    assert approx(S.contest_chance(a, b), 0.41, 0.01)
    assert 75 <= S.clinch_seconds_to_exhaustion(a, b) <= 90
    assert 130 <= S.clinch_seconds_to_exhaustion(b, a) <= 145


def test_clinch_man_vs_women():
    m = S.effective_power(50, "M")
    f30, f45 = S.effective_power(30, "F"), S.effective_power(45, "F")
    assert 20 <= S.clinch_seconds_to_exhaustion(f30, m) <= 30     # ~25 s
    assert 55 <= S.clinch_seconds_to_exhaustion(f45, m) <= 65     # ~60 s (Muay Thai 30-60 s)
    assert approx(S.contest_chance(f30, m), 0.24, 0.01)
    assert approx(S.contest_chance(f45, m), 0.35, 0.01)
    assert S.clinch_seconds_to_exhaustion(m, f45) > 140


def test_grapple_odds():
    h, h55, d = S.effective_power(50, "M"), S.effective_power(55, "M"), S.effective_power(60, "M")
    o = S.effective_power(70, "M")
    ot = o * S.bonus_multiplier(20)  # Titanic Might +20 grappling
    assert approx(S.contest_chance(h, d), 1 / 3)
    assert approx(S.contest_chance(h55, d), 0.41, 0.01)
    assert approx(S.contest_chance(d, o), 1 / 3)
    assert approx(S.contest_chance(d, ot), 0.20)
    per = S.contest_chance(h, ot)
    assert approx(per, 0.11, 0.01)
    assert approx(S.chance_over_attempts(per, 2), 0.21, 0.01)
    assert approx(S.contest_chance(2 * h, ot), 0.20)  # one ally pulling
    assert S.contest_chance(0.01, 100) == 0.05 and S.contest_chance(100, 0.01) == 0.95


def test_technique_lets_weaker_win():
    a, b = S.effective_power(50, "M", "arm"), S.effective_power(55, "M", "arm")
    assert S.contest_chance(a, b) < 0.5
    assert approx(S.contest_chance(a, b, S.technique_multiplier(40, 30)), 0.5)   # +10 skill evens out +5 STR
    assert S.contest_chance(a, b, S.technique_multiplier(45, 30)) > 0.53


def test_march_30kg():
    cases = {  # (str, gender, race_mult, END, bonus): expected km
        "avg_man": ((35, "M", 1.0, 30, 0), 14.6), "strong_man": ((50, "M", 1.0, 50, 0), 37.3),
        "avg_woman": ((25, "F", 1.0, 25, 0), 3.0), "trained_woman": ((45, "F", 1.0, 50, 0), 26.3),
        "elf_male": ((30, "M", 1.0, 30, 10), 13.4), "elf_female": ((25, "F", 1.0, 25, 10), 3.4),
        "dwarf40": ((40, "M", 1.5, 35, 0), 36.3), "dwarf60": ((60, "M", 1.5, 60, 0), 90.0)}
    for name, ((st, g, rm, end, bonus), km) in cases.items():
        cap = S.carry_capacity(st, g, rm)
        assert approx(S.march_km_until_exhausted(30, cap, end, bonus), km, 0.3), name
    assert S.march_km_until_exhausted(30, S.carry_capacity(25, "F"), 25) <= 3.2  # breaks by km 3


def test_sustained_hold_and_grip():
    assert S.sustained_hold_cost(4, "F") == 3 and S.sustained_hold_cost(4, "M") == 4
    weak = S.grip_check(25, "F", 40)
    assert not weak["ok"] and weak["parry_penalty"] < 0 and weak["disarm_risk"]
    assert S.grip_check(45, "M", 40)["ok"]
    assert S.grip_check(70, "M", 40)["stamina_mult"] == 0.5


def test_talent_cap_and_character():
    from character import Character
    c = Character(); c.race, c.gender, c.strength = "Human", "Male", 48
    c.progress_stat("strength", 10); assert c.strength == 50
    c.talents = ["iron_thewed"]; c.progress_stat("strength", 10); assert c.strength == 55
    f = Character(); f.race, f.gender, f.strength, f.talents = "Human", "Female", 44, ["iron_thewed"]
    f.progress_stat("strength", 10); assert f.strength == 45
    assert S.iron_thewed_break_free(["iron_thewed"], False, 90)
    assert not S.iron_thewed_break_free(["iron_thewed"], True, 90)
    assert not S.iron_thewed_break_free(["iron_thewed"], False, 600)


def test_rules_files():
    stats = json.load(open(os.path.join(ROOT, "rules/stats.json"), encoding="utf-8"))
    assert stats["Human_Female"]["max_stats"]["agility"] == 60 > stats["Human_Male"]["max_stats"]["agility"]
    for k in ("Elf_Male", "Elf_Female"):
        assert stats[k]["starting_stats"]["charisma"] >= 30
    assert stats["Elf_Female"]["max_stats"]["agility"] > stats["Elf_Male"]["max_stats"]["agility"]
    dw = json.load(open(os.path.join(ROOT, "rules/lore/dwarves.json"), encoding="utf-8-sig"))
    assert dw["mechanics"]["stat_caps"]["strength"] == 60 == stats["Dwarf_Male"]["max_stats"]["strength"]
    w = json.load(open(os.path.join(ROOT, "rules/weapons.json"), encoding="utf-8"))
    assert w["claymore"]["min_STR"] == 40 and w["warhammer"]["min_STR"] == 42
    cr = json.load(open(os.path.join(ROOT, "rules/combat_rules.json"), encoding="utf-8"))
    light = [t for t in cr["load_bands"] if t["name"] == "light"][0] if "load_bands" in cr else None
    assert light["female_stamina_regen_pct"] == 20


if __name__ == "__main__":
    for n, fn in list(globals().items()):
        if n.startswith("test_"):
            fn(); print("ok", n)
