# Costly magic (decisions and placeholder numbers)

Implemented on the `feature/magic-costs-vessels` branch after the user answered the questions in the draft. Questions 1–3 were skipped: **no** extra nosebleed or health cost on ordinary spells, **no** new year-of-life costs, **no** beauty-magic that hides ageing. Those stay as they were.

Mage and Veil Sorceress remain two classes.

All numbers below are **PLACEHOLDER** and should be tuned after play. Hidden tracks (Corruption, blood-vessel bonds) live only in the Python backend. They are never stored or shown on a Foundry actor.

## Stamina (decision 8)

The confirmed formula is unchanged:

```
max stamina = 100 + race.stats.stamina_bonus + class.stat_modifiers.stamina_max_flat
```

Veil Sorceress gets a placeholder class bonus of **−40**, so she keeps the old, lower “must be fit” pool:

| | Human (race +0) | Elf (race +10) |
|---|---|---|
| Veil Sorceress | **60** | **70** |
| Mage (no class bonus) | 100 | 110 |
| Knight (existing +8) | 108 | — |

The obsolete `base_stats.max_stamina: 55` on the Veil Sorceress file was removed so the formula is the only source. Sample characters such as Isolde still have their own written `max_stamina` until they are rebuilt.

Every spell still costs stamina up front, from the same pool as sword fighting. A basic swing is about 4–8 stamina. Light spells are 8–12, standard 12–18, heavy 20–30, greater 35–45 (existing ability costs, not retuned here).

## Corruption (decision 6)

Every cast adds a **small guaranteed** amount. There is no random “maybe +1” tick any more.

| Band | Gain | Examples |
|---|---|---|
| Light | +2 | Fate Whisper, Fade Step |
| Standard | +5 | Blood Lash, Shadow Bind, Veil Fog, Whisper of Fear, Veil Echo, Shroud Slip |
| Heavy | +8 | Decay Touch, Soul Leech, Blood Pact, Veil Lash, Rift Thread, Sacrificial Pact |
| Greater | +15 | Shroud’s Embrace, Rift Tear, Echo of Eve |
| Capstone | +30 | Veil Apotheosis (once per campaign; left high on purpose) |

A failed or miscast spell still pays the base amount plus **+2**. Casting several times in the same fight adds a small snowball: **+1 per earlier spell**, or **+2** per earlier spell once Corruption is already 75+. Cap is **100** (Hollowed). A Willpower check may still try to halve one gain per long rest (existing Veil Sorceress rule, not newly wired). Purge methods are unchanged (Breath ritual −10 at a price; saint relic −25). Marks still follow the peak, not the purged value.

Sources unified: `rules/magic_rules.json`, `rules/spells.json`, `rules/abilities_magic.json`, `rules/classes/veil_sorceress.json`, `scripts/magic_costs.py`, `scripts/magic_system.py`, `scripts/magic_engine_stub.py`, `scripts/sorcery_ext.py`.

Fate Whisper and Veil Echo were wrongly tagged as a Breath power source; they are Prophetic Veil spells and are tagged Veil now. Active Breath spells are forbidden (`rules/core_rules.txt`). The old male “Divine Verdict” fallback was removed from `scripts/magic_system.py`.

## Blood vessels (decisions 4 and 5)

New rules in `rules/blood_vessels.json`, logic in `scripts/blood_vessels.py`. A day tick on a bound caster is applied from `scripts/time_loop.py`.

| Rule | Placeholder value |
|---|---|
| Maximum vessels | 3 |
| Daily hidden Corruption per bound vessel (even if she casts nothing) | +2 each (3 vessels = +6/day) |
| Binding ritual | 20 stamina, 8 of her own HP |
| Corruption to bind, willing | +8 |
| Corruption to bind, unwilling | +15, and an opposed Willpower roll (d100 + Willpower; ties go to the defender) |
| Range to pay from a vessel | 30 metres / same scene |
| If the vessel dies | bond snaps, she loses 10 stamina and gains +5 Corruption |
| Cannot bind | herself, a dead person, someone already bound, or a fourth vessel |

She still pays her own stamina (and her own corruption from the spell). Only the *blood / HP* cost of a Bloodweaver spell can be taken from a vessel in range. If the vessel is out of reach, dead, or missing, she pays the blood herself. A vessel who is drained to 0 dies and snaps the bond.

Bonds are a Python list on the character (`blood_vessels`). They must not be added to the Foundry actor model or to packed class items.

## What was left alone

- No nosebleed or HP cost on ordinary (non-blood) spells.
- No new “years of life” cost, and no change to Sacrificial Pact’s slower ageing.
- No new beauty / glamour rules for hiding age.
- Overdraw (HP spent on spells that already cost HP) is unchanged.
- Bleeding, zones, and stamina rest/collapse rules are unchanged.

## Related

Elemental backlash, Frost and Fire schools, sigils and ritual debt are in [MAGIC_BACKLASH.md](MAGIC_BACKLASH.md).
