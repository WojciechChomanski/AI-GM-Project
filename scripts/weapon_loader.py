import json
import os


def load_weapon(weapon_name: str):
    """
    Loads weapon stats from rules/weapons.json by name.
    Falls back to a sensible generic if not found.
    """
    path = os.path.join(os.path.dirname(__file__), "../rules/weapons.json")
    with open(path, "r", encoding="utf-8") as f:
        weapons_data = json.load(f)

    data = weapons_data.get(weapon_name)
    if isinstance(data, dict):
        # Ensure minimum fields exist
        return {
            "type": data.get("type", weapon_name),
            "base_damage": int(data.get("base_damage", 10)),
            "damage_type": data.get("damage_type", "slashing"),
            "durability": int(data.get("durability", 60)),
            "name": data.get("name", weapon_name.title()),
        }

    # Fallback: generic weapon using the provided name
    return {
        "type": weapon_name,
        "base_damage": 10,
        "damage_type": "slashing",
        "durability": 60,
        "name": weapon_name.title(),
    }
