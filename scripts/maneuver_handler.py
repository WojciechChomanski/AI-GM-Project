# file: scripts/maneuver_handler.py

import json
import random

class ManeuverHandler:
    def __init__(self, maneuver_file="../rules/weapon_maneuvers.json"):
        self.maneuvers = json.load(open(maneuver_file, "r"))

    def get_applicable_maneuvers(self, weapon_type, stance, trigger, aimed_zone=None):
        """Return a list of maneuvers that match the weapon_type, stance, and trigger."""
        if weapon_type not in self.maneuvers:
            return []

        maneuvers = []
        for m in self.maneuvers[weapon_type]:
            if m["stance_required"] == stance and (m["trigger"] == trigger or m["trigger"] == "always"):
                if aimed_zone and "aimed_zone" in m:
                    if aimed_zone in m["aimed_zone"]:
                        maneuvers.append(m)
                else:
                    maneuvers.append(m)
        return maneuvers

    def get_bonus_effects(self, weapon_type, stance, trigger, aimed_zone=None):
        """Collect bonuses from all triggered maneuvers and combine them."""
        maneuvers = self.get_applicable_maneuvers(weapon_type, stance, trigger, aimed_zone)

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