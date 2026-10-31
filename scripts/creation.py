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


def load_advantages():
    return {k: v for k, v in _load("rules/creation/advantages.json").items() if k != "meta"}


def creation_rules():
    return _load("rules/creation/creation_rules.json")


def _allowed(entry, race, gender, class_name):
    r = entry.get("restrictions") or {}
    if r.get("race") and race not in r["race"]:
        return False
    if r.get("gender") and gender not in r["gender"]:
        return False
    if r.get("class") and class_name not in r["class"]:
        return False
    return class_name not in entry.get("forbidden_classes", [])


def options_for(race, gender, class_name=None):
    """What one character may see: general lists plus the sets matching race/gender/class."""
    adv = {k: v for k, v in load_advantages().items()
           if "talent_ref" in v and T.allowed_for(T.get_talent(v["talent_ref"]), race, gender)
           or "talent_ref" not in v and _allowed(v, race, gender, class_name)}
    dis = {k: v for k, v in load_flaws().items() if _allowed(v, race, gender, class_name)}
    if class_name == "Crusader_Knight":
        for vow in _vows()["vows"].values():
            for a in vow.get("forbids_advantages", []):
                adv.pop(a, None)
    return {"advantages": adv, "disadvantages": dis}


def _vows():
    return _load("rules/orders/crusader_vows.json")


def flaw_intensity(flaw, chosen=None):
    """Intensity used for the heavy-load rule: chosen intensity, or the CP for fixed flaws."""
    if flaw["cp"] == "intensity":
        lo, hi = flaw.get("intensity_range", [1, 5])
        return max(lo, min(hi, chosen or lo))
    return flaw_cp(flaw, chosen)


def flaw_cp(flaw, chosen_cp=None):
    cp = flaw["cp"]
    if cp == "intensity":
        return flaw_intensity(flaw, chosen_cp)
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


def flaw_payout(flaw_cps):
    """Diminishing returns + same-area rule. flaw_cps: list of (id, cp, area).
    Returns (earned_before_cap, {id: paid})."""
    CR = creation_rules()
    best_in_area = {}
    for fid, cp, area in flaw_cps:
        if area and (area not in best_in_area or cp > best_in_area[area][1]):
            best_in_area[area] = (fid, cp)
    paying = [(fid, cp) for fid, cp, area in flaw_cps if not area or best_in_area[area][0] == fid]
    paying.sort(key=lambda x: -x[1])
    full, half = CR["diminishing"]["full_pay_count"], CR["diminishing"]["half_pay_count"]
    paid = {fid: 0 for fid, _, _ in flaw_cps}
    for i, (fid, cp) in enumerate(paying):
        paid[fid] = cp if i < full else cp // 2 if i < full + half else 0
    return sum(paid.values()), paid


def create_character(race, gender, flaws=(), talents=(), stat_buys=None, flaw_cp_choice=None,
                     advantages=None, class_name=None):
    """Build starting stats.
    flaws: list of ids or {id: intensity/CP level}. talents: id list. advantages: {id: level} (talent_ref
    entries count as talents). stat_buys: {stat: CP spent} (1 CP = +2). class_name: e.g. Crusader_Knight.
    Returns dict(stats, caps, cp_total, cp_spent, cp_left, talents, flaws, flaw_paid, heavy_load, vows,
    errors, gm_only). Errors list empty = legal."""
    R = rules()
    CR = creation_rules()
    errors = []
    flaw_data = load_flaws()
    flaw_cp_choice = dict(flaw_cp_choice or {})
    if isinstance(flaws, dict):
        flaw_cp_choice.update(flaws)
        flaws = list(flaws)
    flaws = list(flaws)
    talents = list(talents)
    advantages = dict(advantages or {})
    adv_data = load_advantages()
    adv_cp = 0
    for aid, level in advantages.items():
        a = adv_data.get(aid)
        if not a:
            errors.append(f"unknown advantage {aid}"); continue
        if "talent_ref" in a:
            talents.append(a["talent_ref"]); continue
        if not _allowed(a, race, gender, class_name):
            errors.append(f"advantage {aid} not allowed for {race} {gender} {class_name or ''}".strip())
        cp = a["cp"]
        adv_cp += max(cp[0], min(cp[1], level or cp[0])) if isinstance(cp, list) else cp
    vows = list(_vows()["vows"]) if class_name == "Crusader_Knight" else []
    stat_buys = stat_buys or {}
    base = base_stats(race, gender)
    if not base["starting_stats"]:
        errors.append(f"unknown race/gender {race}_{gender}")
    stats = dict(base["starting_stats"])

    # Flaws -> CP (diminishing returns, same-area rule, 10 CP cap; the rest are 0-CP story flaws)
    flaw_cps = []
    total_intensity = 0
    for fid in flaws:
        f = flaw_data.get(fid)
        if not f:
            errors.append(f"unknown flaw {fid}"); continue
        if not _allowed(f, race, gender, class_name):
            errors.append(f"flaw {fid} not allowed for {race} {gender}")
        for other in f.get("excludes_flaws", []):
            if other in flaws:
                errors.append(f"flaw {fid} cannot be combined with {other}")
        for t in f.get("excludes_talents", []):
            if t in talents:
                errors.append(f"flaw {fid} cannot be combined with talent {t}")
        for a in f.get("excludes_advantages", []):
            if a in advantages:
                errors.append(f"flaw {fid} cannot be combined with advantage {a}")
        flaw_cps.append((fid, flaw_cp(f, flaw_cp_choice.get(fid)), f.get("area")))
        total_intensity += flaw_intensity(f, flaw_cp_choice.get(fid))
        eff = f.get("effects", {})
        for s, v in eff.get("stat_mods", {}).items():
            stats[s] = stats.get(s, 0) + v
        for s, v in eff.get("start_set", {}).items():
            stats[s] = v
    earned, flaw_paid = flaw_payout(flaw_cps)
    earned = min(earned, R["max_flaw_cp"])
    heavy = total_intensity >= CR["heavy_load"]["total_intensity_min"]
    if heavy:
        stats["stress_level"] = stats.get("stress_level", 0) + CR["heavy_load"]["start_stress"]
    cp_total = min(R["free_cp"] + earned, R["max_total_cp"])

    # Talents
    max_t = R["max_talents_at_creation"] + (1 if "adaptable" in advantages else 0)
    if len(talents) > max_t:
        errors.append(f"max {max_t} talents at creation")
    spent = adv_cp
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
            "flaws": list(flaws), "flaw_paid": flaw_paid, "total_intensity": total_intensity,
            "heavy_load": heavy, "advantages": advantages, "vows": vows, "class": class_name,
            "errors": errors}


def player_view(stats):
    """Stats a player may see: GM-only stats (rules/stat_visibility.json) removed."""
    hidden = set(_load("rules/stat_visibility.json")["gm_only"])
    return {k: v for k, v in stats.items() if k not in hidden}
