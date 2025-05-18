# ✅ Updated: character.py — dual-layer inventory system with slots and backpack

from armor_system import ArmorPiece

class Character:
    def __init__(self, name, race, total_hp, max_stamina):
        self.name = name
        self.race = race
        self.total_hp = total_hp
        self.max_stamina = max_stamina
        self.stamina = max_stamina
        self.body_parts = self.initialize_body_parts()
        self.alive = True
        self.bleeding = 0
        self.pain_penalty = 0
        self.mobility_penalty = 0
        self.in_combat = False

        # Loadouts
        self.armor = []
        self.armor_weight = 0
        self.inventory_weight = 0
        self.shield_equipped = False
        self.weapon_equipped = True

        # Dual-layer inventory system
        self.equipment_slots = {
            "head": None,
            "chest": None,
            "legs": None,
            "arms": None,
            "main_hand": None,
            "off_hand": None,
            "feet": None,
            "trinket": None
        }
        self.backpack_inventory = []  # list of (item_name, weight)
        self.backpack_capacity = 40  # max weight or space count

        # Weapon
        self.weapon = None
        self.stance = "neutral"

    def initialize_body_parts(self):
        return {
            "left_lower_leg": int(self.total_hp * 0.08),
            "right_lower_leg": int(self.total_hp * 0.08),
            "left_upper_leg": int(self.total_hp * 0.10),
            "right_upper_leg": int(self.total_hp * 0.10),
            "stomach": int(self.total_hp * 0.15),
            "chest": int(self.total_hp * 0.20),
            "left_lower_arm": int(self.total_hp * 0.08),
            "right_lower_arm": int(self.total_hp * 0.08),
            "left_upper_arm": int(self.total_hp * 0.06),
            "right_upper_arm": int(self.total_hp * 0.06),
        }

    def consume_stamina(self, amount):
        self.stamina -= amount
        print(f"⚡ {self.name} loses {amount} stamina! Current stamina: {self.stamina}/{self.max_stamina}")
        self.check_stamina_state()

    def stamina_penalty(self):
        percent = (self.stamina / self.max_stamina) * 100
        if percent > 50:
            return 0
        elif percent > 25:
            return 3
        elif percent > 0:
            return 6
        elif percent >= -30:
            return 10
        else:
            return 20

    def check_stamina_state(self):
        if self.stamina <= -0.3 * self.max_stamina:
            self.collapse()

    def collapse(self):
        print(f"💀 {self.name} collapses from exhaustion and can no longer act!")
        self.alive = False

    def equip_armor(self, armor_piece):
        self.armor.append(armor_piece)
        self.armor_weight += armor_piece.weight

    def get_total_armor(self, damage_type, hit_zone):
        return sum(piece.effective_armor(damage_type) for piece in self.armor if hit_zone in piece.coverage)

    def apply_armor_damage(self, hit_zone, damage_type, incoming_damage):
        protection = self.get_total_armor(damage_type, hit_zone)
        reduced_damage = max(incoming_damage - protection, 0)
        for piece in self.armor:
            if hit_zone in piece.coverage:
                piece.take_damage(damage_type, incoming_damage)
        return reduced_damage

    def get_armor_stamina_penalty(self):
        return sum(piece.stamina_penalty for piece in self.armor)

    def receive_damage(self, damage_amount):
        if not self.alive:
            print(f"{self.name} is already dead.")
            return

        while damage_amount > 0:
            valid_parts = {k: v for k, v in self.body_parts.items() if v > 0}
            if not valid_parts:
                self.die()
                break
            target_part = max(valid_parts, key=valid_parts.get)
            self.body_parts[target_part] -= 1
            damage_amount -= 1
            if self.body_parts[target_part] == 0:
                self.on_part_crippled(target_part)

    def on_part_crippled(self, part):
        print(f"⚠️ {self.name}'s {part.replace('_', ' ')} is crippled!")
        bleed_amount = 5 if part in ["chest", "stomach"] else 2
        self.bleeding += bleed_amount
        self.pain_penalty += 5
        if "leg" in part:
            self.mobility_penalty += 50
            print(f"⛔ {self.name}'s mobility reduced by {self.mobility_penalty}% due to crippled legs!")
        print(f"🩸 {self.name} starts bleeding! Bleed per round: {self.bleeding}")
        print(f"😖 {self.name} suffers pain penalties! Total penalty: {self.pain_penalty}%")

    def bleed_out(self):
        if self.alive and self.bleeding > 0:
            print(f"🩸 {self.name} suffers {self.bleeding} bleeding damage!")
            self.receive_damage(self.bleeding)

    def die(self):
        self.alive = False
        print(f"💀 {self.name} has died from wounds and bleeding.")

    def status_report(self):
        print(f"\nStatus Report for {self.name}:")
        for part, hp in self.body_parts.items():
            print(f"  {part.replace('_', ' ').capitalize()}: {hp} HP")
        print(f"  Bleeding per round: {self.bleeding}")
        print(f"  Pain penalty: {self.pain_penalty}%")
        print(f"  Stamina: {self.stamina}/{self.max_stamina}")

    def has_shield(self):
        return self.shield_equipped

    def wear_shield(self):
        self.shield_equipped = True

    def wear_weapon(self):
        self.weapon_equipped = True

    def apply_dodge_penalty(self):
        total_weight = self.armor_weight + self.inventory_weight
        if total_weight <= 20:
            return 0
        elif total_weight <= 40:
            return -10
        elif total_weight <= 60:
            return -20
        else:
            return -40
