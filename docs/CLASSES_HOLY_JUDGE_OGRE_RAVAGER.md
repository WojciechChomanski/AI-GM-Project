# Holy Judge and Ogre Ravager (class files v1.0)

## What was wrong

Two class files each contained a second class:

| File | Also contained | That class's own file |
|---|---|---|
| `rules/classes/holy_judge.json` | a full copy of Outlaw_Mercenary_Warrior | `outlaw_mercenary_warrior.json` |
| `rules/classes/ogre_ravager.json` | a full copy of Ogre_Behemoth | `ogre_behemoth.json` |

- **Nothing was lost.** Both copies were checked to be identical to the class's own file, so the copies were removed.
- `holy_judge.json` and `ogre_ravager.json` now each hold only their own class. A test (`tests/test_class_files.py`) fails if any class key appears twice or sits in the wrong file.

## Sources searched

- Git history of both files on `main`, the feature branches, and `backup/main-pre-isolation-20260916`. `dev` was not read.
- There is only one historical version of each file, the same content as before this fix, except one backup with older formatting.
- Also searched: `lore/`, `docs/`, `rules/core_rules.txt`, `rules/class_tags.json`, `README.md` and `rules/classes/crusader_knight.json`.

## Holy Judge (Human Male, Crusader Knight Order vocation)

**Kept from the old file:**
- description and lore (the description was shortened)
- WIL +3 and INT +2, scaled ×3 like every legacy class, giving **WIL +9, INT +6**
- Divine Clarity (+10 Perception vs deception)

**Taken from `crusader_knight.json`:**
- the tier 5 Order_Vocation (Holy_Judge gains Discern_Sin and Final_Verdict)
- their exact definitions
- the piety roll

**Changed to obey `core_rules.txt`** (vocations are Human Male only; Breath is strictly passive; no manual holy bursts):

| Old | New |
|---|---|
| **Judgment Call**: active, 9 stamina, 12 holy damage, +15 vs corrupted | **Judgment** (passive Breath trigger) |
| **Purge Verdict**: active, 12 stamina, removes status effects | **Purge Verdict** (passive) |

- **Judgment** works only at Virtue ≥ 70, with high Piety, against Veilspawn, an abomination or a confirmed major sinner. Effect: +4 damage, and the target's Fear tests against him are at −10.
- **Purge Verdict** triggers after a just Final Verdict at Virtue ≥ 70. Allies within 6 m lose Fear and the Veil effects salt_kiss, taint_mark and brine_marks.

**INVENTED (marked in `meta.invented` in the file):**
- PER +6
- the Judgment and Purge Verdict numbers
- proficiencies, the three tiers (Inquisitor_Novice → Judge → High_Judge) and their requirements
- the skills intimidation and lore_theology (ids from rules/skills.json)
- the flaw Feared_By_The_Flock (−10 CHA with common folk)
- `healing_bonus 2` was dropped, because its meaning is unknown

`scripts/healing_system.breath_purge` (Cleric/Holy Judge, 10 stamina) is old code that makes it active. It's unchanged here; see the questions in the PR.

## Ogre Ravager (Ogre Male)

- All content is kept: description, lore, flesh_rend, devour_charge, gluttons_vitality, XP table and level-up stats.
- Moved into the d100 layout: `race_lock`, `gender_lock` and `stat_modifiers`.
- Stats: STR +4, TOU +3 and DEX −2, scaled ×3, giving **STR +12, TOU +9, DEX −6**. These are the same bonuses the loader already applied.
- No new numbers.

## Loaders

- `character_loader.find_class` already searched every file (case- and space-insensitive), so `Rock.json`'s "Ogre Ravager" now gets the d100 block.
- `gm_console.get_class_data` falls back to the first class-like block. It now always finds the right one, because each file holds a single class.
