"""Progression, creation, talents, mastery (docs/PROGRESSION.md). Placeholders; these lock in the approved rules."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import talents as T
import creation as C
import progression as P
import strength as S
from character import Character

ROOT = os.path.join(os.path.dirname(__file__), "..")


def mk(race="Human", gender="Male", **stats):
    c = Character(); c.race, c.gender, c.name = race, gender, "Test"
    for k, v in stats.items():
        setattr(c, k, v)
    return c


def test_talent_folder_loads_and_iron_thewed_migrated():
    t = T.load_talents(refresh=True)
    assert "iron_thewed" in t and len(t) == 16
    assert not os.path.exists(os.path.join(ROOT, "rules", "talents.json"))
    it = t["iron_thewed"]["effects"]
    assert it["start_bonus"] == {"strength": 3} and it["cap_raise"] == {"strength": 5} and it["growth_mult"] == {"strength": 0.75}


def test_talent_caps_limited_to_plus_5_and_locked():
    assert S.stat_cap(50, "Human", "Male", "strength", ["iron_thewed"]) == 55
    assert S.stat_cap(45, "Human", "Female", "strength", ["iron_thewed"]) == 45
    assert T.cap_raise("toughness", "Dwarf", "Male", ["stone_born"]) == 5
    assert T.cap_raise("toughness", "Human", "Male", ["stone_born"]) == 0
    assert not T.allowed_for(T.get_talent("veil_gifted"), "Human", "Male")
    assert T.allowed_for(T.get_talent("light_footed"), "Elf", "Male")
    assert not T.allowed_for(T.get_talent("light_footed"), "Human", "Male")


def test_thirteen_flaws():
    f = C.load_flaws()
    assert len(f) == 13
    assert f["lost_eye"]["cp"] == 4 and f["lost_hand"]["cp"] == 5 and f["old_debt"]["cp"] == [1, 3]


def test_creation_budget():
    r = C.create_character("Human", "Male", flaws=[], talents=[], stat_buys={"strength": 2})
    assert r["cp_total"] == 5 and r["stats"]["strength"] == 39 and not r["errors"]
    r = C.create_character("Human", "Male", flaws=["lost_eye", "lost_hand", "limp", "paranoia"])
    assert r["cp_total"] == 15  # 15 flaw CP capped at 10 + 5 free
    assert r["stats"]["ballistic_skill"] == 10 and r["caps"]["mobility"] == 50
    r = C.create_character("Human", "Male", talents=["iron_thewed", "battle_born"])
    assert any("only 5" in e for e in r["errors"])
    r = C.create_character("Human", "Male", talents=["iron_thewed", "battle_born", "survivor"])
    assert any("max 2 talents" in e for e in r["errors"])
    r = C.create_character("Human", "Male", talents=["iron_thewed"])
    assert r["stats"]["strength"] == 38 and r["caps"]["strength"] == 55 and not r["errors"]
    r = C.create_character("Human", "Male", talents=["hawk_eyed"], flaws=["lost_eye"])
    assert r["errors"]
    r = C.create_character("Human", "Male", flaws=["veil_tainted"])
    assert r["errors"]
    r = C.create_character("Human", "Female", flaws=["veil_tainted"])
    assert r["stats"]["corruption_level"] == 10 and not r["errors"]
    r = C.create_character("Human", "Male", stat_buys={"strength": 4})
    assert r["errors"]


def test_uses_needed():
    assert P.uses_needed(30, 50) == 30
    assert P.uses_needed(45, 50) == 420          # near cap x2
    assert P.uses_needed(44, 50) == 198
    assert P.uses_needed(44, 50, 0.75) == 149    # 25% faster


def test_growth_per_character_and_session_limit():
    a, b = mk(strength=35), mk(strength=35)
    P.record_use(a, "strength", 500)
    msgs = P.check_growth(a, lambda c, s: 50)
    assert a.strength == 36 and len(msgs) == 1
    assert P.check_growth(a, lambda c, s: 50) == [] and a.strength == 36  # 1 point per session
    P.new_session(a); P.check_growth(a, lambda c, s: 50)
    assert a.strength == 37
    assert b.progression.get("uses", {}).get("strength", 0) == 0  # not shared


def test_failure_counts_double():
    a = mk()
    P.record_action(a, "melee_attack", failed=True)
    assert a.progression["uses"] == {"weapon_skill": 2, "strength": 2}


def test_growth_honours_iron_thewed_cap():
    a = mk(strength=50); a.talents = ["iron_thewed"]
    P.record_use(a, "strength", 10000)
    P.check_growth(a)
    assert a.strength == 51
    h = mk(strength=50); P.record_use(h, "strength", 10000); P.check_growth(h)
    assert h.strength == 50


def test_ballistic_skill_in_stats_and_used_for_ranged():
    s = json.load(open(os.path.join(ROOT, "rules", "stats.json"), encoding="utf-8-sig"))
    assert s["Human_Male"]["starting_stats"]["ballistic_skill"] == 25 and s["Ogre_Male"]["max_stats"]["ballistic_skill"] == 30
    assert s["Elf_Female"]["max_stats"]["ballistic_skill"] == 60
    c = mk(weapon_skill=40, ballistic_skill=20)
    assert P.attack_skill(c, {"name": "Longbow", "type": "ranged"}) == 20
    assert P.attack_skill(c, {"name": "Javelin", "type": "thrown"}) == 20
    assert P.attack_skill(c, {"name": "Claymore", "type": "2H_sword"}) == 40


def test_mastery_ranks_and_ceiling():
    c = mk()
    assert P.mastery_modifiers(c, {"name": "claymore", "type": "2H_sword"})["to_hit"] == 0
    for uses, rank in [(49, 0), (50, 1), (150, 2), (400, 3), (900, 4), (2000, 5), (99999, 5)]:
        c.progression = {}; P.record_mastery(c, "greatsword", uses)
        assert P.mastery_rank(c, "greatsword") == rank
    m = P.mastery_modifiers(c, {"name": "claymore", "type": "2H_sword"}, "two_hander")
    assert (m["to_hit"], m["damage"], m["stamina"], m["trick"]) == (5, 1, -2, True)
    assert P.stamina_per_attack(5, m) == 3 and P.stamina_per_attack(3, m) == 2 and P.stamina_per_attack(2, m) == 2
    assert P.mastery_modifiers(c, {"name": "mace", "type": "1H_blunt"})["to_hit"] == 0  # no cross-family stacking


def test_battle_born_speeds_melee_mastery_only():
    c = mk(); c.talents = ["battle_born"]; P.record_mastery(c, "mace", 40); P.record_mastery(c, "bow", 40)
    assert P.mastery_rank(c, "mace") == 1 and P.mastery_rank(c, "bow") == 0


def test_shield_and_dual_wield_tracks():
    c = mk(); P.record_mastery(c, "shield", 400); P.record_mastery(c, "dual_wield", 150)
    m = P.mastery_modifiers(c, {"name": "arming_sword", "type": "1H_sword"}, "shield")
    assert m["block"] == 10 and m["shield_stamina"] == -1
    assert P.dual_wield_offhand_penalty(c) == -15


def test_action_points_d100():
    assert [P.action_points(a) for a in (20, 25, 30, 40, 55, 60)] == [5, 6, 6, 7, 8, 8]


def test_backgrounds_rescaled():
    b = json.load(open(os.path.join(ROOT, "rules", "backgrounds.json"), encoding="utf-8-sig"))
    for v in b.values():
        for k, n in v["stats"].items():
            assert not k.endswith("_modifier") and abs(n) <= 10
