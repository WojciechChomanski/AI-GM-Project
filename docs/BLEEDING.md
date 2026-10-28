# Bleeding (Breath and the Veil)

**All numbers are PLACEHOLDERS for testing** (owner: tune them after everything works). Code: `scripts/bleeding.py` (rules, bandage), `CombatHealthManager` in `scripts/combat_health.py` (wound list, one bleeding round), `scripts/healing_system.py` (bandage items). Mirrored in `rules/combat_rules.json` → `bleeding` (a test keeps them equal). Tests: `python tests/test_bleeding.py`.

## What bleeds
- Only damage that **got through armour** can cause a wound (0 through = no wound).
- **Blunt bleeds ONLY on a crit.** A non-crit blunt hit never bleeds, whatever the damage.
- Slashing/piercing: a **cut** if ≤5 damage got through, a **deep** wound if 6+ or a crit. A crit result that cuts an artery (crit table text "artery"/"jugular", or the consequence "Artery Slashed") makes an **artery** wound (never from blunt). One artery wound per zone; the same hit does not add a second wound on top of its artery.
- A normal (spread) hit has no single zone: the wound sits on the zone that took the most damage from that hit.

## Rate (whole HP per round, no more int() rounding to 0)
| Zone | Cut | Deep | Artery |
|---|---|---|---|
| Arms, lower legs, head, chest, stomach | 1 | 2 | 3 |
| Upper legs, groin | 2 | 3 | 4 |
| Throat | 3 | 4 | 5 |

## Each round (`apply_bleeding`)
1. All wounds together lose at most **5 HP per round** (cap). More wounds do not add beyond the cap.
2. That HP is taken as **one spread** over the body: throat and groin excluded, head floor 1 (existing rules), and **no zone ever goes below 1**. Bleeding therefore **cannot destroy a limb and rolls no crits/consequences** (it also cannot trigger the 3-zones-at-0 collapse).
3. Then every wound ages: a **cut** stops after 3 rounds; a **deep** wound loses 1 HP/round of rate every 4 rounds until it stops; **artery wounds and every throat wound never stop by themselves.**
4. Perk hooks (not wired to race/class data yet): `character.bleed_clot_mult` (Dwarf 0.8 = −20% clot time) and `character.bleed_rate_mult` (Bear's Endurance 0.5; rate rounded up, minimum 1).

## Death by blood loss (decision)
Because bleeding never takes a zone below 1 and never touches throat/groin, the most blood a body can lose is: every one of the 11 spread zones down to 1, with throat and groin untouched = **17 HP left** (for a 100 HP body). If blood loss is still pending when every zone that can bleed is already at 1, the chest "would reach 0": the character **bleeds out and dies** (`character.die()`). This is the simplest consistent rule that keeps limbs safe and still lets bleeding kill. **Side effect:** a character at ≤ ~17 total HP with a wound that keeps bleeding is dead, so the draft's "30 HP left, thigh deep wound → survives with 6 HP" is now "bleeds out in round 5" (only 13 HP can bleed away).

## Treatment (one rule, used by both bandage scripts)
`bleeding.attempt_bandage` works on the **real wound list** (`CombatHealthManager.bleeding_wounds`). `HealingSystem.attempt_bandage(healer, target, item)` and the old `FirstAidSystem.attempt_bandage` (now a thin wrapper) both call it. The old `bleeding = 0` and `bleeding_rate -= n` shortcuts are gone; `character.bleeding` / `bleeding_rate` are now just the current HP/round (kept in sync, capped).
- Roll d100 + healer Dex//5 − min(pain, 20) ≥ DC.
- Basic bandage stops up to **3 HP/round** of wounds (DC 30), Improved **6** (DC 35), Herbal Poultice **9** (DC 40). A success stops wounds **smallest first** until the limit is used up; a wound bigger than what is left is skipped (Basic cannot stop a 4/round artery).
- A failed attempt still uses the item (existing HealingItem rule).

## Worked examples (rounds/HP from tests; one wound only, "bandaged" = a successful bandage just before round 3)
| Example | Untreated, 100 HP | Untreated, 30 HP left | Bandaged |
|---|---|---|---|
| Arm stab (cut, 1/round) | lose 3, stops | lose 3 | Basic: lose 2 |
| Thigh slash (deep 3→2→1) | lose 24 over 12 rounds, stops | **bleeds out round 5** | Basic: lose 6 |
| Thigh artery (4/round) | dies round 21 | dies round 4 | Basic cannot help (dies round 21 / 4); Improved: lose 8 |
| Throat cut (3/round, never clots) | dies round 28 | dies round 5 | Basic: lose 6 |

Cap: thigh deep + chest deep + two cuts = 7/round on paper, **5** in practice.

## Not done / open
- Race/class perk values are hooks only. `Character.take_damage_to_zone` / `receive_damage` (the old character-level path) still cause no wounds; only `CombatHealthManager` creates them.
- Nobody calls `apply_bleeding()` automatically each round yet (there was no caller before either); the game loop has to call it once per round.
- `bleed_thresholds` / `bleed_pips_by_zone` in `combat_rules.json` are still not read by any code.
- `damage_consequences.py` no longer adds `character.bleeding` (it used to add 0.3–3.6 per consequence).
- `character.py` (ogre hunger) and `healing_system.fast_heal` still do `ally.bleeding_rate += 1.0`; this no longer has any effect.
