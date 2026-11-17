# Racial gear

Hard cultural blocks and ogre size rules. These are visible rules, not hidden stats. A race cannot equip a forbidden item: the Python engine refuses it, and the Foundry sheet refuses the drop or equip with a felt line such as “Dwarves will not bear a blade the elves use.” There is no Kinbreaker flaw and no stress or reputation taboo.

Doctrine of Spite (`lore/core/lore_master.md`): dwarves refuse swords and bows because elves use them; elves refuse guns and shields because dwarves use them. Humans use what works. This file also keeps the extra bans that were already in `rules/races.json`.

## Bans

- **Humans:** no restrictions (`forbidden_weapons` is empty).
- **Elves cannot use:** hammers, axes, crossbows (including arbalests), all gunpowder weapons, all shields.
- **Dwarves cannot use:** all swords (sabres included), shortswords, daggers, spears, all bows.
- Loose words are mapped to the real `rules/weapons.json` types and keys in `rules/racial_gear.json` `groups`. The elf shield ban looks at item type / `item_kind` `shield`, so it will apply to the catalogue in PR 37 (`feature/shields`) once that merges.
- **Dwarves can never ride.** The existing `rules/skills.json` lock is kept and the message is “Dwarves will not ride, as the elves do.”

## Ogres

Ogres have no cultural bans. Every weapon, armour and shield has `size_class` `medium` or `large` (default `medium`).

- A **medium** weapon in ogre hands is improvised: −20 skill (−50 for a dagger), no stances, maneuvers or mastery, and ×3 durability loss.
- A **large** weapon is refused to anyone of mass 150 or less. Some draft `min_STR` values sit inside the existing −15 grip grace of a human cap of 50, so size, not `min_STR` alone, is what always blocks it.
- Native large weapons: `ogre_branch`, `ogre_rock_maul`, `ogre_iron_shod_club`, `ogre_mace`, `ogre_anchor_flail`, `ogre_forge_hammer` (stats from the Breath Keeper draft).
- An axe loses 1 edge per fight without a smith (edge 0–5). At 0 it counts as a club. PLACEHOLDER.
- Rare `ogre_claymore`: master smith only, gold ×10, legendary, base 30 / 55 kg / durability 120 / min_STR 68. Some blades still bear a dwarven machine-mark from the forges that once armed vat-made ogres.
- Medium armour on an ogre covers only half its listed zones (torso first). PLACEHOLDER zone choice. Ogre templates no longer wear human `Light_Heavy` chainmail; they start in `Ogre_Scrap`.

The old `improvised_only` flag and the forced Improvised Club are gone, as is the `character.py` hard block on “small” weapons for mass over 150.

## Gunpowder (PLACEHOLDER stats)

Added for the 1580–1670 pike-and-shot era. Reload times and misfire chances were invented after the draft mid-section was truncated.

- Human: `matchlock_musket`, `arquebus`, `wheellock_pistol`, and `flintlock_musket` (for the missing `flintlock` class id).
- Dwarven: `rifled_gun`, `repeater_arbalest` (an arbalest, so elves cannot use it).
- Ogre: `hand_cannon` (large, improvised, a cut-down stolen gun).

## Class and armour fixes

- **K1** `rules/classes/rogue.json` now has `weapons_by_race`: elves get a composite bow instead of a light crossbow; dwarves get throwing axes and a crossbow instead of blades.
- **K3** missing ids: `throwing_knife`, `light_crossbow`, `composite_bow`, `wand` are real entries; `sword_1h` → `arming_sword`, `sword_2h` → `greatsword`, `staff` → `quarterstaff`, `flintlock` → `flintlock_musket`.
- **K6** `armor_preference` is now `elven` / `dwarven`, matching the lowercase variant keys in `rules/armors.json`. The loader understands those keys (and still accepts the old `mystical` / `forged` words).
- **K7** ogre brute, Rock and Gorthak no longer wear human chainmail.
- **K9** `rules/items/stonewarden_kits_v0_6b.json` is still 0 bytes and is referenced by the Stonewarden quickstart and Ansel the platewright. This PR does not invent kit content.

## Art style (from the draft)

Era look: Hybrid-Earth 1580–1650, pike and shot, plate-and-mail still in use.

- **Humans:** blackened pike-and-shot armour and Order heraldry. Temple white with a red cross, Hospital black with a white cross, Teutonic white with a black cross. Colours: undyed wool, oxblood, faded paint.
- **Dwarves:** squat, low-centred and thick-riveted, locking bands, hasps and chain motifs (a culture of binding). Fluting as in Gothic plate. Engraved geometry and maker's marks; runes are cut only by women. Blued or black steel, brass fittings, copper soul-metal inlay on elite pieces. Axes, hammers, picks, windlass arbalests, rifled guns, wheellock showpieces, pavise wall-shields. Colours: soot black, gunmetal blue, brass, rust-red primer.
- **Elves:** flowing, asymmetric laced lamellar of lacquered wood, horn and bone; beauty as a creed; masks may hide the slow rot. Bows, curved blades, knives. No gunpowder. Ritual, organic armour and veiled mounts.
- **Ogres:** a child's scrap hoard — hides, chains, broken plates, painted handprints, trophy teeth, stolen bright cloth. Colours: rust, mud, and whatever bright thing they last found. A rare vat-era piece is clean, precise and geometric, too fine for its owner.

## PR 37 (shields) merge risk

`feature/shields` is still open and was cut from `main` before this work. Both branches edit `scripts/inventory.py` and `foundry/system/breath-and-the-veil/module/inventory.mjs` (`place_item` / `placeItem`). This PR adds an optional `race` argument at the front of that function and a cultural refuse check; PR 37 adds `is_shield` / `item_kind` and off-hand placement. Expect a merge conflict in those two files, and possibly in `scripts/build_foundry_packs.py` and inventory tests. The shield *ban* itself does not depend on `rules/shields.json`: it already keys off type / `item_kind` `shield`. `docs/ACTOR_MODEL.md` is touched on both sides as well. Rule of Life files are only on current `main`; a two-dot diff against shields looks noisy, but a merge into this main should keep them.
