# file: scripts/healing_system.py

class HealingSystem:
    def attempt_bandage(self, healer, target):
        """Attempt to stop bleeding with basic bandage."""
        if not target.alive:
            print(f"{target.name} is dead. Bandaging is pointless.")
            return False

        bleeding_level = target.bleeding

        # Determine difficulty based on bleeding severity
        if bleeding_level <= 3:
            difficulty = 30  # Light bleeding
        elif bleeding_level <= 6:
            difficulty = 35  # Moderate bleeding
        else:
            difficulty = 40  # Heavy bleeding

        roll = self.roll_check()
        total_roll = roll - healer.pain_penalty - healer.stamina_penalty()

        print(f"🩹 {healer.name} attempts bandaging with a roll of {total_roll} (raw roll: {roll}) against difficulty {difficulty}.")

        if total_roll >= difficulty:
            print(f"✅ Bandaging successful! {target.name}'s bleeding is stopped.")
            target.bleeding = 0
            return True
        else:
            print(f"❌ Bandaging failed. {target.name} continues bleeding.")
            return False

    def roll_check(self):
        """Simulate a simple random roll."""
        import random
        return random.randint(1, 100)