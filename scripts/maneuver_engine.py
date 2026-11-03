# file: scripts/maneuver_engine.py
"""Kept for old imports: maneuver selection now lives in combat_techniques (one maneuver per action)."""
import combat_techniques as CT


class ManeuverEngine:
    def __init__(self, path=None):
        self.maneuvers_data = CT.MANEUVERS

    def get_available_maneuvers(self, weapon, stance, round_context="always", aimed_zone=None, perks=None):
        """weapon = weapons.json key or dict (or a guard-set id such as '2H_sword')."""
        if isinstance(weapon, str) and weapon in CT.GUARD_SETS:
            weapon = {"guard_set": weapon, "stance_tree": list(CT.GUARD_SETS[weapon]["stances"]),
                      "features": ["point", "beak", "hook", "chain"]}
        return CT.valid_maneuvers(weapon, stance, round_context, aimed_zone, perks)

    def select_maneuver(self, weapon, stance, round_context="always", aimed_zone=None, name=None, perks=None):
        if isinstance(weapon, str) and weapon in CT.GUARD_SETS:
            weapon = {"guard_set": weapon, "stance_tree": list(CT.GUARD_SETS[weapon]["stances"]),
                      "features": ["point", "beak", "hook", "chain"]}
        return CT.choose_maneuver(weapon, stance, round_context, aimed_zone, perks, name)[0]

    select_random_maneuver = select_maneuver  # old name; now deterministic best-valid

    def describe_maneuver(self, maneuver):
        e = maneuver["effects"]
        return f"🗡️ Maneuver used: {maneuver['name']} (Stamina: {e['stamina_cost_modifier']}, Attack Bonus: {e['attack_bonus']})"
