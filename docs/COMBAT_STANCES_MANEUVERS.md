# Combat: guards, maneuvers, damage types, armour and weapon perks

Owner decisions t97u/t98u/t99u. Code: `scripts/combat_techniques.py` (one source of truth), used by
`scripts/combat_engine.py` (`/combat/attack`). Tests: `tests/test_stances_maneuvers.py`.

## Files
| File | What it holds |
|---|---|
| `rules/stances.json` | Generic stances: offensive +3 atk/−3 def, defensive +5 def/−3 atk, neutral. Used when a weapon has no guards (daggers, bows, improvised) or when a caller passes `offensive/defensive/neutral`. |
| `rules/weapon_stances.json` | `_meta.guard_change.stamina_cost` = **1**; `guard_sets`: 2H_sword (10), 1H_sword (6), 2H_hammer (3), 1H_blunt (3), axe (3), polearm (4), dagger (3, Fiore). |
| `rules/weapon_maneuvers.json` | Maneuvers per guard set, effect keys documented in `_meta.effect_keys`. |
| `rules/damage_types.json` | Slashing / piercing / blunt trade-offs; `armor_piercing` (the one tunable value, perk/trick bonus, durability x2). |
| `rules/weapons.json` | Every weapon: `damage_type` (primary), `damage_types`, `guard_set`, `stance_tree`, `features` (point/beak/hook/chain), `armor_piercing` (true/false), `two_hand_guard_set` (longsword), `stamina_cost`. |
| `rules/armors.json` | `armor_rating` per type (rebalanced, below) and `rigid` (plate). |
| `rules/weapon_perks.json` | Per-family perk ladders and global caps. |

Old duplicates: `stance_logic.py`, `adventure_new.stance_mods`, `adventure.stance_mods`, `maneuver_engine.py`,
`maneuver_handler.py` now all read through `combat_techniques`. The old ±10 stance values in adventure*.py are gone.

## One attack (combat_engine.attack_roll)
1. Guard: attacker's `stance` (a guard id in the weapon's `stance_tree`, or a generic stance). Unknown guard → the weapon's default guard (noted).
2. Guard change: `previous_stance` ≠ `stance` costs 1 stamina unless a free change is left (Fluid Guards) or Seamless Guards is used.
3. **One maneuver**: `maneuver` = name (used if valid), omitted = the best valid one, `false` = none. Matching accepts lists for guard and trigger (fixes Disarm Attempt / Aimed Head Strike). Trigger comes from `trigger` (`always`, `after_parry`, `after_block`, `after_dodge`).
4. Attack = d100 + skill + mastery to-hit + DEX/10 + guard + maneuver − aimed penalty (−30, −40 head/throat/groin, minus relief capped at 5) − disabled-arm penalty − stress − pain.
5. Defence = d100 + DEX/10 + defender's guard + counter bonus − unbalanced − disabled leg − stress − pain; shield block ×1.1 unless the maneuver ignores or has stripped the shield.
6. Hit: zone = aimed zone, or the maneuver's `target_zone` (least protected of a list), or none (all armour layers count).
   Damage type = the maneuver's type, else the requested `damage_type`, else the weapon type that gets most through.
   Damage = weapon + mastery + type trade-off + maneuver `damage_bonus` + perk bonus vs light armour (total mastery damage ≤ +2).
   Armour per layer covering the zone = rating × (1 − bypass) − armour defeat (≥0). Percussive weapons cutting rigid armour use its blunt rating if lower.
7. Effects (limb disable, disarm, lose next maneuver, unbalance, initiative, strip shield, counter defence) come back as
   `defender_conditions` / `attacker_conditions`. The engine is stateless: **the caller stores** `fight_state`, the conditions
   and `defender_disarmed` and sends them with the next call.
8. Stamina spent = weapon cost + maneuver extra + guard's offensive modifier + guard change, with mastery/perk reductions capped at −2 and a floor of 2.

Crits are never changed by maneuvers or perks (no crit keys exist; the old "+20% crit" and "crit chance" were removed).

## Damage types (rules/damage_types.json)
| Type | Plus | Minus |
|---|---|---|
| Slashing (cut) | +2 damage where the zone's slashing armour ≤ 2 (bare, cloth); bleeds | Armour rates highest against it |
| Piercing (thrust) | Armour rates lower (mail rings, plate gaps); half-sword, beak, spike | −1 damage (narrow wound) |
| Blunt (impact) | Armour rates lowest (shock passes through); 25% more pain | Rarely bleeds; heavy weapons, few guards |

Swords carry slashing+piercing, so they are versatile. There is no multi-type modelling beyond this: a weapon lists the
types it can deal and the engine uses whichever gets the most through.

### Armour piercing (t99u: one mechanic)
`armor_piercing` is a weapon property (true/false). The **one tunable number** is `rules/damage_types.json →
armor_piercing.value` (now **5**).
- **Who has it:** every axe (one- and two-handed and thrown; a small axe is the same as a big one), the halberd, poleaxe, bardiche, Lochaber axe, bill, lucerne hammer, war hammer, mace, morning star, flail, chekan and the new **war pick**.
- **Who doesn't:** swords, daggers, spears, lances and staffs.
- **Effect on hits:** each armour layer covering the hit zone protects `value` less (never below 0), whatever the damage type. This replaced both the old percussive rule and the impact armour-defeat; they no longer exist, so nothing stacks.
- **Perk and trick:** the Through the Plate perk adds +1 (max value+1). Crater gives value+2 once per fight (the one trick).
- **Durability:** a hit that the armour absorbs costs each counted layer max(1, 20% of the damage) durability. Armour piercing doubles that (`durability_multiplier` 2). Armour durability already existed per zone (`scripts/armor_system.py`, permanent wear in docs/DURABILITY.md). `armor_vs_aimed`, `armor_vs_spread` and `ArmorPiece.absorb_damage` take `armor_piercing=True`. The stateless `/combat/attack` returns `armor_wear: [{armor, zone, durability_loss}]` for the caller to apply.

## Armour by damage type (standard variants; elven same as standard unless noted, dwarven +1)
| Armour | Old S/P/B | New S/P/B |
|---|---|---|
| Veil Wraps | 0/0/0 | 0/0/0 |
| Padded Cloth | 2/1/1 | 3/2/1 |
| Reinforced Cloth | 3/2/2 | 4/2/2 (Lamellar 5/3/2, Iron-Bound 5/3/3) |
| Light Chainmail | 5/4/3 | 7/4/2 (Heavy Chainmail 8/5/3) |
| Brigandine | 6/5/4 | 8/6/3 (Steel 9/7/4) |
| Scale Mail | 7/6/5 | 8/6/4 (Forged 9/7/5) |
| Breastplate | 8/7/6 | 11/8/5 (Forged 12/9/6) |
| Half Plate | 9/8/7 | 12/9/6 (Forged 13/10/7) |
| Full Plate | 10/9/8 | 14/10/7 (Forged 15/11/8) |
| Siege Plate | 11/10/9 | 15/11/8 (Rune-Forged 16/12/9) |

Results (combat_engine, standard Full Plate 14/10/7, average hit, no perks, armour piercing 5). Bare skin in brackets:

| Weapon | Type used | Through plate | (bare) |
|---|---|---|---|
| Arming sword / longsword / estoc | piercing | 0 | (11 / 12 / 8) |
| Greatsword | piercing | 1 | (14) |
| Greatsword Mordhau | blunt | 3 | |
| Greatsword Half-Sword Thrust (8 stamina) | piercing | 6 | (11) |
| Battle axe / tabar (1H) | slashing | 2 | (13) |
| Dane axe | slashing | 5 | (16) |
| Mace | blunt | 8 | (10) |
| Halberd | piercing | 8 | (16) |
| Morning star / war pick | blunt | 9 | (11) |
| Poleaxe | blunt | 11 | (15) |
| War hammer | blunt | 16 | (18) |

A test (`test_full_plate_swords_clearly_worse_than_axes_hammers_maces`) keeps every sword's normal blow below every
armour-piercing weapon against plate.

### Why (history, briefly)
- **Plate vs cuts:** good hardened plate was practically immune to cuts. Test literature finds a sword cut far short of the energy needed to cut through 1.5–2 mm of steel, so the high slashing rating stands (e.g. Alan Williams, *The Knight and the Blast Furnace*, 2003; Tobias Capwell's work on English armour). The fencing books agree: Liechtenauer's armoured combat (*Harnischfechten*, Ringeck/Lecküchner glosses) and Fiore's *armizare* both switch to the **half-sword**, thrusting into gaps (armpit, visor, palm, groin), and to the **mordhau** pommel/cross blow. Hence piercing is lower, armour bypass comes from half-sword maneuvers, and the Mordhau is blunt but at −2 because a hilt is a poor hammer.
- **Mail:** riveted mail over padding stops cuts very well but lets narrow points through rings, and transmits blunt force. So mail has high slashing, medium piercing and low blunt.
- **Gambeson/cloth:** good against cuts, weak against thrusts and blows.
- **Impact weapons:** flanged maces, war hammers, the poleaxe and the bec-de-corbin spread in the 14th–15th centuries precisely as answers to plate (concussion through the helm and the beak/spike for joints). That gives blunt the lowest rating, armour piercing and Ringing Blow. Axes and halberds concentrate a heavy head on a small edge or spike (Le Jeu de la Hache treats the poleaxe as the armoured fighter's weapon). The owner's view (t99u) is that an axe, hammer or pick is simply a better tool for breaking into armour and damaging it than a sword, whatever its size. Hence the same armour piercing and the x2 armour wear.
- **Filled in (no source data):** all exact numbers; mace and axe guards (no surviving treatise); Dane axe use; the
  pain ×1.25 for blunt; the +2 cut bonus on bare skin; the −1 thrust damage.

## Guards and maneuvers
- **2H_sword** (all greatswords, and the longsword held in two hands, i.e. no shield and `grip` not `one_hand`; all 10 guards). From Liechtenauer and Fiore:
  - vom_tag: Zwerchhau, Mordhau, Krumphau
  - half_sword: Absetzen, Half-Sword Thrust (now normal, cost +2)
  - wrath_guard: Durchwechseln, Aimed Leg Strike
  - ochs: Scheitelhau
  - pflug: Schielhau
  - posta_di_fenestra: Exchange Thrust
  - porta_di_ferro: Break Thrust
  - dente_di_zenghiaro: Underhand Thrust
  - New: Alber Counter (alber) and Fendente (posta_di_donna)
- **1H_sword** (6 guards):
  - Thrust, Parry and Riposte (no crit change), Pommel Strike (blunt, disrupts), Disarm Attempt (25%)
  - Aimed Head Strike: the old +8 and +20% crit are replaced with 5 less aimed penalty
  - Oberhau, Unterhau, Mittelhau
- **2H_hammer** (war hammer). The owner's names are kept and defined after Le Jeu de la Hache:
  - crater_maker (high): Crushing Blow
  - counterweight (short haft): Haft Parry and Queue Strike, Hook the Leg
  - impact_form (middle): Beak Thrust
- **1H_blunt** (mace, morning star, flail, chekan): high, hanging and middle guards. Maneuvers: Overhead Smash, Helm Ringer, Beak Thrust (chekan), Haft Check, Around the Shield (flail).
- **axe** (1H and 2H axes): high, low and middle guards. Maneuvers: Overhead Chop, Bearded Hook (strips the shield), Leg Chop, Haft Thrust.
- **polearm** (halberd, poleaxe, bill, glaive, spear, lance, lucerne hammer, staffs). Fiore guards: Posta di Donna la Sinestra, Posta Breve la Serpentina, Tutta Porta di Ferro, Dente di Zenghiaro. Maneuvers:
  - Overhead Blow
  - Spike Thrust (needs a point)
  - Hook and Pull (needs a hook)
  - Queue Strike
  - Haft Bind (15% disarm)
- **dagger** (all daggers), from Fiore's dagger section: sopramano (overhand, offensive), mezana porta di ferro (neutral, default), posta longa (defensive). Maneuvers: Fendente Stab (piercing, bypass 0.25), Sottano Thrust (stomach/groin), Arm Bind (after a parry or block, 20% disarm). The numbers are filled in.
- **Without guards:** bows, thrown weapons and the improvised club use the generic stances only.

## Mastery perk ladders (rules/weapon_perks.json)
Every family follows the same ladder (50/150/400/900/2000 uses) and ends with 7 perks:
- Rank 1: one automatic perk.
- Rank 2: **+5 to hit** (every family), plus pick 1 of 2.
- Rank 3: two automatic perks.
- Rank 4: one automatic perk, plus pick 1 of 2.
- Rank 5: pick 1 of 2.

`progression.choose_perk(c, family, rank, id)` makes a pick, and picks are permanent. Ladders exist for greatsword, one_hand_sword, warhammer, mace, axe and spear (polearm). Dagger, bow, crossbow, thrown, gunpowder and the two_hander style keep the old generic gains.

Perks only improve existing maneuvers:
- cheaper (stamina)
- usable after more triggers or from more guards
- smaller guard penalties or a better aim
- impact families only: armour defeat +1

**Picks at a new rank:** the GM console lists the waiting picks after `load`, `status` or `tick` (and with `perks <name>`). `pick <name> <family> <rank> <id>` records one (`progression.pending_perk_picks`, `choose_perk`).

**Caps, enforced in code:**
- to hit +5, damage +2, defence +5
- stamina reduction −2, with a floor of 2 per attack
- aimed relief 5 in total
- armour piercing: weapon value +1, or +2 once per fight (Crater)
- one trick per fight
- crits are never changed
- only the family of the weapon in hand counts

## Foundry VTT (CSB)
`python scripts/foundry_export.py` writes `foundry/csb/weapons_items.json` and `foundry/csb/armor_items.json` (contract:
`foundry/csb/WEAPON_ITEM_CONTRACT.md`). See that file for what CSB can and cannot do on its own.
