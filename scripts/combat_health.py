# file: scripts/combat_health.py
import random
import logging
from damage_consequences import DamageConsequences
from armor_system import worn_pieces, armor_vs_aimed, armor_vs_spread
import bleeding
from zone_hp import BASE_ZONES, spread_damage, total_hp, VITAL_ZONES, SPREAD_EXCLUDED, SPREAD_FLOOR, COLLAPSE_ZONES_AT_ZERO, zones_at_zero

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Bleeding never takes ANY zone below 1 (no destroyed limbs from blood loss)
BLEED_FLOOR = {z: 1 for z in BASE_ZONES}


class CombatHealthManager:
    def __init__(self, character):
        self.character = character
        self.health = {part: hp for part, hp in character.body_parts.items()}
        self.initial_health = self.health.copy()
        self.total_hp = sum(self.health.values())
        self.starting_hp = self.total_hp
        self.bleeding_wounds = []
        if getattr(character, "race", None) == "Dwarf" and not hasattr(character, "bleed_clot_mult"):
            character.bleed_clot_mult = 0.8  # rules/lore/dwarves.json bleed_duration_multiplier
        self.character.health_manager = self  # lets healing scripts find the real wound list
        self.consequences = DamageConsequences()
        self.last_armor_report = None  # what armour did on the most recent hit
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

    # ---- Bleeding (see docs/BLEEDING.md; numbers are placeholders) ----
    def refresh_bleeding(self):
        """Drop stopped wounds and sync the HP/round figure other code reads."""
        self.bleeding_wounds = [w for w in self.bleeding_wounds if w["rate"] > 0]
        self.character.bleeding = bleeding.current_rate(self.bleeding_wounds)
        self.character.bleeding_rate = self.character.bleeding
        return self.character.bleeding

    def add_bleeding_wound(self, zone, damage, damage_type, critical=False, artery=False, breath=False):
        """Add a wound for `damage` that got through armour (None if it does not bleed)."""
        if not artery and any(w["zone"] == zone and w["kind"] == "artery" and w["age"] == 0 for w in self.bleeding_wounds):
            return None  # this very hit already cut an artery here: no extra wound on top
        if artery and any(w["zone"] == zone and w["kind"] == "artery" for w in self.bleeding_wounds):
            artery = False  # one artery wound per zone: the same artery cannot be cut twice
            critical = True
        w = bleeding.make_wound(zone, damage, damage_type, critical, artery,
                                getattr(self.character, "bleed_rate_mult", 1.0))
        if w and breath:
            import wound_recovery as recovery
            w = recovery.breath_wound(w)
        if w:
            self.bleeding_wounds.append(w)
            self.refresh_bleeding()
        return w

    def apply_bleeding(self):
        """One round of bleeding. All wounds together lose at most BLEED_CAP HP, taken as ONE
        spread over the body (throat/groin excluded, head floor 1) and never taking ANY zone
        below 1: bleeding cannot destroy a limb or roll crits. If every zone that can bleed is
        already at 1 and blood loss is still pending, the chest 'would reach 0' = the character
        bleeds out. Returns the HP lost."""
        if not self.bleeding_wounds or not self.character.alive:
            return 0
        wanted = bleeding.current_rate(self.bleeding_wounds)
        lost = 0
        if wanted > 0:
            split = spread_damage(self.health, self.initial_health, wanted, SPREAD_EXCLUDED, BLEED_FLOOR)
            for part, dmg in split.items():
                self.health[part] -= dmg
                lost += dmg
                self._zone_hit(part, dmg, "bleeding", 0)
            self._sync_total()
            print(f"🩸 {self.character.name} suffers {lost} bleeding damage!")
        clot = getattr(self.character, "bleed_clot_mult", 1.0)
        for w in self.bleeding_wounds:
            bleeding.tick_wound(w, clot)
        self.refresh_bleeding()
        if lost < wanted and self.character.alive:
            print(f"💀 {self.character.name} bleeds out!")
            self.character.die()
        else:
            self.check_zone_collapse()
        return lost

    def bandage(self, healer, item):
        """Treat this character's real wound list (see bleeding.attempt_bandage)."""
        return bleeding.attempt_bandage(healer, self.character, item, self)

    def apply_pain(self):
        if self.character.pain_penalty >= 30:
            print(f"⚠️ {self.character.name} is overwhelmed by pain penalties!")
            self.check_auto_collapse()

    def check_zone_collapse(self):
        """Collapse when 3 or more body zones are at 0 HP. (The old '33% of total HP
        lost' blood-loss collapse was removed - see docs/ZONE_DAMAGE.md.)"""
        if len(zones_at_zero(self.health)) >= COLLAPSE_ZONES_AT_ZERO and self.character.alive:
            print(f"💀 {self.character.name} collapses from severe injuries!")
            self.character.alive = False
            self.character.in_combat = False
            self.character.exhausted = True
            self.character.last_action = True
            return True
        return False

    def check_auto_collapse(self):
        if self.check_zone_collapse():
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
                effect = self.consequences.apply_consequence(self.character, zone, damage_type, overflow)
                crit_text = self.apply_critical_wound(zone, damage_type, overflow) or ""
                if "severed" in crit_text.lower() and "tendon" not in crit_text.lower():
                    self.limb_state = getattr(self, "limb_state", {})
                    self.limb_state[zone] = "severed"  # scripts/limb_repair.py
                # a crit result that cuts an artery / the jugular makes an artery wound (never from blunt)
                if damage_type != "blunt" and (effect == "Artery Slashed" or any(k in crit_text.lower() for k in ("artery", "jugular"))):
                    self.add_bleeding_wound(zone, max(1, damage), damage_type, True, True)
            if zone in VITAL_ZONES and self.character.alive:
                print(f"💀 {self.character.name}'s {zone.replace('_', ' ')} is destroyed!")
                self.character.die()
            elif hasattr(self.character, "on_part_crippled") and zone not in getattr(self.character, "compromised_limbs", []):
                self.character.on_part_crippled(zone)
        else:
            self.apply_partial_damage(zone)

    def distribute_damage(self, base_damage, damage_type, critical=False, use_armor=True, artery=False):
        """Normal hit: armour (weighted average over all zones) reduces the damage,
        then the remainder is spread over the whole body, weighted by zone size."""
        if not self.character.alive:
            return {}
        damage = int(base_damage * (1.2 if critical else 1.0))
        self.last_armor_report = None
        pieces = worn_pieces(self.character) if use_armor else []
        if pieces:
            self.last_armor_report = armor_vs_spread(pieces, damage, damage_type)
            damage = self.last_armor_report["remainder"]
            print(f"🛡️ Armour absorbed {self.last_armor_report['absorbed']} "
                  f"(average protection {self.last_armor_report['average']}); {damage} gets through.")
        split = spread_damage(self.health, self.initial_health, damage, SPREAD_EXCLUDED, SPREAD_FLOOR)
        for part, dmg in split.items():
            self.health[part] -= dmg
            self._zone_hit(part, dmg, damage_type, 0)
        if damage > 0 and split:
            # a spread hit has no single zone: the wound sits where it hurt most (ties: the earlier zone)
            wound_zone = max(split, key=lambda z: (split[z], -list(self.health).index(z)))
            self.add_bleeding_wound(wound_zone, damage, damage_type, critical, artery)
        self._sync_total()
        self.check_zone_collapse()
        if self.total_hp <= 0 and self.character.alive:
            self.character.die()
        logging.debug(f"Spread {damage} {damage_type} damage on {self.character.name}: {split}")
        return split

    def take_damage_to_zone(self, zone, damage, damage_type, critical=False, use_armor=True, artery=False):
        """Aimed hit that landed: the armour on that zone reduces the damage, the
        remainder goes fully into that one zone (floored at 0)."""
        if not self.character.alive:
            return 0
        if zone not in self.health:
            print(f"❌ Invalid zone: {zone}")
            return 0
        damage = int(damage * (1.2 if critical else 1.0))
        self.last_armor_report = None
        pieces = worn_pieces(self.character) if use_armor else []
        if pieces:
            self.last_armor_report = armor_vs_aimed(pieces, zone, damage, damage_type)
            damage = self.last_armor_report["remainder"]
            print(f"🛡️ Armour on {zone.replace('_', ' ')} absorbed {self.last_armor_report['absorbed']}; {damage} gets through.")
            if damage <= 0:
                return 0
        overflow = max(0, damage - self.health[zone])
        self.health[zone] = max(0, self.health[zone] - damage)
        self._zone_hit(zone, damage, damage_type, overflow)
        self.add_bleeding_wound(zone, damage, damage_type, critical, artery)
        self._sync_total()
        self.check_zone_collapse()
        if self.total_hp <= 0 and self.character.alive:
            self.character.die()
        logging.debug(f"{self.character.name} took {damage} {damage_type} damage to {zone}")
        return damage

    def resolve_aimed_strike(self, hit, zone, damage, damage_type, critical=False, artery=False):
        """Aimed strike (-30 to hit, -40 for head/throat/groin; applied by the attack roll).
        A miss does NO damage and never falls back to a normal hit."""
        if not hit:
            return 0
        return self.take_damage_to_zone(zone, damage, damage_type, critical, artery=artery)


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
            return effect
        return None

    def morale_check(self):
        roll = random.randint(1, 100)
        threshold = (self.character.willpower // 5) + 30 - (self.character.pain_penalty // 2)
        print(f"Morale check for {self.character.name}: Roll {roll} vs threshold {threshold}")
        return roll > threshold

    def bleed_out(self):
        """One bleeding round (death by blood loss is decided in apply_bleeding)."""
        return self.apply_bleeding()

    def recalculate_penalties(self):
        self.character.pain_penalty = sum(5 for key, hp in self.health.items() if hp < self.initial_health.get(key, 1) * 0.5)
        self.character.mobility_penalty = sum(5 for part in self.health if 'leg' in part and self.health[part] <= 0)
        print(f"📉 {self.character.name} recalculates penalties: Pain {self.character.pain_penalty}%, Mobility {self.character.mobility_penalty}%")