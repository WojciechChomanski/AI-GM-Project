# ✅ Updated: character.py — dual-layer inventory system with slots and backpack

import json
import random
from armors import Armor

class Character:
    def __init__(self):
        self.name = ""
        self.race = ""
        self.total_hp = 0
        self.max_stamina = 0
        self.stamina = 0
        self.bleeding = 0
        self.alive = True
        self.in_combat = False
        self.exhausted = False
        self.last_action = False
        self.armor_weight = 0
        self.inventory_weight = 0
        self.shield_equipped = False
        self.weapon_equipped = False
        self.weapon = {}
        self.armor = []
        self.shield = None
        self.body_parts = {
            "left_lower_leg": 10,
            "right_lower_leg": 10,
            "left_upper_leg": 15,
            "right_upper_leg": 15,
            "stomach": 20,
            "chest": 30,
            "left_lower_arm": 5,
            "right_lower_arm": 5,
            "left_upper_arm": 10,
            "right_upper_arm": 10,
            "head": 15,
            "throat": 5,
            "groin": 5
        }
        self.pain_penalty = 0
        self.mobility_penalty = 0
        self.stance = "neutral"
        self.stamina_cost_modifier = 0

    def receive_damage(self, damage):
        if not self.alive:
            return
        total_damage = max(0, damage)
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
        print(f"😖 {self.name} suffers pain penalties! Total penalty: {self.pain_penalty}%")

    def die(self):
        self.alive = False
        self.in_combat = False
        print(f"💀 {self.name} has died!")

    def consume_stamina(self, amount):
        total_cost = amount + self.stamina_cost_modifier
        self.stamina -= total_cost
        if self.stamina <= 0:
            print(f"⚠️ {self.name} is pushing beyond limits! Stamina: {self.stamina}/{self.max_stamina}")

    def recover_stamina(self, amount):
        if self.stamina < self.max_stamina:
            self.stamina = min(self.stamina + amount, self.max_stamina)
            print(f"⚡ {self.name} recovers {amount} stamina! Current stamina: {self.stamina}/{self.max_stamina}")

    def short_rest(self):
        recovery = self.max_stamina // 5
        self.recover_stamina(recovery)

    def long_rest(self):
        self.stamina = self.max_stamina
        self.pain_penalty = max(0, self.pain_penalty - 10)
        print(f"⏳ {self.name} takes a long rest, fully recovering stamina and reducing pain!")

    def check_stamina_state(self):
        if self.stamina <= -0.3 * self.max_stamina and not self.exhausted:
            print(f"⚠️ {self.name} is critically exhausted! One final action before collapse!")
            self.exhausted = True
            self.last_action = False
        elif self.stamina <= -0.3 * self.max_stamina and self.exhausted and not self.last_action:
            print(f"💀 {self.name} collapses from exhaustion and can no longer act!")
            self.last_action = True

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
            self.weapon["durability"] -= 1
            if self.weapon["durability"] <= 0:
                print(f"⚔️ {self.name}'s weapon breaks!")
                self.weapon_equipped = False
                self.weapon = None

    def apply_dodge_penalty(self):
        self.stamina -= 1
        if self.stamina <= 0:
            print(f"⚠️ {self.name} is too exhausted to dodge effectively!")

    def stamina_penalty(self):
        if self.stamina <= 0:
            return -int(0.1 * abs(self.stamina))
        return 0

    def apply_armor_penalties(self):
        for armor in self.armor:
            if armor.name.startswith("Heavy"):
                self.mobility_penalty += 20
                self.stamina_cost_modifier = 2
                print(f"⚠️ {self.name}'s heavy armor reduces mobility by 20% and increases stamina costs by 2!")
            elif armor.name.startswith("Medium"):
                self.mobility_penalty += 10
                self.stamina_cost_modifier = 1
                print(f"⚠️ {self.name}'s medium armor reduces mobility by 10% and increases stamina costs by 1!")
            else:
                self.stamina_cost_modifier = 0