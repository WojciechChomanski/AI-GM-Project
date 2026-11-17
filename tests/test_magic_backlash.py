"""Elemental backlash tracks, Frost/Fire schools, sigils, ritual debt, stigmata."""
import os
import sys
from types import SimpleNamespace

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import magic_backlash as MB
import magic_costs


def _c(**kw):
    d = dict(
        name="Isolde", willpower=30, toughness=25, stamina=60, current_stamina=60,
        hp=50, current_hp=50, total_hp=50, max_hp=50, alive=True, corruption_level=0,
    )
    d.update(kw)
    return d


def test_frost_and_fire_starter_lists_are_subtle():
    ff = MB.frost_fire_spells()
    frost = [s for s in ff.values() if s["school"] == "frost"]
    fire = [s for s in ff.values() if s["school"] == "fire"]
    assert 3 <= len(frost) <= 5 and 3 <= len(fire) <= 5
    for s in ff.values():
        assert s["power_source"] == "Veil"
        assert s["strain"]["track"] == "thermal"
        assert s["band"] in ("light", "standard", "heavy")  # no greater nukes in the starter list
        assert s["costs"]["stamina"] <= 20
        assert int(s.get("damage") or 0) == 0


def test_ordinary_casts_do_not_take_health_until_a_threshold():
    c = _c()
    spell = MB.frost_fire_spells()["rime_latch"]
    before = c["current_hp"]
    r = MB.apply_cast_strain(c, spell)
    assert r["ok"] and r["moved"]["after"] == -1
    assert c["current_hp"] == before
    # three more lights (1 each) reach -4, still no HP loss
    for _ in range(3):
        MB.apply_cast_strain(c, spell)
    assert MB.state(c)["thermal"] == -4
    assert c["current_hp"] == before
    assert MB.penalties(c)["hp_per_round"] == 0
    # one standard (2) crosses -5: still no flat HP, but the threshold now bleeds each round
    MB.apply_cast_strain(c, MB.frost_fire_spells()["still_breath"])
    assert MB.state(c)["thermal"] == -6
    assert c["current_hp"] == before
    assert MB.penalties(c)["hp_per_round"] == 1
    tick = MB.round_tick(c)
    assert tick["hp_lost"] == 1 and c["current_hp"] == before - 1


def test_thermal_overuse_kills_next_round_unless_a_counter_lands():
    c = _c(current_hp=50)
    MB.state(c)["thermal"] = -9
    MB.apply_cast_strain(c, MB.frost_fire_spells()["hoarfrost_veil"])  # heavy 3 → -10 (clamped)
    assert MB.state(c)["thermal"] == -10
    assert c["alive"] is True
    first = MB.round_tick(c)
    assert first["alive"] is True and first.get("death_window")
    # without a counter, the next round kills
    c2 = _c(current_hp=50)
    MB.state(c2)["thermal"] = -10
    MB.state(c2)["_thermal_death_warned"] = True
    dead = MB.round_tick(c2)
    assert dead.get("died") and c2["alive"] is False

    # a counter in the grace round saves her
    c3 = _c(current_hp=50, current_stamina=60)
    MB.state(c3)["thermal"] = -10
    first = MB.round_tick(c3)
    assert first["alive"] is True
    saved = MB.counter_ice_bath(c3)  # 3 toward 0, now -7
    assert saved["ok"] and MB.state(c3)["thermal"] == -7
    later = MB.round_tick(c3, rng=SimpleNamespace(randint=lambda a, b: 100))  # pass toughness
    assert later["alive"] is True and c3["alive"] is True
    assert not later.get("died")

    # hot iron and brazier also count as counters
    c4 = _c(current_hp=50)
    MB.state(c4)["thermal"] = -10
    MB.round_tick(c4)
    assert MB.counter_hot_iron(c4)["ok"]
    assert MB.state(c4)["thermal"] == -7
    assert MB.state(c4).get("_thermal_death_warned") is False
    c5 = _c(current_hp=50)
    MB.state(c5)["thermal"] = 10
    MB.round_tick(c5)
    assert MB.start_brazier_or_snow(c5, "snow")["ok"]
    assert MB.state(c5)["thermal"] == 9
    assert c5["alive"] is True


def test_opposite_element_cancelling_is_provisionally_banned():
    c = _c()
    MB.apply_cast_strain(c, MB.frost_fire_spells()["rime_latch"])
    assert MB.state(c)["thermal"] == -1
    gate = MB.can_cast(c, MB.frost_fire_spells()["wicks_friend"])
    assert gate["ok"] is False and gate.get("provisional") is True
    r = MB.apply_cast_strain(c, MB.frost_fire_spells()["wicks_friend"])
    assert r["ok"] is False and MB.state(c)["thermal"] == -1
    # same element is still allowed
    assert MB.can_cast(c, MB.frost_fire_spells()["still_breath"])["ok"] is True


def test_grave_chill_thresholds_and_hourly_recovery():
    c = _c()
    heavy = {"strain": {"track": "grave_chill", "school": "necromancy", "band": "heavy"}}
    MB.apply_cast_strain(c, heavy)  # +3
    MB.apply_cast_strain(c, heavy)  # +6, crosses 5
    assert MB.state(c)["grave_chill"] == 6
    assert MB.penalties(c)["numb_hand"] is True  # already at 4+
    MB.apply_cast_strain(c, heavy)  # +9, crosses 7
    assert MB.state(c)["grave_hp_penalty_active"] is True
    assert MB.penalties(c)["max_hp_pct"] == -10
    # hitting 10 loses a finger or ear once
    class Pick:
        def choice(self, seq):
            return "finger"
        def randint(self, a, b):
            return 50
    MB.move_grave_chill(c, 5, rng=Pick())
    assert MB.state(c)["grave_chill"] == 10
    assert MB.state(c)["lost_appendage"] == "finger"
    assert MB.state(c)["permanent_penalty"] == -5
    # recovery 1/hour; loss stays
    MB.rest(c, 60)
    assert MB.state(c)["grave_chill"] == 9
    assert MB.state(c)["lost_appendage"] == "finger"
    MB.rest(c, 24 * 60)
    assert MB.state(c)["grave_chill"] == 0
    assert MB.long_rest(c)["ok"] is True
    assert MB.state(c)["grave_hp_penalty_active"] is False
    assert MB.counter_warm_blood(_c(backlash={"grave_chill": 6}))  # smoke the helper


def test_sigil_tiers_and_sigil_ii_heavy_discount():
    c = _c()
    heavy = MB.frost_fire_spells()["hoarfrost_veil"]
    MB.apply_cast_strain(c, heavy)  # +1 from heavy, gain 3, thermal -3, no cross of 5
    assert MB.state(c)["sigil_points"]["frost"] == 1
    # push points to Sigil II
    MB.state(c)["sigil_points"]["frost"] = 8
    tier, pts = MB.sigil_tier_for(c, "frost")
    assert tier["name"] == "Sigil II" and pts == 8
    before = MB.state(c)["thermal"]
    MB.apply_cast_strain(c, heavy)  # heavy 3 - 1 discount = 2, plus another sigil point
    assert MB.state(c)["thermal"] == before - 2
    # III is visible, I/II are not
    MB.state(c)["sigil_points"]["frost"] = 15
    vis = MB.visible_sigils(c)
    assert vis and vis[0]["name"] == "Sigil III"
    # a glove hides III
    assert MB.visible_sigils(c, cover=["glove"]) == []
    MB.state(c)["sigil_points"]["frost"] = 25
    assert MB.visible_sigils(c, cover=["glove"])[0]["name"] == "Branded"


def test_glamour_hides_sigils_from_a_glance_but_not_close_inspection():
    c = _c()
    MB.state(c)["sigil_points"]["fire"] = 15
    assert MB.visible_sigils(c)
    r = MB.glamour_hide_sigils(c)
    assert r["ok"] and r["corruption_added"] == 5 and c["corruption_level"] == 5
    assert r["fails_against"] == "close_physical_inspection"
    assert MB.visible_sigils(c) == []  # casual sight
    assert MB.visible_sigils(c, close_inspection=True)  # undressing or a hunter's mundane exam
    MB.scene_end(c)
    assert MB.visible_sigils(c)  # glamour ended with the scene


def test_ritual_circle_splits_debt_evenly_due_at_dawn():
    a, b, c = _c(name="A"), _c(name="B"), _c(name="C")
    r = MB.start_ritual([a, b, c], "heavy", "thermal", "frost", lead=a)
    assert r["ok"] and r["total"] == 3
    amounts = sorted(x["amount"] for x in r["split"])
    assert amounts == [1, 1, 1]
    assert MB.state(a)["thermal"] == 0  # no cost while casting
    dawn = MB.dawn_tick(a)
    assert dawn["fever_night"] and MB.state(a)["thermal"] == -1
    assert MB.long_rest(a)["ok"] is False  # fever night, no long-rest benefit
    assert MB.long_rest(a)["ok"] is True   # fever has broken
    # remainder goes to the lead: greater (5) with two casters
    d, e = _c(name="D"), _c(name="E")
    r = MB.start_ritual([d, e], "greater", "thermal", "fire", lead=d)
    by = {x["caster"]: x["amount"] for x in r["split"]}
    assert by["D"] == 3 and by["E"] == 2
    MB.dawn_tick(d)
    MB.dawn_tick(e)
    assert MB.state(d)["thermal"] == 3 and MB.state(e)["thermal"] == 2


def test_blood_stigmata_after_own_blood_costs_in_a_scene():
    c = _c()
    assert MB.note_blood_spent(c, 8)["stigmata"] is False
    r = MB.note_blood_spent(c, 8)
    assert r["stigmata"] is True and r["total"] == 16
    assert MB.state(c)["stigmata_rounds"] == 3
    before = c["current_hp"]
    tick = MB.round_tick(c)
    assert tick["hp_lost"] >= 1 and c["current_hp"] == before - tick["hp_lost"]
    assert MB.counter_tourniquet(c)["ok"]
    assert MB.state(c)["stigmata_rounds"] == 0


def test_symptoms_carry_no_hidden_numbers():
    c = _c()
    MB.state(c)["thermal"] = -7
    MB.state(c)["grave_chill"] = 7
    MB.state(c)["sigil_points"]["frost"] = 15
    text = " ".join(x["text"] for x in MB.symptoms(c))
    for banned in ("-7", "+7", "7/10", "corruption 5", "thermal", "track"):
        assert banned not in text.lower() or banned == "thermal" and "thermal" not in text.lower()
    assert "cold" in text.lower() or "bone" in text.lower()
    # felt entries themselves must not include the numeric track
    blob = str(MB.symptoms(c))
    assert "grave_chill" not in blob and "sigil_points" not in blob


def test_rest_is_too_slow_to_beat_the_death_window():
    c = _c()
    MB.state(c)["thermal"] = -10
    MB.round_tick(c)  # grace round
    # 6 seconds is not 10 minutes
    MB.rest(c, 0)
    assert MB.state(c)["thermal"] == -10
    MB.rest(c, 10)
    assert MB.state(c)["thermal"] == -9  # rest can help later, not inside one combat round


def test_area_evidence_and_penalties():
    c = _c()
    MB.state(c)["thermal"] = -5
    ev = MB.area_evidence(c)
    assert ev["kind"] == "frost" and ev["radius_metres"] == 3
    MB.state(c)["thermal"] = 5
    assert MB.area_evidence(c)["kind"] == "scorching"
    p = MB.penalties(c)
    assert p["all"] == -10 and p["stamina_regen_mult"] == 0.5
    MB.state(c)["thermal"] = 7
    assert MB.penalties(c)["stamina_regen_mult"] == 0.0 and MB.penalties(c)["hp_per_round"] == 3
    # collapse on a failed toughness test
    r = MB.round_tick(c, rng=SimpleNamespace(randint=lambda a, b: 1))
    assert r.get("collapsed") and MB.state(c)["collapsed"]
