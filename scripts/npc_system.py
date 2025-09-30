# file: scripts/npc_system.py
import logging
from character import Character

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class NPCSystem:
    def __init__(self):
        pass

    def interact(self, character: Character, npc_name: str):
        print(f"🗣️ {character.name} interacts with {npc_name}")
        logging.debug(f"Interaction: {character.name} with {npc_name}")
        return True