# file: scripts/addiction.py
"""Alcoholic / Drug Addict withdrawal clock (rules/creation/addiction.json). PLACEHOLDER numbers."""
import json
import os

import knight

ROOT = os.path.join(os.path.dirname(__file__), "..")


def data():
    with open(os.path.join(ROOT, "rules/creation/addiction.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def withdrawal_stage(intensity, hours_without):
    """Withdrawal stage dict reached after hours without the substance, or None."""
    d = data()
    per = d["hours_per_stage"][str(intensity)]
    stages = [s for s in d["stages"] if s.get("min_intensity", 0) <= intensity]
    n = hours_without // per
    return stages[min(n, len(stages)) - 1] if n >= 1 else None


def daily_stress(intensity):
    return data()["daily_stress_by_intensity"][intensity]


def indulge(character, substance="drink"):
    """Feed the habit: stress relief for everyone; a knight also loses Virtue (Purity vow).
    character: object with stress_level and optional virtue / class_name."""
    ind = data()["indulgence"]
    character.stress_level = max(0, character.stress_level + ind["stress_relief"])
    lost = 0
    if getattr(character, "class_name", None) == "Crusader_Knight":
        lost = knight.virtue_loss("vice_drugs" if substance == "drugs" else ind["knight_virtue_loss_event"])
        character.virtue = max(0, getattr(character, "virtue", 0) - lost)
    return lost
