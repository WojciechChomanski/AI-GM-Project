# Breath Class Item Contract v1.0

One general actor sheet. One Class item dropped on it. Every future class uses **these exact keys**.

Source of truth for numbers and locks:

- `rules/stats.json` — race Base and Cap
- `rules/classes/<class>.json` — class bonuses, abilities, progression
- `rules/core_rules.txt` — overrides the class file if they conflict
- `rules/breath_config.json` — passive Breath numbers
- `rules/races.json` — racial magic gates

Permanent rules baked into this contract:

- Crusader Knight + vocations (Templar, Holy Judge, Cleric) = Human Male only
- Breath abilities = passive only (Virtue ≥ 70, high Piety, vs Veilspawn / abominations / major enemies of the faith)
- No active magic, spells, or Divine Smite on male classes
- Active magic = Veil Sorceress only (Female Human or Elf)

## What the general sheet reads

The actor never stores class math as five visible columns. It stores:

- Race Line item → `base_*` and `cap_*`
- Class item → `class_*` bonuses and flags
- Player types only `adv_*`
- Sheet shows `current_*` = base + class + adv, clamped to cap

If two Class items are dropped, the sheet must warn and use the first only. Class items are unique (`uniqueId = breath_class`).

## Required identity fields

- item_kind: always Class
- class_id, class_label, class_version, source_file
- power_source: Breath / Veil / Rune / None
- magic_mode: none / passive_breath / active_veil / passive_rune
- role_tags, description, lore

## Required lock fields

- allowed_races, allowed_genders, vocation_line (comma lists)
- allows_mount, unique_class

## Required stat bonus fields

Every Class item must include all of these, even if 0:
class_strength, class_toughness, class_agility, class_mobility, class_dexterity, class_endurance, class_intelligence, class_willpower, class_perception, class_charisma, class_weapon_skill, class_hp_flat, class_hp_percent, class_stamina_flat, class_stamina_percent, hp_base_override, stamina_base_override.

GM seeds: virtue_start, piety_start, faith_start, corruption_start, holy_fury_start, stress_start, reputation_start.

Flags: show_breath_block, show_veil_block, corruption_visible_to_player, breath_virtue_min, breath_requires_high_piety, breath_vs_abominations_only, veil_corruption_max.

## Ability payload

starting_abilities, passive_abilities, forbidden_abilities, abilities_json, flaws_json, proficiencies_json, progression_json.

activation values: physical, passive, passive_breath, active_veil, forbidden.

## Conflicts resolved in v1.0

crusader_knight.json still lists Smite and Divine_Surge as activated holy power. core_rules.txt forbids both for male classes. The Foundry item follows core_rules. Templar / Holy Judge / Cleric powers stay on Vocation items.
