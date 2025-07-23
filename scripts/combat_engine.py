# ✅ Updated: combat_engine.py for ogre mechanics

import random
import json
import os
from combat_health import CombatHealthManager
from character import Character
from stance_logic import apply_stance_modifiers, get_stamina_cost_modifier
from maneuver_handler import ManeuverHandler
from fear_system import FearSystem

class CombatEngine:
    def __init__(self):
        self.maneuvers = ManeuverHandler()
        self.fear_system = FearSystem()
        self.armor_penetration = {
            "warhammer": 0.3, "flanged_mace": 0.25, "battle_axe": 0.15, "sword": 0.05, "claymore": 0.05,
            "dagger": 0.1, "three_edged_dagger": 0.4, "halberd": 0.2, "saber": 0.05, "rapier": 0.15,
            "spear": 0.2, "bow": 0.1, "crossbow": 0.25, "flintlock": 0.35, "improvised": 0.2
        }
        self.durability_damage_multiplier = {
            "blunt": 1.5, "slashing": 1.0, "piercing": 0.8
        }
        self.weapon_penalties = {
            "warhammer": {"offense": -5, "defense": -5}, "flanged_mace": {"offense": -3, "defense": -3},
            "battle_axe": {"offense": -2, "defense": -2}, "sword": {"offense": 0, "defense": 0},
            "claymore": {"offense": 0, "defense": 0}, "dagger": {"offense": 0, "defense": -3},
            "three_edged_dagger": {"offense": -3, "defense": -3}, "halberd": {"offense": -2, "defense": -1},
            "saber": {"offense": 0, "defense": 0}, "rapier": {"offense": 0, "defense": 0},
            "spear": {"offense": -1, "defense": 0}, "bow": {"offense": 0, "defense": -5},
            "crossbow": {"offense": 0, "defense": -5}, "flintlock": {"offense": 0, "defense": -5},
            "improvised": {"offense": -2, "defense": -2}
        }
        self.last_outcome = {}
        self.stance_locks = {}
        self.upper_leg_priority = ["left_upper_leg", "right_upper_leg"]
        self.grapple_flags = {}  # New: Track grappled targets
        self.rules = self.load_combat_rules()

    def load_combat_rules(self):
        path = os.path.join(os.path.dirname(__file__), "../rules/combat_rules.json")
        with open(path, 'r') as f:
            return json.load(f)

    def attack_roll(self, attacker, defender, weapon_damage, damage_type, attacker_health, defender_health, aimed_zone=None, spell_name=None, chosen_stance=None, ambush_bonus=0, roll_penalty=0, opponents=[]):
        if defender.stunned:
            print(f"😵 {defender.name} is stunned—skips turn!")
            defender.stunned = False
            return {"result": "stunned_skip"}

        if defender.grappled_by and defender.weapon.get("size_class") in ["large", "two-handed"]:
            print(f"⚠️ {defender.name} can't attack with large weapon while grappled—struggle only!")
            struggle_roll = random.randint(1, 100) + defender.strength // 10
            grappler_roll = random.randint(1, 100) + defender.grappled_by.strength // 10
            print(f"Struggle roll: {struggle_roll} vs Grappler: {grappler_roll}")
            if struggle_roll > grappler_roll:
                print(f"🆓 {defender.name} breaks free!")
                defender.grappled_by = None
                self.grapple_flags.pop(defender.name, None)
            return {"result": "grapple_struggle"}

        if not attacker.alive or attacker.exhausted or attacker.last_action:
            print(f"⚠️ {attacker.name} is incapacitated and cannot act!")
            return {"result": "incapacitated"}

        if attacker.name not in self.stance_locks or chosen_stance:
            attacker.stance = chosen_stance if chosen_stance else "neutral"
            self.stance_locks[attacker.name] = attacker.stance
        elif attacker.alive:
            attacker.stance = self.stance_locks[attacker.name]
            print(f"🔒 {attacker.name} remains in {attacker.stance.upper()} stance")

        # New: If grapple_committed, can't normal attack
        if attacker.grapple_committed:
            print(f"⚠️ {attacker.name} is committed to grapple—choose action!")
            grapple_choice = input("Rip apart, smash ground, use as club, or release? ").lower().strip('.')
            if grapple_choice == "rip apart":
                aimed_zone = input("Enter target zone for rip (e.g., left_upper_arm): ").strip().lower()
                rip_roll = random.randint(1, 100) + attacker.strength // 5
                resist_roll = random.randint(1, 100) + defender.toughness // 5
                # Easier rip on limbs
                limb_zones = ["left_lower_leg", "right_lower_leg", "left_upper_leg", "right_upper_leg", "left_lower_arm", "right_lower_arm", "left_upper_arm", "right_upper_arm"]
                if aimed_zone in limb_zones:
                    rip_roll += 10  # Bonus for limbs
                elif aimed_zone == "head":
                    resist_roll += 10  # Harder for head
                print(f"Rip roll: {rip_roll} vs Resist: {resist_roll}")
                if rip_roll > resist_roll:
                    print(f"💥 {attacker.name} rips {defender.name}'s {aimed_zone}—horrific tear! 🩸 Gore sprays as the limb is torn off!")
                    defender_health.take_damage_to_zone(aimed_zone, 35, "slashing", critical=True)  # Full damage to one zone
                    defender.bleeding_rate += 2.4
                    defender.pain_penalty += 15
                    defender.mobility_penalty += 25
                    defender_health.recalculate_penalties()  # Immediate penalty update
                    if attacker.class_name == "Ogre Ravager":
                        attacker.health += 15  # Flesh Rend heal
                        attacker.corruption_level = min(100, attacker.corruption_level + 5)
                        print(f"🩸 {attacker.name} devours the flesh, healing 15 health! Corruption rises to {attacker.corruption_level}%.")
                else:
                    print(f"❌ {defender.name} resists the rip—slips free!")
                attacker.grapple_committed = False
                self.grapple_flags.pop(defender.name, None)
                attacker.consume_stamina(15)
                return {"result": "rip_attempt"}
            elif grapple_choice == "smash ground":
                smash_damage = weapon_damage + 10  # Blunt + stun
                defender_health.distribute_damage(smash_damage, "blunt")
                if random.random() < 0.5:
                    defender.stunned = True
                    print(f"😵 {defender.name} dazed from smash! Skip next turn.")
                    defender.skip_turn = True  # Add stun effect (skip turn)
                attacker.grapple_committed = False
                self.grapple_flags.pop(defender.name, None)
                attacker.consume_stamina(15)
                return {"result": "smash_ground"}
            elif grapple_choice == "use as club":
                if len(opponents) > 1:  # Assume multi-foe
                    other_target = random.choice([opp for opp in opponents if opp != defender])
                    print(f"🌀 {attacker.name} swings {defender.name} as a club at {other_target.name}!")
                    other_target_health = CombatHealthManager(other_target)
                    other_target_health.distribute_damage(weapon_damage, "blunt")
                    defender_health.distribute_damage(10, "blunt")  # Damage to grappled too
                else:
                    print(f"❌ No other foes—smash ground instead!")
                    smash_damage = weapon_damage + 10
                    defender_health.distribute_damage(smash_damage, "blunt")
                attacker.grapple_committed = False
                self.grapple_flags.pop(defender.name, None)
                attacker.consume_stamina(15)
                return {"result": "use_as_club"}
            else:
                print(f"🛑 {attacker.name} releases the grapple!")
                attacker.grapple_committed = False
                self.grapple_flags.pop(defender.name, None)
                return {"result": "release_grapple"}

        # New: Grappled Defender Limits
        if defender.grappled_by:
            print(f"🔗 {defender.name} grappled—limited actions!")
            # Restrict to small weapons (dagger) or struggle
            if defender.weapon.get("size_class") != "small":
                print(f"⚠️ {defender.name} can't swing large weapon while grappled—use dagger or struggle!")
                # Struggle option: Strength vs grappler strength to escape
                struggle_roll = random.randint(1, 100) + defender.strength // 10
                grappler_roll = random.randint(1, 100) + defender.grappled_by.strength // 10
                print(f"Struggle roll: {struggle_roll} vs Grappler: {grappler_roll}")
                if struggle_roll > grappler_roll:
                    print(f"🆓 {defender.name} breaks free!")
                    defender.grappled_by = None
                return {"result": "grapple_struggle"}

        raw_roll = random.randint(1, 100)
        attack_roll = raw_roll + attacker.weapon_skill
        defense_base_roll = random.randint(1, 100)

        if attacker.weapon and isinstance(attacker.weapon, dict) and attacker.weapon.get("fear_trigger", False):
            fear_response = self.fear_system.check_fear(defender, attacker.weapon)
            if fear_response["triggered"]:
                print(f"😱 {defender.name} freezes: {fear_response['outburst']}")
                defender.stress_level += fear_response["stress_increase"]
                attack_roll -= fear_response["roll_penalty"]
                if fear_response["force_stance"]:
                    defender.stance = "defensive"
                    print(f"🛡️ {defender.name} shifts to DEFENSIVE stance out of fear!")

        attacker_stance = attacker.stance
        defender_stance = getattr(defender, "stance", "neutral")
        current_health = sum(defender.body_parts.values())
        if current_health < 0.5 * defender.total_hp:  # Stance variation
            defender_stance = "defensive"
        weapon_type = attacker.weapon.get("type") if isinstance(attacker.weapon, dict) else "none"

        maneuver_bonus = self.maneuvers.get_bonus_effects(weapon_type, attacker_stance, "always", aimed_zone)

        attack_roll += apply_stance_modifiers(attacker, defender, attacker_stance, "attack")
        attack_roll += maneuver_bonus.get("attack_bonus", 0)
        attack_roll += self.weapon_penalties.get(weapon_type, {"offense": 0})["offense"]
        attack_roll += attacker.dexterity // 10
        if attacker_stance == "offensive":
            attack_roll += attacker.strength // 10
        elif attacker_stance == "defensive":
            attack_roll -= 10
        attack_roll += ambush_bonus
        attack_roll -= roll_penalty if aimed_zone else 0

        defense_type = self.select_defense_type(defender)  # Moved here

        defense_roll = defense_base_roll  # Initialize defense_roll

        # New: Ogre Mass Penalty for Block/Parry with Strength Test
        if (defense_type in ["Block", "Parry"]) and (attacker.mass > defender.mass * 1.5):
            mass_penalty = (attacker.strength - defender.strength) // 5
            strength_roll = random.randint(1, 100) + defender.strength // 5
            strength_threshold = 40  # Lowered for ~70% ogre success
            print(f"💪 {defender.name} attempts strength test (needs {strength_threshold}+): rolled {strength_roll}")
            if strength_roll < strength_threshold:
                print(f"🌀 {defender.name} fails to resist ogre's mass! Thrown back, stunned for 1 turn.")
                defender.stunned = True
                defender.mobility_penalty = min(100, defender.mobility_penalty + 20)  # Temporary mobility penalty
                defense_roll -= mass_penalty  # Still apply penalty on fail
            else:
                print(f"💪 {defender.name} braces against ogre's mass!")
                defense_roll -= mass_penalty  # Apply penalty even on success, but no stun

        if defense_type == "Dodge":
            defense_roll += defender.agility // 2
        elif defense_type == "Parry":
            defense_roll += defender.weapon_skill // 2
        elif defense_type == "Block":
            defense_roll += (defender.strength // 2 if defender.has_shield() else defender.weapon_skill // 2)
            if defender.has_shield():
                defense_roll += 5  # Flat shield bonus; can adjust or tie to shield stats later

        defense_roll += apply_stance_modifiers(defender, attacker, defender_stance, "defense")
        defense_roll += maneuver_bonus.get("defense_bonus", 0)
        defense_roll += self.weapon_penalties.get(weapon_type, {"defense": 0})["defense"]
        if defender_stance == "defensive":
            defense_roll += defender.agility // 10  # Keep small agility boost for defensive stance

        stress_penalty = max(0, attacker.stress_level - 80) // 10
        pain_penalty = min(attacker.pain_penalty, 20)
        attack_roll = max(1, attack_roll - attacker.stamina_penalty() - pain_penalty - stress_penalty)
        defense_stress_penalty = max(0, defender.stress_level - 80) // 10
        defense_pain_penalty = min(defender.pain_penalty, 20)
        defense_roll = max(1, defense_roll - defender.stamina_penalty() - defense_pain_penalty - defense_stress_penalty)

        print(f"\n⚔️ {attacker.name} is in {attacker_stance.upper()} stance")
        print(f"🛡️ {defender.name} is in {defender_stance.upper()} stance")
        print(f"⚔️ {attacker.name} rolls {raw_roll} + {attacker.weapon_skill} (Weapon Skill) + {attacker.dexterity // 10} (Dexterity) - {stress_penalty} (Stress) - {pain_penalty} (Pain) + {ambush_bonus} (Ambush) = {attack_roll} to attack!")
        print(f"🛡️ {defender.name} rolls {defense_base_roll} + {defender.agility // 2 if defense_type == 'Dodge' else defender.weapon_skill // 2 if defense_type == 'Parry' else (defender.strength // 2 if defender.has_shield() else defender.weapon_skill // 2)} (Stat) - {defense_stress_penalty} (Stress) - {defense_pain_penalty} (Pain) = {defense_roll} to defend! ({defense_type})")

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
                    attacker.corruption_level = min(100, attacker.corruption_level + 5)
                    print(f"😈 {attacker.name}'s corruption rises to {attacker.corruption_level}%!")
                    self.apply_damage(attacker, defender, damage, spell["damage_type"], defender_health, aimed_zone, critical=False)
                else:
                    outcome["result"] = "effect"
                    print(f"✨ {attacker.name} casts {spell_name} successfully!")
            else:
                outcome["result"] = "spell_failed"
                print(f"❌ {attacker.name} fails to cast {spell_name}!")
        else:
            is_critical = raw_roll >= 95
            is_miss = raw_roll <= 5
            if is_miss:
                print("💀 Critical Miss!")
                outcome["result"] = "critical_miss"
                self.apply_critical_miss(attacker, defender)
            elif attack_roll > defense_roll:
                if is_critical:
                    print("🔥 Critical Hit!")
                    outcome["critical"] = True
                    outcome["damage"] = weapon_damage * 1.2  # Capped
                    self.apply_damage(attacker, defender, outcome["damage"], damage_type, defender_health, aimed_zone, True)
                else:
                    print(f"✅ {attacker.name} hits {defender.name}!")
                    outcome["damage"] = weapon_damage
                    self.apply_damage(attacker, defender, weapon_damage, damage_type, defender_health, aimed_zone, False)
                outcome["result"] = "hit" if not is_critical else "critical_hit"
                attacker.wear_weapon()
                print(f"⚔️ {attacker.name}'s {attacker.weapon.get('name', 'weapon')} durability: {attacker.weapon.get('durability', 50)}")
            else:
                print(f"❌ {attacker.name} misses or {defender.name} successfully defends!")
                outcome["result"] = "miss"
                self.apply_defense_wear(defender, defense_type)
                if defense_type in ["Parry", "Block"]:
                    defender.wear_weapon()
                    print(f"⚔️ {defender.name}'s {defender.weapon.get('name', 'weapon')} durability: {defender.weapon.get('durability', 50)}")
                    if defense_type == "Block" and defender.has_shield():
                        defender.wear_shield()
                        print(f"🛡️ {defender.name}'s shield durability: {defender.shield.get('durability', 50)}")

        self.last_outcome = outcome

        atk_cost = 3 + get_stamina_cost_modifier(attacker_stance, "offensive") + maneuver_bonus.get("stamina_cost_modifier", 0)
        def_cost = 2 + get_stamina_cost_modifier(defender_stance, "defensive")
        if attacker_stance == "offensive":
            atk_cost += 2
        elif attacker_stance == "defensive":
            atk_cost -= 1
        attacker.consume_stamina(atk_cost)
        defender.consume_stamina(def_cost)

        if attacker_stance == "neutral":
            attacker.recover_stamina(1)
        if defender_stance == "neutral":
            defender.recover_stamina(1)

        attacker.check_stamina_state()
        defender.check_stamina_state()
        attacker.combat_count += 1
        if attacker.combat_count % 5 == 0:
            attacker.progress_stat("weapon_skill", 1)
        if attacker.combat_count % 10 == 0:
            attacker.progress_stat("weapon_skill", 2)

        if outcome["result"] in ["hit", "critical_hit"]:
            self.stance_locks.pop(attacker.name, None)

        # Moral/Willpower check after severe damage
        current_health = sum(defender.body_parts.values())
        if current_health < 0.3 * defender.total_hp or self.has_severe_wound(defender):  # Nearly lethal or limb loss
            if not self.morale_check(defender):
                if "elite" not in defender.tags:  # Assume non-elite NPCs surrender/collapse
                    print(f"💔 {defender.name} breaks! They surrender or collapse from the trauma.")
                    defender.alive = False if random.random() < 0.5 else defender.alive  # 50% chance of death vs collapse
                    defender.in_combat = False

        return outcome

    def has_severe_wound(self, character):
        severe_parts = ["head", "chest", "stomach", "groin"]
        for part in severe_parts:
            if character.body_parts.get(part, 1) <= 0:
                return True
        # Check for limb loss (assuming body_parts <=0 means severed)
        limb_parts = ["left_lower_leg", "right_lower_leg", "left_upper_leg", "right_upper_leg", "left_lower_arm", "right_lower_arm", "left_upper_arm", "right_upper_arm"]
        lost_limbs = sum(1 for part in limb_parts if character.body_parts.get(part, 1) <= 0)
        return lost_limbs >= 2  # e.g., 2+ limbs lost = severe

    def morale_check(self, character):
        roll = random.randint(1, 100)
        threshold = (character.willpower // 5) + 30 - character.pain_penalty // 2 - character.stress_level // 10
        print(f"Morale check for {character.name}: Roll {roll} vs threshold {threshold}")
        return roll <= threshold

    def apply_damage(self, attacker, defender, base_damage, damage_type, defender_health, aimed_zone, critical=False):
        weapon_type = attacker.weapon.get("type") if isinstance(attacker.weapon, dict) else "none"  # Fix for string weapon
        penetration_factor = self.armor_penetration.get(weapon_type, 0.0)
        durability_multiplier = self.durability_damage_multiplier.get(damage_type, 1.0)

        base_damage = int(base_damage) + (attacker.strength // 10)
        if attacker.name == "Bandit":
            base_damage = int(base_damage * 0.2)

        if aimed_zone:
            print(f"💥 {attacker.name} deals {base_damage} ({damage_type}) damage to {defender.name}'s {aimed_zone}!")
            remaining_damage = base_damage
            armor_hit = False
            for armor in defender.armor:
                if aimed_zone in armor.coverage and armor.current_durability.get(aimed_zone, 0) > 0:
                    armor_hit = True
                    remaining_damage = armor.absorb_damage(base_damage, damage_type, aimed_zone)
            if not armor_hit:
                print(f"⚠️ {aimed_zone} is unprotected, full damage applied!")
            defender_health.take_damage_to_zone(aimed_zone, remaining_damage, damage_type, critical=critical)

        else:
            print(f"💥 {attacker.name} deals {base_damage} ({damage_type}) damage across {defender.name}'s body!")
            valid_parts = ["left_lower_leg", "right_lower_leg", "left_upper_leg", "right_upper_leg",
                           "stomach", "chest", "left_lower_arm", "right_lower_arm",
                           "left_upper_arm", "right_upper_arm"]
            base_damage_per_part = base_damage // 10
            remainder = base_damage % 10
            damage_parts = {part: base_damage_per_part for part in valid_parts}
            priority_parts = ["chest"]
            if remainder > 0:
                priority_parts.append(self.upper_leg_priority[0])
                self.upper_leg_priority = self.upper_leg_priority[::-1]
            if remainder > 1:
                priority_parts.append(self.upper_leg_priority[0])
            for i in range(min(remainder, len(priority_parts))):
                damage_parts[priority_parts[i]] += 1
            for part, part_damage in damage_parts.items():
                if part_damage > 0:
                    remaining_damage = part_damage
                    armor_hit = False
                    for armor in defender.armor:
                        if part in armor.coverage and armor.current_durability.get(part, 0) > 0:
                            armor_hit = True
                            remaining_damage = armor.absorb_damage(part_damage, damage_type, part)
                    if not armor_hit:
                        print(f"⚠️ {part} is unprotected, {part_damage} damage applied!")
                    defender_health.take_damage_to_zone(part, remaining_damage, damage_type, critical=critical)

    def apply_critical_hit(self, attacker, defender, base_damage, damage_type, attacker_health, defender_health, aimed_zone):
        critical_damage = int(base_damage * 1.2)  # Capped
        self.apply_damage(attacker, defender, critical_damage, damage_type, defender_health, aimed_zone, True)

    def apply_critical_miss(self, attacker, defender):
        print(f"🌀 {attacker.name} is exposed for a counterattack!")
        riposte_roll = random.randint(1, 100)
        threshold = 30 - (defender.perception // 10)
        print(f"Riposte roll: {riposte_roll} vs threshold {threshold}")
        if riposte_roll > threshold:
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