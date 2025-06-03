import json
import random
import os

class FearSystem:
    def __init__(self):
        self.trauma_data = self.load_trauma()
        self.mental_state_data = self.load_mental_state()

    def load_trauma(self):
        path = os.path.join(os.path.dirname(__file__), "../rules/trauma.json")
        return json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}

    def load_mental_state(self):
        path = os.path.join(os.path.dirname(__file__), "../rules/player_mental_state.json")
        return json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}

    def check_fear(self, defender, weapon):
        response = {"triggered": False, "outburst": "", "stress_increase": 0, "roll_penalty": 0, "force_stance": False}
        if not weapon.get("fear_trigger", False):
            return response

        defender_key = defender.name.lower()
        trauma = self.trauma_data.get(defender_key, {})
        mental_state = self.mental_state_data.get(defender_key, {})
        feared_weapons = trauma.get("feared_weapons", [])

        if weapon["name"].lower() in feared_weapons and random.random() < trauma.get("active_traumas", [{}])[0].get("chance_to_interfere", 0):
            response["triggered"] = True
            response["outburst"] = random.choice(trauma.get("active_traumas", [{}])[0].get("example_outbursts", ["I can’t face that weapon again!"]))
            response["stress_increase"] = weapon["fear_intensity"]
            response["roll_penalty"] = 10 if mental_state.get("stress", 0) > 50 else 5
            response["force_stance"] = random.random() < 0.3
        return response