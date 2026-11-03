# file: scripts/stance_logic.py
"""Thin wrapper kept for old imports. The numbers live in rules/stances.json and
rules/weapon_stances.json and are read by combat_techniques (single source of truth)."""
import combat_techniques as CT

STANCE_DATA = CT.STANCES


def apply_stance_modifiers(attacker, defender, stance_type, roll_type, weapon=None):
    """roll_type = 'attack' or 'defense'. stance_type may be a generic stance or a guard id."""
    atk, df = CT.stance_modifiers(stance_type, weapon)
    return atk if roll_type == "attack" else df if roll_type == "defense" else 0


def get_stamina_cost_modifier(stance_type, maneuver_type, weapon=None):
    """Stamina modifier for an offensive or defensive action in this stance/guard."""
    return CT.guard_info(weapon, stance_type)["stamina"].get(maneuver_type, 0)
