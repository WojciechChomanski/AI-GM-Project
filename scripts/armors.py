import json

class Armor:
    def __init__(self, name, coverage, armor_rating, durability):
        self.name = name
        self.coverage = coverage
        self.armor_rating = armor_rating
        self.current_durability = durability

    def absorb_damage(self, damage, damage_type):
        protection = self.armor_rating.get(damage_type, 0)
        absorbed = min(damage, protection)
        remaining = damage - absorbed
        print(f"🛡️ {self.name} absorbed {absorbed} {damage_type} damage. Remaining Durability: {self.current_durability}/{self.current_durability}")
        return remaining

    @staticmethod
    def load_armors():
        with open("../rules/armors.json", "r") as f:
            armors_data = json.load(f)
        armors = []
        for armor_data in armors_data:
            name = armor_data["name"]
            coverage = armor_data["coverage"]
            armor_rating = armor_data["armor_rating"]
            durability = armor_data["durability"]
            armors.append(Armor(name, coverage, armor_rating, durability))
        return armors