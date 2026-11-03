# file: scripts/maneuver_handler.py
"""Kept for old imports. Returns the effects of ONE maneuver (the best valid), never a sum."""
from maneuver_engine import ManeuverEngine


class ManeuverHandler:
    def __init__(self, maneuver_file=None):
        self._e = ManeuverEngine()
        self.maneuvers = self._e.maneuvers_data

    def get_applicable_maneuvers(self, weapon_type, stance, trigger, aimed_zone=None):
        return self._e.get_available_maneuvers(weapon_type, stance, trigger, aimed_zone)

    def get_bonus_effects(self, weapon_type, stance, trigger, aimed_zone=None, name=None):
        m = self._e.select_maneuver(weapon_type, stance, trigger, aimed_zone, name)
        out = {"attack_bonus": 0, "defense_bonus": 0, "stamina_cost_modifier": 0, "notes": [], "maneuver": None}
        if m:
            e = m["effects"]
            out.update(attack_bonus=e.get("attack_bonus", 0), defense_bonus=e.get("defense_bonus", 0),
                       stamina_cost_modifier=e.get("stamina_cost_modifier", 0), maneuver=m["name"],
                       notes=[e["notes"]] if e.get("notes") else [])
        return out
