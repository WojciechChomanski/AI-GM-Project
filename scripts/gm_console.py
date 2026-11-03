# scripts/gm_console.py – v11 FINAL (Ogre Female blocked + all valid females restored + variable damage)
import json, random
from pathlib import Path
from collections import defaultdict
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strength import strength_damage_bonus

BASE_DIR = Path(__file__).parent.parent / "rules"
races = json.loads((BASE_DIR / "races.json").read_text())
weapons = json.loads((BASE_DIR / "weapons.json").read_text())
classes = {f.stem: json.loads(f.read_text()) for f in (BASE_DIR / "classes").glob("*.json")}
stats_data = json.loads((BASE_DIR / "stats.json").read_text())

def get_class_data(file_data, cls_key):
    if isinstance(file_data, dict):
        if cls_key in file_data: return file_data[cls_key]
        for k, v in file_data.items():
            if isinstance(v, dict) and ("restrictions" in v or "gender_lock" in v or "allowed_genders" in v):
                return v
        for k, v in file_data.items():
            if isinstance(v, dict) and cls_key.lower() in str(k).lower():
                return v
    return file_data

def is_valid_class(race, gender, file_data, cls_key):
    if race.lower() == "ogre" and gender == "Female": return False
    cls_data = get_class_data(file_data, cls_key)
    if not isinstance(cls_data, dict): return True
    if "restrictions" in cls_data:
        r = cls_data["restrictions"]
        if r.get("gender") and r["gender"] != gender: return False
        if r.get("race"):
            race_val = r["race"]
            if isinstance(race_val, list) and race not in race_val: return False
            if isinstance(race_val, str) and race_val != race: return False
    if "gender_lock" in cls_data and gender not in cls_data["gender_lock"]: return False
    if "race_lock" in cls_data and race not in cls_data["race_lock"]: return False
    if "allowed_genders" in cls_data and gender not in cls_data["allowed_genders"]: return False
    if "allowed_races" in cls_data and race not in cls_data["allowed_races"]: return False
    return True

print("=== AI GM Console v11 FINAL (Ogre Female blocked) ===\nsimulate quick 150\nsimulate detailed 10\n")

def create_template(race, gender, cls_name, weapon):
    key = f"{race}_{gender}"
    base = stats_data.get(key, {}).get("starting_stats", {})
    return {
        "name": "Attacker", "race": race, "gender": gender, "class": cls_name,
        "total_hp": 140, "hp": 140,
        "max_stamina": 120, "stamina": 120,
        "weapon_skill": base.get("weapon_skill", 30),
        "strength": base.get("strength", 35),
        "weapon": weapon, "armor": ["Medium_Heavy"],
        "stance": "neutral"
    }

def perform_attack(att, defn):
    atk_roll = random.randint(1, 100) + att.get("weapon_skill", 30)
    def_roll = random.randint(1, 100) + defn.get("weapon_skill", 25)
    hit = atk_roll > def_roll + 10
    base_dmg = {"greatsword":14, "axe_2h":13, "mace":12, "sword_1h":11}.get(att["weapon"], 10)
    dmg = base_dmg + strength_damage_bonus(att.get("strength",35), att.get("gender","Male")) if hit else 0
    armor_abs = {"Light_Heavy":3, "Medium_Heavy":5, "Heavy_Heavy":7}[defn["armor"][0]]
    net = max(0, dmg - armor_abs)
    return net, None, None

import character_store  # tick / save / load / list / status (docs/RECOVERY.md)
import progression


def perk_prompt(chars):
    """Remind the GM of weapon perk picks a character has reached but not chosen (new mastery rank)."""
    lines = []
    for name, c in chars.items():
        for fam, rank, opts in progression.pending_perk_picks(c):
            lines.append(f"⭐ {name}: {fam} rank {rank} - choose a perk: {' / '.join(opts)}"
                         f"  (pick {name} {fam} {rank} <id>)")
    return "\n".join(lines)


def perk_command(args, chars):
    """perks <name> | pick <name> <family> <rank> <perk_id>"""
    if len(args) < 2 or args[1] not in chars:
        return "usage: perks <name> | pick <name> <family> <rank> <perk_id> (load the character first)"
    c = chars[args[1]]
    if args[0] == "perks":
        return perk_prompt({args[1]: c}) or f"{args[1]} has no perk picks waiting."
    if len(args) != 5:
        return "usage: pick <name> <family> <rank> <perk_id>"
    try:
        progression.choose_perk(c, args[2], int(args[3]), args[4])
    except ValueError as e:
        return f"✗ {e}"
    return f"✓ {args[1]} chose {args[4]} ({args[2]} rank {args[3]}). Permanent. Remember to save {args[1]}."
loaded_characters = {}

while True:
    raw = input("gm> ").strip()
    cmd = raw.lower().split()
    if not cmd: continue
    if cmd[0] == "quit": break
    if cmd[0] in ("tick", "save", "load", "list", "status"):
        print(character_store.console_command(raw, loaded_characters))
        if cmd[0] in ("load", "status", "tick"):
            print(perk_prompt(loaded_characters))
        continue
    if cmd[0] in ("perks", "pick"):
        print(perk_command(raw.split(), loaded_characters))
        continue
    if cmd[0] != "simulate":
        print("perks <name> | pick <name> <family> <rank> <id> | simulate quick 150 | tick round [n] | tick day [n] [mode] [unfed] | load/save <name> | list | status <name>")
        continue
    mode = cmd[1] if len(cmd) > 1 else "quick"
    runs = int(cmd[2]) if len(cmd) > 2 else 100
    print(f"\n=== {mode.upper()} SIM ===\n")

    if mode == "detailed":
        for i in range(runs):
            att = create_template("Human", "Male", "Crusader_Knight", random.choice(list(weapons.keys())))
            att["stance"] = random.choice(["offensive", "neutral", "defensive"])
            defn = create_template("Human", "Male", "Warrior", "greatsword")
            defn["armor"] = [random.choice(["Light_Heavy", "Medium_Heavy", "Heavy_Heavy"])]
            print(f"Fight {i+1} | {att['stance']} | {att['weapon']} vs {defn['armor'][0]}")
            for r in range(1,9):
                net, _, _ = perform_attack(att, defn)
                print(f"R{r}: Net {net}")
            print("---")
        continue

    results = defaultdict(list)
    for race in races:
        playable = races[race].get("playable_genders", ["Male","Female"])
        for gender in playable:
            for cls, clsdata in classes.items():
                if is_valid_class(race, gender, clsdata, cls):
                    for weapon in ["greatsword","axe_2h","mace","sword_1h"]:
                        for stance in ["offensive","neutral","defensive"]:
                            for armor in ["Light_Heavy","Medium_Heavy","Heavy_Heavy"]:
                                att = create_template(race, gender, cls, weapon)
                                att["stance"] = stance
                                defn = create_template("Human", "Male", "Warrior", "greatsword")
                                defn["armor"] = [armor]
                                dmg_total = hits = 0
                                for _ in range(runs):
                                    net, _, _ = perform_attack(att, defn)
                                    hits += 1 if net > 0 else 0
                                    dmg_total += net
                                avg = round(dmg_total / hits, 1) if hits else 0
                                key = f"{race} {gender} {cls} | {weapon} | {stance} vs {armor}"
                                results[key].append((avg, round(hits / runs * 100), 0, 0))
    print(f"{'Combo':<75} | Net Dmg | Hit%")
    print("-" * 95)
    for k, d in sorted(results.items()):
        avg = round(sum(x[0] for x in d) / len(d), 1)
        h = round(sum(x[1] for x in d) / len(d))
        print(f"{k:<75} | {avg:7.1f} | {h:4}%")
    print("\nDone.")