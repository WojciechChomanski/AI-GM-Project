extends Control

@onready var name_input = $CenterContainer/VBoxContainer/NameRow/NameInput
@onready var gender_select = $CenterContainer/VBoxContainer/GenderRow/GenderSelect
@onready var race_select = $CenterContainer/VBoxContainer/RaceRow/RaceSelect
@onready var background_select = $CenterContainer/VBoxContainer/BackgroundRow/BackgroundSelect
@onready var class_select = $CenterContainer/VBoxContainer/ClassRow/ClassSelect
@onready var confirm_button = $CenterContainer/VBoxContainer/ConfirmButton
@onready var load_button = $CenterContainer/VBoxContainer/LoadButton
@onready var load_dialog = $LoadDialog

func _ready():
	confirm_button.pressed.connect(_on_confirm_pressed)
	load_button.pressed.connect(_on_load_button_pressed)
	load_dialog.file_selected.connect(_on_load_dialog_file_selected)

func _on_confirm_pressed():
	var name_text = name_input.text.strip_edges()
	if name_text == "":
		show_alert("Please enter a character name.")
		return
	if gender_select.selected == -1:
		show_alert("Please select a Gender.")
		return
	if race_select.selected == -1:
		show_alert("Please select a Race.")
		return
	if background_select.selected == -1:
		show_alert("Please select a Background.")
		return
	if class_select.selected == -1:
		show_alert("Please select a Class.")
		return

	var save_path = "res://characters/characters/" + name_text.to_lower() + ".json"
	if FileAccess.file_exists(save_path):
		show_alert("A character with this name already exists. Please choose a different name.")
		return

	var background = background_select.get_item_text(background_select.selected)
	if background == "Prostitute":
		background = "Street_Whore"

	var character_data = {
		"name": name_text,
		"gender": gender_select.get_item_text(gender_select.selected),
		"race": race_select.get_item_text(race_select.selected),
		"background": background,
		"class": class_select.get_item_text(class_select.selected),
		"total_hp": 100,
		"max_stamina": 100,
		"armor_weight": 10,
		"inventory_weight": 5,
		"shield_equipped": false,
		"weapon_equipped": true,
		"weapon": "dagger",
		"armor": ["Light_Light"],
		"bleeding": 0.0
	}

	GlobalData.character_data = character_data

	var file = FileAccess.open(save_path, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(character_data, "\t"))
		file.close()
		print("✅ Character saved successfully to ", save_path)
		get_tree().change_scene_to_file("res://characters/scenes/world_map.tscn")
	else:
		print("❌ Failed to save character!")
		show_alert("Failed to save character.")

func _on_load_button_pressed():
	load_dialog.popup_centered()

func _on_load_dialog_file_selected(path: String) -> void:
	var file = FileAccess.open(path, FileAccess.READ)
	if file:
		var data = JSON.parse_string(file.get_as_text())
		file.close()
		if data:
			if data.get("background") == "Street_Whore":
				data["background"] = "Prostitute"
			if not data.has("bleeding"):
				data["bleeding"] = 0.0
			GlobalData.character_data = data
			name_input.text = data.get("name", "")
			var gender_idx = gender_select.get_item_index(gender_select.find_text(data.get("gender", "")))
			var race_idx = race_select.get_item_index(race_select.find_text(data.get("race", "")))
			var bg_idx = background_select.get_item_index(background_select.find_text(data.get("background", "")))
			var class_idx = class_select.get_item_index(class_select.find_text(data.get("class", "")))
			if gender_idx != -1:
				gender_select.select(gender_idx)
			if race_idx != -1:
				race_select.select(race_idx)
			if bg_idx != -1:
				background_select.select(bg_idx)
			if class_idx != -1:
				class_select.select(class_idx)
			get_tree().change_scene_to_file("res://characters/scenes/world_map.tscn")

func show_alert(message: String) -> void:
	var dialog = AcceptDialog.new()
	dialog.dialog_text = message
	add_child(dialog)
	dialog.popup_centered()
