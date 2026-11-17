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


def breath_state(virtue, piety, corruption=0, cap_at_dim=False):
    """'full' | 'dim' | 'none'. Corruption >= 25 counts as dim at best.
    An open grave stain or a broken vow (Rule of Life) caps the result at dim."""
    b = vows()["breath"]
    f = b["full"]
    if virtue >= f["virtue_min"] and piety >= f["piety_min"] and corruption <= f["corruption_max"]:
        st = "full"
    elif virtue >= b["dim"]["virtue_min"]:
        st = "dim"
    else:
        st = "none"
    if cap_at_dim and st == "full":
        return "dim"
    return st


def _norm_tags(target_tags):
    """Align vow target tags with the witch-hunter list; accept 'corrupted' as an alias."""
    aliases = vows()["breath"].get("kind_aliases") or {"corrupted": "corrupted_beast"}
    tags = set(target_tags or ())
    for raw, canon in aliases.items():
        if raw in tags:
            tags.add(canon)
    return tags


def breath_state_for(character):
    """Read hidden Virtue/Piety/Corruption and the Rule of Life cap from a character."""
    def _g(name, default=0):
        if isinstance(character, dict):
            val = character.get(name, default)
        else:
            val = getattr(character, name, default)
        return val if val is not None else default

    cap = False
    try:
        import rule_of_life
        cap = rule_of_life.caps_breath_at_dim(character)
    except Exception:
        cap = False
    return breath_state(_g("virtue"), _g("piety"), _g("corruption_level") or _g("corruption"), cap_at_dim=cap)


def breath_effects(virtue, piety, corruption=0, target_tags=(), cap_at_dim=False):
    """Effects of his wounds on this target. Only at 'full' Breath and only vs Veil-born/corrupted.
    Never changes his normal weapon damage (steel rule). Passive only."""
    b = vows()["breath"]
    st = breath_state(virtue, piety, corruption, cap_at_dim=cap_at_dim)
    eff = dict(b[st]["effects"]) if st != "full" else {"holy_fury_max_stacks": b["full"]["effects"]["holy_fury_max_stacks"]}
    if st == "full" and _norm_tags(target_tags) & set(b["full"]["vs"]):
        eff = dict(b["full"]["effects"])
    eff["state"] = st
    return eff


def virtue_loss(event):
    """Virtue lost for an event in rules/virtue_rules.json (0 if unknown)."""
    return _load("rules/virtue_rules.json")["virtue"]["loss_events"].get(event, 0)


def discipline(step):
    return vows()["discipline_ladder"][max(1, min(4, step)) - 1]
