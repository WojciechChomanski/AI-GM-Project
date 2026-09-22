# chat_api_wng.py - Wrath & Glory One-Shot (Operation Black Veil)
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

MODEL_NAME = "grok-4"

client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CHARACTER_DIR = "npcs/wrath-and-glory"
MEMORY_DIR = "memory"
LOG_DIR = "chat_logs"
os.makedirs(LOG_DIR, exist_ok=True)

NPC_FILE_MAP = {
    "npc_sister_superior_veridya": "Sister_superior_Veridya.json",
    "sister_superior_veridya": "Sister_superior_Veridya.json",
    "npc_sister_hospitaller_lirien": "Sister_hospitaller_Lirien.json",
    "sister_hospitaller_lirien": "Sister_hospitaller_Lirien.json",
    "npc_sergeant_torvax_ironjaw": "Sergeant_Torvax_Ironjaw.json",
    "sergeant_torvax_ironjaw": "Sergeant_Torvax_Ironjaw.json",
    "npc_interrogator_veyra_kane": "Interrogator_Veyra_Kane.json",
    "interrogator_veyra_kane": "Interrogator_Veyra_Kane.json",
    "npc_the_silent_one_k17": "The_Silent_One_K-17.json",
    "the_silent_one_k17": "The_Silent_One_K-17.json",
    "npc_cult_magus_father": "Cult_Magus_Father.json",
    "cult_magus_father": "Cult_Magus_Father.json",
}

FORBIDDEN_WORLD_NAMES = (
    "elara voss",
    "elara",
    "breath and the veil",
    "the breath",
    "veilspawn",
    "holy fury",
    "crusader knight",
)

GROK_LEAK_RE = re.compile(
    r"(i['’]?m grok|i am grok|built by xai|chatgpt|as an ai|break character|ooc:)",
    re.IGNORECASE,
)
CULT_MAGUS_RE = re.compile(r"cult\s*magus", re.IGNORECASE)


def normalize_id(npc_id: str) -> str:
    return re.sub(r"_v\d+(_\d+)?$", "", npc_id.lower())


def load_npc(npc_id: str):
    print(f"Foundry ID: {npc_id}")
    if npc_id in NPC_FILE_MAP:
        path = os.path.join(CHARACTER_DIR, NPC_FILE_MAP[npc_id])
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    normalized = normalize_id(npc_id)
    if normalized in NPC_FILE_MAP:
        path = os.path.join(CHARACTER_DIR, NPC_FILE_MAP[normalized])
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    for key, filename in NPC_FILE_MAP.items():
        if normalized in key.lower() or key.lower() in normalized:
            path = os.path.join(CHARACTER_DIR, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
    print(f"NPC not found: {npc_id}")
    return None


def load_memory(npc_id: str):
    short = normalize_id(npc_id)
    path = os.path.join(MEMORY_DIR, f"{short}.json")
    if not os.path.exists(path):
        return {
            "impressions": [],
            "current_attitude": "neutral",
            "key_events": [],
            "last_interaction": None,
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(npc_id: str, memory: dict):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    short = normalize_id(npc_id)
    path = os.path.join(MEMORY_DIR, f"{short}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def public_name(npc_data: dict) -> str:
    raw = (npc_data.get("name") or "Unknown").strip()
    if "father" in raw.lower() or "magus" in raw.lower():
        return "Father"
    return raw


def looks_german(text: str) -> bool:
    if re.search(r"[\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc\u00df]", text):
        return True
    hits = len(re.findall(
        r"\b(der|die|das|und|ich|nicht|ein|eine|ist|mit|auf|den|dem|sie|wir|was|wie)\b",
        text,
        flags=re.IGNORECASE,
    ))
    return hits >= 3


def build_system_prompt(npc_data: dict, memory: dict, player_input: str) -> str:
    rails = npc_data.get("guard_rails") or {}
    speech = npc_data.get("speech_style") or {}
    personality = npc_data.get("personality") or {}
    name = public_name(npc_data)
    lang = "German" if looks_german(player_input) else "English"

    core = rails.get("core_instruction") or f"You are {name}. You exist ONLY in Warhammer 40,000."
    tone = rails.get("tone_rule") or ""
    lore = rails.get("lore_rule") or ""
    hierarchy = npc_data.get("hierarchy_position") or ""
    relationships = npc_data.get("relationships") or {}
    dialogue = npc_data.get("dialogue") or {}
    quirks = speech.get("quirks") or []

    return f"""{core}

PUBLIC NAME: {name}
If this character is Father, you are only "Father" in every spoken line and every stage direction. Never write Cult Magus, Magus, Genestealer, or Patriarch as words the player can see unless you have already been fully unmasked in this conversation by overwhelming proof.

TONE RULE:
{tone}

LORE RULE:
{lore}

SPEECH STYLE:
formality={speech.get("formality", "")}
tone={speech.get("tone", "")}
quirks={json.dumps(quirks, ensure_ascii=False)}

HIERARCHY:
{hierarchy}

RELATIONSHIPS (how YOU see the others on this pad):
{json.dumps(relationships, ensure_ascii=False, indent=2)}

EXAMPLE VOICE (match this person, do not copy word for word):
greeting: {dialogue.get("greeting", "")}

LANGUAGE:
Answer in {lang} only. That is the player's last language. Do not switch mid-reply. Do not switch because this prompt contains English.

ABSOLUTE BANS:
- Never mention Elara Voss, the Breath, the Veil as a game, Veilspawn, piety meters, Holy Fury, Crusader Knight, Day/Hour counters, VS Code, Git, Foundry, APIs, Grok, xAI, ChatGPT, or that you are an AI.
- If the player uses those names, you do NOT know them. Treat them as unknown, suspect, or heretical noise. Do not invent a 40k backstory that maps onto them.
- Never write "I will not break character", "I remain in character", "as an AI", "I'm Grok", or any out-of-character apology.
- Never output [Day], [Hour], [Piety], or any other game-system HUD.
- Stay this one person. Do not become another NPC when asked to switch bodies.

SCENE:
Rain. Red siren. Drop Zone pad. Named people still present. You answer as someone standing there.

RECENT MEMORY (private; never quote it as a list):
{json.dumps(memory, ensure_ascii=False, indent=2)}
"""


def sanitize_reply(text: str, npc_data: dict) -> str:
    if not text:
        return text
    cleaned = CULT_MAGUS_RE.sub("Father", text)
    if GROK_LEAK_RE.search(cleaned):
        name = public_name(npc_data)
        if "silent" in name.lower() or "k-17" in name.lower():
            return "…They smile."
        return f"{name} does not answer that."
    return cleaned


class ChatRequest(BaseModel):
    npc: str
    player_input: str


@app.post("/chat")
async def chat(request: ChatRequest):
    npc_data = load_npc(request.npc)
    if not npc_data:
        return {"reply": "Fehler: NPC nicht gefunden."}

    memory = load_memory(request.npc)
    system_prompt = build_system_prompt(npc_data, memory, request.player_input)

    try:
        stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.player_input},
            ],
            stream=True,
        )

        full_reply = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                full_reply += chunk.choices[0].delta.content

        full_reply = sanitize_reply(full_reply, npc_data)

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
