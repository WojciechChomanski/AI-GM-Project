
# file: scripts/magic_system.py

import random
import json
import sqlite3
from character import Character
from combat_health import CombatHealthManager

class MagicSystem:
    def __init__(self, spells_file="rules/spells.json"):
        self.spells = self.load_spells(spells_file)
        self.db_path = "database/characters.db"

    def load_spells(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def cast_spell(self, caster: Character, target: Character, spell_name: str, caster_health: CombatHealthManager, target_health: CombatHealthManager):
        if caster.gender.lower() != "female":
            print(f"❌ {caster.name} cannot cast spells (male characters restricted to passive items).")
            return False

        spell = self.spells.get(spell_name)
        if not spell:
            print(f"❌ Unknown spell: {spell_name}")
            return False

        if caster.stamina < spell["stamina_cost"]:
            print(f"⚡ {caster.name} is too exhausted to cast {spell['name']}!")
            return False

        if sum(caster.body_parts.values()) <= spell["health_cost"]:
            print(f"🩸 {caster.name} is too weak to cast {spell['name']}!")
            return False

        proficiency = self.get_proficiency(caster.name, spell_name)
        difficulty = spell["difficulty"] - min(proficiency // 5, 5)
        roll = random.randint(1, 100)
        total_roll = roll - caster.pain_penalty - caster.stamina_penalty()

        print(f"✨ {caster.name} rolls {total_roll} to cast {spell['name']} (need {difficulty}+)")

        if total_roll >= difficulty:
            caster.consume_stamina(spell["stamina_cost"])
            caster_health.distribute_damage(spell["health_cost"], "necromantic")
            print(f"🩸 {caster.name} sacrifices {spell['health_cost']} HP to cast {spell['name']}!")

            if spell["type"] == "necromantic":
                damage = spell["damage"] + proficiency // 10
                print(f"💥 {caster.name} hits {target.name} for {damage} {spell['damage_type']} damage!")
                target_health.distribute_damage(damage, spell["damage_type"])
            elif spell["type"] == "prophetic":
                bonus = spell["effect"]["defense_bonus"] + proficiency // 15
                print(f"🌫️ {caster.name} grants {target.name} +{bonus} defense for one round!")

            self.update_proficiency(caster.name, spell_name)

            if random.random() < spell["corruption_chance"]:
                self.add_corruption(caster.name, 1)
                print(f"😈 Corruption seeps into {caster.name}'s soul...")

            return True
        else:
            print(f"❌ {caster.name} fails to cast {spell['name']}!")
            caster.consume_stamina(spell["stamina_cost"] // 2)
            return False

    def use_magic_item(self, user: Character, item_name: str, target: Character):
        items = {
            "potion_vigor": {"stamina_restore": 10},
            "rune_ward": {"defense_bonus": 2}
        }
        item = items.get(item_name)
        if not item:
            print(f"❌ Unknown item: {item_name}")
            return False

        print(f"🧪 {user.name} uses {item_name}!")
        if "stamina_restore" in item:
            user.stamina = min(user.max_stamina, user.stamina + item["stamina_restore"])
            print(f"⚡ {user.name} regains {item['stamina_restore']} stamina!")
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
        cursor.execute("UPDATE characters SET corruption = corruption + ? WHERE name=?", (amount, character_name))
        conn.commit()
        conn.close()
