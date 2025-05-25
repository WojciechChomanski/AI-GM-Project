# file: scripts/maneuver_handler.py

import json
import random
from maneuver_engine import ManeuverEngine

class ManeuverHandler:
    def __init__(self, maneuver_file="../rules/weapon_maneuvers.json"):
        self.maneuvers = json.load(open(maneuver_file, "r"))
        self.engine = ManeuverEngine(maneuver_file)

    def get_applicable_maneuvers(self, weapon_type, stance, trigger):
        """Return a list of maneuvers that match the weapon_type, stance, and trigger."""
        if weapon_type not in self.maneuvers:
            return []

        return [m for m in self.maneuvers[weapon_type]
                if m.get("stance_required") == stance and m.get("trigger") == trigger]

    def get_bonus_effects(self, weapon_type, stance, trigger, aimed_zone=None):
        """Collect bonuses from all triggered maneuvers and combine them."""
        maneuvers = self.get_applicable_maneuvers(weapon_type, stance, trigger)
        if aimed_zone:
            aimed_maneuver = self.engine.select_random_maneuver(weapon_type, stance, trigger, aimed_zone)
            if aimed_maneuver:
                maneuvers.append(aimed_maneuver)

        total_bonus = {"attack_bonus": 0, "defense_bonus": 0, "stamina_cost_modifier": 0, "notes": []}

        for m in maneuvers:
            effects = m.get("effects", {})
            total_bonus["attack_bonus"] += effects.get("attack_bonus", 0)
            total_bonus["defense_bonus"] += effects.get("defense_bonus", 0)
            total_bonus["stamina_cost_modifier"] += effects.get("stamina_cost_modifier", 0)
            if effects.get("notes"):
                total_bonus["notes"].append(effects["notes"])
                print(f"🗡️ {m['name']}: {m['description']}")

        return total_bonus
