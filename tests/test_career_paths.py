import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import careers  # noqa: E402
import creation  # noqa: E402
import order_paths as O  # noqa: E402
import progression as P  # noqa: E402
from character_loader import find_class, class_stat_bonuses  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class C:
    def __init__(self, cls, **kw):
        self.name, self.class_name, self.race, self.gender = "T", cls, "Human", "Male"
        self.virtue = self.piety = 75
        self.corruption_level = 0
        self.abilities, self.skills = [], {}
        for s in ("strength", "agility", "dexterity", "intelligence", "perception", "charisma", "willpower", "toughness", "endurance"):
            setattr(self, s, 40)
        self.__dict__.update(kw)
        P.state(self)["skills"] = {}
        O.start_at_creation(self, cls)


def _sessions(c, n):
    for _ in range(n):
        O.record_session(c)


def test_every_class_listed_with_evolutions():
    names = set()
    for fn in os.listdir(os.path.join(ROOT, "rules", "classes")):
        if fn.endswith(".json") and fn != "template.json":
            d = json.load(open(os.path.join(ROOT, "rules", "classes", fn), encoding="utf-8-sig"))
            names |= {k for k, v in d.items() if k not in ("meta", "integration") and isinstance(v, dict)}
    assert names == set(careers.DATA["classes"])
    for cls, v in careers.DATA["classes"].items():
        if cls == "Cleric":
            assert v["on_hold"] and v["evolutions"] == []
        elif cls != "Holy_Judge":
            assert 1 <= len(v["evolutions"]) <= 3, cls


def test_worldly_knight_class():
    k = find_class("Knight")
    assert k["power_source"] == "none" and k["breath"] is False and "Noble" in k["background_required"]
    ck = class_stat_bonuses(find_class("Crusader_Knight"))
    kb = class_stat_bonuses(k)
    assert sum(kb.values()) <= sum(ck.values()) and set(k["proficiencies"]["weapons"]) >= set(find_class("Crusader_Knight")["proficiencies"]["weapons"])


def test_plausibility_gate():
    merc = C("Outlaw_Mercenary_Warrior")
    assert O.state(merc)["raised_by_order"] is False
    assert O.convert(merc, "holy_judge")["ok"] is False
    assert O.convert(merc, "crusader_knight")["ok"] is False
    assert "not an evolution" in careers.evolve_errors(merc, "holy_judge")[0]
    assert careers.become_contractor(merc) and O.state(merc)["path"] == "order_contractor"
    assert careers.become_contractor(C("Crusader_Knight")) is False


def test_one_rank_per_arc_and_hidden_check():
    k = C("Crusader_Knight")
    O.join(k, "crusader_knight")
    _sessions(k, 6)
    O.record_deed(k, "named_enemy_slain", 2)
    O.add_reputation(k, 60)
    k.virtue = 40
    r = O.promote(k, "arc1")
    assert r["ok"] is False and r["why"] == ["hidden"] and "virtue" not in r["felt"].lower()
    k.virtue = 75
    assert O.promote(k, "arc1")["ok"]
    _sessions(k, 10)
    assert O.promote(k, "arc1")["why"] == ["already promoted this arc"]
    assert O.promote(k, "arc2", task_done=False)["why"] == ["order task"]
    assert O.promote(k, "arc2")["rank"] == "Preceptor"


def test_starting_judge_is_former_squire_sergeant():
    r = creation.create_character("Human", "Male", class_name="Holy_Judge")
    assert r["career"] == {"raised_by_order": True, "start_path": "holy_judge"}
    j = C("Holy_Judge")
    st = O.state(j)
    assert st["path"] == "holy_judge" and st["rank"] == 1 and st["class_tier"] == 2
    assert j.virtue == 60 and j.piety == 60
    assert "Lance_Thrust" not in O.PATHS["holy_judge"]["start"]["abilities"]


def test_convert_knight_to_judge_and_switch_back_once():
    k = C("Crusader_Knight")
    O.join(k, "crusader_knight")
    assert O.convert(k, "holy_judge")["ok"] is False  # tier 1, no deeds
    O.state(k)["class_tier"] = 3
    O.record_deed(k, "just_discern_sin", 3)
    r = careers.evolve(k, "holy_judge")
    assert r["ok"] and k.class_name == "Holy_Judge" and O.state(k)["path"] == "holy_judge"
    O.add_reputation(k, 30)
    assert O.switch_back(k) == {"ok": True, "path": "crusader_knight", "task": "penance"}
    assert O.state(k)["rank"] == 1 and O.state(k)["reputation"] == 10
    assert O.switch_back(k)["ok"] is False


def test_bond_is_authority_only():
    j = C("Holy_Judge")
    e = O.bond_effects(j, True)
    assert e["writ"] and e["social_bonus"] == 10 and e["damage_bonus"] == 0
    assert O.bond_effects(j, False)["writ"] is False
    assert O.verdict_lawful(j, "axe1", "axe1") == (True, None)
    assert O.verdict_lawful(j, "sword", "axe1") == (False, "needless_killing")
    O.lose_bond(j)
    assert O.bond_effects(j, True)["writ"] is False
    O.reconsecrate(j)
    assert O.bond_effects(j, True)["writ"]


def test_high_judge_one_witness_and_unjust_verdict():
    j = C("Holy_Judge")
    assert O.name_witness(j, "npc1") is False
    O.state(j)["rank"] = 3
    assert O.name_witness(j, "npc1") and O.name_witness(j, "npc2") is False
    assert O.record_verdict(j, False) == "Doubt gnaws at you." and j.piety == 40
    O.state(j)["rank"] = 4
    assert O.record_verdict(j, False)["result"].startswith("expelled")


def test_penitent_fallback():
    k = C("Crusader_Knight")
    O.join(k, "crusader_knight")
    assert O.fall(k, 2)["path"] == "penitent_brother"
    assert O.convert(k, "penitent_brother")["ok"] is False
    O.state(k)["rank"] = 2
    assert O.redeem(k) and O.state(k)["path"] == "crusader_knight" and O.state(k)["switch_backs"] == 0
    assert O.fall(k, 4)["path"] is None and O.state(k)["raised_by_order"] is False


def test_evolution_adds_skills_not_stats():
    w = C("Warrior")
    before = w.strength
    assert careers.evolve(w, "duelist")["ok"] is False
    _sessions(w, 6)
    O.record_deed(w, "duel_won", 3)
    r = careers.evolve(w, "duelist")
    assert r["ok"] and r["placeholder"] and "acrobatics" in P.state(w)["skills"] and w.strength == before
    w2 = C("Warrior")
    O.record_deed(w2, "knighted")
    assert careers.evolve(w2, "knighted")["ok"] and w2.class_name == "Knight"
