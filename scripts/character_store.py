# file: scripts/character_store.py
"""Simple JSON save/load of a character's body state so the GM console can find characters (docs/RECOVERY.md).
Files: saves/characters/<name>.json (git-ignored). Saves zones, wounds, limb states, infection, regrowth,
prostheses and the main stats; loading rebuilds a Character + CombatHealthManager."""
import json
import os
import re

from character import Character
from combat_health import CombatHealthManager

ROOT = os.path.join(os.path.dirname(__file__), "..")
SAVE_DIR = os.path.join(ROOT, "saves", "characters")
STAT_FIELDS = ("race", "gender", "class_name", "strength", "toughness", "agility", "dexterity", "endurance",
               "intelligence", "willpower", "perception", "charisma", "stress_level", "corruption_level",
               "corruption_peak", "faith", "virtue", "piety", "talents", "flaws", "skills", "prostheses",
               "compromised_limbs", "bleed_clot_mult", "bleed_rate_mult")
MANAGER_FIELDS = ("limb_state", "infection", "regrowing", "zone_armor_bonus", "heal_carry")


def _path(name, folder=None):
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    return os.path.join(folder or SAVE_DIR, safe + ".json")


def to_dict(manager):
    c = manager.character
    d = {"name": c.name, "alive": getattr(c, "alive", True),
         "health": manager.health, "initial_health": manager.initial_health,
         "bleeding_wounds": manager.bleeding_wounds}
    d.update({f: getattr(c, f) for f in STAT_FIELDS if hasattr(c, f)})
    d.update({f: getattr(manager, f) for f in MANAGER_FIELDS if getattr(manager, f, None) is not None})
    return d


def from_dict(d):
    c = Character()
    c.name = d["name"]
    for f in STAT_FIELDS:
        if f in d:
            setattr(c, f, d[f])
    c.body_parts = dict(d["health"])
    c.pain_penalty = getattr(c, "pain_penalty", 0) or 0
    m = CombatHealthManager(c)
    m.initial_health = dict(d["initial_health"])
    m.bleeding_wounds = list(d.get("bleeding_wounds", []))
    for f in MANAGER_FIELDS:
        if f in d:
            setattr(m, f, d[f])
    m.refresh_bleeding()
    m._sync_total()
    c.alive = d.get("alive", True)
    return m


def save(manager, folder=None):
    folder = folder or SAVE_DIR
    os.makedirs(folder, exist_ok=True)
    p = _path(manager.character.name, folder)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(to_dict(manager), f, indent=2, ensure_ascii=False)
    return p


def load(name, folder=None):
    with open(_path(name, folder), encoding="utf-8-sig") as f:
        return from_dict(json.load(f))


def list_saved(folder=None):
    folder = folder or SAVE_DIR
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-5] for f in os.listdir(folder) if f.endswith(".json"))


def console_command(line, loaded, folder=None):
    """GM console helper. Commands: list | load <name> | save <name>|all | status <name> | tick ... (time_loop).
    loaded: {name: manager} kept by the console. Returns text."""
    import time_loop
    p = line.strip().split()
    if not p:
        return ""
    cmd = p[0].lower()
    if cmd == "list":
        return "saved: " + ", ".join(list_saved(folder)) + " | loaded: " + ", ".join(loaded)
    if cmd == "load" and len(p) > 1:
        try:
            loaded[p[1]] = load(p[1], folder)
        except FileNotFoundError:
            return f"no save for {p[1]}"
        return f"loaded {p[1]}"
    if cmd == "save" and len(p) > 1:
        names = list(loaded) if p[1] == "all" else [p[1]]
        return "saved " + ", ".join(os.path.basename(save(loaded[n], folder)) for n in names if n in loaded)
    if cmd == "status" and len(p) > 1 and p[1] in loaded:
        m = loaded[p[1]]
        return (f"{p[1]}: {m.total_hp} HP, bleeding {m.character.bleeding}/round, "
                f"limbs {getattr(m, 'limb_state', {})}, infection {bool(getattr(m, 'infection', None))}")
    if cmd == "tick":
        res = time_loop.gm_command(line, loaded)
        if "error" in res:
            return res["error"]
        return "\n".join(f"{n}: {r[-1]} ({len(r)} ticks)" for n, r in res.items())
    return "commands: list | load <name> | save <name>|all | status <name> | tick round [n] | tick day [n] [mode] [unfed]"
