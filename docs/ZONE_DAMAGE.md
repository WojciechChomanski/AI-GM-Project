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
- **Bleeding follows the same spread rule** (throat/groin excluded), but is gentler: it never takes any zone below 1, so it can never destroy a limb or kill through a zone at 0. See `docs/BLEEDING.md`.
- So a normal hit can never kill through the head or throat; that takes an aimed strike.

## Aimed strike
- **−30** to hit for every zone, **−40** for the narrow targets **head, throat and groin** (the helmet slit, the gap at the throat, the groin joints). Hard to land, but devastating when it works. (`aimed_attack.base_penalty` / `narrow_zone_penalty` and the per-zone `aimed_penalties` table in `rules/combat_rules.json`; code: `zone_hp.AIMED_PENALTY_BY_ZONE` / `aimed_penalty(zone)`; applied in `adventure_new.attack_roll`. `neck` counts as throat.) **PLACEHOLDER numbers.**
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

**Protection of one piece on one zone** = (its `armor_rating[damage_type]` − permanent quality loss, see `docs/DURABILITY.md`) × condition (durability ≥75% ×1.0, ≥50% ×0.75, ≥25% ×0.5, >0 ×0.25, broken 0).

**No stacking:** pieces covering the same zone do **not** add up. Per zone only the **single best piece** (highest rating × condition) counts, and only that piece wears on that zone. A plated gauntlet over a breastplate is simply the better of the two on the lower arm, not the sum. (Weight and mobility of the second piece still cost you; under-layer bonuses are an open question and not implemented.) If the best piece is broken, the next best one counts.

**Aimed strike:** only the armour on the **hit zone** counts. `damage − protection` (min 0) goes **fully into that zone**. Only the piece that counted on that zone loses `max(1, 20% of the incoming damage)` durability on it.

**Normal (spread) hit:**
1. Work out the **zone-size-weighted average protection over the 11 zones a normal hit can actually hit** (throat and groin are left out, because a normal hit never lands there). Weights = base zone HP: chest 20, upper legs 13 each, stomach 11, head 7, upper arms/lower legs 6 each, lower arms 3 each. They sum to 94, so the result is divided by 94. A zone with no armour counts 0. A piece that covers all 11 zones at rating 10 therefore averages exactly 10. Throat/groin armour (gorget, groin guard) does not help against normal hits and does not wear from them; it still protects fully against an aimed strike on its zone.
2. Round half up (6.75 → 7, 0.4 → 0). Damage is reduced by that, never below 0.
3. The remainder is spread with the normal spread rule (throat/groin excluded, head floor 1).
4. Durability: only pieces that actually counted wear, and only on the zones where they were the counted (best) piece. A piece that absorbed *a* loses `max(1, 20% of a)` in total, shared over those zones in proportion to zone size.

Example: 10 damage vs 6 average protection → 4 is spread over the body (chest takes 1–2). 
Real numbers (rules/armors.json, slashing, 11-zone average, best piece per zone): **Full Plate 10.00 (→ 10)** and **Siege Plate 11.00 (→ 11)** — both now cover **all 13 zones with the same rating on every zone**; Half Plate 5.87 (→ 6), Breastplate 4.12 (→ 4), Light Chainmail 2.29 (→ 2), Padded Cloth 0.43 (→ 0). With plate, a normal hit of 10 or less does nothing (Siege: 11 or less), 1 more still leaves 1. **All numbers are placeholders for testing** and need a balance pass against weapon damage.

**Plate sets (tier 8 Full Plate, tier 9 Siege Plate; standard and dwarven):** coverage is all 13 zones (head, throat and groin included — a helm and gorget come with the top tiers). The rating is the same on every zone (the owner gave full plate "the benefit of the doubt"; can be tuned later, e.g. less at the head slit / groin joints). Siege Plate has slightly higher absorption, durability and weight than Full Plate. To keep the zone weight and wear balance, weight was scaled ×100/87 (the old 10-zone set was 87% of the body) and the per-zone durability was **kept** (so total durability = old per-zone × 13):

| Set | rating (s/p/b) | weight kg (was) | max_durability (was) | per zone (13 zones) |
|---|---|---|---|---|
| Full Plate | 10/9/8 | 32.2 (28) | 143 (110) | 11 |
| Forged Full Plate (dwarven) | 11/10/9 | 36.8 (32) | 156 (120) | 12 |
| Siege Plate | 11/10/9 | 40.2 (35) | 156 (120) | 12 |
| Rune-Forged Siege Plate (dwarven) | 12/11/10 | 46.0 (40) | 169 (130) | 13 |

Stamina penalty and mobility are unchanged. **Breastplate and Half Plate (owner decision):** Breastplate (`Medium_Heavy`, tier 6) = chest, stomach and both upper arms only. Half Plate (`Heavy_Light`, tier 7 — **Half Plate is the higher tier**; the two slots were swapped, see "Tier slots" at the end of this file) = those plus both upper legs. Lower arms and lower legs are not covered by either; they need loose pieces (gauntlets, greaves). Variants (Forged Breastplate, Forged Half Plate) follow the same coverage. Ratings are unchanged. Same convention as the plate sets: per-zone durability **kept** (total = per zone × zone count) and weight scaled by the share of body zone HP covered (old/new: Breastplate 75→43, Half Plate 87→69 of 100):

| Set | coverage | weight kg (was) | max_durability (was) | per zone |
|---|---|---|---|---|
| Breastplate | 4 zones | 12.6 (22) | 48 (100) | 12 |
| Forged Breastplate | 4 zones | 14.9 (26) | 52 (110) | 13 |
| Half Plate | 6 zones | 15.9 (20) | 54 (90) | 9 |
| Forged Half Plate | 6 zones | 19.0 (24) | 60 (100) | 10 |

Normal-hit average (slashing, 11 zones): Breastplate 7.18 → 4.12, Forged Breastplate 7.98 → 4.57; Half Plate 7.40 → 5.87, Forged Half Plate 8.33 → 6.61. **Placeholders.**

**Lower sets get no head/throat/groin cover by default** (chainmail, brigandine, scale, half plate, breastplate): those need loose pieces (helm, gorget, groin guard…). Loose pieces are only a draft so far and are not in `armors.json`. Armour objects keep weights and stamina penalties as floats (no `int()` casts).

A piece with no coverage (`Unarmored`) is reported as condition "None", not "Broken".

Critical hits (×1.2) are applied before armour. Bleeding is worked out from the damage that gets through (a hit fully absorbed causes no bleeding).
Code: `armor_system.py` (`best_piece_for_zone`, `average_protection`, `armor_vs_spread`, `armor_vs_aimed`), `durability.py`, used by `CombatHealthManager.distribute_damage` / `take_damage_to_zone` and `Character.receive_damage(damage, damage_type)`. Tests: `python tests/test_zone_armor.py`, `python tests/test_durability.py`.

## Unchanged
Crit tables, bleeding (now spread over the body like a normal hit, same eligibility rules), pain penalties.

## Collapse
- **3 or more zones at 0 HP = collapse.** This is checked after every hit and every bleed tick.
- The old **"33% of total HP lost" collapse was removed.** Losing HP alone never collapses a character; it has to be destroyed zones (or death). `rules/combat_rules.json` → `zone_hp.collapse.blood_loss_percent` is `null` / unused.
- Not implemented yet (not approved): Willpower tests at 2 zones down, both-legs-down rule.

## Code
`scripts/zone_hp.py` (zone table, scaling, spread), `scripts/combat_health.py` (`distribute_damage`, `take_damage_to_zone`, `resolve_aimed_strike`), `scripts/character.py`, `scripts/character_loader.py`. Tests: `python tests/test_zone_damage.py`, `python tests/test_zone_armor.py`.

**Tier slots (owner decision "Half Plate above Breastplate"):** the tier of an armour is its key in `rules/armors.json` (order = rank; class files list allowed tiers such as `medium-heavy`). Slots swapped: `Medium_Heavy` (tier 6) now holds Breastplate / Forged Breastplate, `Heavy_Light` (tier 7) holds Half Plate / Forged Half Plate. Ratings, coverage, weights unchanged. Existing kits that wore Half Plate (wojtek, Torvald, Brock, Outlaw Mercenary Warrior, Holy Judge starting kit) were re-pointed from `Medium_Heavy` to `Heavy_Light` so they keep Half Plate.
