import json
import random
import logging
import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import dotenv

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
        self.strength = data.get("strength", 10)
        self.dexterity = data.get("dexterity", 10)
        self.weapon_skill = data.get("weapon_skill", 0)
        self.pain = 0
        self.stress = 0
        self.armor_specs = []

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
class CombatEngine:
    def attack_roll(self, attacker_data: dict, defender_data: dict, weapon_damage: int = 14):
        attacker = Combatant(attacker_data)
        defender = Combatant(defender_data)

        try:
            armors = load_json("armors.json")
        except:
            armors = {}
        equip_armor(attacker, armors)
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
            hit = True
        else:
            effective = absorbed = 0
            hit = False

        return {
            "hit": hit,
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

engine = CombatEngine()

@app.post("/combat/attack")
def api_attack_roll(data: dict, username: str = Depends(verify_credentials)):
    return engine.attack_roll(
        data.get('attacker', {}),
        data.get('defender', {}),
        data.get('weapon_damage', 14)
    )

# Simple health check
@app.get("/api/healthz")
def healthz():
    return {"status": "ok", "backend": "combat_engine"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)