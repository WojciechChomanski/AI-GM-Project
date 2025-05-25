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

        print("📜 Wojtek, the chronicler, speaks of a village under siege...")
        self.npc_dialogue("wojtek", "Bandits have taken a villager hostage! Will you help?")

        print("\n⚔️ You confront two bandits at the village outskirts!")
        print("Options: [1] Fight, [2] Persuade, [3] Sneak")
        choice = input("Choose action (1-3): ").strip()
        ambush_bonus = 0
        if choice == "2" and player_name.lower() == "lyssa":
            success = self.attempt_persuasion(player, bandit1)
            if success:
                print("🗣️ Lyssa persuades the bandits to release the hostage!")
                return
        elif choice == "3" and player_name.lower() == "lyssa":
            success = self.attempt_sneak(player, bandit1)
            if success:
                print("🕵️ Lyssa sneaks past the bandits and prepares an ambush!")
                ambush_bonus = 10  # Bonus damage on first strike
        self.combat_encounter(player, [bandit1, bandit2], player_health, [bandit1_health, bandit2_health], ambush_bonus)
        if not player.alive or player.exhausted:
            print("💀 You have fallen. The adventure ends.")
            return

        if player.alive:
            print("\n🩹 Attempting to bandage wounds...")
            self.healing.attempt_bandage(healer=player, target=player)
            player.short_rest()
            print("\n⏳ Taking a brief rest to regain strength...")

        print("\n📜 Ser Caldran Vael approaches, offering aid...")
        self.npc_dialogue("Ser_Caldran_Vael", "My liege, I shall fight by your side to save the innocent!")

        print("\n⚔️ You storm the bandit camp to face their leader!")
        self.combat_encounter(player, [bandit_leader], player_health, [bandit_leader_health], 0)
        if not player.alive or player.exhausted:
            print("💀 You have fallen. The adventure ends.")
            return

        print("\n🏆 The villager is saved! The village hails you as a hero.")
        if player.alive:
            print("\n🩹 Final bandaging and rest...")
            self.healing.attempt_bandage(healer=player, target=player)
            player.long_rest()

    def combat_encounter(self, player, opponents, player_health, opponent_healths, ambush_bonus=0):
        round_number = 1
        first_strike = True
        while player.alive and not player.exhausted and any(opp.alive and not opp.exhausted for opp in opponents):
            print(f"\n🎛️⚔️ Round {round_number} ⚔️🎛️")
            player.in_combat = True
            for opp in opponents:
                opp.in_combat = True

            if player.alive and not player.exhausted:
                target = random.choice([opp for opp in opponents if opp.alive and not opp.exhausted])
                print(f"\nOpponent Status ({target.name}): Pain Penalty: {target.pain_penalty}%, Mobility Penalty: {target.mobility_penalty}%")
                print(f"Options for {player.name}: [1] Attack, [2] Aimed Strike")
                action = input("Choose action (1-2): ").strip()
                aimed_zone = None
                if action == "2":
                    print("Available zones: left_lower_leg, right_lower_leg, left_upper_leg, right_upper_leg, stomach, chest, left_lower_arm, right_lower_arm, left_upper_arm, right_upper_arm, head, throat, groin")
                    aimed_zone = input("Choose target zone: ").strip().lower()
                    if aimed_zone not in player.body_parts:
                        print(f"⚠️ Invalid zone: {aimed_zone}. Using normal attack.")
                        aimed_zone = None
                damage = player.weapon["base_damage"]
                if first_strike and ambush_bonus > 0:
                    damage += ambush_bonus
                    print(f"🗡️ {player.name} ambushes with +{ambush_bonus} damage!")
                self.combat.attack_roll(
                    attacker=player,
                    defender=target,
                    weapon_damage=damage,
                    damage_type=player.weapon["damage_type"],
                    attacker_health=player_health,
                    defender_health=[oh for oh, opp in zip(opponent_healths, opponents) if opp == target][0],
                    aimed_zone=aimed_zone
                )
                first_strike = False

            for opp, opp_health in zip(opponents, opponent_healths):
                if opp.alive and not opp.exhausted:
                    self.combat.attack_roll(
                        attacker=opp,
                        defender=player,
                        weapon_damage=opp.weapon["base_damage"],
                        damage_type=opp.weapon["damage_type"],
                        attacker_health=opp_health,
                        defender_health=player_health,
                        aimed_zone=None
                    )

            player_health.bleed_out()
            for opp_health in opponent_healths:
                opp_health.bleed_out()

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

    def attempt_persuasion(self, player, target):
        roll = random.randint(1, 100)
        charisma_bonus = getattr(player, "charisma_modifier", 0) * 5
        difficulty = 25  # Easier for Lyssa
        total_roll = roll + charisma_bonus
        print(f"🗣️ {player.name} attempts persuasion (needs {difficulty}+): rolled {total_roll}")
        return total_roll >= difficulty

    def attempt_sneak(self, player, target):
        roll = random.randint(1, 100)
        agility_bonus = getattr(player, "agility_modifier", 0) * 5
        difficulty = 20  # Easier for rogues
        total_roll = roll + agility_bonus
        print(f"🕵️ {player.name} attempts to sneak (needs {difficulty}+): rolled {total_roll}")
        return total_roll >= difficulty