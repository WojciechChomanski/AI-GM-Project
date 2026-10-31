import json
from zone_hp import scaled_zones, hp_multiplier, total_hp as zones_total
import os
from character import Character
from armors import Armor

def _find_hp_percent(class_data):
    """Class HP bonus in percent (e.g. Crusader Knight 15)."""
    for block, key in (("stat_modifiers", "hp_percent"), ("stats", "hp_percent_bonus")):
        val = (class_data.get(block) or {}).get(key)
        if val:
            return val
    return class_data.get("hp_percent", 0) or 0


class CharacterLoader:
    def __init__(self, base_dir="res://characters/characters"):
        self.base_dir = base_dir
        self.characters = {}

    def load_json_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            raise Exception(f"Failed to load {path}: {e}")

    def load_weapon(self, name):
        path = os.path.join(os.path.dirname(__file__), "../rules/weapons.json")
        weapons_data = self.load_json_file(path)
        return weapons_data.get(name, {"name": "none", "type": "none", "base_damage": 0, "damage_type": "blunt", "stance_tree": ["neutral"], "durability": 50})

    def load_race(self, name):
        path = os.path.join(os.path.dirname(__file__), "../rules/races.json")
        races_data = self.load_json_file(path)
        return races_data.get(name, {})

    def load_class(self, name):
        path = os.path.join(os.path.dirname(__file__), "../rules/classes.json")
        classes_data = self.load_json_file(path)
        return classes_data.get(name, {})

    def load_background(self, name):
        path = os.path.join(os.path.dirname(__file__), "../rules/backgrounds.json")
        backgrounds_data = self.load_json_file(path)
        return backgrounds_data.get(name, {})

    def load_stats(self, race, gender):
        path = os.path.join(os.path.dirname(__file__), "../rules/stats.json")
        stats_data = self.load_json_file(path)
        key = f"{race}_{gender}"
        return stats_data.get(key, {"starting_stats": {}, "max_stats": {}})

    def load_armor_piece(self, name, race):
        path = os.path.join(os.path.dirname(__file__), "../rules/armors.json")
        armor_data = self.load_json_file(path)
        
        tier = name
        variant = race.lower() if race in ["Elven", "Dwarven"] else "standard"
        
        armor_stats = armor_data.get(tier, {}).get(variant, armor_data.get(tier, {}).get("standard"))
        if not armor_stats:
            legacy_path = os.path.join(os.path.dirname(__file__), "../rules/armore.json")
            if os.path.exists(legacy_path):
                legacy_data = self.load_json_file(legacy_path)
                armor_stats = legacy_data.get(tier, {})
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
        
        armor = Armor(
            name=armor_stats["name"],
            coverage=armor_stats["coverage"],
            armor_rating=armor_stats["armor_rating"],
            max_durability=armor_stats["max_durability"],
            weight=armor_stats.get("weight", 0),
            stamina_penalty=armor_stats.get("stamina_penalty", 0),
            mobility_bonus=armor_stats.get("mobility_bonus", 0)
        )
        return armor

    def load_character(self, character_name):
        if character_name in self.characters:
            return self.characters[character_name]

        file_path = os.path.join(self.base_dir, f"{character_name.lower()}.json")
        if not os.path.exists(file_path):
            print(f"⚠️ Character file not found: {file_path}")
            return None

        character = self.load_character_from_json(file_path)
        if character:
            self.characters[character_name] = character
            return character
        else:
            print(f"❌ Failed to load character: {character_name}")
            return None

    def load_character_from_json(self, file_path):
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
        character.max_stamina = data.get('max_stamina', 100)
        character.stamina = character.max_stamina
        character.armor_weight = data.get('armor_weight', 0)
        character.inventory_weight = data.get('inventory_weight', 0)
        character.shield_equipped = data.get('shield_equipped', False)
        character.weapon_equipped = data.get('weapon_equipped', True)
        character.talents = list(data.get('talents', []))
        character.flaws = list(data.get('flaws', []))
        character.progression = dict(data.get('progression', {}))

        stats = self.load_stats(character.race, character.gender)
        for stat in ['strength', 'toughness', 'agility', 'mobility', 'dexterity', 'endurance', 'intelligence', 'willpower', 'perception', 'charisma', 'corruption_level', 'stress_level', 'weapon_skill', 'ballistic_skill', 'faith', 'reputation']:
            setattr(character, stat, stats["starting_stats"].get(stat, 20))

        class_data = self.load_class(character.class_name)
        if class_data:
            class_stats = class_data.get("stats", {})
            for stat, value in class_stats.items():
                if hasattr(character, stat):
                    current = getattr(character, stat, 20)
                    setattr(character, stat, current + value)
            character.abilities = class_data.get("abilities", {})
            character.skills = class_data.get("skills", {})
            character.traits = class_data.get("traits", [])

        background_data = self.load_background(character.background)
        if background_data:
            bg_stats = background_data.get("stats", {})
            for stat, value in bg_stats.items():
                if hasattr(character, stat):
                    current = getattr(character, stat, 20)
                    setattr(character, stat, current + value)

        for attr in ['strength_modifier', 'agility_modifier', 'charisma_modifier']:
            if attr in data:
                setattr(character, attr, data[attr])

        race_name = data.get("race")
        if race_name:
            race_stats = self.load_race(race_name)
            character.mass = race_stats.get("mass", 80)
            for stat in ['hp_bonus', 'stamina_cost_modifier', 'strength_modifier', 'agility_modifier', 'intelligence_modifier', 'charisma_modifier']:
                if stat in race_stats.get("stats", {}):
                    setattr(character, stat, race_stats["stats"][stat])
            character.allowed_weapons = race_stats.get("equipment", {}).get("allowed_weapons", [])
            character.forbidden_weapons = race_stats.get("equipment", {}).get("forbidden_weapons", [])
            character.armor_preference = race_stats.get("equipment", {}).get("armor_preference", "standard")

        weapon_name = data.get("weapon")
        if weapon_name:
            character.weapon = self.load_weapon(weapon_name)
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
            character.armor = [self.load_armor_piece("Light_Heavy", "standard")]
        else:
            for armor_name in data.get("armor", []):
                armor_piece = self.load_armor_piece(armor_name, character.armor_preference)
                character.armor.append(armor_piece)
                character.armor_weight += armor_piece.weight

        # Zone HP: base 100 scaled by race hp_bonus and class hp_percent (see docs/ZONE_DAMAGE.md).
        # Priority: explicit body_parts > legacy file total_hp (spread over zones) > race/class.
        if 'body_parts' in data:
            character.body_parts = dict(data['body_parts'])
        elif data.get('total_hp'):
            character.body_parts = scaled_zones(data['total_hp'] / 100.0)
        else:
            race_bonus = getattr(character, 'hp_bonus', 0) or 0
            class_pct = 0
            if class_data:
                class_pct = _find_hp_percent(class_data)
            character.body_parts = scaled_zones(hp_multiplier(race_bonus, class_pct))
        character.max_body_parts = dict(character.body_parts)
        character.total_hp = zones_total(character.body_parts)
        character.health = character.total_hp

        character.apply_armor_penalties()
        return character

if __name__ == "__main__":
    loader = CharacterLoader()
    character = loader.load_character("torvald")
    if character:
        print(f"Loaded: {character.name}, HP: {character.total_hp}, Stamina: {character.stamina}")
        print(f"Abilities: {character.abilities}")
        print(f"Skills: {character.skills}")
        print(f"Traits: {character.traits}")