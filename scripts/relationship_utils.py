# relationship_utils.py

def get_relationship_state(score: int) -> str:
    if score <= 50:
        return "Hostile"
    elif score <= 100:
        return "Wary"
    elif score <= 150:
        return "Neutral"
    elif score <= 200:
        return "Friendly"
    else:
        return "Loyal"

def get_state_description(state: str) -> str:
    return {
        "Hostile": "This NPC actively dislikes or distrusts the player. Tone will be cold, sarcastic, or threatening.",
        "Wary": "This NPC is guarded and suspicious. Tone is brief, cautious, or formal.",
        "Neutral": "This NPC has no strong feelings. Tone is factual or indifferent.",
        "Friendly": "This NPC likes the player. Tone is warm, curious, and cooperative.",
        "Loyal": "This NPC is emotionally bonded to the player. Tone is protective, supportive, even intimate."
    }.get(state, "Unknown relationship state.")
