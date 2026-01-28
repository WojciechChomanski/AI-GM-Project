import json
import random
import logging
import os
from typing import List, Tuple, Dict
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import dotenv

dotenv.load_dotenv()
app = FastAPI()

# CORS middleware to allow frontend requests
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

# Reliable path to rules folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.join(BASE_DIR, "..", "rules")

def load_json(file_path):
    full_path = os.path.join(RULES_DIR, file_path)
    logging.debug(f"File content for {full_path}: {open(full_path).read()}")
    with open(full_path, "r") as f:
        data = json.load(f)
    logging.debug(f"Loaded from {full_path}")
    return data

class Combatant:
    def __init__(self, data):
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
        self.abilities = data.get("abilities", {})  # Make optional with default {}
        self.skills = data["skills"]
        self.strength = data.get("strength", 10)
        self.dexterity = data.get("dexterity", 10)
        self.weapon_skill = data.get("weapon_skill", 0)
        self.pain = 0
        self.stress = 0
        self.armor_specs = []  # Resolved armor pieces

def resolve_armor_spec(armors_dict, tier: str, race: str | None = None):
    tier_data = armors_dict.get(tier)
    if not tier_data:
        return None
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
            logging.debug(f"Equipped {spec['name']} to {combatant.name}")
            combatant.armor_weight += spec['weight']
            combatant.stamina -= spec['stamina_penalty']
            # Apply mobility (as penalty %)
            mobility_penalty = abs(spec['mobility_bonus']) if spec['mobility_bonus'] < 0 else 0
            logging.info(f"⚠️ {combatant.name}'s {tier} (weight {spec['weight']}) reduces mobility by {mobility_penalty}% and increases stamina costs by {spec['stamina_penalty']}!")

def apply_armor_absorption(base_damage: int, damage_type: str, defender) -> tuple[int, int]:
    absorbed = 0
    remaining = base_damage
    rating_key = damage_type.lower()
    for spec in defender.armor_specs:
        rating = spec.get('armor_rating', {}).get(rating_key, 0)
        if rating <= 0:
            continue
        take = min(rating, remaining)
        absorbed += take
        remaining -= take
        if remaining <= 0:
            break
    return max(remaining, 0), absorbed

def stamina_cost_for_action(attacker, base_cost: int, stance: str) -> int:
    cost = base_cost
    armor_pen = sum(spec.get('stamina_penalty', 0) for spec in attacker.armor_specs)
    cost += armor_pen
    if stance == 'OFFENSIVE':
        cost += 2
    elif stance == 'DEFENSIVE':
        cost = max(0, cost - 1)
    return max(0, cost)

def spend_stamina(actor, amount: int):
    actor.stamina = max(0, actor.stamina - amount)
    logging.info(f"⚡ {actor.name} spends {amount} stamina (now {actor.stamina}/{actor.max_stamina})")

AIMED_ZONES = ["head", "torso", "left_arm", "right_arm", "left_leg", "right_leg"]

def choose_aimed_zone():
    print("Choose zone:", AIMED_ZONES)
    return input("Enter zone: ").strip().lower()

def aimed_hit_penalty(dex: int) -> int:
    return -30 + (dex // 10)

def block_bonus(defender) -> float:
    bonus = 1.0
    if defender.shield_equipped:
        bonus *= 1.10
        iron = defender.abilities.get('iron_wall', {})
        bonus *= (1.0 + iron.get('block_bonus', 0.0))
    return bonus

def d100():
    return random.randint(1, 100)

def choose_target(enemies: List[Combatant]) -> Combatant:
    print("Available targets:")
    for i, enemy in enumerate(enemies, 1):
        print(f"[{i}] {enemy.name} (Pain: {enemy.pain}%, Mobility Penalty: 1%)")
    choice = int(input("Enter target number: ")) - 1
    return enemies[choice] if 0 <= choice < len(enemies) else enemies[0]

def combat_round(player: Combatant, enemies: List[Combatant], round_num: int):
    logging.debug(f"Combat round {round_num} started")
    print(f"🎛️⚔️ Round {round_num} ⚔️🎛️")

    # Player turn
    target = choose_target(enemies)
    print(f"Target: {target.name} (Pain: {target.pain}%, Mobility Penalty: 1%)")
    stance = input("Choose stance: [1] Offensive (boost attack, increase stamina), [2] Neutral (balanced), [3] Defensive (boost defense, lower attack)\nEnter stance (1-3): ")
    stance_map = {"1": "OFFENSIVE", "2": "NEUTRAL", "3": "DEFENSIVE"}
    stance = stance_map.get(stance, "NEUTRAL")
    print(f"⚔️ {player.name} is in {stance} stance")

    attack_type = input("Choose attack type: [1] Normal (spread damage), [2] Aimed (-30 + DEX//10 penalty, single zone)\nEnter attack type (1-2): ")
    zone = None
    if attack_type == "2":
        zone = choose_aimed_zone()

    ability = input(f"Available active abilities: {list(player.abilities.keys())}\nUse ability? (name or none): ").strip().lower()
    use_ability = player.abilities.get(ability) if ability != "none" else None

    # Ability cost if used
    ability_cost = use_ability.get("stamina_cost", 0) if use_ability else 0
    cost = stamina_cost_for_action(player, base_cost=3 + ability_cost, stance=stance)
    spend_stamina(player, cost)

    # Attack roll with weapon skill + dex - pain/stress + stance modifier
    roll = d100()
    pen = aimed_hit_penalty(player.dexterity) if attack_type == "2" else 0
    atk_mod = {"OFFENSIVE": 10, "NEUTRAL": 0, "DEFENSIVE": -10}.get(stance, 0)
    atk = roll + player.weapon_skill + (player.dexterity // 10) - player.stress - player.pain + pen + atk_mod
    print(f"⚔️ {player.name} swings mightily! Rolls {roll} + {player.weapon_skill} (Weapon Skill) + {(player.dexterity // 10)} (Dex) - {player.stress} (Stress) - {player.pain} (Pain) = {atk} to attack!")

    # Defender roll with stance modifier
    def_roll = d100()
    def_type = random.choice(["Parry", "Block", "Dodge"])  # Fixed typo from "BlockBurn"
    def_mod = (target.dexterity // 10) - target.stress - target.pain
    def_mod += {"OFFENSIVE": -10, "NEUTRAL": 0, "DEFENSIVE": 10}.get(stance, 0)
    def_score = def_roll + def_mod
    if def_type == "Block":
        def_score = int(def_score * block_bonus(target))
    print(f"🛡️ {target.name} braces for impact! Rolls {def_roll} to defend! ({def_type})")

    if atk >= def_score:
        base_damage = 14  # Your base sword damage
        if use_ability and use_ability.get("damage_bonus"):
            base_damage += use_ability["damage_bonus"]
        effective, absorbed = apply_armor_absorption(base_damage, "slashing", target)
        logging.debug(f"Player attack - damage={base_damage}, absorbed={absorbed}, effective_damage={effective}")
        target.hp -= effective
        target.pain = min(100, (effective / target.total_hp) * 120)  # Adjusted pain scaling
        print(f"damage: {player.name} deals {effective} to {target.name} ({target.hp}→{target.hp-effective})")
        print(f"⚔️ {player.name}'s {player.weapon} durability: {random.randint(60, 70)}")  # Placeholder
    else:
        print(f"❌ {player.name} misses or {target.name} successfully defends!")

    # Enemy turns (simplified for brevity)
    for enemy in enemies:
        if enemy.hp <= 0:
            print(f"💀 {enemy.name} has fallen!")
            enemies.remove(enemy)
            continue
        enemy_roll = d100() + enemy.weapon_skill + (enemy.dexterity // 10) - enemy.stress - enemy.pain
        player_def = d100() + (player.dexterity // 10) - player.stress - player.pain
        def_type = random.choice(["Parry", "Block", "Dodge"])
        player_def_score = player_def
        if def_type == "Block":
            player_def_score = int(player_def_score * block_bonus(player))
        print(f"⚔️ {enemy.name} lunges fiercely! Rolls {enemy_roll} to attack!")
        print(f"🛡️ {player.name} braces for impact! Rolls {player_def} to defend! ({def_type})")
        if enemy_roll >= player_def_score:
            base_damage = 14  # Enemy damage
            effective, absorbed = apply_armor_absorption(base_damage, "slashing", player)
            player.hp -= effective
            player.pain = min(100, (effective / player.total_hp) * 120)
            print(f"damage: {enemy.name} deals {effective} to {player.name} ({player.hp}→{player.hp-effective})")
            print(f"⚔️ {enemy.name}'s {enemy.weapon} durability: {random.randint(60, 70)}")
        else:
            print(f"❌ {enemy.name} misses or {player.name} successfully defends!")

    if all(e.hp <= 0 for e in enemies):
        print("🏆 Victory! Enemies defeated.")

# Example usage
armors = load_json("armors.json")
player_data = load_json("characters/Torvald.json")
player = Combatant(player_data)
equip_armor(player, armors)
enemy_data = load_json("characters/bandit_leader.json")
enemy = Combatant(enemy_data)
equip_armor(enemy, armors)
enemies = [enemy]

round_num = 1
while player.hp > 0 and any(e.hp > 0 for e in enemies):
    combat_round(player, enemies, round_num)
    round_num += 1

class CombatEngine:
    def attack_roll(self, attacker, defender, weapon_damage):
        # Accept either dicts (raw data) or Combatant objects
        if isinstance(attacker, dict):
            attacker = Combatant(attacker)
            try:
                armors = load_json("armors.json")
            except Exception:
                armors = {}
            equip_armor(attacker, armors)
        if isinstance(defender, dict):
            defender = Combatant(defender)
            try:
                armors = load_json("armors.json")
            except Exception:
                armors = {}
            equip_armor(defender, armors)

        roll = d100()
        atk = roll + attacker.weapon_skill + (attacker.dexterity // 10) - attacker.stress - attacker.pain
        def_roll = d100()
        def_score = def_roll + (defender.dexterity // 10) - defender.stress - defender.pain
        def_type = random.choice(["Parry", "Block", "Dodge"])
        if def_type == "Block":
            def_score = int(def_score * block_bonus(defender))
        if atk >= def_score:
            effective, absorbed = apply_armor_absorption(weapon_damage, "slashing", defender)
            defender.hp -= effective
            defender.pain = min(100, (effective / defender.total_hp) * 120) if defender.total_hp else defender.pain
            return {
                "hit": True,
                "damage": effective,
                "absorbed": absorbed,
                "defender_hp": defender.hp,
                "defender_pain": defender.pain,
                "attack_roll": roll,
                "atk_total": atk,
                "def_roll": def_roll,
                "def_total": def_score,
                "def_type": def_type,
            }
        else:
            return {
                "hit": False,
                "defender_hp": defender.hp,
                "attack_roll": roll,
                "atk_total": atk,
                "def_roll": def_roll,
                "def_total": def_score,
                "def_type": def_type,
            }

engine = CombatEngine()

@app.post("/combat/attack")
def api_attack_roll(data: dict, username: str = Depends(verify_credentials)):
    return engine.attack_roll(data['attacker'], data['defender'], data.get('weapon_damage', 14))