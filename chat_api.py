# file: chat_api.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os
import json
from datetime import datetime

# === App Setup
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Paths & Constants
LOG_DIR = "chat_logs"
MEMORY_FILE = "rules/npc_memory.json"
EMOTION_FILE = "rules/emotions.json"
INTERACTION_FILE = "rules/last_interactions.json"
WORLD_TIME_FILE = "rules/world_time.json"
MENTAL_STATE_FILE = "rules/player_mental_state.json"
CHARACTER_DIR = "rules/characters"
os.makedirs(LOG_DIR, exist_ok=True)

# === Classes
class ChatRequest(BaseModel):
    npc: str
    player_input: str

# === File I/O
def read_json(path):
    return json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# === Game Time
def get_current_game_hours():
    world_time = read_json(WORLD_TIME_FILE)
    return world_time.get("day", 0) * 24 + world_time.get("hour", 0)

def hours_since_last(npc_name):
    interactions = read_json(INTERACTION_FILE)
    last = interactions.get(npc_name.lower().replace(" ", "_"), 0)
    return get_current_game_hours() - last

def update_last_interaction(npc_name):
    interactions = read_json(INTERACTION_FILE)
    interactions[npc_name.lower().replace(" ", "_")] = get_current_game_hours()
    write_json(INTERACTION_FILE, interactions)

# === Emotion System
def load_emotions():
    return read_json(EMOTION_FILE)

def save_emotions(data):
    write_json(EMOTION_FILE, data)

def update_emotions(npc, text):
    emotions = load_emotions()
    npc_key = npc.lower().replace(" ", "_")
    emotions.setdefault(npc_key, {"trust": 150, "hostility": 150, "romance": 0, "fear": 100})
    score = emotions[npc_key]
    text = text.lower()

    if "thank" in text or "respect" in text:
        score["trust"] = min(300, score["trust"] + 10)
    if "love" in text or "miss" in text or "care" in text:
        score["romance"] = min(300, score["romance"] + 15)
    if "hate" in text or "traitor" in text or "kill" in text:
        score["hostility"] = min(300, score["hostility"] + 20)
    if "afraid" in text or "run" in text or "monster" in text:
        score["fear"] = min(300, score["fear"] + 10)

    save_emotions(emotions)
    return score

# === Memory
def load_memory(npc):
    return read_json(MEMORY_FILE).get(npc.lower().replace(" ", "_"), [])

def write_to_memory(npc, line):
    memory_data = read_json(MEMORY_FILE)
    key = npc.lower().replace(" ", "_")
    memory_data.setdefault(key, [])
    if line not in memory_data[key]:
        memory_data[key].append(line)
    write_json(MEMORY_FILE, memory_data)

# === Logs
def write_to_log(npc_name, player_input, npc_reply):
    filename = os.path.join(LOG_DIR, f"{npc_name}_chatlog.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*40}\n[{timestamp}]\n")
        f.write(f"Player: {player_input.strip()}\n")
        f.write(f"{npc_name}: {npc_reply.strip()}\n")

# === Mental State
def get_mental_state(player="wojtek"):
    return read_json(MENTAL_STATE_FILE).get(player, {})

def update_stress(mental_state, increase=0, decay=0):
    current = mental_state.get("stress", 0)
    current = max(0, min(300, current + increase - decay))
    mental_state["stress"] = current
    return current

def check_condition_effects(mental_state):
    effects = []
    conditions = mental_state.get("conditions", {})
    stress = mental_state.get("stress", 0)

    if conditions.get("paranoia", 0) > 70:
        effects.append("Why are you asking that again? Are you hiding something?")
    if conditions.get("emotional_numbness", 0) > 60:
        effects.append("Does it even matter anymore?")
    if conditions.get("nightmares", 0) > 30 and stress > 80:
        effects.append("Was this real... or another dream?")
    if stress >= 100:
        effects.append("[SYSTEM]: Your mind splinters. You freeze. (Mental Collapse)")
    elif stress >= 90:
        effects.append("[SYSTEM]: You feel a rising panic. You can't hold it back.")
    elif stress >= 70:
        effects.append("[SYSTEM]: Your hands tremble. Everything feels too loud.")

    return effects

# === API Endpoint
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    npc = request.npc.lower()
    player_input = request.player_input

    try:
        npc_data = read_json(os.path.join(CHARACTER_DIR, f"{npc}.json"))
    except:
        return {"reply": f"[ERROR] NPC '{npc}' not found."}

    log_path = os.path.join(LOG_DIR, f"{npc}_chatlog.txt")
    memory_lines = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            memory_lines = [
                line.strip() for line in f.readlines()[-20:]
                if "Player:" in line or npc_data['name'] in line
            ]

    long_term = load_memory(npc)
    emotion_scores = update_emotions(npc, player_input)
    emotion_summary = ", ".join([f"{k}: {v}" for k, v in emotion_scores.items()])
    long_summary = "\n".join(f"- {m}" for m in long_term) or "None yet."

    neglect_hours = hours_since_last(npc)
    neglect_line = "It’s been far too long since we last spoke." if neglect_hours > 96 else ""
    update_last_interaction(npc)

    # 🧠 Stress System
    mental_state = get_mental_state()
    stress = update_stress(mental_state, increase=5 if "hate" in player_input.lower() else 1)
    extra_text = "\n".join(check_condition_effects(mental_state))

    prompt = f"""
You are {npc_data['name']}, an NPC in a grimdark RPG.
Respond truthfully, with memory, emotion, and psychological context.

ROLE: {npc_data.get("role", "Unknown")}
RELATIONSHIP: {npc_data.get("relationship_with_player", '?')}
AGE: {npc_data.get("age", '?')} | GENDER: {npc_data.get("gender", '?')}

EMOTIONS: {emotion_summary}
STRESS: {stress}
{neglect_line}

RECENT DIALOGUE:
{chr(10).join(memory_lines)}

LONG-TERM MEMORY:
{long_summary}

MENTAL CONDITIONS:
{extra_text}
""".strip()

    try:
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": player_input}
            ],
            stream=True
        )

        full_reply = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                full_reply += chunk.choices[0].delta.content

        write_to_log(npc_data["name"], player_input, full_reply)

        if any(word in player_input.lower() for word in ["trust", "kill", "protect", "love", "threaten", "betray"]):
            write_to_memory(npc, f"You said: '{player_input.strip()}'")

        return {"reply": full_reply}

    except Exception as e:
        return {"reply": f"[OpenAI ERROR] {str(e)}"}


# === Dev Only
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

# === Recovery Endpoint
from scripts.recovery import apply_recovery

@app.get("/recover/{player_name}")
def recover_player(player_name: str, hours: int = 24):
    result = apply_recovery(player_name, hours)
    return result
