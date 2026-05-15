# file: dialogue_box.gd
extends Control

@onready var npc_selector = $VBoxContainer/NpcSelector
@onready var npc_name_label = $VBoxContainer/NpcNameLabel
@onready var dialogue_log = $VBoxContainer/DialogueLog
@onready var player_input = $VBoxContainer2/InputRow/PlayerInput
@onready var send_button = $VBoxContainer2/InputRow/SendButton
@onready var http = $HTTPRequest

var current_npc = "wojtek"
var streaming_reply = ""
var stream_index = 0
var is_streaming = false
var stream_timer := Timer.new()

func _ready():
	npc_selector.clear()
	npc_selector.add_item("Wojtek")
	npc_selector.add_item("Vyrda_the_Hollow")
	npc_selector.add_item("Sister_Rhaen")
	npc_selector.add_item("Ser_Caldran_Vael")
	npc_selector.add_item("Archon_Threll_The_Charismatic_Monster")
	npc_selector.select(0)

	npc_name_label.text = "Wojtek"
	current_npc = "wojtek"

	npc_selector.item_selected.connect(_on_npc_selected)
	send_button.pressed.connect(_on_send_pressed)
	http.request_completed.connect(_on_response)

	add_child(stream_timer)
	stream_timer.timeout.connect(_stream_next_letter)

func _on_npc_selected(index: int):
	var npc_name = npc_selector.get_item_text(index)  # Renamed to avoid shadowing
	npc_name_label.text = npc_name
	current_npc = npc_name.to_lower().replace(" ", "_")

func _on_send_pressed():
	if http.get_http_client_status() == HTTPClient.STATUS_REQUESTING:
		dialogue_log.append_text("[System]: Still waiting on last reply...\n")
		return

	var text = player_input.text.strip_edges()
	if text.is_empty():
		return

	dialogue_log.append_text("[Player]:\n" + text + "\n")
	player_input.clear()

	var data = {
		"npc": current_npc,
		"player_input": text
	}
	var headers = ["Content-Type: application/json"]
	var json_string = JSON.stringify(data)

	var err = http.request(
		"http://localhost:8000/chat",
		headers,
		HTTPClient.METHOD_POST,
		json_string
	)

	if err != OK:
		dialogue_log.append_text("[System]: Failed to send request.\n")

func _on_response(_result, response_code, _headers, body):
	if response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json and json.has("reply"):
			_start_streaming_reply(json["reply"])
		else:
			dialogue_log.append_text("[System]: Malformed response.\n")
	else:
		dialogue_log.append_text("[System]: Server error %d\n" % response_code)

func _start_streaming_reply(reply: String):
	streaming_reply = reply
	stream_index = 0
	is_streaming = true
	dialogue_log.append_text("[" + npc_name_label.text + "]:\n")
	stream_timer.wait_time = 0.03
	stream_timer.start()

func _stream_next_letter():
	if not is_streaming:
		return

	if stream_index < streaming_reply.length():
		var next_char = streaming_reply[stream_index]
		dialogue_log.append_text(next_char)
		stream_index += 1
	else:
		stream_timer.stop()
		is_streaming = false
