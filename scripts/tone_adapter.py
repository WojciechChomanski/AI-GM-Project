# tone_adapter.py

import json
from relationship_utils import get_relationship_state
from memory_summarizer import summarize_recent_emotions

def build_dynamic_prompt(npc_path, memory_path, relationship_score):
    with open(npc_path, 'r', encoding='utf-8') as f:
        npc = json.load(f)

    # Base tone elements
    name = npc.get("name")
    role = npc.get("role")
    style = npc.get("personality", {}).get("speech_style", {})
    tone = style.get("tone", "neutral")
    formality = style.get("formality", "neutral")
    quirks = style.get("quirks", [])

    # Relationship state
    relationship_state = get_relationship_state(relationship_score)

    # Recent emotional modifiers
    emotion_tags = summarize_recent_emotions(memory_path)
    emotion_summary = ", ".join(emotion_tags) if emotion_tags else "no strong emotional bias"

    # Build final system prompt string
    system_prompt = f"""
You are {name}, a {role} in a grimdark fantasy world.
Your tone is usually {tone} and your speech is {formality}.
You are currently {relationship_state} toward the player.
Recent emotional influences: {emotion_summary}.

When speaking, maintain these quirks:
- {'\n- '.join(quirks) if quirks else 'None'}

Respond in a way that reflects your personality, current relationship, and emotional state.
"""
    return system_prompt.strip()