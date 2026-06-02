# chat_api_wng.py - Wrath & Glory One-Shot (FINAL VERSION)
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

# === EXAKTE Zuordnung: Alle IDs die Foundry schicken → echte Dateinamen ===
NPC_FILE_MAP = {
    # Veridya
    "npc_sister_superior_veridya_v1_5": "Sister_superior_Veridya.json",
    "sister_superior_veridya": "Sister_superior_Veridya.json",
    "sister_superior_veridya_v1_5": "Sister_superior_Veridya.json",

    # Lirien (das war das Problem)
    "npc_sister_hospitaller_lirien_v1_3": "Sister_hospitaller_Lirien.json",
    "npc_sister_hospitaller_lirien": "Sister_hospitaller_Lirien.json",
    "sister_hospitaller_lirien": "Sister_hospitaller_Lirien.json",
    "sister_hospitaller_lirien_v1_3": "Sister_hospitaller_Lirien.json",

    # Torvax
    "npc_sergeant_torvax_ironjaw_v1_3": "Sergeant_Torvax_Ironjaw.json",
    "npc_sergeant_torvax_ironjaw_v1_0": "Sergeant_Torvax_Ironjaw.json",
    "sergeant_torvax_ironjaw": "Sergeant_Torvax_Ironjaw.json",
    "sergeant_torvax_ironjaw_v1_3": "Sergeant_Torvax_Ironjaw.json",

    # Kane
    "npc_interrogator_veyra_kane_v1_3": "Interrogator_Veyra_Kane.json",
    "npc_interrogator_veyra_kane_v1_0": "Interrogator_Veyra_Kane.json",
    "interrogator_veyra_kane": "Interrogator_Veyra_Kane.json",
    "interrogator_veyra_kane_v1_3": "Interrogator_Veyra_Kane.json",

    # K-17
    "npc_the_silent_one_k17_v1_3": "The_Silent_One_K-17.json",
    "npc_the_silent_one_k17_v1_0": "The_Silent_One_K-17.json",
    "the_silent_one_k17": "The_Silent_One_K-17.json",
    "the_silent_one_k17_v1_3": "The_Silent_One_K-17.json",

    # Father
    "npc_cult_magus_father_v1_2": "Cult_Magus_Father.json",
    "npc_cult_magus_father_v1_0": "Cult_Magus_Father.json",
    "cult_magus_father": "Cult_Magus_Father.json",
    "cult_magus_father_v1_2": "Cult_Magus_Father.json",
}

class ChatRequest(BaseModel):
    npc: str
    player_input: str

def load_npc(npc_id: str):
    print(f"🔍 Foundry sendet ID: {npc_id}")
    
    filename = NPC_FILE_MAP.get(npc_id)
    if filename:
        path = os.path.join(CHARACTER_DIR, filename)
        if os.path.exists(path):
            print(f"✅ Geladen: {filename}")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    
    print(f"❌ Keine passende Datei für: {npc_id}")
    return None

def load_memory(npc_id: str):
    short = NPC_FILE_MAP.get(npc_id, npc_id).replace(".json", "").lower()
    path = os.path.join(MEMORY_DIR, f"{short}.json")
    if not os.path.exists(path):
        return {"impressions": [], "current_attitude": "neutral", "key_events": [], "last_interaction": None}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_memory(npc_id: str, memory: dict):
    short = NPC_FILE_MAP.get(npc_id, npc_id).replace(".json", "").lower()
    path = os.path.join(MEMORY_DIR, f"{short}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

@app.post("/chat")
async def chat(request: ChatRequest):
    npc_data = load_npc(request.npc)
    if not npc_data:
        return {"reply": "Fehler: NPC nicht gefunden."}

    memory = load_memory(request.npc)

    system_prompt = f"""Du bist {npc_data.get('name', request.npc)}. 
Du existierst nur im grimdark Universum von Warhammer 40.000.
NEVER break character. NEVER output meta info wie [Day] oder Piety.
Du antwortest immer auf Deutsch, wenn der Spieler auf Deutsch fragt.

Aktuelles Memory:
{json.dumps(memory, indent=2, ensure_ascii=False)}

=== WICHTIG ===
- Bleib 100% im Charakter
- Keine OOC-Kommentare
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

        memory["impressions"].append(request.player_input[:200])
        if len(memory["impressions"]) > 8:
            memory["impressions"] = memory["impressions"][-8:]
        memory["last_interaction"] = datetime.now().isoformat()
        save_memory(request.npc, memory)

        return {"reply": full_reply}

    except Exception as e:
        return {"reply": f"[ERROR] {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)