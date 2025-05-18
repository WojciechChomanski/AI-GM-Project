# ✅ Updated: character_loader.py — now supports armor loading from armor.json

import json
import os
from character import Character
from armor_system import ArmorPiece

# Helper: Load any JSON file

def load_json_file(path):
    with open(path, 'r') as file:
        return json.load(file)

# Load a weapon from weapons.json

def load_weapon(name):
    path = os.path.join("../rules/weapons.json")
    weapons_data = load_json_file(path)
    return weapons_data.get(name)

# Load armor piece from armor.json

def load_armor_piece(name):
    path = os.path.join("../rules/armor.json")
    armor_data = load_json_file(path)
    return armor_data.get(name)

# Load full character from file

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

    # Weapon setup
    weapon_name = data.get("weapon")
    if weapon_name:
        character.weapon = load_weapon(weapon_name)
        character.stance = character.weapon.get("stance_tree", ["neutral"])[-1]

    # Armor setup
    for armor_name in data.get("armor", []):
        armor_stats = load_armor_piece(armor_name)
        if armor_stats:
            armor_piece = ArmorPiece(
                name=armor_stats["name"],
                coverage=armor_stats["coverage"],
                armor_rating=armor_stats["armor_rating"],
                stamina_penalty=armor_stats["stamina_penalty"],
                max_durability=armor_stats["max_durability"],
                weight=armor_stats["weight"]
            )
            character.equip_armor(armor_piece)

    return character
