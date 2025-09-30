#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import random
import sys
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

# ========= Safe I/O =========
def safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logging.debug(f"File content for {path}: {json.dumps(data, ensure_ascii=False, indent=2)}")
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
    # category -> (display_name, weight)
    "Light_Light": ("Padded Cloth", 5),
    "Light_Heavy": ("Light Chainmail", 10),
    "Medium_Heavy": ("Half Plate", 20),
    "Heavy_Heavy": ("Siege Plate", 35),
}

def load_armors():
    data = safe_load_json(ARMORS_JSON)
    if data is None:
        logging.debug(f"Loaded armors from FALLBACK default table (no {ARMORS_JSON})")
        # Convert to the common shape used below
        armors = {}
        for k, (name, weight) in DEFAULT_ARMORS.items():
            armors[k] = {"name": name, "weight": weight}
        return armors
    else:
        logging.debug(f"Loaded armors from {ARMORS_JSON}")
        # Expect either same shape as DEFAULT_ARMORS or map name->weight—normalize it.
        armors = {}
        for k, v in data.items():
            if isinstance(v, dict):
                name = v.get("name", k)
                weight = int(v.get("weight", 10))
            elif isinstance(v, (list, tuple)) and len(v) >= 2:
                name, weight = v[0], int(v[1])
            else:
                name, weight = k, int(v)
            armors[k] = {"name": name, "weight": weight}
        # Ensure defaults exist
        for k, (name, weight) in DEFAULT_ARMORS.items():
            armors.setdefault(k, {"name": name, "weight": weight})
        return armors

ARMORS = load_armors()

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

def weapon_label_for_log(wpn):
    # make logs look like your examples
    if wpn == "greatsword":
        return "2h_sword"
    if wpn == "longsword":
        return "Longsword"
    if wpn == "dagger":
        return "Dagger"
    if wpn == "improvised_club":
        return "Club"
    if wpn == "ceremonial blade":
        return "Ceremonial Blade"
    return str(wpn)

# ========= Logging-safe printers (avoid ValueError) =========
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

# ========= Combat helpers (HP/stalemate) =========
def ensure_hp_fields(unit):
    if "current_hp" not in unit:
        unit["current_hp"] = unit.get("total_hp", unit.get("hp", 1))
    if "alive" not in unit:
        unit["alive"] = unit["current_hp"] > 0

def init_combatants(units):
    roster = list(units)  # keep same objects, no deepcopy per round
    for u in roster:
        ensure_hp_fields(u)
    return roster

def apply_damage(attacker, target, raw_damage, round_log):
    dmg = max(0, int(raw_damage))
    before = target["current_hp"]
    target["current_hp"] = max(0, before - dmg)
    after = target["current_hp"]
    round_log.append(("damage", f"{attacker['name']} deals {dmg} to {target['name']} ({before}→{after})"))
    if after <= 0 and target.get("alive", True):
        target["alive"] = False
        round_log.append(f"💀 {target['name']} has fallen!")

def cleanup_dead(units, round_log):
    alive_units = [u for u in units if u.get("alive", True)]
    for u in list(units):
        if not u.get("alive", True):
            round_log.append(("removed", f"{u['name']} is removed from battle"))
    return alive_units

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
    # Determine armor category and equip a concrete piece from ARMORS
    if isinstance(character.get("armor"), list) and character["armor"]:
        cat = character["armor"][0]
    else:
        cat = "Light_Light"
    armor_def = ARMORS.get(cat, {"name": "Padded Cloth", "weight": 5})
    name = armor_def["name"]
    weight = int(armor_def["weight"])
    # compute tiny mobility penalty used in skill checks
    mobility_penalty = weight // 10  # 20 -> 2, 35 -> 3
    stamina_increase = max(0, weight // 20)  # 20 -> 1, 35 -> 1 (light touch)
    character["_equipped_armor"] = {"name": name, "weight": weight, "mobility_penalty": mobility_penalty, "stamina_increase": stamina_increase}
    # Flavor text to match your outputs
    if weight <= 5:
        print(f"🛡️ {character['name']}'s {name} (weight {weight}) has minimal impact on mobility and stamina.")
    else:
        print(f"⚠️ {character['name']}'s {name} (weight {weight}) reduces mobility by {mobility_penalty}% and increases stamina costs by {stamina_increase}!")
    print(f"🛡️ {character['name']} equips {name}")
    logging.debug(f"Equipped {name} to {character['name']}")

def load_character_file(short):
    """Map user choice to a filename and load it."""
    mapping = {
        "torvald": "Torvald.json",
        "lyssa": "Lyssa.json",
        "ada": "ada.json",
        "brock": "brock.json",
        "rock": "rock.json",
        "caldran": "Ser_Caldran_Vael.json",
        "ser_caldran": "Ser_Caldran_Vael.json",
    }
    fname = mapping.get(short.lower(), None)
    if not fname:
        return None
    return safe_load_json(CHAR_DIR / fname)

def load_enemy_template(basename):
    return safe_load_json(CHAR_DIR / f"{basename}.json")

def init_weapon_state(unit):
    wpn = None
    if isinstance(unit.get("weapon"), dict):
        wpn = unit["weapon"].get("type")
    else:
        wpn = unit.get("weapon")
    unit["_weapon_type"] = wpn
    dur = None
    if isinstance(unit.get("weapon"), dict):
        dur = unit["weapon"].get("durability")
    if dur is None:
        dur = DEFAULT_DURABILITY.get(wpn, 50)
    unit["_weapon_durability"] = dur

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

def attack_roll(attacker, attack_stance, target, target_stance, attack_type="normal", round_num=1, player_turn=False):
    # Compute modifiers
    atk_stance_mod, _ = stance_mods(attack_stance)
    _, def_stance_mod = stance_mods(target_stance)

    # Simple dex mod similar to your +2 in logs from DEX//10
    dex = int(attacker.get("dexterity", attacker.get("Dexterity", 25)))
    dex_mod = dex // 10

    # Aimed attack penalty (-30 + DEX//10)
    aimed_pen = 0
    if (attack_type or "normal").lower().startswith("aim"):
        aimed_pen = -30 + dex_mod

    # Pain / Stress hooks (currently 0, but we keep them for log compatibility)
    stress_mod = -int(attacker.get("stress_level", 0))  # usually 0
    pain_pct = 0
    if attacker.get("total_hp"):
        pain_pct = int(100 * (1 - attacker.get("current_hp", attacker["total_hp"]) / attacker["total_hp"]))
    pain_mod = -(pain_pct // 25)  # very mild effect

    ambush_mod = 0  # control elsewhere if you want
    weapon_skill = 0  # if you want to read from skills

    atk_roll = random.randint(1, 100)
    def_roll = random.randint(1, 100)

    attack_total = atk_roll + weapon_skill + dex_mod + atk_stance_mod + aimed_pen + stress_mod + pain_mod + ambush_mod
    # Defender uses dex-ish stat too
    t_dex = int(target.get("dexterity", target.get("Dexterity", 25)))
    t_stat = t_dex // 10
    defense_total = def_roll + t_stat + def_stance_mod  # block/parry abstracted

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
            w = unit["weapon"].get("type")
        else:
            w = unit.get("weapon")
    return WEAPON_DAMAGE.get((w or "").lower(), 8)

def apply_durability_tick(attacker, round_log):
    w = attacker.get("_weapon_type")
    if not w:
        return
    attacker["_weapon_durability"] = max(0, int(attacker.get("_weapon_durability", DEFAULT_DURABILITY.get(w, 50))) - 1)
    label = weapon_label_for_log(w)
    round_log.append(f"⚔️ {attacker['name']}'s {label} durability: {attacker['_weapon_durability']}")

# ========= UI helpers =========
def choose_stance():
    print("Choose stance: [1] Offensive (boost attack, increase stamina), [2] Neutral (balanced), [3] Defensive (boost defense, lower attack)")
    x = ask_int("Enter stance (1-3): ", lo=1, hi=3, default=1)
    return {1: "offensive", 2: "neutral", 3: "defensive"}[x]

def choose_attack_type():
    print("Choose attack type: [1] Normal (spread damage), [2] Aimed (-30 + DEX//10 penalty, single zone)")
    x = ask_int("Enter attack type (1-2): ", lo=1, hi=2, default=1)
    return "aimed" if x == 2 else "normal"

def list_active_abilities(unit):
    ab = unit.get("abilities", {})
    # only active ones
    names = [k for k, v in ab.items() if isinstance(v, dict) and v.get("type") == "active"]
    return names

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
def athletics_probe(player):
    # small opener like in your logs
    agility = int(player.get("agility", player.get("Agility", 35)))
    agi_mod = agility // 10  # "+5 (Agility)" if 50 → 5 ; for 35 → 3
    mobility_pen = int(player.get("_equipped_armor", {}).get("mobility_penalty", 0))
    # pain currently 0 at start
    pain_mod = 0
    roll = random.randint(1, 100)
    total = roll + agi_mod - mobility_pen - pain_mod
    need = 30
    print(f"🏃 {player['name']} attempts athletics check (needs {need}+): rolled {roll} + {agi_mod} (Agility) - {mobility_pen} (Mobility Penalty) - {pain_mod} (Pain) = {total}")
    return total >= need

def target_header(t):
    # "Target: Bandit 1 (Pain: 0%, Mobility Penalty: 0%)"
    pain_pct = 0
    if t.get("total_hp"):
        pain_pct = int(100 * (1 - t.get("current_hp", t["total_hp"]) / t["total_hp"]))
    mobp = int(t.get("_equipped_armor", {}).get("mobility_penalty", 0))
    return f"Target: {t['name']} (Pain: {pain_pct}%, Mobility Penalty: {mobp}%)"

def run_combat(player, enemies, label):
    # Initialize combat state
    enemies = init_combatants(enemies)
    player = init_combatants([player])[0]
    init_weapon_state(player)
    for e in enemies:
        init_weapon_state(e)

    print(f"⚔️ {label}")
    if athletics_probe(player):
        pass  # flavor only

    MAX_ROUNDS = 40
    watch = StalemateWatch(threshold=6)

    for rnd in range(1, MAX_ROUNDS + 1):
        print(f"\n🎛️⚔️ Round {rnd} ⚔️🎛️")
        logging.debug(f"Combat round {rnd} started")
        round_log = []
        did_damage = False

        # Pick current target (first alive)
        enemies = [e for e in enemies if e.get("alive", True)]
        if not enemies:
            print("🏆 Victory!")
            return True
        target = enemies[0]
        print(target_header(target))

        # === Player turn ===
        p_stance = choose_stance()
        a_type = choose_attack_type()
        ability = choose_ability(player)

        # Calculate and print roll logs similar to yours
        calc = attack_roll(player, p_stance, target, "neutral", a_type, round_num=rnd, player_turn=True)
        base = base_damage_for(player)
        bonus = ability_damage_bonus(player, ability)
        raw_damage = base + bonus
        absorbed = 0
        eff_damage = max(0, raw_damage - absorbed)
        logging.debug(f"Player attack - damage={raw_damage}, absorbed={absorbed}, effective_damage={eff_damage}")

        print(f"⚔️ {player['name']} is in {p_stance.upper()} stance")
        print(f"🛡️ {target['name']} is in NEUTRAL stance")
        print(f"⚔️ {player['name']} rolls {calc['atk_roll']} + {calc['weapon_skill']} (Weapon Skill) + {calc['dex_mod']} (Dexterity) - {abs(calc['stress_mod'])} (Stress) - {abs(calc['pain_mod'])} (Pain) + {calc['ambush_mod']} (Ambush) = {calc['attack_total']} to attack!")
        print(f"🛡️ {target['name']} rolls {calc['def_roll']} + {calc['t_stat']} (Stat) - 0 (Stress) - 0 (Pain) = {calc['defense_total']} to defend! (Parry)")

        if calc["hit"]:
            apply_damage(player, target, eff_damage, round_log)
            did_damage = True
            apply_durability_tick(player, round_log)
        else:
            print(f"❌ {player['name']} misses or {target['name']} successfully defends!")

        # Remove dead enemies and victory check before they act
        enemies = cleanup_dead(enemies, round_log)
        if not enemies:
            safe_print_log(round_log)
            print("🏆 Victory! Enemies defeated.")
            return True

        # === Enemy turns ===
        for e in list(enemies):
            if not player.get("alive", True):
                break
            # Simple stance choice for enemies
            e_stance = "offensive" if e["current_hp"] > e["total_hp"] * 0.35 else "defensive"
            calc_e = attack_roll(e, e_stance, player, "neutral", "normal", round_num=rnd, player_turn=False)
            e_base = base_damage_for(e)
            e_eff = e_base  # no soak for now
            logging.debug(f"Opponent {e['name']} attack - damage={e_base}, absorbed=0, effective_damage={e_eff}")

            print(f"⚔️ {e['name']} is in {e_stance.upper()} stance")
            print(f"🛡️ {player['name']} is in NEUTRAL stance")
            print(f"⚔️ {e['name']} rolls {calc_e['atk_roll']} + {calc_e['weapon_skill']} (Weapon Skill) + {calc_e['dex_mod']} (Dexterity) - {abs(calc_e['stress_mod'])} (Stress) - {abs(calc_e['pain_mod'])} (Pain) + {calc_e['ambush_mod']} (Ambush) = {calc_e['attack_total']} to attack!")
            print(f"🛡️ {player['name']} rolls {calc_e['def_roll']} + {calc_e['t_stat']} (Stat) - 0 (Stress) - 0 (Pain) = {calc_e['defense_total']} to defend! (Block)")

            if calc_e["hit"]:
                apply_damage(e, player, e_eff, round_log)
                did_damage = True
                apply_durability_tick(e, round_log)
            else:
                print(f"❌ {e['name']} misses or {player['name']} successfully defends!")

        if not player.get("alive", True) or player["current_hp"] <= 0:
            safe_print_log(round_log)
            print("☠️ You are defeated!")
            return False

        # Stalemate breaker
        if watch.note(did_damage, round_log):
            apply_fatigue_to_all([player] + enemies, round_log)

        safe_print_log(round_log)

    print("⏱️ Combat auto-ended (max rounds reached).")
    return False

# ========= Scenario =========
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
        # Fallback small template
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
        b = json.loads(json.dumps(base))  # shallow copy via json to detach
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

def main():
    print("⚔️ Welcome to the Grimdark Village Rescue ⚔️")
    player = choose_player()
    if not player:
        print("Could not load player. Exiting.")
        return
    logging.info("Starting Grimdark Village Rescue")

    # Equip player + minimal NPCs mentioned in your logs (purely cosmetic here)
    equip_armor(player)

    print("📜 Wojtek, the chronicler, speaks of a village under siege...")
    # (No HTTP/NPC call here; we keep it simple and offline.)

    print("Options: [1] Fight bandits, [2] Persuade bandits (Lyssa, Ada), [3] Sneak (Lyssa, Ada), [4] Test combat vs. Caldran")
    print("Debug: Before input prompt")
    choice = ask_int("Choose action (1-4): ", lo=1, hi=4, default=1)
    print(f"Debug: After input prompt, choice =  {choice}")

    if choice != 1:
        print("Only the combat path is implemented in this simplified build. Proceeding to fight…")

    # --- Encounter 1: Two bandits ---
    enemies = make_bandits(2)
    ok = run_combat(player, enemies, "You confront two bandits at the village outskirts!")
    if not ok:
        return

    # --- Encounter 2: Bandit Leader ---
    leader = make_bandit_leader()
    _ = run_combat(player, [leader], "The Bandit Leader steps forward, greatsword raised!")

    print("🎉 Scenario complete.")

if __name__ == "__main__":
    # Make randomness a bit more exciting each run
    random.seed()
    main()


