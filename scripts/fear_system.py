import json
import random
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class FearSystem:
    def __init__(self):
        self.trauma_data = self.load_trauma()
        self.mental_state_data = self.load_mental_state()

    def load_trauma(self):
        path = os.path.join(os.path.dirname(__file__), "../rules/trauma.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logging.debug(f"Loaded trauma.json: {data}")
                return data
        except Exception as e:
            logging.error(f"Failed to load trauma.json: {e}")
            return {}

    def load_mental_state(self):
        path = os.path.join(os.path.dirname(__file__), "../rules/player_mental_state.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load player_mental_state.json: {e}")
            return {}

    def check_fear(self, defender, weapon):
        response = {"triggered": False, "outburst": "", "stress_increase": 0, "roll_penalty": 0, "force_stance": False}
        if not weapon.get("fear_trigger", False):
            logging.debug(f"No fear trigger for weapon: {weapon.get('name')}")
            return response

        defender_key = defender.name
        logging.debug(f"Checking fear for defender: {defender_key}")
        trauma = self.trauma_data.get(defender_key, {})
        mental_state = self.mental_state_data.get(defender_key.lower(), {})
        feared_weapons = trauma.get("feared_weapons", [])

        if weapon["name"].lower() in [fw.lower() for fw in feared_weapons]:
            chance = trauma.get("active_traumas", [{}])[0].get("chance_to_interfere", 0)
            if random.random() < chance:
                response["triggered"] = True
                response["outburst"] = random.choice(trauma.get("active_traumas", [{}])[0].get("example_outbursts", ["I can’t face that weapon!"]))
                response["stress_increase"] = weapon["fear_intensity"]
                response["roll_penalty"] = 10 if mental_state.get("stress", 0) > 50 else 5
                response["force_stance"] = random.random() < 0.3
                logging.debug(f"Fear triggered for {defender_key}: {response}")
        else:
            logging.debug(f"No fear for weapon {weapon['name']} in {feared_weapons}")
        return response