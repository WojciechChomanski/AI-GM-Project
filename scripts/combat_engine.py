import json
import random
import logging
import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import progression
import knight
import corruption
import wound_recovery as recovery
import combat_techniques as CT
from zone_hp import aimed_penalty

dotenv.load_dotenv()
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()
USERNAME = os.getenv("API_USERNAME", "admin")
PASSWORD = os.getenv("API_PASSWORD", "secret")

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != USERNAME or credentials.password != PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return credentials.username

# Path to rules
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.join(BASE_DIR, "..", "rules")

def load_json(file_path: str):
    full_path = os.path.join(RULES_DIR, file_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)

class Combatant:
    def __init__(self, data: dict):
        self.name = data["name"]
        self.race = data["race"]
        self.total_hp = data["total_hp"]
        self.hp = data["total_hp"]
        self.max_stamina = data["max_stamina"]
        self.stamina = data["max_stamina"]
        self.armor_weight = data["armor_weight"]
        self.inventory_weight = data["inventory_weight"]
        self.shield_equipped = data["shield_equipped"]
        self.weapon_equipped = data["weapon_equipped"]
        self.weapon = data["weapon"]
        self.armor = data["armor"]
        self.abilities = data.get("abilities", {})
        self.skills = data.get("skills", {})                  # ← fixed
        self.strength = data.get("strength", 35)  # d100 scale: human male start (rules/stats.json)
        self.dexterity = data.get("dexterity", 30)
        self.weapon_skill = data.get("weapon_skill", 30)
        self.ballistic_skill = data.get("ballistic_skill", 25)
        self.gender = data.get("gender")
        self.talents = data.get("talents", [])
        self.progression = data.get("progression", {})  # per-character mastery uses
        self.style = data.get("style")  # "shield" | "dual_wield" | "two_hander" | None
        self.pain = 0
        self.stress = 0
        self.armor_specs = []
        # GM-only (rules/stat_visibility.json); used for the hidden Crusader Breath
        self.class_name = data.get("class_name")
        self.virtue = data.get("virtue", 0)
        self.piety = data.get("piety", 0)
        self.corruption_level = data.get("corruption_level", 0)
        self.creature_tags = data.get("creature_tags", [])
        self.corrupted = bool(data.get("corrupted")) or "corrupted" in self.creature_tags

# ─────────────────────────────────────────────────────────────────────────────
# Armor & Combat helper functions (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def resolve_armor_spec(armors_dict, tier: str, race: str | None = None):
    tier_data = armors_dict.get(tier)
    if not tier_data: return None
    if race and race.lower().startswith('dwarf') and 'dwarven' in tier_data:
        return tier_data['dwarven']
    if race and race.lower().startswith('elf') and 'elven' in tier_data:
        return tier_data['elven']
    return tier_data.get('standard') or next(iter(tier_data.values()), None)

def equip_armor(combatant, armors):
    for tier in combatant.armor:
        spec = resolve_armor_spec(armors, tier, combatant.race)
        if spec:
            combatant.armor_specs.append(spec)
            combatant.armor_weight += spec['weight']
            combatant.stamina -= spec['stamina_penalty']

def apply_armor_absorption(base_damage: int, damage_type: str, defender) -> tuple[int, int]:
    absorbed = 0
    remaining = base_damage
    rating_key = damage_type.lower()
    for spec in defender.armor_specs:
        rating = spec.get('armor_rating', {}).get(rating_key, 0)
        if rating <= 0: continue
        take = min(rating, remaining)
        absorbed += take
        remaining -= take
        if remaining <= 0: break
    return max(remaining, 0), absorbed

def block_bonus(defender) -> float:
    bonus = 1.0
    if defender.shield_equipped:
        bonus *= 1.10
        iron = defender.abilities.get('iron_wall', {})
        bonus *= (1.0 + iron.get('block_bonus', 0.0))
    return bonus

def d100(): return random.randint(1, 100)

# ─────────────────────────────────────────────────────────────────────────────
# Combat Engine (used by frontend)
# ─────────────────────────────────────────────────────────────────────────────
def _cond_total(conds, ctype, zones=None):
    return sum(int(c.get("value", 0)) for c in conds
               if c.get("type") == ctype and (zones is None or c.get("zone") in zones))


def _consume(conds, ctype):
    """Remove one-shot ('next') conditions of a type; returns their total value."""
    total = sum(int(c.get("value", 1)) for c in conds if c.get("type") == ctype and c.get("duration") == "next")
    conds[:] = [c for c in conds if not (c.get("type") == ctype and c.get("duration") == "next")]
    return total


class CombatEngine:
    def attack_roll(self, attacker_data: dict, defender_data: dict, weapon_damage: int | None = None, rng=random):
        """One attack. Optional inputs (all stateless; the caller stores what comes back):
        attacker_data: stance (guard id or offensive/defensive/neutral), previous_stance, maneuver (name),
          trigger (always/after_parry/after_block/after_dodge), aimed_zone, damage_type, use_trick,
          fight_state {trick_used, free_changes_used, rung}, conditions [..], disarmed.
        defender_data: stance, conditions [..], shield_equipped.
        See docs/COMBAT_STANCES_MANEUVERS.md."""
        attacker = Combatant(attacker_data)
        defender = Combatant(defender_data)

        try:
            armors = load_json("armors.json")
        except Exception:
            armors = {}
        equip_armor(attacker, armors)
        equip_armor(defender, armors)

        # Ranged/thrown use Ballistic Skill; mastery adds capped to-hit/damage (scripts/progression.py).
        weapon_ref = CT.weapon_data(attacker.weapon) if attacker.weapon else {}
        # longsword: full 2H_sword guards in two hands (no shield, grip not "one_hand")
        if weapon_ref.get("two_hand_guard_set"):
            weapon_ref = CT.grip(weapon_ref, not attacker.shield_equipped and attacker_data.get("grip") != "one_hand")
        armor_wear = []
        if weapon_damage is None:
            weapon_damage = int(weapon_ref.get("base_damage", 14))
        skill = progression.attack_skill(attacker, weapon_ref)
        mastery = progression.mastery_modifiers(attacker, weapon_ref, attacker.style)
        perks = progression.perk_effects(attacker, weapon_ref)
        weapon_damage = weapon_damage + mastery["damage"]

        # A Veil-thing attacking a full-Breath knight tests morale; fail = turns to another target if one exists
        if (attacker.corrupted or set(attacker.creature_tags) & {"veilspawn", "abomination", "demon"}) \
                and defender.class_name == "Crusader_Knight" \
                and knight.breath_state(defender.virtue, defender.piety, defender.corruption_level) == "full" \
                and attacker_data.get("other_targets_available") \
                and not recovery.morale_vs_knight(attacker_data.get("willpower", 30)):
            return {"hit": False, "shied_away": True, "damage": 0, "absorbed": 0, "defender_hp": defender.hp,
                    "breath_gm_only": {"state": "full", "morale_failed": True}}

        fight = dict(attacker_data.get("fight_state") or {})
        fight.setdefault("rung", [])
        a_conds = [dict(c) for c in attacker_data.get("conditions", [])]
        d_conds = [dict(c) for c in defender_data.get("conditions", [])]
        notes = []

        # --- Trick (one per fight) -------------------------------------------
        trick = None
        want = attacker_data.get("use_trick")
        if want and perks["tricks"] and not fight.get("trick_used"):
            if want is True or want in perks["tricks"]:
                trick = perks["tricks"][0]
                fight["trick_used"] = True
        elif want:
            notes.append("trick not available (none learned, or already used this fight)")

        # --- Guards ----------------------------------------------------------
        a_guard = CT.guard_info(weapon_ref, attacker_data.get("stance"))
        d_weapon = CT.weapon_data(defender.weapon) if defender.weapon else {}
        d_guard = CT.guard_info(d_weapon, defender_data.get("stance"))
        if attacker_data.get("stance") and not a_guard["valid"]:
            notes.append(f"guard {attacker_data.get('stance')} not available to this weapon: using {a_guard['id']}")
        gmod = perks["guard_mods"].get(a_guard["id"], {})
        free_left = perks["free_guard_changes"] - int(fight.get("free_changes_used", 0))
        prev = attacker_data.get("previous_stance")
        change_cost = CT.guard_change_cost(prev, a_guard["id"], free_left, trick == "seamless_guards")
        if prev and prev != a_guard["id"] and change_cost == 0 and trick != "seamless_guards":
            fight["free_changes_used"] = int(fight.get("free_changes_used", 0)) + 1

        # --- Maneuver (ONE per action) ---------------------------------------
        aimed_zone = attacker_data.get("aimed_zone")
        defeat = CT.weapon_armor_piercing(weapon_ref, perks["armor_piercing"], trick == "crater")
        maneuver, mnote = None, "none"
        if attacker_data.get("disarmed"):
            mnote = "disarmed: no maneuver"
        elif _consume(a_conds, "lose_next_maneuver"):
            mnote = "rung/disrupted: no maneuver this action"
        elif attacker_data.get("maneuver") is not False:
            maneuver, mnote = CT.choose_maneuver(weapon_ref, a_guard["id"], attacker_data.get("trigger", "always"),
                                                 aimed_zone, perks, attacker_data.get("maneuver"),
                                                 defender.armor_specs, weapon_damage, defeat,
                                                 any_guard=(trick == "seamless_guards"))
        fx = maneuver["effects"] if maneuver else {}

        # --- Attack ------------------------------------------------------------
        aim_pen = 0
        if aimed_zone:
            relief = fx.get("aim_relief", 0) + (perks["maneuver_aim_relief"].get(maneuver["name"], 0) if maneuver else 0)
            for ar in perks["aim_relief"]:
                armoured = CT.raw_armor(defender.armor_specs, "slashing", aimed_zone) > 0
                if aimed_zone in ar["zones"] and (armoured or not ar.get("armoured_only")):
                    relief += ar["value"]
            aim_pen = aimed_penalty(aimed_zone) - min(progression.PCAPS["aim_relief"], relief)
        man_atk = fx.get("attack_bonus", 0) + (perks["maneuver_attack"].get(maneuver["name"], 0) if maneuver else 0)
        arm_pen = _cond_total(a_conds, "limb_disabled", CT.ARMS)
        roll = rng.randint(1, 100)
        atk = (roll + skill + mastery["to_hit"] + (attacker.dexterity // 10) + a_guard["attack"] + gmod.get("attack", 0)
               + man_atk - aim_pen - arm_pen - attacker.stress - attacker.pain)

        # --- Defence -------------------------------------------------------------
        def_roll = rng.randint(1, 100)
        d_bonus = min(progression.PCAPS["defense"], _consume(d_conds, "counter_defense"))
        def_score = (def_roll + (defender.dexterity // 10) + d_guard["defense"] + d_bonus
                     - _consume(d_conds, "unbalanced") - _cond_total(d_conds, "limb_disabled", CT.LEGS)
                     - defender.stress - defender.pain)
        def_type = rng.choice(["Parry", "Block", "Dodge"])
        stripped = _consume(d_conds, "shield_stripped")
        if def_type == "Block" and not fx.get("ignore_shield") and not stripped:
            def_score = int(def_score * block_bonus(defender))

        # --- Stamina -------------------------------------------------------------
        w_cost = int(weapon_ref.get("stamina_cost", 2))
        m_red = CT.maneuver_perk_reduction(maneuver, perks)
        total_red = min(progression.PCAPS["stamina_reduction"], -mastery["stamina"] + m_red)
        raw_cost = w_cost + fx.get("stamina_cost_modifier", 0) + a_guard["stamina"].get("offensive", 0) + change_cost
        stamina_spent = max(min(raw_cost, progression.PCAPS["min_stamina_per_attack"]), raw_cost - total_red)

        dtype = None
        zone = aimed_zone
        effects_applied = []
        disarmed = False
        if atk >= def_score:
            hit_type = fx.get("damage_type")
            if not zone and fx.get("target_zone"):
                zone = CT.pick_zone(defender.armor_specs, fx["target_zone"], hit_type or "slashing")
            bypass = fx.get("armor_bypass", 0)
            req = attacker_data.get("damage_type")
            choices = [hit_type] if hit_type else ([req] if req in weapon_ref.get("damage_types", []) else None)
            dtype = CT.best_damage_type(weapon_ref, defender.armor_specs, weapon_damage, zone, bypass, defeat, choices)
            raw = CT.raw_armor(defender.armor_specs, dtype, zone)
            dmg = weapon_damage + CT.type_damage_mod(dtype, raw) + fx.get("damage_bonus", 0)
            extra = sum(d["bonus"] for d in perks["damage_vs_light"] if dtype in d["types"] and raw <= d["max_armor"])
            dmg += min(extra, max(0, progression.CEIL["damage"] - mastery["damage"]))
            if attacker_data.get("disarmed"):
                dmg, dtype = 2, "blunt"
            protection = CT.effective_armor(defender.armor_specs, dtype, zone, bypass, defeat)
            absorbed = min(max(dmg, 0), protection)
            # armour durability: the caller applies it (stateless engine); x2 for armour piercing
            armor_wear = [{"armor": sp.get("name", "?"), "zone": zone,
                           "durability_loss": CT.armor_durability_loss(dmg, defeat)}
                          for sp in defender.armor_specs if CT.spec_covers(sp, zone)
                          and CT.armor_rating(sp, dtype) > 0] if absorbed > 0 else []
            effective = max(0, dmg - protection)
            breath = {"state": "none"}
            if attacker.class_name == "Crusader_Knight":
                breath = knight.breath_effects(attacker.virtue, attacker.piety, attacker.corruption_level,
                                               defender.creature_tags + (["corrupted"] if defender.corrupted else []))
            if defender.corrupted:
                # total_hp = natural HP; pool x M; Breath damage counts x M; penalties vs natural HP
                cc = corruption.CorruptedCreature(defender.total_hp, defender_data.get("hp_multiplier"),
                                                  defender_data.get("corruption_tier", "ordinary"))
                cc.effective = defender_data.get("damage_taken", 0)
                cc.breath_effective = defender_data.get("breath_damage_taken", 0)
                cc.take(effective, breath=bool(breath.get("bypass_undying")))
                defender.hp = cc.hp
                breath = dict(breath, damage_taken=cc.effective, breath_damage_taken=cc.breath_effective)
                ratio = cc.wound_ratio
            else:
                defender.hp -= effective
                ratio = effective / defender.total_hp if defender.total_hp else 0
            pain_mult = breath.get("pain_mult", 1) * CT.DAMAGE_TYPES.get(dtype, {}).get("pain_mult", 1)
            defender.pain = min(100, ratio * 120 * pain_mult) if defender.total_hp else defender.pain
            hit = True
            # --- maneuver / perk effects on a hit ---
            if fx.get("limb_disable") and effective > 0:
                lz = zone if zone in CT.ARMS | CT.LEGS else None
                if lz:
                    d_conds.append({"type": "limb_disabled", "zone": lz, "value": fx["limb_disable"], "duration": "fight"})
                    effects_applied.append(f"{lz} disabled (-{fx['limb_disable']})")
            if fx.get("disarm_chance") and CT.roll_chance(fx["disarm_chance"], rng):
                disarmed = True
                effects_applied.append("foe disarmed")
            if fx.get("target_lose_next_maneuver"):
                d_conds.append({"type": "lose_next_maneuver", "value": 1, "duration": "next"})
                effects_applied.append("foe loses next maneuver")
            foe_id = defender_data.get("name", "?")
            if perks["ring_on_head"] and dtype == "blunt" and zone == "head" and foe_id not in fight["rung"] \
                    and not fx.get("target_lose_next_maneuver"):
                fight["rung"].append(foe_id)
                d_conds.append({"type": "lose_next_maneuver", "value": 1, "duration": "next"})
                effects_applied.append("helm rung: foe loses next maneuver")
            if fx.get("target_defense_penalty_next"):
                d_conds.append({"type": "unbalanced", "value": fx["target_defense_penalty_next"], "duration": "next"})
                effects_applied.append(f"foe unbalanced (-{fx['target_defense_penalty_next']} next defence)")
            if fx.get("target_initiative_penalty_next"):
                d_conds.append({"type": "initiative", "value": -fx["target_initiative_penalty_next"], "duration": "next"})
            if fx.get("strip_shield"):
                d_conds.append({"type": "shield_stripped", "value": 1, "duration": "next"})
                effects_applied.append("shield hooked aside")
            if fx.get("counter_defense_next"):
                a_conds.append({"type": "counter_defense", "value": fx["counter_defense_next"], "duration": "next"})
        else:
            effective = absorbed = 0
            hit = False

        if not hit:
            breath = {"state": "none"}
        return {
            "breath_gm_only": breath,
            "hit": hit,
            "damage": effective,
            "absorbed": absorbed,
            "damage_type": dtype,
            "zone": zone,
            "defender_hp": defender.hp,
            "defender_pain": defender.pain,
            "attack_roll": roll,
            "atk_total": atk,
            "def_roll": def_roll,
            "def_total": def_score,
            "def_type": def_type,
            "attack_skill": skill,
            "mastery": mastery,
            "stance": a_guard["id"],
            "defender_stance": d_guard["id"],
            "guard_change_cost": change_cost,
            "maneuver": maneuver["name"] if maneuver else None,
            "maneuver_note": mnote,
            "aimed_penalty": aim_pen,
            "armor_piercing": defeat,
            "armor_wear": armor_wear,
            "trick": trick,
            "stamina_spent": stamina_spent,
            "effects": effects_applied,
            "defender_disarmed": disarmed,
            "attacker_conditions": a_conds,
            "defender_conditions": d_conds,
            "fight_state": fight,
            "notes": notes,
        }

engine = CombatEngine()

@app.post("/combat/attack")
def api_attack_roll(data: dict, username: str = Depends(verify_credentials)):
    return engine.attack_roll(
        data.get('attacker', {}),
        data.get('defender', {}),
        data.get('weapon_damage')
    )

# Simple health check
@app.get("/api/healthz")
def healthz():
    return {"status": "ok", "backend": "combat_engine"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)