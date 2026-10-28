"""Zone damage tests. Run: python tests/test_zone_damage.py  (or pytest)"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from zone_hp import BASE_ZONES, scaled_zones, hp_multiplier, spread_damage, AIMED_PENALTY, VITAL_ZONES
from character import Character
from combat_health import CombatHealthManager


def fresh(mult=1.0):
    c = Character(); c.name = "Test"
    c.body_parts = scaled_zones(mult); c.max_body_parts = dict(c.body_parts)
    c.total_hp = sum(c.body_parts.values())
    return c, CombatHealthManager(c)


def test_base_and_scaling():
    assert sum(BASE_ZONES.values()) == 100 and len(BASE_ZONES) == 13
    assert sum(scaled_zones(hp_multiplier(20, 0)).values()) == 120   # Dwarf
    assert sum(scaled_zones(hp_multiplier(100, 0)).values()) == 200  # Ogre
    assert sum(scaled_zones(hp_multiplier(0, 15)).values()) == 115   # Knight
    assert sum(scaled_zones(hp_multiplier(20, 15)).values()) == 138  # Dwarf knight


def test_spread_is_weighted_and_exact():
    mx = scaled_zones()
    split = spread_damage(dict(mx), mx, 25)
    assert sum(split.values()) == 25
    assert split["chest"] >= split["left_upper_leg"] >= split["left_lower_arm"]
    assert len(split) == 11 and "throat" not in split and "groin" not in split


def test_normal_hit_keeps_total_in_sync():
    random.seed(1)
    c, h = fresh()
    h.distribute_damage(10, "slashing")
    assert h.total_hp == 90 == c.total_hp == sum(h.health.values())
    assert c.alive


def test_zone_floor_and_limb_destroyed():
    random.seed(2)
    c, h = fresh()
    h.take_damage_to_zone("right_lower_arm", 10, "slashing")
    assert h.health["right_lower_arm"] == 0  # never below 0
    assert c.alive and "right_lower_arm" in c.compromised_limbs
    assert h.total_hp == 97


def test_vital_zone_kills():
    random.seed(3)
    c, h = fresh()
    h.take_damage_to_zone("head", 50, "blunt")
    assert not c.alive


def test_missed_aimed_strike_does_nothing():
    c, h = fresh()
    assert h.resolve_aimed_strike(False, "head", 50, "piercing") == 0
    assert h.total_hp == 100 and c.alive and AIMED_PENALTY == 30


def test_character_level_spread():
    c = Character(); c.toughness = 0
    c.receive_damage(10)
    assert c.total_hp == 90 and sum(c.body_parts.values()) == 90


def test_throat_and_groin_untouched_by_spread():
    mx = scaled_zones()
    for dmg in (1, 6, 10, 15, 20, 60, 500):
        split = spread_damage(dict(mx), mx, dmg)
        assert "throat" not in split and "groin" not in split


def test_head_floors_at_1_under_spread():
    mx = scaled_zones()
    split = spread_damage(dict(mx), mx, 1000)
    after = {z: mx[z] - split.get(z, 0) for z in mx}
    assert after["head"] == 1
    assert after["chest"] == 0                      # chest may reach 0 by spread
    assert after["throat"] == mx["throat"] and after["groin"] == mx["groin"]
    # damage the head could not absorb went elsewhere (everything else eligible is 0)
    assert all(after[z] == 0 for z in mx if z not in ("head", "throat", "groin"))


def test_spread_never_kills_via_head_or_throat():
    random.seed(5)
    for dmg in (6, 10, 15, 20):
        c, h = fresh()
        for _ in range(200):
            if not c.alive:
                break
            h.distribute_damage(dmg, "slashing")
            assert h.health["head"] >= 1 and h.health["throat"] == 3 and h.health["groin"] == 3
        assert not c.alive  # eventually dies, but via chest / collapse
        assert h.health["head"] >= 1 and h.health["throat"] == 3


def test_head_hit_by_spread_still_wounded_not_dead():
    c, h = fresh()
    h.distribute_damage(10, "blunt")
    assert 1 <= h.health["head"] < 7 and c.alive


def test_aimed_strike_to_throat_can_kill():
    random.seed(6)
    c, h = fresh()
    h.resolve_aimed_strike(True, "throat", 3, "piercing")
    assert h.health["throat"] == 0 and not c.alive


def test_three_zones_at_zero_collapse():
    random.seed(7)
    c, h = fresh()
    h.morale_check = lambda: True  # isolate collapse from the crit-wound morale break
    h.take_damage_to_zone("right_lower_arm", 10, "slashing")
    h.take_damage_to_zone("left_lower_arm", 10, "slashing")
    assert c.alive  # two zones down: still up
    h.take_damage_to_zone("left_lower_leg", 20, "slashing")
    assert sum(1 for v in h.health.values() if v == 0) == 3
    assert not c.alive  # collapse


def test_no_collapse_from_33_percent_loss_alone():
    random.seed(8)
    c, h = fresh()
    # 40% of total HP lost, but no zone at 0: chest -12 (20->8), thigh -12 (13->1), stomach -10, upper arm -5
    for z, d in (("chest", 12), ("left_upper_leg", 12), ("stomach", 10), ("right_upper_arm", 5)):
        h.health[z] -= d
    h._sync_total()
    h.apply_bleeding()
    h.check_zone_collapse()
    assert h.total_hp <= 67 and c.alive
    h.character.pain_penalty = 0
    assert h.check_auto_collapse() is False and c.alive
    assert not hasattr(h, "check_blood_loss_collapse")


def test_bleeding_respects_spread_rules():
    c, h = fresh()
    h.bleeding_wounds.append({"amount": 500, "duration": 3})
    h.apply_bleeding()
    assert h.health["throat"] == 3 and h.health["groin"] == 3 and h.health["head"] >= 1


if __name__ == "__main__":
    import logging; logging.disable(logging.CRITICAL)
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f(); print("PASS", f.__name__)
    print(f"{len(fns)} tests passed")
