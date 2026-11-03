import random
import logging
from character import Character
from healing_items import HealingItem
import bleeding

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class HealingSystem:
    def __init__(self):
        self.healing_items = {
            "basic_bandage": HealingItem("Basic Bandage", 3, 30, 1),
            "improved_bandage": HealingItem("Improved Bandage", 6, 35, 1),
            "herbal_poultice": HealingItem("Herbal Poultice", 9, 40, 1)
        }

    def attempt_bandage(self, healer: Character, target: Character, item_name: str = "basic_bandage"):
        """One bandage attempt on the target's REAL wound list (CombatHealthManager.bleeding_wounds).
        Basic stops up to 3 HP/round (DC 30), Improved 6 (DC 35), Herbal Poultice 9 (DC 40);
        see docs/BLEEDING.md. first_aid.py delegates here, so there is one bandage rule."""
        item = self.healing_items.get(item_name)
        if not item:
            print(f"❌ Unknown healing item: {item_name}")
            return False
        return bleeding.attempt_bandage(healer, target, item)

    VEIL_EFFECTS = ("salt_kiss", "taint_mark", "brine_marks")

    def breath_purge(self, healer: Character, targets, trigger="just_verdict"):
        """PASSIVE Breath (core_rules: no active magic for men). There is no action, no stamina cost.
        It fires on its own for a Holy Judge at full Breath (knight.breath_state: Virtue >= 70, high Piety,
        low Corruption) right after a just Final_Verdict (holy_judge.json Purge_Verdict), clearing Veil
        effects from the given allies. Cleric: on hold (redesign pending), so nothing happens.
        Returns the names of allies cleared."""
        import knight
        if getattr(healer, "class_name", None) != "Holy_Judge" or trigger != "just_verdict":
            return []
        if knight.breath_state(getattr(healer, "virtue", 0), getattr(healer, "piety", 0),
                               getattr(healer, "corruption_level", 0)) != "full":
            return []
        if not isinstance(targets, (list, tuple)):
            targets = [targets]
        cleared = []
        for t in targets:
            before = len(t.status_effects)
            t.status_effects = [e for e in t.status_effects if e["name"] not in self.VEIL_EFFECTS]
            if len(t.status_effects) < before:
                cleared.append(t.name)
        if cleared:
            logging.debug(f"Passive Purge_Verdict by {healer.name}: {cleared}")
        return cleared

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