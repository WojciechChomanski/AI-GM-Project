# file: scripts/shield_system.py

class Shield:
    def __init__(self, name, durability, stamina_penalty, block_bonus):
        self.name = name
        self.max_durability = durability
        self.current_durability = durability
        self.stamina_penalty = stamina_penalty
        self.block_bonus = block_bonus

    def absorb_damage(self, damage):
        """Shield absorbs incoming damage, reducing its durability."""
        durability_loss = max(1, int(damage * 0.2))  # Shields lose 20% of incoming damage as durability loss
        self.current_durability -= durability_loss
        if self.current_durability < 0:
            self.current_durability = 0
        print(f"🛡️ {self.name} absorbed damage! Current durability: {self.current_durability}/{self.max_durability}")

    def is_broken(self):
        """Returns True if the shield is broken and no longer functional."""
        return self.current_durability <= 0

    def condition_status(self):
        """Returns a human-readable condition status based on durability."""
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