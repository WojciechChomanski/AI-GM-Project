import json
import random
import logging
import os
from character_loader import CharacterLoader
from combat_engine import CombatEngine
from combat_health import CombatHealthManager
from healing_system import HealingSystem
from armors import Armor
import stance_logic
import requests

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Adventure:
    def __init__(self):
        self.combat = CombatEngine()
        self.healing = HealingSystem()
        self.api_url = "http://127.0.0.1:8000/chat"
        self.opponent_names = {}
        self.grapple_flags = {}  # Add this

    def assign_opponent_name(self, opponent, index):
        if opponent.name not in self.opponent_names:
            self.opponent_names[opponent.name] = f"{opponent.name} {index + 1}"
        return self.opponent_names[opponent.name]

    def load_armor_for_character(self, character):
        if not hasattr(character, 'armor') or character.armor is None:
            character.armor = []

    def run_adventure(self, player_name):
        logger.info("Starting Grimdark Village Rescue")
        print("⚔️ Welcome to the Grimdark Village Rescue ⚔️\n")

        base_dir = os.path.abspath("../rules/characters")
        loader = CharacterLoader()
        try:
            print("Debug: Loading characters")
            player = loader.load_character_from_json(os.path.join(base_dir, f"{player_name}.json"))
            wojtek = loader.load_character_from_json(os.path.join(base_dir, "wojtek.json"))
            caldran = loader.load_character_from_json(os.path.join(base_dir, "Ser_Caldran_Vael.json"))
            bandit1 = loader.load_character_from_json(os.path.join(base_dir, "bandit.json"))
            bandit2 = loader.load_character_from_json(os.path.join(base_dir, "bandit.json"))
            bandit_leader = loader.load_character_from_json(os.path.join(base_dir, "bandit_leader.json"))
            for char in [player, wojtek, caldran, bandit1, bandit2, bandit_leader]:
                self.load_armor_for_character(char)
            print("Debug: Characters loaded")
        except Exception as e:
            logger.error(f"Failed to load characters: {e}")
            print(f"❌ Error loading characters: {e}")
            return

        # Load abilities for player if applicable
        class_data = self.load_classes(player.class_name)
        player.abilities = class_data.get("abilities", {})

        player_health = CombatHealthManager(player)
        wojtek_health = CombatHealthManager(wojtek)
        caldran_health = CombatHealthManager(caldran)
        bandit1_health = CombatHealthManager(bandit1)
        bandit2_health = CombatHealthManager(bandit2)
        bandit_leader_health = CombatHealthManager(bandit_leader)

        if player.background in ["Street_Whore", "High_End_Escort"] and (player.gender != "Female" or player.race != "Human"):
            print(f"❌ {player.name}'s background {player.background} requires Female Human!")
            return
        if player.class_name == "Mage" and (player.gender != "Female" or player.race != "Human"):
            print(f"❌ {player.name}'s class {player.class_name} requires Female Human!")
            return

        if player.reputation >= 50:
            print(f"🏛️ {player.name}'s heroic reputation precedes them! The village offers support.")
            player.progress_stat("charisma", 1)
        elif player.reputation <= -30:
            print(f"🏛️ {player.name}'s dark reputation sows fear! Villagers avoid them.")
            player.stress_level = min(100, player.stress_level + 5)

        print("📜 Wojtek, the chronicler, speaks of a village under siege...")
        self.npc_dialogue("wojtek", "Bandits have taken a villager hostage! Will you help?")

        print("\nOptions: [1] Fight bandits, [2] Persuade bandits (Lyssa, Ada), [3] Sneak (Lyssa, Ada), [4] Test combat vs. Caldran")
        print("Debug: Before input prompt")
        choice = input("Choose action (1-4): ").strip()
        print("Debug: After input prompt, choice = ", choice)
        ambush_bonus = 0
        if choice == "2" and player_name.lower() in ["lyssa", "ada"]:
            success = self.attempt_persuasion(player, bandit1)
            if success:
                print(f"🗣️ {player.name} persuades the bandits to release the hostage!")
                player.reputation = min(100, player.reputation + 10)
                player.progress_stat("charisma", 2)
                return
        elif choice == "3" and player_name.lower() in ["lyssa", "ada"]:
            success = self.attempt_sneak(player, bandit1)
            if success:
                print(f"🕵️ {player.name} sneaks past the bandits and prepares an ambush!")
                ambush_bonus = 10
                player.reputation = min(100, player.reputation + 5)
                player.progress_stat("agility", 1)
        elif choice == "4":
            print("\n⚔️ You challenge Ser Caldran Vael to a duel!")
            self.combat_encounter(player, [caldran], player_health, [caldran_health], 0)
            return

        print("\n⚔️ You confront two bandits at the village outskirts!")
        print("Debug: Entering combat encounter")
        athletics_success = player.athletics_check(30)
        bandit_ambush_bonus = 0 if athletics_success else 10
        if not athletics_success:
            print(f"⚠️ {player.name} fails to spot the bandits! They gain an ambush advantage (+10 attack in Round 1).")
        self.combat_encounter(player, [bandit1, bandit2], player_health, [bandit1_health, bandit2_health], bandit_ambush_bonus)
        if not player.alive or player.exhausted:
            print("💀 You have fallen. The adventure ends.")
            player.reputation = max(-100, player.reputation - 5)
            return

        if player.alive:
            print("\n🩹 Attempting to bandage wounds...")
            self.healing.attempt_bandage(healer=player, target=player)
            player.short_rest()
            print("\n⏳ Taking a brief rest to regain strength...")
            self.log_armor_status(player)

        print("\n📜 Ser Caldran Vael approaches, offering aid...")
        self.npc_dialogue("Ser_Caldran_Vael", "My liege, I shall fight by your side to save the innocent!")

        print("\n⚔️ You storm the bandit camp to face their leader!")
        print("Debug: Entering leader combat encounter")
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
            self.log_armor_status(player)

    def load_classes(self, class_name):
        path = os.path.join(os.path.dirname(__file__), "../rules/classes.json")
        with open(path, 'r', encoding='utf-8') as f:
            classes_data = json.load(f)
        return classes_data.get(class_name, {"abilities": {}})

    def log_armor_status(self, character):
        for armor in character.armor:
            print(f"\n🛡️ {armor.name} Status:")
            for part in armor.coverage:
                current = armor.current_durability.get(part, 0)
                max_repairable = armor.max_repairable_durability.get(part, armor.max_durability // len(armor.coverage))
                if current < max_repairable:
                    print(f"  - {part.replace('_', ' ')}: {current}/{max_repairable} durability (needs repair)")
                elif current == 0:
                    print(f"  - {part.replace('_', ' ')}: Broken (needs repair)")
                else:
                    print(f"  - {part.replace('_', ' ')}: {current}/{max_repairable} durability (intact)")

    def combat_encounter(self, player, opponents, player_health, opponent_healths, ambush_bonus):
        round_number = 1
        first_strike = True
        self.opponent_names = {}
        for opp in opponents:
            opp.last_action = False  # Initialize
        while player.alive and not player.exhausted and any(opp.alive and not opp.exhausted for opp in opponents):
            print(f"\n🎛️⚔️ Round {round_number} ⚔️🎛️")
            print(f"Debug: Combat round {round_number} started")
            player.in_combat = True
            for opp in opponents:
                if opp.alive and not opp.exhausted:
                    opp.in_combat = True
                    opp.last_action = False  # Reset per round

            if player.alive and not player.exhausted:
                valid_targets = [opp for opp in opponents if opp.alive and not opp.exhausted]
                if not valid_targets:
                    break
                target = random.choice(valid_targets)
                target_health = [oh for oh, opp in zip(opponent_healths, opponents) if opp == target][0]
                target_name = self.assign_opponent_name(target, opponents.index(target))
                print(f"\nTarget: {target_name} (Pain: {target.pain_penalty}%, Mobility Penalty: {target.mobility_penalty}%)")

                # Prompt for stance selection
                print("Choose stance: [1] Offensive (boost attack, increase stamina), [2] Neutral (balanced), [3] Defensive (boost defense, lower attack)")
                stance_choice = input("Enter stance (1-3): ").strip()
                if stance_choice not in ["1", "2", "3"]:
                    stance_choice = "1"  # Default
                chosen_stance = {"1": "offensive", "2": "neutral", "3": "defensive"}[stance_choice]
                print(f"Debug: Chosen stance = {chosen_stance}")

                # Prompt for attack type
                print("Choose attack type: [1] Normal (spread damage), [2] Aimed (-30 + DEX//10 penalty, single zone)")
                attack_choice = input("Enter attack type (1-2): ").strip()
                if attack_choice not in ["1", "2"]:
                    attack_choice = "1"  # Default
                aimed_zone = None
                if attack_choice == "2":
                    print("Available body zones: " + ", ".join(player.body_parts.keys()))
                    aimed_zone = input("Enter target zone: ").strip().lower()
                    if aimed_zone not in player.body_parts:
                        print(f"⚠️ Invalid zone {aimed_zone}, defaulting to normal attack.")
                        aimed_zone = None

                # New: Prompt for abilities
                print("Available active abilities: grab_rip, heavy_throw")
                ability = input("Use ability? (name or none): ").lower().strip('.')
                roll_penalty = 0  # Reset roll_penalty
                weapon_damage = player.weapon.get("base_damage", 10) + (player.strength // 10)  # Define here for grapple
                if ability == "grab_rip":
                    grab_roll = random.randint(1, 100) + player.strength // 8 + player.dexterity // 5  # Ogre ~70% success
                    dodge_roll = random.randint(1, 100) + target.agility // 5
                    print(f"Grab roll: {grab_roll} vs Dodge: {dodge_roll}")
                    if grab_roll > dodge_roll:
                        print(f"🔗 {player.name} grabs {target.name} in a vise grip!")
                        player.grapple_committed = True
                        self.grapple_flags[target.name] = player.name  # Use Adventure's grapple_flags
                        player.consume_stamina(10)  # Lowered for ogre racial trait
                        # Immediate follow-up prompt
                        grapple_choice = input("Rip apart, smash ground, use as club, or release? ").lower().strip('.')
                        if grapple_choice == "rip apart":
                            aimed_zone = input("Enter target zone for rip (e.g., left_upper_arm): ").strip().lower()
                            rip_roll = random.randint(1, 100) + player.strength // 5
                            resist_roll = random.randint(1, 100) + target.toughness // 5
                            # Easier rip on limbs
                            limb_zones = ["left_lower_leg", "right_lower_leg", "left_upper_leg", "right_upper_leg", "left_lower_arm", "right_lower_arm", "left_upper_arm", "right_upper_arm"]
                            if aimed_zone in limb_zones:
                                rip_roll += 10  # Bonus for limbs
                            elif aimed_zone == "head":
                                resist_roll += 10  # Harder for head
                            print(f"Rip roll: {rip_roll} vs Resist: {resist_roll}")
                            if rip_roll > resist_roll:
                                print(f"💥 {player.name} rips {target.name}'s {aimed_zone}—horrific tear! 🩸 Gore sprays as the limb is torn off!")
                                target_health.take_damage_to_zone(aimed_zone, 35, "slashing", critical=True)  # Full damage to one zone
                                target.bleeding_rate += 2.4
                                target.pain_penalty += 15
                                target.mobility_penalty += 25
                                target_health.recalculate_penalties()  # Immediate penalty update
                                if player.class_name == "Ogre Ravager":
                                    player.health += 15  # Flesh Rend heal
                                    player.corruption_level = min(100, player.corruption_level + 5)
                                    print(f"🩸 Rock devours the flesh, healing 15 health! Corruption rises to {player.corruption_level}%.")
                            else:
                                print(f"❌ {target.name} resists the rip—slips free!")
                        elif grapple_choice == "smash ground":
                            smash_damage = weapon_damage + 10  # Blunt + stun
                            target_health.distribute_damage(smash_damage, "blunt")
                            if random.random() < 0.5:
                                target.stunned = True
                                print(f"😵 {target.name} dazed from smash! Skip next turn.")
                                target.skip_turn = True  # Add stun effect (skip turn)
                        elif grapple_choice == "use as club":
                            if len(opponents) > 1:
                                other_target = random.choice([opp for opp in opponents if opp != target])
                                print(f"🌀 {player.name} swings {target.name} as a club at {other_target.name}!")
                                other_target_health = CombatHealthManager(other_target)
                                other_target_health.distribute_damage(weapon_damage, "blunt")
                                target_health.distribute_damage(10, "blunt")  # Damage to grappled too
                            else:
                                print(f"❌ No other foes—smash ground instead!")
                                smash_damage = weapon_damage + 10
                                target_health.distribute_damage(smash_damage, "blunt")
                        else:
                            print(f"🛑 {player.name} releases the grapple!")
                        player.grapple_committed = False
                        self.grapple_flags.pop(target.name, None)
                    else:
                        print(f"❌ {target.name} slips free from {player.name}'s grasp!")
                        player.consume_stamina(5)
                    # Remove continue here to let round proceed
                elif ability == "heavy_throw":
                    weapon_damage += player.mass // 10 + player.strength // 5
                    roll_penalty += 20  # Accuracy penalty for throw
                    player.consume_stamina(20)
                    if aimed_zone == "head" and random.random() < 0.5:
                        print(f"😵 {target.name} is stunned!")
                        target.stunned = True

                action_choice = "1"  # Default attack
                damage = player.weapon.get("base_damage", 10) + (player.strength // 10)
                absorbed = 0
                for armor in target.armor:  # Fixed to target.armor
                    if aimed_zone in armor.coverage:
                        absorbed += armor.absorb_damage(damage, player.weapon.get("damage_type", "slashing"), aimed_zone)
                effective_damage = max(0, damage - absorbed)
                print(f"Debug: Player attack - damage={damage}, absorbed={absorbed}, effective_damage={effective_damage}")
                try:
                    self.combat.attack_roll(
                        attacker=player,
                        defender=target,
                        weapon_damage=effective_damage,
                        damage_type=player.weapon.get("damage_type", "slashing"),
                        attacker_health=player_health,
                        defender_health=target_health,
                        aimed_zone=aimed_zone,
                        chosen_stance=chosen_stance,
                        ambush_bonus=ambush_bonus if first_strike else 0,
                        roll_penalty=roll_penalty
                    )
                except Exception as e:
                    logger.error(f"Combat error: {e}")
                    print(f"❌ Combat error: {e}")
                    break

                first_strike = False

            for idx, (opp, opp_health) in enumerate(zip(opponents, opponent_healths)):
                if opp.alive and not opp.exhausted and not opp.last_action:
                    opp_name = self.assign_opponent_name(opp, idx)
                    damage = opp.weapon.get("base_damage", 10) + (opp.strength // 10)
                    absorbed = 0
                    for armor in player.armor:
                        if aimed_zone in armor.coverage:
                            absorbed += armor.absorb_damage(damage, opp.weapon.get("damage_type", "slashing"), aimed_zone)
                    effective_damage = max(0, damage - absorbed)
                    print(f"Debug: Opponent {opp_name} attack - damage={damage}, absorbed={absorbed}, effective_damage={effective_damage}")
                    try:
                        opp_stance = random.choice(["offensive", "defensive", "neutral"])
                        opp_ambush_bonus = ambush_bonus if round_number == 1 and first_strike else 0
                        self.combat.attack_roll(
                            attacker=opp,
                            defender=player,
                            weapon_damage=effective_damage,
                            damage_type=opp.weapon.get("damage_type", "slashing"),
                            attacker_health=opp_health,
                            defender_health=player_health,
                            aimed_zone=None,
                            chosen_stance=opp_stance,
                            ambush_bonus=opp_ambush_bonus
                        )
                    except Exception as e:
                        logger.error(f"Combat error: {e}")
                        print(f"❌ Combat error: {e}")
                        continue
                    opp.last_action = True

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
        charisma_bonus = player.charisma // 5 if hasattr(player, 'charisma') else 0
        pain_penalty = min(player.pain_penalty, 20)
        difficulty = 30
        total_roll = roll + charisma_bonus - pain_penalty
        print(f"🗣️ {player.name} attempts persuasion (needs {difficulty}+): rolled {roll} + {charisma_bonus} (Charisma) - {pain_penalty} (Pain) = {total_roll}")
        return total_roll >= difficulty

    def attempt_sneak(self, player, target):
        roll = random.randint(1, 100)
        agility_bonus = player.agility // 5 if hasattr(player, 'agility') else 0
        pain_penalty = min(player.pain_penalty, 20)
        difficulty = 25
        total_roll = roll + agility_bonus - pain_penalty
        print(f"🕵️ {player.name} attempts to sneak (needs {difficulty}+): rolled {roll} + {agility_bonus} (Agility) - {pain_penalty} (Pain) = {total_roll}")
        return total_roll >= difficulty

if __name__ == "__main__":
    valid_chars = ["torvald", "lyssa", "ada", "brock", "rock"]
    player_name = input("Choose your character (torvald, lyssa, ada, brock, rock): ").lower()
    if player_name not in valid_chars:
        print("❌ Invalid character!")
        exit()
    adventure = Adventure()
    try:
        adventure.run_adventure(player_name)
    except Exception as e:
        logger.error(f"Adventure failed: {e}")
        print(f"❌ Adventure failed: {e}")