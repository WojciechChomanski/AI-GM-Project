# file: scripts/quest_system.py
import random
import json
import logging
from character import Character

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class QuestSystem:
    def __init__(self):
        self.quests = {
            "steal_breath_key": {
                "faction": "saffron_veil",
                "description": "Steal a Breath-warded key from a Church cleric for Lyssa.",
                "difficulty": 50,
                "reward": {"intel_drop_rate": 0.2, "alignment_increase": 20},
                "penalty": {"reputation_loss": 10, "church_hostility": 15}
            },
            "cursed_bell": {
                "faction": "daughters_drowned_moon",
                "description": "Ring a cursed bell in Cursed Swamps to summon Veil power.",
                "difficulty": 60,
                "reward": {"spell_access": "tide_wail", "alignment_increase": 20},
                "penalty": {"brine_marks": 2, "breath_access": False}
            },
            "forge_defense": {
                "faction": "iron_covenant",
                "description": "Defend an Iron Covenant forge from Veilspawn attack.",
                "difficulty": 55,
                "reward": {"rune_craft": 10, "alignment_increase": 20},
                "penalty": {"willpower_check": 25}
            }
        }

    def start_quest(self, character: Character, quest_name: str, faction_system):
        quest = self.quests.get(quest_name)
        if not quest:
            print(f"❌ Unknown quest: {quest_name}")
            return False
        roll = random.randint(1, 100) + (character.intelligence // 5)
        print(f"📜 {character.name} attempts {quest_name} (roll: {roll} vs difficulty {quest['difficulty']})")
        if roll >= quest["difficulty"]:
            print(f"✅ {character.name} completes {quest_name}!")
            faction_system.align_with_faction(quest["faction"], quest["reward"]["alignment_increase"])
            if "spell_access" in quest["reward"]:
                print(f"🔓 Unlocked spell: {quest['reward']['spell_access']}")
            if quest["faction"] == "saffron_veil":
                character.reputation = max(-100, character.reputation - quest["penalty"]["reputation_loss"])
                print(f"🏛️ {character.name}'s reputation falls by {quest['penalty']['reputation_loss']}!")
            elif quest["faction"] == "daughters_drowned_moon":
                character.status_effects.append({"name": "brine_marks", "count": quest["penalty"]["brine_marks"]})
                print(f"😈 {character.name} gains {quest['penalty']['brine_marks']} Brine Marks!")
            elif quest["faction"] == "iron_covenant" and character.race != "Dwarf":
                if random.randint(1, 100) < quest["penalty"]["willpower_check"]:
                    print(f"⚠️ {character.name} fails Iron Covenant's faith test!")
                    faction_system.align_with_faction("iron_covenant", -10)
            return True
        else:
            print(f"❌ {character.name} fails {quest_name}!")
            return False