# ✅ File: scripts/maneuver_engine.py
# Loads and selects weapon-specific combat maneuvers based on stance, weapon type, and combat context

import json
import random

class ManeuverEngine:
    def __init__(self, path="../rules/weapon_maneuvers.json"):
        with open(path, 'r') as f:
            self.maneuvers_data = json.load(f)

    def get_available_maneuvers(self, weapon_type, stance, round_context="always"):
        """Return maneuvers based on weapon type, stance, and round context (e.g. 'after_block')"""
        if weapon_type not in self.maneuvers_data:
            return []

        return [m for m in self.maneuvers_data[weapon_type]
                if m["stance"] == stance and (m["context"] == round_context or m["context"] == "always")]

    def select_random_maneuver(self, weapon_type, stance, round_context="always"):
        """Randomly select a maneuver from available options."""
        options = self.get_available_maneuvers(weapon_type, stance, round_context)
        if not options:
            return None
        return random.choice(options)

    def describe_maneuver(self, maneuver):
        """Generate a description log line for the maneuver."""
        return f"🗡️ Maneuver used: {maneuver['name']} (Stamina: {maneuver['stamina_cost']}, Damage Bonus: {maneuver['damage_bonus']})"

# Example usage:
if __name__ == "__main__":
    engine = ManeuverEngine()
    move = engine.select_random_maneuver("2H_sword", "vom_tag")
    if move:
        print(engine.describe_maneuver(move))
