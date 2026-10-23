# Zone Damage (Breath and the Veil)

## Hit points = body zones
Every character has 13 body zones. **Total HP is the zones added together** — there is no separate HP pool.

| Zone | Base HP |
|---|---|
| Chest | 20 |
| Upper leg (L/R) | 13 / 13 |
| Stomach | 11 |
| Head | 7 |
| Upper arm (L/R) | 6 / 6 |
| Lower leg (L/R) | 6 / 6 |
| Lower arm (L/R) | 3 / 3 |
| Throat | 3 |
| Groin | 3 |
| **Total** | **100** |

Race and class scale every zone by the same factor: Dwarf ×1.2 (120), Ogre ×2 (200), Crusader Knight ×1.15. Factors multiply (Dwarf Knight = 138). Rounding leftovers go to the chest.

## Normal hit — spread
Damage (after armour) is spread over **all** living zones, in proportion to each zone's maximum. Big zones (chest, upper legs, stomach, head) take 2–3 points where small ones take 1. Example: 10 damage → chest 2, every other large/medium zone 1. A zone can reach 0 but never goes below 0; damage it can't absorb moves to the other zones.

## Aimed strike
- Flat **−30** to hit (`aimed_attack.base_penalty`). The per-zone `aimed_penalties` table is kept as data but not used.
- On a hit, the **full damage** goes to the one chosen zone.
- A **miss does no damage**. It never turns into a normal hit.

## Zone at 0
- **Head, throat or chest** → death / dying.
- **Arm or leg** → destroyed / crippled (existing cripple rules: no two-handed weapons and −parry for arms; −mobility and no charge for legs).
- Stomach / groin → crit wound + consequences, bleeding, pain.
- Every zone that hits 0 from a weapon rolls the crit wound table for its **body area and damage type** (blunt / slashing / piercing), plus the consequence roll; damage beyond 0 is added to the roll.

## Unchanged
Armour per zone, bleeding (now spread over the body like a normal hit), collapse at 33% of total HP lost, collapse at 3 zones at 0, pain penalties.

## Code
`scripts/zone_hp.py` (zone table, scaling, spread), `scripts/combat_health.py` (`distribute_damage`, `take_damage_to_zone`, `resolve_aimed_strike`), `scripts/character.py`, `scripts/character_loader.py`. Tests: `python tests/test_zone_damage.py`.
