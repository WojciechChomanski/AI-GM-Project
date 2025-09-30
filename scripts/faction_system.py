# file: scripts/faction_system.py
import random
import json
import logging
import os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class FactionSystem:
    def __init__(self, character):
        self.character = character
        self.factions = self.load_factions()
        self.alignment = {"daughters_drowned_moon": 0, "saffron_veil": 0, "iron_covenant": 0}

    def load_factions(self):
        path = os.path.join(os.path.dirname(__file__), "../rules/factions.json")
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "daughters_drowned_moon": {
                    "role": "veil_covenant",
                    "alignment": "chaotic",
                    "benefits": {"spell_access": ["tide_wail"], "corruption_risk": 0.15},
                    "penalties": {"brine_marks": 1, "breath_access": False}
                },
                "saffron_veil": {
                    "role": "espionage",
                    "alignment": "chaotic",
                    "benefits": {"persuasion_bonus": 15, "intel_drop_rate": 0.2},
                    "penalties": {"abyss_tether": {"willpower_penalty": -5, "chance": 0.1}}
                },
                "iron_covenant": {
                    "role": "breath_zealots",
                    "alignment": "lawful",
                    "benefits": {"rune_craft": 10, "defense_bonus": 5},
                    "penalties": {"veil_access": False, "willpower_check": 25}
                }
            }

    def align_with_faction(self, faction_name, amount):
        if faction_name not in self.alignment:
            print(f"❌ Unknown faction: {faction_name}")
            return False
        self.alignment[faction_name] = min(100, self.alignment[faction_name] + amount)
        print(f"🤝 {self.character.name}'s alignment with {faction_name} rises to {self.alignment[faction_name]}")
        logging.debug(f"Alignment updated: {faction_name} = {self.alignment[faction_name]}")
        if faction_name == "daughters_drowned_moon" and self.alignment[faction_name] >= 50:
            self.character.status_effects.append({"name": "brine_marks", "count": 1})
            print(f"😈 {self.character.name} gains Brine Marks from Daughters of the Drowned Moon!")
        elif faction_name == "saffron_veil" and self.alignment[faction_name] >= 50:
            if random.random() < 0.1:
                self.character.status_effects.append({"name": "abyss_tether", "willpower_penalty": -5, "duration": 3})
                print(f"😈 {self.character.name} suffers Abyss Tether from Saffron Veil!")
        elif faction_name == "iron_covenant" and self.alignment[faction_name] >= 50:
            if self.character.race == "Dwarf":
                self.character.rune_craft = getattr(self.character, "rune_craft", 0) + 10
                print(f"🔨 {self.character.name} masters rune crafting with Iron Covenant!")
            else:
                roll = random.randint(1, 100)
                if roll < 25:
                    print(f"⚠️ {self.character.name} fails Iron Covenant's faith test!")
                    self.alignment[faction_name] -= 10
        return True

    def charisma_check(self, difficulty):
        charisma = self.character.charisma + getattr(self.character, "charisma_penalty", 0)
        roll = random.randint(1, 100) + (charisma // 5)
        print(f"🎭 {self.character.name} charisma check: rolled {roll} vs difficulty {difficulty}")
        logging.debug(f"Charisma check for {self.character.name}: {roll} vs {difficulty}")
        return roll >= difficulty