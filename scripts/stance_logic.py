# ✅ stance_logic.py
# file: scripts/stance_logic.py

STANCE_DATA = {
    "offensive": {
        "attack_bonus": 3,
        "defense_penalty": 3,
        "stamina_cost_modifier": {"offensive": -1, "defensive": +1},
    },
    "defensive": {
        "defense_bonus": 5,
        "attack_penalty": 3,
        "stamina_cost_modifier": {"offensive": +1, "defensive": -1},
    },
    "neutral": {
        "attack_bonus": 0,
        "defense_bonus": 0,
        "stamina_cost_modifier": {"offensive": 0, "defensive": 0},
    }
}

def apply_stance_modifiers(attacker, defender, stance_type, roll_type):
    """
    Applies stance-based roll modifiers. 
    roll_type = "attack" or "defense"
    """
    stance = STANCE_DATA.get(stance_type, STANCE_DATA["neutral"])
    bonus = 0

    if roll_type == "attack":
        bonus += stance.get("attack_bonus", 0)
        bonus -= stance.get("attack_penalty", 0)
    elif roll_type == "defense":
        bonus += stance.get("defense_bonus", 0)
        bonus -= stance.get("defense_penalty", 0)

    return bonus

def get_stamina_cost_modifier(stance_type, maneuver_type):
    """
    Returns stamina modifier: offensive or defensive maneuver during stance.
    """
    stance = STANCE_DATA.get(stance_type, STANCE_DATA["neutral"])
    return stance["stamina_cost_modifier"].get(maneuver_type, 0)