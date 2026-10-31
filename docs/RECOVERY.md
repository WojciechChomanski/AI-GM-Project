# Bleeding ticks, healing, regeneration, Breath wounds, morale (v0.1, PLACEHOLDER numbers)

Data: `rules/wound_recovery.json`. Code: `scripts/recovery.py`, hooks in `scripts/bleeding.py`, `scripts/combat_health.py`,
`scripts/corruption.py`, `scripts/combat_engine.py`. Tests: `tests/test_recovery.py`.

## Per round
- Bleeding: unchanged (docs/BLEEDING.md). `CombatHealthManager.apply_bleeding()`, 13-zone model, 5 HP/round cap,
  no zone below 1, cuts stop after 3 rounds.
- **Breath wounds** (`add_bleeding_wound(..., breath=True)`): rate x1.5 (rounded up), clot time x1.5, GM label "burning".
  Fair: a cut still stops (after 4 rounds instead of 3), and the cap still applies.
- **Dwarf**: `bleed_clot_mult` 0.8 is now set automatically for race Dwarf (from rules/lore/dwarves.json).
- **Corrupted regeneration** (`recovery.regen_round`): 5% of natural HP per round (min 1), only removes normal damage.
  Full-Breath damage (`CorruptedCreature.breath_effective`) is never regenerated.
- **Morale vs a full-Breath knight**: d100 <= 50 + WIL//5 - 10 holds. A fail means it picks another target if one is
  available; with no one else it still attacks. In `combat_engine.attack_roll`, a corrupted attacker with
  `other_targets_available` tests first; on a fail it returns `shied_away: true`. `recovery.choose_target` does the same for
  game loops.

## Per day
- `recovery.heal_day` / `heal_manager_day`: 1 HP per wounded zone per day resting, 2 with bed rest and care, 0.5 while
  travelling. Zones at 0 (crippled or severed) do not heal by themselves, and nothing heals while still bleeding.
- Ogre: x1.5 if fed, 0 if unfed (rules/races.json "Fast Healing ... as long as fed"). **Dwarves have no faster-healing
  trait in the data**, only shorter bleeding (0.8).
- Corrupted creature: Breath damage heals naturally at x0.5 (`creature_heal_day`).

## Wired vs data-only
Wired: Breath wound bleeding/clotting, Dwarf clot rate, regeneration, daily healing, morale test in combat_engine,
damage_taken / breath_damage_taken returned from combat_engine.
Not automatic: nobody calls `apply_bleeding`, `regen_round` or `heal_manager_day` on a clock yet. The game loop or GM
console must call them once per round or day (there is no round loop that owns them).
