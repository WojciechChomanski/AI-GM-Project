import os
import sys
import json
from openai import OpenAI

# === Setup Paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
RULES_DIR = os.path.join(BASE_DIR, "rules")
CHAR_DIR = os.path.join(RULES_DIR, "characters")
MEMORY_DIR = os.path.join(BASE_DIR, "memory_logs")

sys.path.append(SCRIPTS_DIR)

# === Import project functions ===
from generate_npc_system_prompt import generate_npc_system_prompt
from npc_memory_handler import build_interaction_context, add_interaction

# === OpenAI Client ===
client = OpenAI(api_key="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")  # <-- Set your real key

# === Define IDs ===
npc_id = "Wojtek"
player_id = "player1"

# === Load NPC profile ===
with open(os.path.join(CHAR_DIR, "wojtek.json"), "r", encoding="utf-8") as f:
    npc_data = json.load(f)

# === Load or create memory log ===
memory_log_path = os.path.join(MEMORY_DIR, f"memory_log_{npc_id}_{player_id}.json")
if os.path.exists(memory_log_path):
    with open(memory_log_path, "r", encoding="utf-8") as f:
        memory_log = json.load(f)
else:
    memory_log = {
        "trust_level": 0,
        "respect_level": 0,
        "hostility_level": 0,
        "interactions": []
    }

# === Get player input ===
player_input = input("You: ")

# === Build system prompt with memory context ===
context = build_interaction_context(npc_data, player_id, memory_log)
system_prompt = generate_npc_system_prompt(npc_data) + "\n\n" + context

# === Send to GPT-4 ===
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": player_input}
    ]
)

# === Extract and show response ===
npc_reply = response.choices[0].message.content.strip()
print(f"\nWojtek: {npc_reply}")

# === Save to memory log ===
add_interaction(npc_id, player_id, player_input, npc_reply)
