import json
import os
from character import Character
from armors import Armor

def load_json_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        raise Exception(f"Failed to load {path}: {e}")

def load_weapon(file_path):
    path = os.path.join(os.path.dirname(__file__), "../rules/weapons.json")
    weapons_data = load_json_file(path)
    return weapons_data.get(file_path, {"name": "none", "type": "none", "base_damage": 0, "damage_type": "blunt", "stance_tree": ["neutral"], "durability": 50})

def load_race(name):
    path = os.path.join(os.path.dirname(__file__), "../rules/races.json")
    races_data = load_json_file(path)
    return races_data.get(name, {})

def load_class(name):
    path = os.path.join(os.path.dirname(__file__), "../rules/classes.json")
    classes_data = load_json_file(path)
    return classes_data.get(name, {})

def load_background(name):
    path = os.path.join(os.path.dirname(__file__), "../rules/backgrounds.json")
    backgrounds_data = load_json_file(path)
    return backgrounds_data.get(name, {})

def load_stats(race, gender):
    path = os.path.join(os.path.dirname(__file__), "../rules/stats.json")
    stats_data = load_json_file(path)
    key = f"{race}_{gender}"
    return stats_data.get(key, {"starting_stats": {}, "max_stats": {}})

def load_armor_piece(name, race):
    path = os.path.join(os.path.dirname(__file__), "../rules/armors.json")
    armor_data = load_json_file(path)
    
    tier = name
    variant = race.lower() if race in ["Elven", "Dwarven"] else "standard"
    
    armor_stats = armor_data.get(tier, {}).get(variant, armor_data.get(tier, {}).get("standard"))
    if not armor_stats:
        armor_stats = {
            "name": "Default Cloth",
            "coverage": ["chest"],
            "armor_rating": {"slashing": 1, "piercing": 1, "blunt": 1},
            "max_durability": 40,
            "weight": 5,
            "stamina_penalty": 1,
            "mobility_bonus": 5
        }
    
    return Armor(
        name=armor_stats["name"],
        coverage=armor_stats["coverage"],
        armor_rating=armor_stats["armor_rating"],
        max_durability=armor_stats["max_durability"]
    )

def load_character_from_json(file_path):
    try:
        abs_path = os.path.join(os.path.dirname(__file__), file_path)
        with open(abs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        raise Exception(f"Failed to load character from {file_path}: {e}")

    character = Character()
    character.name = data.get('name', 'Unknown')
    character.race = data.get('race', 'Human')
    character.gender = data.get('gender', 'Male')
    character.class_name = data.get('class', '')
    character.background = data.get('background', '')
    character.total_hp = data.get('total_hp', 100)
    character.max_stamina = data.get('max_stamina', 100)
    character.stamina = character.max_stamina
    character.armor_weight = data.get('armor_weight', 0)
    character.inventory_weight = data.get('inventory_weight', 0)
    character.shield_equipped = data.get('shield_equipped', False)
    character.weapon_equipped = data.get('weapon_equipped', True)

    if 'body_parts' not in data:
        character.body_parts = {
            "left_lower_leg": 10, "right_lower_leg": 10, "left_upper_leg": 15, "right_upper_leg": 15,
            "stomach": 20, "chest": 25, "left_lower_arm": 5, "right_lower_arm": 5,
            "left_upper_arm": 10, "right_upper_arm": 10, "head": 10, "throat": 5, "groin": 5
        }
    else:
        character.body_parts = data['body_parts']

    # Load base stats
    stats = load_stats(character.race, character.gender)
    for stat in ['strength', 'toughness', 'agility', 'mobility', 'dexterity', 'endurance', 'intelligence', 'willpower', 'perception', 'charisma', 'corruption_level', 'stress_level', 'weapon_skill', 'faith', 'reputation']:
        setattr(character, stat, stats["starting_stats"].get(stat, 20))

    # Apply class modifiers
    class_data = load_class(character.class_name)
    if class_data:
        class_stats = class_data.get("stats", {})
        for stat, value in class_stats.items():
            if hasattr(character, stat):
                current = getattr(character, stat, 20)
                setattr(character, stat, current + value)

    # Apply background modifiers
    background_data = load_background(character.background)
    if background_data:
        bg_stats = background_data.get("stats", {})
        for stat, value in bg_stats.items():
            if hasattr(character, stat):
                current = getattr(character, stat, 20)
                setattr(character, stat, current + value)

    # Load modifiers from JSON
    for attr in ['strength_modifier', 'agility_modifier', 'charisma_modifier']:
        if attr in data:
            setattr(character, attr, data[attr])

    race_name = data.get("race")
    if race_name:
        race_stats = load_race(race_name)
        character.mass = race_stats.get("mass", 80)
        for stat in ['hp_bonus', 'stamina_cost_modifier', 'strength_modifier', 'agility_modifier', 'intelligence_modifier', 'charisma_modifier']:
            if stat in race_stats.get("stats", {}):
                setattr(character, stat, race_stats["stats"][stat])
        character.allowed_weapons = race_stats.get("equipment", {}).get("allowed_weapons", [])
        character.forbidden_weapons = race_stats.get("equipment", {}).get("forbidden_weapons", [])
        character.armor_preference = race_stats.get("equipment", {}).get("armor_preference", "standard")

    weapon_name = data.get("weapon")
    if weapon_name:
        character.weapon = load_weapon(weapon_name)
        valid_stances = character.weapon.get("stance_tree", ["neutral"])
        character.stance = valid_stances[0] if valid_stances else "neutral"

    if character.race == "Ogre":
        character.weapon = {
            "name": "Improvised Club",
            "type": "improvised",
            "damage_type": "blunt",
            "base_damage": 15,
            "stance_tree": ["neutral"],
            "durability": 60
        }
        character.armor = [load_armor_piece("Light_Heavy", "standard")]
    else:
        for armor_name in data.get("armor", []):
            armor_piece = load_armor_piece(armor_name, character.armor_preference)
            character.armor.append(armor_piece)

    character.apply_armor_penalties()
    return character