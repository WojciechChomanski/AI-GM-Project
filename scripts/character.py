# ✅ Updated: character.py — dual-layer inventory system with slots and backpack

import json
import random
import logging
import os
from armors import Armor

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Character:
    def __init__(self):
        self.name = ""
        self.race = ""
        self.gender = ""
        self.class_name = ""
        self.background = ""
        self.total_hp = 0
        self.max_stamina = 0
        self.stamina = 0
        self.bleeding = 0
        self.alive = True
        self.in_combat = False
        self.exhausted = False
        self.last_action = False
        self.combat_count = 0
        self.armor_weight = 0
        self.inventory_weight = 0
        self.mass = 80  # Default human male; loaded from stats.json
        self.shield_equipped = False
        self.weapon_equipped = False
        self.weapon = {}
        self.armor = []
        self.shield = None
        self.body_parts = {
            "left_lower_leg": 2, "right_lower_leg": 2, "left_upper_leg": 4, "right_upper_leg": 4,
            "stomach": 3, "chest": 6, "left_lower_arm": 1, "right_lower_arm": 1,
            "left_upper_arm": 2, "right_upper_arm": 2, "head": 2, "throat": 1, "groin": 1
        }
        self.pain_penalty = 0
        self.mobility_penalty = 0
        self.stance = "neutral"
        self.stamina_cost_modifier = 0
        self.strength = 0
        self.toughness = 0
        self.agility = 0
        self.mobility = 0
        self.dexterity = 0
        self.endurance = 0
        self.intelligence = 0
        self.willpower = 0
        self.perception = 0
        self.charisma = 0
        self.corruption_level = 0
        self.stress_level = 0
        self.weapon_skill = 0
        self.faith = 0
        self.reputation = 0

    def receive_damage(self, damage):
        if not self.alive:
            return
        total_damage = max(0, damage - (self.toughness // 5))
        if total_damage >= sum(hp for hp in self.body_parts.values() if hp > 0):
            self.die()
        else:
            self.distribute_damage(total_damage)

    def distribute_damage(self, damage):
        valid_parts = [part for part, hp in self.body_parts.items() if hp > 0]
        if not valid_parts:
            self.die()
            return
        damage_per_part = max(1, damage // max(1, len(valid_parts) // 2))
        hit_parts = random.sample(valid_parts, min(len(valid_parts), 2))
        for part in hit_parts:
            self.body_parts[part] -= damage_per_part
            if self.body_parts[part] <= 0:
                self.body_parts[part] = 0
                self.on_part_crippled(part)

    def take_damage_to_zone(self, zone, damage):
        if zone in self.body_parts:
            self.body_parts[zone] -= damage
            if self.body_parts[zone] <= 0:
                self.body_parts[zone] = 0
                self.on_part_crippled(zone)
        else:
            print(f"⚠️ Invalid zone: {zone}")

    def on_part_crippled(self, part):
        if part in ["left_lower_leg", "right_lower_leg", "left_upper_leg", "right_upper_leg"]:
            self.mobility_penalty += 25
            print(f"⚠️ {self.name}'s {part.replace('_', ' ')} is crippled!")
            print(f"⛔ {self.name}'s mobility reduced by {self.mobility_penalty}% due to crippled legs!")
        self.pain_penalty += 3
        self.stress_level = min(100, self.stress_level + 5)
        print(f"😖 {self.name} suffers pain penalties! Total penalty: {self.pain_penalty}%")
        print(f"🧠 {self.name}'s stress level rises to {self.stress_level}%")
        self.check_corruption_outburst()

    def check_corruption_outburst(self):
        if self.corruption_level >= 50:
            roll = random.randint(1, 100)
            threshold = self.corruption_level - self.willpower - (self.faith // 2)
            if roll <= threshold:
                print(f"😈 Corruption consumes {self.name}! They lash out uncontrollably!")
                self.reputation = max(-100, self.reputation - 20)
                print(f"🏛️ {self.name}'s reputation falls to {self.reputation} due to their outburst!")

    def die(self):
        self.alive = False
        self.in_combat = False
        print(f"💀 {self.name} has died!")

    def consume_stamina(self, amount):
        total_cost = amount + self.stamina_cost_modifier
        self.stamina -= total_cost
        if self.stamina <= 0:
            print(f"⚠️ {self.name} is pushing beyond limits! Stamina: {self.stamina}/{self.max_stamina}")
            self.stress_level = min(100, self.stress_level + 2)

    def recover_stamina(self, amount):
        if self.stamina < self.max_stamina:
            recovery = amount + (self.endurance // 20)
            self.stamina = min(self.stamina + recovery, self.max_stamina)
            print(f"⚡ {self.name} recovers {recovery} stamina! Current stamina: {self.stamina}/{self.max_stamina}")

    def short_rest(self):
        recovery = self.max_stamina // 5
        self.recover_stamina(recovery)
        self.stress_level = max(0, self.stress_level - 5)

    def long_rest(self):
        self.stamina = self.max_stamina
        self.pain_penalty = max(0, self.pain_penalty - 10)
        self.stress_level = max(0, self.stress_level - 15)
        print(f"⏳ {self.name} takes a long rest, fully recovering stamina and reducing pain/stress!")

    def check_stamina_state(self):
        if self.stamina <= -0.3 * self.max_stamina and not self.exhausted:
            print(f"⚠️ {self.name} is critically exhausted! One final action before collapse!")
            self.exhausted = True
            self.last_action = False
        elif self.stamina <= -0.3 * self.max_stamina and self.exhausted and not self.last_action:
            print(f"💀 {self.name} collapses from exhaustion and can no longer act!")
            self.last_action = True
            self.in_combat = False

    def has_shield(self):
        return self.shield_equipped and self.shield is not None

    def wear_shield(self):
        if self.shield:
            self.shield["durability"] -= 1
            if self.shield["durability"] <= 0:
                print(f"🛡️ {self.name}'s shield breaks!")
                self.shield_equipped = False
                self.shield = None

    def wear_weapon(self):
        if self.weapon_equipped and self.weapon:
            durability = self.weapon.get("durability", 50)
            self.weapon["durability"] = durability - 1
            if self.weapon["durability"] <= 0:
                print(f"⚔️ {self.name}'s weapon breaks!")
                self.weapon_equipped = False
                self.weapon = None

    def apply_dodge_penalty(self):
        dodge_cost = 1 - (self.agility // 20)
        self.stamina -= max(1, dodge_cost)
        if self.stamina <= 0:
            print(f"⚠️ {self.name} is too exhausted to dodge effectively!")

    def stamina_penalty(self):
        if self.stamina <= 0:
            return -int(0.1 * abs(self.stamina))
        return 0

    def apply_armor_penalties(self):
        total_weight = sum(getattr(armor, 'weight', 0) for armor in self.armor)
        self.mobility_penalty = 0
        self.stamina_cost_modifier = 0

        for armor in self.armor:
            weight = getattr(armor, 'weight', 0)
            if weight >= 25:
                self.mobility_penalty += int(weight / 5)
                self.stamina_cost_modifier += int(weight / 10)
                print(f"⚠️ {self.name}'s {armor.name} (weight {weight}) reduces mobility by {int(weight / 5)}% and increases stamina costs by {int(weight / 10)}!")
            elif weight >= 15:
                self.mobility_penalty += int(weight / 7)
                self.stamina_cost_modifier += int(weight / 15)
                print(f"⚠️ {self.name}'s {armor.name} (weight {weight}) reduces mobility by {int(weight / 7)}% and increases stamina costs by {int(weight / 15)}!")
            else:
                self.stamina_cost_modifier += 0
                print(f"🛡️ {self.name}'s {armor.name} (weight {weight}) has minimal impact on mobility and stamina.")

    def athletics_check(self, difficulty):
        roll = random.randint(1, 100)
        pain_penalty = min(self.pain_penalty, 20)
        total_roll = roll + (self.agility // 5) - self.mobility_penalty - pain_penalty
        print(f"🏃 {self.name} attempts athletics check (needs {difficulty}+): rolled {roll} + {self.agility // 5} (Agility) - {self.mobility_penalty} (Mobility Penalty) - {pain_penalty} (Pain) = {total_roll}")
        return total_roll >= difficulty

    def progress_stat(self, stat, amount):
        current = getattr(self, stat, 0)
        max_stat = load_stats(self.race, self.gender)["max_stats"].get(stat, 50)
        new_value = min(current + amount, max_stat)
        setattr(self, stat, new_value)
        print(f"📈 {self.name}'s {stat} increases by {amount} to {new_value}!")

    def can_wield_weapon(self, weapon):
        min_str = weapon.get("min_STR", 10)
        size_class = weapon.get("size_class", "medium")
        grip_size = weapon.get("grip_size", "standard")

        if self.strength < min_str:
            print(f"⚠️ {self.name} lacks strength to wield {weapon['name']} (needs {min_str} STR)!")
            return False

        # Mass/Grip Check
        if self.mass > 150 and size_class == "small":  # Ogres can't use small weapons
            print(f"⚠️ {self.name}'s grip too large for {weapon['name']}!")
            return False
        elif self.mass < 50 and size_class == "large":  # Small races can't use large
            print(f"⚠️ {weapon['name']} too heavy for {self.name}'s size!")
            return False

        return True

def load_stats(race, gender):
    path = os.path.join(os.path.dirname(__file__), "../rules/stats.json")
    with open(path, 'r', encoding='utf-8') as f:
        stats_data = json.load(f)
    key = f"{race}_{gender}"
    return stats_data.get(key, {"starting_stats": {}, "max_stats": {}})