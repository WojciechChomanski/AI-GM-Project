# file: scripts/strength.py
"""Strength system v1 (docs/STRENGTH.md). ALL NUMBERS ARE PLACEHOLDERS for playtesting.

Strength (the stat) is training level; Power is what it produces.
"""
import math

# --- 1. Power curve -------------------------------------------------------
LINEAR_BASE_STR = 30      # STR 30 -> power 1.0
LINEAR_SLOPE = 0.05       # +0.05 power per point up to 50
KNEE_STR = 50             # above this, power doubles every DOUBLING_STEP points
DOUBLING_STEP = 10
POWER_FLOOR = 0.1


def power(strength):
    """Power from Strength: gentle to 50, then doubling every 10 points."""
    s = float(strength)
    if s <= KNEE_STR:
        return max(POWER_FLOOR, 1.0 + (s - LINEAR_BASE_STR) * LINEAR_SLOPE)
    knee = 1.0 + (KNEE_STR - LINEAR_BASE_STR) * LINEAR_SLOPE  # 2.0
    return knee * 2 ** ((s - KNEE_STR) / DOUBLING_STEP)


# --- 2. Sex factors -------------------------------------------------------
MALE_FACTORS = {"arm": 1.15, "leg": 1.05, "compound": 1.6}


def sex_factor(gender, kind):
    if str(gender).lower().startswith("m"):
        return MALE_FACTORS[kind]
    return 1.0


def effective_power(strength, gender, kind="compound"):
    """kind: 'arm' (grip/swing/parry/bow), 'leg' (kick/brace), 'compound' (clinch/grapple/shove/drag/march)."""
    return power(strength) * sex_factor(gender, kind)


# --- 3. Contests ----------------------------------------------------------
CONTEST_MIN, CONTEST_MAX = 0.05, 0.95
STEP_MULT = math.sqrt(2)  # every +10 of a flat bonus / technique edge = x1.41


def bonus_multiplier(flat_bonus):
    """Convert a flat bonus (e.g. ogre Titanic Might +20 grappling) into a power multiplier."""
    return STEP_MULT ** (flat_bonus / 10.0)


def technique_multiplier(own_skill, other_skill):
    """Weapon Skill or Agility edge: x1.41 per 10 points of advantage (symmetric)."""
    return STEP_MULT ** ((own_skill - other_skill) / 10.0)


MASS_REF = 80.0


def mass_multiplier(mass_kg):
    """Only for shove/knockdown: (mass/80)^(1/3)."""
    return (mass_kg / MASS_REF) ** (1.0 / 3.0)


def contest_chance(power_a, power_b, technique_a=1.0, technique_b=1.0):
    """Chance A wins one contest: A's share of combined power, clamped 5..95%.
    power_a / power_b may be sums (allies grabbing the same target add power)."""
    a = power_a * technique_a
    b = power_b * technique_b
    if a + b <= 0:
        return 0.5
    return min(CONTEST_MAX, max(CONTEST_MIN, a / (a + b)))


def chance_over_attempts(per_try, attempts):
    """Chance of at least one success in N tries (e.g. escaping a 2-round ogre rip)."""
    return 1 - (1 - per_try) ** attempts


# --- 4. Clinch stamina ----------------------------------------------------
ROUND_SECONDS = 6
CLINCH_BASE_COST = 2.0
CLINCH_LOAD_COEF = 1.2
DEFAULT_STAMINA_POOL = 60
SUSTAINED_HOLD_FEMALE_DISCOUNT = 0.25  # women: -25% on static holds (bow drawn, shield up, ledge)


def clinch_cost_per_round(own_power, opponent_power):
    """Being clinched = carrying them. Load L = their power / yours."""
    load = opponent_power / own_power
    return CLINCH_BASE_COST + CLINCH_LOAD_COEF * load * load


def clinch_seconds_to_exhaustion(own_power, opponent_power, pool=DEFAULT_STAMINA_POOL):
    return pool / clinch_cost_per_round(own_power, opponent_power) * ROUND_SECONDS


def sustained_hold_cost(base_cost, gender):
    """Static holds only (not a contested clinch)."""
    if not str(gender).lower().startswith("m"):
        return base_cost * (1 - SUSTAINED_HOLD_FEMALE_DISCOUNT)
    return base_cost


# --- 5. Carry and march ---------------------------------------------------
CARRY_MALE_MULT = 1.15  # mirrors rules/combat_rules.json carry_capacity


def carry_capacity(strength, gender, race_mult=1.0):
    """Existing formula from rules/combat_rules.json: base_kg = 20 + STR*1.5, male x1.15."""
    sexm = CARRY_MALE_MULT if str(gender).lower().startswith("m") else 1.0
    return (20 + strength * 1.5) * sexm * race_mult


MARCH_BASE = 1.0
MARCH_LOAD_COEF = 40.0
MARCH_CLIFF_START = 0.5
MARCH_CLIFF_COEF = 600.0
MARCH_RESERVE_PER_END = 3


def march_cost_per_km(load_kg, capacity_kg):
    load = load_kg / capacity_kg
    cost = MARCH_BASE + MARCH_LOAD_COEF * load * load
    if load > MARCH_CLIFF_START:
        cost += MARCH_CLIFF_COEF * (load - MARCH_CLIFF_START)
    return cost


def march_reserve(endurance, bonus=0):
    return endurance * MARCH_RESERVE_PER_END + bonus


def march_km_until_exhausted(load_kg, capacity_kg, endurance, bonus=0):
    return march_reserve(endurance, bonus) / march_cost_per_km(load_kg, capacity_kg)


# --- 6. Damage bonus ------------------------------------------------------
def strength_damage_bonus(strength, gender):
    """floor(2 x arm power). F30 +2, F45 +3, M50 +4, M55 +6, M60 +9, M70 +18.
    Replaces the old STR//5 and ogre Grizzly Force mass//10."""
    return int(math.floor(2 * effective_power(strength, gender, "arm")))


# --- 7. Grip demand (weapon min_STR) -------------------------------------
GRIP_PENALTY_PER_5 = 5
GRIP_STAMINA_PER_5 = 0.10


def grip_check(strength, gender, min_str):
    """Compare arm power with the power a min_STR weapon needs."""
    if not min_str:
        return {"ok": True, "parry_penalty": 0, "stamina_mult": 1.0, "disarm_risk": False}
    have = effective_power(strength, gender, "arm")
    need = power(min_str)
    if have >= 2 * need:
        return {"ok": True, "parry_penalty": 0, "stamina_mult": 0.5, "disarm_risk": False}
    if have >= need:
        return {"ok": True, "parry_penalty": 0, "stamina_mult": 1.0, "disarm_risk": False}
    # express shortfall in Strength points on the linear part
    eff_str = LINEAR_BASE_STR + (have - 1.0) / LINEAR_SLOPE
    short = max(0.0, min_str - eff_str)
    steps = math.ceil(short / 5)
    return {"ok": False, "parry_penalty": -GRIP_PENALTY_PER_5 * steps,
            "stamina_mult": 1 + GRIP_STAMINA_PER_5 * steps, "disarm_risk": True}


# --- 8/9. Caps and talents -----------------------------------------------
IRON_THEWED = "iron_thewed"


def stat_cap(base_max, race, gender, stat, talents=()):
    """Race cap from stats.json plus talent cap raises from rules/talents/ (max +5).
    Iron-Thewed: human male STR 50 -> 55."""
    import talents as T
    return base_max + T.cap_raise(stat, race, gender, talents)


def iron_thewed_break_free(character_talents, used_this_fight, grabber_mass_kg):
    """Once per fight: automatic break-free from a human-size grab (grabber mass <= 120 kg)."""
    return IRON_THEWED in (character_talents or ()) and not used_this_fight and grabber_mass_kg <= 120
