# chat_api_wng.py - Wrath & Glory One-Shot (Clean & Robust Version)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os
import json
import re
from datetime import datetime

load_dotenv()
XAI_API_KEY = os.getenv("XAI_API_KEY")

# ============================================================
# MODEL CONFIGURATION
# ============================================================
# Empfohlene Modelle für NPC-Rollenspiel:
# "grok-4"        → Beste Qualität + beste Einhaltung der Guard Rails (empfohlen)
# "grok-4-turbo"  → Sehr gute Qualität + schneller
# "grok-3"        → Stabil, aber schwächer bei Nuancen
MODEL_NAME = "grok-4"
# ============================================================

client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CHARACTER_DIR = "npcs/wrath-and-glory"
MEMORY_DIR = "memory"
LOG_DIR = "chat_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ============================================================
# NPC FILE MAP - Nur die wichtigsten / stabilsten IDs
# ============================================================
NPC_FILE_MAP = {
    # Sister Superior Veridya
    "npc_sister_superior_veridya": "Sister_superior_Veridya.json",
    "sister_superior_veridya": "Sister_superior_Veridya.json",

    # Sister Hospitaller Lirien
    "npc_sister_hospitaller_lirien": "Sister_hospitaller_Lirien.json",
    "sister_hospitaller_lirien": "Sister_hospitaller_Lirien.json",

    # Sergeant Torvax Ironjaw
    "npc_sergeant_torvax_ironjaw": "Sergeant_Torvax_Ironjaw.json",
    "sergeant_torvax_ironjaw": "Sergeant_Torvax_Ironjaw.json",

    # Interrogator Veyra Kane
    "npc_interrogator_veyra_kane": "Interrogator_Veyra_Kane.json",
    "interrogator_veyra_kane": "Interrogator_Veyra_Kane.json",

    # The Silent One (K-17)
    "npc_the_silent_one_k17": "The_Silent_One_K-17.json",
    "the_silent_one_k17": "The_Silent_One_K-17.json",

    # Cult Magus Father
    "npc_cult_magus_father": "Cult_Magus_Father.json",
    "cult_magus_father": "Cult_Magus_Father.json",
}


def normalize_id(npc_id: str) -> str:
    """Entfernt Versionsnummern und macht die ID vergleichbar"""
    return re.sub(r'_v\d+(_\d+)?$', '', npc_id.lower())


def load_npc(npc_id: str):
    print(f"🔍 Foundry sendet ID: {npc_id}")

    # 1. Direkter Lookup in der Map
    if npc_id in NPC_FILE_MAP:
        filename = NPC_FILE_MAP[npc_id]
        path = os.path.join(CHARACTER_DIR, filename)
        if os.path.exists(path):
            print(f"✅ Geladen (direkt): {filename}")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    # 2. Normalisierte ID versuchen (ohne Versionsnummer)
    normalized = normalize_id(npc_id)
    if normalized in NPC_FILE_MAP:
        filename = NPC_FILE_MAP[normalized]
        path = os.path.join(CHARACTER_DIR, filename)
        if os.path.exists(path):
            print(f"✅ Geladen (normalisiert): {filename}")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    # 3. Fallback: Versuche Datei über partiellen Namen zu finden
    for key, filename in NPC_FILE_MAP.items():
        if normalized in key.lower() or key.lower() in normalized:
            path = os.path.join(CHARACTER_DIR, filename)
            if os.path.exists(path):
                print(f"✅ Geladen (Fallback): {filename}")
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

    print(f"❌ Keine passende Datei gefunden für: {npc_id}")
    return None


def load_memory(npc_id: str):
    short = normalize_id(npc_id)
    path = os.path.join(MEMORY_DIR, f"{short}.json")
    if not os.path.exists(path):
        return {"impressions": [], "current_attitude": "neutral", "key_events": [], "last_interaction": None}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(npc_id: str, memory: dict):
    short = normalize_id(npc_id)
    path = os.path.join(MEMORY_DIR, f"{short}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


class ChatRequest(BaseModel):
    npc: str
    player_input: str


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
            model=MODEL_NAME,
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