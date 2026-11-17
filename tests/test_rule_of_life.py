import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import rule_of_life as R  # noqa: E402
import knight  # noqa: E402
import build_foundry_packs as B  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _knight(**kw):
    c = {
        "name": "Brother",
        "class_name": "Crusader_Knight",
        "virtue": 75,
        "piety": 70,
        "corruption_level": 0,
    }
    c.update(kw)
    return c


def test_piety_gain_table_and_rule_cap():
    cfg = R.data()["piety"]
    assert cfg["gain_table"]["rule_kept"] == 2
    assert cfg["gain_table"]["rule_broken"] == -4
    assert cfg["rule_alone_cap"] == 80
    assert cfg["start_default"] == 50
    k = _knight(piety=78)
    R.day_tick(k, rule_kept=True)
    R.day_tick(k, rule_kept=True)
    assert k["piety"] == 80
    R.day_tick(k, rule_kept=False)
    assert k["piety"] == 76


def test_honest_drunk_recovers_in_two_kept_days():
    ex = R.data()["worked_examples"]["honest_drunk"]
    k = _knight(virtue=ex["start_virtue"], piety=70, corruption_level=0)
    stain = R.record_sin(k, ex["sin"])
    assert stain["grade"] == "venial" and stain["weight"] == 4
    assert k["virtue"] == ex["after_sin"] == 71
    assert R.caps_breath_at_dim(k) is False
    R.day_tick(k, rule_kept=True)
    R.day_tick(k, rule_kept=True)
    assert k["virtue"] == ex["recovered_virtue"] == 75
    assert R.open_stains(k) == []
    assert R.state(k)["week_cleanse_used"] == 4


def test_daily_cleansing_slows_and_caps_the_week():
    k = _knight()
    # eight cursing stains of weight 1 would be too small; use gambling/drugs mix
    for _ in range(3):
        R.record_sin(k, "vice_gambling")  # 4 each, venial
    # force the day already ticked so the next ticks are kept days
    R.state(k)["day"] = 1
    totals = []
    for _ in range(7):
        r = R.day_tick(k, rule_kept=True)
        totals.append(r["cleansed"])
    # 2+2+2+1+1 then 0 once the weekly max of 8 is hit
    assert totals[:5] == [2, 2, 2, 1, 1]
    assert sum(totals) == 8
    assert sum(s["weight"] for s in R.open_stains(k, "venial")) == 12 - 8


def test_prayer_never_lifts_a_grave_stain():
    k = _knight()
    R.record_sin(k, "vice_brothel")
    assert R.confess_to_god(k)["ok"] is False
    for _ in range(8):
        R.day_tick(k, rule_kept=True)
    assert R.open_grave_weight(k) == 6
    assert k["virtue"] == 75 - 6
    assert R.caps_breath_at_dim(k) is True
    assert knight.breath_state_for(k) == "dim"


def test_brother_aimery_ends_worse_on_every_count():
    ex = R.data()["worked_examples"]["aimery"]
    k = _knight(**ex["start"], name="Brother Aimery")
    # start uses 'corruption' in the example; the engine uses corruption_level
    if "corruption" in k and "corruption_level" not in k:
        k["corruption_level"] = k.pop("corruption")
    k["corruption_level"] = ex["start"]["corruption"]
    k["virtue"] = ex["start"]["virtue"]
    k["piety"] = ex["start"]["piety"]
    assert knight.breath_state_for(k) == "full"

    for key in ex["day_1_sins"]:
        R.record_sin(k, key)
    # Private prayer that night does nothing for grave stains.
    assert R.confess_to_god(k)["ok"] is False
    d1 = R.day_tick(k, rule_kept=False)
    assert k["virtue"] == ex["after_day_1"]["virtue"] == 44
    assert k["corruption_level"] == ex["after_day_1"]["corruption"] == 17
    assert d1["rule_ward"] == 0
    assert knight.breath_state_for(k) == "dim"
    assert R.virtue_ceiling(k) == 44
    assert R.felt_line(k) == "You say the words. Nothing answers."

    for _ in range(7):
        R.confess_to_god(k)
        R.day_tick(k, rule_kept=True)

    assert k["piety"] == ex["after_day_8"]["piety"] == 80
    assert k["virtue"] == ex["after_day_8"]["virtue"] == 44
    assert k["corruption_level"] == ex["after_day_8"]["corruption"] == 20
    assert knight.breath_state_for(k) == "dim"
    assert R.open_grave_weight(k) == 31
    assert R.state(k)["rule_ward"] == 5
    # Worse than the start on Virtue, Corruption and Breath; Piety at the Rule cap
    # is the false comfort of praying 'to God' alone. He still needs a priest.
    assert k["virtue"] < ex["start"]["virtue"]
    assert k["corruption_level"] > ex["start"]["corruption"]
    assert knight.breath_state_for(k) != "full"
    assert R.state(k)["loss_of_house_required"] is True

    # Confession and fasting cannot pray the murder away (C5).
    assert R.apply_virtue_gain(k, "confession") == 0
    assert R.apply_virtue_gain(k, "fasting_day") == 0
    assert k["virtue"] == 44

    # Recovery: priest, restitution, penance, and loss of the house.
    assert R.confess_to_priest(k)["ok"] is True
    assert R.felt_line(k) in (
        "The weight has a name now. It is not gone.",
        "The house is closed to you.",
        "Something that stood at your back has stepped away.",
    )
    assert R.make_restitution(k)["ok"] is True
    R.complete_penance(k)
    # Murder of a Christian still blocks until he gives up the house.
    assert any(s["key"] == "murder_christian" and s["open"] for s in R.state(k)["stains"])
    out = R.loss_of_the_house(k, "penitent_brother")
    assert out["house_status"] == "penitent_brother"
    R.complete_penance(k)
    assert R.open_grave_weight(k) == 0
    assert R.virtue_ceiling(k) == 75
    assert R.felt_line(k) == "You sleep without dreams for the first time in weeks."


def test_open_grave_or_broken_vow_caps_breath_at_dim():
    # Virtue and Piety would otherwise be full; a single grave stain still caps at dim.
    k = _knight(virtue=75, piety=80, corruption_level=0)
    R.record_sin(k, "vice_brothel")  # weight 6, ceiling 69, virtue 69
    k["virtue"] = 69
    k["piety"] = 80
    assert R.virtue_ceiling(k) == 69
    assert knight.breath_state(69, 80, 0) == "dim"  # ceiling already blocks full
    # Even if someone bypassed the ceiling, the cap still holds:
    assert knight.breath_state(75, 80, 0, cap_at_dim=True) == "dim"
    assert knight.breath_state_for(k) == "dim"
    # A broken vow with no remaining grave weight cannot happen while the stain is open;
    # a resolved-weight vow flag is tested via caps_breath_at_dim.
    assert R.caps_breath_at_dim(k) is True


def test_breath_targets_match_witch_hunters():
    import witch_hunters as WH
    vs = set(R.data()["breath"]["valid_kinds"])
    assert vs == set(WH.VALID_BREATH_KINDS)
    vows = json.load(open(os.path.join(ROOT, "rules/orders/crusader_vows.json"), encoding="utf-8-sig"))
    assert vs == set(vows["breath"]["full"]["vs"])
    full = knight.breath_effects(80, 80, 0, ["ghost"])
    assert full["state"] == "full" and full.get("bypass_undying") is True
    possessed = knight.breath_effects(80, 80, 0, ["possessed_human"])
    assert possessed.get("bypass_undying") is True
    # legacy alias used by the combat engine
    aliased = knight.breath_effects(80, 80, 0, ["corrupted"])
    assert aliased.get("bypass_undying") is True
    human = knight.breath_effects(80, 80, 0, ["human"])
    assert "bypass_undying" not in human


def test_confession_and_fasting_are_capped(monkeypatch=None):
    k = _knight(virtue=50, piety=50)
    first = R.apply_virtue_gain(k, "confession")
    assert first == 8 and k["virtue"] == 58
    # Same week: cooldown and weekly devotion cap of 8 block a second confession and a fast.
    assert R.apply_virtue_gain(k, "confession") == 0
    assert R.apply_virtue_gain(k, "fasting_day") == 0
    assert k["virtue"] == 58
    # Repeat non-devotion gains halve.
    k2 = _knight(virtue=50)
    assert R.apply_virtue_gain(k2, "defend_innocent") == 8
    assert R.apply_virtue_gain(k2, "defend_innocent") == 4
    assert k2["virtue"] == 62


def test_rule_ward_reduces_incoming_veil_corruption():
    k = _knight()
    for _ in range(5):
        R.day_tick(k, rule_kept=True)
    assert R.state(k)["rule_ward"] == 5
    taken = R.apply_incoming_veil_corruption(k, 7)
    assert taken == 2 and k["corruption_level"] == 2
    assert R.felt_line(k) == "The lamp burns steady; the dark keeps its distance."


def test_c1_c2_c4_c7_c8_c9_conflicts_are_closed():
    magic = json.load(open(os.path.join(ROOT, "rules/magic_rules.json"), encoding="utf-8-sig"))
    methods = magic["corruption"]["purge_methods"]
    assert "breath_ritual" not in methods
    assert "saint_relic" in methods and methods["saint_relic"]["reduce_corruption"] == 25
    stages = [s["threshold"] for s in magic["corruption"]["stages"]]
    assert 90 in stages and 100 in stages

    vows = json.load(open(os.path.join(ROOT, "rules/orders/crusader_vows.json"), encoding="utf-8-sig"))
    purity = vows["vows"]["purity"]["rule"].lower()
    assert "purged at once" not in purity
    assert "penance" in purity or "confess" in purity
    none = json.dumps(vows["breath"]["none"]).lower()
    assert "discern_sin" not in none
    assert "discern sin" not in json.dumps(vows).lower()

    breath = json.load(open(os.path.join(ROOT, "rules/breath_config.json"), encoding="utf-8-sig"))
    for key in ("smite_base", "smite_scale_wil_div", "smite_scale_virtue_div", "smite_demon_undead_multiplier"):
        assert key not in breath.get("breath", breath)

    ck = json.dumps(json.load(open(os.path.join(ROOT, "rules/classes/crusader_knight.json"), encoding="utf-8-sig")))
    assert "miracle_breath_burst" not in ck

    # The rare relic cure still works; the removed ritual must not.
    k = _knight(corruption_level=40)
    assert R.saint_relic_purge(k) == 25
    assert k["corruption_level"] == 15


def test_hidden_keys_are_registered_and_stripped():
    keys = [
        "rule_ward", "stain_ledger", "virtue_ceiling", "venial_stain",
        "grave_stain", "rule_kept", "stain_weight", "rule_of_life",
        "open_grave_weight",
    ]
    for k in keys:
        assert B.HIDDEN_KEY.match(k), k
    # Generic armour words must not be swallowed.
    assert not B.HIDDEN_KEY.match("protection")
    assert not B.HIDDEN_KEY.match("ward")
    # A fake pack node is stripped of the new keys.
    stripped = B.strip_hidden({
        "name": "Knight",
        "rule_ward": 5,
        "stain_ledger": [{"weight": 6}],
        "virtue": 75,
        "armor": 10,
    })
    assert stripped == {"name": "Knight", "armor": 10}


def test_a_civilian_is_untouched():
    c = {"name": "Elara", "class_name": "Veil_Sorceress", "virtue": 0, "piety": 0, "corruption_level": 8}
    assert R.day_tick(c) == {}
    assert c["corruption_level"] == 8
