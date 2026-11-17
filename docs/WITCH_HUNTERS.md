# The Mercy of Ash (witch hunters)

Data: `rules/witch_hunters.json`. Code: `scripts/witch_hunters.py`. Tests: `tests/test_witch_hunters.py`. Lore: `lore/orders/mercy_of_ash.json`. All numbers are placeholders.

Witch hunters are **The Mercy of Ash**, an independent Church order under a **Witchfinder General**. They have their own courts for Veil crimes, their own prisons and bounty chests. They are rivals of the Holy Judges (who handle heresy, knights and nobles), not an arm of that tribunal, and they are not under kings. They specialise in Veil sorceresses. Court sorceresses and tolerated mages are politically off-limits unless someone pays the price.

They are ordinary trained men. They use **no magic** and **no Witch-Sight**. They spot signs by mundane means: Inspect, pricking, salt, cold water or heat, a stripping exam, scene evidence (frost or scorch), behaviour, and informants. A magic-using female witch hunter may come later as a special NPC only.

Hidden values (Suspicion, Protection, Political Cost, Church favour, Zeal, Greed, writs, sentences) live only in the Python backend. They are never stored on a Foundry actor.

## Ranks

Authority is what lets a hunter act against a protected woman (see Protection). Informers and Trackers have Authority 0.

| Rank | Authority | Inspect | Interrogate | Notes |
|---|---|---|---|---|
| Informer | 0 | 30 | 25 | Street ears, not sworn. |
| Tracker | 0 | 40 | 30 | Follows spoor and rumours. |
| Sworn Hunter | 1 | 50 | 45 | May hunt in the order's name. |
| Hunt-Sergeant | 1 | 55 | 55 | Leads a party. |
| Witchfinder-Captain | 2 | 60 | 65 | Regional command. |
| Witchfinder General | 3 | 70 | 70 | Answers to no Judge and no king. |

Other skill values (awareness, tracking, intimidation, Lore: Witchcraft, letters of law, leadership) are in the rules file.

## GM toolkit

Thresholds and sentences are **prompts and menus**, not automatic outcomes. The GM chooses.

### Suspicion (0–100, per region)

It rises and falls with named events (`apply_event`). Fleeing helps: a new region starts at 0, or at 10 if she already has a bounty (Suspicion 60+) somewhere else.

| Event | Change |
|---|---|
| Open magic witnessed | +25 |
| Reliable informant | +10 |
| Rumour | +5 |
| Scene evidence (frost, scorch, ritual remains) | +10 |
| Sigil III seen | +15 |
| Branded sigil seen | +25 |
| Odd behaviour | +5 |
| Failed Interrogate | +15 |
| Fled a summons or hunt | +20 |
| Refused or failed an exam | +20 |
| Failed / reported bribe | +15 |
| Framing another woman | −25 |
| Clean exam | −10 |
| Won Interrogate (defender) | −5 |
| Accepted bribe | −15 |
| Quiet month in the region | −5 |

Thresholds (GM prompts only):

- **20 Watched:** an informer tails her and prices rise.
- **40 Questioned:** she is summoned and her lodgings searched. A hunter may Interrogate her.
- **60 Hunted:** a bounty is posted and a hunting party is sent.
- **80 Taken:** an arrest attempt and a full exam are in play. Any sentence is chosen from the menu.

### Protection (0–3) vs Authority (1–3)

- 0 nobody
- 1 a guild, merchant house or abbot
- 2 a lord or city council
- 3 a king or prince (court sorceress)

Hunters can act freely only when their Authority is at least her Protection.

### Political Cost

Acting against a protected woman without enough Authority costs **−10 Church favour per Protection level**, makes the patron an enemy, and may end in scapegoating if Church favour falls to 20 or below. A king's **Sealed Writ** waives the Church-favour hit for that act; the patron may still become an enemy if the king was not the patron. Church favour is hidden, 0–100, and starts at 50.

### Writs

- **Church Writ:** ordinary license to investigate and arrest Veil crimes. It does not override Protection.
- **Sealed Writ:** a king hires the order as legal assassins against a named target. They may act; Church-favour cost is waived.
- **Tolerance Tithe:** a neutral city takes **20–50%** of her income and caps that region's Suspicion at **39**. If the tithe goes unpaid (grace: 30 days), Suspicion jumps to **60**. `day_tick` counts unpaid days.

### Zeal and Greed (0–100, per hunter NPC)

- **Corrupt** at Greed ≥ 60.
- **Fanatic** at Zeal ≥ 80 (never takes a bribe; reporting the offer raises Suspicion by 15).

Bribe formula (placeholder): accept if `(Greed + min(40, offer_gold // 5)) >= Zeal`. A corrupt hunter treats Zeal as 20 lower for this check. A refused bribe from a non-corrupt hunter is reported and also raises Suspicion by 15.

### Sentence menu

The GM picks one. `default_lean` only suggests (a sealed writ or a fanatic with proof leans execution; a fanatic without proof leans torture; a corrupt hunter leans fine or ransom; weak evidence leans confinement; a well-protected woman leans service).

- Fine or ransom (placeholder: 50 × (Protection + 1))
- Forced service (30 days)
- Confinement, branding, or mutilation (tongue or hands may be taken to end casting)
- Torture for information: **1d10 HP** and **+5 Stress**, and **Willpower −10** for the session
- Sale (galleys or a noble house; she leaves play pending the GM)
- Execution by ordinary means after the sentence — **not** an instant-kill power

## Detection (Inspect)

The hunter rolls Inspect + d100 + modifier; 100 or more succeeds. Concealment and composure are opposed by Willpower or Deceive; a tie goes to the defender.

- Corruption 10 or 25: hunters cannot detect it.
- Corruption 50: found only by a stripping exam.
- Corruption 75: Inspect +0; −20 if concealed with gloves, collar or paint, which fails on close contact.
- Corruption 90: automatic.
- Sigil I: −30 at a glance; automatic on stripping or pricking.
- Sigil II: −15; automatic on stripping.
- Sigil III: +0, or −20 if concealed.
- Branded: automatic, and Lore: Witchcraft names her school.

Pricking, cold-water and heat tests can look damning on an innocent woman. They never prove magic; a suggestive result is a GM prompt. Salt may sting or fizz on Veil-touched flesh (it is already a Veil bane in the lore), and that is still not proof on its own.

## Holy Judge (vocation, not a class)

Holy Judge stays a vocation inside the Crusader Knight order. The class file is the vocation's rules, not a new starting class.

**Discern Sin** is now **Interrogate**: Perception + Willpower + d100 vs the higher of Willpower or Deceive + d100. No stamina or piety cost. It reads guilt, not magic, and cannot prove a woman is a sorceress without physical evidence. Divine Clarity still gives +10 against lies. Optional flavour: if Breath has already triggered randomly near a possessed person or demon, the Judge may sense the thing inside them — that stays passive.

**Final Verdict** is legal authority to pass a sentence and have it carried out by ordinary means. It is not an instant-kill power. A just verdict still needs a legal finding (evidence, confession, or a completed exam), not a magical reading of sin. The bonded-blade lawfulness rule in `scripts/order_paths.py` is unchanged (a Judge who personally kills with the wrong blade still risks a Virtue event).

## Breath (passive, random, limited targets)

Breath answers only a Crusader or Judge who has kept his purity, and only against **corrupted beasts, demons, ghosts, spirits, and possessed humans**. It never answers against ordinary sinners or an un-possessed sorceress.

The **Judgment** passive no longer lists a "confirmed major sinner" as a valid target. The same list is used in `witch_hunters.breath_may_trigger` / `judgment_may_trigger`.

**Purge Verdict / `breath_purge`:** the function was already passive (no stamina, fires only on `trigger="just_verdict"`). It now also requires the condemned target to be a valid Breath target, so sentencing an ordinary sinner or an un-possessed sorceress does not clear Veil effects from allies. The stale note in `docs/CLASSES_HOLY_JUDGE_OGRE_RAVAGER.md` that called it an active 10-stamina power is corrected.

## Conflicts flagged, not changed here

These already live on `main` and sit outside this order's toolkit:

- **`witch_sight`** in `rules/creation/advantages.json` is still a female-only caster advantage ("sense corruption bands"). It is not a hunter tool and male hunters must not take it.
- Holy Judge still has a class file and is packed for Foundry, marked `vocation_of: Crusader_Knight`. It stays selectable. This PR does not hide it from the classes pack.

## Church rites (Crusader Knight / Cleric vocation)

Cleansing Ritual, Church Blessing (formerly Breath Blessing) and the Rite of Purgation (`Purge_Corruption`) are now **mundane church rites**. They use no Breath, cost no stamina or piety, and have no holy-damage or Veilspawn-damage effects. Each has a time, materials and a `lore_theology` skill roll (placeholder DCs). They can ease felt taint, bless companions against Fear, or cleanse a room or corpse; they cannot lower hidden Corruption or replace a Breath-answered exorcism of a possessed human.
