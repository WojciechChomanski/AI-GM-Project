# file: scripts/test_adventure.py
import random
from character import Character
from combat_engine import CombatEngine
from magic_system import MagicSystem
from npc_system import NPCSystem
from enemy_spawner import EnemySpawner
from faction_system import FactionSystem
from item_system import ItemSystem
from quest_system import QuestSystem
from status_effects import StatusEffects
from combat_health import CombatHealthManager
from healing_system import HealingSystem

def create_test_character(name, race, gender, class_name, stats):
    try:
        char = Character()
        char.name = name
        char.race = race
        char.gender = gender
        char.class_name = class_name
        char.total_hp = stats.get("hp", 100)
        char.health = char.total_hp
        char.max_stamina = stats.get("stamina", 100)
        char.stamina = char.max_stamina
        for stat, value in stats.items():
            setattr(char, stat, value)
        return char
    except Exception as e:
        print(f"❌ Error creating character {name}: {e}")
        return None

def test_adventure():
    try:
        combat_engine = CombatEngine()
        magic_system = MagicSystem()
        npc_system = NPCSystem()
        enemy_spawner = EnemySpawner()
        item_system = ItemSystem()
        quest_system = QuestSystem()
        healing_system = HealingSystem()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return

    # Create test party with Crusader Knight and Holy Judge
    party = [
        create_test_character("Grokthar", "Ogre", "Male", "Ogre_Brute", {
            "hp": 200, "stamina": 600, "strength": 20, "toughness": 15, "agility": -5, "endurance": 10
        }),
        create_test_character("Eldric", "Human", "Male", "Paladin", {
            "hp": 100, "stamina": 100, "strength": 10, "willpower": 10, "healing_bonus": 5
        }),
        create_test_character("Sylvara", "Elf", "Female", "Mage", {
            "hp": 80, "stamina": 110, "intelligence": 12, "agility": 5
        }),
        create_test_character("Thrain", "Dwarf", "Male", "Warrior", {
            "hp": 120, "stamina": 115, "strength": 12, "toughness": 10, "rune_craft": 5
        }),
        create_test_character("Baldric", "Human", "Male", "Crusader_Knight", {
            "hp": 110, "stamina": 105, "strength": 12, "willpower": 8
        }),
        create_test_character("Cassian", "Human", "Male", "Holy_Judge", {
            "hp": 90, "stamina": 100, "willpower": 12, "intelligence": 10
        })
    ]

    # Filter out failed character creations
    party = [char for char in party if char is not None]

    # Assign allies
    for char in party:
        char.allies = [c for c in party if c != char]

    # Scenario 1: Combat with Daughters of the Drowned Moon
    print("\n=== Scenario 1: Drowned Moon Ambush ===")
    enemies = enemy_spawner.spawn_enemy("veilspawn_leviathan", 1) + enemy_spawner.spawn_enemy("drowned_thrall", 2)
    for char in party:
        for enemy in enemies:
            combat_engine.attack_roll(
                attacker=char,
                defender=enemy,
                weapon_damage=20,
                damage_type="blunt",
                attacker_health=CombatHealthManager(char),
                defender_health=CombatHealthManager(enemy),
                environment="tight" if char.race == "Ogre" else "open"
            )
            if char.class_name == "Mage":
                magic_system.cast_spell(char, enemy, "tide_wail", CombatHealthManager(char), CombatHealthManager(enemy))
            elif char.class_name == "Paladin":
                magic_system.cast_spell(char, enemy, "divine_verdict", CombatHealthManager(char), CombatHealthManager(enemy))
            elif char.class_name == "Crusader_Knight":
                magic_system.cast_spell(char, enemy, "holy_smite", CombatHealthManager(char), CombatHealthManager(enemy))
            elif char.class_name == "Holy_Judge":
                magic_system.cast_spell(char, enemy, "judgment_call", CombatHealthManager(char), CombatHealthManager(enemy))

    # Scenario 2: Social Encounter with Lyssa
    print("\n=== Scenario 2: Saffron Veil Seduction ===")
    for char in party:
        faction_system = FactionSystem(char)
        npc_system.interact(char, "lyssa")
        item_system.use_item(char, "moonbloom_elixir", char)
        faction_system.align_with_faction("saffron_veil", 10)

    # Scenario 3: Iron Covenant Forge Defense
    print("\n=== Scenario 3: Iron Covenant Clash ===")
    enemies = enemy_spawner.spawn_enemy("clockwork_golem", 2)
    for char in party:
        for enemy in enemies:
            combat_engine.attack_roll(
                attacker=char,
                defender=enemy,
                weapon_damage=20,
                damage_type="blunt",
                attacker_health=CombatHealthManager(char),
                defender_health=CombatHealthManager(enemy)
            )
            if char.race == "Dwarf":
                magic_system.cast_spell(char, enemy, "rune_trap", CombatHealthManager(char), CombatHealthManager(enemy))
        faction_system = FactionSystem(char)
        faction_system.align_with_faction("iron_covenant", 20)

    # Scenario 4: Ogre Hunger Test
    print("\n=== Scenario 4: Ogre Hunger Crisis ===")
    for char in party:
        if char.race == "Ogre":
            char.consume_food(2000)  # Underfeed to trigger hunger
            char.reset_daily()

    # Scenario 5: Social Encounter with Drowned Matron
    print("\n=== Scenario 5: Drowned Moon Bargain ===")
    for char in party:
        faction_system = FactionSystem(char)
        npc_system.interact(char, "drowned_matron")
        if char.class_name == "Mage":
            magic_system.cast_spell(char, char, "salt_kiss", CombatHealthManager(char), CombatHealthManager(char))
        faction_system.align_with_faction("daughters_drowned_moon", 10)

    # Scenario 6: Breath Purge Test
    print("\n=== Scenario 6: Breath Purge Healing ===")
    for char in party:
        if char.class_name in ["Cleric", "Holy_Judge"]:
            for target in party:
                if any(e["name"] in ["salt_kiss", "taint_mark", "brine_marks"] for e in target.status_effects):
                    healing_system.breath_purge(char, target)

if __name__ == "__main__":
    test_adventure()