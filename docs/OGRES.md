# Ogres

## Lore
- **Origin:** ogres were made by the **Eldran**, the united elder race from before elves and dwarves split. They made them from **human male infants**, using Veil magic, alchemy, forbidden rituals and the dwarves' arcane machines. They grew fast, hard to kill and huge.
- **Purpose:** they were war-weapons and transport/logistics beasts against the Veil, demons, vampires, werewolves and the corrupted.
- **Mind:** like a child of 6–8. Simple loyalty to whoever feeds them, which is a dangerous mix with that strength.
- **Rarity:** very rare. No new ogres are born.
- **GM secret:** whether any of the machines still exist, and who uses them.
- **GM note (far future, not in rules):** a few ancient ogres may still be alive with their own agenda.

## Hunger (`rules/ogre_hunger.json`, `scripts/ogre_hunger.py`; hidden, backend only)
- **Daily need:** 6000 kcal (a human needs about 2500). Every 1000 kcal short adds 1 hunger point. A full day's food recovers 2 points, and each extra 1000 kcal recovers 1 more.
- **States (by points):**

| State | Points | WIL | Stress/day | Notes |
|---|---|---|---|---|
| sated | 0 | 0 | 0 | |
| peckish | 1+ | 0 | 0 | |
| hungry | 4+ | −5 | +1 | |
| ravenous | 8+ | −10 | +2 | no fast healing (not fed) |
| starving | 14+ | −20 | +3 | −1 HP/day, floor 1 |

- **Daily hidden check** from ravenous on: d100 ≤ WIL + 30 + state modifier − 5 × Hunger flaw intensity + talent `vs_hunger_rage`.
- **On a failure:** even a friendly ogre bites the nearest companion like a starving bear. That means 20 damage to an arm and +10 stress for the victim, and the ogre eats about 1500 kcal.
- **The player only sees felt text** ("Everything smells like meat.").
- **Day tick:** `time_loop.day_tick(manager, companions=[nearest first])` runs it, and ogre healing uses "fed" only below ravenous.
- **Saving:** state is saved in `character.hunger` (character_store now also saves `hunger` and `progression`).
- **Old code:** `Character.consume_food` / `reset_daily` and `healing_system.fast_heal` now go through this module. The old random 10% ally attacks are gone.

## Devouring foes (Ogre Flesh Eater only)
- **Code:** `ogre_hunger.devour(eater, victim, grabbed_or_downed)`. The numbers come from `consume_rip`: 10 stamina, heal 15 HP, +10 corruption, 15 bite damage, and it feeds 2000 kcal. The victim must be grabbed or downed.
- **Every other ogre is refused.**
- **Note:** Ogre Ravager's `flesh_rend` text still mentions a "devour heal" (+10 HP, +5 corruption). This needs the owner's call.
