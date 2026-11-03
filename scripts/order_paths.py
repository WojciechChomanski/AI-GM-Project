"""Order paths (rules/orders/paths.json, docs/CAREER_PATHS.md).

State: character.progression['order'] = {path, rank, reputation, sessions_at_rank, last_arc,
deeds{}, switch_backs, history[], raised_by_order, class_tier, witness, unjust_sessions_ago}.
Hidden values (virtue/piety/corruption) are read here only; the player gets felt text.
"""
import json
import os
import random

import progression as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "rules", "orders", "paths.json"), encoding="utf-8") as _f:
    DATA = json.load(_f)
R, PATHS = DATA["rules"], DATA["paths"]
_get, _set = P._get, P._set
ORDER_PATHS = set(PATHS)


def state(c):
    st = P.state(c).setdefault("order", {})
    for k, v in (("path", None), ("rank", 0), ("reputation", 0), ("sessions_at_rank", 0), ("last_arc", None),
                 ("deeds", {}), ("switch_backs", 0), ("history", []), ("raised_by_order", False),
                 ("class_tier", 1), ("witness", None), ("sessions_since_unjust", 99)):
        st.setdefault(k, v)
    return st


def path_def(pid):
    return PATHS.get(pid) or (DATA["order_contractor"] if pid == "order_contractor" else None)


def rank_def(pid, n):
    return next((r for r in path_def(pid)["ranks"] if r["rank"] == n), None)


def _hidden_ok(c, hidden):
    for k, v in (hidden or {}).items():
        if k == "corruption_max":
            if (_get(c, "corruption_level", 0) or 0) > v:
                return False
        elif (_get(c, k, 0) or 0) < v:
            return False
    return True


def _deeds_ok(st, deeds):
    for d, n in (deeds or {}).items():
        have = sum(st["deeds"].values()) if d == "any" else st["deeds"].get(d, 0)
        if have < n:
            return False
    return True


# --- events ------------------------------------------------------------------
def record_session(c):
    st = state(c)
    st["sessions_at_rank"] += 1
    st["sessions_since_unjust"] += 1


def record_deed(c, deed, n=1):
    st = state(c)
    st["deeds"][deed] = st["deeds"].get(deed, 0) + n


def add_reputation(c, n):
    st = state(c)
    st["reputation"] = max(-100, min(100, st["reputation"] + n))


# --- joining ------------------------------------------------------------------
def join(c, pid, rank=1):
    st = state(c)
    if st["path"]:
        st["history"].append({"path": st["path"], "rank": st["rank"]})
    st.update(path=pid, rank=rank, sessions_at_rank=0)
    return st


def start_at_creation(c, class_name):
    """Creation hook. Order-raised classes set raised_by_order (the only way to get it)."""
    import careers
    st = state(c)
    st["raised_by_order"] = careers.is_order_raised(class_name)
    if class_name == "Holy_Judge":
        s = PATHS["holy_judge"]["start"]
        st["class_tier"] = s["counts_as_class_tier"]
        for k, v in s["hidden_start"].items():
            _set(c, k, v)
        join(c, "holy_judge")
        return s["abilities"]
    if class_name == "Crusader_Knight":
        # Squire years are pre-game background only: play starts as a Brother-Knight.
        st["class_tier"] = PATHS["crusader_knight"]["start"]["counts_as_class_tier"]
        join(c, "crusader_knight")
    return []


def entry_errors(c, pid):
    """Backend reasons a character cannot enter a path (not shown to the player)."""
    st, p = state(c), PATHS.get(pid)
    if p is None:
        return [f"unknown path {pid}"]
    if not st["raised_by_order"]:
        return ["not raised by the Order: only order_contractor is open"]
    e, out = p.get("entry", {}), []
    if p.get("fallback"):
        return ["penitent_brother is entered only through discipline (fall())"]
    if e.get("convert_from") and st["path"] != e["convert_from"]:
        out.append(f"must convert from {e['convert_from']}")
    if st["class_tier"] < e.get("class_tier_min", 0):
        out.append(f"class tier {e['class_tier_min']}+ needed")
    if not _deeds_ok(st, e.get("deeds")):
        out.append("deeds missing")
    if not _hidden_ok(c, e.get("hidden")):
        out.append("hidden check failed")
    return out


def convert(c, pid, story_ok=True):
    """Join or change path (exclusive: the old path's rank and benefits are lost)."""
    errs = entry_errors(c, pid) + ([] if story_ok else ["story event missing"])
    if errs:
        return {"ok": False, "errors": errs, "felt": R["felt"]["not_ready"]}
    join(c, pid)
    return {"ok": True, "path": pid, "felt": R["felt"]["promoted"], "loses": PATHS[pid].get("loses", [])}


def switch_back(c):
    """Return once per character to the previous path at rank 1, -20 reputation, with a penance task."""
    st = state(c)
    if st["switch_backs"] >= R["switch_backs_per_character"] or not st["history"]:
        return {"ok": False, "errors": ["no switch-back left"]}
    prev = st["history"][-1]["path"]
    sb = R["switch_back"]
    join(c, prev, sb["to_rank"])
    st["switch_backs"] += 1
    add_reputation(c, sb["reputation"])
    return {"ok": True, "path": prev, "task": sb["task"]}


def fall(c, discipline_step):
    """Discipline ladder: steps 2-3 offer the Penitent Brother instead of expulsion; step 4 ends every path.
    Any step 2+ revokes the Paladin honour."""
    st = state(c)
    if discipline_step >= 2:
        st["honours"] = [h for h in st.get("honours", []) if h != "paladin"]
    if discipline_step >= 4:
        join(c, None, 0)
        st["raised_by_order"] = False
        return {"path": None, "result": "expelled: Fallen Knight"}
    if discipline_step in PATHS["penitent_brother"]["entry"]["from_discipline_steps"] and st["path"] != "penitent_brother":
        join(c, "penitent_brother")
        return {"path": "penitent_brother", "result": "penitent"}
    return {"path": st["path"], "result": "penance"}


def redeem(c):
    """Redeemed Penitent returns to crusader_knight rank 1 (does not use the switch-back)."""
    st = state(c)
    if st["path"] != "penitent_brother" or st["rank"] < 2:
        return False
    join(c, "crusader_knight")
    return True


# --- promotion -----------------------------------------------------------------
def can_advance(c, arc_id):
    """(ok, backend reasons, felt text). Max 1 rank per arc."""
    st = state(c)
    if not st["path"]:
        return False, ["no path"], R["felt"]["not_ready"]
    nxt = rank_def(st["path"], st["rank"] + 1)
    if nxt is None:
        return False, ["top rank"], R["felt"]["not_ready"]
    q, why = nxt["requires"], []
    if st["last_arc"] == arc_id:
        why.append("already promoted this arc")
    if st["sessions_at_rank"] < q.get("sessions_min", 0):
        why.append("sessions")
    if st["reputation"] < q.get("reputation", -100):
        why.append("reputation")
    if not _deeds_ok(st, q.get("deeds")):
        why.append("deeds")
    if st["sessions_since_unjust"] < q.get("no_unjust_sessions", 0):
        why.append("recent unjust verdict")
    hidden = not _hidden_ok(c, q.get("hidden"))
    if hidden:
        why.append("hidden")
    felt = R["felt"]["hidden_fail"] if why == ["hidden"] else R["felt"]["ready" if not why else "not_ready"]
    return not why, why, felt


def promote(c, arc_id, task_done=True, story_ok=True):
    ok, why, felt = can_advance(c, arc_id)
    st = state(c)
    nxt = rank_def(st["path"], st["rank"] + 1) if st["path"] else None
    if ok and nxt and nxt["requires"].get("task") and not task_done:
        ok, why = False, ["order task"]
    if ok and nxt and nxt["requires"].get("story") and not story_ok:
        ok, why = False, ["story"]
    if not ok:
        return {"ok": False, "why": why, "felt": felt}
    st.update(rank=st["rank"] + 1, sessions_at_rank=0, last_arc=arc_id)
    return {"ok": True, "rank": nxt["name"], "gives": nxt["gives"], "costs": nxt["costs"], "felt": R["felt"]["promoted"]}


def assign_task(c, rng=None):
    return (rng or random).choice(DATA["tasks"])


def resolve_task(c, accepted):
    if accepted:
        add_reputation(c, 5)
        return {"accepted": True}
    rt = R["refused_task"]
    add_reputation(c, rt["reputation"])
    return {"accepted": False, "discipline_step": rt["discipline_step"]}


# --- Holy Judge ----------------------------------------------------------------
BOND = PATHS["holy_judge"]["bond"]


def is_judge(c):
    return state(c)["path"] == "holy_judge"


def bond_effects(c, carrying_bonded_blade):
    """Authority only: Writ social bonus and the defiance test. No damage change, ever."""
    if not is_judge(c) or not carrying_bonded_blade or state(c).get("bond_lost"):
        return {"writ": False, "social_bonus": 0, "damage_bonus": 0}
    return {"writ": True, "social_bonus": BOND["writ_social_bonus"], "skills": BOND["writ_skills"],
            "defy_test": BOND["defy_test"], "damage_bonus": 0}


def verdict_lawful(c, weapon_id, bonded_weapon_id):
    """Final_Verdict is lawful only with the bonded blade; otherwise it is a Virtue loss event."""
    if is_judge(c) and weapon_id == bonded_weapon_id:
        return True, None
    return False, BOND["unlawful_verdict_event"]


def lose_bond(c):
    state(c)["bond_lost"] = True
    add_reputation(c, BOND["lost"]["reputation"])


def reconsecrate(c):
    state(c)["bond_lost"] = False


def record_verdict(c, just):
    """Just verdicts count as deeds; an unjust one costs hidden Piety/Virtue and reputation."""
    if just:
        record_deed(c, "verdict_just")
        return "You feel certain."
    u = PATHS["holy_judge"]["unjust_verdict"]
    for k, v in u["hidden"].items():
        _set(c, k, max(0, (_get(c, k, 0) or 0) + v))
    add_reputation(c, u["reputation"])
    state(c)["sessions_since_unjust"] = 0
    if state(c)["rank"] >= 4:
        return fall(c, 4)
    return "Doubt gnaws at you."


def name_witness(c, npc_id):
    st = state(c)
    r = rank_def("holy_judge", 3)
    if not is_judge(c) or st["rank"] < 3:
        return False
    if st["witness"] and r["witness_max"] <= 1:
        return False
    st["witness"] = npc_id
    return True


# --- Paladin honour (Crusader Knight path) -------------------------------------
PALADIN = PATHS["crusader_knight"]["honours"]["paladin"]


def can_grant_paladin(c, story_ok=True):
    st, q = state(c), PALADIN["requires"]
    why = []
    if st["path"] != "crusader_knight" or st["rank"] < PALADIN["min_rank"]:
        why.append("Crusader Knight rank 2+ needed")
    if st["sessions_at_rank"] < q["sessions_at_rank_min"]:
        why.append("sessions")
    if st["reputation"] < q["reputation"]:
        why.append("reputation")
    if not _deeds_ok(st, q["deeds"]):
        why.append("deeds")
    if not _hidden_ok(c, q["hidden"]):
        why.append("hidden")
    if not story_ok:
        why.append("story")
    return not why, why


def grant_paladin(c, story_ok=True):
    ok, why = can_grant_paladin(c, story_ok)
    if ok:
        state(c)["honours"] = sorted(set(state(c).get("honours", [])) | {"paladin"})
        return {"ok": True, "felt": PALADIN["felt"]}
    return {"ok": False, "why": why, "felt": R["felt"]["not_ready"]}


def revoke_paladin(c):
    st = state(c)
    st["honours"] = [h for h in st.get("honours", []) if h != "paladin"]


def is_paladin(c):
    return "paladin" in state(c).get("honours", [])


def paladin_passives(c):
    """Passive-only extras while his Breath is full. {} otherwise."""
    import knight
    if not is_paladin(c) or state(c)["path"] != "crusader_knight":
        return {}
    if knight.breath_state(_get(c, "virtue", 0) or 0, _get(c, "piety", 0) or 0, _get(c, "corruption_level", 0) or 0) != "full":
        return {}
    return {k: v for k, v in PALADIN["passives"].items() if k != "note"}
