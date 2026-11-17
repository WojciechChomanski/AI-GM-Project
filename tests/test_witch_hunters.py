import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import witch_hunters as WH  # noqa: E402
from healing_system import HealingSystem  # noqa: E402


class Rng:
    def __init__(self, *rolls):
        self.rolls = list(rolls)

    def randint(self, a, b):
        if self.rolls:
            return self.rolls.pop(0)
        return a


def _sorceress(**kw):
    c = {
        "name": "Elara",
        "perception": 40,
        "willpower": 45,
        "corruption_level": 0,
        "health": 20,
        "stress_level": 0,
        "alive": True,
        "skills": {"deception": 40},
    }
    c.update(kw)
    return c


def _hunter(rank="sworn_hunter", zeal=40, greed=30, **kw):
    h = {"name": "Rhys", "perception": 50, "willpower": 50, "abilities": {}}
    h.update(kw)
    WH.state(h)["rank"] = rank
    WH.set_nature(h, zeal, greed)
    return h


def test_order_is_mercy_of_ash_and_uses_no_magic():
    o = WH.data()["order"]
    assert o["name"] == "The Mercy of Ash"
    assert o["kind"] == "independent_church_order"
    assert o["answers_to"] == "Witchfinder General"
    assert o["uses_magic"] is False and o["uses_witch_sight"] is False
    ids = [r["id"] for r in WH.data()["ranks"]]
    assert ids == [
        "informer", "tracker", "sworn_hunter",
        "hunt_sergeant", "witchfinder_captain", "witchfinder_general",
    ]
    assert WH.ranks()["sworn_hunter"]["authority"] == 1
    assert WH.ranks()["witchfinder_captain"]["authority"] == 2
    assert WH.ranks()["witchfinder_general"]["authority"] == 3
    assert WH.ranks()["informer"]["authority"] == 0


def test_suspicion_is_per_region_and_thresholds_are_prompts():
    c = _sorceress()
    assert WH.suspicion(c, "ashen_coast") == 0
    WH.adjust_suspicion(c, "ashen_coast", 20)
    row = WH.suspicion_threshold(c, "ashen_coast")
    assert row["id"] == "watched" and "informer" in row["prompt"].lower()
    WH.adjust_suspicion(c, "vale", 80)
    assert WH.suspicion(c, "ashen_coast") == 20  # other region unchanged
    assert WH.suspicion_threshold(c, "vale")["id"] == "taken"
    # fleeing helps: a new region starts at 10 only because a bounty already exists
    assert WH.enter_region(c, "freeport", from_region="vale") == 10
    assert WH.enter_region(_sorceress(), "freeport") == 0


def test_named_modifiers_include_framing():
    c = _sorceress()
    WH.apply_event(c, "vale", "open_magic_witnessed")
    assert WH.suspicion(c, "vale") == 25
    WH.apply_event(c, "vale", "framing_another_woman")
    assert WH.suspicion(c, "vale") == 0  # 25 - 25


def test_protection_blocks_low_authority_and_costs_favour():
    c = _sorceress()
    WH.set_protection(c, 3, patron="King Aldric")
    hunter = _hunter("sworn_hunter")
    assert WH.authority_of(hunter) == 1
    assert WH.can_act_freely(hunter, c) is False
    cap = _hunter("witchfinder_captain")
    assert WH.can_act_freely(cap, c) is False
    gen = _hunter("witchfinder_general")
    assert WH.can_act_freely(gen, c) is True
    cost = WH.political_cost(hunter, c)
    assert cost["applied"] is True and cost["church_favour_delta"] == -30
    assert hunter["witch_hunters"]["church_favour"] == 20
    assert cost["scapegoat"] is True and "King Aldric" in hunter["witch_hunters"]["enemies"]
    # Sealed writ lets them act and waives the Church-favour hit
    other = _hunter("sworn_hunter")
    assert WH.can_act_freely(other, c, writ="sealed_writ") is True
    waived = WH.political_cost(other, c, writ="sealed_writ")
    assert waived["applied"] is True and waived["church_favour_delta"] == 0
    assert other["witch_hunters"]["church_favour"] == 50


def test_tolerance_tithe_caps_and_unpaid_jumps_to_hunted():
    c = _sorceress()
    WH.set_suspicion(c, "freeport", 70)
    WH.start_tithe(c, "freeport", 30)
    assert WH.suspicion(c, "freeport") == 39
    WH.adjust_suspicion(c, "freeport", 50)
    assert WH.suspicion(c, "freeport") == 39  # still capped while paid
    WH.miss_tithe(c)
    assert WH.suspicion(c, "freeport") == 60
    # grace period on day_tick
    d = _sorceress()
    WH.start_tithe(d, "vale", 20)
    d["witch_hunters"]["tithe"]["paid"] = False
    for _ in range(29):
        assert "tithe_lapsed" not in WH.day_tick(d)
    assert WH.day_tick(d)["tithe_lapsed"] is True
    assert WH.suspicion(d, "vale") == 60


def test_bribe_formula_corrupt_and_fanatic():
    c = _sorceress()
    honest = _hunter(zeal=50, greed=20)
    assert WH.consider_bribe(honest, offer_gold=10, region="vale", target=c)["accepted"] is False
    assert WH.suspicion(c, "vale") == 15  # reported
    corrupt = _hunter(zeal=50, greed=70)
    assert WH.is_corrupt(corrupt) and not WH.is_fanatic(corrupt)
    # effective zeal 30; bonus 10 for 50 gold -> 70+10 >= 30
    assert WH.consider_bribe(corrupt, 50, region="vale", target=_sorceress())["accepted"] is True
    fanatic = _hunter(zeal=90, greed=80)
    assert WH.is_fanatic(fanatic)
    marked = _sorceress()
    r = WH.consider_bribe(fanatic, 1000, region="vale", target=marked)
    assert r["accepted"] is False and r["reason"] == "fanatic" and r["reported"] is True
    assert WH.suspicion(marked, "vale") == 15


def test_inspect_finds_marks_only_by_mundane_means():
    hunter = _hunter()
    hidden = _sorceress(corruption_level=25)
    assert WH.inspect_marks(hunter, hidden, stripping=True)["found"] == []
    subtle = _sorceress(corruption_level=50)
    assert WH.inspect_marks(hunter, subtle, glance=True)["found"] == []
    assert WH.inspect_marks(hunter, subtle, stripping=True)["found"][0]["band"] == 50
    branded = _sorceress(sigils=[{"tier": "Branded", "school": "fire"}])
    row = WH.inspect_marks(hunter, branded)["found"][0]
    assert row["how"] == "automatic" and row["school"] == "fire"
    # Sigil I is automatic on pricking, not at a bad glance
    sigil = _sorceress(sigils=[{"tier": "I", "school": "frost"}])
    miss = WH.inspect_marks(hunter, sigil, glance=True, rng=Rng(1))
    assert miss["found"] == []
    prick = WH.inspect_marks(hunter, sigil, glance=False, pricking=True)
    assert prick["found"][0]["tier"] == "I" and prick["magic_used"] is False


def test_mundane_tests_never_prove_magic():
    hunter, innocent = _hunter(), _sorceress()
    r = WH.mundane_test("pricking", hunter, innocent, rng=Rng(1))
    assert r["suggestive"] is True and r["proves_magic"] is False and r["prompt_only"] is True


def test_interrogate_has_no_cost_and_reads_guilt_not_magic():
    judge = _hunter()
    judge["abilities"] = {"Divine_Clarity": True}
    target = _sorceress()
    # questioner 50+50+90+10 = 200; defender max(45,40)+10 = 55; success
    r = WH.interrogate(judge, target, rng=Rng(90, 10))
    assert r["success"] is True and r["reads"] == "guilt" and r["proves_magic"] is False
    assert r["costs"] == {"stamina": 0, "piety": 0} and r["divine_clarity"] is True
    # a tie goes to the defender: 50+50+10+10 = 120 vs 45+75 = 120
    t = WH.interrogate(judge, target, rng=Rng(10, 75))
    assert t["success"] is False and t["tie_goes_to"] == "defender"


def test_final_verdict_is_not_an_instant_kill():
    judge, target = _hunter("witchfinder_captain"), _sorceress(health=20)
    r = WH.final_verdict(judge, target, "execution", evidence="confirmed")
    assert r["instant_kill"] is False and r["stamina"] == 0 and target["health"] == 20
    assert r["legal"] is True
    carried = WH.apply_sentence(target, "execution")
    assert carried["instant_kill_power"] is False and target["health"] == 0 and target["alive"] is False


def test_torture_and_default_lean():
    hunter, target = _hunter(zeal=40, greed=70), _sorceress(health=20, protection=0)
    # corrupt hunter leans toward a fine
    assert WH.default_lean(hunter, target, evidence="confirmed") == "fine_ransom"
    fanatic = _hunter(zeal=90, greed=10)
    assert WH.default_lean(fanatic, target, evidence="confirmed") == "execution"
    assert WH.default_lean(fanatic, target, writ="sealed_writ", evidence="weak") == "execution"
    t = WH.apply_sentence(target, "torture", rng=Rng(7))
    assert t["hp_lost"] == 7 and target["health"] == 13
    assert target["stress_level"] == 5 and target["witch_hunters"]["willpower_penalty"] == -10


def test_breath_never_fires_on_ordinary_sinners_or_sorceresses():
    assert WH.breath_may_trigger({"kind": "possessed_human"}) is True
    assert WH.breath_may_trigger({"kind": "demon"}) is True
    assert WH.breath_may_trigger({"kind": "corrupted_beast"}) is True
    assert WH.breath_may_trigger({"kind": "ghost"}) is True
    assert WH.breath_may_trigger({"is_possessed": True}) is True
    assert WH.breath_may_trigger({"kind": "ordinary_sinner"}) is False
    assert WH.breath_may_trigger({"kind": "sorceress"}) is False
    assert WH.breath_may_trigger({"kind": "human"}) is False
    assert WH.judgment_may_trigger({"kind": "confirmed_major_sinner"}) is False
    assert WH.judgment_may_trigger(None) is False


def test_breath_purge_only_after_just_verdict_on_a_valid_target():
    hs, ally = HealingSystem(), NS(name="Ally", status_effects=[{"name": "salt_kiss"}, {"name": "bleeding"}])
    judge = NS(name="J", class_name="Holy_Judge", virtue=80, piety=90, corruption_level=0, stamina=0)
    # no condemned target, or an ordinary sinner: nothing happens
    assert hs.breath_purge(judge, [ally], against={"kind": "ordinary_sinner"}) == []
    assert hs.breath_purge(judge, [ally]) == []
    assert ally.status_effects[0]["name"] == "salt_kiss"
    # possessed human, just verdict: still passive, no stamina
    assert hs.breath_purge(judge, [ally], against={"kind": "possessed_human"}) == ["Ally"]
    assert ally.status_effects == [{"name": "bleeding"}] and judge.stamina == 0
    # manual trigger still refused
    ally2 = NS(name="A2", status_effects=[{"name": "salt_kiss"}])
    assert hs.breath_purge(judge, [ally2], trigger="manual", against={"kind": "demon"}) == []
