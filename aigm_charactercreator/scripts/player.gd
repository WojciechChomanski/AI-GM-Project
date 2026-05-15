extends CharacterBody2D

const SPEED = 150

func _ready():
	print("✅ Torvald loaded into the world.")

func _physics_process(_delta):
	var input_vector = Vector2(
		Input.get_action_strength("ui_right") - Input.get_action_strength("ui_left"),
		Input.get_action_strength("ui_down") - Input.get_action_strength("ui_up")
	).normalized()

	if input_vector != Vector2.ZERO:
		print("📦 Moving:", input_vector)

	velocity = input_vector * SPEED
	move_and_slide()

func _on_combat_trigger_entered(body):
	if body == self:
		print("⚔️ Entering combat...")
		get_tree().change_scene_to_file("res://scenes/combat_scene.tscn")
