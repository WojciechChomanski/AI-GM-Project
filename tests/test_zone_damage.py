"""Zone damage tests. Run: python tests/test_zone_damage.py  (or pytest)"""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from zone_hp import BASE_ZONES, scaled_zones, hp_multiplier, spread_damage, AIMED_PENALTY
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
    assert len(split) == 13  # whole body takes damage


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


if __name__ == "__main__":
    import logging; logging.disable(logging.CRITICAL)
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f(); print("PASS", f.__name__)
    print(f"{len(fns)} tests passed")
