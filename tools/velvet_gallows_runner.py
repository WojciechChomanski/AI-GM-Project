import json, os, sys, random, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "rules"
CHARS = RULES / "characters"
ENCOUNTERS = RULES / "encounters"
SIM = ROOT / "scripts" / "battle_simulation.py"

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    print("=== Velvet Gallows: Encounter Runner (no code changes) ===")
    enc_path = ENCOUNTERS / "velvet_gallows.json"
    if not enc_path.exists():
        print(f"[!] Missing file: {enc_path}")
        print("    Make sure rules/encounters/velvet_gallows.json exists.")
        sys.exit(1)

    enc = load_json(enc_path)
    files = {a["ref"]: CHARS / a["file"] for a in enc.get("actors", [])}

    # Require at least player and leader to proceed
    for r in ["player", "leader"]:
        if r not in files or not files[r].exists():
            print(f"[!] Missing actor file for '{r}': {files.get(r)}")
            sys.exit(1)

    player = load_json(files["player"])
    leader = load_json(files["leader"])

    print(f"[i] Location: {enc.get('location')}")
    print(f"[i] Player: {player.get('name','player')}  Charisma={player.get('charisma','?')}")
    print(f"[i] Leader: {leader.get('name','leader')}  Willpower={leader.get('willpower','?')}")

    # Simple parley: (charisma - willpower) + random(-50..50)
    c = int(player.get("charisma", 30))
    w = int(leader.get("willpower", 30))
    roll = random.randint(-50, 50)
    score = (c - w) + roll
    print(f"[check] (Charisma {c} - Willpower {w}) + roll {roll:+} = score {score:+}")

    if score >= 0:
        print("[result] Parley success: Tension eases. No combat.")
        out = ROOT / "chat_logs" / "velvet_gallows_outcome.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("Parley success at Velvet Gallows. No combat.\n", encoding="utf-8")
        print(f"[log] Wrote: {out}")
        return

    print("[result] Parley failed: Combat begins.")
    gorthak = CHARS / "gorthak.json"
    backup = CHARS / "gorthak.json.bak"
    leader_file = CHARS / "bandit_leader.json"

    if not SIM.exists():
        print(f"[!] Could not find battle_simulation: {SIM}")
        sys.exit(1)
    if not leader_file.exists():
        print(f"[!] Missing bandit_leader.json: {leader_file}")
        sys.exit(1)
    if not gorthak.exists():
        print(f"[!] Missing gorthak.json to swap into: {gorthak}")
        sys.exit(1)

    try:
        if backup.exists():
            backup.unlink()
        backup.write_text(gorthak.read_text(encoding="utf-8"), encoding="utf-8")
        gorthak.write_text(leader_file.read_text(encoding="utf-8"), encoding="utf-8")
        print("[swap] Injected bandit leader into gorthak.json for this run.")
        print("[run] Starting battle_simulation.py ...")
        subprocess.run([sys.executable, str(SIM)], check=False)
    finally:
        if backup.exists():
            gorthak.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
            backup.unlink(missing_ok=True)
            print("[restore] Restored original gorthak.json.")

if __name__ == "__main__":
    main()
