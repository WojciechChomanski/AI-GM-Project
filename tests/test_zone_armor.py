"""Zone armour (option B) tests. Run: python tests/test_zone_armor.py  (or pytest)"""
import os, sys, json, random, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
logging.disable(logging.CRITICAL)

from zone_hp import BASE_ZONES, scaled_zones
from character import Character
from combat_health import CombatHealthManager
from armor_system import (ArmorPiece, average_protection, zone_protection, armor_vs_aimed,
                          armor_vs_spread, round_protection, SPREAD_WEIGHTS, SPREAD_WEIGHT_TOTAL)

ARMORS = json.load(open(os.path.join(os.path.dirname(__file__), "..", "rules", "armors.json")))


def piece(key):
    s = ARMORS[key]["standard"]
    return ArmorPiece(s["name"], s["coverage"], s["armor_rating"], s["stamina_penalty"],
                      s["max_durability"], s["weight"])


def fighter(*keys):
    c = Character(); c.name = "Test"; c.toughness = 0
    c.body_parts = scaled_zones(1.0); c.max_body_parts = dict(c.body_parts)
    c.total_hp = 100
    c.armor = [piece(k) for k in keys]
    return c, CombatHealthManager(c)


def lost(h):
    return {z: h.initial_health[z] - h.health[z] for z in h.health if h.health[z] != h.initial_health[z]}


def test_weighted_average_formula():
    # weights = base HP of the 11 zones a normal hit can hit (no throat/groin), sum 94
    assert SPREAD_WEIGHT_TOTAL == 94 and set(SPREAD_WEIGHTS) == set(BASE_ZONES) - {"throat", "groin"}
    # chest only (weight 20) with slashing 2 -> 2*20/94
    assert abs(average_protection([piece("Light_Light")], "slashing") - 40 / 94) < 1e-9
    # no armour at all -> 0
    assert average_protection([], "slashing") == 0
    # full plate today: covers 10 zones (no head/throat/groin); head (7) is the only
    # hittable zone left bare -> 10 * 87/94
    assert abs(average_protection([piece("Heavy_Medium")], "slashing") - 870 / 94) < 1e-9


def test_rounding_half_up():
    assert [round_protection(x) for x in (0.4, 0.5, 5.5, 6.49, 9.26)] == [0, 1, 6, 6, 9]


def test_normal_hit_unarmoured_unchanged():
    random.seed(1)
    c, h = fighter()
    h.distribute_damage(10, "slashing")
    assert h.total_hp == 90 and h.last_armor_report is None


def test_normal_hit_full_plate_vs_none_vs_partial():
    random.seed(2)
    res = {}
    for name, keys in (("none", ()), ("partial", ("Light_Heavy",)), ("full", ("Heavy_Medium",))):
        c, h = fighter(*keys)
        h.distribute_damage(12, "slashing")
        res[name] = 100 - h.total_hp
    assert res["none"] == 12
    assert res["partial"] == 12 - 2          # chainmail avg 2.29 -> 2 absorbed
    assert res["full"] == 12 - 9             # full plate avg 9.26 -> 9 absorbed
    assert res["none"] > res["partial"] > res["full"]


def test_armour_never_makes_wearer_immune():
    random.seed(3)
    c, h = fighter("Heavy_Heavy")             # siege plate: slashing avg 10.18 -> 10
    h.distribute_damage(10, "slashing")
    assert h.total_hp == 100                  # fully absorbed at exactly the protection
    h.distribute_damage(11, "slashing")
    assert h.total_hp == 99                   # one point always gets through when damage > protection
    h.distribute_damage(30, "slashing")
    assert 100 - h.total_hp >= 1 + 20         # 30 - ~10 still hurts
    assert c.alive


def test_remainder_is_spread_like_a_normal_hit():
    random.seed(4)
    # 10 damage, 6 average protection -> 4 left, spread over the body (chest takes 1-2)
    p = ArmorPiece("TestSuit", list(BASE_ZONES), {"slashing": 6}, 0, 13 * 100, 10)
    c = Character(); c.name = "T"; c.toughness = 0
    c.body_parts = scaled_zones(1.0); c.max_body_parts = dict(c.body_parts); c.armor = [p]
    h = CombatHealthManager(c)
    h.distribute_damage(10, "slashing")
    assert h.last_armor_report["absorbed"] == 6 and h.last_armor_report["remainder"] == 4
    assert h.total_hp == 96
    taken = lost(h)
    assert sum(taken.values()) == 4 and len(taken) == 4
    assert "throat" not in taken and "groin" not in taken
    assert taken.get("chest", 0) >= 1


def test_aimed_uses_hit_zone_armour_only():
    random.seed(5)
    # Full plate chest slashing 10: 8 damage aimed at chest -> 0 through; aimed at head -> all 8
    c, h = fighter("Heavy_Medium")
    assert h.take_damage_to_zone("chest", 8, "slashing") == 0 and h.health["chest"] == 20
    c, h = fighter("Heavy_Medium")
    assert h.take_damage_to_zone("head", 5, "slashing") == 5 and h.health["head"] == 2
    # 14 aimed at the chest: 10 absorbed, 4 all into the chest
    c, h = fighter("Heavy_Medium")
    h.take_damage_to_zone("chest", 14, "slashing")
    assert h.health["chest"] == 16 and h.last_armor_report["absorbed"] == 10
    # aimed ignores average: unarmoured throat is not helped by plate elsewhere
    c, h = fighter("Heavy_Medium")
    h.take_damage_to_zone("throat", 3, "piercing")
    assert h.health["throat"] == 0 and not c.alive


def test_aimed_vs_normal_same_hit():
    random.seed(6)
    # Breastplate (slashing 9, chest/stomach/arms/upper legs). 12 damage:
    c, a = fighter("Heavy_Light"); a.take_damage_to_zone("chest", 12, "slashing")
    c, n = fighter("Heavy_Light"); n.distribute_damage(12, "slashing")
    assert 100 - a.total_hp == 3             # chest: 12 - 9
    assert round_protection(7.18) == 7 and 100 - n.total_hp == 5


def test_condition_lowers_protection():
    p = piece("Heavy_Medium")
    p.current_durability["chest"] = 5         # 5/11 = 45% -> x0.5
    assert zone_protection([p], "chest", "slashing") == 5.0
    p.current_durability["chest"] = 0         # broken
    assert zone_protection([p], "chest", "slashing") == 0.0


def test_aimed_durability_loss():
    p = piece("Heavy_Medium")                 # 11 per zone
    r = armor_vs_aimed([p], "chest", 20, "slashing")
    assert r["absorbed"] == 10 and r["remainder"] == 10
    assert p.current_durability["chest"] == 11 - 4        # max(1, 20% of 20)
    assert p.current_durability["stomach"] == 11          # other zones untouched
    r = armor_vs_aimed([p], "chest", 1, "slashing")
    assert p.current_durability["chest"] == 7 - 1         # at least 1


def test_normal_durability_only_pieces_that_helped():
    plate, cloth = piece("Heavy_Medium"), piece("Light_Light")   # cloth: chest only
    broken = piece("Light_Heavy")
    for z in broken.current_durability:
        broken.current_durability[z] = 0                          # broken piece contributes 0
    r = armor_vs_spread([plate, cloth, broken], 30, "slashing")
    assert r["absorbed"] == 10 and r["remainder"] == 20   # 9.26 + 0.43 = 9.68 -> 10
    assert sum(plate.current_durability.values()) < 110
    assert sum(cloth.current_durability.values()) < 40
    assert sum(broken.current_durability.values()) == 0 and "Light Chainmail" not in r["wear"]
    # wear is ~20% of what each piece absorbed (>= 1), spread over its zones
    assert r["wear"][plate.name] >= 1 and r["wear"][cloth.name] >= 1
    # a piece covering nothing relevant (wrong type rating 0) does not wear
    q = ArmorPiece("Nothing", ["chest"], {"blunt": 5}, 0, 20, 1)
    before = dict(q.current_durability)
    armor_vs_spread([plate, q], 10, "slashing")
    assert q.current_durability == before


def test_normal_hit_wears_armour_and_no_hit_means_no_wear():
    c, h = fighter("Heavy_Medium")
    arm = c.armor[0]
    h.distribute_damage(12, "slashing")
    assert sum(arm.current_durability.values()) == 110 - 1   # max(1, 20% of 9 = 1)
    c, h = fighter("Heavy_Medium")
    assert sum(c.armor[0].current_durability.values()) == 110


def test_character_receive_damage_uses_armour_when_type_given():
    c, _ = fighter("Heavy_Medium")
    c.receive_damage(12, "slashing")
    assert c.total_hp == 100 - 3
    c2, _ = fighter()
    c2.receive_damage(12)
    assert c2.total_hp == 88


def test_throat_and_groin_do_not_count_for_normal_hits():
    # A piece covering ALL 13 zones with rating 10 averages exactly 10 on a normal hit
    # (before: 13-zone weights, 87% -> bare throat/groin lowered it for nothing).
    everything = ArmorPiece("All13", list(BASE_ZONES), {"slashing": 10}, 0, 13 * 10, 1)
    assert abs(average_protection([everything], "slashing") - 10.0) < 1e-9
    # same piece minus throat+groin: identical normal-hit average
    eleven = ArmorPiece("Eleven", [z for z in BASE_ZONES if z not in ("throat", "groin")],
                        {"slashing": 10}, 0, 11 * 10, 1)
    assert abs(average_protection([eleven], "slashing") - 10.0) < 1e-9
    # a gorget / groin guard does nothing against a normal hit and does not wear
    gorget = ArmorPiece("Gorget", ["throat", "groin"], {"slashing": 10}, 0, 20, 1)
    assert average_protection([gorget], "slashing") == 0
    before = dict(gorget.current_durability)
    r = armor_vs_spread([everything, gorget], 30, "slashing")
    assert r["absorbed"] == 10 and gorget.current_durability == before
    assert "Gorget" not in r["wear"]
    # ...but it still protects fully against an AIMED strike on its zone
    assert armor_vs_aimed([gorget], "throat", 8, "slashing")["remainder"] == 0
    # the normal-hit wear of a 13-zone piece never lands on throat/groin
    assert everything.current_durability["throat"] == 10 and everything.current_durability["groin"] == 10
    # weighted example: chest(20)+head(7) only, rating 9 -> 9*27/94
    chest_head = ArmorPiece("CH", ["chest", "head"], {"slashing": 9}, 0, 20, 1)
    assert abs(average_protection([chest_head], "slashing") - 243 / 94) < 1e-9


def test_unarmored_is_not_broken():
    u = ARMORS["Unarmored"]["standard"]
    p = ArmorPiece(u["name"], u["coverage"], u["armor_rating"], u["stamina_penalty"],
                   u["max_durability"], u["weight"])
    assert p.coverage == [] and p.condition_status() == "None"
    assert average_protection([p], "slashing") == 0
    assert armor_vs_spread([p], 10, "slashing")["absorbed"] == 0
    # real pieces still report normally, and a destroyed one is still Broken
    full = piece("Heavy_Medium")
    assert full.condition_status() == "Pristine"
    for z in full.current_durability:
        full.current_durability[z] = 0
    assert full.condition_status() == "Broken"
    # legacy armors.Armor with empty coverage must not divide by zero
    from armors import Armor
    a = Armor("Empty", [], {"slashing": 0}, 0, 0, 0, 0)
    assert a.current_durability == {} and a.absorb_damage(5, "slashing", "chest") == 5


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f(); print("PASS", f.__name__)
    print(f"{len(fns)} tests passed")
