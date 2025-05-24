import random
from combat_health import CombatHealthManager
from character import Character
from stance_logic import apply_stance_modifiers, get_stamina_cost_modifier
from maneuver_handler import ManeuverHandler

class CombatEngine:
    def __init__(self):
        self.maneuvers = ManeuverHandler()
        self.armor_penetration = {
            "warhammer": 0.3,
            "flanged_mace": 0.25,
            "battle_axe": 0.15,
            "sword": 0.05,
            "claymore": 0.05,
            "dagger": 0.1,
            "three_edged_dagger": 0.4,
            "halberd": 0.2,
            "saber": 0.05,
            "rapier": 0.15,
            "spear": 0.2,
            "bow": 0.1,
            "crossbow": 0.25,
            "flintlock": 0.35
        }
        self.durability_damage_multiplier = {
            "blunt": 1.5,
            "slashing": 1.0,
            "piercing": 0.8
        }
        self.weapon_penalties = {
            "warhammer": {"offense": -5, "defense": -5},
            "flanged_mace": {"offense": -3, "defense": -3},
            "battle_axe": {"offense": -2, "defense": -2},
            "sword": {"offense": 0, "defense": 0},
            "claymore": {"offense": 0, "defense": 0},
            "dagger": {"offense": 0, "defense": -3},
            "three_edged_dagger": {"offense": 0, "defense": -3},
            "halberd": {"offense": -2, "defense": -1},
            "saber": {"offense": 0, "defense": 0},
            "rapier": {"offense": 0, "defense": 0},
            "spear": {"offense": -1, "defense": 0},
            "bow": {"offense": 0, "defense": -5},
            "crossbow": {"offense": 0, "defense": -5},
            "flintlock": {"offense": 0, "defense": -5}
        }
        self.last_outcome = {}

    def attack_roll(self, attacker, defender, weapon_damage, damage_type, attacker_health, defender_health, aimed_zone=None, spell_name=None):
        attack_roll = random.randint(1, 100)
        defense_roll = random.randint(1, 100)

        attacker_stance = getattr(attacker, "stance", "neutral")
        defender_stance = getattr(defender, "stance", "neutral")
        weapon_type = attacker.weapon.get("type") if attacker.weapon and not spell_name else "none"

        maneuver_bonus = self.maneuvers.get_bonus_effects(weapon_type, attacker_stance, trigger="always")
        attack_roll += apply_stance_modifiers(attacker, defender, attacker_stance, "attack")
        attack_roll += maneuver_bonus.get("attack_bonus", 0)
        attack_roll += self.weapon_penalties.get(weapon_type, {"offense": 0})["offense"]

        defense_roll += apply_stance_modifiers(defender, attacker, defender_stance, "defense")
        defense_roll += maneuver_bonus.get("defense_bonus", 0)
        defense_roll += self.weapon_penalties.get(weapon_type, {"defense": 0})["defense"]

        if aimed_zone:
            print(f"🎯 {attacker.name} attempts an aimed strike at {aimed_zone}!")
            attack_roll -= 30

        attack_roll = max(1, attack_roll - attacker.stamina_penalty() - min(attacker.pain_penalty, 20))
        defense_roll = max(1, defense_roll - defender.stamina_penalty() - min(defender.pain_penalty, 20))

        defense_type = self.select_defense_type(defender)

        print(f"\n⚔️ {attacker.name} is in {attacker_stance.upper()} stance")
        print(f"🛡️ {defender.name} is in {defender_stance.upper()} stance")
        print(f"⚔️ {attacker.name} rolls {attack_roll} to attack!")
        print(f"🛡️ {defender.name} rolls {defense_roll} to defend! ({defense_type})")

        outcome = {
            "attacker": attacker.name,
            "defender": defender.name,
            "attack_roll": attack_roll,
            "defense_roll": defense_roll,
            "defense_type": defense_type,
            "result": None,
            "damage": 0,
            "critical": False,
            "aimed_zone": aimed_zone,
            "spell_used": spell_name
        }

        if spell_name:
            from magic_system import MagicSystem
            magic = MagicSystem()
            if magic.cast_spell(attacker, defender, spell_name, attacker_health, defender_health):
                spell = magic.spells.get(spell_name)
                if spell["type"] == "necromantic":
                    damage = spell["damage"]
                    outcome["result"] = "hit"
                    outcome["damage"] = damage
                    print(f"✨ {attacker.name} casts {spell_name} successfully!")
                    self.apply_damage(attacker, defender, damage, spell["damage_type"], defender_health, aimed_zone, critical=False)
                else:
                    outcome["result"] = "effect"
                    print(f"✨ {attacker.name} casts {spell_name} successfully!")
            else:
                outcome["result"] = "spell_failed"
                print(f"❌ {attacker.name} fails to cast {spell_name}!")
        else:
            if attack_roll >= 95:
                print("🔥 Critical Hit!")
                outcome["result"] = "critical_hit"
                outcome["critical"] = True
                outcome["damage"] = weapon_damage * 1.5
                self.apply_critical_hit(attacker, defender, weapon_damage, damage_type, attacker_health, defender_health, aimed_zone)
            elif attack_roll <= 5:
                print("💀 Critical Miss!")
                outcome["result"] = "critical_miss"
                self.apply_critical_miss(attacker, defender)
            elif attack_roll > defense_roll:
                print(f"✅ {attacker.name} hits {defender.name}!")
                outcome["result"] = "hit"
                outcome["damage"] = weapon_damage
                self.apply_damage(attacker, defender, weapon_damage, damage_type, defender_health, aimed_zone, critical=False)
            else:
                print(f"❌ {attacker.name} misses or {defender.name} successfully defends!")
                outcome["result"] = "miss"
                self.apply_defense_wear(defender, defense_type)

        self.last_outcome = outcome

        atk_cost = 5 + get_stamina_cost_modifier(attacker_stance, "offensive") + maneuver_bonus.get("stamina_cost_modifier", 0)
        def_cost = 3 + get_stamina_cost_modifier(defender_stance, "defensive")
        attacker.consume_stamina(atk_cost)
        defender.consume_stamina(def_cost)

        attacker.check_stamina_state()
        defender.check_stamina_state()

        return outcome

    def apply_damage(self, attacker, defender, base_damage, damage_type, defender_health, aimed_zone, critical=False):
        weapon_type = attacker.weapon.get("type") if attacker.weapon else "none"
        penetration_factor = self.armor_penetration.get(weapon_type, 0.0)
        durability_multiplier = self.durability_damage_multiplier.get(damage_type, 1.0)

        if aimed_zone:
            print(f"💥 {attacker.name} deals {base_damage} ({damage_type}) damage to {defender.name}'s {aimed_zone}!")
            remaining_damage = base_damage
            for armor in defender.armor:
                if aimed_zone in armor.coverage:
                    original_protection = armor.armor_rating.get(damage_type, 0)
                    reduced_protection = original_protection * (1 - penetration_factor)
                    adjusted_damage = max(0, base_damage - reduced_protection)
                    armor.current_durability -= max(1, int(adjusted_damage * 0.1 * durability_multiplier))
                    if armor.current_durability < 0:
                        armor.current_durability = 0
                    remaining_damage = armor.absorb_damage(adjusted_damage, damage_type)
            defender_health.take_damage_to_zone(aimed_zone, remaining_damage, damage_type, critical=critical)
        else:
            print(f"💥 {attacker.name} deals {base_damage} ({damage_type}) damage across {defender.name}'s body!")
            remaining_damage = base_damage
            for armor in defender.armor:
                original_protection = armor.armor_rating.get(damage_type, 0)
                reduced_protection = original_protection * (1 - penetration_factor)
                adjusted_damage = max(0, base_damage / len(defender.armor) if defender.armor else base_damage - reduced_protection)
                armor.current_durability -= max(1, int(adjusted_damage * 0.1 * durability_multiplier))
                if armor.current_durability < 0:
                    armor.current_durability = 0
                remaining_damage = armor.absorb_damage(adjusted_damage, damage_type)
            defender_health.distribute_damage(remaining_damage, damage_type, critical=critical)

    def apply_critical_hit(self, attacker, defender, base_damage, damage_type, attacker_health, defender_health, aimed_zone):
        critical_damage = base_damage * 1.5
        weapon_type = attacker.weapon.get("type") if attacker.weapon else "none"
        penetration_factor = self.armor_penetration.get(weapon_type, 0.0)
        durability_multiplier = self.durability_damage_multiplier.get(damage_type, 1.0)

        if aimed_zone:
            print(f"💥💥 Critical Aimed Strike! {attacker.name} critically strikes {defender.name}'s {aimed_zone} for {critical_damage} {damage_type} damage!")
            remaining_damage = critical_damage
            for armor in defender.armor:
                if aimed_zone in armor.coverage:
                    original_protection = armor.armor_rating.get(damage_type, 0)
                    reduced_protection = original_protection * (1 - penetration_factor)
                    adjusted_damage = max(0, critical_damage - reduced_protection)
                    armor.current_durability -= max(1, int(adjusted_damage * 0.1 * durability_multiplier))
                    if armor.current_durability < 0:
                        armor.current_durability = 0
                    remaining_damage = armor.absorb_damage(adjusted_damage, damage_type)
            defender_health.take_damage_to_zone(aimed_zone, remaining_damage, damage_type, critical=True)
        else:
            print(f"💥💥 Critical Strike! {attacker.name} deals {critical_damage} critical {damage_type} damage across {defender.name}'s body!")
            remaining_damage = critical_damage
            for armor in defender.armor:
                original_protection = armor.armor_rating.get(damage_type, 0)
                reduced_protection = original_protection * (1 - penetration_factor)
                adjusted_damage = max(0, critical_damage / len(defender.armor) if defender.armor else critical_damage - reduced_protection)
                armor.current_durability -= max(1, int(adjusted_damage * 0.1 * durability_multiplier))
                if armor.current_durability < 0:
                    armor.current_durability = 0
                remaining_damage = armor.absorb_damage(adjusted_damage, damage_type)
            defender_health.distribute_damage(remaining_damage, damage_type, critical=True)

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