
extends Control

@onready var gender_select = $VBoxContainer/GenderSelect
@onready var race_select = $VBoxContainer/RaceSelect
@onready var background_select = $VBoxContainer/BackgroundSelect
@onready var class_select = $VBoxContainer/ClassSelect
@onready var name_input = $VBoxContainer/NameInput
@onready var confirm_button = $VBoxContainer/ConfirmButton

func _ready():
    confirm_button.pressed.connect(_on_confirm_pressed)
    _populate_options()

func _populate_options():
    gender_select.add_item("Male")
    gender_select.add_item("Female")
    
    race_select.add_item("Human")
    race_select.add_item("Elf")
    race_select.add_item("Dwarf")

    background_select.add_item("Noble")
    background_select.add_item("Outlaw")
    background_select.add_item("Prostitute")
    background_select.add_item("Hunter")

    class_select.add_item("Mercenary")
    class_select.add_item("Knight")
    class_select.add_item("Mage")

func _on_confirm_pressed():
    var character_data = {
        "name": name_input.text,
        "gender": gender_select.get_item_text(gender_select.selected),
        "race": race_select.get_item_text(race_select.selected),
        "background": background_select.get_item_text(background_select.selected),
        "class": class_select.get_item_text(class_select.selected),
        "total_hp": 100,
        "max_stamina": 100,
        "armor_weight": 10,
        "inventory_weight": 5,
        "shield_equipped": false,
        "weapon_equipped": true,
        "weapon": "dagger",
        "armor": ["Light_Light"]
    }
    GlobalData.character_data = character_data
    var file_path = "res://characters/%s.json" % name_input.text.to_lower()
    var file = FileAccess.open(file_path, FileAccess.WRITE)
    file.store_string(JSON.stringify(character_data))
    file.close()
    get_tree().change_scene_to_file("res://scenes/world_map.tscn")
