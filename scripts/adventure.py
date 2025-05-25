# file: scripts/adventure.py

import random
import requests
import logging
from character_loader import load_character_from_json
from combat_engine import CombatEngine
from combat_health import CombatHealthManager
from healing_system import HealingSystem

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Adventure:
    def __init__(self):
        self.combat = CombatEngine()
        self.healing = HealingSystem()
        self.api_url = "http://127.0.0.1:8000/chat"

    def run_adventure(self, player_name):
        logger.info("Starting Grimdark Village Rescue")
        print("⚔️ Welcome to the Grimdark Village Rescue ⚔️\n")

        try:
            player = load_character_from_json(f"../rules/characters/{player_name}.json")
            wojtek = load_character_from_json("../rules/characters/wojtek.json")
            caldran = load_character_from_json("../rules/characters/Ser_Caldran_Vael.json")
            bandit1 = load_character_from_json("../rules/characters/bandit.json")
            bandit2 = load_character_from_json("../rules/characters/bandit.json")
            bandit_leader = load_character_from_json("../rules/characters/bandit_leader.json")
        except Exception as e:
            logger.error(f"Failed to load characters: {e}")
            print(f"❌ Error loading characters: {e}")
            return

        player_health = CombatHealthManager(player)
        wojtek_health = CombatHealthManager(wojtek)
        caldran_health = CombatHealthManager(caldran)
        bandit1_health = CombatHealthManager(bandit1)
        bandit2_health = CombatHealthManager(bandit2)
        bandit_leader_health = CombatHealthManager(bandit_leader)

        if player.reputation >= 50:
            print(f"🏛️ {player.name}'s heroic reputation precedes them! The village offers support.")
            player.progress_stat("charisma", 1)
        elif player.reputation <= -30:
            print(f"🏛️ {player.name}'s dark reputation sows fear! Villagers avoid them.")
            player.stress_level = min(100, player.stress_level + 5)

        print("📜 Wojtek, the chronicler, speaks of a village under siege...")
        self.npc_dialogue("wojtek", "Bandits have taken a villager hostage! Will you help?")

        print("\nOptions: [1] Fight bandits, [2] Persuade bandits (Lyssa), [3] Sneak (Lyssa), [4] Test combat vs. Caldran")
        choice = input("Choose action (1-4): ").strip()
        ambush_bonus = 0
        if choice == "2" and player_name.lower() == "lyssa":
            success = self.attempt_persuasion(player, bandit1)
            if success:
                print("🗣️ Lyssa persuades the bandits to release the hostage!")
                player.reputation = min(100, player.reputation + 10)
                player.progress_stat("charisma", 2)
                return
        elif choice == "3" and player_name.lower() == "lyssa":
            success = self.attempt_sneak(player, bandit1)
            if success:
                print("🕵️ Lyssa sneaks past the bandits and prepares an ambush!")
                ambush_bonus = 10
                player.reputation = min(100, player.reputation + 5)
                player.progress_stat("agility", 1)
        elif choice == "4":
            print("\n⚔️ You challenge Ser Caldran Vael to a duel!")
            self.combat_encounter(player, [caldran], player_health, [caldran_health], 0)
            return

        print("\n⚔️ You confront two bandits at the village outskirts!")
        self.combat_encounter(player, [bandit1, bandit2], player_health, [bandit1_health, bandit2_health], ambush_bonus)
        if not player.alive or player.exhausted:
            print("💀 You have fallen. The adventure ends.")
            player.reputation = max(-100, player.reputation - 5)
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
            player.reputation = max(-100, player.reputation - 10)
            return

        print("\n🏆 The villager is saved! The village hails you as a hero.")
        player.reputation = min(100, player.reputation + 15)
        player.progress_stat("reputation", 15)
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
                print(f"Choose stance for {player.name}: [1] Offensive, [2] Defensive, [3] Neutral")
                stance_choice = input("Choose stance (1-3): ").strip()
                stance_map = {"1": "offensive", "2": "defensive", "3": "neutral"}
                chosen_stance = stance_map.get(stance_choice, "neutral")
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
                try:
                    self.combat.attack_roll(
                        attacker=player,
                        defender=target,
                        weapon_damage=damage,
                        damage_type=player.weapon["damage_type"],
                        attacker_health=player_health,
                        defender_health=[oh for oh, opp in zip(opponent_healths, opponents) if opp == target][0],
                        aimed_zone=aimed_zone,
                        chosen_stance=chosen_stance
                    )
                except Exception as e:
                    logger.error(f"Combat error: {e}")
                    print(f"❌ Combat error: {e}")
                    return
                first_strike = False

            for opp, opp_health in zip(opponents, opponent_healths):
                if opp.alive and not opp.exhausted:
                    try:
                        opp_stance = random.choice(["offensive", "defensive", "neutral"])  # NPCs choose randomly
                        self.combat.attack_roll(
                            attacker=opp,
                            defender=player,
                            weapon_damage=opp.weapon["base_damage"],
                            damage_type=opp.weapon["damage_type"],
                            attacker_health=opp_health,
                            defender_health=player_health,
                            aimed_zone=None,
                            chosen_stance=opp_stance
                        )
                    except Exception as e:
                        logger.error(f"Combat error: {e}")
                        print(f"❌ Combat error: {e}")
                        return

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
            logger.error(f"Dialogue error: {e}")
            print(f"⚠️ Error in dialogue: {e}")
            print(f"🗣️ {npc_name}: The world is too dark for words...")

    def attempt_persuasion(self, player, target):
        roll = random.randint(1, 100)
        charisma_bonus = player.charisma // 5
        difficulty = 30  # Increased difficulty
        total_roll = roll + charisma_bonus
        print(f"🗣️ {player.name} attempts persuasion (needs {difficulty}+): rolled {roll} + {charisma_bonus} (Charisma) = {total_roll}")
        return total_roll >= difficulty

    def attempt_sneak(self, player, target):
        roll = random.randint(1, 100)
        agility_bonus = player.agility // 5
        difficulty = 25  # Increased difficulty
        total_roll = roll + agility_bonus
        print(f"🕵️ {player.name} attempts to sneak (needs {difficulty}+): rolled {roll} + {agility_bonus} (Agility) = {total_roll}")
        return total_roll >= difficulty

if __name__ == "__main__":
    player_name = input("Choose your character (torvald or lyssa): ").lower()
    adventure = Adventure()
    try:
        adventure.run_adventure(player_name)
    except Exception as e:
        logger.error(f"Adventure failed: {e}")
        print(f"❌ Adventure failed: {e}")