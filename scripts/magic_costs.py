# file: scripts/magic_costs.py
"""Fixed per-cast corruption and the confirmed stamina formula.

Corruption is GM-only (rules/stat_visibility.json): never write it onto a Foundry actor.
Numbers in rules/magic_rules.json are PLACEHOLDER.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8-sig") as f:
        return json.load(f)


def magic_rules():
    return _load("rules", "magic_rules.json")


def corruption_cfg():
    return magic_rules()["corruption"]


def corruption_cap():
    return int(corruption_cfg().get("cap", 100))


def band_amount(band):
    return int(corruption_cfg()["bands"][band])


def spell_corruption(spell):
    """Guaranteed corruption for a successful cast of this spell dict or raw int."""
    if spell is None:
        return 0
    if isinstance(spell, (int, float)):
        return int(spell)
    if "corruption_gain" in spell and isinstance(spell["corruption_gain"], (int, float)):
        return int(spell["corruption_gain"])
    c = spell.get("corruption")
    if isinstance(c, (int, float)):
        return int(c)
    if isinstance(c, dict) and "amount" in c:
        return int(c["amount"])
    return 0


def scene_snowball(prior_casts, current_corruption=0):
    cfg = corruption_cfg()
    prior = max(0, int(prior_casts or 0))
    if current_corruption >= int(cfg.get("snowball_after", 75)):
        return prior * int(cfg.get("snowball_after_extra", 2))
    return prior * int(cfg.get("snowball_per_prior_cast_in_scene", 1))


def gain_for_cast(spell, failed=False, prior_casts_this_scene=0, current_corruption=0):
    """Total corruption added for one attempt. failed still pays fail_extra on top of the base."""
    base = spell_corruption(spell)
    extra = int(corruption_cfg().get("fail_extra", 0)) if failed else 0
    return base + extra + scene_snowball(prior_casts_this_scene, current_corruption)


def _get(obj, name, default=0):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _set(obj, name, value):
    if isinstance(obj, dict):
        obj[name] = value
    else:
        setattr(obj, name, value)


def add_corruption(character, amount, cap=None):
    """Raise hidden corruption, clamped to the cap. Returns the actual amount added."""
    cap = corruption_cap() if cap is None else cap
    cur = int(_get(character, "corruption_level", 0) or 0)
    new = max(0, min(int(cap), cur + int(amount)))
    _set(character, "corruption_level", new)
    peak = int(_get(character, "corruption_peak", cur) or cur)
    _set(character, "corruption_peak", max(peak, new))
    return new - cur


def apply_cast_corruption(character, spell, failed=False, prior_casts_this_scene=0):
    """Apply the unified fixed gain for one cast. Returns the amount added."""
    cur = int(_get(character, "corruption_level", 0) or 0)
    total = gain_for_cast(spell, failed, prior_casts_this_scene, cur)
    added = add_corruption(character, total)
    casts = int(_get(character, "_casts_this_fight", 0) or 0)
    _set(character, "_casts_this_fight", casts + 1)
    return added


def race_stamina_bonus(race_data):
    if not race_data:
        return 0
    stats = race_data.get("stats") if isinstance(race_data, dict) and "stats" in race_data else race_data
    return int((stats or {}).get("stamina_bonus", 0) or 0)


def class_stamina_flat(class_data):
    if not class_data:
        return 0
    mods = class_data.get("stat_modifiers") or {}
    return int(mods.get("stamina_max_flat", 0) or 0)


def stamina_max(race_data=None, class_data=None, race_bonus=None, class_flat=None):
    """Confirmed formula: 100 + race stamina_bonus + class stamina_max_flat."""
    bonus = race_stamina_bonus(race_data) if race_bonus is None else int(race_bonus or 0)
    flat = class_stamina_flat(class_data) if class_flat is None else int(class_flat or 0)
    return 100 + bonus + flat
