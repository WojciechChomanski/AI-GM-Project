# file: scripts/knight.py
"""Crusader Knight vows, hidden Breath and Virtue events (rules/orders/crusader_vows.json, rules/virtue_rules.json).
Breath is GM-only: no visible light; the knight only notices that Veil-things fear him. PLACEHOLDER numbers."""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8-sig") as f:
        return json.load(f)


def vows():
    return _load("rules/orders/crusader_vows.json")


def breath_state(virtue, piety, corruption=0):
    """'full' | 'dim' | 'none'. Corruption >= 25 counts as dim at best."""
    b = vows()["breath"]
    f = b["full"]
    if virtue >= f["virtue_min"] and piety >= f["piety_min"] and corruption <= f["corruption_max"]:
        return "full"
    if virtue >= b["dim"]["virtue_min"]:
        return "dim"
    return "none"


def breath_effects(virtue, piety, corruption=0, target_tags=()):
    """Effects of his wounds on this target. Only at 'full' Breath and only vs Veil-born/corrupted.
    Never changes his normal weapon damage (steel rule)."""
    b = vows()["breath"]
    st = breath_state(virtue, piety, corruption)
    eff = dict(b[st]["effects"]) if st != "full" else {"holy_fury_max_stacks": b["full"]["effects"]["holy_fury_max_stacks"]}
    if st == "full" and set(target_tags) & set(b["full"]["vs"]):
        eff = dict(b["full"]["effects"])
    eff["state"] = st
    return eff


def virtue_loss(event):
    """Virtue lost for an event in rules/virtue_rules.json (0 if unknown)."""
    return _load("rules/virtue_rules.json")["virtue"]["loss_events"].get(event, 0)


def discipline(step):
    return vows()["discipline_ladder"][max(1, min(4, step)) - 1]
