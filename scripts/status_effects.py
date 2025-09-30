import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class StatusEffects:
    def __init__(self, character):
        self.character = character
        self.effects = character.status_effects if hasattr(character, 'status_effects') else []

    def apply_effect(self, effect):
        self.effects.append(effect)
        logging.debug(f"Applied {effect['name']} to {self.character.name}")

    def update_effects(self):
        for effect in self.effects[:]:
            if effect.get("duration", 0) > 0:
                effect["duration"] -= 1
                if effect["name"] == "breath_overload":
                    self.character.stamina = max(0, self.character.stamina - effect["stamina_penalty"])
                    print(f"⚠️ {self.character.name} suffers Breath Overload, stamina: {self.character.stamina}")
                elif effect["name"] == "sterility":
                    self.character.charisma_penalty = effect.get("charisma_penalty", 0)
                elif effect["name"] == "taint_mark":
                    self.character.hunt_check_bonus = effect.get("hunt_check_bonus", 0)
                if effect["duration"] == 0:
                    self.effects.remove(effect)
                    print(f"🛑 {effect['name']} expires for {self.character.name}")
                    if effect["name"] == "sterility":
                        self.character.charisma_penalty = 0
                    elif effect["name"] == "taint_mark":
                        self.character.hunt_check_bonus = 0
        self.character.status_effects = self.effects

    def has_effect(self, effect_name):
        return any(effect["name"] == effect_name for effect in self.effects)