# file: scripts/json_loader.py

import json
from character import Character

def load_character_from_json(file_path):
    """Load a character from a JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    character = Character(
        name=data['name'],
        race=data['race'],
        total_hp=data['total_hp'],
        max_stamina=data['max_stamina']
    )

    character.body_parts = data['body_parts']
    character.stamina = data['current_stamina']
    character.alive = data['alive']
    character.bleeding = data['bleeding']
    character.pain_penalty = data['pain_penalty']
    character.armor_weight = data['armor_weight']
    character.inventory_weight = data['inventory_weight']
    character.shield_equipped = data['shield_equipped']
    character.weapon_equipped = data['weapon_equipped']

    return character

def save_character_to_json(character, file_path):
    """Save a character to a JSON file."""
    data = {
        "name": character.name,
        "race": character.race,
        "total_hp": character.total_hp,
        "max_stamina": character.max_stamina,
        "current_stamina": character.stamina,
        "body_parts": character.body_parts,
        "alive": character.alive,
        "bleeding": character.bleeding,
        "pain_penalty": character.pain_penalty,
        "armor_weight": character.armor_weight,
        "inventory_weight": character.inventory_weight,
        "shield_equipped": character.shield_equipped,
        "weapon_equipped": character.weapon_equipped
    }

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)