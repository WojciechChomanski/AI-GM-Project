def apply_recovery(action: str, player="wojtek"):
    # Load mental state
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

    # Save
    state[player] = profile
    write_json("rules/player_mental_state.json", state)
