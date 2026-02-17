# scripts/gm_console.py – AI GM Console Test Tool
# Run: python gm_console.py

import json
import random
from pathlib import Path
from collections import defaultdict

# Load from rules
BASE_DIR = Path(__file__).parent.parent / "rules"
races = json.loads((BASE_DIR / "races.json").read_text())
weapons = json.loads((BASE_DIR / "weapons.json").read_text())
stances = json.loads((BASE_DIR / "stances.json").read_text())
armors = json.loads((BASE_DIR / "armors.json").read_text())

# Load classes from folder
classes = {}
for cls_file in (BASE_DIR / "classes").glob("*.json"):
  key = cls_file.stem
  classes[key] = json.loads(cls_file.read_text())

print("=== AI GM Console – Test All Mechanics ===\n")
print("Loaded: Races, Weapons, Stances, Armors, Classes\n")

# Default combatants
attacker = {
  "name": "Torvald", "race": "Human", "gender": "Male", "class": "Outlaw_Mercenary_Warrior",
  "total_hp": 140, "hp": 140, "max_stamina": 120, "stamina": 120, "pain": 0, "stress": 0, "corruption": 0,
  "armor": ["Medium_Heavy"], "weapon": "greatsword", "shield_equipped": False,
  "strength": 35, "dexterity": 30, "weapon_skill": 30, "abilities": {"brutal_strike": {"damage_bonus": 5, "stamina_cost": 8}}
}
defender = {
  "name": "Bandit Leader", "race": "Human", "gender": "Male", "class": "Warrior",
  "total_hp": 100, "hp": 100, "max_stamina": 100, "stamina": 100, "pain": 0, "stress": 0, "corruption": 0,
  "armor": ["Light_Heavy"], "weapon": "greatsword", "shield_equipped": False,
  "strength": 30, "dexterity": 25, "weapon_skill": 20, "abilities": {}
}

attacker["stance"] = "neutral"
defender["stance"] = "neutral"

print("Default: Attacker Torvald (greatsword) vs Defender Bandit Leader (light heavy armor)\n")
print("Commands:")
print("  set stance <offensive/neutral/defensive> [attacker/defender]")
print("  set weapon <name> [attacker/defender]")
print("  set class <name> [attacker/defender]")
print("  set race <name> [attacker/defender]")
print("  set gender <male/female> [attacker/defender]")
print("  set shield <true/false> [attacker/defender]")
print("  set armor <tier> [attacker/defender]")
print("  attack [maneuver]  # e.g., attack brutal_strike")
print("  status")
print("  test <weapon> <armor_tier> <runs>  # e.g., test axe_2h heavy_heavy 100")
print("  quit\n")

while True:
  cmd = input("gm> ").strip().lower().split()
  if not cmd: continue

  if cmd[0] == "quit":
    break

  target = "attacker" if len(cmd) < 4 or cmd[3] != "defender" else "defender"
  t = attacker if target == "attacker" else defender

  if cmd[0] == "set":
    if cmd[1] == "stance":
      t["stance"] = cmd[2]
      print(f"{target.capitalize()} stance set to {t['stance']}")

    elif cmd[1] == "weapon":
      weapon = cmd[2]
      if weapon in weapons:
        t["weapon"] = weapon
        t["handedness"] = "2h" if "2H" in weapons[weapon]["type"] else "1h"
        print(f"{target.capitalize()} weapon set to {weapon} ({t['handedness']})")
      else:
        print("Weapon not found. Available:", list(weapons.keys()))

    elif cmd[1] == "class":
      cls = cmd[2]
      if cls in classes:
        t["class"] = cls
        # Apply class stats/mods (from progression tier 1)
        prog = classes[cls]["progression"][0]
        t["abilities"] = {ab: {} for ab in prog["abilities_gain"]}  # Stub abilities
        print(f"{target.capitalize()} class set to {cls}")
      else:
        print("Class not found. Available:", list(classes.keys()))

    elif cmd[1] == "race":
      race = cmd[2].capitalize()
      if race in races:
        t["race"] = race
        # Apply race stats (use starting_stats)
        race_key = f"{race}_{t['gender']}"
        if race_key in races:
          t.update(races[race_key]["starting_stats"])
        print(f"{target.capitalize()} race set to {race}")
      else:
        print("Race not found. Available:", [k.split('_')[0] for k in races.keys()])

    elif cmd[1] == "gender":
      t["gender"] = cmd[2].capitalize()
      print(f"{target.capitalize()} gender set to {t['gender']}")

    elif cmd[1] == "shield":
      t["shield_equipped"] = cmd[2] == "true"
      print(f"{target.capitalize()} shield: {t['shield_equipped']}")

    elif cmd[1] == "armor":
      t["armor"] = [cmd[2].capitalize()]
      print(f"{target.capitalize()} armor set to {t['armor']}")

    else:
      print("Unknown set command. Try: stance/weapon/class/race/gender/shield/armor")

  elif cmd[0] == "attack":
    maneuver = cmd[1] if len(cmd) > 1 else None
    # Apply maneuver if valid
    extra_dmg = 0
    extra_cost = 0
    if maneuver in t["abilities"]:
      ab = t["abilities"][maneuver]
      extra_dmg = ab.get("damage_bonus", 0)
      extra_cost = ab.get("stamina_cost", 0)

    # Stance mod
    stance = t["stance"]
    atk_mod = {"offensive": 10, "neutral": 0, "defensive": -10}[stance]
    cost_mod = {"offensive": 2, "neutral": 0, "defensive": -1}[stance]
    cost = 5 + extra_cost + cost_mod  # Base attack cost 5

    # Roll with mods
    roll = random.randint(1, 100)
    atk = roll + t["weapon_skill"] + (t["dexterity"] // 10) - t["pain"] - t["stress"] + atk_mod

    def_roll = random.randint(1, 100)
    def_type = random.choice(["Dodge", "Parry", "Block"])
    def_mod = (defender["dexterity"] // 10) - defender["pain"] - defender["stress"]
    def_score = def_roll + def_mod
    if def_type == "Block" and defender["shield_equipped"]:
      def_score *= 1.1  # Shield bonus

    hit = atk >= def_score
    if hit:
      dmg_type = weapons[t["weapon"]]["damage_type"]
      absorbed = random.randint(1, defender["armor_specs"][0]["armor_rating"][dmg_type]) if defender["armor_specs"] else 0
      dmg = 14 + extra_dmg - absorbed  # Base dmg 14
      defender["hp"] -= dmg
      defender["pain"] += (dmg / defender["total_hp"]) * 20
      if dmg > 15:  # Trauma trigger
        print("TRAUMA: High damage! Arm broken.")
      if "veil_bound" in classes[t["class"]]["role_tags"] and t["gender"] == "Female":
        t["corruption"] += 5  # Veil risk

      print(f"HIT! Dmg: {dmg} ({absorbed} absorbed). Defender HP: {defender['hp']}, Pain: {defender['pain']:.1f}%")
    else:
      print(f"MISS! {def_type} defense.")

  elif cmd[0] == "status":
    for c in [attacker, defender]:
      print(f"{c['name']} ({c['race']}/{c['gender']}/{c['class']}): HP {c['hp']}/{c['total_hp']}, Pain {c['pain']:.1f}%, Stress {c['stress']}, Corruption {c['corruption']}")
      print(f"  Weapon: {c['weapon']} ({weapons[c['weapon']]['damage_type']}, {c.get('handedness', '1h')})")
      print(f"  Stance: {c['stance']}, Shield: {c['shield_equipped']}, Armor: {c['armor']}\n")

  elif cmd[0] == "test":
    weapon = cmd[1]
    armor_tier = cmd[2]
    runs = int(cmd[3]) if len(cmd) > 3 else 100
    attacker["weapon"] = weapon
    defender["armor"] = [armor_tier]
    hits = dmg_total = trauma = 0
    for _ in range(runs):
      result = engine.attack_roll(attacker, defender, 14)
      if result["hit"]:
        hits += 1
        dmg_total += result["damage"]
        if result["damage"] > 15: trauma += 1
        if "veil_bound" in classes[attacker["class"]]["role_tags"] and attacker["gender"] == "Female":
          attacker["corruption"] += 5

    avg_dmg = dmg_total / hits if hits else 0
    print(f"{runs} tests: {weapon} vs {armor_tier} → Hits {hits}% | Avg Dmg {avg_dmg:.1f} | Trauma {trauma}% | Corruption {attacker['corruption']}\n")

  else:
    print("Unknown. Try: set <type> <value> [target] | attack | status | test <weapon> <armor> <runs> | quit")