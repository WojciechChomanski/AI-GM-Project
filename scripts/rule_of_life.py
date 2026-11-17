# file: scripts/rule_of_life.py
"""Crusader Knight Rule of Life (rules/rule_of_life.json, docs/RULE_OF_LIFE.md).

Hidden only: stain ledger, Rule Ward, Virtue ceiling, piety-from-the-Rule and
penance progress never go on a Foundry actor. The player sees felt lines only.
Several numeric values are PLACEHOLDER (see the JSON status fields and the doc).
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = None


def data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(ROOT, "rules", "rule_of_life.json"), encoding="utf-8-sig") as f:
            _DATA = json.load(f)
    return _DATA


def reload():
    global _DATA
    _DATA = None
    return data()


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _set(obj, name, value):
    if isinstance(obj, dict):
        obj[name] = value
    else:
        setattr(obj, name, value)


def _int(obj, name, default=0):
    try:
        return int(_get(obj, name, default) or default)
    except (TypeError, ValueError):
        return default


def _class_name(c):
    return _get(c, "class_name", None) or _get(c, "char_class", None) or ""


def _path_id(c):
    st = _get(c, "order_path") or _get(c, "path") or {}
    if isinstance(st, dict):
        return st.get("path") or ""
    try:
        import order_paths
        return (order_paths.state(c) or {}).get("path") or ""
    except Exception:
        return ""


def under_the_rule(c):
    cfg = data()
    if _class_name(c) in cfg["applies_to_classes"]:
        return True
    return _path_id(c) in cfg["applies_to_paths"]


def _blank_state():
    return {
        "stains": [],
        "next_id": 1,
        "rule_ward": 0,
        "rule_kept_streak": 0,
        "day": 0,
        "week_cleanse_used": 0,
        "week_cleanse_days": 0,
        "week_started_on": 0,
        "virtue_gain_log": {},
        "devotion_week": {"gained": 0, "started_on": 0, "confession_day": None, "fasting_day": None},
        "house_status": "in_house",
        "last_rule_kept": None,
        "pending_felt": None,
        "loss_of_house_required": False,
    }


def state(c):
    st = _get(c, "rule_of_life")
    if not isinstance(st, dict):
        st = _blank_state()
        _set(c, "rule_of_life", st)
    for k, v in _blank_state().items():
        st.setdefault(k, v)
    return st


def sin_def(key):
    row = data()["sins"].get(key)
    if not row:
        raise KeyError(f"unknown sin: {key}")
    return row


def is_grave(row):
    return row.get("grade") == "grave" or int(row.get("weight", 0)) >= data()["stain"]["grave_min_weight"]


def open_stains(c, grade=None):
    out = [s for s in state(c)["stains"] if s.get("open")]
    if grade:
        out = [s for s in out if s.get("grade") == grade]
    return out


def open_grave_weight(c):
    return sum(int(s.get("weight", 0)) for s in open_stains(c, "grave"))


def virtue_ceiling(c):
    base = int(data()["virtue"]["base_ceiling"])
    return max(0, base - open_grave_weight(c))


def broken_vow_open(c):
    return any(s.get("open") and s.get("breaks_vow") for s in state(c)["stains"])


def caps_breath_at_dim(c):
    return bool(open_stains(c, "grave") or broken_vow_open(c))


def _clip_virtue(c):
    ceil = virtue_ceiling(c)
    v = _int(c, "virtue", 0)
    if v > ceil:
        _set(c, "virtue", ceil)
        return ceil
    return v


def record_sin(c, key):
    """Apply virtue loss, hidden stain, and (if grave) hidden corruption. Does not lift anything."""
    row = sin_def(key)
    st = state(c)
    stain = {
        "id": f"s{st['next_id']}",
        "key": key,
        "deadly_sin": row["deadly_sin"],
        "weight": int(row["weight"]),
        "grade": "grave" if is_grave(row) else "venial",
        "corruption": int(row.get("corruption") or 0),
        "day": st["day"],
        "unconfessed_days": 0,
        "open": True,
        "confessed": False,
        "restitution": False,
        "penance_remaining": int(row["weight"]) if is_grave(row) and data()["stain"]["penance"].get("days_equal_weight") else 0,
        "penance_done": False,
        "breaks_vow": row.get("breaks_vow"),
        "loss_of_the_house": bool(row.get("loss_of_the_house")),
    }
    st["next_id"] += 1
    st["stains"].append(stain)
    if stain["loss_of_the_house"]:
        st["loss_of_house_required"] = True
    _set(c, "virtue", max(0, _int(c, "virtue", 0) - stain["weight"]))
    _clip_virtue(c)
    if stain["grade"] == "grave" and stain["corruption"]:
        _set(c, "corruption_level", _int(c, "corruption_level", 0) + stain["corruption"])
    st["last_rule_kept"] = False
    st["pending_felt"] = None
    return stain


def felt_line(c):
    """One player-facing line. No numbers."""
    cfg = data()["felt"]
    st = state(c)
    if st.get("pending_felt"):
        return st["pending_felt"]
    graves = open_stains(c, "grave")
    if any(s.get("loss_of_the_house") and st["house_status"] == "in_house" for s in graves):
        if any(not s.get("confessed") for s in graves):
            return cfg["grave_stain"]
        return cfg["house_lost"]
    if any(not s.get("confessed") for s in graves):
        return cfg["grave_stain"]
    if broken_vow_open(c):
        return cfg["vow_broken"]
    if any(s.get("confessed") and not s.get("penance_done") for s in graves):
        return cfg["confessed_unfinished"]
    if open_stains(c, "venial"):
        return cfg["venial_stain"]
    if st.get("rule_ward", 0) > 0:
        return cfg["ward_up"]
    return ""


def _reset_week_if_needed(st, cfg):
    if st["week_started_on"] == 0:
        st["week_started_on"] = st["day"] or 1
        st["devotion_week"]["started_on"] = st["week_started_on"]
        return
    if st["day"] - st["week_started_on"] >= 7:
        st["week_started_on"] = st["day"]
        st["week_cleanse_used"] = 0
        st["week_cleanse_days"] = 0
        st["devotion_week"] = {"gained": 0, "started_on": st["day"], "confession_day": None, "fasting_day": None}


def _cleanse_venial(c, st, cfg):
    cleanse_cfg = cfg["daily_cleansing"]
    if st["week_cleanse_used"] >= int(cleanse_cfg["weekly_max"]):
        return 0
    if st["week_cleanse_days"] < int(cleanse_cfg["first_days"]):
        budget = int(cleanse_cfg["points_first_days"])
    else:
        budget = int(cleanse_cfg["points_after"])
    budget = min(budget, int(cleanse_cfg["weekly_max"]) - st["week_cleanse_used"])
    removed = 0
    for s in list(open_stains(c, "venial")):
        if budget <= 0:
            break
        take = min(int(s["weight"]), budget)
        s["weight"] -= take
        budget -= take
        removed += take
        if s["weight"] <= 0:
            s["open"] = False
            s["penance_done"] = True
    if removed:
        st["week_cleanse_used"] += removed
        st["week_cleanse_days"] += 1
    return removed


def _weekly_rot(c, st, cfg):
    added = 0
    per = int(cfg["stain"]["weekly_unconfessed_corruption"])
    for s in open_stains(c, "grave"):
        if s.get("confessed"):
            continue
        s["unconfessed_days"] = int(s.get("unconfessed_days") or 0) + 1
        if s["unconfessed_days"] % 7 == 0:
            _set(c, "corruption_level", _int(c, "corruption_level", 0) + per)
            added += per
    return added


def _advance_penance_days(c, st):
    """A day of living the Rule counts toward an already-accepted penance."""
    done = []
    for s in open_stains(c, "grave"):
        if s.get("confessed") and s.get("restitution") and not s.get("penance_done") and int(s.get("penance_remaining") or 0) > 0:
            s["penance_remaining"] -= 1
            if s["penance_remaining"] <= 0:
                # house-loss sins still need the house to be given up
                if s.get("loss_of_the_house") and st["house_status"] == "in_house":
                    s["penance_remaining"] = 0
                    continue
                _lift_stain(c, s)
                done.append(s["id"])
    return done


def _lift_stain(c, s):
    s["open"] = False
    s["penance_done"] = True
    s["penance_remaining"] = 0
    state(c)["pending_felt"] = data()["felt"]["stain_lifted"]
    _clip_virtue(c)


def day_tick(c, rule_kept=None):
    """One day under the Rule. No-op for characters who do not keep it.

    rule_kept: True/False, or None to infer (broken if a stain was recorded today or
    last_rule_kept is False).
    """
    if not under_the_rule(c):
        return {}
    cfg = data()
    st = state(c)
    st["day"] = int(st.get("day") or 0) + 1
    st["pending_felt"] = None
    _reset_week_if_needed(st, cfg)

    if rule_kept is None:
        # Sins recorded since the previous tick carry that day's number (before this increment).
        prev = st["day"] - 1
        rule_kept = not any(s.get("day") == prev for s in st["stains"])

    piety_tbl = cfg["piety"]
    piety = _int(c, "piety", 0)
    if rule_kept:
        piety = min(int(piety_tbl["rule_alone_cap"]), piety + int(piety_tbl["gain_table"]["rule_kept"]))
        st["rule_kept_streak"] = int(st.get("rule_kept_streak") or 0) + 1
        st["rule_ward"] = min(int(cfg["rule_ward"]["max"]), int(st.get("rule_ward") or 0) + int(cfg["rule_ward"]["gain_per_kept_day"]))
        rec = int(cfg["virtue"]["recover_per_kept_day"])
        _set(c, "virtue", min(virtue_ceiling(c), _int(c, "virtue", 0) + rec))
        if cfg["daily_cleansing"].get("only_when_rule_kept", True):
            cleansed = _cleanse_venial(c, st, cfg)
        else:
            cleansed = 0
        lifted = _advance_penance_days(c, st)
    else:
        piety = max(int(piety_tbl["absolute_min"]), piety + int(piety_tbl["gain_table"]["rule_broken"]))
        st["rule_kept_streak"] = 0
        st["rule_ward"] = int(cfg["rule_ward"]["on_broken_day"])
        cleansed = 0
        lifted = []
    piety = max(int(piety_tbl["absolute_min"]), min(int(piety_tbl["absolute_max"]), piety))
    # The Rule alone cannot push piety above rule_alone_cap.
    if piety > int(piety_tbl["rule_alone_cap"]):
        piety = int(piety_tbl["rule_alone_cap"])
    _set(c, "piety", piety)
    st["last_rule_kept"] = bool(rule_kept)
    rot = _weekly_rot(c, st, cfg)
    _clip_virtue(c)
    return {
        "day": st["day"],
        "rule_kept": bool(rule_kept),
        "piety": piety,
        "virtue": _int(c, "virtue", 0),
        "virtue_ceiling": virtue_ceiling(c),
        "rule_ward": st["rule_ward"],
        "cleansed": cleansed,
        "weekly_rot": rot,
        "penance_lifted": lifted,
        "felt": felt_line(c),
    }


def confess_to_god(c):
    """Private prayer. Never lifts a grave stain, never starts penance."""
    if open_stains(c, "grave"):
        return {"ok": False, "felt": data()["felt"]["grave_stain"]}
    return {"ok": True, "felt": felt_line(c)}


def confess_to_priest(c, stain_id=None):
    """Names the stain. Does not lift it. Required before restitution and penance."""
    graves = open_stains(c, "grave")
    if stain_id:
        graves = [s for s in graves if s["id"] == stain_id]
    if not graves:
        return {"ok": False, "felt": felt_line(c)}
    for s in graves:
        s["confessed"] = True
    # confession may grant Virtue, capped by the ceiling and the weekly devotion cap
    apply_virtue_gain(c, "confession")
    return {"ok": True, "felt": felt_line(c)}


def make_restitution(c, stain_id=None):
    stains = [s for s in open_stains(c, "grave") if s.get("confessed")]
    if stain_id:
        stains = [s for s in stains if s["id"] == stain_id]
    if not stains:
        return {"ok": False, "felt": felt_line(c)}
    for s in stains:
        s["restitution"] = True
    return {"ok": True, "felt": felt_line(c)}


def serve_penance_day(c, stain_id=None):
    """One day of accepted penance (priest already heard the confession, restitution done)."""
    st = state(c)
    stains = [s for s in open_stains(c, "grave") if s.get("confessed") and s.get("restitution") and not s.get("penance_done")]
    if stain_id:
        stains = [s for s in stains if s["id"] == stain_id]
    if not stains:
        return {"ok": False, "felt": felt_line(c)}
    lifted = []
    for s in stains:
        s["penance_remaining"] = max(0, int(s.get("penance_remaining") or 0) - 1)
        if s["penance_remaining"] <= 0:
            if s.get("loss_of_the_house") and st["house_status"] == "in_house":
                continue
            _lift_stain(c, s)
            lifted.append(s["id"])
    return {"ok": True, "lifted": lifted, "felt": felt_line(c)}


def complete_penance(c, stain_id=None):
    """Finish remaining penance days in one call (tests / when the days have been served)."""
    st = state(c)
    stains = [s for s in open_stains(c, "grave") if s.get("confessed") and s.get("restitution") and not s.get("penance_done")]
    if stain_id:
        stains = [s for s in stains if s["id"] == stain_id]
    for s in stains:
        s["penance_remaining"] = 0
        if s.get("loss_of_the_house") and st["house_status"] == "in_house":
            continue
        _lift_stain(c, s)
    return {"ok": True, "open_grave_weight": open_grave_weight(c), "felt": felt_line(c)}


def loss_of_the_house(c, choice="penitent_brother"):
    """Decision 5. Expulsion, or becoming a Penitent Brother. Required to lift murder / fleeing the banner."""
    st = state(c)
    try:
        import order_paths
    except Exception:
        order_paths = None
    if choice == "expulsion":
        if order_paths:
            result = order_paths.fall(c, 4)
        else:
            result = {"path": None, "result": "expelled: Fallen Knight"}
        st["house_status"] = "expelled"
    else:
        if order_paths:
            result = order_paths.fall(c, 2)
        else:
            result = {"path": "penitent_brother", "result": "penitent"}
        st["house_status"] = "penitent_brother"
        _set(c, "class_name", _class_name(c) or "Crusader_Knight")
    st["loss_of_house_required"] = False
    # house-loss stains whose penance has already been served can now lift
    for s in list(open_stains(c, "grave")):
        if s.get("loss_of_the_house") and s.get("confessed") and s.get("restitution") and int(s.get("penance_remaining") or 0) <= 0:
            _lift_stain(c, s)
    return {"ok": True, "house_status": st["house_status"], "path": result, "felt": felt_line(c)}


def _devotion_week(st, cfg, day):
    week = st["devotion_week"]
    started = int(week.get("started_on") or 0)
    if started and day - started >= 7:
        st["devotion_week"] = {"gained": 0, "started_on": day, "confession_day": None, "fasting_day": None}
        week = st["devotion_week"]
    if not week.get("started_on"):
        week["started_on"] = day or 1
    return week


def apply_virtue_gain(c, event):
    """Apply a virtue gain event, honouring the ceiling, halved repeats, and C5 devotion caps."""
    cfg = data()
    virtue_rules_gain = None
    try:
        with open(os.path.join(ROOT, "rules", "virtue_rules.json"), encoding="utf-8-sig") as f:
            virtue_rules_gain = json.load(f)["virtue"]["gain_events"]
    except Exception:
        virtue_rules_gain = {}
    devotion = cfg["virtue"]["devotion"]
    amount = int(virtue_rules_gain.get(event) or 0)
    if event == "confession":
        amount = int(devotion["confession_virtue"])
    elif event == "fasting_day":
        amount = int(devotion["fasting_day_virtue"])
    if amount <= 0:
        return 0

    st = state(c)
    day = int(st.get("day") or 0)
    log = st["virtue_gain_log"]
    if cfg["virtue"].get("repeat_gains_halve") and event in log:
        # each repeat halves, min 1 until it would be 0 from caps
        times = int(log[event].get("times") or 0)
        if times > 0:
            amount = max(1, amount // (2 ** times))

    if event in ("confession", "fasting_day"):
        week = _devotion_week(st, cfg, day)
        key_day = "confession_day" if event == "confession" else "fasting_day"
        cooldown = int(devotion["confession_cooldown_days"] if event == "confession" else devotion["fasting_cooldown_days"])
        last = week.get(key_day)
        if last is not None and day - int(last) < cooldown:
            return 0
        remaining = int(devotion["weekly_devotion_cap"]) - int(week.get("gained") or 0)
        if remaining <= 0:
            return 0
        amount = min(amount, remaining)
        week["gained"] = int(week.get("gained") or 0) + amount
        week[key_day] = day

    before = _int(c, "virtue", 0)
    _set(c, "virtue", min(virtue_ceiling(c), before + amount))
    applied = _int(c, "virtue", 0) - before
    entry = log.setdefault(event, {"times": 0, "last_day": 0})
    if applied:
        entry["times"] = int(entry.get("times") or 0) + 1
        entry["last_day"] = day
    return applied


def apply_incoming_veil_corruption(c, amount):
    """Rule Ward reduces incoming Veil corruption (PLACEHOLDER: 1 per Ward point)."""
    amount = max(0, int(amount))
    ward = int(state(c).get("rule_ward") or 0)
    taken = max(0, amount - ward)
    if taken:
        _set(c, "corruption_level", _int(c, "corruption_level", 0) + taken)
    return taken


def saint_relic_purge(c):
    """Rare cure kept from magic_rules.purge_methods.saint_relic. Does not lift stains by itself."""
    with open(os.path.join(ROOT, "rules", "magic_rules.json"), encoding="utf-8-sig") as f:
        methods = json.load(f)["corruption"]["purge_methods"]
    if "breath_ritual" in methods:
        raise RuntimeError("breath_ritual purge must be removed")
    relic = methods["saint_relic"]
    reduce = int(relic["reduce_corruption"])
    before = _int(c, "corruption_level", 0)
    _set(c, "corruption_level", max(0, before - reduce))
    return before - _int(c, "corruption_level", 0)
