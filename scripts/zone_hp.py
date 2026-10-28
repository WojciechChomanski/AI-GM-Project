# file: scripts/zone_hp.py
"""Body-zone hit points: one source of truth for HP.

Total HP is ALWAYS the sum of the 13 zones. See docs/ZONE_DAMAGE.md.
"""

BASE_ZONES = {
    "chest": 20,
    "left_upper_leg": 13, "right_upper_leg": 13,
    "stomach": 11,
    "head": 7,
    "left_upper_arm": 6, "right_upper_arm": 6,
    "left_lower_leg": 6, "right_lower_leg": 6,
    "left_lower_arm": 3, "right_lower_arm": 3,
    "throat": 3,
    "groin": 3,
}  # sums to 100

VITAL_ZONES = ("head", "throat", "chest")  # at 0 -> death / dying
AIMED_PENALTY = 30  # flat -30 to hit for every aimed strike


def hp_multiplier(race_hp_bonus=0, class_hp_percent=0):
    """Dwarf hp_bonus 20 -> x1.2, Ogre 100 -> x2, knight hp_percent 15 -> x1.15."""
    return (1 + (race_hp_bonus or 0) / 100.0) * (1 + (class_hp_percent or 0) / 100.0)


def scaled_zones(multiplier=1.0):
    """Scale every zone proportionally; rounding leftovers go to the chest."""
    target = round(100 * multiplier)
    zones = {z: max(1, round(hp * multiplier)) for z, hp in BASE_ZONES.items()}
    zones["chest"] += target - sum(zones.values())
    return zones


def total_hp(zones):
    return sum(max(0, v) for v in zones.values())


# Normal (spread) hits never touch these zones - only aimed strikes can.
SPREAD_EXCLUDED = frozenset({"throat", "groin"})
# Spread damage can lower these zones only down to the given value (head never 0 via spread).
SPREAD_FLOOR = {"head": 1}
COLLAPSE_ZONES_AT_ZERO = 3  # this many zones at 0 HP = collapse


def zones_at_zero(current):
    return [z for z, v in current.items() if v <= 0]


def spread_damage(current, maximum, damage, excluded=SPREAD_EXCLUDED, floor=SPREAD_FLOOR):
    """Split a normal hit over the eligible zones, proportional to each zone's max
    (largest-remainder rounding).
    - `excluded` zones (throat, groin) take nothing from a spread hit.
    - `floor` maps zone -> lowest value spread damage may leave it at (head: 1).
      The chest has no floor, so it can reach 0 by spread (= death).
    Damage a zone cannot absorb is re-spread over the remaining eligible zones.
    Returns {zone: damage_actually_taken}."""
    excluded = excluded or ()
    floor = floor or {}
    taken = {z: 0 for z in current}
    remaining = int(max(0, damage))
    while remaining > 0:
        alive = [z for z in current
                 if z not in excluded and current[z] - taken[z] > floor.get(z, 0)]
        if not alive:
            break
        weight = sum(maximum.get(z, 1) for z in alive)
        shares = {z: remaining * maximum.get(z, 1) / weight for z in alive}
        alloc = {z: int(sh) for z, sh in shares.items()}
        leftover = remaining - sum(alloc.values())
        # largest remainder; ties -> bigger zone first, then fixed order
        order = sorted(alive, key=lambda z: (-(shares[z] - alloc[z]), -maximum.get(z, 1), list(current).index(z)))
        for z in order[:leftover]:
            alloc[z] += 1
        spent = 0
        for z in alive:
            room = current[z] - taken[z] - floor.get(z, 0)
            hit = min(room, alloc[z])
            taken[z] += hit
            spent += hit
        remaining -= spent
        if spent == 0:
            break
    return {z: d for z, d in taken.items() if d > 0}
