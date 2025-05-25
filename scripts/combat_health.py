# ✅ Updated: combat_health.py to support damage_type

import random

class CombatHealthManager:
    def __init__(self, character):
        self.character = character
        self.starting_hp = sum(character.body_parts.values())
        self.round_counter = 0
        self.bleeding_wounds = []

    def apply_bleeding(self):
        if not self.bleeding_wounds:
            self.character.bleeding = 0
            return
        total_bleeding = 0
        for wound in self.bleeding_wounds[:]:
            total_bleeding += wound["amount"]
            wound["duration"] -= 1
            if wound["duration"] <= 0:
                self.bleeding_wounds.remove(wound)
        total_bleeding = min(total_bleeding, 8.0)
        self.character.bleeding = round(total_bleeding, 1)
        if total_bleeding > 0:
            self.inflict_bleed_damage()

    def inflict_bleed_damage(self):
        print(f"🩸 {self.character.name} suffers {self.character.bleeding} bleeding damage!")
        self.character.receive_damage(int(self.character.bleeding))
        self.check_blood_loss_collapse()

    def add_bleeding_wound(self, severity, is_critical=False):
        if severity == "light":
            amount, duration = 0.03, 2
        elif severity == "medium":
            amount, duration = 0.3, 4
        else:
            amount, duration = 0.6, 6
        if is_critical:
            amount *= 1.5
            duration += 1
        self.bleeding_wounds.append({"amount": amount, "duration": duration})
        total_bleeding = sum(w["amount"] for w in self.bleeding_wounds)
        self.character.bleeding = round(min(total_bleeding, 8.0 if not is_critical else 16.0), 1)

    def apply_pain(self):
        if self.character.pain_penalty >= 30:
            print(f"⚠️ {self.character.name} is overwhelmed by pain penalties!")
            self.check_auto_collapse()

    def check_blood_loss_collapse(self):
        blood_loss = self.starting_hp - sum(max(hp, 0) for hp in self.character.body_parts.values())
        blood_loss_percent = (blood_loss / self.starting_hp) * 100
        if blood_loss_percent >= 33 and self.character.alive:
            print(f"💀 {self.character.name} collapses from massive blood loss and falls unconscious!")
            self.character.alive = True
            self.character.in_combat = False
            self.character.exhausted = True
            self.character.last_action = True

    def check_auto_collapse(self):
        crippled = [part for part, hp in self.character.body_parts.items() if hp <= 0]
        if len(crippled) >= 3:
            print(f"💀 {self.character.name} collapses from severe injuries!")
            self.character.alive = True
            self.character.in_combat = False
            self.character.exhausted = True
            self.character.last_action = True
            return True
        collapse_chance = self.character.pain_penalty - 30
        if collapse_chance > 0:
            roll = random.randint(1, 100)
            print(f"🧠 Collapse Check: Rolled {roll} vs Threshold {collapse_chance}")
            if roll <= collapse_chance:
                print(f"💀 {self.character.name} collapses from overwhelming pain!")
                self.character.alive = True
                self.character.in_combat = False
                self.character.exhausted = True
                self.character.last_action = True
                return True
        return False

    def distribute_damage(self, base_damage, damage_type, critical=False):
        if not self.character.alive:
            return
        valid_parts = {k: v for k, v in self.character.body_parts.items() if v > 0}
        parts = list(valid_parts.keys())
        if not parts:
            self.character.die()
            return
        damage_per_part = max(1, base_damage // max(1, len(parts) // 2))
        hit_parts = random.sample(parts, min(len(parts), 2))
        for part in hit_parts:
            self.character.body_parts[part] -= damage_per_part
            if self.character.body_parts[part] <= 0:
                self.character.body_parts[part] = 0
                self.character.on_part_crippled(part)
            severity = "light" if base_damage <= 5 else "medium" if base_damage <= 10 else "heavy"
            self.add_bleeding_wound(severity, is_critical=critical and part in ["chest", "stomach", "left_upper_leg", "right_upper_leg"])

    def take_damage_to_zone(self, zone, damage_amount, damage_type, critical=False):
        if not self.character.alive:
            return
        if zone in self.character.body_parts:
            self.character.body_parts[zone] -= damage_amount
            if self.character.body_parts[zone] <= 0:
                self.character.body_parts[zone] = 0
                self.character.on_part_crippled(zone)
            severity = "light" if damage_amount <= 5 else "medium" if damage_amount <= 10 else "heavy"
            self.add_bleeding_wound(severity, is_critical=critical and zone in ["chest", "stomach", "left_upper_leg", "right_upper_leg"])
        else:
            print(f"⚠️ Invalid zone: {zone}")

    def bleed_out(self):
        self.apply_bleeding()