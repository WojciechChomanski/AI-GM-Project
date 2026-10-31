# Cleanup and conflict fixes (chore/cleanup-duplicates)

## Deleted (verified unused)
- Root `bestiary/`, `extras/`, `factions/`, `quests/`: byte-identical to `lore/<same>/` (`diff -r` clean). Every code/manifest reference (`scripts/validate_lore.py`, `lore_manifest.txt`) points at the `lore/` copies; no code scans the repo root.
- `chat_with_wojtek.py.bak`, `rules/characters/wojtek.json.bak`, `rules/characters/elara_voss.json.bak`: backups (`*.bak` is already in `.gitignore`). Only reference was the file listing in `rules_manifest.txt` (lines removed).
- `scripts/memory_handler.py`, `npc_engine.py`, `prompt_generator.py`, `relationship_manager.py`, `trauma_engine.py`: 0 bytes, not imported anywhere (the live module is `scripts/npc_memory_handler.py`).

## Kept on purpose
- `rules/items/stonewarden_kits_v0_6b.json` and `rules/npc_system.md` are also empty files, but they are not duplicates of anything; left for the owner to decide.
- Torvax entry in `npc_memory.json`: isolation cleanup is the owner's own job.

## Conflict fixes
- **Crusader Knight +12 STR listed twice**: removed the duplicate `stats` block (`strength_modifier` 12, etc.). `stat_modifiers` is kept; `character_loader._find_hp_percent` still finds `hp_percent` 15 there.
- **Race modifiers vs stats.json**: in the Python code the race `*_modifier` values were only stored as unused attributes and never added to stats, but the data read as if an ogre got 50 + 20. Rule now: `rules/stats.json` starting/max values are final and already include race. The STR/AGI/INT/CHA modifiers in `rules/races.json` are set to 0 (hp_bonus, stamina_bonus untouched). Elf CHA will be handled by the Looks/Charisma work.
- **D&D-scale leftovers rescaled to d100**: `combat_engine.Combatant` defaults STR 10→35, DEX 10→30, weapon_skill 0→30 (human male start); `enemy_spawner` enemies (e.g. Drowned Thrall STR 8→30, Leviathan 15→55, Golem toughness 15→55); `scripts/test_advanture.py` party stats moved to stats.json starts plus class bonuses (e.g. Crusader 35+12=47).

## Follow-ups (fix/class-loading-followups)
- Deleted empty `rules/npc_system.md` (no references). **Kept** empty `rules/items/stonewarden_kits_v0_6b.json`: it is referenced by `rules/kits/stonewarden_quickstart_party_v0_6e.json` and `rules/vendors/ansel_platewright_v0_6b.json`.
- Class loading fixed: `character_loader` looked for `rules/classes.json`, which never existed, so no class bonus ever applied. It now finds the class in `rules/classes/*.json`.
  - d100 classes (`stat_modifiers`: Crusader Knight, Rogue, Veil Sorceress) apply as written, exactly once. If a class has both blocks, only `stat_modifiers` counts.
  - Older classes with small `*_modifier` values in `stats` are scaled x3 (same as backgrounds), e.g. Ogre Brute STR +4 -> +12.
  - After class and background, every stat is clamped to the stats.json cap plus talent cap raises.
  - Crusader Knight (human male) now starts STR 47, TOU 45, AGI 35, WIL 33.
