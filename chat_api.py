# chat_api.py - Wrath & Glory NPC Chat API (minimal & clean)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os
import json
from datetime import datetime

load_dotenv()
XAI_API_KEY = os.getenv("XAI_API_KEY")
client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CHARACTER_DIR = "npcs/wrath-and-glory"
MEMORY_DIR = "memory"
LOG_DIR = "chat_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Mapping von npc_id zu kurzem Dateinamen
NPC_SHORT_NAME = {
    "npc_sister_superior_veridya_v1_5": "veridya",
    "npc_sister_hospitaller_lirien_v1_3": "lirien",
    "npc_sergeant_torvax_ironjaw_v1_3": "torvax",
    "npc_interrogator_veyra_kane_v1_3": "kane",
    "npc_the_silent_one_k17_v1_3": "k17",
    "npc_cult_magus_father_v1_2": "father"
}

class ChatRequest(BaseModel):
    npc: str
    player_input: str

def load_npc(npc_id: str):
    path = os.path.join(CHARACTER_DIR, f"{npc_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_short_name(npc_id: str):
    return NPC_SHORT_NAME.get(npc_id, npc_id.split("_")[-2] if "_" in npc_id else npc_id)

def load_memory(npc_id: str):
    short = get_short_name(npc_id)
    path = os.path.join(MEMORY_DIR, f"{short}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"impressions": [], "current_attitude": "neutral", "key_events": []}

def save_memory(npc_id: str, memory_data):
    short = get_short_name(npc_id)
    path = os.path.join(MEMORY_DIR, f"{short}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, indent=2, ensure_ascii=False)

def write_log(npc_name, player_input, reply):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(LOG_DIR, f"{npc_name.replace(' ', '_')}.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}]\nPLAYER: {player_input}\nNPC: {reply}\n{'-'*60}\n")

@app.post("/chat")
async def chat(request: ChatRequest):
    npc_data = load_npc(request.npc)
    if not npc_data:
        return {"reply": f"[ERROR] NPC '{request.npc}' not found in npcs/wrath-and-glory/"}

    memory = load_memory(request.npc)

    core = npc_data.get("guard_rails", {}).get("core_instruction", "")
    tone = npc_data.get("guard_rails", {}).get("tone_rule", "")
    lore = npc_data.get("guard_rails", {}).get("lore_rule", "")
    hierarchy = npc_data.get("hierarchy_position", "")
    relationships = npc_data.get("relationships", {})

    rel_text = "\n".join([f"- {k}: {v}" for k, v in relationships.items()])

    system_prompt = f"""{core}

{tone}

{lore}

=== HIERARCHY & POSITION ===
{hierarchy}

=== RELATIONSHIPS TO OTHER NPCs ===
{rel_text}

=== CURRENT MEMORY / IMPRESSIONS ===
{json.dumps(memory, indent=2, ensure_ascii=False)}

=== IMPORTANT RULES ===
- NEVER output meta information like [Day XX | Hour XX | Piety XX]
- NEVER break character
- ALWAYS reply in the exact same language the player used
- If the player mentions something important, remember it in your next responses
"""

    try:
        stream = client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.player_input}
            ],
            stream=True
        )

        full_reply = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                full_reply += chunk.choices[0].delta.content

        # Memory aktualisieren
        memory["impressions"].append(request.player_input[:200])
        if len(memory["impressions"]) > 8:
            memory["impressions"] = memory["impressions"][-8:]
        memory["last_interaction"] = datetime.now().isoformat()
        save_memory(request.npc, memory)

        write_log(npc_data.get("name", request.npc), request.player_input, full_reply)
        return {"reply": full_reply}

    except Exception as e:
        return {"reply": f"[ERROR] {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
