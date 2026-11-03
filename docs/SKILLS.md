# Skills

Data: `rules/skills.json` (v1.0). Code: `scripts/skills.py`. Tests: `tests/test_skills.py`.
Source: SKILLS_DRAFT v0.2 + SKILL_PICKS_EXAMPLES, with the owner's decisions (2026-11-03). All numbers are placeholders for playtesting.

## The rules
- **Value** = floor(average of the linked stats). Each skill links 1 or 2 stats.
- **Creation:** 6 picks, each at base + 10. Free class and background skills (`class_free_skills`, `background_free_skills`) don't count toward the 6. Wired in as `creation.create_character(..., skills=[...], background=...)`, which returns `skills` and adds errors for too many picks, locks or a missing advantage.
- **XP** buys a skill you don't have: 100 XP, or 200 if it is trained-only. XP never raises a value.
- **Growth by use only.** It uses the stat formula `progression.uses_needed`. Failures count ×2, and a skill can gain at most +1 per session (`skills.record_use`, `skills.check_growth`). Session reset is `progression.new_session`.
- **Use bar:** every use adds 1. Ranks are at 50/150/400/900/2000 uses (Familiar … Master). The bar keeps filling while growth is gated.
- **Master gate past 50:** values above 50 have to be unlocked. `skills.teach(c, id, master_value)`:
  - The master must be at least 10 above the target.
  - Each period unlocks +5.
  - Gold = 20 × the target value.
  - Reputation must be 20 (up to 60), 40 (up to 75) or 60 (up to 95).
  - It only raises the ceiling. The value still has to grow by use.
- **Order/Tribunal masters:** `teach(..., master_of="order"|"tribunal")` counts the character's standing on a matching Order path (Crusader Knight, Warden, Penitent, contractor → order; Holy Judge → tribunal) if it is higher than general reputation.
- **Cross-race teaching** is the only way to get a race-locked skill (for example a Dwarf learning Elven Bowcraft): 5× gold, +30 reputation, and +2 per period. **Gender locks are absolute** (Spellcraft and Runecraft follow the magic rules).
- **Tools cap the usable value:** none 30, field kit 50, proper tools 70, workshop 95. Above the cap, uses still fill the bar but don't raise the value.
- **Untrained use:** trained-only skills can't be used (`effective_value` returns None), with one exception: a basic bandage at half value. Common skills work at half value.
- **Medicine:** the use-bar rank gives +5 per rank to surgery and bandaging (`limb_repair.medicine_bonus`). Perks:
  - R2: the bandage takes 1 round less (data only, since bandaging has no rounds yet).
  - R3: infection chance from your own failed surgery is halved (wired in).
  - R4: a field kit counts as proper tools for surgery (wired in).
  - R5: 1 re-roll of a failed surgery per day (data only).
- **Excluded:** Prayer/Rites, until the Cleric is redesigned.

## Compatibility
- **Characters without `progression['skills']`** (everything that exists today) behave exactly as before. `skills['medicine']` stays a 0–5 rank, and `skills['surgery']` still overrides.
- **New-system characters:** surgery uses the Medicine value capped by the tool tier. Untrained surgery is refused. `sync_legacy` mirrors the Medicine rank into `skills['medicine']`.
- **Weapon ranks in class files** (swordsmanship, shield_defense, club_smash) become a weapon-mastery head start (`weapon_head_start`) instead of skills.

## Invented (please check)
- Background free skills: Noble Etiquette, Hunter Survival, Scholar Lore: History, Outlaw/Street Deception, Escort Etiquette.
- Class free lists for Warrior, Stonewarden, Veil Sorceress, Outlaw and Holy Judge.
- Head-start sizes (rank 1–2 = 50 uses, 3+ = 150).
- Lore is split into 3 skills, which makes 30 entries in total.
- Dwarves can't take Riding.

## Foundry
- `rules/skills.json` → `skills` is a flat `{id: {name, stats, trained_only, tools, restrictions, description}}`, so it can be turned straight into `skill` Items.
- PR 14 (not merged) still builds its skills pack from class files. Once both are merged, `build_foundry_packs.py` should read `rules/skills.json` instead (a small follow-up).
