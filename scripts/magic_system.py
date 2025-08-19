import random
import json
import sqlite3
import logging
from character import Character
from combat_health import CombatHealthManager

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MagicSystem:
    def __init__(self, spells_file="rules/spells.json"):
        self.spells = self.load_spells(spells_file)
        self.db_path = "database/characters.db"

    def load_spells(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "divine_verdict": {
                    "type": "breath",
                    "damage": 15,
                    "damage_type": "holy",
                    "bonus_vs_corrupted": 10,
                    "stamina_cost": 8,
                    "overload_chance": 0.01,
                    "description": "Deals 15 holy damage, +10 vs corrupted, 1% Breath Overload risk."
                },
                "veil_whisper": {
                    "type": "veil",
                    "effect": {"defense_bonus": 5},
                    "stamina_cost": 6,
                    "corruption_risk": 0.1,
                    "taint_mark": {"hunt_check_bonus": 5},
                    "description": "Grants ally +5 defense, leaves taint_mark (+5 enemy hunt_check)."
                },
                "sacrificial_pact": {
                    "type": "veil",
                    "stamina_cost": 10,
                    "corruption_risk": 0.15,
                    "effects": {
                        "power_bonus": 20,
                        "aging_rate": 0.5,
                        "sterility": True
                    },
                    "description": "Ritual sacrifices fertility for +20 power, halved aging rate, +0.15 corruption risk."
                },
                "tide_wail": {
                    "type": "veil",
                    "effect": {"fear_intensity": 15},
                    "stamina_cost": 15,
                    "corruption_risk": 0.15,
                    "brine_marks": 1,
                    "description": "AOE fear, +15 intensity, adds Brine Marks."
                },
                "veil_caress": {
                    "type": "veil",
                    "effect": {"charm_count": 2},
                    "stamina_cost": 15,
                    "corruption_risk": 0.15,
                    "taint_mark": {"hunt_check_bonus": 5},
                    "description": "Charms up to 2 targets, leaves taint_mark."
                },
                "rune_trap": {
                    "type": "rune",
                    "damage": 10,
                    "effect": {"immobilize_chance": 0.4},
                    "stamina_cost": 8,
                    "description": "Deploys a rune trap, deals 10 damage, 40% chance to immobilize."
                },
                "salt_kiss": {
                    "type": "veil",
                    "effect": {"max_hp_drain": 2},
                    "stamina_cost": 8,
                    "corruption_risk": 0.1,
                    "brine_marks": 1,
                    "description": "Drains 2 HP/round unless Breath-purified, adds Brine Marks."
                }
            }

    def cast_spell(self, caster: Character, target: Character, spell_name: str, caster_health: CombatHealthManager, target_health: CombatHealthManager):
        spell = self.spells.get(spell_name)
        if not spell:
            print(f"❌ Unknown spell: {spell_name}")
            return False

        # Check restrictions
        if spell["type"] == "breath" and (caster.race != "Human" or caster.gender != "Male"):
            print(f"❌ {caster.name} cannot cast Breath spell {spell_name} (male Human only).")
            return False
        if spell["type"] == "veil" and (caster.gender != "Female" or caster.race not in ["Human", "Elf"]):
            print(f"❌ {caster.name} cannot cast Veil spell {spell_name} (female Human/Elf only).")
            return False
        if spell["type"] == "rune" and caster.race != "Dwarf":
            print(f"❌ {caster.name} cannot use rune ability {spell_name} (Dwarf only).")
            return False

        # Stamina check
        if caster.stamina < spell["stamina_cost"]:
            print(f"⚡ {caster.name} is too exhausted to cast {spell_name}!")
            return False

        # Proficiency-based roll
        proficiency = self.get_proficiency(caster.name, spell_name)
        difficulty = 30 - min(proficiency // 5, 5)
        roll = random.randint(1, 100)
        total_roll = roll - caster.pain_penalty - caster.stamina_penalty()

        print(f"✨ {caster.name} rolls {total_roll} to cast {spell_name} (need {difficulty}+)")

        if total_roll >= difficulty:
            caster.consume_stamina(spell["stamina_cost"])
            print(f"✅ {caster.name} successfully casts {spell_name}!")

            if spell_name == "divine_verdict":
                damage = spell["damage"]
                if target.corruption_level > 0:
                    damage += spell["bonus_vs_corrupted"]
                target_health.take_damage_to_zone("chest", damage, spell["damage_type"])
                if random.random() < spell["overload_chance"]:
                    caster.status_effects.append({"name": "breath_overload", "duration": 3, "stamina_penalty": -5})
                    print(f"⚠️ {caster.name} suffers Breath Overload (-5 stamina, 3 rounds).")
            elif spell_name == "veil_whisper":
                target.defense_bonus = spell["effect"]["defense_bonus"]
                target.status_effects.append({"name": "taint_mark", "hunt_check_bonus": 5})
                caster.corruption_level = min(100, caster.corruption_level + (5 if random.random() < spell["corruption_risk"] else 0))
                print(f"😈 {caster.name}'s corruption: {caster.corruption_level}%")
            elif spell_name == "sacrificial_pact":
                caster.power_bonus = spell["effects"]["power_bonus"]
                caster.aging_rate = spell["effects"]["aging_rate"]
                caster.status_effects.append({"name": "sterility", "charisma_penalty": -10})
                caster.corruption_level = min(100, caster.corruption_level + (15 if random.random() < spell["corruption_risk"] else 0))
                print(f"😈 {caster.name} completes Sacrificial Pact, gains power but sterility. Corruption: {caster.corruption_level}%")
            elif spell_name == "tide_wail":
                for ally in caster.allies + [caster]:
                    ally.status_effects.append({"name": "fear", "intensity": spell["effect"]["fear_intensity"], "duration": 1})
                caster.corruption_level = min(100, caster.corruption_level + (5 if random.random() < spell["corruption_risk"] else 0))
                caster.status_effects.append({"name": "brine_marks", "count": spell["brine_marks"]})
                print(f"😈 {caster.name}'s corruption: {caster.corruption_level}%, Brine Marks added.")
            elif spell_name == "veil_caress":
                charmed = min(spell["effect"]["charm_count"], len(caster.allies))
                for _ in range(charmed):
                    if caster.allies:
                        ally = random.choice(caster.allies)
                        ally.status_effects.append({"name": "charmed", "duration": 1})
                        ally.status_effects.append({"name": "taint_mark", "hunt_check_bonus": 5})
                caster.corruption_level = min(100, caster.corruption_level + (5 if random.random() < spell["corruption_risk"] else 0))
                print(f"😈 {caster.name}'s corruption: {caster.corruption_level}%")
            elif spell_name == "rune_trap":
                target_health.take_damage_to_zone("legs", spell["damage"], "blunt")
                if random.random() < spell["effect"]["immobilize_chance"]:
                    target.status_effects.append({"name": "immobilized", "duration": 1, "mobility_penalty": 20})
                    print(f"🪤 {target.name} is immobilized by {caster.name}'s rune trap!")
            elif spell_name == "salt_kiss":
                target.status_effects.append({"name": "salt_kiss", "max_hp_drain": 2, "duration": 3})
                caster.corruption_level = min(100, caster.corruption_level + (5 if random.random() < spell["corruption_risk"] else 0))
                caster.status_effects.append({"name": "brine_marks", "count": spell["brine_marks"]})
                print(f"😈 {caster.name}'s corruption: {caster.corruption_level}%, Brine Marks added.")
            self.update_proficiency(caster.name, spell_name)
            return True
        else:
            print(f"❌ {caster.name} fails to cast {spell_name}!")
            caster.consume_stamina(spell["stamina_cost"] // 2)
            return False

    def use_magic_item(self, user: Character, item_name: str, target: Character):
        items = {
            "potion_vigor": {"stamina_restore": 10},
            "rune_ward": {"defense_bonus": 2},
            "moonbloom_elixir": {
                "stress_relief": -20,
                "secret_spill_chance": 0.3,
                "addiction_risk": 0.15,
                "description": "Reduces stress, risks addiction and secret spilling."
            }
        }
        item = items.get(item_name)
        if not item:
            print(f"❌ Unknown item: {item_name}")
            return False

        print(f"🧪 {user.name} uses {item_name}!")
        if "stamina_restore" in item:
            user.stamina = min(user.max_stamina, user.stamina + item["stamina_restore"])
            print(f"⚡ {user.name} regains {item['stamina_restore']} stamina!")
        if "defense_bonus" in item:
            target.defense_bonus = item["defense_bonus"]
            print(f"🛡️ {target.name} gains +{item['defense_bonus']} defense!")
        if "stress_relief" in item:
            user.stress_level = max(0, user.stress_level + item["stress_relief"])
            print(f"😌 {user.name} reduces stress by {abs(item['stress_relief'])}!")
            if random.random() < item["secret_spill_chance"]:
                print(f"🗣️ {user.name} spills secrets under Moonbloom's influence!")
            if random.random() < item["addiction_risk"]:
                user.status_effects.append({"name": "moonbloom_addiction", "duration": 5, "stress_penalty": 5})
                print(f"⚠️ {user.name} risks addiction to Moonbloom Elixir!")
        return True

    def get_proficiency(self, character_name, spell_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS spell_proficiency (character_name TEXT, spell_name TEXT, proficiency INTEGER, PRIMARY KEY (character_name, spell_name))")
        cursor.execute("SELECT proficiency FROM spell_proficiency WHERE character_name=? AND spell_name=?", (character_name, spell_name))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def update_proficiency(self, character_name, spell_name):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO spell_proficiency (character_name, spell_name, proficiency) VALUES (?, ?, 0)", (character_name, spell_name))
        cursor.execute("UPDATE spell_proficiency SET proficiency = proficiency + 1 WHERE character_name=? AND spell_name=?", (character_name, spell_name))
        conn.commit()
        conn.close()

    def add_corruption(self, character_name, amount):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE characters SET corruption_level = corruption_level + ? WHERE name=?", (amount, character_name))
        conn.commit()
        conn.close()