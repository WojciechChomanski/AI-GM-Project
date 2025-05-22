# memory_summarizer.py

import json
import os
from collections import Counter
from datetime import datetime, timedelta

# Define keyword → emotion mappings
EMOTION_KEYWORDS = {
    "insult": "resentment",
    "gift": "gratitude",
    "lie": "distrust",
    "truth": "respect",
    "help": "trust",
    "ignore": "hurt",
    "abandon": "betrayal",
    "praise": "warmth",
    "attack": "anger",
    "joke": "amusement",
    "share": "bonding",
    "silence": "tension"
}


def summarize_recent_emotions(memory_path, recent_minutes=60):
    if not os.path.exists(memory_path):
        return []

    with open(memory_path, 'r', encoding='utf-8') as f:
        memories = json.load(f)

    cutoff = datetime.utcnow() - timedelta(minutes=recent_minutes)
    emotions = []

    for mem in memories[-20:]:  # Limit to last 20 entries
        timestamp = datetime.fromisoformat(mem.get("timestamp"))
        if timestamp < cutoff:
            continue

        event = mem.get("event", "").lower()
        for keyword, emotion in EMOTION_KEYWORDS.items():
            if keyword in event:
                emotions.append(emotion)

        if "emotion" in mem:
            emotions.append(mem["emotion"].lower())

    # Prioritize top 2 dominant emotions
    top_emotions = [e for e, _ in Counter(emotions).most_common(2)]
    return top_emotions
