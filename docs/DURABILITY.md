# Durability and permanent wear (Breath and the Veil)

**Every number on this page is a PLACEHOLDER for testing.** They will be tuned after play. Code: `scripts/durability.py` (`Wear`), wired into `scripts/armor_system.py` (armour, per zone) and `scripts/adventure_new.py` (weapons). Tests: `python tests/test_durability.py`.

## The rules (as the owner described them)
1. Every item has an **original maximum** durability and a **current maximum**.
2. Every time the durability lost since the last mark reaches **30% of the CURRENT maximum**, the current maximum **permanently drops by 5% of the ORIGINAL maximum** (100 → 95 → 90 …). The wear counter then resets. The counter is cumulative: it keeps counting across repairs, so light damage that you always repair still adds up over time.
3. **Repairs** only restore durability up to the *current* maximum. They never reset the wear counter and can never bring an item back to its original maximum once marks have been taken. The old **field-repair cap** is kept (see below).
4. When the current maximum reaches 0 the item is **destroyed**.
5. **Quality** (permanent, on top of the temporary condition bands): for every **10%** of the original maximum permanently lost (= every 2 marks):
   - **Weapons:** damage −1 per 10 base damage (rounded half up; at least −1 per step for weapons with ≥5 base damage). A 10-damage sword loses 1 per step, a 14-damage greatsword 1, a 20-damage weapon 2. A living weapon never drops below 1 damage; a destroyed or broken (0 durability) weapon deals no weapon damage.
   - **Armour:** armour rating −1 for each damage type (never below 0).

## Armour: per zone
Each armour zone has its own `Wear` (a dented chest does not weaken the gauntlets). `ArmorPiece.per_zone_max[zone]` is the **current** zone maximum and shrinks with each mark; `original_zone_max[zone]` never changes; `zone_wear[zone]` holds the counter and the number of marks (`armors.Armor` objects get the same lazily). Durability that exceeds a new maximum is clamped down. Only the piece that actually *counted* on a zone wears there (see "No stacking" in `docs/ZONE_DAMAGE.md`).

`repair(skill, zone)` restores `current_max × (0.20 + 0.05 × skill)` (max 0.90), never above the current maximum. **Existing 85% field-repair cap kept (flagged):** if more than half of the current maximum is missing, one repair stops at 85% of the current maximum. A zone at 0 durability is "beyond field repair" (existing rule). Because 5% of the original maximum per mark is fractional on small zone values (e.g. 11), armour durability values are floats.

## Weapons
`adventure_new.init_weapon_state` creates a `Wear` from the weapon's starting durability (original max). `apply_durability_tick(unit, log, kind)` takes **0.5 per attack** and **1.0 per parry** from `rules/combat_rules.json` → `weapon_durability` (`loss_per_attack`, `loss_on_parry`) and feeds the wear counter. `base_damage_for` applies the quality loss. A weapon at 0 durability (`break_threshold`) is broken and deals no weapon damage until repaired (`repair_weapon_durability`, capped at the current maximum); one whose current maximum is 0 is destroyed for good. A parry tick was added where a parry (`spend_stamina(..., "parry")`) happens in the attack loops.

Not wired: blocks with a shield (`shield_system.py` / `character.wear_shield` are not used by the game loop), `character.wear_weapon` (never called), and the old `armors.Armor.max_repairable_durability` (a fixed 80%, never read). There is no weapon repair command in the game loop yet (only the helper).

## Example (placeholder): 100-durability, 10-damage sword, ~12 durability lost per fight, fully repaired after each fight
| after fight | current max | quality steps | damage |
|---|---|---|---|
| 3 | 95 | 0 | 10 |
| 5 | 90 | 1 | 9 |
| 10 | 80 | 2 | 8 |
| 14 | 70 | 3 | 7 |
| 20 | 50 | 5 | 5 |
| 26 | 10 | 9 | 1 |
| 27 | 0 | – | destroyed |

Marks speed up as the current maximum shrinks (30% of a smaller number). If the 30% mark should use the original maximum instead (fixed 30 points) the sword would last about 50 fights; this is a one-line change in `Wear.lose` and open for tuning.

## Constants (mirrored in `rules/combat_rules.json` → `durability`; a test keeps them equal)
| constant | value |
|---|---|
| mark_fraction_of_current_max | 0.30 |
| mark_loss_fraction_of_original_max | 0.05 |
| quality_step_fraction_of_original_max | 0.10 |
| field_repair_cap | 0.85 |
| weapon loss per attack / per parry | 0.5 / 1.0 |
