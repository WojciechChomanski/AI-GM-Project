import random
import logging
from character import Character

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class EnemySpawner:
    def __init__(self):
        self.enemies = {
            "veilspawn_leviathan": {
                "name": "Veilspawn Leviathan",
                "hp": 50,
                "stamina": 100,
                "stats": {"strength": 55, "toughness": 40, "agility": 20},
                "abilities": {"stun_slam": {"damage": 20, "stun_chance": 0.5, "flood_terrain": 0.5}},
                "description": "A low-HP, high-stun sea beast summoned by Daughters of the Drowned Moon."
            },
            "drowned_thrall": {
                "name": "Drowned Thrall",
                "hp": 30,
                "stamina": 50,
                "stats": {"strength": 30, "toughness": 30, "agility": 15},
                "abilities": {"brine_grasp": {"damage": 10, "bleed": 1}},
                "description": "A drowned minion serving the Drowned Matron."
            },
            "clockwork_golem": {
                "name": "Clockwork Golem",
                "hp": 80,
                "stamina": 150,
                "stats": {"strength": 45, "toughness": 55, "agility": 10},
                "abilities": {"iron_smash": {"damage": 15, "armor_bonus": 10}},
                "description": "A rune-forged construct of the Iron Covenant, high armor, blunt damage."
            }
        }

    def spawn_enemy(self, enemy_name, count=1):
        enemy_template = self.enemies.get(enemy_name)
        if not enemy_template:
            print(f"❌ Unknown enemy: {enemy_name}")
            return []
        enemies = []
        for _ in range(count):
            enemy = Character()
            enemy.name = enemy_template["name"]
            enemy.total_hp = enemy_template["hp"]
            enemy.health = enemy.total_hp
            enemy.max_stamina = enemy_template["stamina"]
            enemy.stamina = enemy.max_stamina
            for stat, value in enemy_template["stats"].items():
                setattr(enemy, stat, value)
            enemy.abilities = enemy_template["abilities"]
            enemies.append(enemy)
            print(f"🩸 Spawned {enemy.name}!")
        return enemies