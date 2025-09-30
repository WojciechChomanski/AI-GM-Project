# ✅ File: scripts/maneuver_engine.py
# Loads and selects weapon-specific combat maneuvers based on stance, weapon type, and combat context

import json
import random

class ManeuverEngine:
    def __init__(self, path="../rules/weapon_maneuvers.json"):
        with open(path, 'r') as f:
            self.maneuvers_data = json.load(f)

    def get_available_maneuvers(self, weapon_type, stance, round_context="always", aimed_zone=None):
        """Return maneuvers based on weapon type, stance, context, and aimed zone."""
        if weapon_type not in self.maneuvers_data:
            return []

        maneuvers = []
        for m in self.maneuvers_data[weapon_type]:
            if m["stance_required"] == stance and (m["trigger"] == round_context or m["trigger"] == "always"):
                if aimed_zone and "aimed_zone" in m:
                    if aimed_zone in m["aimed_zone"]:
                        maneuvers.append(m)
                else:
                    maneuvers.append(m)
        return maneuvers

    def select_random_maneuver(self, weapon_type, stance, round_context="always", aimed_zone=None):
        """Randomly select a maneuver from available options."""
        options = self.get_available_maneuvers(weapon_type, stance, round_context, aimed_zone)
        if not options:
            return None
        return random.choice(options)

    def describe_maneuver(self, maneuver):
        """Generate a description log line for the maneuver."""
        return f"🗡️ Maneuver used: {maneuver['name']} (Stamina: {maneuver['effects']['stamina_cost_modifier']}, Attack Bonus: {maneuver['effects']['attack_bonus']})"

if __name__ == "__main__":
    engine = ManeuverEngine()
    move = engine.select_random_maneuver("2H_sword", "vom_tag")
    if move:
        print(engine.describe_maneuver(move))