import random
import logging
from character import Character
from healing_items import HealingItem

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class HealingSystem:
    def __init__(self):
        self.healing_items = {
            "basic_bandage": HealingItem("Basic Bandage", 3, 30, 1),
            "improved_bandage": HealingItem("Improved Bandage", 6, 35, 1),
            "herbal_poultice": HealingItem("Herbal Poultice", 9, 40, 1)
        }

    def attempt_bandage(self, healer: Character, target: Character, item_name: str):
        item = self.healing_items.get(item_name)
        if not item:
            print(f"❌ Unknown healing item: {item_name}")
            return False
        if not item.use():
            return False
        if not target.alive:
            print(f"{target.name} is dead. Bandaging is pointless.")
            logging.debug(f"Attempted bandaging on dead target: {target.name}")
            return False

        bleeding_level = target.bleeding_rate
        difficulty = item.difficulty_threshold
        roll = random.randint(1, 100)
        dexterity_bonus = healer.dexterity // 5
        pain_penalty = min(healer.pain_penalty, 20)
        total_roll = roll + dexterity_bonus - pain_penalty

        print(f"🩹 {healer.name} attempts bandaging with {item.name} (roll: {total_roll}, dexterity: +{dexterity_bonus}, pain: -{pain_penalty}) vs difficulty {difficulty}")
        logging.debug(f"Bandage attempt: {healer.name} rolled {total_roll} vs difficulty {difficulty}")
        if total_roll >= difficulty:
            print(f"✅ Bandaging successful! {target.name}'s bleeding reduced by {item.bleed_stop_amount}.")
            target.bleeding_rate = max(0, target.bleeding_rate - item.bleed_stop_amount)
            return True
        else:
            print(f"❌ Bandaging failed. {target.name} continues bleeding.")
            return False

    def breath_purge(self, healer: Character, target: Character):
        if healer.class_name not in ["Cleric", "Holy_Judge"]:
            print(f"❌ {healer.name} cannot use Breath Purge (Cleric/Holy Judge only).")
            return False
        if healer.stamina < 10:
            print(f"⚡ {healer.name} is too exhausted to cast Breath Purge!")
            return False
        healer.consume_stamina(10)
        target.status_effects = [e for e in target.status_effects if e["name"] not in ["salt_kiss", "taint_mark", "brine_marks"]]
        print(f"✨ {healer.name} purges Veil effects from {target.name}!")
        logging.debug(f"Breath Purge by {healer.name} on {target.name}")
        return True

    def fast_heal(self, character: Character):
        if character.race == "Ogre":
            if character.calories_consumed >= 6000:
                heal_rate = 1.5
                healed = int(character.total_hp * 0.1 * heal_rate)
                character.health = min(character.total_hp, character.health + healed)
                print(f"🩹 {character.name} heals {healed} HP (fast healing)!")
                logging.debug(f"Ogre {character.name} healed {healed} HP with fast healing")
            else:
                print(f"⚠️ {character.name} starves—reduced healing.")
                logging.debug(f"Ogre {character.name} underfed, reduced healing")
                hunger_roll = random.randint(1, 100)
                if hunger_roll < 10 and character.allies:
                    ally = random.choice(character.allies)
                    print(f"🍖 {character.name} attacks {ally.name} in hunger!")
                    limb = random.choice(["left_upper_arm", "right_upper_arm"])
                    ally.take_damage_to_zone(limb, 20)
                    ally.bleeding_rate += 1.0
                    ally.pain_penalty += 10
                    ally.stress_level += 10
                    character.health = min(character.total_hp, character.health + 5)
                    print(f"🩸 {ally.name} bleeds and suffers pain! {character.name} gains 5 HP from flesh!")
                    roll = random.randint(1, 100)
                    threshold = (ally.willpower // 5) + 30 - ally.pain_penalty // 2 - ally.stress_level // 10
                    if roll > threshold:
                        print(f"💔 {ally.name} panics from the attack and may flee!")
                        ally.in_combat = False if "elite" not in ally.tags else ally.in_combat