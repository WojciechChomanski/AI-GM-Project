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
Damage (after armour, see below) is spread over the **11 eligible zones** in proportion to each zone's maximum. Big zones (chest, upper legs, stomach, head) take 2–3 points where small ones take 1. Example: 10 damage → chest 2, most other zones 1.
- **Throat and groin are never hit by a spread hit.** Only an aimed strike can damage them.
- **The head floors at 1 under spread.** A normal hit can wound the head but never reduce it to 0. Damage the head can't absorb moves to the other eligible zones.
- **The chest has no floor.** Enough normal hits can take it to 0, which is death (a real "worn down" death).
- Other zones can reach 0 (destroyed) but never go below 0.
- **Bleeding follows the same rule** (same excluded zones, same head floor).
- So a normal hit can never kill through the head or throat; that takes an aimed strike.

## Aimed strike
- Flat **−30** to hit (`aimed_attack.base_penalty`). The per-zone `aimed_penalties` table is kept as data but not used.
- On a hit, the **full damage** goes to the one chosen zone.
- A **miss does no damage**. It never turns into a normal hit.

## Zone at 0
- **Head, throat or chest** → death / dying. (Head and throat can only get to 0 from an aimed strike; the chest can also get there by spread.)
- **Arm or leg** → destroyed / crippled (existing cripple rules: no two-handed weapons and −parry for arms; −mobility and no charge for legs).
- Stomach / groin → crit wound + consequences, bleeding, pain.
- Every zone that hits 0 from a weapon rolls the crit wound table for its **body area and damage type** (blunt / slashing / piercing), plus the consequence roll; damage beyond 0 is added to the roll.

## Armour (option B)
Armour keeps you alive longer; it never makes you immune. Whatever armour does not absorb is **real damage**.
Uses the existing armour data only (`armor_rating` per damage type, `coverage`, per-zone durability); no new stats.

**Protection of one piece on one zone** = its `armor_rating[damage_type]` × condition (durability ≥75% ×1.0, ≥50% ×0.75, ≥25% ×0.5, >0 ×0.25, broken 0). Pieces layered on the same zone add up.

**Aimed strike:** only the armour on the **hit zone** counts. `damage − protection` (min 0) goes **fully into that zone**. Every piece covering that zone loses `max(1, 20% of the incoming damage)` durability on it (as before).

**Normal (spread) hit:**
1. Work out the **zone-size-weighted average protection** over all 13 zones. Weights = base zone HP (chest 20, upper legs 13 each, stomach 11, head 7, upper arms/lower legs 6 each, lower arms/throat/groin 3 each; sum 100). A zone with no armour counts 0.
2. Round half up (6.75 → 7, 0.4 → 0). Damage is reduced by that, never below 0.
3. The remainder is spread with the normal spread rule (throat/groin excluded, head floor 1).
4. Durability: only pieces that actually contributed wear. A piece that absorbed *a* loses `max(1, 20% of a)` in total, shared over the zones it covers in proportion to zone size.

Example: 10 damage vs 6 average protection → 4 is spread over the body (chest takes 1–2). 
Real numbers (rules/armors.json, slashing): Full Plate averages 8.7 (→ 9), Half Plate 7.0, Breastplate 6.75 (→ 7), Light Chainmail 2.15 (→ 2), Padded Cloth 0.4 (→ 0). No armour covers head, throat or groin, so even Full Plate is ~87% of its rating. Siege Plate (avg 9.57 → 10) means 10 damage or less does nothing, 11 still leaves 1.

Critical hits (×1.2) are applied before armour. Bleeding is worked out from the damage that gets through (a hit fully absorbed causes no bleeding).
Code: `armor_system.py` (`average_protection`, `armor_vs_spread`, `armor_vs_aimed`), used by `CombatHealthManager.distribute_damage` / `take_damage_to_zone` and `Character.receive_damage(damage, damage_type)`. Tests: `python tests/test_zone_armor.py`.

## Unchanged
Crit tables, bleeding (now spread over the body like a normal hit, same eligibility rules), pain penalties.

## Collapse
- **3 or more zones at 0 HP = collapse.** This is checked after every hit and every bleed tick.
- The old **"33% of total HP lost" collapse was removed.** Losing HP alone never collapses a character; it has to be destroyed zones (or death). `rules/combat_rules.json` → `zone_hp.collapse.blood_loss_percent` is `null` / unused.
- Not implemented yet (not approved): Willpower tests at 2 zones down, both-legs-down rule.

## Code
`scripts/zone_hp.py` (zone table, scaling, spread), `scripts/combat_health.py` (`distribute_damage`, `take_damage_to_zone`, `resolve_aimed_strike`), `scripts/character.py`, `scripts/character_loader.py`. Tests: `python tests/test_zone_damage.py`, `python tests/test_zone_armor.py`.
