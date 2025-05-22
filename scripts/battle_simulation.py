from combat_engine import CombatEngine
from combat_health import CombatHealthManager
from character_loader import load_character_from_json
from armor_system import ArmorPiece
from healing_system import HealingSystem

# Load characters from JSON
wojtek = load_character_from_json("../rules/characters/wojtek.json")
gorthak = load_character_from_json("../rules/characters/gorthak.json")

# Equip Wojtek with armor and a Claymore
wojtek.equip_armor(ArmorPiece("Chainmail Chest", ["chest"], {"blunt": 10, "slash": 8}, 2, 50, 15))
wojtek.weapon = {"type": "claymore", "base_damage": 10, "damage_type": "slashing"}

# Equip Gorthak with a warhammer
gorthak.weapon = {"type": "warhammer", "base_damage": 12, "damage_type": "blunt"}

# Health Managers
wojtek_health = CombatHealthManager(wojtek)
gorthak_health = CombatHealthManager(gorthak)

# Systems
combat = CombatEngine()
healing = HealingSystem()

def simulate_battle():
    round_number = 1
    while wojtek.alive and gorthak.alive:
        print(f"\n🎛️⚔️ Round {round_number} ⚔️🎛️")

        wojtek.in_combat = True
        gorthak.in_combat = True

        # Wojtek attacks with Claymore
        combat.attack_roll(
            attacker=wojtek,
            defender=gorthak,
            weapon_damage=wojtek.weapon["base_damage"],
            damage_type=wojtek.weapon["damage_type"],
            attacker_health=wojtek_health,
            defender_health=gorthak_health
        )

        if gorthak.alive:
            # Gorthak attacks with warhammer
            combat.attack_roll(
                attacker=gorthak,
                defender=wojtek,
                weapon_damage=gorthak.weapon["base_damage"],
                damage_type=gorthak.weapon["damage_type"],
                attacker_health=gorthak_health,
                defender_health=wojtek_health
            )

        wojtek.in_combat = False
        gorthak.in_combat = False
        round_number += 1

    print("\n🎯 Battle finished!")

    if wojtek.alive and not gorthak.alive:
        print(f"\n🏆 {wojtek.name} wins the battle! {gorthak.name} is defeated.")
    elif gorthak.alive and not wojtek.alive:
        print(f"\n🏆 {gorthak.name} wins the battle! {wojtek.name} is defeated.")
    elif not wojtek.alive and not gorthak.alive:
        print("\n☠️ Both combatants have fallen. The battlefield is silent.")
    else:
        print("\n⚠️ Combat ended unexpectedly. Check logic.")

    if wojtek.alive:
        print("\n🩹 Wojtek tries to heal himself...")
        healing.attempt_bandage(healer=wojtek, target=wojtek)

if __name__ == "__main__":
    simulate_battle()