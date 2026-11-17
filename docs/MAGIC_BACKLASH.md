# Elemental backlash (Frost, Fire, Grave-Chill, sigils)

Placeholder rules, implemented after the costly-magic work in PR 31. All **numbers are PLACEHOLDER** and should be tuned after play. Tracks, sigil points, ritual debt and Corruption live only in the Python backend (`scripts/magic_backlash.py`, `rules/magic_backlash.json`). Foundry may show **symptom text** from `symptoms()`, never the numbers themselves.

This does **not** add a flat health cost to ordinary spells. Health is lost only when a backlash track has already crossed a threshold (or from existing Bloodweaver HP costs, stigmata, and deliberate counters).

## Thermal track (−10 to +10)

Frost spells push the track **down**. Fire spells push it **up**. They share one track.

| Band | Track gain |
|---|---|
| Light | 1 |
| Standard | 2 |
| Heavy | 3 (Sigil II of that school: 2) |
| Greater | 5 |

| Threshold | What happens |
|---|---|
| ±3 | −5 to fine work and Spellcraft |
| ±5 | −10 to everything, stamina recovery halved, **1 HP per round**, and visible evidence within 3 metres (frost rime, or a scorching heat) |
| ±7 | no stamina recovery, **3 HP per round**, Toughness test (d100 + Toughness against DC 50, placeholder) or collapse |
| ±10 | **death in one round** unless a counter lands first |

Recovery while resting is **1 step toward 0 per 10 minutes**. That is far too slow to survive ±10 in a single 6-second combat round. The grace is one round to use a counter.

Counters:

- **Hot iron** — 3 steps toward 0, costs 4 HP, leaves +1 Fire sigil scar.
- **Ice bath** — 3 steps toward 0, costs 10 stamina, takes 1 round.
- **Brazier or snow** — 1 step toward 0 each round while you stay in it. This can also save someone in the death window if it gets them off ±10 in that same round.

## Opposite-element cancelling (provisional default: banned)

You cannot cool a Fire debt by casting Frost, or warm a Frost debt by casting Fire. While the track is below 0, Fire spells are refused; while it is above 0, Frost spells are refused. Rest and counters are the only way back toward 0. This is a **provisional default** because the shared track would otherwise invite alternating schools as a trick. Flagged in the rules file so it can be revisited.

## Grave-Chill (necromancy, 0 to 10)

Same band gains as Thermal (+1 / +2 / +3 / +5). Recovery is **1 step per hour**.

| Threshold | What happens |
|---|---|
| 4 | −10 Agility, a numb hand |
| 7 | max HP −10% until a real long rest |
| 10 | lose a finger or an ear, permanent −5 (once) |

Counters: **warm blood** (−3, +2 hidden Corruption) or **salt-and-ash** (−2, 3 HP).

## Blood stigmata

If a caster pays more than 15 HP of **her own** blood in one scene (16 or more), stigmata open: Bleeding 1 for 3 rounds. Paying from a blood vessel does not open her palms. Counters: **cautery** (3 HP, +1 Fire scar) or a **tourniquet** and 1 round of rest.

## Ritual debt

A ritual has **no track cost while it is being cast**. At the **next dawn** the band is paid as a Thermal or Grave-Chill hit, and the casters take a **fever night** (a long rest that night gives no benefit; the fever then breaks). If several casters work in a circle, the delayed debt is **split evenly**. Any remainder goes to the lead caster (placeholder).

## Sigils (per school: Frost, Fire, Necromancy)

+1 point for each heavy or greater cast of that school, and +1 when a relevant track crosses 5 or 7.

| Points | Name | Effect |
|---|---|---|
| 3 | Sigil I | Hidden |
| 8 | Sigil II | Hidden; **−1 track gain on heavy casts** of that school (not greater) |
| 15 | Sigil III | Visible, like Corruption 75; a glove or collar can hide it |
| 25 | Branded | Visible, not hidden by a glove or collar |

**Glamour** can hide visible sigils for **one scene** at **+5 Corruption**. It never fools **Witch-Sight**.

TODO: hunter Witch-Sight rules (how a hunter spots or contests a sigil) are **not** implemented in this PR. The glamour flag simply does not apply when `witch_sight=True`.

## Frost and Fire starter spells

Two new schools, each with five quiet spells that fit a hidden world. No fireballs, no blizzards, no greater-band nukes in the starter list. Costs use the existing stamina and corruption bands, plus Thermal strain as above. Listed in `rules/spells_frost_fire.json`.

Frost: Rime Latch, Still Breath, Numb the Limb, White Trail, Hoarfrost Veil.

Fire: Wick’s Friend, Banked Stone, Fever Touch, Soot Screen, Cinder Mark.

Existing necromancy spells Decay Touch and Soul Leech gain Grave-Chill (heavy). Blood Lash still spends its existing health cost and now counts toward stigmata.

## Foundry

Do not store Thermal, Grave-Chill, sigil points, ritual debt or Corruption on a Foundry actor. If the backend later writes `felt` entries, use `symptoms()` so the player sees only prose.
