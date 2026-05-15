# file: scripts/weapon_loader.py
import json
import os

def load_weapon(weapon_name):
    path = os.path.join(os.path.dirname(__file__), "../rules/weapons.json")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            weapons_data = json.load(f)
        weapon = weapons_data.get(weapon_name)
        if weapon:
            return weapon
        else:
            print(f"⚠️ Weapon '{weapon_name}' not found in weapons.json.")
            return {
                "type": weapon_name,
                "base_damage": 10,
                "damage_type": "slashing",
                "durability": 30
            }
    except FileNotFoundError:
        print(f"❌ Missing file: {path}")
        return {
            "type": weapon_name,
            "base_damage": 10,
            "damage_type": "slashing",
            "durability": 30
        }
