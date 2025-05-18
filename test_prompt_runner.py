import json
import os
import sys

# Fix paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
RULES_DIR = os.path.join(BASE_DIR, "rules")

sys.path.append(SCRIPTS_DIR)

# Import from scripts
from generate_npc_system_prompt import generate_npc_system_prompt
from npc_memory_handler import build_interaction_context

# Load Wojtek's character
with open(os.path.join(RULES_DIR, "characters", "wojtek.json"), "r", encoding="utf-8") as f:
    npc_data = json.load(f)

# Load or initialize memory log
memory_log_path = os.path.join(RULES_DIR, "memory_log.json")
if os.path.exists(memory_log_path):
    with open(memory_log_path, "r", encoding="utf-8") as f:
        memory_log = json.load(f)
else:
    memory_log = {
        "npc_id": "wojtek",
        "player_id": "player_001",
        "interactions": [],
        "trust_level": 0,
        "respect_level": 0,
        "hostility_level": 0
    }

# Build the prompt
context = build_interaction_context(npc_data, None, memory_log)
system_prompt = generate_npc_system_prompt(npc_data) + "\n\n" + context

# Simulated input
player_input = "What do you know about the ruins north of here?"

# Create response stack
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": player_input}
]

# Output to terminal
print("==== SYSTEM PROMPT ====")
print(system_prompt)
print("\n==== SAMPLE CONVERSATION ====")
print(f"User: {player_input}")
