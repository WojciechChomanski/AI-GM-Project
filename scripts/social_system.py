import random
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class SocialSystem:
    def __init__(self, character):
        self.character = character

    def charisma_check(self, difficulty):
        charisma = self.character.charisma + getattr(self.character, "charisma_penalty", 0)
        roll = random.randint(1, 100) + (charisma // 5)
        print(f"🎭 {self.character.name} charisma check: rolled {roll} vs difficulty {difficulty}")
        logging.debug(f"Charisma check for {self.character.name}: {roll} vs {difficulty}")
        return roll >= difficulty

    def interact_with_npc(self, npc, action="persuade"):
        difficulty = 50  # Base difficulty
        if any(effect["name"] == "sterility" for effect in self.character.status_effects):
            difficulty += 10  # Social stigma for sterility
        success = self.charisma_check(difficulty)
        if success:
            print(f"✅ {self.character.name} successfully {action}s {npc.name}!")
        else:
            print(f"❌ {self.character.name} fails to {action} {npc.name}.")
        return success