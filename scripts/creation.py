# file: scripts/creation.py
"""Character creation with flaws, Creation Points and talents (docs/PROGRESSION.md).
ALL NUMBERS ARE PLACEHOLDERS."""
import json
import os

import talents as T

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8-sig") as f:
        return json.load(f)


def rules():
    return _load("rules/progression.json")["creation"]


def load_flaws():
    return {k: v for k, v in _load("rules/creation/flaws.json").items() if k != "meta"}


def base_stats(race, gender):
    return _load("rules/stats.json").get(f"{race}_{gender}", {"starting_stats": {}, "max_stats": {}})


def flaw_cp(flaw, chosen_cp=None):
    cp = flaw["cp"]
    if isinstance(cp, list):  # range, e.g. Old Debt 1-3 (GM sets)
        lo, hi = cp
        return max(lo, min(hi, chosen_cp if chosen_cp is not None else lo))
    return cp


def caps_for(race, gender, talent_ids=(), flaw_ids=()):
    """Final caps: stats.json max + talent raises (max +5) + flaw cap penalties."""
    caps = dict(base_stats(race, gender)["max_stats"])
    flaws = load_flaws()
    for stat in list(caps):
        caps[stat] += T.cap_raise(stat, race, gender, talent_ids)
        for fid in flaw_ids:
            caps[stat] += flaws.get(fid, {}).get("effects", {}).get("cap_mods", {}).get(stat, 0)
    return caps


def create_character(race, gender, flaws=(), talents=(), stat_buys=None, flaw_cp_choice=None):
    """Build starting stats. flaws/talents: id lists. stat_buys: {stat: CP spent} (1 CP = +2).
    Returns dict(stats, caps, cp_total, cp_spent, cp_left, talents, flaws, errors). Errors list empty = legal."""
    R = rules()
    errors = []
    flaw_data = load_flaws()
    flaw_cp_choice = flaw_cp_choice or {}
    stat_buys = stat_buys or {}
    base = base_stats(race, gender)
    if not base["starting_stats"]:
        errors.append(f"unknown race/gender {race}_{gender}")
    stats = dict(base["starting_stats"])

    # Flaws -> CP
    earned = 0
    for fid in flaws:
        f = flaw_data.get(fid)
        if not f:
            errors.append(f"unknown flaw {fid}"); continue
        r = f.get("restrictions") or {}
        if (r.get("gender") and gender not in r["gender"]) or (r.get("race") and race not in r["race"]):
            errors.append(f"flaw {fid} not allowed for {race} {gender}")
        for other in f.get("excludes_flaws", []):
            if other in flaws:
                errors.append(f"flaw {fid} cannot be combined with {other}")
        for t in f.get("excludes_talents", []):
            if t in talents:
                errors.append(f"flaw {fid} cannot be combined with talent {t}")
        earned += flaw_cp(f, flaw_cp_choice.get(fid))
        eff = f.get("effects", {})
        for s, v in eff.get("stat_mods", {}).items():
            stats[s] = stats.get(s, 0) + v
        for s, v in eff.get("start_set", {}).items():
            stats[s] = v
    earned = min(earned, R["max_flaw_cp"])
    cp_total = min(R["free_cp"] + earned, R["max_total_cp"])

    # Talents
    if len(talents) > R["max_talents_at_creation"]:
        errors.append(f"max {R['max_talents_at_creation']} talents at creation")
    spent = 0
    for tid in talents:
        t = T.get_talent(tid)
        if not t:
            errors.append(f"unknown talent {tid}"); continue
        if not T.allowed_for(t, race, gender):
            errors.append(f"talent {tid} not allowed for {race} {gender}")
        for fl in t.get("excludes_flaws", []):
            if fl in flaws:
                errors.append(f"talent {tid} cannot be combined with flaw {fl}")
        spent += t.get("cp", 0)
        for s, v in t.get("effects", {}).get("start_bonus", {}).items():
            stats[s] = stats.get(s, 0) + v

    # Stat buys
    caps = caps_for(race, gender, talents, flaws)
    for s, cp in stat_buys.items():
        raise_by = cp * R["stat_points_per_step"]
        if raise_by > R["max_stat_raise_at_creation"] + 1:  # 3 CP = +6 is over the +5 limit
            errors.append(f"{s}: max +{R['max_stat_raise_at_creation']} from CP at creation")
        spent += cp
        stats[s] = stats.get(s, 0) + min(raise_by, R["max_stat_raise_at_creation"])
    for s, v in stats.items():
        if s in caps and v > caps[s]:
            stats[s] = caps[s]

    if spent > cp_total:
        errors.append(f"spent {spent} CP but only {cp_total} available")
    return {"race": race, "gender": gender, "stats": stats, "caps": caps, "cp_total": cp_total,
            "cp_spent": spent, "cp_left": cp_total - spent, "talents": list(talents),
            "flaws": list(flaws), "errors": errors}
