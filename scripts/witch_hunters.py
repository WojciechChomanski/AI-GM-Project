"""The Mercy of Ash: hidden witch-hunter toolkit (Python backend only).

Hunters are ordinary trained men. They use no magic and no Witch-Sight.
Suspicion, Protection, Political Cost, Church favour, Zeal, Greed, writs and
sentences never go on a Foundry actor. All numbers are placeholders.
"""
from __future__ import annotations

import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = None

VALID_BREATH_KINDS = frozenset({
    "veilspawn", "abomination", "corrupted_beast", "demon", "ghost", "spirit",
    "possessed_human",
})
NEVER_BREATH_KINDS = frozenset({
    "ordinary_sinner", "sorceress", "witch", "human",
})


def data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(ROOT, "rules", "witch_hunters.json"), encoding="utf-8") as f:
            _DATA = json.load(f)
    return _DATA


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


def state(obj):
    """Hidden hunter toolkit on a character or hunter NPC. Never a Foundry field."""
    s = _get(obj, "witch_hunters")
    if s is None:
        s = {
            "suspicion": {},          # region -> 0-100
            "protection": 0,
            "patron": None,
            "church_favour": 50,
            "writs": {},              # id -> record
            "tithe": None,            # {region, percent, paid, days_unpaid}
            "sentence": None,
            "zeal": None,
            "greed": None,
            "rank": None,
            "enemies": [],
        }
        _set(obj, "witch_hunters", s)
    s.setdefault("suspicion", {})
    s.setdefault("protection", 0)
    s.setdefault("church_favour", 50)
    s.setdefault("writs", {})
    s.setdefault("enemies", [])
    return s


def ranks():
    return {r["id"]: r for r in data()["ranks"]}


def rank_of(hunter):
    rid = _get(state(hunter), "rank") or _get(hunter, "hunter_rank")
    return ranks().get(rid)


def authority_of(hunter):
    if _get(hunter, "sealed_writ_target"):
        return 3
    r = rank_of(hunter)
    if r:
        return int(r["authority"])
    return _int(hunter, "authority", 0)


def skill_value(person, skill):
    """NPC rank skills first, then a skills map, then a stat fallback."""
    r = rank_of(person)
    if r and skill in r.get("skills", {}):
        return int(r["skills"][skill])
    skills = _get(person, "skills") or {}
    if isinstance(skills, dict) and skill in skills:
        return int(skills[skill])
    # alias deceive / deception
    if skill in ("deceive", "deception"):
        if isinstance(skills, dict):
            if "deception" in skills:
                return int(skills["deception"])
            if "deceive" in skills:
                return int(skills["deceive"])
        r = rank_of(person)
        if r and "deception" in r.get("skills", {}):
            return int(r["skills"]["deception"])
        return _int(person, "willpower", 30)
    if skill == "inspect":
        return _int(person, "perception", 30)
    if skill == "interrogate":
        return (_int(person, "perception", 30) + _int(person, "willpower", 30)) // 2
    return 0


# --- Breath targets -----------------------------------------------------------

def target_kind(target):
    if target is None:
        return None
    for key in ("breath_kind", "kind", "creature_kind", "category"):
        v = _get(target, key)
        if v:
            return str(v).lower()
    tags = _get(target, "tags") or []
    for t in tags:
        tl = str(t).lower()
        if tl in VALID_BREATH_KINDS or tl in NEVER_BREATH_KINDS:
            return tl
    if _get(target, "is_possessed") or _get(target, "possessed"):
        return "possessed_human"
    return None


def breath_may_trigger(target):
    """Passive Breath may answer only vs corrupted beasts, demons, ghosts, spirits, possessed humans.

    Never against ordinary sinners or an un-possessed sorceress.
    """
    kind = target_kind(target)
    if kind in VALID_BREATH_KINDS:
        return True
    return False


def judgment_may_trigger(target):
    """The Judgment passive uses the same target list as Breath (no 'confirmed major sinner')."""
    return breath_may_trigger(target)


# --- Suspicion ----------------------------------------------------------------

def suspicion(obj, region):
    return int(state(obj)["suspicion"].get(region, 0))


def set_suspicion(obj, region, value):
    value = max(0, min(100, int(value)))
    tithe = state(obj).get("tithe") or {}
    if tithe.get("region") == region and tithe.get("paid"):
        value = min(value, int(data()["writs"]["tolerance_tithe"]["caps_suspicion_at"]))
    state(obj)["suspicion"][region] = value
    return value


def adjust_suspicion(obj, region, delta):
    return set_suspicion(obj, region, suspicion(obj, region) + int(delta))


def apply_event(obj, region, event):
    """Apply a named suspicion modifier from the rules. Unknown events raise KeyError."""
    mods = data()["suspicion"]["modifiers"]
    if event not in mods:
        raise KeyError(event)
    return adjust_suspicion(obj, region, mods[event])


def suspicion_threshold(obj, region):
    """Highest GM-prompt threshold reached, or None. Never an automatic outcome."""
    score = suspicion(obj, region)
    hit = None
    for row in data()["suspicion"]["thresholds"]:
        if score >= int(row["score"]):
            hit = dict(row)
            hit["score_now"] = score
    return hit


def enter_region(obj, new_region, from_region=None):
    """New regions start at 0, or 10 if she already has a bounty elsewhere (placeholder)."""
    if suspicion(obj, new_region):
        return suspicion(obj, new_region)
    start = 0
    if from_region and suspicion(obj, from_region) >= 60:
        start = 10
    else:
        for r, sc in state(obj)["suspicion"].items():
            if r != new_region and sc >= 60:
                start = 10
                break
    return set_suspicion(obj, new_region, start)


# --- Protection, authority, political cost ------------------------------------

def set_protection(obj, level, patron=None):
    level = max(0, min(3, int(level)))
    s = state(obj)
    s["protection"] = level
    if patron is not None:
        s["patron"] = patron
    return level


def can_act_freely(hunter, target, writ=None):
    """True when Authority >= Protection, or a Sealed Writ names this target."""
    if writ == "sealed_writ" or _covers(hunter, target, writ):
        return True
    return authority_of(hunter) >= _int(state(target), "protection", 0)


def _covers(hunter, target, writ):
    if writ == "sealed_writ":
        return True
    rec = (state(hunter).get("writs") or {}).get("sealed_writ") or {}
    name = _get(target, "name")
    return rec.get("target") and name and rec.get("target") == name


def political_cost(hunter, target, writ=None):
    """Apply Church-favour loss, patron enmity and a scapegoat prompt when they overreach."""
    prot = _int(state(target), "protection", 0)
    if prot <= 0:
        return {"applied": False, "church_favour": state(hunter)["church_favour"]}
    rules = data()["political_cost"]
    # A Sealed Writ lets them act, waives the Church-favour hit, and may still make a patron an enemy.
    if (writ == "sealed_writ" or _covers(hunter, target, writ)) and rules.get("sealed_writ_waives_church_favour"):
        # Patron may still become an enemy if the king was not the patron.
        patron = state(target).get("patron")
        out = {"applied": True, "church_favour_delta": 0, "waived": "church_favour",
               "patron_enmity": bool(patron)}
        if patron:
            enemies = state(hunter)["enemies"]
            if patron not in enemies:
                enemies.append(patron)
        return out
    if can_act_freely(hunter, target, writ):
        return {"applied": False, "church_favour": state(hunter)["church_favour"]}
    delta = int(rules["church_favour_per_protection_level"]) * prot
    s = state(hunter)
    s["church_favour"] = max(0, min(100, s["church_favour"] + delta))
    patron = state(target).get("patron")
    if patron and patron not in s["enemies"]:
        s["enemies"].append(patron)
    out = {
        "applied": True,
        "church_favour_delta": delta,
        "church_favour": s["church_favour"],
        "patron_enmity": bool(patron),
        "scapegoat": s["church_favour"] <= int(rules["scapegoat_if_church_favour_at_or_below"]),
    }
    return out


# --- Writs and the Tolerance Tithe -------------------------------------------

def grant_writ(holder, kind, **extra):
    if kind not in data()["writs"]:
        raise KeyError(kind)
    rec = {"kind": kind, **extra}
    state(holder)["writs"][kind] = rec
    return rec


def start_tithe(obj, region, percent):
    lo = int(data()["writs"]["tolerance_tithe"]["income_share"]["min"])
    hi = int(data()["writs"]["tolerance_tithe"]["income_share"]["max"])
    percent = max(lo, min(hi, int(percent)))
    state(obj)["tithe"] = {"region": region, "percent": percent, "paid": True, "days_unpaid": 0}
    # Paying caps current suspicion in that region.
    if suspicion(obj, region) > int(data()["writs"]["tolerance_tithe"]["caps_suspicion_at"]):
        set_suspicion(obj, region, int(data()["writs"]["tolerance_tithe"]["caps_suspicion_at"]))
    return state(obj)["tithe"]


def pay_tithe(obj):
    t = state(obj).get("tithe")
    if not t:
        return None
    t["paid"] = True
    t["days_unpaid"] = 0
    cap = int(data()["writs"]["tolerance_tithe"]["caps_suspicion_at"])
    if suspicion(obj, t["region"]) > cap:
        set_suspicion(obj, t["region"], cap)
    return t


def miss_tithe(obj):
    """Mark the tithe unpaid and jump Suspicion to 60 in that region."""
    t = state(obj).get("tithe")
    if not t:
        return None
    t["paid"] = False
    jump = int(data()["writs"]["tolerance_tithe"]["unpaid_sets_suspicion_to"])
    if suspicion(obj, t["region"]) < jump:
        set_suspicion(obj, t["region"], jump)
    return t


def day_tick(obj):
    """Count unpaid tithe days; after the grace period the tithe lapses to Suspicion 60."""
    t = state(obj).get("tithe")
    if not t:
        return {}
    if t.get("paid"):
        t["days_unpaid"] = 0
        return {}
    t["days_unpaid"] = int(t.get("days_unpaid") or 0) + 1
    grace = int(data()["writs"]["tolerance_tithe"]["grace_days"])
    if t["days_unpaid"] >= grace:
        miss_tithe(obj)
        return {"tithe_lapsed": True, "region": t["region"], "suspicion": suspicion(obj, t["region"])}
    return {"days_unpaid": t["days_unpaid"]}


def quiet_month(obj, region):
    return apply_event(obj, region, "quiet_month")


# --- Zeal, Greed, bribes ------------------------------------------------------

def set_nature(hunter, zeal, greed):
    s = state(hunter)
    s["zeal"] = max(0, min(100, int(zeal)))
    s["greed"] = max(0, min(100, int(greed)))
    return s["zeal"], s["greed"]


def is_corrupt(hunter):
    return _int(state(hunter), "greed") >= int(data()["hunter_nature"]["corrupt_at_greed"])


def is_fanatic(hunter):
    return _int(state(hunter), "zeal") >= int(data()["hunter_nature"]["fanatic_at_zeal"])


def consider_bribe(hunter, offer_gold, region=None, target=None):
    """Placeholder: accept if (Greed + min(40, gold//5)) >= Zeal. Fanatics never take it."""
    zeal = _int(state(hunter), "zeal")
    greed = _int(state(hunter), "greed")
    bonus = min(40, int(offer_gold) // 5)
    effective_zeal = zeal - 20 if is_corrupt(hunter) and not is_fanatic(hunter) else zeal
    if is_fanatic(hunter):
        if target is not None and region is not None:
            apply_event(target, region, "failed_bribe")
        return {"accepted": False, "reason": "fanatic", "reported": True,
                "suspicion": suspicion(target, region) if target is not None and region else None}
    if greed + bonus >= effective_zeal:
        if target is not None and region is not None:
            apply_event(target, region, "accepted_bribe")
        return {"accepted": True, "reason": "corrupt" if is_corrupt(hunter) else "bought",
                "effective_zeal": effective_zeal, "bonus": bonus}
    # Non-corrupt hunters who refuse still report the offer.
    reported = not is_corrupt(hunter)
    if reported and target is not None and region is not None:
        apply_event(target, region, "failed_bribe")
    return {"accepted": False, "reason": "too_little", "reported": reported,
            "effective_zeal": effective_zeal, "bonus": bonus}


# --- Inspect, exams, Interrogate ---------------------------------------------

def _d100(rng):
    rng = rng or random
    return rng.randint(1, 100)


def inspect_marks(hunter, target, *, glance=True, stripping=False, pricking=False, rng=None):
    """Mundane detection of corruption marks and sigil scars. No Witch-Sight."""
    found = []
    automatic = []
    corr = _int(target, "corruption_level")
    if corr >= 90:
        found.append({"what": "corruption", "band": 90, "how": "automatic"})
        automatic.append("corruption_90")
    elif corr >= 75:
        if stripping:
            found.append({"what": "corruption", "band": 75, "how": "stripping_exam"})
            automatic.append("corruption_75_close")
        else:
            mod = -20 if _get(target, "marks_concealed") else 0
            if skill_value(hunter, "inspect") + mod + _d100(rng) >= 100:
                found.append({"what": "corruption", "band": 75, "how": "inspect", "modifier": mod})
    elif corr >= 50:
        if stripping:
            found.append({"what": "corruption", "band": 50, "how": "stripping_exam"})
            automatic.append("corruption_50")
        # otherwise hunters cannot detect it
    # lower bands are invisible to hunters

    sigils = _get(target, "visible_sigils") or _get(target, "sigils") or []
    if isinstance(sigils, dict):
        # {school: points} or {school: tier name}
        rows = []
        for school, val in sigils.items():
            rows.append({"school": school, "tier": val if isinstance(val, str) else _sigil_tier(val)})
        sigils = rows
    for row in sigils:
        if isinstance(row, str):
            row = {"tier": row}
        tier = str(row.get("tier") or row.get("name") or "")
        school = row.get("school")
        key = tier if tier in ("I", "II", "III", "Branded") else _sigil_tier(row.get("points"))
        if key == "Branded":
            named = skill_value(hunter, "lore_witchcraft") >= 40
            found.append({"what": "sigil", "tier": "Branded", "school": school if named else None,
                          "how": "automatic", "school_named": named})
            automatic.append("branded")
        elif key == "III":
            if stripping:
                found.append({"what": "sigil", "tier": "III", "school": school, "how": "stripping_exam"})
            else:
                mod = -20 if _get(target, "sigil_concealed") else 0
                if skill_value(hunter, "inspect") + mod + _d100(rng) >= 100:
                    found.append({"what": "sigil", "tier": "III", "school": school, "how": "inspect", "modifier": mod})
        elif key == "II":
            if stripping:
                found.append({"what": "sigil", "tier": "II", "school": school, "how": "stripping_exam"})
            elif skill_value(hunter, "inspect") - 15 + _d100(rng) >= 100:
                found.append({"what": "sigil", "tier": "II", "school": school, "how": "inspect", "modifier": -15})
        elif key == "I":
            if stripping or pricking:
                found.append({"what": "sigil", "tier": "I", "school": school,
                              "how": "stripping_exam" if stripping else "pricking"})
            elif glance and skill_value(hunter, "inspect") - 30 + _d100(rng) >= 100:
                found.append({"what": "sigil", "tier": "I", "school": school, "how": "inspect", "modifier": -30})
    return {"found": found, "automatic": automatic, "magic_used": False}


def _sigil_tier(points):
    try:
        pts = int(points)
    except (TypeError, ValueError):
        return None
    if pts >= 25:
        return "Branded"
    if pts >= 15:
        return "III"
    if pts >= 8:
        return "II"
    if pts >= 3:
        return "I"
    return None


def mundane_test(kind, hunter, target, rng=None):
    """Pricking, salt, cold water or heat. May look damning. Never proves magic."""
    kind = kind.replace(" ", "_").replace("-", "_")
    if kind not in {"pricking", "salt", "cold_water", "heat"}:
        raise KeyError(kind)
    roll = _d100(rng)
    actually_marked = bool(inspect_marks(hunter, target, glance=False, stripping=True, pricking=True, rng=rng)["found"])
    # Suggestive on a low roll even when she is clean: false confidence, GM prompt only.
    suggestive = (roll <= 15 and not actually_marked) or (actually_marked and roll <= 80)
    if kind == "salt" and (breath_may_trigger(target) or _int(target, "corruption_level") >= 50 or actually_marked):
        suggestive = True
        note = data()["methods"]["salt_note"]
    else:
        note = data()["methods"]["false_positives"]
    return {
        "kind": kind,
        "suggestive": suggestive,
        "proves_magic": False,
        "prompt_only": True,
        "note": note,
        "roll": roll,
    }


def interrogate(questioner, target, rng=None):
    """Mundane Interrogate (replaces Discern Sin). Reads guilt, not magic. No costs."""
    q = _int(questioner, "perception", 30) + _int(questioner, "willpower", 30) + _d100(rng)
    abilities = _get(questioner, "abilities") or {}
    if "Divine_Clarity" in abilities or _get(questioner, "divine_clarity"):
        q += 10
        clarity = True
    else:
        clarity = False
    deceive = skill_value(target, "deceive")
    will = _int(target, "willpower", 30)
    d = max(will, deceive) + _d100(rng)
    success = q > d  # tie goes to the defender
    return {
        "success": success,
        "reads": "guilt" if success else "composed",
        "proves_magic": False,
        "costs": {"stamina": 0, "piety": 0},
        "divine_clarity": clarity,
        "totals": {"questioner": q, "defender": d},
        "tie_goes_to": "defender",
    }


# --- Sentences ----------------------------------------------------------------

SENTENCE_IDS = ("fine_ransom", "service", "confinement", "torture", "sale", "execution")


def default_lean(hunter, target, *, writ=None, evidence="weak"):
    """Helper only. The GM still chooses the sentence."""
    if writ == "sealed_writ":
        return "execution"
    if is_fanatic(hunter) and evidence == "confirmed":
        return "execution"
    if is_fanatic(hunter):
        return "torture"
    if is_corrupt(hunter):
        return "fine_ransom"
    prot = _int(state(target), "protection", 0)
    if evidence == "weak":
        return "confinement" if prot <= 1 else "fine_ransom"
    if evidence == "confirmed" and prot == 0:
        return "execution"
    if prot >= 2:
        return "service"
    return "service"


def final_verdict(judge, target, sentence, *, writ=None, evidence="confirmed", variant=None, rng=None):
    """Legal authority to sentence. Does not instant-kill or spend stamina/piety."""
    if sentence not in SENTENCE_IDS:
        raise KeyError(sentence)
    rec = {
        "ok": True,
        "instant_kill": False,
        "stamina": 0,
        "piety": 0,
        "sentence": sentence,
        "variant": variant,
        "legal": True,
        "requires": "legal finding (evidence, confession or exam), not a magical reading",
        "breath_triggers": breath_may_trigger(target),
        "lean_was": default_lean(judge, target, writ=writ, evidence=evidence),
    }
    state(target)["sentence"] = {"id": sentence, "variant": variant, "by": _get(judge, "name")}
    return rec


def apply_sentence(target, sentence, *, variant=None, rng=None):
    """Carry out a mundane sentence. Execution is ordinary death, not a holy instant kill."""
    rng = rng or random
    rec = {"sentence": sentence, "variant": variant}
    if sentence == "fine_ransom":
        prot = _int(state(target), "protection", 0)
        rec["gold"] = 50 * (prot + 1)
    elif sentence == "service":
        rec["days"] = int(data()["sentences"]["menu"][1]["days"])
        rec["status"] = "in_service"
    elif sentence == "confinement":
        rec["status"] = variant or "confinement"
        if variant == "branding":
            rec["branded"] = True
            _set(target, "branded_by_hunters", True)
        elif variant == "mutilation":
            rec["mutilated"] = True
            _set(target, "mutilated_caster", True)
    elif sentence == "torture":
        hp = rng.randint(1, 10)
        rec["hp_lost"] = hp
        rec["stress"] = 5
        rec["willpower_penalty"] = -10
        rec["willpower_penalty_per"] = "session"
        _set_hp(target, _hp(target) - hp)
        _set(target, "stress_level", _int(target, "stress_level") + 5)
        s = state(target)
        s["willpower_penalty"] = s.get("willpower_penalty", 0) - 10
        s["willpower_penalty_sessions"] = s.get("willpower_penalty_sessions", 0) + 1
    elif sentence == "sale":
        rec["status"] = "sold"
        rec["leaves_play"] = True
        _set(target, "sold_into_service", True)
    elif sentence == "execution":
        rec["status"] = "executed"
        rec["instant_kill_power"] = False
        rec["means"] = "ordinary execution after sentence"
        _set_hp(target, 0)
        if isinstance(target, dict):
            target["alive"] = False
        else:
            try:
                target.alive = False
            except Exception:
                pass
    else:
        raise KeyError(sentence)
    return rec


def _hp(obj):
    v = _get(obj, "health")
    if v is None:
        v = _get(obj, "hp", 0)
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _set_hp(obj, value):
    value = max(0, int(value))
    if isinstance(obj, dict):
        if "health" in obj or "hp" not in obj:
            obj["health"] = value
        if "hp" in obj:
            obj["hp"] = value
    else:
        if hasattr(obj, "health"):
            obj.health = value
        if hasattr(obj, "hp"):
            obj.hp = value


# --- Felt text (optional; never the numbers) ----------------------------------

def felt_suspicion(obj, region):
    row = suspicion_threshold(obj, region)
    if not row:
        return None
    return {"topic": "hunters", "text": row["prompt"]}
