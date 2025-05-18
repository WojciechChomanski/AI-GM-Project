# file: scripts/healing_items.py

class HealingItem:
    def __init__(self, name, bleed_stop_amount, difficulty_threshold, max_uses=1):
        self.name = name
        self.bleed_stop_amount = bleed_stop_amount  # How much bleeding it can stop
        self.difficulty_threshold = difficulty_threshold  # Difficulty to succeed
        self.max_uses = max_uses  # How many times it can be used
        self.remaining_uses = max_uses

    def use(self):
        if self.remaining_uses <= 0:
            print(f"❌ {self.name} has no uses left!")
            return False
        self.remaining_uses -= 1
        return True

# ✅ Define available healing items
basic_bandage = HealingItem(
    name="Basic Bandage",
    bleed_stop_amount=3,    # Stops light bleeding (1-3 bleed per round)
    difficulty_threshold=30,  # Requires 30+ roll to succeed
    max_uses=1
)

improved_bandage = HealingItem(
    name="Improved Bandage",
    bleed_stop_amount=6,    # Stops moderate bleeding (4-6 bleed per round)
    difficulty_threshold=35,  # Requires 35+ roll to succeed
    max_uses=1
)

herbal_poultice = HealingItem(
    name="Herbal Poultice",
    bleed_stop_amount=9,    # Stops heavy bleeding (7-9 bleed per round)
    difficulty_threshold=40,  # Requires 40+ roll to succeed
    max_uses=1
)

# ✅ Available healing items dictionary
healing_items = {
    "basic_bandage": basic_bandage,
    "improved_bandage": improved_bandage,
    "herbal_poultice": herbal_poultice,
}