# Bleeding ticks, healing, regeneration, Breath wounds, morale (v0.1, PLACEHOLDER numbers)

Data: `rules/wound_recovery.json`. Code: `scripts/wound_recovery.py`, hooks in `scripts/bleeding.py`, `scripts/combat_health.py`,
`scripts/corruption.py`, `scripts/combat_engine.py`. Tests: `tests/test_recovery.py`.

## Per round
- Bleeding: unchanged (docs/BLEEDING.md). `CombatHealthManager.apply_bleeding()`, 13-zone model, 5 HP/round cap,
  no zone below 1, cuts stop after 3 rounds.
- **Breath wounds** (`add_bleeding_wound(..., breath=True)`): rate x1.5 (rounded up), clot time x1.5, GM label "burning".
  Fair: a cut still stops (after 4 rounds instead of 3), and the cap still applies.
- **Dwarf**: `bleed_clot_mult` 0.8 is now set automatically for race Dwarf (from rules/lore/dwarves.json).
- **Corrupted regeneration** (`wound_recovery.regen_round`): 5% of natural HP per round (min 1), only removes normal damage.
  Full-Breath damage (`CorruptedCreature.breath_effective`) is never regenerated.
- **Morale vs a full-Breath knight**: d100 <= 50 + WIL//5 - 10 holds. A fail means it picks another target if one is
  available; with no one else it still attacks. In `combat_engine.attack_roll`, a corrupted attacker with
  `other_targets_available` tests first; on a fail it returns `shied_away: true`. `wound_recovery.choose_target` does the same for
  game loops.

## Per day
- `wound_recovery.heal_day` / `heal_manager_day`: 1 HP per wounded zone per day resting, 2 with bed rest and care, 0.5 while
  travelling. Zones at 0 (crippled or severed) do not heal by themselves, and nothing heals while still bleeding.
- Ogre: x1.5 if fed, 0 if unfed (rules/races.json "Fast Healing ... as long as fed"). **Dwarves have no faster-healing
  trait in the data**, only shorter bleeding (0.8).
- Corrupted creature: Breath damage heals naturally at x0.5 (`creature_heal_day`).

## Wired vs data-only
Wired: Breath wound bleeding/clotting, Dwarf clot rate, regeneration, daily healing, morale test in combat_engine,
damage_taken / breath_damage_taken returned from combat_engine.
Not automatic: nobody calls `apply_bleeding`, `regen_round` or `heal_manager_day` on a clock yet. The game loop or GM
console must call them once per round or day (there is no round loop that owns them).

## Round and day loop (`scripts/time_loop.py`, `rules/time_loop.json`)
- `round_tick(manager, creature)`: bleeding with clotting (`apply_bleeding`), then corrupted regeneration (Breath damage
  is never regenerated).
- `day_tick(manager, mode, fed)`: infection step first, then natural healing for the rest mode (`resting` 1,
  `bed_rest_with_care` 2, `travelling` 0.5 HP per zone). No healing while bleeding or infected, and zones at 0 stay at 0.
- GM command: `gm_command("tick round 3" | "tick day 2 bed_rest_with_care [unfed]", {name: manager}, {name: creature})`.
  Safe per character: dead characters are skipped, unknown modes raise an error, and each command runs at most
  1000 ticks.

## Repairing crippled and severed parts (`scripts/limb_repair.py`, `rules/limb_repair.json`)
States are kept in `manager.limb_state`. A zone at 0 is `crippled`. A crit text saying "severed" marks it `severed`.
After treatment a severed zone becomes `stabilised` or `prosthesis`.
- **Surgery.** The repo has no surgery skill, so it uses `skills["surgery"]` if present, else (INT + DEX) / 2.
  - Roll d100 <= skill + tools (field kit 0, surgeon kit +10, infirmary +20; no tools -30) - difficulty - pain (max 20).
  - Crippled: on success the zone is restored to 1 HP and then heals normally.
  - Severed: surgery cannot reattach it. It can only stabilise the zone (stops its bleeding) or fit a prosthesis
    (arm: -20 WS / -10 DEX; leg: -20 mobility).
  - Failure: 30% chance of infection. A roll of 96+, or missing by more than 20, also deals 3 extra damage, spread so
    no zone drops below 1.
  - Infection: +2 stress per day, blocks healing, needs a daily TOU test. Two passes clear it. A fail costs 1 HP,
    spread so no zone drops below 1, so an infection alone can never kill.
- **Magic** (core_rules.txt: active magic is female only, human or elf; passive items are for everyone):
  - Veil healing by a sorceress restores a crippled part. The caster takes 5 corruption and pays 6 HP. The patient
    takes 2 corruption.
  - Regrowing a severed part is a hard roll (-40). The caster takes 15 corruption and the patient 10. The caster pays
    her price even when the spell fails.
  - A relic or potion (passive) restores a crippled part and uses one charge. Only a saint relic can restore a severed
    part, with no corruption.
