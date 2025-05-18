import json
import os

# Basic character creation options
genders = ["Male", "Female"]
races = ["Human", "Elf", "Dwarf", "Orc"]
backgrounds = ["Noble", "Hunter", "Scholar", "Outlaw"]
classes = ["Warrior", "Mage", "Rogue", "Cleric"]

# Folder where characters will be saved
CHARACTER_FOLDER = "characters"

def ensure_character_folder():
    if not os.path.exists(CHARACTER_FOLDER):
        os.makedirs(CHARACTER_FOLDER)

def create_character():
    character = {}

    print("\n--- Create New Character ---")

    print("\nSelect Gender:")
    for i, gender in enumerate(genders, 1):
        print(f"{i}. {gender}")
    choice = int(input("Enter number: ")) - 1
    character["gender"] = genders[choice]

    print("\nSelect Race:")
    for i, race in enumerate(races, 1):
        print(f"{i}. {race}")
    choice = int(input("Enter number: ")) - 1
    character["race"] = races[choice]

    print("\nSelect Background:")
    for i, background in enumerate(backgrounds, 1):
        print(f"{i}. {background}")
    choice = int(input("Enter number: ")) - 1
    character["background"] = backgrounds[choice]

    print("\nSelect Class:")
    for i, cls in enumerate(classes, 1):
        print(f"{i}. {cls}")
    choice = int(input("Enter number: ")) - 1
    character["class"] = classes[choice]

    character_name = input("\nEnter character name: ")
    filename = os.path.join(CHARACTER_FOLDER, f"{character_name}.json")

    with open(filename, "w") as f:
        json.dump(character, f, indent=4)

    print(f"\n✅ Character '{character_name}' created successfully!\n")

def load_character():
    print("\n--- Load Existing Character ---")
    files = os.listdir(CHARACTER_FOLDER)
    json_files = [f for f in files if f.endswith(".json")]

    if not json_files:
        print("❌ No characters found.\n")
        return

    print("\nAvailable Characters:")
    for i, file in enumerate(json_files, 1):
        print(f"{i}. {file}")

    choice = int(input("Enter number: ")) - 1
    filename = json_files[choice]
    filepath = os.path.join(CHARACTER_FOLDER, filename)

    with open(filepath, "r") as f:
        character = json.load(f)

    print("\n--- Character Details ---")
    for key, value in character.items():
        print(f"{key.capitalize()}: {value}")
    print()

def main_menu():
    ensure_character_folder()

    while True:
        print("=== Main Menu ===")
        print("1. Create New Character")
        print("2. Load Existing Character")
        print("3. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            create_character()
        elif choice == "2":
            load_character()
        elif choice == "3":
            print("\nGoodbye, brother.")
            break
        else:
            print("❌ Invalid choice. Please try again.\n")

if __name__ == "__main__":
    main_menu()

from scripts.time_utils import skip_time

if __name__ == "__main__":
    skip_time(6)
    skip_time(18)
    skip_time(48)

