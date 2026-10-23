# file: scripts/combat_health.py
import random
import logging
from damage_consequences import DamageConsequences
from zone_hp import spread_damage, total_hp, VITAL_ZONES

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CombatHealthManager:
    def __init__(self, character):
        self.character = character
        self.health = {part: hp for part, hp in character.body_parts.items()}
        self.initial_health = self.health.copy()
        self.total_hp = sum(self.health.values())
        self.starting_hp = self.total_hp
        self.bleeding_wounds = []
        self.consequences = DamageConsequences()
        self.character.alive = True
        self.critical_wound_tables = {
            'arm': {
                'blunt': [
                    "Bone bruised, arm numb, -10% dexterity" for _ in range(20)
                ] + ["Compound fracture, bleeding starts, -15% weapon_skill" for _ in range(20)
                ] + ["Bone shattered, arm useless, -20% dexterity, heavy bleeding" for _ in range(20)
                ] + ["Arm crushed, severe pain, -25% all rolls, shock" for _ in range(20)
                ] + ["Arm pulverized, severed, massive blood loss, collapse likely" for _ in range(20)],
                'slashing': [
                    "Shallow cut, minor bleeding, -5% weapon_skill" for _ in range(20)
                ] + ["Deep gash, bleeding heavily, -10% dexterity" for _ in range(20)
                ] + ["Muscle slashed, arm weakened, -15% strength" for _ in range(20)
                ] + ["Artery cut, rapid blood loss, -20% all rolls" for _ in range(20)
                ] + ["Arm severed, shock and trauma, instant collapse" for _ in range(20)],
                'piercing': [
                    "Puncture wound, light bleeding, -5% dexterity" for _ in range(20)
                ] + ["Deep stab, internal damage, -10% stamina regen" for _ in range(20)
                ] + ["Tendon pierced, arm stiff, -15% weapon_skill" for _ in range(20)
                ] + ["Artery punctured, heavy bleeding, -20% all rolls" for _ in range(20)
                ] + ["Vital hit, arm disabled, severe shock" for _ in range(20)]
            },
            'leg': {
                'blunt': [
                    "Leg bruised, limp, -10% mobility" for _ in range(20)
                ] + ["Knee cracked, slowed movement, -15% agility" for _ in range(20)
                ] + ["Bone fractured, hobbling, -20% dodge" for _ in range(20)
                ] + ["Leg crushed, can't stand, -25% all movement" for _ in range(20)
                ] + ["Leg shattered, severed, collapse from pain" for _ in range(20)],
                'slashing': [
                    "Cut on leg, minor bleed, -5% mobility" for _ in range(20)
                ] + ["Hamstring slashed, slowed, -10% agility" for _ in range(20)
                ] + ["Deep laceration, bleeding, -15% dodge" for _ in range(20)
                ] + ["Tendon severed, leg useless, -20% movement" for _ in range(20)
                ] + ["Leg amputated, massive trauma, shock" for _ in range(20)],
                'piercing': [
                    "Stab in leg, light bleed, -5% agility" for _ in range(20)
                ] + ["Muscle pierced, limp, -10% mobility" for _ in range(20)
                ] + ["Bone hit, fracture, -15% dodge" for _ in range(20)
                ] + ["Artery nicked, heavy bleed, -20% all rolls" for _ in range(20)
                ] + ["Vital pierce, leg disabled, collapse" for _ in range(20)]
            },
            'head': {
                'blunt': [
                    "Concussion, dazed, -10% all rolls" for _ in range(20)
                ] + ["Skull cracked, headache, -15% perception" for _ in range(20)
                ] + ["Brain trauma, disoriented, -20% intelligence" for _ in range(20)
                ] + ["Severe concussion, vomiting, -25% willpower" for _ in range(20)
                ] + ["Skull crushed, instant death" for _ in range(20)],
                'slashing': [
                    "Scalp cut, bleeding, -5% perception" for _ in range(20)
                ] + ["Ear sliced, disoriented, -10% hearing" for _ in range(20)
                ] + ["Face gashed, blinded one eye, -15% accuracy" for _ in range(20)
                ] + ["Throat nicked, choking, -20% breathing" for _ in range(20)
                ] + ["Decapitation, immediate death" for _ in range(20)],
                'piercing': [
                    "Puncture to head, stun, -5% all rolls" for _ in range(20)
                ] + ["Eye pierced, partial blind, -10% perception" for _ in range(20)
                ] + ["Brain stab, confused, -15% intelligence" for _ in range(20)
                ] + ["Vital hit, coma, -20% willpower" for _ in range(20)
                ] + ["Fatal pierce, death" for _ in range(20)]
            },
            'throat': {
                'blunt': [
                    "Throat bruised, hoarse, -10% charisma" for _ in range(20)
                ] + ["Windpipe crushed, gasping, -15% stamina" for _ in range(20)
                ] + ["Neck broken, paralyzed, -20% all rolls" for _ in range(20)
                ] + ["Severe trauma, choking, collapse" for _ in range(20)
                ] + ["Instant kill from crushed throat" for _ in range(20)],
                'slashing': [
                    "Throat nicked, bleeding, -5% breathing" for _ in range(20)
                ] + ["Jugular cut, heavy bleed, -10% stamina" for _ in range(20)
                ] + ["Windpipe slashed, suffocating, -15% all rolls" for _ in range(20)
                ] + ["Throat severed, gurgling death" for _ in range(20)
                ] + ["Decapitation-level slash, instant death" for _ in range(20)],
                'piercing': [
                    "Throat punctured, cough, -5% charisma" for _ in range(20)
                ] + ["Artery pierced, bleed out, -10% stamina" for _ in range(20)
                ] + ["Vital stab, choking blood, -15% all rolls" for _ in range(20)
                ] + ["Fatal pierce, quick death" for _ in range(20)
                ] + ["Instant kill from throat impale" for _ in range(20)]
            },
            'groin': {
                'blunt': [
                    "Groin bruised, pained, -10% mobility" for _ in range(20)
                ] + ["Vital hit, nauseous, -15% strength" for _ in range(20)
                ] + ["Crushed, agony, -20% all rolls" for _ in range(20)
                ] + ["Severe trauma, shock, collapse" for _ in range(20)
                ] + ["Ruptured, fatal internal damage" for _ in range(20)],
                'slashing': [
                    "Groin cut, bleeding, -5% mobility" for _ in range(20)
                ] + ["Deep gash, pain surge, -10% agility" for _ in range(20)
                ] + ["Severed, massive bleed, -15% all rolls" for _ in range(20)
                ] + ["Castration, shock, collapse" for _ in range(20)
                ] + ["Fatal slash, quick death" for _ in range(20)],
                'piercing': [
                    "Puncture, sting, -5% mobility" for _ in range(20)
                ] + ["Deep stab, internal bleed, -10% stamina" for _ in range(20)
                ] + ["Vital pierce, agony, -15% all rolls" for _ in range(20)
                ] + ["Rupture, shock, collapse" for _ in range(20)
                ] + ["Instant kill from vital hit" for _ in range(20)]
            },
            'chest': {
                'blunt': [
                    "Ribs bruised, winded, -10% stamina" for _ in range(20)
                ] + ["Ribs cracked, pained breath, -15% endurance" for _ in range(20)
                ] + ["Sternum fractured, internal hurt, -20% toughness" for _ in range(20)
                ] + ["Heart bruised, arrhythmia, collapse" for _ in range(20)
                ] + ["Chest caved in, fatal" for _ in range(20)],
                'slashing': [
                    "Chest cut, bleed, -5% stamina" for _ in range(20)
                ] + ["Ribs slashed, deep wound, -10% endurance" for _ in range(20)
                ] + ["Lung nicked, coughing blood, -15% toughness" for _ in range(20)
                ] + ["Heart slashed, bleed out" for _ in range(20)
                ] + ["Chest opened, instant death" for _ in range(20)],
                'piercing': [
                    "Chest puncture, sting, -5% stamina" for _ in range(20)
                ] + ["Rib pierced, pain, -10% endurance" for _ in range(20)
                ] + ["Lung stabbed, breath short, -15% toughness" for _ in range(20)
                ] + ["Heart hit, quick death" for _ in range(20)
                ] + ["Vital pierce, immediate end" for _ in range(20)]
            },
            'stomach': {
                'blunt': [
                    "Gut punch, winded, -10% endurance" for _ in range(20)
                ] + ["Organs bruised, nauseous, -15% toughness" for _ in range(20)
                ] + ["Internal bleed, pain, -20% stamina" for _ in range(20)
                ] + ["Rupture, shock, collapse" for _ in range(20)
                ] + ["Fatal internal damage" for _ in range(20)],
                'slashing': [
                    "Abdomen cut, bleed, -5% endurance" for _ in range(20)
                ] + ["Gut slashed, spilling, -10% toughness" for _ in range(20)
                ] + ["Organs exposed, infection risk, -15% stamina" for _ in range(20)
                ] + ["Eviscerated, bleed out" for _ in range(20)
                ] + ["Gutted, death" for _ in range(20)],
                'piercing': [
                    "Stab in gut, pain, -5% endurance" for _ in range(20)
                ] + ["Organ puncture, bleed, -10% toughness" for _ in range(20)
                ] + ["Deep wound, sepsis, -15% stamina" for _ in range(20)
                ] + ["Vital stab, quick death" for _ in range(20)
                ] + ["Fatal pierce" for _ in range(20)]
            }
        }

    def apply_bleeding(self):
        if not self.bleeding_wounds:
            return
        total_bleeding_damage = 0
        for wound in self.bleeding_wounds[:]:
            wound_damage = int(wound["amount"])
            total_bleeding_damage += wound_damage
            # Blood loss is spread over the body like a normal hit (no new wounds)
            for part, dmg in spread_damage(self.health, self.initial_health, wound_damage).items():
                self.health[part] -= dmg
                self._zone_hit(part, dmg, "bleeding", 0)
            wound["duration"] -= 1
            if wound["duration"] <= 0:
                self.bleeding_wounds.remove(wound)
        self._sync_total()
        if total_bleeding_damage > 0:
            print(f"🩸 {self.character.name} suffers {total_bleeding_damage} bleeding damage!")
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
        self.character.bleeding = round(sum(w["amount"] for w in self.bleeding_wounds), 1)

    def apply_pain(self):
        if self.character.pain_penalty >= 30:
            print(f"⚠️ {self.character.name} is overwhelmed by pain penalties!")
            self.check_auto_collapse()

    def check_blood_loss_collapse(self):
        blood_loss = self.starting_hp - sum(max(hp, 0) for hp in self.health.values())
        blood_loss_percent = (blood_loss / self.starting_hp) * 100
        if blood_loss_percent >= 33 and self.character.alive:
            print(f"💀 {self.character.name} collapses from massive blood loss and falls unconscious!")
            self.character.alive = False
            self.character.in_combat = False
            self.character.exhausted = True
            self.character.last_action = True

    def check_auto_collapse(self):
        crippled = [part for part, hp in self.health.items() if hp <= 0]
        if len(crippled) >= 3:
            print(f"💀 {self.character.name} collapses from severe injuries!")
            self.character.alive = False
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
                self.character.alive = False
                self.character.in_combat = False
                self.character.exhausted = True
                self.character.last_action = True
                return True
        return False

    # ---- Zone damage (see docs/ZONE_DAMAGE.md) ----
    def _sync_total(self):
        self.total_hp = total_hp(self.health)
        self.character.total_hp = self.total_hp
        self.character.body_parts = dict(self.health)

    def _zone_hit(self, zone, damage, damage_type, overflow=0):
        """Common after-effects for a zone that just lost `damage` points."""
        if self.health[zone] <= 0:
            self.health[zone] = 0
            if damage_type in ("blunt", "slashing", "piercing"):
                self.consequences.apply_consequence(self.character, zone, damage_type, overflow)
                self.apply_critical_wound(zone, damage_type, overflow)
            if zone in VITAL_ZONES and self.character.alive:
                print(f"💀 {self.character.name}'s {zone.replace('_', ' ')} is destroyed!")
                self.character.die()
            elif hasattr(self.character, "on_part_crippled") and zone not in getattr(self.character, "compromised_limbs", []):
                self.character.on_part_crippled(zone)
        else:
            self.apply_partial_damage(zone)

    def distribute_damage(self, base_damage, damage_type, critical=False):
        """Normal hit: spread damage over the whole body, weighted by zone size."""
        if not self.character.alive:
            return {}
        damage = int(base_damage * (1.2 if critical else 1.0))
        split = spread_damage(self.health, self.initial_health, damage)
        for part, dmg in split.items():
            self.health[part] -= dmg
            self._zone_hit(part, dmg, damage_type, 0)
        if damage > 0:
            severity = "light" if damage <= 5 else "medium" if damage <= 10 else "heavy"
            self.add_bleeding_wound(severity, is_critical=critical)
        self._sync_total()
        if self.total_hp <= 0 and self.character.alive:
            self.character.die()
        logging.debug(f"Spread {damage} {damage_type} damage on {self.character.name}: {split}")
        return split

    def take_damage_to_zone(self, zone, damage, damage_type, critical=False):
        """Aimed hit that landed: full damage to one zone (floored at 0)."""
        if not self.character.alive:
            return 0
        if zone not in self.health:
            print(f"❌ Invalid zone: {zone}")
            return 0
        damage = int(damage * (1.2 if critical else 1.0))
        overflow = max(0, damage - self.health[zone])
        self.health[zone] = max(0, self.health[zone] - damage)
        self._zone_hit(zone, damage, damage_type, overflow)
        severity = "light" if damage <= 5 else "medium" if damage <= 10 else "heavy"
        self.add_bleeding_wound(severity, is_critical=critical and zone in ["chest", "stomach", "left_upper_leg", "right_upper_leg"])
        self._sync_total()
        if self.total_hp <= 0 and self.character.alive:
            self.character.die()
        logging.debug(f"{self.character.name} took {damage} {damage_type} damage to {zone}")
        return damage

    def resolve_aimed_strike(self, hit, zone, damage, damage_type, critical=False):
        """Aimed strike (flat -30 to hit, applied by the attack roll).
        A miss does NO damage and never falls back to a normal hit."""
        if not hit:
            return 0
        return self.take_damage_to_zone(zone, damage, damage_type, critical)


    def apply_partial_damage(self, zone):
        initial = self.initial_health.get(zone, 1)
        current = self.health.get(zone, 0)
        if current < initial * 0.5:
            penalty = 5  # 5% per threshold; can scale
            if 'leg' in zone:
                self.character.mobility_penalty += penalty
                print(f"⚠️ Partial damage to {zone}: +{penalty}% mobility penalty")
            elif 'arm' in zone:
                self.character.pain_penalty += penalty
                print(f"⚠️ Partial damage to {zone}: +{penalty}% pain penalty")
            # Add more for head/chest etc. if needed

    def apply_critical_wound(self, zone, damage_type, overflow):
        group = 'arm' if 'arm' in zone else 'leg' if 'leg' in zone else zone  # Map to group
        table = self.critical_wound_tables.get(group, {}).get(damage_type, [])
        if table:
            roll = random.randint(1, 100) + overflow
            roll = min(roll, 100)
            effect = table[roll - 1]
            print(f"Critical wound to {zone}: {effect}")
            # Apply mechanical effects based on effect (parse string or map to dict for penalties)
            # Example: if "severed" in effect.lower():
            #     self.character.pain_penalty += 20
            #     self.character.mobility_penalty += 25 if 'leg' in group else 0
            # Morale check if severe
            if roll > 50 or "severed" in effect.lower() or "fatal" in effect.lower():
                if not self.morale_check():
                    print(f"💔 {self.character.name} breaks from the wound!")
                    self.character.alive = False
                    self.character.in_combat = False

    def morale_check(self):
        roll = random.randint(1, 100)
        threshold = (self.character.willpower // 5) + 30 - (self.character.pain_penalty // 2)
        print(f"Morale check for {self.character.name}: Roll {roll} vs threshold {threshold}")
        return roll > threshold

    def bleed_out(self):
        self.apply_bleeding()
        self.total_hp = sum(self.health.values())
        if self.total_hp <= 0:
            self.character.alive = False
            print(f"💀 {self.character.name} bleeds out!")

    def recalculate_penalties(self):
        self.character.pain_penalty = sum(5 for key, hp in self.health.items() if hp < self.initial_health.get(key, 1) * 0.5)
        self.character.mobility_penalty = sum(5 for part in self.health if 'leg' in part and self.health[part] <= 0)
        print(f"📉 {self.character.name} recalculates penalties: Pain {self.character.pain_penalty}%, Mobility {self.character.mobility_penalty}%")