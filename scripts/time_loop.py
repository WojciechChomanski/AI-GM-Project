# file: scripts/time_loop.py
"""Round and day ticks (rules/time_loop.json, docs/RECOVERY.md). Safe per character and from a GM command.
Round: bleeding + clotting (CombatHealthManager.apply_bleeding) then corrupted regeneration.
Day: infection, then natural healing by rest mode (no healing while bleeding/infected, zones at 0 stay)."""
import json
import os

import limb_repair
import wound_recovery as WR

ROOT = os.path.join(os.path.dirname(__file__), "..")


def cfg():
    with open(os.path.join(ROOT, "rules/time_loop.json"), encoding="utf-8-sig") as f:
        return json.load(f)


def round_tick(manager=None, creature=None):
    """One round. manager: CombatHealthManager or None; creature: corruption.CorruptedCreature or None."""
    rep = {}
    if manager is not None and getattr(manager.character, "alive", True):
        rep["bled"] = manager.apply_bleeding()
        rep["alive"] = manager.character.alive
    if creature is not None and not creature.dead:
        rep["regenerated"] = WR.regen_round(creature)
    return rep


def day_tick(manager, mode=None, fed=True, rng=None):
    mode = mode or cfg()["default_rest_mode"]
    if mode not in cfg()["day_rest_modes"]:
        raise ValueError(f"rest mode must be one of {cfg()['day_rest_modes']}")
    if not getattr(manager.character, "alive", True):
        return {"healed": 0, "alive": False}
    limb_repair.states(manager)
    inf = limb_repair.infection_day(manager, rng)
    healed = 0 if getattr(manager, "infection", None) else WR.heal_manager_day(manager, fed, mode)
    return {"healed": healed, "infection": inf, "mode": mode}


def gm_command(line, characters, creatures=None):
    """'tick round [n]' | 'tick day [n] [mode] [unfed]'. characters: {name: CombatHealthManager};
    creatures: {name: CorruptedCreature}. Returns {name: [reports]}."""
    p = line.strip().lower().split()
    if len(p) < 2 or p[0] != "tick" or p[1] not in ("round", "day"):
        return {"error": "usage: tick round [n] | tick day [n] [resting|bed_rest_with_care|travelling] [unfed]"}
    n = min(int(p[2]) if len(p) > 2 and p[2].isdigit() else 1, cfg()["max_ticks_per_command"])
    creatures = creatures or {}
    out = {}
    for _ in range(n):
        if p[1] == "round":
            for name, m in characters.items():
                out.setdefault(name, []).append(round_tick(manager=m))
            for name, c in creatures.items():
                out.setdefault(name, []).append(round_tick(creature=c))
        else:
            mode = next((x for x in p[2:] if x in cfg()["day_rest_modes"]), None)
            for name, m in characters.items():
                out.setdefault(name, []).append(day_tick(m, mode, fed="unfed" not in p))
    return out
