extends Node2D

@onready var stance_selector = $StanceSelector
@onready var action_selector = $ActionSelector
@onready var zone_selector = $ZoneSelector
@onready var confirm_button = $ConfirmButton
@onready var output_label = $OutputLabel
@onready var cooldown_label = $CooldownLabel
@onready var turn_counter = $TurnCounter

var cooldowns = {"Shield Bash": 0, "Battle Cry": 0}
var current_turn = 1

func _ready():
	var player_name = GlobalData.character_data.get("name", "ada").to_lower()
	if player_name not in ["ada", "brock", "rock", "wojtek"]:
		output_label.text = "Invalid character: " + player_name
		return

	confirm_button.pressed.connect(_on_confirm_pressed)
	_update_cooldowns()
	turn_counter.text = "Turn: " + str(current_turn)

func _update_cooldowns():
	for action in cooldowns:
		if cooldowns[action] > 0:
			cooldowns[action] -= 1
	cooldown_label.text = "Cooldowns: Shield Bash: %d, Battle Cry: %d" % [cooldowns["Shield Bash"], cooldowns["Battle Cry"]]

func _on_confirm_pressed():
	var stance = stance_selector.get_item_text(stance_selector.selected)
	var action = action_selector.get_item_text(action_selector.selected)
	var player_name = GlobalData.character_data.get("name", "ada").to_lower()
	var aimed_zone = zone_selector.get_item_text(zone_selector.selected) if action == "Aimed Strike" else null
	
	zone_selector.visible = action == "Aimed Strike"
	
	if action == "Shield Bash" and cooldowns["Shield Bash"] > 0:
		output_label.text = "Shield Bash is on cooldown!"
		return
	elif action == "Battle Cry" and cooldowns["Battle Cry"] > 0:
		output_label.text = "Battle Cry is on cooldown!"
		return
	
	var python_path = "python3" # Use "python3" for compatibility
	var script_path = "res://scripts/adventure_godot.py"
	var output = []
	var args = [script_path, player_name, stance, action]
	if aimed_zone:
		args.append(aimed_zone)
	
	var exit_code = OS.execute(python_path, args, output, true)
	
	if exit_code == 0 and output:
		output_label.text = output[0].replace("\n", "\n")
		current_turn += 1
		turn_counter.text = "Turn: " + str(current_turn)
		if action == "Shield Bash":
			cooldowns["Shield Bash"] = 4
		elif action == "Battle Cry":
			cooldowns["Battle Cry"] = 6
		_update_cooldowns()
	else:
		output_label.text = "Adventure failed. Ensure Python and chat API are running."

	var button = Button.new()
	button.text = "Return to Map"
	button.position = Vector2(25, 650)
	button.pressed.connect(_return_to_map)
	add_child(button)

func _return_to_map():
	get_tree().change_scene_to_file("res://scenes/world_map.tscn")