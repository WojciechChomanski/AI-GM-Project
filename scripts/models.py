# file: scripts/main.py

from fetch_data import fetch_player_data, fetch_npc_data
from battle_simulation import simulate_battle
from setup_database import initialize_database

def main():
    print("⚔️ Welcome to the Grimdark Battle Simulator ⚔️\n")

    # Step 1: Initialize database if needed
    initialize_database()

    # Step 2: Fetch Player and NPC data
    player = fetch_player_data(player_id=1)
    npc = fetch_npc_data(npc_id=1)

    # Step 3: Run battle simulation
    simulate_battle(player, npc)

if __name__ == "__main__":
    main()