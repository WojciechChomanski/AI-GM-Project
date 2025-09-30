# THE BREATH & THE VEIL — LORE MASTERFILE
*Canonical World Bible (Single File Edition)*  
*Build: 2025-09-12*

---

## Executive Summary
A biblical-grimdark world where **The Breath** (divine Word/Light) contends with **The Veil** (primordial un-creation). Eden was a continent-realm bridging Heaven and Earth. Eve, tempted by whispers from the Veil, moved the Eldran (the ancient people) to raise the **Tower of Va**, a spire rooted in the Veil and crowned toward Heaven. Angels shattered it. **Eden was sealed**. The world fractured (the **Sundering**). Eldran split into **Elves** (Mystics) and **Dwarves** (Artificers). **Humans** were left as mortal heirs of the Breath. **Ogres**—pre-Sundering vat-made titans—remained as tragic engines of war.

**Design pillars:** costly power, moral consequence, asymmetry of races, demons as campaign events (not trash mobs), scripture as actionable gameplay.

---

## Table of Contents
1. [Cosmology](#cosmology)  
2. [Eden & The Tower of Va](#eden--the-tower-of-va)  
3. [The Sundering & Aftermath](#the-sundering--aftermath)  
4. [Power Systems](#power-systems)  
5. [Corruption Model](#corruption-model)  
6. [Races](#races)  
7. [Factions](#factions)  
8. [Worldframe, Tech & War](#worldframe-tech--war)  
9. [Key Locales](#key-locales)  
10. [Scripture: *Scroll of Light and Fall*](#scripture-scroll-of-light-and-fall)  
11. [Classes (Lore Shape)](#classes-lore-shape)  
12. [Professions (Lore Add-Ons)](#professions-lore-add-ons)  
13. [Hooks & Present Tensions](#hooks--present-tensions)  
14. [Canonical Terms & Glossary](#canonical-terms--glossary)  
15. [Implementation Notes (for Devs)](#implementation-notes-for-devs)  
16. [Changelog](#changelog)

---

## Cosmology
- **The Veil** — Genesis 1:2 darkness: *“upon the face of the deep.”* Not a person; it is un-creation, the pull back to formlessness. It tempts by promising knowledge/power beyond order. The Serpent/Satan is a whisperer toward the Veil, not the Veil itself.
- **The Breath** — Genesis 1:3: *“Let there be light.”* The divine Word/Light; ordering power that heals and remembers. In this world, the Breath uniquely echoes in humankind.
- **Moral Field** — Creation sits between Breath (order/mercy) and Veil (un-making/seduction). All power has a price.

---

## Eden & The Tower of Va
- **Eden**: a continent-realm between Heaven and Earth. No hunger, age, or disease. Humans and **Eldran** walked with angels.  
- **The Tower of Va**: raised by Eve (tempted by Veil whispers), abetted by Eldran craft, with Adam’s culpable inaction. Its roots sank into the Veil; its crown reached toward Heaven—an unlawful bridge.
- **Angelic Intervention**: Angels descended; the Tower shattered; **Eden sealed**. Holy fragments—relic veins, broken leylines, tower shards—fell across the world.

---

## The Sundering & Aftermath
- **Eldran Split**:
  - **Elves (Mystics)** → forests; immortal, slowly decaying from Veil entanglement; ritual sacrifice to offload corruption.
  - **Dwarves (Artificers)** → under-mountain; bodies hardened under **high gravity**; runic engineering and sealing.
- **Humans**: mortal heirs of the Breath’s echo; fragile yet the only true vessels for holy power.
- **Ogres**: pre-Fall vat-made titans (alchemy + engines + Veil serums) from stolen boys; tragic, child-minds; no females.
- **Demons**: rare and catastrophic—signs of failed seals, mass rites, or moral collapse. Their arrival is a campaign-scale event.

---

## Power Systems
- **Breath** — holy, restorative, oath-bound.  
  **Gameplay:** Human, **male-only**, **class-tagged**, **Virtue-gated**, and **mainly vs. abominations**.
- **Veil** — destructive, seductive, corrupting.  
  **Gameplay:** accessible at a cost; Elves culturally aligned; corruption accrues.
- **Runes** — dwarven passive bindings/engines (no live casting); **female dwarves +10% potency**.

---

## Corruption Model
- **Scale:** 0–150, accelerating with use.
  - **0–30**: whispers, faint rune glow; minor stealth penalty.  
  - **31–60**: tremors, black specks in eyes; −accuracy, +spell damage.  
  - **61–90**: alluring malice; black eyes/teeth; −trust, +spell damage.  
  - **91–120**: horns/scales; +damage; **friendly-fire risk**.  
  - **121–150**: **possession**—becomes a Veil host (monster/NPC control).
- **Purification:** Breath cleanses without corrupting. Elves offload via sacrifice; Dwarves suppress via runes; Ogres have low tolerance & frenzy risks.

---

## Races
### Humans — Heirs of the Breath
- **Lore:** frail, hunted, but uniquely able to echo the Breath. Demons fear them; Elves covet them; Dwarves grind them for soul-metal.  
- **Breath Gate (current rule):** **male**, **breath-bound class tag**, **Virtue ≥ 70**, **effects awaken vs. abominations** (undead, demons, veil-hosts).  
- **Culture:** versatile, early-modern urban/rural mix; Breathbound Orders train Crusaders/Confessors/Judges.

### Elves — Mystics of the Thorn
- **Lore:** immortal yet decaying; ritual sacrifice transfers corruption into human victims (a high-echelon secret).  
- **Arms/Doctrine:** refuse gunpowder; prefer bows/curved blades/knives; ride veiled beasts; beauty as creed; shields rare.  
- **Mechanics:** Veil affinity; higher corruption rate; **Thorn’s Sacrifice** (transfer corruption on kill).

### Dwarves — Sealed Under Stone
- **Lore:** gravity-forged bodies, runic craftsmen. **Soul-Grinders** harvest trace iron/copper “soul-metal” from human bodies for devastating arms & elite ammo.  
- **Arms/Doctrine:** axes/hammers/crossbows/guns; **no swords/bows**; disdain mounts; culture of binding and sealing.  
- **Mechanics:** passive runes (female potency +10%), natural Veil resistance.

### Ogres — Vats’ Children
- **Origin:** stolen boys converted in Eldran vats (alchemy + machines + Veil). No females; minds ≈ **6–8 years** old.  
- **Body:** **strongman/bear-like** mass (~600 kg), asymmetries/disfigurements (fused fingers, bone ridges, offset jaw/teeth).  
- **Gear:** **improvised**—patchwork leather, chains, broken shields, straps.  
- **Mechanics:** 3× carry; high caloric needs; **claustrophobia**; stress-immune “childlike mind”; devour-to-heal (corruption risk); berserk at low HP.

---

## Factions
- **Breathbound Orders** (human sacred orders) — relics, confession, knightly formation; pursue **Abel’s Echo**.  
- **Iron Wards** (dwarven sealers) — rune pylons, soul-forges; aim to **bind the Veil forever** (moral costs).  
- **Echelon of Thorns** (elven regime) — ritual sacrifice doctrine; guard Veil rifts; hunt human conduits.  
- **Daughters of the Drowned Moon** (water witches) — brine rites, drownings; thin boundaries at river mouths; **salt** as bane.  
- **Reclaimers of Va** (cult of the Tower) — rebuild Va with leyline **Va-Pylons** and **living Breath counterweights**.

---

## Worldframe, Tech & War
- **Era Aesthetic:** **Hybrid-Earth 1580–1650** (pike & shot; matchlocks/flintlocks; plate-and-mail still relevant).  
- **Asymmetry:**  
  - **Dwarves** — most advanced gunpowder (grim, primitive “frontier” feel), crossbows, cannons.  
  - **Humans** — mixed melee + rare firearms.  
  - **Elves** — **no gunpowder**, ritual gear, organic armors, veiled mounts.  
  - **Ogres** — improvised siege implements, brute force.  
- **Doctrine of Spite:** Dwarves refuse swords/bows because Elves use them; Elves refuse guns/shields because Dwarves use them. Humans use what works.

---

## Key Locales
- **Cinderhold** (Human port) — soot, relic markets, soot-smeared pulpits; early firearms in back alleys.  
- **Thornskull** (Elf spire-city) — hollowed living tree; **Altar of Rot**; bone-lattice skyways; ritual hunts.  
- **Ironcrag** (Dwarf citadel) — mountain forges, **Soul Crucible**, rune pylons; ash haze and steam-carts.  
- **Gearwomb** (Ogre scrapyard) — buried engines, rumor of a pulsing vat; nomad bands gather for war.

---

## Scripture: *Scroll of Light and Fall*
**Chapter 1: The First Divide**  
**1:1** In the beginning the Breath spoke, and there was Light.  
**1:2** And the Light parted the Darkness, yet did not unmake it.  
**1:3** The Darkness remained behind the firmament, a waiting abyss men call the Veil.  
**1:4** The Breath ordered measure and season; the Veil desired unmaking.  
**1:5** The Breath warmed clay and taught it to sing; the Veil answered with silence.  
**1:6** The Maker saw the Light and named it good, and the Darkness He left unnamed.  
**1:7** From that day, all things would choose: to breathe—or to listen.

**Chapter 2: Eden, the Bridge**  
**2:1** Eden was fashioned between Heaven and Earth, a continent without hunger or age.  
**2:2** There the Firstborn, called Eldran, walked with men and with angels.  
**2:3** Their craft bound stone and star; their wisdom carved laws into living rock.  
**2:4** No death dwelt in Eden, for the Breath watered every heart.  
**2:5** And yet the Veil pressed against the rim of the world like a tide at night.  
**2:6** The Eldran heard a question in the hush: Why should you not?  
**2:7** Thus began the counsel of ruin.

**Chapter 3: The Tower of Va**  
**3:1** Eve turned her gaze into the Deep; Adam stood and did not speak.  
**3:2** The Eldran raised a spire with roots in the Veil and a crown toward Heaven.  
**3:3** They named it Va, a bridge of stone and soul, to drink what was forbidden.  
**3:4** The spire grew like pride, and the world held its breath.  
**3:5** Then the Angels descended, weeping iron and fire.  
**3:6** The Tower broke, and Eden was sealed from the sons of clay.  
**3:7** The shards of paradise rained upon the earth; the Sundering began.

**Chapter 4: After the Sundering**  
**4:1** The Eldran split as rock along a fault: Mystics to the forests, Artificers to the deeps.  
**4:2** The Mystics became Elves—immortal, beautiful, and dying from within.  
**4:3** The Artificers became Dwarves—heavy-boned, sealed and steadfast under weight.  
**4:4** Men were left with tears and the Breath, frail as candles in wind.  
**4:5** Ogres remained—vats’ children, war-made from stolen boys and dark serums.  
**4:6** The Veil crept into beast and man, and the world learned fear.

**Chapter 5: Breath and Choice**  
**5:1** The Breath mends what it names; the Veil unmakes what it touches.  
**5:2** To drink the Breath is to remember; to draw the Veil is to forget.  
**5:3** The path of light wounds pride; the path of shadow flatters hunger.  
**5:4** Abel’s blood cried like a bell in the dusk, and men heard it faintly.  
**5:5** When the Breath returns to many hearts, Eden’s seal shall loosen.  
**5:6** Until that day, choose, and pay the price of your choosing.

---

## Classes (Lore Shape)
- **Human (Breath-bound):** *CrusaderKnight, Confessor, Judge*. Breath perks (Aegis/Sanctified Steel/Smite) only if **male**, **class has tag `breath_bound`**, **Virtue ≥ 70**, and **target is abomination**. Virtue fluctuates with behavior (defend innocent/fasting/confession vs. cruelty/vice/desecration).  
- **Elf:** *Hollow Warden, Arcanite, Sorceress (female-only)* — high power, high corruption; seduction/fear/rituals; at peak corruption becomes a **Veil vessel**.  
- **Dwarf:** *Runebearer, Forge Sentinel, Ash Priest* — sealing, suppression, soul-metal gear; passive rune play.  
- **Ogre:** *Ravager, Siegeborn* — grapples, shock, logistics, frenzy control; cannibal-heal risks.

---

## Professions (Lore Add-Ons)
- **Prophecy Seeker (Human):** relic finding, corruption sense, morale.  
- **Veil Ritualist (Elf/Human Heretic):** boosts Veil potency; sacrifices (moral costs).  
- **Soul-Grinder (Dwarf):** forge durability buffs; Crucible access/logistics.  
- **Awakening Ritualist (Ogre):** vat-quest, unlocks ogre ally or reveals ongoing “births.”

---

## Hooks & Present Tensions
- **Reclaimers’ Three-Pylon Rite** — stop a Va-Pylon triangulation before the aperture opens.  
- **Echelon Mass Sacrifice** — sabotage the **Altar of Rot**; rescue marked conduits.  
- **Iron Wards’ Dilemma** — use the **Soul Crucible** on a captive to complete a seal?  
- **Moon Drowning** — break a tidal rite by consecrated **salt**.  
- **Gearwomb Pulse** — investigate a vat reawakening or a demon forcing “birth” through the machine.

---

## Canonical Terms & Glossary
- **Breath** — divine Word/Light; holy power; human echo.  
- **Veil** — primordial darkness; un-creation; corruptive lure.  
- **Eldran** — ancient people before the split (source of Elves/Dwarves).  
- **Sundering** — the world-fracture after the Tower’s fall and Eden’s sealing.  
- **Va-Pylon** — Reclaimers’ leyline spires used to thin the boundary.  
- **Soul-Metal** — dwarven term for trace iron/copper essence refined from bodies.  
- **Abomination** — undead, demon, veil-host, or warped constructs.  
- **Abel’s Echo** — prophecy that when many hearts truly breathe, Eden’s seal loosens.

---

## Implementation Notes (for Devs)
- **Source of Truth files (already in your project):**  
  - `AI_GM_Project/rules/races.json` — Human Option B gate set.  
  - `AI_GM_Project/rules/class_tags.json` — tag e.g., `"CrusaderKnight": ["breath_bound"]`.  
  - `AI_GM_Project/rules/virtue_rules.json` — thresholds (`full:70`, `dim:40`), gains/losses.  
  - `AI_GM_Project/rules/breath_config.json` — all Breath numbers (Aegis/Sanctified Steel/Smite tuning).  
  - `AI_GM_Project/lore/core/lore_master.json` — compact data mirror of this file.  
  - `AI_GM_Project/lore/factions/factions.json` — five core factions defined.  
  - `AI_GM_Project/lore/scrolls/scroll_of_light_and_fall.json` — verse-numbered scripture.  
  - `AI_GM_Project/bestiary/*.json` — tag enemies with `"abomination"` for Breath triggers.
- **Demons:** treat as event gates (encounter tables should reference missions/seals/rites, not random combat).

---

## Changelog
- **2025-09-12** — Single-file consolidation; added doctrine of spite, clarified demon rarity, locked Human Option B (male/class/virtue/abomination), embedded full scripture, formalized faction aims, summarized city anchors.

---
