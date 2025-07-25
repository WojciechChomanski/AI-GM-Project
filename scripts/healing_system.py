# file: scripts/healing_system.py

import random

class HealingSystem:
    def attempt_bandage(self, healer, target):
        if not target.alive:
            print(f"{target.name} is dead. Bandaging is pointless.")
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
        roll = random.randint(1, 100)
        total_roll = roll + dexterity_bonus - pain_penalty

        print(f"🩹 {healer.name} attempts bandaging with a roll of {total_roll} (raw roll: {roll}, dexterity: +{dexterity_bonus}, pain: -{pain_penalty}) against difficulty {difficulty}.")
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
                healed = int(character.total_hp * 0.1 * heal_rate)  # Example rest heal
                character.health = min(character.total_hp, character.health + healed)
                print(f"🩹 {character.name} heals {healed} HP (fast healing)!")
            else:
                print(f"⚠️ {character.name} starves—reduced healing.")
                # Apply hunger effects
                hunger_roll = random.randint(1, 100)
                if hunger_roll < 10:
                    print(f"🍖 {character.name} attacks ally in hunger desperation!")
                    # Implement attack