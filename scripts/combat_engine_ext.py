# AI_GM_Project/scripts/combat_engine_ext.py
"""
Drop-in helpers (stamina, morale/rout, 2H+shield enforcement, aimed-attack penalty)
PLUS a safe wrapper that re-exports CombatEngine/load_rules from combat_engine.py
— and provides a fallback load_rules if combat_engine.py doesn't have one.
"""

from __future__ import annotations
import logging, json, os
from typing import Any, Dict

log = logging.getLogger(__name__)

# -------------------------
# small utils
# -------------------------
def _stance_key(stance):
    return (stance or "neutral").lower()

def _get(dic, path, default=None):
    cur = dic
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        if part not in cur:
            return default
        cur = cur[part]
    return cur

# -------------------------
# helpers (stamina, morale, etc.)
# -------------------------
def enforce_two_handed_and_shield(char, weapon_data, rules, logs):
    if not weapon_data or not isinstance(weapon_data, dict):
        return
    ttypes = _get(rules, "two_handed_and_shields.two_handed_types", [])
    allow = bool(_get(rules, "two_handed_and_shields.allow", False))
    wtype = str(weapon_data.get("type", "")).strip()
    is_two_handed = any(wtype.startswith(tt) for tt in ttypes) or wtype.startswith("2H")
    if is_two_handed and char.get("shield_equipped") and not allow:
        char["shield_equipped"] = False
        logs.append(
            f"⛔ {char.get('name','?')}: {weapon_data.get('name','Two-handed weapon')} "
            f"requires two hands; auto-unequipping shield."
        )

def spend_stamina(actor, action_kind, stance, ability_name, rules, logs):
    if actor is None:
        return 0
    if "current_stamina" not in actor:
        actor["current_stamina"] = actor.get("max_stamina", 0)
    costs = _get(rules, "stamina_costs", {}) or {}
    base = 0
    if action_kind == "attack":
        base += int(costs.get("attack_base", 0))
    elif action_kind in ("parry", "block", "dodge"):
        base += int(costs.get(action_kind, 0))
    base += int(_get(rules, f"stamina_costs.stance.{_stance_key(stance)}", 0))
    if ability_name:
        ability = actor.get("abilities", {}).get(ability_name, {})
        base += int(ability.get("stamina_cost", 0))
    armor_mult = 1.0
    final_cost = max(0, int(round(base * armor_mult)))
    before = actor["current_stamina"]
    actor["current_stamina"] = max(0, before - final_cost)
    logs.append(
        f"🫁 {actor.get('name','?')} stamina -{final_cost} ➜ "
        f"ST: {actor['current_stamina']}/{actor.get('max_stamina',0)}"
    )
    return final_cost

def regen_stamina(char, stance, rules, logs):
    """
    Prefers rules.stamina_regen map (e.g., {'offensive':2,'neutral':3,'defensive':4}).
    Falls back to rules.stamina_regeneration.base * (1+stance_synergies.stamina_regen_pct/100).
    """
    if char is None:
        return 0
    if "current_stamina" not in char:
        char["current_stamina"] = char.get("max_stamina", 0)

    # Preferred: explicit per-stance values
    sr = _get(rules, "stamina_regen", None)
    if isinstance(sr, dict):
        regen = int(sr.get(_stance_key(stance), sr.get("neutral", 0)))
    else:
        # Legacy fallback
        base = int(_get(rules, "stamina_regeneration.base", 0))
        stance_rules = _get(rules, f"stance_synergies.{_stance_key(stance)}", {}) or {}
        regen_pct = int(stance_rules.get("stamina_regen_pct", 0))
        regen = int(round(base * (1 + regen_pct / 100.0)))

    before = char["current_stamina"]
    char["current_stamina"] = min(char.get("max_stamina", 0), before + regen)
    gained = char["current_stamina"] - before
    if gained > 0:
        logs.append(f"💤 {char.get('name','?')} recovers {gained} stamina (stance: {stance}).")
    return gained

def init_morale(char):
    if char is None:
        return
    if "morale" not in char:
        char["morale"] = 100

def morale_event(char, event, rules, logs):
    if char is None:
        return
    fs = _get(rules, "fear_system", {}) or {}
    if not fs.get("enabled", True):
        return
    drop = 0
    if event == "ally_down":
        drop += int(fs.get("on_ally_down_morale_drop", 0))
    elif isinstance(event, dict):
        et = event.get("type")
        if et == "heavy_hit":
            drop += int(fs.get("heavy_hit_morale_drop", 0))
        elif et == "headshot":
            drop += int(fs.get("headshot_morale_drop", 0))
    if drop:
        before = char.get("morale", 100)
        min_morale = int(fs.get("min_morale", 0))
        char["morale"] = max(min_morale, before - drop)
        label = event if isinstance(event, str) else event.get("type", "event")
        logs.append(f"😨 {char.get('name','?')} morale {before}→{char['morale']} ({label})")

def check_rout(team_chars, rules, logs):
    fs = _get(rules, "fear_system", {}) or {}
    if not fs.get("enabled", True):
        return False
    if not team_chars:
        return False
    avg = sum(c.get("morale", 100) for c in team_chars) / max(1, len(team_chars))
    threshold = int(fs.get("rout_threshold", 10))
    if avg <= threshold:
        logs.append("🏳️ The enemy loses nerve and routs!")
        return True
    return False

def aimed_attack_penalty(attacker, rules):
    """
    Flat aimed penalty (e.g., 30) minus DEX relief ratio.
    Keeps your classic feel; ignores per-zone maps.
    """
    base = int(_get(rules, "aimed_attack.base_penalty", 30))
    ratio = float(_get(rules, "aimed_attack.dex_bonus_ratio", 0.0))
    dex = int(attacker.get("dexterity", attacker.get("DEX", attacker.get("dex", 0))))
    bonus = int(round(dex * ratio))
    pen = max(0, base - bonus)
    return pen

# -------------------------
# load_rules: prefer base engine's version, else fallback here
# -------------------------
def _fallback_load_rules(path_or_dict: Any) -> Dict[str, Any]:
    """
    Minimal, robust loader:
      - if given a dict, returns it
      - if given a path, reads JSON and returns a dict
      - never crashes on missing optional keys (helpers default safely via _get)
    """
    if isinstance(path_or_dict, dict):
        rules = dict(path_or_dict)  # shallow copy
        log.debug("combat_engine_ext: rules supplied as dict, %d top-level keys", len(rules))
        return rules
    if not isinstance(path_or_dict, str):
        raise TypeError("load_rules(path_or_dict): expected file path (str) or dict of rules")
    path = os.path.normpath(path_or_dict)
    with open(path, "r", encoding="utf-8") as f:
        rules = json.load(f)
    # optional: ensure some sections exist so _get has something to traverse
    rules.setdefault("stamina_regeneration", {"base": 0})
    rules.setdefault("stance_synergies", {})
    rules.setdefault("stamina_costs", {})
    rules.setdefault("fear_system", {"enabled": False})
    rules.setdefault("aimed_attack", {"base_penalty": 30})
    rules.setdefault("two_handed_and_shields", {"two_handed_types": ["2H_", "greatsword", "polearm"], "allow": False})
    log.debug("combat_engine_ext: loaded rules from %s with %d top-level keys", path, len(rules))
    return rules

try:
    # Try to re-export from your base engine if available
    from combat_engine import CombatEngine as _BaseCombatEngine  # type: ignore
    try:
        from combat_engine import load_rules as _base_load_rules  # type: ignore
    except Exception:
        _base_load_rules = None
    _import_error = None
except Exception as e:
    _BaseCombatEngine = None
    _base_load_rules = None
    _import_error = e

def load_rules(path_or_dict: Any) -> Dict[str, Any]:
    """
    Uses combat_engine.load_rules if it exists; otherwise uses our fallback that simply
    reads the JSON and injects safe defaults for optional sections.
    """
    if _base_load_rules is not None:
        return _base_load_rules(path_or_dict)  # type: ignore[misc]
    return _fallback_load_rules(path_or_dict)

# -------------------------
# Safe CombatEngine wrapper
# -------------------------
if _BaseCombatEngine is not None:
    class CombatEngine(_BaseCombatEngine):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            log.debug("combat_engine_ext: CombatEngine wrapper initialized")
else:
    class CombatEngine:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "combat_engine_ext: couldn't import CombatEngine from combat_engine.py. "
                "Make sure scripts/combat_engine.py exists and defines `CombatEngine`.\n"
                f"Original error: {_import_error!r}"
            )

__all__ = [
    # helpers
    "enforce_two_handed_and_shield", "spend_stamina", "regen_stamina",
    "init_morale", "morale_event", "check_rout", "aimed_attack_penalty",
    # engine + rules loader
    "CombatEngine", "load_rules",
]




