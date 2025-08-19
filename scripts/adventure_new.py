#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import random
from pathlib import Path

# ========= Logging setup =========
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# ========= Paths =========
HERE = Path(__file__).resolve().parent
RULES_DIR = (HERE / "../rules").resolve()
CHAR_DIR = (RULES_DIR / "characters").resolve()
ARMORS_JSON = (RULES_DIR / "armors.json").resolve()
WEAPONS_JSON = (RULES_DIR / "weapons.json").resolve()

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

# ========= Armor data =========
DEFAULT_ARMORS = {
    "Light_Light": ("Padded Cloth", 5),
    "Light_Heavy": ("Light Chainmail", 10),
    "Medium_Heavy": ("Half Plate", 20),
    "Heavy_Heavy": ("Siege Plate", 35),
}

ARMORS_RAW = safe_load_json(ARMORS_JSON) or {}

def resolve_armor(category_key: str):
    """
    Resolve an armor *category* (e.g., 'Medium_Heavy') to a concrete piece using armors.json variants.
    Prefers 'standard' variant; otherwise picks the first available variant.
    Returns a dict with guaranteed keys: name, weight, mobility_penalty, stamina_penalty, category, variant_key
    """
    cat = str(category_key or "").strip()
    # If the file doesn't define this category, fall back to defaults
    node = ARMORS_RAW.get(cat)
    if node is None:
        name, w = DEFAULT_ARMORS.get(cat, (cat or "Padded Cloth", 10))
        return {
            "name": name,
            "weight": int(w),
            "mobility_penalty": max(0, int(w) // 10),
            "stamina_penalty": max(0, int(w) // 20),
            "category": cat or "Light_Light",
            "variant_key": "default",
        }

    # If the node itself looks like a variant-map (no direct name/weight keys)
    if isinstance(node, dict) and not ("name" in node or "weight" in node):
        if not node:
            name, w = DEFAULT_ARMORS.get(cat, (cat, 10))
            return {
                "name": name,
                "weight": int(w),
                "mobility_penalty": max(0, int(w) // 10),
                "stamina_penalty": max(0, int(w) // 20),
                "category": cat,
                "variant_key": "default-empty",
            }
        vkey = "standard" if "standard" in node else next(iter(node.keys()))
        v = node.get(vkey, {})
        name = v.get("name", DEFAULT_ARMORS.get(cat, (cat, 10))[0])
        weight = int(v.get("weight", DEFAULT_ARMORS.get(cat, (cat, 10))[1]))
        # prefer explicit penalties if present
        stamina_pen = int(v.get("stamina_penalty", max(0, weight // 20)))
        # mobility_bonus in file is positive; treat it as reducing penalty
        mob_bonus = int(v.get("mobility_bonus", 0))
        mobility_pen = max(0, (weight // 10) - (mob_bonus // 10))
        return {
            "name": name,
            "weight": weight,
            "mobility_penalty": mobility_pen,
            "stamina_penalty": stamina_pen,
            "category": cat,
            "variant_key": vkey,
        }

    # Flat dict or other shapes
    if isinstance(node, dict):
        name = node.get("name", DEFAULT_ARMORS.get(cat, (cat, 10))[0])
        weight = int(node.get("weight", DEFAULT_ARMORS.get(cat, (cat, 10))[1]))
        stamina_pen = int(node.get("stamina_penalty", max(0, weight // 20)))
        mob_bonus = int(node.get("mobility_bonus", 0))
        mobility_pen = max(0, (weight // 10) - (mob_bonus // 10))
        return {
            "name": name,
            "weight": weight,
            "mobility_penalty": mobility_pen,
            "stamina_penalty": stamina_pen,
            "category": cat,
            "variant_key": "flat",
        }

    # List/tuple -> [name, weight]
    if isinstance(node, (list, tuple)) and len(node) >= 2:
        name, weight = node[0], int(node[1])
        return {
            "name": name,
            "weight": weight,
            "mobility_penalty": max(0, weight // 10),
            "stamina_penalty": max(0, weight // 20),
            "category": cat,
            "variant_key": "inline",
        }

    # Fallback
    name, w = DEFAULT_ARMORS.get(cat, (cat, 10))
    return {
        "name": name,
        "weight": int(w),
        "mobility_penalty": max(0, int(w) // 10),
        "stamina_penalty": max(0, int(w) // 20),
        "category": cat,
        "variant_key": "fallback",
    }

# ========= Weapons / damage / durability =========
WEAPON_DAMAGE = {
    "greatsword": 14,
    "longsword": 10,
    "dagger": 8,
    "improvised_club": 12,
    "ceremonial blade": 7,
}
DEFAULT_DURABILITY = {
    "greatsword": 70,
    "longsword": 60,
    "dagger": 50,
    "improvised_club": 55,
    "ceremonial blade": 45,
}

def overlay_weapons_from_json():
    data = safe_load_json(WEAPONS_JSON)
    if not data:
        return
    for key, w in data.items():
        key_l = str(key).lower()
        if isinstance(w, dict):
            if "base_damage" in w:
                try:
                    WEAPON_DAMAGE[key_l] = int(w["base_damage"])
                except Exception:
                    pass
            if "durability" in w:
                try:
                    DEFAULT_DURABILITY[key_l] = int(w["durability"])
                except Exception:
                    pass

overlay_weapons_from_json()

def weapon_label_for_log(wpn):
    return str(wpn or "weapon")

# ========= Logging-safe printers =========
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

# ========= Combat helpers =========
def ensure_hp_fields(unit):
    if "current_hp" not in unit:
        unit["current_hp"] = unit.get("total_hp", unit.get("hp", 1))
    if "alive" not in unit:
        unit["alive"] = unit["current_hp"] > 0

def init_combatants(units):
    roster = list(units)
    for u in roster:
        ensure_hp_fields(u)
    return roster

def apply_damage(attacker, target, raw_damage, round_log):
    dmg = max(0, int(raw_damage))
    before = target["current_hp"]
    target["current_hp"] = max(0, before - dmg)
    after = target["current_hp"]
    if after <= 0 and target.get("alive", True):
        target["alive"] = False
        round_log.append("🏴 " + f"{target['name']} falls!")
    else:
        round_log.append("💥 " + f"{target['name']} takes {dmg} damage! ➜ HP: {after}/{target.get('total_hp', after)}")

def cleanup_dead(units, round_log):
    return [u for u in units if u.get("alive", True)]

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

# ========= Character/Armor helpers =========
def equip_armor(character):
    # Determine armor category from character
    if isinstance(character.get("armor"), list) and character["armor"]:
        cat = character["armor"][0]
    else:
        cat = "Light_Light"

    ar = resolve_armor(cat)

    # Save for later checks
    character["_equipped_armor"] = {
        "name": ar["name"],
        "weight": ar["weight"],
        "mobility_penalty": ar["mobility_penalty"],
        "stamina_increase": ar["stamina_penalty"],
        "category": ar["category"],
        "variant": ar["variant_key"],
    }

    # Flavor text & confirmation with category
    if ar["weight"] <= 5:
        print(f"🛡️ {character['name']}'s {ar['name']} ({ar['category']}, weight {ar['weight']}) has minimal impact on mobility and stamina.")
    else:
        print(f"⚠️ {character['name']}'s {ar['name']} ({ar['category']}, weight {ar['weight']}) reduces mobility by {ar['mobility_penalty']}% and increases stamina costs by {ar['stamina_penalty']}!")
    print(f"🛡️ {character['name']} equips {ar['name']}")
    logging.debug(f"Equipped {ar['name']} to {character['name']} (category={ar['category']}, variant={ar['variant_key']})")

def _find_character_filename(key_lower: str):
    # Preferred explicit aliases
    aliases = {
        "torvald": "Torvald.json",
        "lyssa": "Lyssa.json",
        "ada": "ada.json",
        "brock": "Brock.json",
        "caldran": "Ser_Caldran_Vael.json",
        "ser_caldran": "Ser_Caldran_Vael.json",
        "ser caldran": "Ser_Caldran_Vael.json",
    }
    if key_lower in aliases:
        return CHAR_DIR / aliases[key_lower]

    # Special handling for 'rock'
    if key_lower == "rock":
        # Prefer Rock.json if present
        p1 = CHAR_DIR / "Rock.json"
        if p1.exists():
            return p1
        # Graceful fallback to Brock.json if it exists
        p2 = CHAR_DIR / "Brock.json"
        if p2.exists():
            print("ℹ️  'Rock.json' not found; loading Brock as a fallback.")
            return p2
        return None

    # scan characters folder case-insensitively
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

def init_weapon_state(unit):
    wpn = None
    if isinstance(unit.get("weapon"), dict):
        wpn = unit["weapon"].get("type") or unit["weapon"].get("name") or unit["weapon"].get("kind")
    else:
        wpn = unit.get("weapon")
    wpn = (wpn or "").lower().strip()
    unit["_weapon_type"] = wpn

    dur = None
    if isinstance(unit.get("weapon"), dict):
        dur = unit["weapon"].get("durability")
    if dur is None:
        dur = DEFAULT_DURABILITY.get(wpn, 50)
    unit["_weapon_durability"] = int(dur)

# ========= Rolls / math =========
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

def attack_roll(attacker, attack_stance, target, target_stance, attack_type="normal"):
    atk_stance_mod, _ = stance_mods(attack_stance)
    _, def_stance_mod = stance_mods(target_stance)

    dex = int(attacker.get("dexterity", attacker.get("Dexterity", 25)))
    dex_mod = dex // 10
    aimed_pen = -30 + dex_mod if str(attack_type).lower().startswith("aim") else 0

    stress_mod = -int(attacker.get("stress_level", 0))
    pain_pct = 0
    if attacker.get("total_hp"):
        pain_pct = int(100 * (1 - attacker.get("current_hp", attacker["total_hp"]) / attacker["total_hp"]))
    pain_mod = -(pain_pct // 25)

    ambush_mod = 0
    weapon_skill = 0

    atk_roll = random.randint(1, 100)
    def_roll = random.randint(1, 100)

    attack_total = atk_roll + weapon_skill + dex_mod + atk_stance_mod + aimed_pen + stress_mod + pain_mod + ambush_mod
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
        "aimed_pen": aimed_pen,
        "hit": attack_total > defense_total
    }

def base_damage_for(unit):
    w = unit.get("_weapon_type")
    if not w:
        if isinstance(unit.get("weapon"), dict):
            w = unit["weapon"].get("type") or unit["weapon"].get("name") or unit["weapon"].get("kind")
        else:
            w = unit.get("weapon")
    w = (w or "").lower()
    return WEAPON_DAMAGE.get(w, 8)

def apply_durability_tick(attacker, round_log):
    w = attacker.get("_weapon_type")
    if not w:
        return
    attacker["_weapon_durability"] = max(0, int(attacker.get("_weapon_durability", DEFAULT_DURABILITY.get(w, 50))) - 1)
    label = weapon_label_for_log(w)
    round_log.append(f"⚔️ {attacker['name']}'s {label} durability: {attacker['_weapon_durability']}")

# ========= UI helpers =========
def choose_stance():
    print("Choose stance: [1] Offensive, [2] Neutral, [3] Defensive")
    x = ask_int("Enter stance (1-3): ", lo=1, hi=3, default=1)
    return {1: "offensive", 2: "neutral", 3: "defensive"}[x]

def choose_attack_type():
    print("Choose attack type: [1] Normal, [2] Aimed (-30 + DEX//10)")
    x = ask_int("Enter attack type (1-2): ", lo=1, hi=2, default=1)
    return "aimed" if x == 2 else "normal"

def list_active_abilities(unit):
    ab = unit.get("abilities", {})
    return [k for k, v in ab.items() if isinstance(v, dict) and v.get("type") == "active"]

def choose_ability(unit):
    names = list_active_abilities(unit)
    if not names:
        return None
    print(f"Available active abilities: {', '.join(names)}")
    raw = ask("Use ability? (name or none): ", default="none").strip().lower()
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
    while rnd < MAX_ROUNDS:
        rnd += 1
        print("\n🎛️⚔️ New Round ⚔️🎛️")
        round_log = []
        did_damage = False

        # choose first alive target
        enemies = [e for e in enemies if e.get("alive", True)]
        if not enemies:
            print("🎉 The bandits are defeated! Onward to the leader's camp...")
            return True
        target = enemies[0]

        # Player turn
        p_stance = choose_stance()
        a_type = choose_attack_type()
        ability = choose_ability(player)

        calc = attack_roll(player, p_stance, target, "neutral", a_type)
        base = base_damage_for(player)
        bonus = ability_damage_bonus(player, ability)
        raw_damage = base + bonus

        print(f"⚔️ {player['name']} is in {p_stance.upper()} stance")
        print(f"🛡️ {target['name']} is in NEUTRAL stance")
        print(f"⚔️ {player['name']} rolls {calc['atk_roll']} ➜ {calc['attack_total']} to attack!")
        print(f"🛡️ {target['name']} rolls {calc['def_roll']} ➜ {calc['defense_total']} to defend!")

        if calc["hit"]:
            apply_damage(player, target, raw_damage, round_log)
            did_damage = True
            apply_durability_tick(player, round_log)
        else:
            print("❌ Attack misses or is defended!")

        enemies = cleanup_dead(enemies, round_log)
        if not enemies:
            safe_print_log(round_log)
            print("🎉 The bandits are defeated! Onward to the leader's camp...")
            return True

        # Enemy turns
        for e in list(enemies):
            if not player.get("alive", True):
                break
            e_stance = "offensive" if e["current_hp"] > e["total_hp"] * 0.35 else "defensive"
            calc_e = attack_roll(e, e_stance, player, "neutral", "normal")
            e_base = base_damage_for(e)

            print(f"⚔️ {e['name']} is in {e_stance.UPPER()} stance" if hasattr(str, "UPPER") else f"⚔️ {e['name']} is in {e_stance.upper()} stance")
            print(f"🛡️ {player['name']} is in NEUTRAL stance")
            print(f"⚔️ {e['name']} rolls {calc_e['atk_roll']} ➜ {calc_e['attack_total']} to attack!")
            print(f"🛡️ {player['name']} rolls {calc_e['def_roll']} ➜ {calc_e['defense_total']} to defend!")

            if calc_e["hit"]:
                apply_damage(e, player, e_base, round_log)
                did_damage = True
                apply_durability_tick(e, round_log)
            else:
                print("❌ Enemy attack misses or is defended!")

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
    print("Choose your character (torvald, lyssa, ada, brock, rock): ", end="")
    who = ask("", default="torvald").lower()
    player = load_character_file(who)
    if not player:
        print("Unknown choice, defaulting to Torvald.")
        player = load_character_file("torvald")
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
        print("Only the combat path is implemented in this simplified build. Proceeding to fight…")

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

