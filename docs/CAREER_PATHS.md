# Career paths and Order paths

Data:
- `rules/orders/paths.json` (Order paths)
- `rules/careers.json` (evolutions for every class)
- `rules/classes/knight.json` (new worldly Knight)

Code: `scripts/order_paths.py`, `scripts/careers.py`. Tests: `tests/test_career_paths.py`.
Source: breath-audit/ORDER_PATHS_DRAFT.md v0.1, approved (t104u). All numbers are placeholders.

## Core rules
- **Staying is a full career.** Every class can stay on its starting path to the end and keep progressing through class tiers, Order ranks, skills and mastery.
- **Evolutions** (2–3 per class) open skills (learned at base value, no XP) and abilities. They **never** re-apply class stat modifiers or raise caps. A `to_class` evolution changes the class name and nothing else.
- **Plausibility gate:** `raised_by_order` is set only by starting in an Order-raised class (Crusader Knight, Holy Judge, Cleric), because the Order takes them at 6–7.
  - Only those characters can enter Order paths or classes or a preacher evolution.
  - Everyone else (mercenary, bounty hunter, bandit, assassin, outlaw…) can at most become an **Order contractor** (Hireling → Trusted Contractor → Friend of the Order): paid work and favours, no vows, no Breath.
  - Transitions are lists per class in `careers.json`, not ad-hoc checks.
- **Promotion limits:** at most 1 rank per arc, a minimum number of sessions per rank, deeds, Order reputation, sometimes an Order task (refusing one costs reputation and starts the discipline ladder) or a story event.
- **Hidden values:** Virtue, Piety and Corruption are checked only in the backend. The player gets felt text ("You feel no certainty that you are worthy.").
- **Paths are exclusive.** Changing path loses the old rank and its benefits. There is **one switch-back** per character: back to rank 1, −20 reputation and a penance task.

## Order paths
- **A starting Crusader Knight** begins on the path as a Brother-Knight (rank 1, class tier 2). Squire is a pre-game background only.
- **Paladin (honour title, not a class or rank).** `rules/classes/paladin.json` is retired.
  - **Who:** a Crusader Knight of rank 2+ (Knight-Sergeant). This is the first proven field rank; Preceptor is an administrative post.
  - **Requires:** 4 sessions at rank, 3 Veil foes slain, reputation 40, hidden Virtue/Piety 75 and Corruption ≤10, and the chapter's confirmation.
  - **The title is not a promotion**, so it does not use the 1-rank-per-arc limit.
  - **Passives, only while his Breath is full:**
    - Veil/corruption gains on him ×0.75
    - +10 to his Fear tests vs Veil-born
    - allies within 6 m get +5 morale vs Veil-born
    - creatures he wounded can't regenerate his wounds for 1 more round
  - **No actions and no damage.** The title is revoked at discipline step 2+.
  - **Code:** `order_paths.grant_paladin` / `paladin_passives`.
- **Crusader Knight:** Brother-Knight → Knight-Sergeant → Preceptor → Marshal → Grand Commander. It gives hospitality, armourers, sergeants, a commandery, a lance and a council seat. It costs vows, alms, summons, being bound to a region and politics.
- **Holy Judge** (the Tribunal, outside the hierarchy): Inquisitor-Novice → Judge → High Judge (1 Witness) → Lord Inquisitor. The Writ grows from commoners up to Order officers.
  - **Starting as a Judge:** counts as a former Squire-Sergeant (class tier 2, tier 1–2 abilities plus Discern_Sin and Final_Verdict), with hidden Virtue/Piety 60/60.
  - **Converting:** needs knight tier 3+, 3 just Discern_Sin results and hidden 60/60.
  - **Unjust verdicts:** each costs hidden Piety −20 and Virtue −15 and reputation −25. At Lord Inquisitor, one unjust verdict means expulsion.
- **Executioner's Bond** (authority only):
  - With the bonded blade carried openly: the Writ applies, +10 Intimidation/Etiquette to compel, and lesser authorities make a hidden WIL test to defy him.
  - Final_Verdict is lawful only with the bond blade; otherwise it is a `needless_killing` Virtue event.
  - Losing the blade means −10 reputation and the Writ is suspended until the blade is reconsecrated.
  - Damage bonus is always 0. It uses normal greatsword/axe mastery.
- **Warden of the Marches:** Watchman → Marcher Knight → Warden-Captain → Lord Warden. Veil hunters at the swamp watch-forts. They get Lore: Veil and Survival and a felt Veil dread. Costs are no court life, answering breaches, and hidden Stress.
- **Penitent Brother** (fallback): taken at discipline steps 2–3 instead of expulsion. Light armour, no horse, the hardest tasks. Redeemed → back to Crusader Knight rank 1 (does not use the switch-back). Step 4 still expels.

## Evolutions per class (placeholders unless noted)
| Class | Stay | Evolutions |
|---|---|---|
| Crusader Knight | Order ranks + tiers 1–5 | Holy Judge (final), Warden of the Marches (final) |
| Holy Judge | Judge ranks | none (switch back to the Knight once) |
| Cleric | on hold | none |
| Knight (new, worldly) | Squire → Knight Bachelor → Banneret → Lord | Knight Errant, Castellan/Marcher Lord, Church-Paid Sword (contractor) |
| Warrior | tiers + mastery | Sergeant-at-Arms, Duelist, Knighted for Valour (→ Knight) |
| Outlaw Mercenary | tiers + mastery | Mercenary Captain, Bounty Hunter, Bandit Chief |
| Rogue | tiers + skills | Assassin, Spy/Informant, Guild Thief |
| Mage | levels + spells | Court Magus, Hedge Witch, Veil Scholar |
| Veil Sorceress | spell mastery | Veil Seer, Coven Mistress |
| Stonewarden | tiers | Hold Engineer, Gate Thane |
| Ogre Brute | tiers | Ravager, Stormbreaker, Behemoth (→ those classes) |
| Ogre Behemoth / Ravager / Stormbreaker / Flesh-Eater | tiers | Gut-Guard / Tyrant / Siege Master / Gorger |

## Worldly Knight (`rules/classes/knight.json`, invented parts in meta)
- **Who he is:** Human Male, needs the Noble background (or is knighted from Warrior). No vows, no Breath.
- **Stats:** STR 10, TOU 9, AGI 5, WIL 5, CHA 6, stamina +8, HP +10%. That is the Crusader's profile minus the Order's edge, plus CHA.
- **Equipment:** the same weapon and armour access, plus axe and warhammer.
- **Obligations:** liege, feudal duty (one arc in four), honour reputation with the nobility, and lands from Banneret on.
- **Church work:** he may take Church pay only as an Order contractor.

## Plugging in
- **Creation:** `create_character` returns `career` {raised_by_order, start_path}. `order_paths.start_at_creation(c, class)` sets the state.
- **State:** `progression['order']` and `progression['career']`.
- **Session and events:** call `record_session` each session and `record_deed` / `add_reputation` from events.
- **Foundry:** path and rank are visible fields; Virtue/Piety stay server-side.
