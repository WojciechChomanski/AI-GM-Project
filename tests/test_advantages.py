import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import addiction  # noqa: E402
import corruption as K  # noqa: E402
import creation as C  # noqa: E402
import knight  # noqa: E402


def test_intensity_flaw_cp_and_dict_form():
    r = C.create_character("Human", "Male", flaws={"alcoholic": 3})
    assert r["cp_total"] == 8 and r["flaw_paid"]["alcoholic"] == 3 and not r["errors"]


def test_diminishing_returns():
    # paid sorted high->low: 5,4 full; 3,2 half
    r = C.create_character("Human", "Male", flaws={"lost_hand": 5, "lost_eye": 4, "alcoholic": 3, "paranoia": 2})
    assert r["flaw_paid"] == {"lost_hand": 5, "lost_eye": 4, "alcoholic": 1, "paranoia": 1}


def test_same_area_pays_once():
    earned, paid = C.flaw_payout([("a", 4, "legs"), ("b", 3, "legs")])
    assert earned == 4 and paid["b"] == 0


def test_heavy_load_stress():
    r = C.create_character("Human", "Male", flaws={"alcoholic": 5, "paranoia": 4, "breakdowns": 3})
    assert r["heavy_load"] and r["stats"].get("stress_level", 0) >= 10


def test_crusader_vows_forbid_profession_and_resources():
    opts = C.options_for("Human", "Male", "Crusader_Knight")["advantages"]
    assert "profession_training" not in opts and "resources" not in opts
    r = C.create_character("Human", "Male", advantages={"resources": 1}, class_name="Crusader_Knight")
    assert r["errors"] and "poverty" in r["vows"]


def test_player_view_hides_gm_stats():
    v = C.player_view({"strength": 40, "faith": 50, "virtue": 75, "piety": 70, "corruption_level": 5})
    assert v == {"strength": 40}


def test_corruption_visibility_and_permanent_marks():
    assert K.visibility(25) == "hidden" and K.visibility(50) == "subtle" and K.visibility(80) == "visible"
    t = K.Tracker()
    t.add(80)
    t.purge(70)
    assert t.level == 10 and "black nails" in t.marks and K.visible_to_others(t.peak)
    assert not K.visible_to_others(60)


def test_corrupted_creature_pool_x3():
    c = K.CorruptedCreature(20)
    assert c.pool == 60
    c.take(20)
    assert not c.dead and c.wound_ratio == 1.0
    c.take(14, breath=True)  # 42 effective
    assert c.effective == 62 and c.dead


def test_breath_tiers():
    assert knight.breath_state(75, 75) == "full"
    assert knight.breath_state(75, 75, corruption=30) == "dim"
    assert knight.breath_state(50, 80) == "dim" and knight.breath_state(20, 90) == "none"
    e = knight.breath_effects(80, 80, 0, ["veilspawn"])
    assert e["bypass_undying"] and e["bleed_rate_mult"] > 1 and e["creature_heal_mult"] < 1
    assert "bypass_undying" not in knight.breath_effects(80, 80, 0, ["human"])


def test_addiction_stress_and_knight_virtue():
    class P:
        stress_level = 5
        virtue = 75
        class_name = "Crusader_Knight"
    p = P()
    assert addiction.indulge(p) == 4 and p.virtue == 71 and p.stress_level == 3
    assert addiction.withdrawal_stage(3, 5) is None and addiction.withdrawal_stage(3, 6)["id"] == "shakes"
    assert addiction.withdrawal_stage(2, 100)["id"] == "sweats_rage"  # fits need intensity 4
    assert addiction.daily_stress(4) == 4


def test_combat_engine_breath_vs_corrupted():
    import random
    try:
        import combat_engine as CE
    except Exception:  # fastapi missing in this env
        import pytest
        pytest.skip("combat_engine deps unavailable")
    base = dict(race="Human", total_hp=20, max_stamina=50, armor_weight=0, inventory_weight=0,
                shield_equipped=False, weapon_equipped=True, weapon="none", armor=[])
    knight_d = dict(base, name="K", class_name="Crusader_Knight", virtue=80, piety=80, weapon_skill=500)
    beast = dict(base, name="B", corrupted=True, creature_tags=["veilspawn"])
    random.seed(3)
    r = CE.CombatEngine().attack_roll(knight_d, beast, weapon_damage=10)
    assert r["hit"] and r["breath_gm_only"]["state"] == "full"
    assert r["defender_hp"] == 60 - r["damage"] * 3
    random.seed(3)
    r2 = CE.CombatEngine().attack_roll(dict(knight_d, virtue=20), beast, weapon_damage=10)
    assert r2["defender_hp"] == 60 - r2["damage"] and r2["damage"] == r["damage"]  # steel rule
