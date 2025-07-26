# ✅ Updated: healing_system.py for fast healing with caloric checks

import random
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class HealingSystem:
    def attempt_bandage(self, healer, target):
        if not target.alive:
            print(f"{target.name} is dead. Bandaging is pointless.")
            logging.debug(f"Attempted bandaging on dead target: {target.name}")
            return False

        bleeding_level = target.bleeding
        if bleeding_level <= 3:
            difficulty = 30
        elif bleeding_level <= 6:
            difficulty = 35
        else:
            difficulty = 40

        roll = random.randint(1, 100)
        dexterity_bonus = healer.dexterity // 5
        pain_penalty = min(healer.pain_penalty, 20)
        total_roll = roll + dexterity_bonus - pain_penalty

        print(f"🩹 {healer.name} attempts bandaging with a roll of {total_roll} (raw roll: {roll}, dexterity: +{dexterity_bonus}, pain: -{pain_penalty}) against difficulty {difficulty}.")
        logging.debug(f"Bandage attempt: {healer.name} rolled {total_roll} vs difficulty {difficulty}")
        if total_roll >= difficulty:
            print(f"✅ Bandaging successful! {target.name}'s bleeding is stopped.")
            target.bleeding = 0
            return True
        else:
            print(f"❌ Bandaging failed. {target.name} continues bleeding.")
            return False

    def roll_check(self):
        return random.randint(1, 100)

    def fast_heal(self, character):
        if character.race == "Ogre":
            if character.calories_consumed >= 6000:
                heal_rate = 1.5  # 50% faster
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
                    # Morale check for ally
                    roll = random.randint(1, 100)
                    threshold = (ally.willpower // 5) + 30 - ally.pain_penalty // 2 - ally.stress_level // 10
                    if roll > threshold:
                        print(f"💔 {ally.name} panics from the attack and may flee!")
                        ally.in_combat = False if "elite" not in ally.tags else ally.in_combat
                    logging.debug(f"Hunger attack by {character.name} on {ally.name}: {limb}, 20 damage")