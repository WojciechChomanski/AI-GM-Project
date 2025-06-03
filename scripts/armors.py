import json
import os

class Armor:
    def __init__(self, name, coverage, armor_rating, max_durability):
        self.name = name
        self.coverage = coverage
        self.armor_rating = armor_rating
        self.max_durability = max_durability
        self.current_durability = max_durability
        self.weight = 0
        self.stamina_penalty = 0
        self.mobility_bonus = 0

    def absorb_damage(self, damage, damage_type):
        if self.current_durability <= 0:
            print(f"⚠️ {self.name} is broken and offers no protection!")
            return damage
        protection = self.armor_rating.get(damage_type, 0)
        absorbed = min(damage, protection)
        remaining = max(0, damage - absorbed)
        durability_loss = max(1, int(damage * 0.1))
        self.current_durability -= durability_loss
        if self.current_durability < 0:
            self.current_durability = 0
        print(f"🛡️ {self.name} absorbed {absorbed} {damage_type} damage. Durability: {self.current_durability}/{self.max_durability}")
        return remaining

    @staticmethod
    def load_armors():
        path = os.path.join(os.path.dirname(__file__), "../rules/armors.json")
        with open(path, "r", encoding='utf-8') as f:
            armors_data = json.load(f)
        armors = []
        for tier in armors_data.values():
            for variant_data in tier.values():
                name = variant_data["name"]
                coverage = variant_data["coverage"]
                armor_rating = variant_data["armor_rating"]
                max_durability = variant_data["max_durability"]
                armor = Armor(name, coverage, armor_rating, max_durability)
                armor.weight = variant_data.get("weight", 0)
                armor.stamina_penalty = variant_data.get("stamina_penalty", 0)
                armor.mobility_bonus = variant_data.get("mobility_bonus", 0)
                armors.append(armor)
        return armors