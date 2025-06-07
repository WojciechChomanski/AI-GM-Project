import json
import os

class Armor:
    def __init__(self, name, coverage, armor_rating, max_durability, weight, stamina_penalty, mobility_bonus):
        self.name = name
        self.coverage = coverage
        self.armor_rating = armor_rating
        self.max_durability = max_durability
        self.current_durability = {part: max_durability // len(coverage) for part in coverage}
        self.max_repairable_durability = {part: max_durability // len(coverage) for part in coverage}
        self.weight = weight
        self.stamina_penalty = stamina_penalty
        self.mobility_bonus = mobility_bonus

    def absorb_damage(self, damage, damage_type, part):
        if part not in self.current_durability or self.current_durability[part] <= 0:
            print(f"⚠️ {self.name} part ({part}) is broken and offers no protection!")
            return damage
        protection = self.armor_rating.get(damage_type, 0)
        absorbed = min(damage, protection)
        remaining = max(0, damage - absorbed)
        durability_loss = max(1, int(damage * 0.1))
        self.current_durability[part] -= durability_loss
        if self.current_durability[part] < 0:
            self.current_durability[part] = 0
        if self.current_durability[part] < 0.2 * (self.max_durability // len(self.coverage)):
            self.max_repairable_durability[part] = int(0.8 * (self.max_durability // len(self.coverage)))
        print(f"🛡️ {self.name} absorbed {absorbed} {damage_type} damage. Part ({part}) Durability: {self.current_durability[part]}/{self.max_repairable_durability[part]}")
        return remaining

    @staticmethod
    def load_armors():
        armors = []
        # Load from armors.json
        path = os.path.join(os.path.dirname(__file__), "../rules/armors.json")
        try:
            with open(path, "r", encoding='utf-8') as f:
                armors_data = json.load(f)
            for tier in armors_data.values():
                for variant_data in tier.values():
                    armor = Armor(
                        name=variant_data["name"],
                        coverage=variant_data["coverage"],
                        armor_rating=variant_data["armor_rating"],
                        max_durability=variant_data["max_durability"],
                        weight=variant_data["weight"],
                        stamina_penalty=variant_data["stamina_penalty"],
                        mobility_bonus=variant_data["mobility_bonus"]
                    )
                    armors.append(armor)
        except Exception as e:
            print(f"⚠️ Failed to load armors.json: {e}")
        
        # Optionally load from armore.json
        legacy_path = os.path.join(os.path.dirname(__file__), "../rules/armore.json")
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, "r", encoding='utf-8') as f:
                    legacy_data = json.load(f)
                for armor_data in legacy_data.values():
                    armor = Armor(
                        name=armor_data["name"],
                        coverage=armor_data["coverage"],
                        armor_rating=armor_data["armor_rating"],
                        max_durability=armor_data["max_durability"],
                        weight=armor_data["weight"],
                        stamina_penalty=armor_data["stamina_penalty"],
                        mobility_bonus=0
                    )
                    armors.append(armor)
            except Exception as e:
                print(f"⚠️ Failed to load armore.json: {e}")
        
        return armors