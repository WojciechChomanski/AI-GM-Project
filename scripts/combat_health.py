# ✅ Updated: combat_health.py to support damage_type

class CombatHealthManager:
    def __init__(self, character):
        self.character = character
        self.starting_hp = sum(character.body_parts.values())
        self.round_counter = 0

    def apply_bleeding(self):
        if self.character.bleeding > 0:
            self.round_counter += 1
            if self.character.bleeding <= 3:
                if self.round_counter % 3 == 0:
                    self.inflict_bleed_damage()
            elif self.character.bleeding <= 6:
                if self.round_counter % 2 == 0:
                    self.inflict_bleed_damage()
            else:
                self.inflict_bleed_damage()

    def inflict_bleed_damage(self):
        print(f"🩸 {self.character.name} suffers {self.character.bleeding} bleeding damage!")
        self.character.receive_damage(self.character.bleeding)
        self.check_blood_loss_collapse()

    def apply_pain(self):
        if self.character.pain_penalty >= 30:
            print(f"⚠️ {self.character.name} is overwhelmed by pain penalties!")
            self.check_auto_collapse()

    def check_blood_loss_collapse(self):
        blood_loss = self.starting_hp - sum(max(hp, 0) for hp in self.character.body_parts.values())
        blood_loss_percent = (blood_loss / self.starting_hp) * 100
        if blood_loss_percent >= 33 and self.character.alive:
            print(f"💀 {self.character.name} collapses from massive blood loss and falls unconscious!")
            self.character.alive = False

    def check_auto_collapse(self):
        crippled = [part for part, hp in self.character.body_parts.items() if hp <= 0]
        if len(crippled) >= 3:
            print(f"💀 {self.character.name} collapses from severe injuries!")
            self.character.alive = False
            return True

        collapse_chance = self.character.pain_penalty - 30
        if collapse_chance > 0:
            from random import randint
            roll = randint(1, 100)
            print(f"🧠 Collapse Check: Rolled {roll} vs Threshold {collapse_chance}")
            if roll <= collapse_chance:
                print(f"💀 {self.character.name} collapses from overwhelming pain!")
                self.character.alive = False
                return True

        return False

    def distribute_damage(self, base_damage, damage_type):
        if not self.character.alive:
            return

        valid_parts = {k: v for k, v in self.character.body_parts.items() if v > 0}
        parts = list(valid_parts.keys())

        if not parts:
            self.character.die()
            return

        damage_per_part = max(1, base_damage // len(parts))

        for part in parts:
            self.character.body_parts[part] -= damage_per_part
            if self.character.body_parts[part] <= 0:
                self.character.body_parts[part] = 0
                self.character.on_part_crippled(part)

    def take_damage_to_zone(self, zone, damage_amount, damage_type):
        if not self.character.alive:
            return

        if zone in self.character.body_parts:
            self.character.body_parts[zone] -= damage_amount
            if self.character.body_parts[zone] <= 0:
                self.character.body_parts[zone] = 0
                self.character.on_part_crippled(zone)
        else:
            print(f"⚠️ Invalid zone: {zone}")

    def bleed_out(self):
        self.apply_bleeding()