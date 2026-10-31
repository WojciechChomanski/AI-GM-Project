# Strength System v1

> **All numbers are PLACEHOLDERS** for playtesting. Approved 2026-10-31. Code: `scripts/strength.py`. Data: `rules/strength_system.json`, `rules/talents.json`. Tests: `tests/test_strength.py`.

## The idea
- Humans are the realistic baseline, and the other races build on top of them.
- The Strength number is the *training level*. **Power** is what it produces.
- Human 50 is the normal peak. 55 (the Iron-Thewed talent) is noticeable but beatable. Dwarf 60 is a clear step up. Ogre 70 is a Kodiak bear: you need tools, numbers, fire and traps.

## 1. Power curve
- Up to 50, Power grows gently: `1 + (STR−30)×0.05`.
- Above 50 it doubles every 10 points: `2 × 2^((STR−50)/10)`.

| STR | 25 | 30 | 35 | 45 | 50 | 55 | 60 | 70 |
|---|---|---|---|---|---|---|---|---|
| Power | 0.75 | 1 | 1.25 | 1.75 | 2 | 2.83 | 4 | 8 |

Human→dwarf (×2) feels the same as dwarf→ogre (×2).

## 2. Male factors
| Use | Male | Female |
|---|---|---|
| Arms and grip (swing, parry, bow) | ×1.15 | ×1 |
| Legs (kick, brace) | ×1.05 | ×1 |
| Whole body (clinch, grapple, shove, drag, march) | ×1.6 | ×1 |

Dwarves (male-only) and ogres use the male factors.

## 3. Contests
- Your chance = your Power ÷ (your Power + theirs), clamped to 5–95%.
- **Allies grabbing the same target add their Power together.**
- **Flat bonuses and technique** (Weapon Skill or Agility edge): every +10 = ×1.41. +10 skill exactly cancels +5 Strength above 50.
- Mass counts **only for shove and knockdown**: × (mass ÷ 80)^(1/3).

## 4. Clinch
- Being clinched means carrying them.
- Load L = their whole-body Power ÷ yours. Each 6-second round costs 2 + 1.2×L² stamina (placeholder pool: 60).

## 5. March
- Carry capacity is unchanged (`rules/combat_rules.json`): 20 + STR×1.5, male ×1.15, dwarf ×1.5, ogre ×3.
- Load share L = load ÷ capacity.
- Cost per km = 1 + 40×L², plus 600×(L−0.5) once past half load (the cliff).
- Reserve = END × 3 (+10 for elves).

## 6. Damage bonus
- Bonus = floor(2 × arm Power).
- Results: F30 +2, F45 +3, M50 +4, M55 +6, dwarf 60 +9, ogre 70 +18.
- It replaces `gm_console` STR//5 and the ogre Grizzly Force +mass//10, which gave +60 at 600 kg.

## 7. Grip Demand (`min_STR` on heavy weapons)
- Values: claymore and the greatswords 40, warhammer and Lucerne hammer 42, polearms and great axes 36–38, flail and bill 35, improvised club 38.
- **Below the demand:** −5 parry and +10% stamina per 5 points short, plus a disarm risk on a failed parry.
- **More than 15 points short:** too heavy to fight with.
- **Double the needed Power:** half the stamina cost.

## 8. Women's edges
- Active magic (female only).
- Agility cap 60 vs 55 (exists).
- **−25% stamina on sustained static holds** (bow drawn, shield up, ledge); this does not apply to a contested clinch.
- +20% stamina regen under a light load (exists in `combat_rules.json` load_bands).
- Lower-body actions cost −10% (exists).

## 9. Iron-Thewed (human male talent)
- Strength cap 50 → 55, enforced in `Character.progress_stat`.
- Once per fight: an automatic break-free from a human-size grab (grabber ≤120 kg).

## Worked examples (verified by tests)
- **M50 vs M55 clinch:** M50 wins 41% of contests. He is exhausted in ~82 s; M55 in ~138 s.
- **M50 vs F30 clinch:** she wins 24% and is exhausted in ~25 s. **vs F45:** she wins 35%, ~60 s.
- **Grapple:**

  | Matchup | Chance |
  |---|---|
  | Human 50 vs dwarf 60 | 33% |
  | Human 55 vs dwarf 60 | 41% |
  | Dwarf vs ogre | 33% (20% with Titanic Might +20) |
  | Human vs ogre | 11% per try, ~21% to escape the 2-round rip; 20% per try with one ally pulling |

- **30 kg march, km until exhausted:**

  | Marcher | km |
  |---|---|
  | Avg man | ~15 |
  | Strong man | ~37 |
  | Avg woman | ~3 |
  | Trained woman | ~26 |
  | Elf male | ~13 |
  | Elf female | ~3.4 |
  | Dwarf | 36–90 |

## Elf stat blocks (`rules/stats.json`, placeholders)
| | STR | TGH | AGI | MOB | DEX | END | INT | WIL | PER | CHA | WS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Elf_Male start / max | 30/45 | 30/45 | 40/60 | 45/65 | 35/55 | 30/50 | 32/60 | 30/55 | 35/65 | 35/65 | 30/60 |
| Elf_Female start / max | 25/40 | 25/40 | 45/65 | 50/65 | 35/55 | 25/50 | 32/60 | 30/60 | 40/65 | 40/70 | 25/55 |

- Why these numbers:
  - **Lighter build** (65 kg): STR/TGH caps are 5 below humans.
  - **Agile and perceptive** (races.json AGI +5, Eagle-Eye): AGI/MOB/PER caps are 5 above humans. The female Agility edge is kept (65 vs 60).
  - **Approved +10 Charisma with a minimum of 30:** CHA start is human +10.
  - **Long-lived:** INT and Weapon Skill caps are higher.
