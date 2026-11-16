# Actor data model (Foundry)

Short contract for the Breath and the Veil system, so the sheet (this workstream), inventory/encumbrance (workstream B), and art (workstream C) can land on the same actor without fighting each other.

Hidden stats are **never** stored on a Foundry actor or item and **never** shown: Faith, Virtue, Piety, Holy Fury, Corruption, Stress, Reputation. Those live only in the Python backend. Players see `felt` text only.

## Actor types

`character`, `npc`, `creature`. All three share the base block below. `character` also has `details`.

## Visible attributes

Twelve stats, each `{ value, max }` (max is the cap from `rules/stats.json` for that race/gender, after talent cap raises if any):

`strength`, `toughness`, `agility`, `mobility`, `dexterity`, `endurance`, `intelligence`, `willpower`, `perception`, `charisma`, `weapon_skill`, `ballistic_skill`.

Starting values come from the Gender item (`rules/stats.json`, e.g. `Human_Male`). Class bonuses from `scripts/character_loader.class_stat_bonuses` are then applied once and clamped to the cap. Race `*_modifier` fields in `rules/races.json` are already baked into `stats.json` and must not be applied again.

## Resources

- `resources.hp.value` / `resources.hp.max` — total hit points. Formula (from `scripts/zone_hp.hp_multiplier`):  
  `round(100 * (1 + race.hp_bonus/100) * (1 + class.hp_percent/100))`.  
  Zone HP (13 coverage zones summing to this total) is the Python source of truth for combat; the sheet in 0.2 shows the total pool. Zone breakdown is not required on this actor yet.
- `resources.stamina.value` / `resources.stamina.max` — see open question in the 0.2 notes. Inferred (not a single documented formula in the loader): `100 + race.stats.stamina_bonus + class.stat_modifiers.stamina_max_flat`.

## Details (`character` only)

- `details.race`, `details.gender`, `details.class_name` — set by dropping Race, Gender, and Class items (one of each). Gender items are race-specific (`Human_Male`, …).
- `details.background`, `details.age`
- `details.mass` — kg from `rules/races.json` (Human 80, Elf 65, Dwarf 100, Ogre 600)

## Combat (already in the model)

`combat.weapon_in_hand`, `combat.grip` (`two_hands` | `one_hand`), `combat.current_guard`, `combat.shield_equipped`.

## Felt

`felt`: array of `{ topic, text }`. Player-facing prose only, written later from the GM client / backend.

## Inventory (reserved for workstream B)

These fields exist on every actor from 0.1.1 so B can fill them in without a schema fight. The 0.2 sheet may *display* carried weight and capacity; it does not implement equip/unequip or containers.

```
system.inventory.equipped.<slot>   // Foundry item id, or "" if empty
system.inventory.backpack.itemId   // the backpack/container item id, or ""
system.inventory.backpack.contents // array of item ids stored in the backpack
system.inventory.carried_weight    // kg, computed; software overwrites this
system.inventory.carry_capacity    // kg, computed; software overwrites this
```

### Equipped slots

Three groups, all string fields on `system.inventory.equipped` (item id or `""`):

- **Armour zones** (same names as `coverage` in `rules/armors.json`):  
  `head`, `throat`, `chest`, `stomach`, `groin`, `left_upper_arm`, `right_upper_arm`, `left_lower_arm`, `right_lower_arm`, `left_upper_leg`, `right_upper_leg`, `left_lower_leg`, `right_lower_leg`.
- **Hands:** `main_hand`, `off_hand`. A two-handed weapon occupies both.
- **Worn containers:** `back`, `belt` (satchel/backpack and pouch). Reserved for B.

A worn armour item fills every zone in its `coverage` list. Two pieces may be worn together only if their coverage does not overlap (best piece per zone; PR 3's loose helm/gorget/gauntlets/greaves use these same zones). Weapon and armour items already have a boolean `system.equipped`; B should keep that flag in sync with the slot map.

Items may also record `system.location` (`body` | `backpack` | empty) and `system.container_id` (the backpack they sit in). B owns that behaviour. The actor-level `inventory.backpack.itemId` / `contents` fields are the same facts mirrored for a quick read of capacity and weight.

A dedicated `container` or `gear` item type is **not** added in 0.1.1. If B needs one (for backpacks), add it in the inventory PR.

### Carry capacity

From `rules/combat_rules.json` and `scripts/strength.py`, with race and talent multipliers already in the rules:

```
capacity_kg = (20 + strength * 1.5) * sex * race * talents
sex   = 1.15 if male else 1.0          # carry factor, not the 1.6 compound Power factor
race  = Dwarf 1.5 (rules/lore/dwarves.json), Ogre 3.0 (Logistics Beast / docs/STRENGTH.md), others 1.0
talents = Ox-Back 1.15 (rules/talents/physical.json), else 1.0
```

`carried_weight` is the sum of item `weight` values on the person (equipped + in a worn pack). Missing weapon weights are not invented (some weapons have none yet); treat missing as 0 and flag them.

Named load bands (light / medium / heavy at ratios 0.2 / 0.5 / 1.0) live in `rules/combat_rules.json`. AP and speed penalties in `rules/combat/action_economy_v0_1.json` use different thresholds (0.5 / 0.8 / 1.0) — B should keep both, not collapse them. Ogre Brute `heavy_lift` is an activated ability, not a permanent bonus.

## Art paths (workstream C)

C adds files under `foundry/system/breath-and-the-veil/assets/`. Until a file exists, the system must fall back (never Foundry's default gun art).

| Kind | Path | Fallback |
|---|---|---|
| Compendium banners | `assets/banners/<pack>.webp` | shipped dark-parchment image (same file for every pack until C replaces it) |
| Portraits | `assets/portraits/<race>-<gender>.webp` | `assets/portraits/_fallback.webp` (lowercase ids, e.g. `human-male.webp`) |
| Class icons | `assets/icons/classes/<id>.webp` | `assets/icons/classes/_fallback.webp` (id is the class key, e.g. `crusader_knight.webp`) |

## Character creation (0.2 sheet)

Dropping items onto a character actor is what fills the numbers. The software does all the arithmetic.

1. **Race** — sets `details.race`, `details.mass`, and race abilities/traits shown on the sheet. Playable-gender locks: Dwarf and Ogre are male-only (`playable_genders` in `rules/races.json`; there is no `Dwarf_Female` / `Ogre_Female` in `stats.json`).
2. **Gender** — must match the race (and that race's playable genders). Sets starting visible stats and caps from the item.
3. **Class** — must pass the class locks (`race_lock` / `gender_lock` / `allowed_races` / `allowed_genders` / `restrictions`). Applies class stat bonuses once, HP/stamina as above, starting skills, and lists class traits/abilities. Paladin is not a class; it is an honour title on the Crusader Knight order path.

Illegal drops are rejected with a visible notice; they do not leave a half-applied item on the actor. One race, one gender, one class at a time (a new drop replaces the previous item of that type and recalculates).

## What this file is not

- It does not invent a container item type, a backpack capacity, or coin-weight rules (see `rules/system/wallet_v0_6d.json` if B needs coins).
- It does not put hidden stats, even as GM-only flags, on the actor.
- Background bonuses are not applied until backgrounds exist as a pack (open question).
