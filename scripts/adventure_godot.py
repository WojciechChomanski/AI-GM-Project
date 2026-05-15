import sys
import random
import logging
from character_loader import CharacterLoader
from combat_engine import CombatEngine
from combat_health import CombatHealthManager
from healing_system import HealingSystem
from chat_api import ChatAPIClient
from damage_consequences import DamageConsequences
from fear_system import FearSystem

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdventureGodot:
    def __init__(self):
        self.combat = CombatEngine()
        self.healing = HealingSystem()
        self.chat_api = ChatAPIClient()
        self.damage_consequences = DamageConsequences()
        self.fear_system = FearSystem()
        self.opponent_names = {}
        self.characters = {
            "torvald": CharacterLoader.load_character("torvald"),
            "lyssa": CharacterLoader.load_character("lyssa"),
            "ada": CharacterLoader.load_character("ada"),
            "brock": CharacterLoader.load_character("brock"),
            "rock": CharacterLoader.load_character("rock")
        }
        self.bandits = [
            CharacterLoader.load_character("bandit"),
            CharacterLoader.load_character("bandit")
        ]
        self.bandit_leader = CharacterLoader.load_character("bandit_leader")
        self.npcs = {
            "wojtek": CharacterLoader.load_character("wojtek"),
            "ser_caldran_vael": CharacterLoader.load_character("ser_caldran_vael")
        }

    def assign_opponent_name(self, opponent, index):
        if opponent.name not in self.opponent_names:
            self.opponent_names[opponent.name] = f"{opponent.name} {index + 1}"
        return self.opponent_names[opponent.name]

    def run_adventure(self, player_name):
        output = []
        def log(msg):
            print(msg)
            output.append(msg)

        log("⚔️ Grimdark Village Rescue ⚔️\n")

        if player_name.lower() not in self.characters:
            log("❌ Invalid character!")
            return "\n".join(output)

        player = self.characters[player_name.lower()]
        player_health = CombatHealthManager(player)
        wojtek = self.npcs["wojtek"]
        caldran = self.npcs["ser_caldran_vael"]
        wojtek_health = CombatHealthManager(wojtek)
        caldran_health = CombatHealthManager(caldran)

        for character in [player, wojtek, caldran]:
            if character.armor:
                weight = sum(armor.weight for armor in character.armor)
                mobility_penalty = weight // 10
                stamina_penalty = weight // 20
                log(f"⚠️ {character.name}'s {character.armor[0].name} (weight {weight}) reduces mobility by {mobility_penalty}% and increases stamina costs by {stamina_penalty}!")

        for bandit in self.bandits + [self.bandit_leader]:
            if bandit.armor:
                weight = sum(armor.weight for armor in bandit.armor)
                log(f"🛡️ {bandit.name}'s {bandit.armor[0].name} (weight {weight}) has minimal impact on mobility and stamina.")

        if player.reputation >= 50:
            log(f"🏛️ {player.name}'s heroic reputation precedes them! The village offers support.")
            player.progress_stat("charisma", 1)
        elif player.reputation <= -30:
            log(f"🏛️ {player.name}'s dark reputation sows fear! Villagers avoid them.")
            player.stress_level = min(100, player.stress_level + 5)

        log("📜 Wojtek speaks of a village under siege...")
        response = self.chat_api.get_response("wojtek", "Bandits have taken a villager hostage! Will you help?")
        log(f"🗣️ wojtek: {response}\n")

        log("⚔️ Confronting bandits at the village outskirts!")
        athletics_success = player.athletics_check(30)
        bandit_ambush_bonus = 0 if athletics_success else 10
        if not athletics_success:
            log(f"⚠️ {player.name} fails to spot the bandits! They gain an ambush advantage (+10 attack in Round 1).")
        self.combat_encounter(player, self.bandits, player_health, [CombatHealthManager(b) for b in self.bandits], bandit_ambush_bonus, log)
        if not player.alive or player.exhausted:
            log("💀 You have fallen. The adventure ends.")
            player.reputation = max(-100, player.reputation - 5)
            return "\n".join(output)

        if player.alive:
            log("\n🩹 Attempting to bandage wounds...")
            self.healing.attempt_bandage(healer=player, target=player)
            player.short_rest()
            log("\n⏳ Taking a brief rest to regain strength...")
            self.log_armor_status(player, log)

        log("\n📜 Ser Caldran Vael approaches, offering aid...")
        response = self.chat_api.get_response("ser_caldran_vael", "My liege, I shall fight by your side to save the innocent!")
        log(f"🗣️ ser_caldran_vael: {response}\n")

        log("⚔️ Storming the bandit camp to face their leader!")
        bandit_leader_health = CombatHealthManager(self.bandit_leader)
        self.combat_encounter(player, [self.bandit_leader], player_health, [bandit_leader_health], 0, log)
        if not player.alive or player.exhausted:
            log("💀 You have fallen. The adventure ends.")
            player.reputation = max(-100, player.reputation - 10)
            return "\n".join(output)

        log("\n🏆 The villager is saved! The village hails you as a hero.")
        player.reputation = min(100, player.reputation + 15)
        player.progress_stat("reputation", 15)
        if player.alive:
            log("\n🩹 Final bandaging and rest...")
            self.healing.attempt_bandage(healer=player, target=player)
            player.long_rest()
            self.log_armor_status(player, log)

        return "\n".join(output)

    def log_armor_status(self, character, log):
        for armor in character.armor:
            log(f"\n🛡️ {armor.name} Status:")
            for part in armor.coverage:
                current = armor.current_durability.get(part, 0)
                max_repairable = armor.max_repairable_durability.get(part, 9)
                if current < max_repairable:
                    log(f"  - {part.replace('_', ' ')}: {current}/{max_repairable} durability (needs repair)")
                elif current == 0:
                    log(f"  - {part.replace('_', ' ')}: Broken (needs repair)")
                else:
                    log(f"  - {part.replace('_', ' ')}: {current}/{max_repairable} durability (intact)")

    def combat_encounter(self, player, opponents, player_health, opponent_healths, ambush_bonus, log):
        round_number = 1
        first_strike = True
        self.opponent_names = {}
        while player.alive and not player.exhausted and any(opp.alive and not opp_health.exhausted for opp_health, opp in zip(opponent_healths, opponents)):
            log(f"\n🎛️⚔️ Round {round_number} ⚔️🎛️")
            player.in_combat = True
            for opp in opponents:
                if opp.alive and not opp_health.exhausted:
                    opp.in_combat = True

            if player.alive and not player.exhausted:
                valid_targets = [opp for opp, opp_health in zip(opponents, opponent_healths) if opp.alive and not opp_health.exhausted]
                if not valid_targets:
                    break
                target = random.choice(valid_targets)
                target_health = [oh for oh, opp in zip(opponent_healths, opponents) if opp == target][0]
                target_name = self.assign_opponent_name(target, opponents.index(target))
                log(f"\nTarget: {target_name} (Pain: {target.pain_penalty}%, Mobility Penalty: {(target.armor_weight // 10)}%)")
                chosen_stance = "offensive"  # Default, UI will override
                ability = None
                action_choice = "1"  # Default attack
                aimed_zone = None
                damage = 15
                fear_response = self.fear_system.check_fear(target, {"name": player.weapon["name"], "fear_trigger": player.weapon.get("fear_trigger", False), "fear_intensity": player.weapon.get("fear_intensity", 0)})
                if fear_response["triggered"]:
                    log(f"😱 {target.name} fears {player.weapon['name']}! {fear_response['outburst']}")
                    player_health.apply_status_effect("Fear", 2)
                    player.pain_penalty += fear_response["roll_penalty"]
                try:
                    outcome = self.combat.attack_roll(
                        attacker=player,
                        defender=target,
                        weapon_damage=damage,
                        damage_type="slashing",
                        attacker_health=player_health,
                        defender_health=target_health,
                        aimed_zone=aimed_zone,
                        chosen_stance=chosen_stance,
                        ambush_bonus=ambush_bonus if first_strike else 0,
                        ability=ability
                    )
                except Exception as e:
                    logger.error(f"Combat error: {e}")
                    log(f"❌ Combat error: {e}")
                    continue
                first_strike = False

            for idx, (opp, opp_health) in enumerate(zip(opponents, opponent_healths)):
                if opp.alive and not opp_health.exhausted and not opp.last_action:
                    opp_name = self.assign_opponent_name(opp, idx)
                    fear_response = self.fear_system.check_fear(player, {"name": opp.weapon["name"], "fear_trigger": opp.weapon.get("fear_trigger", False), "fear_intensity": opp.weapon.get("fear_intensity", 0)})
                    if fear_response["triggered"]:
                        log(f"😱 {player.name} fears {opp.weapon['name']}! {fear_response['outburst']}")
                        player_health.apply_status_effect("Fear", 2)
                        player.pain_penalty += fear_response["roll_penalty"]
                    try:
                        opp_stance = random.choice(["offensive", "defensive", "neutral"])
                        opp_ambush_bonus = ambush_bonus if round_number == 1 and first_strike else 0
                        outcome = self.combat.attack_roll(
                            attacker=opp,
                            defender=player,
                            weapon_damage=15,
                            damage_type="slashing",
                            attacker_health=opp_health,
                            defender_health=player_health,
                            aimed_zone=None,
                            chosen_stance=opp_stance,
                            ambush_bonus=opp_ambush_bonus
                        )
                    except Exception as e:
                        logger.error(f"Combat error: {e}")
                        log(f"❌ Combat error: {e}")
                        continue

            player_health.bleed_out()
            for opp_health in opponent_healths:
                opp_health.bleed_out()
                opp_health.update_status_effects()

            player.in_combat = False
            for opp in opponents:
                opp.in_combat = False
            round_number += 1

if __name__ == "__main__":
    player_name = sys.argv[1] if len(sys.argv) > 1 else "torvald"
    adventure = AdventureGodot()
    print(adventure.run_adventure(player_name))