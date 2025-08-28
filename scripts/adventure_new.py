#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Grimdark Village Rescue – battle loop with:
- Aimed strikes to body parts (zones) with number OR name entry
- Rules-driven aimed penalty (from combat_rules.json) without extra head penalty
- Critical hits and critical misses -> riposte
- Stamina regen/costs + durability + 2H+shield enforcement (from combat_engine_ext)
- Sorceress spell system (from sorcery_ext) including veil aura, fog/fear, shroud, melee vuln, Veil’s Grace

Drop-in: replace your existing scripts/adventure_new.py with this file.
"""

from __future__ import annotations
from sorcery_ext import (
    is_sorceress, cast_spell, on_new_round_tick,
    apply_melee_vulnerability, consume_evade_on_melee_if_any,
    override_from_rules
)

import json
import logging
import random
from pathlib import Path

# ---- Extensions / rules loader ----
from combat_engine_ext import (
    CombatEngine, load_rules,
    enforce_two_handed_and_shield, spend_stamina, regen_stamina,
    init_morale, morale_event, check_rout, aimed_attack_penalty
)

# ========= Logging setup =========
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# ========= Paths =========
HERE = Path(__file__).resolve().parent
RULES_DIR = (HERE / "../rules").resolve()
CHAR_DIR = (RULES_DIR / "characters").resolve()
ARMORS_JSON = (RULES_DIR / "armors.json").resolve()
WEAPONS_JSON = (RULES_DIR / "weapons.json").resolve()
COMBAT_RULES_JSON = (RULES_DIR / "combat_rules.json").resolve()

# ========= Load rules once =========
rules = load_rules(str(COMBAT_RULES_JSON))
override_from_rules(rules)   # <-- allows combat_rules.json to override spell costs/cooldowns
eng = CombatEngine(rules)

# ========= Safe I/O =========
def safe_load_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logging.debug(f"File content for {path}: {json.dumps(data, ensure_ascii=False, indent=2)[:2000]}")
            return data
    except FileNotFoundError:
        logging.warning(f"Missing file: {path}")
        return None
    except Exception as e:
        logging.exception(f"Failed to load JSON {path}: {e}")
        return None

# ========= Input helpers =========
def ask(prompt, default=None):
    try:
        s = input(prompt)
    except EOFError:
        s = ""
    if s.strip() == "" and default is not None:
        return str(default)
    return s.strip()

def ask_int(prompt, lo=None, hi=None, default=None):
    s = ask(prompt, default=("" if default is None else str(default)))
    try:
        val = int(s)
    except Exception:
        return int(default) if default is not None else 0
    if lo is not None and val < lo:
        return lo
    if hi is not None and val > hi:
        return hi
    return val

# ========= Data: armors & weapons =========
ARMORS_RAW = safe_load_json(ARMORS_JSON) or {}
WEAPONS_RAW = safe_load_json(WEAPONS_JSON) or {}

# Base damages if weapons.json misses something
WEAPON_DAMAGE = {
    "greatsword": 14, "longsword": 10, "dagger": 6, "improvised_club": 12, "ceremonial blade": 7,
}
DEFAULT_DURABILITY = {
    "greatsword": 70, "longsword": 60, "dagger": 50, "improvised_club": 55, "ceremonial blade": 45,
}

def overlay_weapons_from_json():
    data = WEAPONS_RAW
    if not data:
        return
    for key, w in data.items():
        key_l = str(key).lower()
        if isinstance(w, dict):
            if "base_damage" in w:
                try: WEAPON_DAMAGE[key_l] = int(w["base_damage"])
                except Exception: pass
            if "durability" in w:
                try: DEFAULT_DURABILITY[key_l] = int(w["durability"])
                except Exception: pass

overlay_weapons_from_json()

# ========= Armor resolver =========
DEFAULT_ARMORS = {
    "Light_Light": ("Padded Cloth", 5),
    "Light_Heavy": ("Light Chainmail", 10),
    "Medium_Heavy": ("Half Plate", 20),
    "Heavy_Heavy": ("Siege Plate", 35),
}

def resolve_armor(category_key: str):
    """
    Resolve an armor category (e.g. 'Medium_Heavy') to a concrete piece using armors.json variants.
    Returns dict with: name, weight, mobility_penalty, stamina_penalty, category, variant_key, coverage(list)
    """
    cat = str(category_key or "").strip()
    node = ARMORS_RAW.get(cat)
    def pack(name, weight, vkey, coverage=None, mob_bonus=0, stam_pen=None):
        weight = int(weight)
        stamina_pen = int(stam_pen if stam_pen is not None else max(0, weight // 20))
        mobility_pen = max(0, (weight // 10) - (int(mob_bonus) // 10))
        return {
            "name": name, "weight": weight,
            "mobility_penalty": mobility_pen,
            "stamina_penalty": stamina_pen,
            "category": cat or "Light_Light",
            "variant_key": vkey,
            "coverage": list(coverage or []),
        }

    if node is None:
        name, w = DEFAULT_ARMORS.get(cat, (cat or "Padded Cloth", 10))
        return pack(name, w, "default", coverage=[])

    if isinstance(node, dict) and not ("name" in node or "weight" in node):
        if not node:
            name, w = DEFAULT_ARMORS.get(cat, (cat, 10))
            return pack(name, w, "default-empty")
        vkey = "standard" if "standard" in node else next(iter(node.keys()))
        v = node.get(vkey, {})
        name = v.get("name", DEFAULT_ARMORS.get(cat, (cat, 10))[0])
        weight = int(v.get("weight", DEFAULT_ARMORS.get(cat, (cat, 10))[1]))
        cov = v.get("coverage", [])
        mob_bonus = int(v.get("mobility_bonus", 0))
        stam_pen = v.get("stamina_penalty")
        return pack(name, weight, vkey, coverage=cov, mob_bonus=mob_bonus, stam_pen=stam_pen)

    if isinstance(node, dict):
        name = node.get("name", DEFAULT_ARMORS.get(cat, (cat, 10))[0])
        weight = int(node.get("weight", DEFAULT_ARMORS.get(cat, (cat, 10))[1]))
        cov = node.get("coverage", [])
        mob_bonus = int(node.get("mobility_bonus", 0))
        stam_pen = node.get("stamina_penalty")
        return pack(name, weight, "flat", coverage=cov, mob_bonus=mob_bonus, stam_pen=stam_pen)

    if isinstance(node, (list, tuple)) and len(node) >= 2:
        name, weight = node[0], int(node[1])
        return pack(name, weight, "inline", coverage=[])

    name, w = DEFAULT_ARMORS.get(cat, (cat, 10))
    return pack(name, w, "fallback", coverage=[])

# ========= Characters / equipment =========
def equip_armor(character):
    if isinstance(character.get("armor"), list) and character["armor"]:
        cat = character["armor"][0]
    else:
        cat = "Light_Light"

    ar = resolve_armor(cat)
    character["_equipped_armor"] = {
        "name": ar["name"],
        "weight": ar["weight"],
        "mobility_penalty": ar["mobility_penalty"],
        "stamina_increase": ar["stamina_penalty"],
        "category": ar["category"],
        "variant": ar["variant_key"],
        "coverage": ar["coverage"],  # NEW
    }

    if ar["weight"] <= 5:
        print(f"🛡️ {character['name']}'s {ar['name']} ({ar['category']}, weight {ar['weight']}) has minimal impact on mobility and stamina.")
    else:
        print(f"⚠️ {character['name']}'s {ar['name']} ({ar['category']}, weight {ar['weight']}) reduces mobility by {ar['mobility_penalty']}% and increases stamina costs by {ar['stamina_penalty']}!")
    print(f"🛡️ {character['name']} equips {ar['name']}")
    logging.debug(f"Equipped {ar['name']} to {character['name']} (category={ar['category']}, variant={ar['variant_key']})")

    # Enforce 2H + shield rule and PRINT the result
    weapon_key = None
    if isinstance(character.get("weapon"), dict):
        weapon_key = character["weapon"].get("type") or character["weapon"].get("name")
    else:
        weapon_key = character.get("weapon")
    wdat = WEAPONS_RAW.get(str(weapon_key or "").lower())
    _logs = []
    enforce_two_handed_and_shield(character, wdat if isinstance(wdat, dict) else None, rules, _logs)
    for m in _logs:
        print(m)

def _find_character_filename(key_lower: str):
    aliases = {
        "torvald": "Torvald.json",
        "lyssa": "Lyssa.json",
        "ada": "ada.json",
        "brock": "Brock.json",
        "caldran": "Ser_Caldran_Vael.json",
        "ser_caldran": "Ser_Caldran_Vael.json",
        "ser caldran": "Ser_Caldran_Vael.json",
        "rock": "Rock.json",
        "isolde": "Isolde.json",
        "isolda": "Isolde.json",
    }
    if key_lower in aliases:
        p = CHAR_DIR / aliases[key_lower]
        if p.exists():
            return p
        if key_lower == "rock":
            p2 = CHAR_DIR / "Brock.json"
            if p2.exists():
                print("ℹ️  'Rock.json' not found; loading Brock as a fallback.")
                return p2
        return None
    normalized_query = key_lower.replace(" ", "_")
    for p in CHAR_DIR.glob("*.json"):
        stem = p.stem.lower()
        if stem == key_lower or stem.replace(" ", "_") == normalized_query or stem.replace("_", " ") == key_lower:
            return p
    return None

def load_character_file(short):
    p = _find_character_filename(short.lower())
    if p and p.exists():
        return safe_load_json(p)
    return None

def load_enemy_template(basename):
    return safe_load_json(CHAR_DIR / f"{basename}.json")

# ========= HP/weapon state =========
def ensure_hp_fields(unit):
    if "current_hp" not in unit:
        unit["current_hp"] = unit.get("total_hp", unit.get("hp", 1))
    if "alive" not in unit:
        unit["alive"] = unit["current_hp"] > 0

def init_weapon_state(unit):
    wpn = None
    if isinstance(unit.get("weapon"), dict):
        wpn = unit["weapon"].get("type") or unit["weapon"].get("name") or unit["weapon"].get("kind")
    else:
        wpn = unit.get("weapon")
    wpn = (str(wpn or "")).lower().strip()
    unit["_weapon_type"] = wpn

    dur = None
    if isinstance(unit.get("weapon"), dict):
        dur = unit["weapon"].get("durability")
    if dur is None:
        dur = DEFAULT_DURABILITY.get(wpn, 50)
    unit["_weapon_durability"] = int(dur)

def init_combatants(units):
    roster = list(units)
    for u in roster:
        ensure_hp_fields(u)
        init_morale(u)
    return roster

def base_damage_for(unit):
    w = unit.get("_weapon_type")
    if not w:
        if isinstance(unit.get("weapon"), dict):
            w = unit["weapon"].get("type") or unit["weapon"].get("name") or unit["weapon"].get("kind")
        else:
            w = unit.get("weapon")
    w = (str(w or "")).lower()
    return WEAPON_DAMAGE.get(w, 8)

def weapon_label_for_log(wpn):
    return str(wpn or "weapon")

def apply_durability_tick(attacker, round_log):
    w = attacker.get("_weapon_type")
    if not w:
        return
    attacker["_weapon_durability"] = max(0, int(attacker.get("_weapon_durability", DEFAULT_DURABILITY.get(w, 50))) - 1)
    label = weapon_label_for_log(w)
    round_log.append(f"⚔️ {attacker['name']}'s {label} durability: {attacker['_weapon_durability']}")

# ========= Stance / rolls =========
def stance_mods(stance):
    stance = (stance or "neutral").lower()
    atk = 0
    df = 0
    if stance == "offensive":
        atk += 10
        df -= 10
    elif stance == "defensive":
        atk -= 10
        df += 10
    return atk, df

# ——— Aimed zones and difficulty ———
AIM_ZONES = [
    "head", "throat", "neck",
    "chest", "stomach", "groin",
    "left_upper_arm", "left_lower_arm", "right_upper_arm", "right_lower_arm",
    "left_upper_leg", "left_lower_leg", "right_upper_leg", "right_lower_leg",
]

def choose_target_zone():
    print("Pick a target zone:")
    for i, z in enumerate(AIM_ZONES, 1):
        print(f"  [{i}] {z}")
    raw = ask("Enter zone (number or name): ", default="1").strip().lower()
    if raw.isdigit():
        idx = int(raw)
        idx = 1 if idx < 1 else idx
        idx = len(AIM_ZONES) if idx > len(AIM_ZONES) else idx
        return AIM_ZONES[idx - 1]
    key = raw.replace(" ", "_")
    if key in AIM_ZONES:
        return key
    for z in AIM_ZONES:
        if z.endswith(key) or key in z:
            return z
    return AIM_ZONES[0]

def coverage_keys_for_zone(zone):
    z = zone.lower()
    return {
        "head": ["head"],
        "throat": ["neck", "throat"],
        "neck": ["neck"],
        "chest": ["chest", "torso"],
        "stomach": ["stomach", "abdomen", "belly"],
        "groin": ["groin", "hips"],
        "left_upper_arm": ["left_upper_arm"],
        "left_lower_arm": ["left_lower_arm", "left_forearm"],
        "right_upper_arm": ["right_upper_arm"],
        "right_lower_arm": ["right_lower_arm", "right_forearm"],
        "left_upper_leg": ["left_upper_leg", "left_thigh"],
        "left_lower_leg": ["left_lower_leg", "left_shin"],
        "right_upper_leg": ["right_upper_leg", "right_thigh"],
        "right_lower_leg": ["right_lower_leg", "right_shin"],
    }.get(z, [z])

def is_zone_covered(target, zone):
    cov = (target.get("_equipped_armor") or {}).get("coverage") or []
    if not cov:
        return False
    ck = coverage_keys_for_zone(zone)
    cov_low = [c.lower() for c in cov]
    return any(c in cov_low for c in ck)

def attack_roll(attacker, attack_stance, target, target_stance, attack_type="normal", aimed_zone=None):
    atk_stance_mod, _ = stance_mods(attack_stance)
    _, def_stance_mod = stance_mods(target_stance)

    dex = int(attacker.get("dexterity", attacker.get("Dexterity", 25)))
    dex_mod = dex // 10

    aimed_pen_rules = aimed_attack_penalty(attacker, rules) if str(attack_type).lower().startswith("aim") else 0
    total_aimed_pen = aimed_pen_rules  # no per-zone extra in this build

    stress_mod = -int(attacker.get("stress_level", 0))
    pain_pct = 0
    if attacker.get("total_hp"):
        pain_pct = int(100 * (1 - attacker.get("current_hp", attacker["total_hp"]) / attacker["total_hp"]))
    pain_mod = -(pain_pct // 25)
    ambush_mod = 0
    weapon_skill = 0

    # Status penalties on the ATTACKER (fog, fear, veil aura)
    status_pen = 0
    fog_pen = int(attacker.get("_fog_atk_penalty", 0)) if int(attacker.get("_fogged_rounds", 0)) > 0 else 0
    if fog_pen:
        status_pen -= fog_pen
    if int(attacker.get("_feared_rounds", 0)) > 0:
        status_pen -= 10
    if int(attacker.get("_veil_aura_rounds", 0)) > 0:
        status_pen -= int(attacker.get("_veil_aura_penalty", 10) or 10)

    atk_roll = random.randint(1, 100)
    def_roll = random.randint(1, 100)

    attack_total = atk_roll + weapon_skill + dex_mod + atk_stance_mod + status_pen - total_aimed_pen + stress_mod + pain_mod + ambush_mod
    t_dex = int(target.get("dexterity", target.get("Dexterity", 25)))
    t_stat = t_dex // 10
    defense_total = def_roll + t_stat + def_stance_mod

    return {
        "atk_roll": atk_roll,
        "def_roll": def_roll,
        "attack_total": attack_total,
        "defense_total": defense_total,
        "dex_mod": dex_mod,
        "t_stat": t_stat,
        "weapon_skill": weapon_skill,
        "stress_mod": stress_mod,
        "pain_mod": pain_mod,
        "ambush_mod": ambush_mod,
        "aimed_pen": total_aimed_pen,
        "status_pen": status_pen,   # for optional logging
        "hit": attack_total > defense_total
    }

# ========= Damage application =========
def apply_damage(attacker, target, raw_damage, round_log, zone=None, is_crit=False):
    dmg = max(0, int(raw_damage))
    # armor mitigation if zone is covered; "zone=None" bypasses armor (used by Veil damage)
    if zone and is_zone_covered(target, zone):
        dmg = max(0, int(round(dmg * 0.75)))
        round_log.append(f"🛡️ Armor absorbs part of the blow to {zone}!")

    before = target["current_hp"]
    target["current_hp"] = max(0, before - dmg)
    after = target["current_hp"]

    crit_tag = " (CRIT!)" if is_crit else ""

    if after <= 0 and target.get("alive", True):
        target["alive"] = False
        if zone:
            round_log.append("🏴 " + f"{target['name']} falls! (hit to {zone}){crit_tag}")
        else:
            round_log.append("🏴 " + f"{target['name']} falls!{crit_tag}")
    else:
        if zone:
            round_log.append("💥 " + f"{target['name']} takes {dmg} damage to {zone}! ➜ HP: {after}/{target.get('total_hp', after)}{crit_tag}")
        else:
            round_log.append("💥 " + f"{target['name']} takes {dmg} damage! ➜ HP: {after}/{target.get('total_hp', after)}{crit_tag}")

def cleanup_dead(units, round_log):
    return [u for u in units if u.get("alive", True)]

# ========= Simple stalemate breaker =========
class StalemateWatch:
    def __init__(self, threshold=6):
        self.threshold = threshold
        self.no_damage_rounds = 0
    def note(self, did_damage, round_log):
        if did_damage:
            self.no_damage_rounds = 0
        else:
            self.no_damage_rounds += 1
            if self.no_damage_rounds >= self.threshold:
                round_log.append("⚠️ Stalemate detected → fatigue penalty applied to all.")
                self.no_damage_rounds = 0
                return True
        return False

def apply_fatigue_to_all(all_sides, round_log):
    for unit in all_sides:
        ensure_hp_fields(unit)
        unit["max_stamina"] = max(0, unit.get("max_stamina", 0) - 2)
        unit["current_hp"] = max(0, unit["current_hp"] - 1)
    round_log.append(("fatigue", "All combatants lose 1 HP and 2 max stamina"))

# ========= UI helpers =========
def choose_stance():
    print("Choose stance: [1] Offensive, [2] Neutral, [3] Defensive")
    x = ask_int("Enter stance (1-3): ", lo=1, hi=3, default=1)
    return {1: "offensive", 2: "neutral", 3: "defensive"}[x]

def choose_attack_type():
    print("Choose attack type: [1] Normal, [2] Aimed (rules-driven penalty)")
    x = ask_int("Enter attack type (1-2): ", lo=1, hi=2, default=1)
    return "aimed" if x == 2 else "normal"

def list_active_abilities(unit):
    ab = unit.get("abilities", {})
    return [k for k, v in ab.items() if isinstance(v, dict) and v.get("type") == "active"]

def choose_ability(unit):
    names = list_active_abilities(unit)
    if not names:
        return None
    listed = ", ".join(f"[{i+1}] {n}" for i, n in enumerate(names))
    print(f"Available active abilities: {listed}")
    raw = ask("Use ability? (number, name, or none): ", default="none").strip().lower()
    if raw in ("", "none", "0"):
        return None
    if raw.isdigit():
        i = int(raw) - 1
        if 0 <= i < len(names):
            return names[i]
        return None
    return raw if raw in names else None

def ability_damage_bonus(unit, ability_name):
    if not ability_name:
        return 0
    ab = unit.get("abilities", {}).get(ability_name, {})
    return int(ab.get("damage_bonus", 0))

# ========= Encounter/Combat =========
def safe_print_log(lines):
    for entry in lines:
        if isinstance(entry, dict):
            for k, v in entry.items():
                print(f"{k}: {v}")
        elif isinstance(entry, (list, tuple)):
            if len(entry) == 2:
                k, v = entry
                print(f"{k}: {v}")
            else:
                print(" ".join(map(str, entry)))
        else:
            print(str(entry))

def run_combat(player, enemies, label):
    enemies = init_combatants(enemies)
    player = init_combatants([player])[0]
    init_weapon_state(player)
    for e in enemies:
        init_weapon_state(e)

    print(f"\n⚔️ {label}")
    MAX_ROUNDS = 40
    watch = StalemateWatch(threshold=6)
    rnd = 0

    # thresholds from rules
    crit_hi = int(rules.get("critical_hit_threshold", 95))
    crit_lo = int(rules.get("critical_miss_threshold", 5))
    crit_mult = float((rules.get("critical_multipliers") or {}).get("default", 1.5))
    head_bonus_pct = int(((rules.get("aimed_attack") or {}).get("crit_bonus_head_pct", 10)))

    while rnd < MAX_ROUNDS:
        rnd += 1
        print("\n🎛️⚔️ New Round ⚔️🎛️")
        round_log = []

        # --- decay temporary statuses (fog/fear/root/aura) at round start
        on_new_round_tick(player, enemies, round_log)

        did_damage = False

        # filter alive
        enemies = [e for e in enemies if e.get("alive", True)]
        if not enemies:
            print("🎉 The bandits are defeated! Onward to the leader's camp...")
            return True
        target = enemies[0]

        # =========================
        # PLAYER TURN
        # =========================
        p_stance = choose_stance()

        # regen at start of your turn (applies to both casting and melee paths)
        regen_stamina(player, p_stance, rules, round_log)

        # If rooted by Shroud, you lose this action (both sides get rooted when cast)
        if int(player.get("_rooted_rounds", 0)) > 0:
            round_log.append(f"⛓️ {player['name']} is trapped by the rift and cannot act this turn.")
            player["_rooted_rounds"] = 0  # consumed
        else:
            did_cast = False
            if is_sorceress(player):
                did_cast = cast_spell(player, enemies, apply_damage, round_log)

            if not is_sorceress(player) or not did_cast:
                # ----- normal melee flow -----
                a_type = choose_attack_type()
                aimed_zone = choose_target_zone() if a_type == "aimed" else None
                ability = choose_ability(player)

                spend_stamina(player, "attack", p_stance, ability, rules, round_log)

                calc = attack_roll(player, p_stance, target, "neutral", a_type, aimed_zone=aimed_zone)
                base = base_damage_for(player)
                bonus = ability_damage_bonus(player, ability)
                raw_damage = base + bonus

                if a_type == "aimed" and aimed_zone:
                    print(f"🎯 Target zone: {aimed_zone} (aimed penalty {calc['aimed_pen']})")

                print(f"⚔️ {player['name']} is in {p_stance.upper()} stance")
                print(f"🛡️ {target['name']} is in NEUTRAL stance")
                line = f"⚔️ {player['name']} rolls {calc['atk_roll']} ➜ {calc['attack_total']} to attack!"
                if calc.get("status_pen", 0):
                    line += f" (−{abs(calc['status_pen'])} from fog/fear/aura)"
                print(line)
                print(f"🛡️ {target['name']} rolls {calc['def_roll']} ➜ {calc['defense_total']} to defend!")

                if calc["hit"]:
                    is_crit = calc["atk_roll"] >= crit_hi
                    if is_crit and aimed_zone and aimed_zone.lower() == "head":
                        raw_damage = int(round(raw_damage * (1 + head_bonus_pct / 100.0)))
                    final_damage = int(round(raw_damage * (crit_mult if is_crit else 1.0)))
                    apply_damage(player, target, final_damage, round_log, zone=aimed_zone, is_crit=is_crit)
                    did_damage = True
                    apply_durability_tick(player, round_log)
                else:
                    print("❌ Attack misses or is defended!")
                    spend_stamina(target, "parry", "neutral", None, rules, round_log)
                    # critical miss -> enemy riposte
                    if calc["atk_roll"] <= crit_lo:
                        round_log.append("⚡ Riposte! Your blunder opens you up!")
                        e_stance_r = "offensive"
                        regen_stamina(target, e_stance_r, rules, round_log)
                        spend_stamina(target, "attack", e_stance_r, None, rules, round_log)
                        calc_r = attack_roll(target, e_stance_r, player, "neutral", "normal")
                        e_base = base_damage_for(target)
                        if calc_r["hit"]:
                            is_crit_r = calc_r["atk_roll"] >= crit_hi
                            final_r = int(round(e_base * (crit_mult if is_crit_r else 1.0)))
                            # Veil’s Grace check on lethal
                            if is_sorceress(player) and player.get("current_hp", 0) - final_r <= 0:
                                if random.randint(1, 100) <= 20:
                                    round_log.append("🪽 Veil’s Grace triggers: death averted as she slips through the Veil!")
                                    player["_evade_next_melee"] = True
                                else:
                                    final_r = (final_r + 1) // 2
                                    round_log.append("🩶 Veil’s Grace falters—fatal blow reduced by half.")
                                    if not consume_evade_on_melee_if_any(player, round_log):
                                        final_r = apply_melee_vulnerability(player, final_r, is_melee=True)
                                        apply_damage(target, player, final_r, round_log, zone=None, is_crit=is_crit_r)
                                        did_damage = True
                                apply_durability_tick(target, round_log)
                            else:
                                # Fade Step auto-evade? If not, apply melee vuln
                                if not consume_evade_on_melee_if_any(player, round_log):
                                    final_r = apply_melee_vulnerability(player, final_r, is_melee=True)
                                    apply_damage(target, player, final_r, round_log, zone=None, is_crit=is_crit_r)
                                    did_damage = True
                                apply_durability_tick(target, round_log)
                        else:
                            round_log.append("…but the riposte fails to land.")

        enemies = cleanup_dead(enemies, round_log)
        if not enemies:
            safe_print_log(round_log)
            print("🎉 The bandits are defeated! Onward to the leader's camp...")
            return True

        # =========================
        # ENEMY TURNS
        # =========================
        for e in list(enemies):
            if not player.get("alive", True):
                break

            # skip their action if dazed/rooted
            if int(e.get("_dazed_rounds", 0)) > 0:
                round_log.append(f"💫 {e['name']} is staggered and loses their action.")
                e["_dazed_rounds"] = 0
                continue
            if int(e.get("_rooted_rounds", 0)) > 0:
                round_log.append(f"⛓️ {e['name']} is trapped by the rift and cannot act.")
                e["_rooted_rounds"] = 0
                continue

            e_stance = "offensive" if e["current_hp"] > e["total_hp"] * 0.35 else "defensive"
            regen_stamina(e, e_stance, rules, round_log)
            spend_stamina(e, "attack", e_stance, None, rules, round_log)
            calc_e = attack_roll(e, e_stance, player, "neutral", "normal")
            e_base = base_damage_for(e)

            print(f"⚔️ {e['name']} is in {e_stance.upper()} stance")
            print(f"🛡️ {player['name']} is in NEUTRAL stance")
            line_e = f"⚔️ {e['name']} rolls {calc_e['atk_roll']} ➜ {calc_e['attack_total']} to attack!"
            if calc_e.get("status_pen", 0):
                line_e += f" (−{abs(calc_e['status_pen'])} from fog/fear/aura)"
            print(line_e)
            print(f"🛡️ {player['name']} rolls {calc_e['def_roll']} ➜ {calc_e['defense_total']} to defend!")

            if calc_e["hit"]:
                is_crit_e = calc_e["atk_roll"] >= crit_hi
                final_e = int(round(e_base * (crit_mult if is_crit_e else 1.0)))

                # Veil's Grace: if this hit would kill a Sorceress, 20% avoid; else halve the killing blow
                if is_sorceress(player) and player.get("current_hp", 0) - final_e <= 0:
                    if random.randint(1, 100) <= 20:
                        round_log.append("🪽 Veil’s Grace triggers: death averted as she slips through the Veil!")
                        player["_evade_next_melee"] = True
                        # skip applying this lethal hit
                    else:
                        final_e = (final_e + 1) // 2
                        round_log.append("🩶 Veil’s Grace falters—fatal blow reduced by half.")
                        if not consume_evade_on_melee_if_any(player, round_log):
                            final_e = apply_melee_vulnerability(player, final_e, is_melee=True)
                            apply_damage(e, player, final_e, round_log, zone=None, is_crit=is_crit_e)
                            did_damage = True
                        apply_durability_tick(e, round_log)
                else:
                    # Fade Step auto-negate? If not, apply melee vulnerability (sorceress takes +50% from melee)
                    if not consume_evade_on_melee_if_any(player, round_log):
                        final_e = apply_melee_vulnerability(player, final_e, is_melee=True)
                        apply_damage(e, player, final_e, round_log, zone=None, is_crit=is_crit_e)
                        did_damage = True
                    apply_durability_tick(e, round_log)
            else:
                print("❌ Enemy attack misses or is defended!")
                spend_stamina(player, "parry", "neutral", None, rules, round_log)
                # enemy crit-miss -> your riposte
                if calc_e["atk_roll"] <= crit_lo:
                    round_log.append("⚡ Riposte! You punish their mistake!")
                    p_stance_r = "offensive"
                    regen_stamina(player, p_stance_r, rules, round_log)
                    spend_stamina(player, "attack", p_stance_r, None, rules, round_log)
                    calc_r2 = attack_roll(player, p_stance_r, e, "neutral", "normal")
                    p_base = base_damage_for(player)
                    if calc_r2["hit"]:
                        is_crit_r2 = calc_r2["atk_roll"] >= crit_hi
                        final_r2 = int(round(p_base * (crit_mult if is_crit_r2 else 1.0)))
                        apply_damage(player, e, final_r2, round_log, zone=None, is_crit=is_crit_r2)
                        did_damage = True
                        apply_durability_tick(player, round_log)
                    else:
                        round_log.append("…but your riposte misses!")

        if not player.get("alive", True) or player["current_hp"] <= 0:
            safe_print_log(round_log)
            print("💀 You have been defeated...")
            return False

        # Stalemate breaker
        if watch.note(did_damage, round_log):
            apply_fatigue_to_all([player] + enemies, round_log)

        safe_print_log(round_log)

    print("⏱️ Combat auto-ended (max rounds reached).")
    return False


# ========= Scenario helpers =========
def choose_player():
    print("Choose your character (torvald, lyssa, ada, brock, rock, isolde): ", end="")
    who = ask("", default="torvald").lower()
    player = load_character_file(who)
    # Allow 'isolde' alias to load Isolde.json
    if not player and who == "isolde":
        player = load_character_file("Isolde")
    if not player:
        print("Unknown choice, defaulting to Torvald.")
        player = load_character_file("torvald")

    # Enforce female-only for Sorceress
    if player and is_sorceress(player) and str(player.get("gender","")).lower() != "female":
        print("⚠️ Only women can wield Veil sorcery. Loading Isolde instead.")
        iso = load_character_file("Isolde")
        if iso: player = iso
    return player


def equip_starters(characters):
    for c in characters:
        equip_armor(c)

def make_bandits(n=2):
    base = load_enemy_template("bandit")
    if not base:
        base = {
            "name": "Bandit",
            "race": "Human",
            "total_hp": 15,
            "max_stamina": 10,
            "weapon_equipped": True,
            "weapon": "dagger",
            "armor": ["Light_Light"],
        }
    out = []
    for i in range(1, n + 1):
        b = json.loads(json.dumps(base))
        b["name"] = f"Bandit {i}"
        equip_armor(b)
        out.append(b)
    return out

def make_bandit_leader():
    base = load_enemy_template("bandit_leader")
    if not base:
        base = {
            "name": "Bandit Leader",
            "race": "Human",
            "total_hp": 100,
            "max_stamina": 90,
            "weapon_equipped": True,
            "weapon": "greatsword",
            "armor": ["Light_Heavy"],
        }
    equip_armor(base)
    return base

# ========= Main =========
def main():
    print("⚔️ Welcome to the Grimdark Village Rescue ⚔️")
    player = choose_player()
    if not player:
        print("Could not load player. Exiting.")
        return
    logging.info("Starting Grimdark Village Rescue")

    equip_armor(player)

    print("📜 A village pleads for help. Bandits hold a hostage...")
    print("Options: [1] Fight bandits, [2] Persuade bandits (Lyssa, Ada), [3] Sneak (Lyssa, Ada), [4] Test combat vs. Caldran]")
    choice = ask_int("Choose action (1-4): ", lo=1, hi=4, default=1)

    if choice != 1:
        print("Only the combat path is implemented in this build. Proceeding to fight…")

    # Encounter 1: two bandits
    enemies = make_bandits(2)
    ok = run_combat(player, enemies, "You confront Bandit!")
    if not ok:
        print("The attempt failed.")
        return

    # Encounter 2: leader
    leader = make_bandit_leader()
    _ = run_combat(player, [leader], "You confront Bandit Leader!")

if __name__ == "__main__":
    random.seed()
    main()






