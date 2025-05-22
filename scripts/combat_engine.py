import random
from combat_health import CombatHealthManager
from character import Character
from stance_logic import apply_stance_modifiers, get_stamina_cost_modifier
from maneuver_handler import ManeuverHandler

class CombatEngine:
    def __init__(self):
        self.maneuvers = ManeuverHandler()
        # Armor penetration modifiers: {weapon_type: penetration_value}
        # Penetration reduces armor effectiveness (e.g., 0.3 = 30% reduction)
        self.armor_penetration = {
            "warhammer": 0.3,    # 30% penetration (good against armor, less versatile)
            "flanged_mace": 0.25, # 25% penetration (similar to warhammer but lighter)
            "axe": 0.15,         # 15% penetration (better than swords, less than maces)
            "sword": 0.05,       # 5% penetration (versatile but not armor-piercing)
            "claymore": 0.05,    # 5% penetration (versatile, like sword)
            "dagger": 0.1,       # 10% penetration (fast but situational)
            "three_edged_dagger": 0.4, # 40% penetration (designed for armor weak points, close combat)
            "halberd": 0.2,      # 20% penetration (good reach, decent against armor)
            "saber": 0.05,       # 5% penetration (like sword, slashing focus)
            "rapier": 0.15,      # 15% penetration (piercing, good for weak points)
            "spear": 0.2,        # 20% penetration (piercing, decent against armor)
            "bow": 0.1,          # 10% penetration (piercing, arrows)
            "crossbow": 0.25,    # 25% penetration (piercing, bolts, better against armor)
            "flintlock": 0.35    # 35% penetration (primitive gunpowder, high penetration)
        }
        # Durability damage multiplier: {damage_type: multiplier}
        # Blunt weapons cause more durability loss to armor
        self.durability_damage_multiplier = {
            "blunt": 1.5,    # 50% more durability damage (warhammer, flanged mace)
            "slashing": 1.0, # Normal durability damage (sword, saber)
            "piercing": 0.8  # Less durability damage (arrows, spears, focus on penetration)
        }

    def attack_roll(self, attacker, defender, weapon_damage, damage_type, attacker_health, defender_health, aimed_zone=None):
        attack_roll = random.randint(1, 100)
        defense_roll = random.randint(1, 100)

        # ✅ Extract stance + weapon
        attacker_stance = getattr(attacker, "stance", "neutral")
        defender_stance = getattr(defender, "stance", "neutral")
        weapon_type = attacker.weapon.get("type") if attacker.weapon else "none"

        # ✅ Apply maneuver bonuses (e.g. Zwerchhau, Absetzen)
        maneuver_bonus = self.maneuvers.get_bonus_effects(weapon_type, attacker_stance, trigger="always")

        # ✅ Apply stance + maneuver bonuses
        attack_roll += apply_stance_modifiers(attacker, defender, attacker_stance, "attack")
        attack_roll += maneuver_bonus.get("attack_bonus", 0)

        defense_roll += apply_stance_modifiers(defender, attacker, defender_stance, "defense")
        defense_roll += maneuver_bonus.get("defense_bonus", 0)

        if aimed_zone:
            print(f"🎯 {attacker.name} attempts an aimed strike at {aimed_zone}!")
            attack_roll -= 30

        attack_roll -= attacker.stamina_penalty() + attacker.pain_penalty
        defense_roll -= defender.stamina_penalty() + defender.pain_penalty

        defense_type = self.select_defense_type(defender)

        print(f"\n⚔️ {attacker.name} is in {attacker_stance.upper()} stance")
        print(f"🛡️ {defender.name} is in {defender_stance.upper()} stance")
        print(f"⚔️ {attacker.name} rolls {attack_roll} to attack!")
        print(f"🛡️ {defender.name} rolls {defense_roll} to defend! ({defense_type})")

        if attack_roll >= 95:
            print("🔥 Critical Hit!")
            self.apply_critical_hit(attacker, defender, weapon_damage, damage_type, attacker_health, defender_health, aimed_zone)
        elif attack_roll <= 5:
            print("💀 Critical Miss!")
            self.apply_critical_miss(attacker, defender)
        elif attack_roll > defense_roll:
            print(f"✅ {attacker.name} hits {defender.name}!")
            self.apply_damage(attacker, defender, weapon_damage, damage_type, defender_health, aimed_zone)
        else:
            print(f"❌ {attacker.name} misses or {defender.name} successfully defends!")
            self.apply_defense_wear(defender, defense_type)

        # ✅ Apply stamina cost (base + stance + maneuver modifier)
        atk_cost = 5 + get_stamina_cost_modifier(attacker_stance, "offensive") + maneuver_bonus.get("stamina_cost_modifier", 0)
        def_cost = 3 + get_stamina_cost_modifier(defender_stance, "defensive")

        attacker.consume_stamina(atk_cost)
        defender.consume_stamina(def_cost)

    def apply_damage(self, attacker, defender, base_damage, damage_type, defender_health, aimed_zone):
        # ✅ Apply armor penetration and durability damage based on weapon type and damage type
        weapon_type = attacker.weapon.get("type") if attacker.weapon else "none"
        penetration_factor = self.armor_penetration.get(weapon_type, 0.0)
        durability_multiplier = self.durability_damage_multiplier.get(damage_type, 1.0)

        if aimed_zone:
            print(f"💥 {attacker.name} deals {base_damage} ({damage_type}) damage to {defender.name}'s {aimed_zone}!")
            # Apply armor durability reduction for aimed strikes
            remaining_damage = base_damage
            for armor in defender.armor:
                if aimed_zone in armor.coverage:
                    # Adjust damage for armor penetration
                    original_protection = armor.armor_rating.get(damage_type, 0)
                    reduced_protection = original_protection * (1 - penetration_factor)
                    adjusted_damage = max(0, base_damage - reduced_protection)
                    # Apply durability multiplier for damage type
                    armor.current_durability -= max(1, int(adjusted_damage * 0.2 * durability_multiplier))
                    if armor.current_durability < 0:
                        armor.current_durability = 0
                    remaining_damage = armor.absorb_damage(adjusted_damage, damage_type)
            defender_health.take_damage_to_zone(aimed_zone, remaining_damage, damage_type)
        else:
            print(f"💥 {attacker.name} deals {base_damage} ({damage_type}) damage across {defender.name}'s body!")
            # Apply armor durability reduction across all armor pieces
            remaining_damage = base_damage
            for armor in defender.armor:
                # Adjust damage for armor penetration
                original_protection = armor.armor_rating.get(damage_type, 0)
                reduced_protection = original_protection * (1 - penetration_factor)
                adjusted_damage = max(0, base_damage / len(defender.armor) if defender.armor else base_damage - reduced_protection)
                # Apply durability multiplier for damage type
                armor.current_durability -= max(1, int(adjusted_damage * 0.2 * durability_multiplier))
                if armor.current_durability < 0:
                    armor.current_durability = 0
                remaining_damage = armor.absorb_damage(adjusted_damage, damage_type)
            defender_health.distribute_damage(remaining_damage, damage_type)

    def apply_critical_hit(self, attacker, defender, base_damage, damage_type, attacker_health, defender_health, aimed_zone):
        critical_damage = base_damage * 2
        # ✅ Apply armor penetration and durability damage for critical hits
        weapon_type = attacker.weapon.get("type") if attacker.weapon else "none"
        penetration_factor = self.armor_penetration.get(weapon_type, 0.0)
        durability_multiplier = self.durability_damage_multiplier.get(damage_type, 1.0)

        if aimed_zone:
            print(f"💥💥 Critical Aimed Strike! {attacker.name} critically strikes {defender.name}'s {aimed_zone} for {critical_damage} {damage_type} damage!")
            # Apply armor durability reduction for critical aimed strikes
            remaining_damage = critical_damage
            for armor in defender.armor:
                if aimed_zone in armor.coverage:
                    # Adjust damage for armor penetration
                    original_protection = armor.armor_rating.get(damage_type, 0)
                    reduced_protection = original_protection * (1 - penetration_factor)
                    adjusted_damage = max(0, critical_damage - reduced_protection)
                    # Apply durability multiplier for damage type
                    armor.current_durability -= max(1, int(adjusted_damage * 0.2 * durability_multiplier))
                    if armor.current_durability < 0:
                        armor.current_durability = 0
                    remaining_damage = armor.absorb_damage(adjusted_damage, damage_type)
            defender_health.take_damage_to_zone(aimed_zone, remaining_damage, damage_type)
        else:
            print(f"💥💥 Critical Strike! {attacker.name} deals {critical_damage} critical {damage_type} damage across {defender.name}'s body!")
            # Apply armor durability reduction across all armor pieces
            remaining_damage = critical_damage
            for armor in defender.armor:
                # Adjust damage for armor penetration
                original_protection = armor.armor_rating.get(damage_type, 0)
                reduced_protection = original_protection * (1 - penetration_factor)
                adjusted_damage = max(0, critical_damage / len(defender.armor) if defender.armor else critical_damage - reduced_protection)
                # Apply durability multiplier for damage type
                armor.current_durability -= max(1, int(adjusted_damage * 0.2 * durability_multiplier))
                if armor.current_durability < 0:
                    armor.current_durability = 0
                remaining_damage = armor.absorb_damage(adjusted_damage, damage_type)
            defender_health.distribute_damage(remaining_damage, damage_type)

    def apply_critical_miss(self, attacker, defender):
        print(f"🌀 {attacker.name} is exposed for a counterattack!")
        riposte_roll = random.randint(1, 100)
        if riposte_roll > 30:
            print(f"⚡️ {defender.name} counterattacks immediately!")
            self.apply_damage(defender, attacker, base_damage=5, damage_type="blunt", defender_health=CombatHealthManager(attacker), aimed_zone=None)
        else:
            print(f"{defender.name} misses the riposte opportunity.")

    def select_defense_type(self, character):
        roll = random.randint(1, 100)
        if character.has_shield():
            if roll <= 50:
                return "Block"
            elif roll <= 80:
                return "Parry"
            return "Dodge"
        if roll <= 40:
            return "Parry"
        return "Dodge"

    def apply_defense_wear(self, character, defense_type):
        if defense_type == "Block":
            if character.has_shield():
                character.wear_shield()
            else:
                character.wear_weapon()
        elif defense_type == "Parry":
            character.wear_weapon()
        elif defense_type == "Dodge":
            character.apply_dodge_penalty()