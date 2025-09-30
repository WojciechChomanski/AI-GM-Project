# file: scripts/item_system.py
import random
import logging
from character import Character

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ItemSystem:
    def __init__(self):
        self.items = {
            "moonbloom_elixir": {
                "stress_relief": -20,
                "secret_spill_chance": 0.3,
                "addiction_risk": 0.15
            }
        }

    def use_item(self, user: Character, item_name: str, target: Character):
        item = self.items.get(item_name)
        if not item:
            print(f"❌ Unknown item: {item_name}")
            return False
        print(f"🧪 {user.name} uses {item_name} on {target.name}")
        if "stress_relief" in item:
            target.stress_level = max(0, target.stress_level + item["stress_relief"])
            print(f"😌 {target.name} reduces stress by {abs(item['stress_relief'])}")
            if random.random() < item.get("secret_spill_chance", 0):
                print(f"🗣️ {target.name} spills secrets under {item_name} influence!")
            if random.random() < item.get("addiction_risk", 0):
                target.status_effects.append({"name": "moonbloom_addiction", "duration": 5, "stress_penalty": 5})
                print(f"⚠️ {target.name} risks addiction to {item_name}!")
        logging.debug(f"Item used: {item_name} by {user.name} on {target.name}")
        return True