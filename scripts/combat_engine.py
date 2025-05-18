# ✅ Final integration: CombatEngine with stance + maneuver bonuses

import random
from combat_health import CombatHealthManager
from character import Character
from stance_logic import apply_stance_modifiers, get_stamina_cost_modifier
from maneuver_handler import ManeuverHandler

class CombatEngine:
    def __init__(self):
        self.maneuvers = ManeuverHandler()

    def attack_roll(self, attacker, defender, weapon_damage, damage_type, attacker_health, defender_health, aimed_zone=None):
        attack_roll = random.randint(1, 100)
        defense_roll = random.randint(1, 100)

        # ✅ Extract stance + weapon
        attacker_stance = getattr(attacker, "stance", "neutral")
        defender_stance = getattr(defender, "stance", "neutral")
        weapon_type = attacker.weapon.get("type")

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
            self.apply_critical_hit(attacker, defender, weapon_damage, damage_type, defender_health, aimed_zone)
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
        if aimed_zone:
            print(f"💥 {attacker.name} deals {base_damage} ({damage_type}) damage to {defender.name}'s {aimed_zone}!")
            defender_health.take_damage_to_zone(aimed_zone, base_damage, damage_type)
        else:
            print(f"💥 {attacker.name} deals {base_damage} ({damage_type}) damage across {defender.name}'s body!")
            defender_health.distribute_damage(base_damage, damage_type)

    def apply_critical_hit(self, attacker, defender, base_damage, damage_type, defender_health, aimed_zone):
        critical_damage = base_damage * 2
        if aimed_zone:
            print(f"💥💥 Critical Aimed Strike! {attacker.name} critically strikes {defender.name}'s {aimed_zone} for {critical_damage} {damage_type} damage!")
            defender_health.take_damage_to_zone(aimed_zone, critical_damage, damage_type)
        else:
            print(f"💥💥 Critical Strike! {attacker.name} deals {critical_damage} critical {damage_type} damage across {defender.name}'s body!")
            defender_health.distribute_damage(critical_damage, damage_type)

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
