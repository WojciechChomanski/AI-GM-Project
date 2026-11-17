# Crusader Knight: Rule of Life

Hidden spiritual rule for the Crusader Knight (and the Holy Judge vocation, Paladin honour, and Penitent Brother fallback). Numbers live only in the Python backend (`rules/rule_of_life.json`, `scripts/rule_of_life.py`). Nothing is stored or shown on a Foundry actor. The player sees a single felt line.

Several figures are marked PLACEHOLDER: the Breath Keeper draft was truncated in the middle, so weights and timings were reconstructed from the user's summary, the six final decisions, and the Brother Aimery worked example.

## Historical rule

Drawn from the Templar Primitive Rule (Latin Rule of 1129, [Fordham](https://sourcebooks.fordham.edu/source/templar-rle.asp)), the Templar Retrais, and the Hospitaller rule of Raymond du Puy.

- **Hours.** The seven canonical Hours with the chaplain. Silence after Compline. In the field, or when he cannot read, Paternosters in their place: 13 for Matins, 9 for Vespers, 7 for each other Hour (Primitive Rule §10).
- **Table.** Meals in silence with a reading. Meat at most three times a week. Lenten fare on Fridays. Fast from All Saints to Easter.
- **Vows.** Poverty, chastity and obedience. No lockable purse. He owns only arms, armour, horse and habit.
- **Sleep.** A lamp is left lit at night.
- **Campaign.** Fleeing the banner is loss of the house: expulsion, or becoming a Penitent Brother.
- **Murder of a Christian.** The same loss of the house (decision 5).

## Hidden mechanics

### Daily Rule Kept check

Each day, the knight either kept the Rule or broke it.

- Kept: Piety **+2**. Broken: Piety **−4**.
- The Rule alone caps Piety at **80**. This check *replaces* the generic engine decay of −4 a day for anyone under the Rule (C6).
- Piety has a gain table in `rules/rule_of_life.json`. The default start is **50** (`ai_gm_engine`). `scripts/character.py` still initialises piety at 0 until a value is loaded; a trained brother is usually in the 50–70 band. Aimery starts at 72 as an established knight.

### Stain ledger

Every sin is written in a hidden ledger and mapped to one of the seven deadly sins.

- **Venial:** weight 5 or less. **Grave:** weight 6 or more.
- Grave sins also add hidden Corruption: **+2** or **+5** when incurred, then **+1 per open unconfessed grave stain every 7 days** (decision 1). The weekly rot is PLACEHOLDER, inferred from Aimery (Corruption 17 → 20 after a week with three open graves).
- Prayer, Hours and Paternosters never lift a grave stain.

**PLACEHOLDER stain weights.** Existing Virtue losses were kept where they already existed (drunkenness 4, brothel 6, and so on). Two Aimery weights had to be set so the worked example lands on Virtue 44:

- `theft` (greed) weight **7**, Corruption +2, breaks poverty.
- `murder_christian` (wrath) weight **18** (needless killing 8 + cruelty 10, applied once), Corruption +5, loss of the house.

### Virtue ceiling

Virtue ceiling = **75 minus the weight of every open grave stain**. Repeat Virtue gains from the same event halve. Daily, if the Rule was kept, Virtue recovers **+2** toward the current ceiling (PLACEHOLDER, chosen so an honest drunk at 71 is back at 75 in two days).

### Rule Ward

Rule Ward is a hidden 0–5 buffer. It rises by 1 for each day the Rule is kept, and drops to 0 on a broken day. Incoming Veil corruption is reduced by 1 per Ward point (PLACEHOLDER). It never appears in Foundry.

### Daily cleansing (decision 3)

Venial stains only, and only on a day the Rule is kept:

- **2** points a day for the first **3** cleansing days of the week, then **1** a day, at most **8** points a week (2+2+2+1+1).
- Prayer never lifts a grave stain.

### Penance (the only way to lift a grave stain)

1. Confession to a priest (not “to God” alone).
2. Restitution.
3. Penance lasting **weight** days (PLACEHOLDER).
4. If the sin is murder of a Christian or fleeing the banner, he must also accept **loss of the house**: expulsion, or the Penitent Brother path.

Until that is done, the stain stays open, the Virtue ceiling stays lowered, and Breath stays capped (see below).

### Breath (decisions 2 and 6)

Breath stays **passive only**.

- A broken vow, or any open grave stain, **caps Breath at dim**. It does not block Breath entirely.
- Valid targets match the witch-hunter list: veilspawn, abomination, corrupted beasts, demons, ghosts, spirits, and possessed humans. Never ordinary sinners, witches, or an un-possessed sorceress. The combat engine's old `corrupted` tag is kept as an alias for `corrupted_beast`.

### Anti-abuse (C5)

Confession (+8 Virtue) and a fasting day (+5) cannot be stacked to pray a murder away.

- Each may be used at most once per 7 days (PLACEHOLDER cooldown).
- Combined weekly devotion cap of **8** (PLACEHOLDER).
- No gain may push Virtue above the current ceiling, so an open grave stain of weight 31 holds Aimery at 44 no matter how hard he prays.

## Felt lines (the player sees only these)

- Ward up: “The lamp burns steady; the dark keeps its distance.”
- Venial stain: “The Paternosters snag on your tongue.”
- Grave stain: “You say the words. Nothing answers.”
- Vow broken: “Something that stood at your back has stepped away.”
- Confessed, penance not done: “The weight has a name now. It is not gone.”
- Stain lifted: “You sleep without dreams for the first time in weeks.”
- House lost (when that is the thing still hanging over him): “The house is closed to you.”

The GM sees the ledger, the streak, the Ward, the ceiling and the cooldowns.

## Worked examples

**Brother Aimery.** Start: Virtue 75, Piety 72, Corruption 8, Breath full. Day 1: he robs a merchant, murders him and visits a brothel, then prays every Paternoster that night. Virtue 44, Corruption 17, Ward 0, Breath dim. Days 2–8: a perfect Rule, but he confesses only “to God”. Piety climbs to 80, Virtue stays at 44 (the ceiling), Corruption rises to 20, Breath is still dim (the draft said “none”; decision 2 caps it at dim instead). He ends worse on Virtue, Corruption and Breath. To recover he needs a priest, restitution, penance, and loss of the house.

**An honest drunk.** Virtue drops 75 → 71 (venial, weight 4) and is back at 75 in two kept days, once daily cleansing has washed the stain.

## Conflicts closed against `main`

- **C1.** `magic_rules.json` `purge_methods.breath_ritual` is removed. `saint_relic` is kept as the rare cure (decision 4).
- **C2.** The purity vow no longer promises that corruption is “purged at once”. It now requires confession, restitution and penance, with a saint's relic as a rare corruption cure.
- **C3 / decision 6.** `crusader_vows.json` Breath targets match `scripts/witch_hunters.py` `VALID_BREATH_KINDS`.
- **C4.** The stale Discern Sin reference under Breath “none” is gone (Interrogate is the mundane skill).
- **C5.** Confession and fasting are on a cooldown and a weekly devotion cap, and cannot beat the Virtue ceiling.
- **C6.** Piety has a gain table (Rule kept +2, broken −4, Rule cap 80, default start 50).
- **C7.** Smite remnants (`smite_base` and the three scale keys) are removed from `rules/breath_config.json`.
- **C8.** `miracle_breath_burst` is removed from the Templar Ascendant vow rewards. Breath is not an activated burst.
- **C9.** `magic_rules.json` now has a corruption stage at **90** (`speaking_veil`), in line with `rules/corruption_marks.json`.
- **C10.** Every new hidden key (`rule_ward`, `stain_ledger`, `virtue_ceiling`, `venial_stain*`, `grave_stain*`, `rule_kept*`, `stain_weight`, `open_grave*`, `rule_of_life`) is in `HIDDEN_KEY` in `scripts/build_foundry_packs.py`, and in the Foundry hidden-stat tests. The hunter-toolkit keys that were already tested are now stripped by the pack builder as well.

## Open questions

- Fleeing the banner is treated like murder of a Christian (loss of the house). If that should be a lesser discipline step, say so.
- Holy Judge, Paladin and Penitent Brother keep the same Rule. If a Judge or a Penitent should follow a shorter office, that is not yet split out.
- Penance length equals stain weight in days, Ward reduction is 1:1, and the weekly unconfessed rot is +1 per open grave stain. All three are PLACEHOLDER and can be retuned without changing the shape of the rule.
