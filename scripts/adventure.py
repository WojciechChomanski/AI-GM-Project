# file: scripts/adventure.py

import random
import requests
from character_loader import load_character_from_json
from combat_engine import CombatEngine
from combat_health import CombatHealthManager
from healing_system import HealingSystem

class Adventure:
    def __init__(self):
        self.combat = CombatEngine()
        self.healing = HealingSystem()
        self.api_url = "http://127.0.0.1:8000/chat"

    def run_adventure(self, player_name):
        print("⚔️ Welcome to the Grimdark Village Rescue ⚔️\n")

        # Load player and NPCs
        player = load_character_from_json(f"../rules/characters/{player_name}.json")
        wojtek = load_character_from_json("../rules/characters/wojtek.json")
        caldran = load_character_from_json("../rules/characters/Ser_Caldran_Vael.json")
        bandit1 = load_character_from_json("../rules/characters/bandit.json")
        bandit2 = load_character_from_json("../rules/characters/bandit.json")
        bandit_leader = load_character_from_json("../rules/characters/bandit_leader.json")

        player_health = CombatHealthManager(player)
        wojtek_health = CombatHealthManager(wojtek)
        caldran_health = CombatHealthManager(caldran)
        bandit1_health = CombatHealthManager(bandit1)
        bandit2_health = CombatHealthManager(bandit2)
        bandit_leader_health = CombatHealthManager(bandit_leader)

        # Intro: Dialogue with Wojtek
        print("📜 Wojtek, the chronicler, speaks of a village under siege...")
        self.npc_dialogue("wojtek", "Bandits have taken a villager hostage! Will you help?")

        # Encounter 1: Fight two bandits
        print("\n⚔️ You confront two bandits at the village outskirts!")
        self.combat_encounter(player, [bandit1, bandit2], player_health, [bandit1_health, bandit2_health])
        if not player.alive:
            print("💀 You have fallen. The adventure ends.")
            return

        # Heal if alive
        if player.alive:
            self.healing.attempt_bandage(healer=player, target=player, item_name="basic_bandage")

        # Dialogue: Ser Caldran Vael joins
        print("\n📜 Ser Caldran Vael approaches, offering aid...")
        self.npc_dialogue("Ser_Caldran_Vael", "My liege, I shall fight by your side to save the innocent!")

        # Encounter 2: Fight bandit leader
        print("\n⚔️ You storm the bandit camp to face their leader!")
        self.combat_encounter(player, [bandit_leader, caldran], player_health, [bandit_leader_health, caldran_health])
        if not player.alive:
            print("💀 You have fallen. The adventure ends.")
            return

        # Conclusion
        print("\n🏆 The villager is saved! The village hails you as a hero.")
        if player.alive:
            self.healing.attempt_bandage(healer=player, target=player, item_name="basic_bandage")

    def combat_encounter(self, player, opponents, player_health, opponent_healths):
        round_number = 1
        while player.alive and any(opp.alive for opp in opponents):
            print(f"\n🎛️⚔️ Round {round_number} ⚔️🎛️")
            player.in_combat = True
            for opp in opponents:
                opp.in_combat = True

            # Player's turn
            target = random.choice([opp for opp in opponents if opp.alive])
            self.combat.attack_roll(
                attacker=player,
                defender=target,
                weapon_damage=player.weapon["base_damage"],
                damage_type=player.weapon["damage_type"],
                attacker_health=player_health,
                defender_health=[oh for oh, opp in zip(opponent_healths, opponents) if opp == target][0]
            )

            # Opponents' turn
            for opp, opp_health in zip(opponents, opponent_healths):
                if opp.alive:
                    self.combat.attack_roll(
                        attacker=opp,
                        defender=player,
                        weapon_damage=opp.weapon["base_damage"],
                        damage_type=opp.weapon["damage_type"],
                        attacker_health=opp_health,
                        defender_health=player_health
                    )

                    # Ally turn (if Caldran is present)
                    if opp.name == "Ser Caldran Vael" and player.alive:
                        target = random.choice([o for o in opponents if o.alive and o != opp])
                        self.combat.attack_roll(
                            attacker=opp,
                            defender=target,
                            weapon_damage=opp.weapon["base_damage"],
                            damage_type=opp.weapon["damage_type"],
                            attacker_health=opp_health,
                            defender_health=[oh for oh, o in zip(opponent_healths, opponents) if o == target][0]
                        )

            player.in_combat = False
            for opp in opponents:
                opp.in_combat = False
            round_number += 1

    def npc_dialogue(self, npc_name, player_input):
        try:
            payload = {"npc": npc_name, "player_input": player_input}
            response = requests.post(self.api_url, json=payload)
            reply = response.json().get("reply", f"{npc_name} remains silent.")
            print(f"🗣️ {npc_name}: {reply}")
        except Exception as e:
            print(f"⚠️ Error in dialogue: {e}")
            print(f"🗣️ {npc_name}: The world is too dark for words...")

if __name__ == "__main__":
    player_name = input("Choose your character (torvald or lyssa): ").lower()
    adventure = Adventure()
    adventure.run_adventure(player_name)