"""Skills (rules/skills.json, docs/SKILLS.md).

Value = floor(average of linked stats); a creation pick adds +10. Values rise only by use
(progression.uses_needed growth). XP only buys a skill you do not have. Past 50 a master must
unlock points; tools cap the usable value; trained-only skills are unusable untrained.
Each skill also has a use bar (50/150/400/900/2000 -> rank 1..5); Medicine rank feeds limb_repair.

State: character.progression['skills'] = {id: {'value', 'uses', 'bar', 'unlocked_to'}}.
"""
import json
import os

import progression as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "rules", "skills.json"), encoding="utf-8") as _f:
    DATA = json.load(_f)
R = DATA["rules"]
SKILLS = DATA["skills"]
_get, _set = P._get, P._set


def get(sid):
    return SKILLS.get(sid)


def _skills_state(c):
    return P.state(c).setdefault("skills", {})


def has(c, sid):
    return sid in _skills_state(c)


def base_value(stats, sid):
    """floor(average of linked stats). stats: dict or character."""
    names = SKILLS[sid]["stats"]
    vals = [(stats.get(n, 0) if isinstance(stats, dict) else getattr(stats, n, 0)) or 0 for n in names]
    return sum(vals) // len(vals)


def lock_error(sid, race, gender, cross_race_master=False, advantages=()):
    """None if allowed; else a reason. Race locks yield only to a found cross-race master;
    gender locks never do."""
    s = SKILLS.get(sid)
    if s is None:
        return f"unknown skill {sid}"
    r = s.get("restrictions", {})
    if r.get("gender") and gender not in r["gender"]:
        return f"{s['name']} is {'/'.join(r['gender'])} only"
    if race in s.get("forbidden_races", []):
        return f"{race} cannot learn {s['name']}"
    if r.get("race") and race not in r["race"] and not cross_race_master:
        return f"{s['name']} is {'/'.join(r['race'])} only (needs a cross-race master)"
    adv = s.get("requires_advantage")
    if adv and adv not in (advantages or ()):
        return f"{s['name']} needs the {adv} advantage"
    return None


def free_skills(class_name=None, background=None):
    out = list(DATA["class_free_skills"].get(class_name or "", []))
    for sid in DATA["background_free_skills"].get(background or "", []):
        if sid not in out:
            out.append(sid)
    return out


def creation_skills(stats, race, gender, picks=(), class_name=None, background=None, advantages=()):
    """Returns (values {id: value}, errors). Free class/background skills do not count against
    the 6 picks; every learned skill gets the +10 pick bonus."""
    errors = []
    picks = list(dict.fromkeys(picks or ()))
    free = free_skills(class_name, background)
    paid = [p for p in picks if p not in free]
    if len(paid) > R["creation_picks"]:
        errors.append(f"max {R['creation_picks']} skill picks at creation (free class/background skills not counted)")
    values = {}
    for sid in free + paid:
        err = lock_error(sid, race, gender, advantages=advantages)
        if err:
            if sid in paid or sid not in SKILLS:
                errors.append(err)
            continue  # a free skill the character cannot have is just dropped
        values[sid] = min(base_value(stats, sid) + R["pick_bonus"], R["master_gate"]["free_until"])
    return values, errors


def learn(c, sid, value=None):
    st = _skills_state(c)
    st[sid] = {"value": base_value(c, sid) if value is None else value, "uses": 0,
               "bar": st.get(sid, {}).get("bar", 0), "unlocked_to": R["master_gate"]["free_until"]}
    return st[sid]


def apply_creation(c, values):
    for sid, v in values.items():
        learn(c, sid, v)
    sync_legacy(c)


def xp_cost(sid):
    return R["xp_cost"]["trained_only" if SKILLS[sid]["trained_only"] else "common"]


def buy_with_xp(c, sid, cross_race_master=False):
    """Learn a new skill at its base value for 100 XP (200 trained-only). Never raises a value.
    Returns (ok, message)."""
    if has(c, sid):
        return False, "XP cannot raise a skill; it grows by use"
    err = lock_error(sid, _get(c, "race"), _get(c, "gender"), cross_race_master, _get(c, "advantages", []) or [])
    if err:
        return False, err
    cost, xp = xp_cost(sid), _get(c, "xp", 0) or 0
    if xp < cost:
        return False, f"needs {cost} XP (has {xp})"
    _set(c, "xp", xp - cost)
    learn(c, sid)
    sync_legacy(c)
    return True, f"learned {SKILLS[sid]['name']} for {cost} XP"


def tool_cap(sid, tools=None):
    if not SKILLS[sid].get("tools"):
        return R["skill_max"]
    return R["tool_tiers"].get(tools or "none", R["tool_tiers"]["none"])


def effective_value(c, sid, tools=None):
    """Value used for a test. None = cannot attempt (trained-only, untrained)."""
    if has(c, sid):
        return min(_skills_state(c)[sid]["value"], tool_cap(sid, tools))
    if SKILLS[sid]["trained_only"]:
        return None
    return min(int(base_value(c, sid) * R["untrained_mult"]), tool_cap(sid, tools))


def basic_bandage_value(c):
    """The one untrained exception: a basic bandage at half the Medicine base."""
    return int(base_value(c, "medicine") * R["untrained_mult"])


def growth_limit(c, sid, tools=None):
    s = _skills_state(c)[sid]
    return min(R["skill_max"], s["unlocked_to"], tool_cap(sid, tools))


def record_use(c, sid, failed=False, tools=None):
    """One use: fills the use bar; counts toward growth (failures x2) if the value may rise."""
    if not has(c, sid):
        return
    s = _skills_state(c)[sid]
    s["bar"] += 1
    if s["value"] < growth_limit(c, sid, tools):
        s["uses"] += P.G["failure_counts"] if failed else 1


def check_growth(c, tools=None):
    """+1 to each skill whose uses reached uses_needed (same formula as stats). Max 1 per session."""
    msgs, sess = [], P.state(c)["session"]
    for sid, s in _skills_state(c).items():
        key = "skill:" + sid
        if sess.get(key, 0) >= P.G["max_points_per_stat_per_session"] or s["value"] >= growth_limit(c, sid, tools):
            continue
        need = P.uses_needed(s["value"], R["skill_max"])
        if s["uses"] >= need:
            s["value"] += 1
            s["uses"] -= need
            sess[key] = sess.get(key, 0) + 1
            msgs.append(f"{_get(c, 'name', 'Character')}'s {SKILLS[sid]['name']} improved to {s['value']}!")
    sync_legacy(c)
    return msgs


def rank(c, sid):
    bar = _skills_state(c).get(sid, {}).get("bar", 0)
    return sum(1 for t in R["use_bar"]["thresholds"] if bar >= t)


def rank_name(c, sid):
    r = rank(c, sid)
    return R["use_bar"]["ranks"][r - 1] if r else "Untested"


def reputation_needed(target, cross_race=False):
    M = R["master_gate"]
    need = next((b["min"] for b in M["reputation"] if target <= b["up_to"]), M["reputation"][-1]["min"])
    return need + (R["cross_race"]["reputation_extra"] if cross_race else 0)


def is_cross_race(c, sid):
    races = SKILLS[sid].get("restrictions", {}).get("race")
    return bool(races) and _get(c, "race") not in races


def teaching_quote(c, sid, master_value):
    """What one teaching period costs and unlocks. Returns dict(ok, reason|points, target, gold, reputation)."""
    if not has(c, sid):
        return {"ok": False, "reason": "learn the skill first"}
    s, M = _skills_state(c)[sid], R["master_gate"]
    cross = is_cross_race(c, sid)
    pts = R["cross_race"]["points_per_period"] if cross else M["points_per_period"]
    target = min(s["unlocked_to"] + pts, R["skill_max"])
    if target <= s["unlocked_to"]:
        return {"ok": False, "reason": "already at the skill maximum"}
    if master_value < target + M["master_margin"] and master_value < R["skill_max"]:
        return {"ok": False, "reason": f"master must be at least {M['master_margin']} above the target ({target})"}
    gold = M["gold_per_target_point"] * target * (R["cross_race"]["gold_mult"] if cross else 1)
    return {"ok": True, "points": target - s["unlocked_to"], "target": target, "gold": gold,
            "reputation": reputation_needed(target, cross), "cross_race": cross}


ORDER_MASTER_PATHS = {"order": ("crusader_knight", "warden_of_the_marches", "penitent_brother", "order_contractor"),
                      "tribunal": ("holy_judge",)}


def teaching_reputation(c, master_of=None):
    """Reputation that counts for the master gate. With an Order or Tribunal master
    (master_of='order'|'tribunal'), the character's standing on a matching Order path counts
    if it is higher than his general reputation."""
    rep = _get(c, "reputation", 0) or 0
    order = (P.state(c).get("order") or {})
    if master_of in ORDER_MASTER_PATHS and order.get("path") in ORDER_MASTER_PATHS[master_of]:
        rep = max(rep, order.get("reputation", 0))
    return rep


def teach(c, sid, master_value, master_of=None):
    """One teaching period: pays gold from c.gold, checks reputation (Order/Tribunal standing
    counts with an Order/Tribunal master, see teaching_reputation), raises the unlock ceiling.
    The value itself still grows only by use."""
    q = teaching_quote(c, sid, master_value)
    if not q["ok"]:
        return q
    gold, rep = _get(c, "gold", 0) or 0, teaching_reputation(c, master_of)
    if rep < q["reputation"]:
        return dict(q, ok=False, reason=f"needs reputation {q['reputation']} (has {rep})")
    if gold < q["gold"]:
        return dict(q, ok=False, reason=f"needs {q['gold']} gold (has {gold})")
    _set(c, "gold", gold - q["gold"])
    _skills_state(c)[sid]["unlocked_to"] = q["target"]
    return q


# --- Medicine ---------------------------------------------------------------
def uses_skill_system(c):
    return isinstance(_get(c, "progression"), dict) and "skills" in _get(c, "progression")


def medicine_rank(c):
    """Use-bar rank if the character uses this system; else the legacy skills['medicine'] rank."""
    legacy = (_get(c, "skills", None) or {}).get("medicine", 0)
    return max(rank(c, "medicine"), legacy) if uses_skill_system(c) else legacy


def medicine_perks(c):
    out = {}
    for p in SKILLS["medicine"]["rank_perks"]:
        if p["rank"] <= medicine_rank(c):
            out.update({k: v for k, v in p.items() if k not in ("rank", "bonus")})
    return out


def sync_legacy(c):
    """Mirror Medicine rank into character.skills['medicine'] for older readers."""
    sk = _get(c, "skills", None)
    if isinstance(sk, dict) and uses_skill_system(c):
        sk["medicine"] = max(sk.get("medicine", 0), rank(c, "medicine"))


def weapon_head_start(class_skills):
    """Class-file weapon ranks (e.g. {'swordsmanship': 3}) -> {mastery_track: uses} head start."""
    W = DATA["class_weapon_skills"]
    return {W["map"][k]: W["head_start_uses"][str(min(max(int(v), 1), 5))]
            for k, v in (class_skills or {}).items() if k in W["map"] and v}


def apply_weapon_head_start(c, class_skills):
    for track, uses in weapon_head_start(class_skills).items():
        P.record_mastery(c, track, uses)
