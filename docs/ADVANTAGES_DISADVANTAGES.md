# Advantages & Disadvantages (v0.1, PLACEHOLDER numbers)

Source draft: approved by the user 2026-10-31 (all 10 decisions YES), with corrections below.

## Data
| File | Content |
|---|---|
| rules/creation/flaws.json | 23 general + 18 race/gender/class set disadvantages; `cp:"intensity"` (1-5), `area`, `hooks`, `restrictions` (race/gender/class) |
| rules/creation/advantages.json | 12 talent_ref + 12 general + 18 set advantages; `forbidden_classes` |
| rules/creation/creation_rules.json | diminishing returns, same-area, heavy load, buy-off, NPC generator |
| rules/creation/social_reactions.json | Elf/Human/Dwarf/Ogre reactions by intensity |
| rules/creation/addiction.json | withdrawal clock, death rule, spiral, indulgence |
| rules/orders/crusader_vows.json | vows, discipline ladder, hidden Breath tiers, steel rule |
| rules/corruption_marks.json | stages, marks, visibility, corrupted-creature HP |
| rules/stat_visibility.json | GM-only stats + fiction bands |

## CP rules
- Flaw CP: 1st-2nd flaw (by CP, high first) full, 3rd-4th half (rounded down), 5th+ 0 (story only; effects still apply).
- Same area (e.g. two `legs` flaws): only the highest pays.
- Cap 10 CP from flaws + 5 free. Total intensity >= 12: start with +10 stress.
- Crusader Knight: no Profession, no Resources (vows). 12+ years of Order training is why he starts STR ~47.

## Hidden stats
Faith, Virtue, Piety, Holy Fury stacks and Corruption are GM-only. `creation.player_view()` strips them; the player
gets fiction bands (stat_visibility.json) only.

## Corruption visibility (follows the existing veil_sorceress.json table)
10/25 hidden, 50 subtle (under clothing; Witch-Sight / Discern Sin / exam), 75 visible ("friends notice something is
wrong"), 90 unmistakable, 100 lost. Marks are permanent: tracked by the PEAK value; purging lowers current only.

## Corrupted creatures
`pool = natural_hp * M` (M default 3, range 3-4 undecided). `effective = normal + breath * M`; dead when
`effective >= pool`. Wound/pain penalties use `min(1, effective / natural_hp)` so it still degrades.

## Crusader Breath (hidden)
Full: Virtue >= 70, Piety >= 70, Corruption <= 24, vs Veilspawn/abominations/demons/corrupted: bypasses undying
(damage x M), bleed x1.5, creature heals x0.5, pain x1.5, no regeneration of his wounds, creature morale -10 / avoids him.
Dim (Virtue >= 40, or corruption >= 25): Holy Fury 2 only. None: nothing. **Steel rule:** never lowers his weapon damage.

## Addiction
Indulging: -2 stress for anyone; a knight loses Virtue (vice_drunkenness 4 / vice_drugs 5). Daily stress = intensity.

## Wired vs data-only
Wired: creation.py (intensity, dict flaws, advantages, class, diminishing/same-area/heavy load, vows, player_view,
options_for); corruption.py; knight.py; addiction.py; combat_engine attack_roll (corrupted defender pool + Breath
x M and pain); character.py virtue/piety/corruption_peak attributes.
Data-only: social reactions, bleed/heal/regeneration/morale Breath effects (no bleed/heal loop in engine yet),
discipline ladder, spiral, buy-off, NPC generator, hooks, most set-flaw effects text.
