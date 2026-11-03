import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import creation  # noqa: E402
import limb_repair as L  # noqa: E402
import progression as P  # noqa: E402
import skills as SK  # noqa: E402


class C:
    def __init__(self, race="Human", gender="Male", **kw):
        self.name, self.race, self.gender = "T", race, gender
        self.intelligence = self.dexterity = self.agility = self.perception = 40
        self.strength = self.charisma = self.willpower = self.toughness = self.endurance = 40
        self.skills, self.talents, self.advantages, self.xp, self.gold, self.reputation = {}, [], {}, 0, 0, 0
        self.__dict__.update(kw)
        P.state(self)["skills"] = {}


def test_data_shape():
    d = json.load(open(os.path.join(SK.ROOT, "rules", "skills.json"), encoding="utf-8"))
    assert len(d["skills"]) == 30 and "prayer" not in d["skills"]
    for s in d["skills"].values():
        assert {"name", "stats", "trained_only", "restrictions", "description"} <= set(s)
    for lst in list(d["class_free_skills"].values()) + list(d["background_free_skills"].values()):
        if isinstance(lst, list):
            assert all(x in d["skills"] for x in lst)


def test_creation_picks_and_locks():
    r = creation.create_character("Human", "Male", class_name="Crusader_Knight",
                                  skills=["athletics", "awareness", "medicine", "persuasion", "endurance", "stealth", "riding"])
    assert r["errors"] == []  # riding is free for the knight, so 6 paid picks
    assert r["skills"]["riding"] == (r["stats"]["agility"] + r["stats"]["willpower"]) // 2 + 10
    assert "lore_theology" in r["skills"]
    r = creation.create_character("Human", "Male", skills=["athletics", "awareness", "medicine", "persuasion", "endurance", "stealth", "riding"])
    assert any("max 6" in e for e in r["errors"])
    r = creation.create_character("Human", "Male", skills=["spellcraft", "runecraft", "elven_bowcraft", "letters_law"])
    assert len(r["errors"]) == 4


def test_untrained_and_tools():
    c = C()
    assert SK.effective_value(c, "medicine") is None
    assert SK.basic_bandage_value(c) == 20
    assert SK.effective_value(c, "athletics") == 20
    SK.learn(c, "smithing", 80)
    assert SK.effective_value(c, "smithing", "field_kit") == 50
    assert SK.effective_value(c, "smithing", "workshop") == 80
    assert SK.effective_value(c, "smithing") == 30


def test_xp_buys_never_raises():
    c = C(xp=250)
    assert SK.buy_with_xp(c, "medicine")[0] and c.xp == 50
    assert SK.buy_with_xp(c, "medicine")[0] is False
    assert SK.buy_with_xp(c, "athletics")[0] is False  # 100 needed
    d = C(race="Dwarf", xp=500)
    assert SK.buy_with_xp(d, "elven_bowcraft")[0] is False
    assert SK.buy_with_xp(d, "elven_bowcraft", cross_race_master=True)[0]
    assert SK.buy_with_xp(C(gender="Male", xp=500), "spellcraft", True)[0] is False  # gender lock absolute


def test_growth_by_use_and_session_limit():
    c = C()
    SK.learn(c, "athletics", 30)
    for _ in range(30):
        SK.record_use(c, "athletics")
    assert SK.check_growth(c) and P.state(c)["skills"]["athletics"]["value"] == 31
    for _ in range(100):
        SK.record_use(c, "athletics", failed=True)
    assert SK.check_growth(c) == []  # 1 per session
    P.new_session(c)
    assert SK.check_growth(c)


def test_gate_at_50_and_teaching():
    c = C(gold=10000, reputation=25)
    SK.learn(c, "athletics", 50)
    SK.record_use(c, "athletics")
    assert P.state(c)["skills"]["athletics"]["uses"] == 0  # gated
    assert SK.teach(c, "athletics", 60)["ok"] is False  # master must be >= 65
    q = SK.teach(c, "athletics", 65)
    assert q["ok"] and q["gold"] == 1100 and c.gold == 8900 and q["reputation"] == 20
    SK._skills_state(c)["athletics"]["unlocked_to"] = 60
    assert SK.teaching_quote(c, "athletics", 80)["reputation"] == 40


def test_cross_race_teaching():
    d = C(race="Dwarf", gold=100000, reputation=60)
    SK.learn(d, "elven_bowcraft", 50)
    q = SK.teach(d, "elven_bowcraft", 70)
    assert q["ok"] and q["points"] == 2 and q["gold"] == 20 * 52 * 5 and q["reputation"] == 50


def test_use_bar_and_medicine():
    c = C()
    SK.learn(c, "medicine", 50)
    assert SK.rank(c, "medicine") == 0 and SK.rank_name(c, "medicine") == "Untested"
    P.state(c)["skills"]["medicine"]["bar"] = 400
    assert SK.rank(c, "medicine") == 3 and L.medicine_bonus(c) == 15
    assert SK.medicine_perks(c) == {"bandage_rounds": -1, "own_surgery_infection_mult": 0.5}
    assert L.surgery_skill(c, "field_kit") == 50 + 15
    P.state(c)["skills"]["medicine"]["bar"] = 900
    assert L.surgery_skill(c, "field_kit") == 50 + 20  # R4: field kit counts as proper tools (cap 70)
    SK.sync_legacy(c)
    assert c.skills["medicine"] == 4


def test_untrained_surgery_refused():
    class M:
        limb_state = {"left_arm": "crippled"}
    u = C()
    orig = L.states
    L.states = lambda m: m.limb_state
    try:
        r = L.surgery(u, M(), "left_arm", rng=random.Random(1))
    finally:
        L.states = orig
    assert r["ok"] is False and "trained-only" in r["result"]


def test_legacy_rank_still_works():
    class Old:
        intelligence = dexterity = 40
        skills = {"medicine": 3}
        talents = []
    assert SK.medicine_rank(Old()) == 3 and L.medicine_bonus(Old()) == 15


def test_weapon_head_start():
    assert SK.weapon_head_start({"swordsmanship": 3, "intimidation": 1}) == {"one_hand_sword": 150}
    c = C()
    SK.apply_weapon_head_start(c, {"club_smash": 4})
    assert P.mastery_rank(c, "mace") == 2


def test_order_reputation_counts_with_order_master():
    import order_paths as O
    c = C(gold=10000, reputation=0)
    SK.learn(c, "athletics", 50)
    O.join(c, "crusader_knight")
    O.add_reputation(c, 25)
    assert SK.teach(c, "athletics", 65)["ok"] is False  # ordinary master: general reputation 0
    assert SK.teach(c, "athletics", 65, master_of="tribunal")["ok"] is False  # wrong body
    assert SK.teach(c, "athletics", 65, master_of="order")["ok"]
    j = C(gold=10000, reputation=0)
    SK.learn(j, "lore_theology", 50)
    O.join(j, "holy_judge")
    O.add_reputation(j, 25)
    assert SK.teach(j, "lore_theology", 65, master_of="order")["ok"] is False
    assert SK.teach(j, "lore_theology", 65, master_of="tribunal")["ok"]
    assert SK.teaching_reputation(C(reputation=30), "order") == 30
