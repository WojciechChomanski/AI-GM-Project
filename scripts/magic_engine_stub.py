import json, random
from dataclasses import dataclass

@dataclass
class Caster:
    name: str
    max_hp: int
    hp: int
    stamina: int
    willpower: int
    spellcraft: int
    corruption: int = 0

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

SPELLS = _load("AI_GM_Project/rules/spells.json")
MAGIC = _load("AI_GM_Project/rules/magic_rules.json")

def d100():
    return random.randint(1,100)

def cast_spell(caster: Caster, spell_id: str, context=None):
    sp = SPELLS[spell_id]
    hp_cost = sp["costs"]["health"]
    stam_cost = sp["costs"]["stamina"]
    max_hp_pay = int(caster.max_hp * (MAGIC["overdraw"]["hard_cap_pct_per_encounter"]/100))
    if hp_cost > max_hp_pay:
        hp_cost = max_hp_pay
    if caster.hp <= hp_cost or caster.stamina < stam_cost:
        return {"ok": False, "reason": "insufficient resources"}
    caster.hp -= hp_cost
    caster.stamina -= stam_cost
    roll = d100()
    skill = caster.spellcraft
    margin = roll - skill
    result = {"roll": roll, "skill": skill, "margin": margin, "id": spell_id, "name": sp["name"]}
    base_cc = sp["corruption"]["base_chance"]
    extra = sp["corruption"]["on_fail_extra"] if margin > 0 else sp["corruption"]["on_success_extra"]
    cc_total = min(0.95, base_cc + extra)
    if random.random() < cc_total:
        caster.corruption += 1
        result["corruption_tick"] = 1
    if roll >= MAGIC["casting"]["critical_hit_threshold"]:
        result["outcome"] = "critical_success"
        result["damage"] = int(sp.get("damage", 0) * 1.5)
        return result
    if roll <= MAGIC["casting"]["critical_miss_threshold"]:
        result["outcome"] = "critical_fail"
        _apply_backlash(caster, sp, "catastrophic", result)
        return result
    if margin <= -MAGIC["casting"]["success_bands"]["full"]:
        result["outcome"] = "success"
        result["damage"] = sp.get("damage", 0)
    elif margin <= -MAGIC["casting"]["success_bands"]["glancing"]:
        result["outcome"] = "glancing"
        result["damage"] = int(sp.get("damage", 0) * 0.5)
    else:
        result["outcome"] = "fail"
        band = "major" if margin > 25 else "minor"
        _apply_backlash(caster, sp, band, result)
    return result

def _apply_backlash(caster, sp, band, result):
    b = sp["backlash"]["fail_margin_scale"][band]
    caster.hp -= b.get("hp", 0)
    caster.stamina -= b.get("stamina", 0)
    result["backlash"] = {"band": band, **b}
