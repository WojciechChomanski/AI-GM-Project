"""Zone armour (option B) tests. Run: python tests/test_zone_armor.py  (or pytest)"""
import os, sys, json, random, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
logging.disable(logging.CRITICAL)

from zone_hp import BASE_ZONES, scaled_zones
from character import Character
from combat_health import CombatHealthManager
from armor_system import (ArmorPiece, average_protection, zone_protection, armor_vs_aimed,
                          armor_vs_spread, round_protection, SPREAD_WEIGHTS, SPREAD_WEIGHT_TOTAL,
                          best_piece_for_zone)

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
    # full plate covers all 13 zones at the same rating -> normal-hit average is exactly the rating
    assert abs(average_protection([piece("Heavy_Medium")], "slashing") - 10.0) < 1e-9
    # a 10-zone set without head (7 of 94) would average 10 * 87/94
    ten = ArmorPiece("Ten", [z for z in BASE_ZONES if z not in ("head", "throat", "groin")],
                     {"slashing": 10}, 0, 110, 28)
    assert abs(average_protection([ten], "slashing") - 870 / 94) < 1e-9


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
    assert res["full"] == 12 - 10            # full plate avg 10.0 -> 10 absorbed
    assert res["none"] > res["partial"] > res["full"]


def test_armour_never_makes_wearer_immune():
    random.seed(3)
    c, h = fighter("Heavy_Heavy")             # siege plate: slashing 11 on every zone -> avg 11
    h.distribute_damage(11, "slashing")
    assert h.total_hp == 100                  # fully absorbed at exactly the protection
    h.distribute_damage(12, "slashing")
    assert h.total_hp == 99                   # one point always gets through when damage > protection
    h.distribute_damage(30, "slashing")
    assert 100 - h.total_hp >= 1 + 19         # 30 - 11 still hurts
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
    # Full plate chest slashing 10: 8 damage aimed at chest -> 0 through; plate now covers the head too
    c, h = fighter("Heavy_Medium")
    assert h.take_damage_to_zone("chest", 8, "slashing") == 0 and h.health["chest"] == 20
    c, h = fighter("Heavy_Medium")
    assert h.take_damage_to_zone("head", 5, "slashing") == 0 and h.health["head"] == 7
    # a Breastplate does not cover the head -> all 5 goes in
    c, h = fighter("Medium_Heavy")
    assert h.take_damage_to_zone("head", 5, "slashing") == 5 and h.health["head"] == 2
    # 14 aimed at the chest: 10 absorbed, 4 all into the chest
    c, h = fighter("Heavy_Medium")
    h.take_damage_to_zone("chest", 14, "slashing")
    assert h.health["chest"] == 16 and h.last_armor_report["absorbed"] == 10
    # aimed ignores average: unarmoured throat is not helped by armour elsewhere
    c, h = fighter("Medium_Heavy")
    h.take_damage_to_zone("throat", 3, "piercing")
    assert h.health["throat"] == 0 and not c.alive


def test_aimed_vs_normal_same_hit():
    random.seed(6)
    # Breastplate (slashing 8, chest/stomach/upper arms only). 12 damage:
    c, a = fighter("Medium_Heavy"); a.take_damage_to_zone("chest", 12, "slashing")
    c, n = fighter("Medium_Heavy"); n.distribute_damage(12, "slashing")
    assert 100 - a.total_hp == 4             # chest: 12 - 8
    assert round_protection(3.66) == 4 and 100 - n.total_hp == 8   # 12 - 4 spread over the body


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
    plate, cloth = piece("Heavy_Medium"), piece("Light_Light")   # cloth: chest only (rating 2 < plate 10)
    broken = piece("Light_Heavy")
    for z in broken.current_durability:
        broken.current_durability[z] = 0                          # broken piece contributes 0
    r = armor_vs_spread([plate, cloth, broken], 30, "slashing")
    assert r["absorbed"] == 10 and r["remainder"] == 20   # NO stacking: plate 10.0 only (cloth does not add)
    assert sum(plate.current_durability.values()) < 143
    assert sum(cloth.current_durability.values()) == 40   # cloth never counted -> no wear
    assert sum(broken.current_durability.values()) == 0 and "Light Chainmail" not in r["wear"]
    assert plate.name in r["wear"] and cloth.name not in r["wear"] and r["wear"][plate.name] >= 1
    # a piece covering nothing relevant (wrong type rating 0) does not wear
    q = ArmorPiece("Nothing", ["chest"], {"blunt": 5}, 0, 20, 1)
    before = dict(q.current_durability)
    armor_vs_spread([plate, q], 10, "slashing")
    assert q.current_durability == before


def test_normal_hit_wears_armour_and_no_hit_means_no_wear():
    c, h = fighter("Heavy_Medium")
    arm = c.armor[0]
    h.distribute_damage(12, "slashing")
    assert sum(arm.current_durability.values()) == 143 - 2   # absorbed 10 -> max(1, 20% of 10 = 2)
    c, h = fighter("Heavy_Medium")
    assert sum(c.armor[0].current_durability.values()) == 143


def test_character_receive_damage_uses_armour_when_type_given():
    c, _ = fighter("Heavy_Medium")
    c.receive_damage(12, "slashing")
    assert c.total_hp == 100 - 2
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


def test_no_stacking_best_piece_per_zone():
    plate, cloth = piece("Heavy_Medium"), piece("Light_Light")
    # plate (10) over cloth (2) on the chest: only the best counts, NOT 12
    assert zone_protection([plate, cloth], "chest", "slashing") == 10
    assert zone_protection([cloth, plate], "chest", "slashing") == 10
    # gauntlets over a breastplate do not add on the lower arm: best of 8 and 10
    bp = piece("Medium_Heavy")
    gaunt = ArmorPiece("Plate Gauntlets", ["left_lower_arm", "right_lower_arm"], {"slashing": 10}, 0, 44, 1.9)
    assert zone_protection([bp, gaunt], "left_lower_arm", "slashing") == 10
    # a broken best piece lets the next best count
    for z in plate.current_durability:
        plate.current_durability[z] = 0
    assert zone_protection([plate, cloth], "chest", "slashing") == 2
    # condition is part of "best": a worn plate (x0.5) loses to an intact better-rated-after-condition piece
    plate2 = piece("Heavy_Medium"); plate2.current_durability["chest"] = 5      # 5/11 -> x0.5 -> 5
    mail = piece("Light_Heavy")                                                   # chest 5
    assert best_piece_for_zone([plate2, mail], "chest", "slashing")[1] == 5.0
    assert zone_protection([plate2, mail], "chest", "slashing") == 5.0            # not 10


def test_no_stacking_wear_only_to_counted_piece():
    plate, cloth = piece("Heavy_Medium"), piece("Light_Light")
    r = armor_vs_aimed([plate, cloth], "chest", 20, "slashing")
    assert r["protection"] == 10 and r["absorbed"] == 10 and r["remainder"] == 10
    assert plate.current_durability["chest"] == 11 - 4 and cloth.current_durability["chest"] == 40
    assert list(r["wear"]) == [plate.name]
    # spread: cloth (chest only, weaker) never counted -> untouched; plate wears
    plate, cloth = piece("Heavy_Medium"), piece("Light_Light")
    r = armor_vs_spread([plate, cloth], 30, "slashing")
    assert r["absorbed"] == 10 and cloth.name not in r["wear"] and cloth.current_durability["chest"] == 40
    # when the weak piece is the counted one on some zones, it wears only there
    gorget = ArmorPiece("Gorget", ["chest", "head"], {"slashing": 4}, 0, 20, 1)
    big = ArmorPiece("ChestOnly", ["chest"], {"slashing": 9}, 0, 20, 1)
    r = armor_vs_spread([gorget, big], 30, "slashing")
    assert big.current_durability["chest"] < 20 and gorget.current_durability["chest"] == 10
    assert gorget.current_durability["head"] <= 10


def test_full_and_siege_plate_cover_all_13_zones_equally():
    for tier in ("Heavy_Medium", "Heavy_Heavy"):
        for var, a in ARMORS[tier].items():
            assert sorted(a["coverage"]) == sorted(BASE_ZONES), (tier, var)
            p = ArmorPiece(a["name"], a["coverage"], a["armor_rating"], a["stamina_penalty"],
                           a["max_durability"], a["weight"])
            for t in ("slashing", "piercing", "blunt"):
                vals = {zone_protection([p], z, t) for z in BASE_ZONES}
                assert vals == {a["armor_rating"][t]}, (a["name"], t)   # same rating on every zone
                assert abs(average_protection([p], t) - a["armor_rating"][t]) < 1e-9
            assert len(set(p.per_zone_max.values())) == 1           # durability split evenly over 13 zones
    # Siege Plate: slightly higher absorption, durability and weight than Full Plate
    for var in ("standard", "dwarven"):
        full, siege = ARMORS["Heavy_Medium"][var], ARMORS["Heavy_Heavy"][var]
        assert all(siege["armor_rating"][t] > full["armor_rating"][t] for t in full["armor_rating"])
        assert siege["max_durability"] >= full["max_durability"] and siege["weight"] > full["weight"]
    # floats survive (no int() cast): Full Plate weighs 32.2
    fp = piece("Heavy_Medium")
    assert fp.weight == 32.2 and fp.stamina_penalty == 10
    assert ArmorPiece("Light", ["head"], {"slashing": 1}, 0.4, 16, 0.7).stamina_penalty == 0.4
    assert ArmorPiece("Light", ["head"], {"slashing": 1}, 0.4, 16, 0.7).weight == 0.7


def test_lower_sets_get_no_head_throat_groin():
    for tier in ("Light_Light", "Light_Medium", "Light_Heavy", "Medium_Light", "Medium_Medium",
                 "Heavy_Light", "Medium_Heavy"):
        for var, a in ARMORS[tier].items():
            assert not {"head", "throat", "groin"} & set(a["coverage"]), (tier, var)


def test_breastplate_and_half_plate_coverage():
    # owner decision: Breastplate = chest, stomach, upper arms; Half Plate adds the upper legs.
    # lower arms / lower legs always need loose pieces (gauntlets, greaves).
    bp = {"chest", "stomach", "left_upper_arm", "right_upper_arm"}
    hp = bp | {"left_upper_leg", "right_upper_leg"}
    for var, a in ARMORS["Medium_Heavy"].items():
        assert set(a["coverage"]) == bp and len(a["coverage"]) == 4, var
    for var, a in ARMORS["Heavy_Light"].items():
        assert set(a["coverage"]) == hp and len(a["coverage"]) == 6, var
    b, h = piece("Medium_Heavy"), piece("Heavy_Light")
    assert round(average_protection([b], "slashing"), 2) == 3.66
    assert round(average_protection([h], "slashing"), 2) == 6.61
    # bare lower arm / lower leg under a Breastplate / Half Plate: aimed strike goes in fully
    c, hm = fighter("Medium_Heavy")
    assert hm.take_damage_to_zone("left_lower_arm", 2, "slashing") == 2
    c, hm = fighter("Heavy_Light")
    assert hm.take_damage_to_zone("left_lower_leg", 4, "slashing") == 4
    assert hm.take_damage_to_zone("left_upper_leg", 4, "slashing") == 0     # 9 absorbs it


def test_half_plate_ranks_above_breastplate():
    # owner decision: Half Plate is the higher tier. Tier order = key order in armors.json.
    order = list(ARMORS)
    assert order.index("Heavy_Light") == order.index("Medium_Heavy") + 1
    assert [a["name"] for a in ARMORS["Medium_Heavy"].values()] == ["Breastplate", "Forged Breastplate"]
    assert [a["name"] for a in ARMORS["Heavy_Light"].values()] == ["Half Plate", "Forged Half Plate"]
    # the higher tier covers more and its normal-hit average is higher (for both variants)
    for var in ("standard", "dwarven"):
        lo = ArmorPiece(*[ARMORS["Medium_Heavy"][var][k] for k in ("name", "coverage", "armor_rating", "stamina_penalty", "max_durability", "weight")])
        hi = ArmorPiece(*[ARMORS["Heavy_Light"][var][k] for k in ("name", "coverage", "armor_rating", "stamina_penalty", "max_durability", "weight")])
        assert len(hi.coverage) > len(lo.coverage)
        assert average_protection([hi], "slashing") > average_protection([lo], "slashing")
        # per-piece rating: Half Plate strictly above Breastplate on every damage type
        for dt in ("slashing", "piercing", "blunt"):
            assert ARMORS["Heavy_Light"][var]["armor_rating"][dt] > ARMORS["Medium_Heavy"][var]["armor_rating"][dt], (var, dt)
    # whole ladder per variant: Scale < Breastplate < Half Plate < Full Plate on every damage type
    for var in ("standard", "dwarven"):
        for dt in ("slashing", "piercing", "blunt"):
            r = [ARMORS[t][var]["armor_rating"][dt] for t in ("Medium_Medium", "Medium_Heavy", "Heavy_Light", "Heavy_Medium")]
            assert r == sorted(set(r)), (var, dt, r)
    # every armour tier named by a character kit exists in armors.json; the old Half Plate kits point at Heavy_Light
    import glob, json as _j
    for f in glob.glob(os.path.join(os.path.dirname(__file__), "..", "rules", "characters", "*.json")):
        for key in _j.load(open(f, encoding="utf-8-sig")).get("armor", []):
            assert key in ARMORS, (f, key)
    for name in ("wojtek", "Torvald", "Brock"):
        kit = _j.load(open(os.path.join(os.path.dirname(__file__), "..", "rules", "characters", name + ".json"), encoding="utf-8-sig"))
        assert kit["armor"] == ["Heavy_Light"]    # still Half Plate


def test_wear_is_permanent_and_lowers_rating():
    p = ArmorPiece("Plate", list(BASE_ZONES), {"slashing": 10}, 0, 13 * 100, 1)   # 100 per zone
    assert p.per_zone_max["chest"] == 100 and p.original_zone_max["chest"] == 100
    for _ in range(3):                         # 3 x 10 = 30 lost = 30% of 100 -> first mark
        armor_vs_aimed([p], "chest", 50, "slashing")      # 20% of 50 = 10 per hit
    assert p.per_zone_max["chest"] == 95 and p.current_durability["chest"] == 70
    assert p.per_zone_max["stomach"] == 100              # other zones unaffected
    p.repair(10, "chest")                                  # repair never exceeds the current max
    assert p.current_durability["chest"] <= 95
    for _ in range(10):
        p.repair(10, "chest")
    assert p.current_durability["chest"] <= 95 and p.current_durability["chest"] > 70
    # two marks (90 = 10% of the original lost) -> armour rating -1
    assert zone_protection([p], "chest", "slashing") == 10
    for _ in range(4):
        armor_vs_aimed([p], "chest", 50, "slashing")
        p.repair(10, "chest")
    assert p.per_zone_max["chest"] <= 90
    assert zone_protection([p], "chest", "slashing") <= 9

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


def test_loose_placeholder_pieces():
    # owner decision: placeholder helm, gorget, gauntlets, greaves; worn on top of a body set, no stacking
    expect = {"Loose_Helm": ["head"], "Loose_Gorget": ["throat"],
              "Loose_Gauntlets": ["left_lower_arm", "right_lower_arm"],
              "Loose_Greaves": ["left_lower_leg", "right_lower_leg"]}
    for key, cov in expect.items():
        s = ARMORS[key]["standard"]
        assert s["coverage"] == cov and s["slot"] == "loose" and s["placeholder"] is True
        for k in ("armor_rating", "stamina_penalty", "max_durability", "weight", "mobility_bonus"):
            assert k in s, (key, k)
    # the body tiers keep their order: loose pieces come after Siege Plate
    order = list(ARMORS)
    assert order.index("Loose_Helm") > order.index("Heavy_Heavy")
    # Half Plate + all four loose pieces: only the best piece per zone counts
    pieces = [piece(k) for k in ("Heavy_Light", *expect)]
    assert zone_protection(pieces, "head", "slashing") == 9
    assert zone_protection(pieces, "chest", "slashing") == 9
    assert zone_protection(pieces, "throat", "slashing") == 8
    avg = average_protection(pieces, "slashing")
    assert abs(avg - (9 * 69 + 9 * 7 + 7 * 6 + 8 * 12) / 94) < 1e-9
    # aimed throat: gorget counts; legacy loader still loads every entry
    assert armor_vs_aimed(pieces, "throat", 10, "slashing")["absorbed"] == 8
    from armors import Armor
    names = [a.name for a in Armor.load_armors()]
    assert "Placeholder Helm" in names and "Half Plate" in names


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f(); print("PASS", f.__name__)
    print(f"{len(fns)} tests passed")
