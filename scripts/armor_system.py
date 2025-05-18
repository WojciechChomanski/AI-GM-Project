# file: armor_system.py

class ArmorPiece:
    def __init__(self, name, coverage, armor_rating, stamina_penalty, max_durability, weight):
        self.name = name
        self.coverage = coverage  # list of body parts it covers
        self.armor_rating = armor_rating  # dict: damage_type -> value
        self.stamina_penalty = stamina_penalty  # stamina tax while equipped
        self.max_durability = max_durability
        self.current_durability = max_durability
        self.weight = weight  # NEW: weight of the armor piece for encumbrance

    def absorb_damage(self, damage, damage_type):
        """Absorb damage and reduce durability accordingly."""
        protection = self.armor_rating.get(damage_type, 0)

        if self.current_durability <= 0:
            print(f"⚠️ {self.name} is broken and offers no protection!")
            return damage  # Armor is useless now

        effective_protection = protection

        # Durability penalties
        if self.current_durability < 0.75 * self.max_durability:
            effective_protection *= 0.75
        if self.current_durability < 0.5 * self.max_durability:
            effective_protection *= 0.5
        if self.current_durability < 0.25 * self.max_durability:
            effective_protection *= 0.25

        reduced_damage = max(0, damage - effective_protection)

        # Damage to durability (always some small percentage of incoming raw hit)
        durability_loss = max(1, int(damage * 0.2))
        self.current_durability -= durability_loss
        if self.current_durability < 0:
            self.current_durability = 0

        print(f"🛡️ {self.name} absorbed {damage - reduced_damage:.1f} damage. Remaining Durability: {self.current_durability}/{self.max_durability}")

        return reduced_damage

    def condition_status(self):
        """Return human-readable condition."""
        durability_percent = (self.current_durability / self.max_durability) * 100

        if durability_percent >= 90:
            return "Pristine"
        elif durability_percent >= 75:
            return "Good"
        elif durability_percent >= 50:
            return "Worn"
        elif durability_percent >= 25:
            return "Damaged"
        elif durability_percent > 0:
            return "Critical"
        else:
            return "Broken"

    def repair(self, skill_level):
        """Attempt to repair armor based on blacksmithing or crafting skill."""
        if self.current_durability <= 0:
            print(f"💀 {self.name} is beyond repair and needs full replacement!")
            return

        repair_effectiveness = 0.2 + (skill_level * 0.05)  # Skill level improves repair efficiency
        repair_amount = int(self.max_durability * repair_effectiveness)

        # However, armor that dropped below 50% max can never return to 100%
        if self.max_durability - self.current_durability > self.max_durability * 0.5:
            max_possible = int(self.max_durability * 0.85)
            self.current_durability = min(self.current_durability + repair_amount, max_possible)
        else:
            self.current_durability = min(self.current_durability + repair_amount, self.max_durability)

        print(f"🔧 Repaired {self.name}! New durability: {self.current_durability}/{self.max_durability}")
