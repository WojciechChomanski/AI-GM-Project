# Character creation, growth and mastery (v0.1)

> **All numbers are PLACEHOLDERS** for playtesting. Approved by the owner 2026-10-31 (all 10 decisions yes).
> Code: `scripts/creation.py`, `scripts/progression.py`, `scripts/talents.py`. Data: `rules/creation/flaws.json`, `rules/talents/*.json`, `rules/progression.json`, `rules/stats.json`. Tests: `tests/test_progression.py`.

## 1. Creation Points (CP)
- Everyone gets **5 free CP**. Flaws give more, **max 10 CP from flaws**, so **15 CP total** at most.
- 1 CP = +2 to one stat, max +5 per stat at creation, never above the cap. Talents cost 2-5 CP.
- `creation.create_character(race, gender, flaws, talents, stat_buys)` returns final stats, caps, CP and a list of rule errors (empty = legal).

## 2. Flaws (`rules/creation/flaws.json`)
13 flaws: Lost Eye 4, Lost Fingers 2, Lost Hand 5, Limp 3, Paranoia 3, Weak Lungs 3, Night-Blind 2, Hunted 2, Hard of Hearing 2, Hot-Blooded 2, Old Debt 1-3 (GM sets), Ugly Scarring 1, Veil-Tainted 3 (women only).
Number effects (stat or cap changes, starting corruption) are applied by `creation.py`. Situational effects (darkness, blind side, ambushes) are text for the GM for now.

## 3. Talents (`rules/talents/`, one file per group)
physical, martial, mind, veil (women only), racial: 16 talents. Max **2 at creation, 4 ever** (later only from story milestones).
A talent may raise a cap by **at most +5** (enforced in code). Locks: Iron-Thewed and Battle-Born human men; Ox-Back human/dwarf men; Light-Footed human women and elves; Veil-Gifted and Blood-Calm women; Stone-Born dwarves; Old-Blood ogres; Thorn-Trained elf men; Hawk-Eyed not with Lost Eye.
**Iron-Thewed** (moved from `rules/talents.json`): STR +3 at start, STR cap 55, STR grows 25% faster, once-per-fight break-free kept.

## 4. Use-based growth (`scripts/progression.py`)
- +1 needs `30 + (current-30) x 12` uses (minimum 30); **x2 in the last 5 points** before the cap. Human male STR 45->46 = 420 uses.
- **Max 1 point per stat per session** (`new_session()` resets it). Failures count double.
- Counters are now **per character** (`character.progression`), not shared. `adventure_new.py` keeps its old calls but stores on the character.
- Talent "25% faster" = uses x0.75.

## 5. Ballistic Skill
New stat `ballistic_skill` in `rules/stats.json`: human male 25/50, human female 30/55, dwarf 30/55, ogre 15/30, elf (both) 35/60. Bows, crossbows, slings and thrown weapons use it instead of Weapon Skill in `combat_engine.attack_roll`. STR still sets thrown range and damage.

## 6. Mastery
Families: greatsword, warhammer, mace, axe, one-hand sword, spear, dagger, bow, crossbow, thrown, gunpowder. Style tracks: shield, dual wield, two-hander.
Ranks at **50 / 150 / 400 / 900 / 2000** uses: stamina -1, +5 to hit, stamina -1, +1 damage, one trick.
Shield: block +5, stamina -1, block +5, bash +1 damage, trick. Dual wield: off-hand penalty shrinks 5 per rank (assumed base -25, so 0 at rank 5).
**Hard ceiling:** +5 to hit, +1 damage, -2 stamina (never below 2 per attack), one trick. Families do not stack; two-hander and weapon family take the best of each.

## 7. Rescaled to d100
- `rules/backgrounds.json`: old `+1`-style modifiers x3, old `_bonus` values halved, now plain stat keys (e.g. Noble CHA +5, INT +3). These now actually apply in `character_loader` (the old keys never matched a stat).
- Action points (`rules/combat/action_economy_v0_1.json` v0.2): `6 + floor((AGI-25)/15)`, min 4: AGI 20 = 5, 25 = 6, 40 = 7, 55-60 = 8.

## Wired vs data-only
Wired: talent caps in `Character.progress_stat` and growth; per-character growth in `adventure_new.py`; Ballistic Skill and mastery to-hit/damage in `combat_engine.attack_roll`; ballistic_skill/flaws/progression loaded by `character_loader`.
Not wired yet: mastery stamina savings in the stamina spend code, recording mastery uses during fights, tricks, shield block bonus in block rolls, AP formula (no code reads the action economy yet), situational flaw effects, Ox-Back/Quick Hands/Steady Aim/Survivor/Iron Will/Blood-Calm effects, flaw cap penalties in `progress_stat` (they apply in `creation.caps_for`), and talent start bonuses in `character_loader` (characters built with `creation.py` carry final stats).
