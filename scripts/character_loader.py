import json
import os
from character import Character
from armor_system import ArmorPiece

def load_json_file(path):
    with open(path, 'r') as file:
        return json.load(file)

def load_weapon(name):
    path = os.path.join("../rules/weapons.json")
    weapons_data = load_json_file(path)
    return weapons_data.get(name)

def load_race(name):
    path = os.path.join("../rules/races.json")
    races_data = load_json_file(path)
    return races_data.get(name)

def load_armor_piece(name, race):
    path = os.path.join("../rules/armors.json")
    armor_data = load_json_file(path)
    tier, variant = name.split("_") if "_" in name else (name, "standard")
    armor_stats = armor_data.get(tier, {}).get(race.lower() if race in ["Elven", "Dwarven"] else "standard")
    if not armor_stats:
        armor_stats = armor_data.get(tier, {}).get("standard")
    return ArmorPiece(
        name=armor_stats["name"],
        coverage=armor_stats["coverage"],
        armor_rating=armor_stats["armor_rating"],
        stamina_penalty=armor_stats["stamina_penalty"],
        max_durability=armor_stats["max_durability"],
        weight=armor_stats["weight"]
    )

def load_character_from_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)

    character = Character(
        name=data['name'],
        race=data['race'],
        total_hp=data['total_hp'],
        max_stamina=data['max_stamina']
    )
    character.armor_weight = data.get('armor_weight', 0)
    character.inventory_weight = data.get('inventory_weight', 0)
    character.shield_equipped = data.get('shield_equipped', False)
    character.weapon_equipped = data.get('weapon_equipped', True)

    if 'body_parts' in data:
        character.body_parts = data['body_parts']
    if 'strength_modifier' in data:
        character.strength_modifier = data['strength_modifier']
    if 'agility_modifier' in data:
        character.agility_modifier = data['agility_modifier']

    race_name = data.get("race")
    if race_name:
        race_stats = load_race(race_name)
        character.mass = race_stats.get("mass", 80)
        character.hp_bonus = race_stats.get("stats", {}).get("hp_bonus", 0)
        character.stamina_bonus = race_stats.get("stats", {}).get("stamina_bonus", 0)
        character.strength_modifier = race_stats.get("stats", {}).get("strength_modifier", 0)
        character.agility_modifier = race_stats.get("stats", {}).get("agility_modifier", 0)
        character.intelligence_modifier = race_stats.get("stats", {}).get("intelligence_modifier", 0)
        character.charisma_modifier = race_stats.get("stats", {}).get("charisma_modifier", 0)
        character.allowed_weapons = race_stats.get("equipment", {}).get("allowed_weapons", [])
        character.forbidden_weapons = race_stats.get("equipment", {}).get("forbidden_weapons", [])
        character.armor_preference = race_stats.get("equipment", {}).get("armor_preference", "standard")

    weapon_name = data.get("weapon")
    if weapon_name:
        character.weapon = load_weapon(weapon_name)
        valid_stances = character.weapon.get("stance_tree", ["neutral"])
        character.stance = valid_stances[-1] if valid_stances else "neutral"

    if character.race == "Ogre":
        character.weapon = {
            "name": "Improvised Club",
            "type": "improvised",
            "damage_type": "blunt",
            "base_damage": 15,
            "stance_tree": ["neutral"]
        }
        # Improvised straps
        character.armor = [
            load_armor_piece("Light_Light", "standard")
        ]
    else:
        for armor_name in data.get("armor", []):
            armor_piece = load_armor_piece(armor_name, character.armor_preference)
            character.equip_armor(armor_piece)

    return character