# validate_lore.py
# Works with your current layout (everything under AI_GM_Project/lore/…).
# No moves, no symlinks. Just run:  python .\scripts\validate_lore.py

from __future__ import annotations
import json, sys
from pathlib import Path

# Resolve project root as the folder that contains /scripts
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent
print(f"[i] Using project root: {PROJECT_ROOT}")

# --- Expected files *in your tree* ---
# (mapped to your folders per your screenshot)
EXPECTED = {
    # core
    "lore_master":              PROJECT_ROOT / "lore" / "core" / "lore_master.json",
    "era_1670":                 PROJECT_ROOT / "lore" / "era_1670.json",
    "scroll_of_light_and_fall": PROJECT_ROOT / "lore" / "scrolls" / "scroll_of_light_and_fall.json",

    # factions / races
    "factions": PROJECT_ROOT / "lore" / "factions" / "factions.json",
    "races":    PROJECT_ROOT / "lore" / "races" / "races.json",

    # quests & events
    "hooks_1670":                 PROJECT_ROOT / "lore" / "quests" / "hooks_1670.json",
    "event_cinderhold_storm":     PROJECT_ROOT / "lore" / "events" / "veil_storm_cinderhold_1670.json",
    "event_ironcrag_riots":       PROJECT_ROOT / "lore" / "events" / "ironcrag_fuel_riots_1670.json",
    "event_first_thorn":          PROJECT_ROOT / "lore" / "events" / "hunt_first_thorn_1670.json",
    "event_ogre_would_be_king":   PROJECT_ROOT / "lore" / "events" / "ogre_would_be_king_1670.json",
    "event_blade_in_crescent":    PROJECT_ROOT / "lore" / "events" / "blade_in_the_crescent_1670.json",

    # bestiary & extras
    "abominations": PROJECT_ROOT / "lore" / "bestiary" / "abominations.json",
    "quotes":       PROJECT_ROOT / "lore" / "extras" / "quotes.json",
    "legends":      PROJECT_ROOT / "lore" / "extras" / "legends.json",

    # optional but present in your tree
    "khilafate": PROJECT_ROOT / "lore" / "factions" / "khilafate_scoured_veil.json",
    "relics":    PROJECT_ROOT / "lore" / "items" / "relics_crescent.json",
    "orders":    PROJECT_ROOT / "lore" / "orders" / "Crusader_Orders.json",
}

# --- Helpers ---
def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

missing = []
parse_errors = []
warnings = []
ok = []

# Check presence + JSON validity
for name, path in EXPECTED.items():
    if not path.exists():
        missing.append(f"[MISSING] {path}")
        continue
    try:
        data = load_json(path)
        ok.append(f"[OK] {path}")
        # Lightweight, file-specific sanity checks
        if name == "era_1670":
            for key in ("era", "regions", "omens", "faction_activity", "pressure_dials", "flashpoints"):
                if key not in data:
                    warnings.append(f"[WARN] era_1670.json missing key: {key}")
        if name == "hooks_1670":
            if "quests" not in data or not isinstance(data["quests"], list):
                warnings.append("[WARN] hooks_1670.json should contain a 'quests' array")
        if name == "factions":
            if not isinstance(data, dict):
                warnings.append("[WARN] factions.json should be a JSON object (dictionary)")
        if name == "races":
            if not isinstance(data, dict):
                warnings.append("[WARN] races.json should be a JSON object (dictionary)")
    except Exception as e:
        parse_errors.append(f"[PARSE] {path}: {e}")

# --- Report ---
if ok:
    print("\nPASSED files:")
    for line in ok:
        print(" -", line)

if missing or parse_errors or warnings:
    print("\nFAILED / WARNINGS:")
    for line in missing + parse_errors + warnings:
        print(" -", line)
    sys.exit(1)
else:
    print("\nAll checks passed.")
    sys.exit(0)

