# file: scripts/first_aid.py

class FirstAidSystem:
    def __init__(self):
        pass

    def attempt_bandage(self, healer, target):
        # Assume bandaging is always attempted after battle manually

        if not target.alive:
            print(f"{target.name} is dead. Cannot treat dead characters.")
            return False

        bleeding = target.bleeding

        if bleeding == 0:
            print(f"{target.name} is not bleeding and does not need bandaging.")
            return True

        if bleeding <= 3:
            difficulty = 30  # Light bleeding
        elif bleeding <= 6:
            difficulty = 35  # Moderate bleeding
        else:
            difficulty = 40  # Heavy bleeding

        from random import randint
        roll = randint(1, 100)

        print(f"🎲 {healer.name} attempts to bandage {target.name} (needs {difficulty}+): rolled {roll}")

        if roll >= difficulty:
            print(f"🩹 Success! {target.name}'s bleeding is stopped!")
            target.bleeding = 0
            return True
        else:
            print(f"❌ Failed! {target.name} is still bleeding.")
            return False