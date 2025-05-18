# file: scripts/fetch_data.py

import json
import os

# Set base folder for JSON files
BASE_FOLDER = os.path.join(os.path.dirname(__file__), "..", "rules")

def load_json_file(file_name):
    file_path = os.path.join(BASE_FOLDER, file_name)
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def load_races():
    return load_json_file("races.json")

def load_classes():
    return load_json_file("classes.json")

def load_backgrounds():
    return load_json_file("backgrounds.json")

def load_characters():
    return load_json_file("characters/character_list.json")