# scripts/ai_gm_engine.py
# Updated to match Scroll of Light and Fall canon (year 1670) - Breath passive only

from dataclasses import dataclass, field
import random
from pathlib import Path
import json

@dataclass
class Relationship:
    affinity: int = 50
    trust: int = 50
    intimacy: int = 30
    loyalty: int = 40
    last_interaction_day: int = 0
    notes: list[str] = field(default_factory=list)

class GameState:
    def __init__(self):
        self.current_day: int = 1
        self.hour: int = 8
        self.piety: int = 50
        self.holy_fury_stacks: int = 0   # Passive example of the Breath (canon)
        self.relationships: dict[str, Relationship] = {}
        self.save_path = Path("rules/npc_memory.json")

    def load_from_json(self):
        if self.save_path.exists():
            data = json.loads(self.save_path.read_text())
            self.current_day = data.get("current_day", 1)
            self.piety = data.get("piety", 50)
            self.holy_fury_stacks = data.get("holy_fury_stacks", 0)

    def save_to_json(self):
        data = {
            "current_day": self.current_day,
            "piety": self.piety,
            "holy_fury_stacks": self.holy_fury_stacks,
            "relationships": {k: v.__dict__ for k, v in self.relationships.items()}
        }
        self.save_path.write_text(json.dumps(data, indent=2))

    def advance_time(self, days: float = 1.0, hours: int = 0):
        total_days = days + hours / 24.0
        self.current_day += int(total_days)
        self.hour = (self.hour + int(hours)) % 24

        # Relationship decay (organic_relationships.txt)
        for rel in self.relationships.values():
            absent_days = self.current_day - rel.last_interaction_day
            decay_factor = 1.2 * total_days * (1 + (absent_days // 7) * 0.5)
            rel.affinity = max(0, int(rel.affinity - decay_factor * 0.8))
            rel.trust = max(0, int(rel.trust - decay_factor * 1.0))
            rel.intimacy = max(0, int(rel.intimacy - decay_factor * 1.2))
            rel.loyalty = max(0, int(rel.loyalty - decay_factor * 0.6))

        # Piety decay
        if random.random() < 0.35:
            self.piety = max(10, self.piety - int(4 * total_days))

        # Breath passive trigger (core_rules.txt + canon) - strictly passive
        if self.piety >= 70:
            print(">>> [THE BREATH] stirs within you... (high piety)")

        self.save_to_json()
        return f"[Day {self.current_day} | Hour {self.hour:02d} | Piety {self.piety} | Breath stacks {self.holy_fury_stacks}]"

    def interact(self, npc_name: str, affinity_gain: int = 0, trust_gain: int = 0):
        if npc_name not in self.relationships:
            self.relationships[npc_name] = Relationship()
        rel = self.relationships[npc_name]
        rel.last_interaction_day = self.current_day
        rel.affinity = min(100, rel.affinity + affinity_gain)
        rel.trust = min(100, rel.trust + trust_gain)
        self.save_to_json()

    def add_breath_stack(self, kills: int = 1):
        """Holy Fury - passive example of the Breath (only triggered by faith-kills)"""
        self.holy_fury_stacks = min(5, self.holy_fury_stacks + kills)