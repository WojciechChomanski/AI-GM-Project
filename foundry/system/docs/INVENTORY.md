# Foundry inventory and carried load (0.3)

Workstream B. Python: `scripts/inventory.py`. Foundry: `foundry/system/breath-and-the-veil/module/inventory.mjs`.
Canonical numbers: `rules/inventory.json` (copied into the system as `module/inventory-rules.json`; tests require them to match).

Hidden stats are not used and must not be added to the actor or item models.

## Actor model (workstream A / 0.1.1)

This PR follows `foundry/system/docs/ACTOR_MODEL.md` (added on the 0.1.1 branch). It is based on that commit so the reserved `system.inventory` fields already exist.

- Visible stats stay on `system.attributes` and `system.details.race` / `gender`.
- After every item change the software writes `system.inventory.equipped`, `system.inventory.backpack`, `system.inventory.carried_weight` and `system.inventory.carry_capacity`.
- Where an item sits is stored on the item as `system.location` (`body` or `backpack`) and `system.container_id`, plus the existing `system.equipped` flag, as the contract asks.
- A clinch counts as carried load: set `flags.breath-and-the-veil.clinchMassKg` to the opponent's mass in kilograms (Human 80, Elf 65, Dwarf 100, Ogre 600 from `rules/races.json`). The Power-ratio clinch cost in `scripts/strength.py` is unchanged and is for stamina, not kilograms.
- New item type: `gear` (backpacks and pouches). New pack: `gear`, with the same parchment banner as the others until art arrives.
- The inventory panel is injected when the actor sheet renders (`templates/parts/inventory.hbs` + `styles/inventory.css`). A can move the panel into their sheet by calling `prepareInventory(actor)` and including that template. `registerInventory()` is one line in `module/breath.mjs`.
- Going over *character* carry capacity is allowed (penalties apply, some actions are greyed out). A drop is refused only when there is no free body slot and no room in a worn pack.

## How carry capacity is computed

```
(20 + Strength × 1.5) × sex × race × talents
```

| Factor | Value | Source |
|---|---|---|
| Base formula | 20 + STR × 1.5 | `rules/combat_rules.json` `carry_capacity`, `scripts/strength.py` `carry_capacity` |
| Male | ×1.15 | same. **Not** the ×1.6 whole-body Power factor (that is only for clinch / grapple / shove / drag / march *contests*, `docs/STRENGTH.md` section 2) |
| Female | ×1 | same |
| Human, Elf | ×1 | no carry multiplier in the race files |
| Dwarf | ×1.5 | `rules/lore/dwarves.json` `carry_capacity_multiplier` |
| Ogre | ×3 | Logistics Beast in `rules/races.json`, applied as `race_mult=3` in `docs/STRENGTH.md` |
| Ox-Back talent | ×1.15 | `rules/talents/physical.json` |

The Power curve (gentle to 50, then doubling every 10) is **not** used for kilograms. It stays on contests, damage bonus and clinch stamina.

The march "cliff" past half capacity (`scripts/strength.py` `march_cost_per_km`) is flagged on the sheet (`past_half_load`) so marching cost can stay in the backend.

Ogre Brute `heavy_lift` (+500 kg, 5 stamina, *active* ability) is **not** applied automatically.

## Load tiers (what the player sees)

From `rules/combat_rules.json` `load_bands`, plus a new **placeholder** overloaded tier:

| Tier | Load / capacity | Penalties (ported, unless marked placeholder) |
|---|---|---|
| Light | up to 20% | Women: +20% stamina regen. Men: no bonus |
| Medium | up to 50% | No drain |
| Heavy | up to 100% | Women: +30% stamina drain, −10 Dex / aim. Men: +15% stamina drain, −5 Agility. **Placeholder:** −20 to Athletics when climbing |
| Overloaded | over 100% | **Placeholder tier** (not in combat_rules). Still able to walk. Sprint and acrobatics blocked. Climb −40 Athletics (placeholder). Unaided rope climb blocked. |

A second, older table in `rules/combat/action_economy_v0_1.json` uses *different* thresholds (50% / 80% / 100%) for AP and speed. Inventory keeps those AP / speed penalties, looked up by the raw ratio, and does not rename the player's load band to match them. Overloaded AP −3 and speed −40% are placeholders (the action-economy file has no band past 100%).

## Drag and drop

1. Class, race, gender, talent, flaw, advantage and skill items are not inventory; they attach as they do today.
2. A weapon, armour piece or pack is equipped on the body if the needed slots are free.
   - Armour occupies every zone in its `coverage` list.
   - A two-handed weapon occupies both hands (types starting `2H_`; polearms, staves and the listed bows/crossbows are assumed two-handed — placeholder). Longsword follows the actor's current grip.
   - Only one item on `back` and one on `belt`.
3. Otherwise the item goes into a worn backpack or pouch that has enough free kilograms.
4. If there is no free slot and no room in a pack, the drop is refused and a message explains why.
5. Volume is only checked if both the item and the pack have a volume number. Nothing in the rules currently does, so volume is not enforced.

## Placeholder backpacks

There is no official pack list in the rules. These four `gear` items are placeholders:

| Item | Worn on | Pack weight | Holds |
|---|---|---|---|
| Belt Pouch | belt | 0.2 kg | 2 kg |
| Satchel | back | 0.8 kg | 8 kg |
| Traveller's Backpack | back | 1.5 kg | 20 kg |
| Large Pack | back | 2.5 kg | 30 kg |

## Shields

Catalogue: `rules/shields.json`. Shipped as gear items in the Foundry **gear** pack (`slot` is `off_hand`, `rules.item_kind` is `shield`). Keys: `buckler`, `targe`, `round_shield`, `heater`, `kite`, `pavise`. Weights count toward carried load. Equipping one occupies the off hand, so it cannot be used with a two-handed weapon (`combat_rules.two_handed_and_shields.allow` is false). When a catalogue shield is in the off hand, inventory sets `system.combat.shield_equipped` so the existing x1.10 block bonus applies. Per-shield coverage and block multipliers are placeholders for a later combat pass.

## Known gaps (not invented)

- `warhammer`, `longsword` and `shortsword` have no `weight` in `rules/weapons.json`. They count as 0 kg and are flagged on the sheet.
- Coin weight (`rules/system/currency_v0_6d.json`, 50 coins per kg) is not wired in yet.
- Sprint / acrobatics / climb / unaided rope-climb restrictions are placeholders (requested for 0.3, not present in the rules files).
