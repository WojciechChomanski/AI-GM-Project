import json
import os


def read_json(path: str):
    """Load JSON data from a file or return an empty dict if it doesn't exist."""
    return json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {}


def write_json(path: str, data) -> None:
    """Write JSON data to a file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def apply_recovery(action: str, player: str = "wojtek"):
    """Apply a recovery rule to the player's mental state."""
    state = read_json("rules/player_mental_state.json")
    rules = read_json("rules/recovery_rules.json")

    profile = state.get(player, {})
    recovery = rules.get(action, {})

    # Apply stress reduction
    profile["stress"] = max(0, profile.get("stress", 0) - recovery.get("stress_reduction", 0))

    # Apply condition changes
    for cond, delta in recovery.get("conditions", {}).items():
        if cond in profile.get("conditions", {}):
            profile["conditions"][cond] = max(0, profile["conditions"][cond] + delta)

    # Apply trauma reduction
    profile["trauma_score"] = max(0, profile.get("trauma_score", 0) - recovery.get("trauma_score_reduction", 0))

    # Save updated profile
    state[player] = profile
    write_json("rules/player_mental_state.json", state)

    return profile
