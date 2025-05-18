import os
import json
from datetime import datetime

def generate_tone(memory_log):
    trust = memory_log.get("trust_level", 0)
    hostility = memory_log.get("hostility_level", 0)

    if hostility > 5:
        return "cold, suspicious, and guarded"
    elif trust > 5:
        return "more respectful, open, but still cautious"
    elif trust < -3:
        return "mocking, sarcastic, possibly cruel"
    else:
        return "neutral, slightly distant, observing"

def build_interaction_context(npc_data, player_data, memory_log):
    interactions = memory_log.get("interactions", [])
    recent = interactions[-2:] if len(interactions) >= 2 else interactions

    history_snippets = "\n".join(
        [f'> “{entry["npc_response"]}”' for entry in recent]
    ) if recent else "No prior conversations."

    return f"""--- Memory with Player ---

This NPC has spoken to this player {len(interactions)} time(s). Based on those:
- Trust: {memory_log.get("trust_level", 0)}
- Respect: {memory_log.get("respect_level", 0)}
- Hostility: {memory_log.get("hostility_level", 0)}

Recent quotes:  
{history_snippets}

Modify your tone accordingly: {generate_tone(memory_log)}.
""".strip()

def add_interaction(npc_id, player_id, player_message, npc_response):
    os.makedirs("memory_logs", exist_ok=True)
    filename = f"memory_log_{npc_id}_{player_id}.json"
    path = os.path.join("memory_logs", filename)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            memory_log = json.load(f)
    else:
        memory_log = {
            "trust_level": 0,
            "respect_level": 0,
            "hostility_level": 0,
            "interactions": [],
            "npc_id": npc_id,
            "player_id": player_id
        }

    memory_log["interactions"].append({
        "timestamp": datetime.now().isoformat(),
        "player_input": player_message,
        "npc_response": npc_response
    })

    # Adjust emotional stats
    lowered = player_message.lower()
    if any(word in lowered for word in ["thank", "respect", "admire", "grateful"]):
        memory_log["trust_level"] += 1
        memory_log["respect_level"] += 1
    elif any(word in lowered for word in ["idiot", "fool", "kill", "hate", "scum"]):
        memory_log["hostility_level"] += 2
        memory_log["trust_level"] -= 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory_log, f, indent=2, ensure_ascii=False)

    return memory_log
