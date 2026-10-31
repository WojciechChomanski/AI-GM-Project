# file: scripts/talents.py
"""Talents loader (docs/PROGRESSION.md). Data: rules/talents/*.json, one file per group."""
import glob
import json
import os

TALENT_DIR = os.path.join(os.path.dirname(__file__), "..", "rules", "talents")
CAP_RAISE_LIMIT = 5
_cache = None


def load_talents(refresh=False):
    """All talents keyed by id, each with its 'group'."""
    global _cache
    if _cache is None or refresh:
        out = {}
        for path in sorted(glob.glob(os.path.join(TALENT_DIR, "*.json"))):
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
            group = data.get("meta", {}).get("group", os.path.splitext(os.path.basename(path))[0])
            for tid, t in data.items():
                if tid == "meta":
                    continue
                out[tid] = dict(t, id=tid, group=group)
        _cache = out
    return _cache


def get_talent(tid):
    return load_talents().get(tid)


def allowed_for(talent, race, gender):
    r = talent.get("restrictions") or {}
    if r.get("race") and race not in r["race"]:
        return False
    if r.get("gender") and gender not in r["gender"]:
        return False
    pairs = r.get("race_gender_any")
    if pairs and [race, gender] not in [list(p) for p in pairs]:
        return False
    return True


def _effects(talent_ids, race, gender):
    for tid in talent_ids or ():
        t = get_talent(tid)
        if t and allowed_for(t, race, gender):
            yield t.get("effects", {})


def cap_raise(stat, race, gender, talent_ids):
    """Total cap raise for a stat from eligible talents, never more than +5."""
    total = sum(e.get("cap_raise", {}).get(stat, 0) for e in _effects(talent_ids, race, gender))
    return min(total, CAP_RAISE_LIMIT)


def start_bonus(stat, race, gender, talent_ids):
    return sum(e.get("start_bonus", {}).get(stat, 0) for e in _effects(talent_ids, race, gender))


def growth_mult(stat, race, gender, talent_ids):
    """Use multiplier for stat growth (0.75 = 25% faster). Strongest one wins, no stacking."""
    mults = [e.get("growth_mult", {}).get(stat) for e in _effects(talent_ids, race, gender)]
    mults = [m for m in mults if m]
    return min(mults) if mults else 1.0


def mastery_uses_mult(track, race, gender, talent_ids, melee_tracks=()):
    best = 1.0
    for e in _effects(talent_ids, race, gender):
        m = e.get("mastery_uses_mult")
        if not m:
            continue
        tracks = m.get("tracks")
        if tracks == "all" or (tracks == "all_melee" and track in melee_tracks) or (isinstance(tracks, list) and track in tracks):
            best = min(best, m.get("mult", 1.0))
    return best
