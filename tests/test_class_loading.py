"""Class stat bonuses load from rules/classes/*.json, once, capped (docs/CLEANUP_NOTES.md)."""
import os, sys, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from character_loader import CharacterLoader, find_class, class_stat_bonuses


def load(data):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(data, f)
    try:
        return CharacterLoader().load_character_from_json(f.name)
    finally:
        os.unlink(f.name)


def test_find_class():
    assert find_class("Crusader_Knight")["stat_modifiers"]["strength"] == 12
    assert find_class("ogre_brute") and find_class("Nope") == {}


def test_crusader_plus_12_once():
    c = load({"name": "K", "race": "Human", "gender": "Male", "class": "Crusader_Knight"})
    assert (c.strength, c.toughness, c.agility, c.willpower) == (47, 45, 35, 33)


def test_legacy_scaled_and_capped():
    assert class_stat_bonuses({"stats": {"strength_modifier": 4, "mass_base": 600}}) == {"strength": 12}
    assert class_stat_bonuses({"stat_modifiers": {"strength": 12}, "stats": {"strength_modifier": 12}}) == {"strength": 12}
    c = load({"name": "K", "race": "Human", "gender": "Male", "class": "Crusader_Knight", "background": "Outlaw"})
    assert c.strength == 50  # 35 + 12 + 3 = 50, at the human cap
    c = load({"name": "O", "race": "Ogre", "gender": "Male", "class": "Ogre_Brute"})
    assert c.strength == 62 and c.agility == 14  # STR 50 + 4x3; AGI 20 - 2x3


def test_cap_honours_talent():
    big = {"name": "K", "race": "Human", "gender": "Male", "class": "Crusader_Knight", "background": "Outlaw"}
    assert load(big).strength <= 50
    assert load(dict(big, talents=["iron_thewed"])).strength == 50
