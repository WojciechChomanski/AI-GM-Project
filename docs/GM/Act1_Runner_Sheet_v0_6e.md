# GM Runner Sheet — Act I: The Cut (v0.6e)

**Scenes**
1) **Approach the Cut** → scouting + kit check (2 short beats)  
2) **Hold the Cut** → use existing trial file (defense lane)  
3) **Door-to-Breach** → use existing trial file (over-prime tension)  
4) **Aftermath** → Ansel appears; apply perk if earned

---

## Quick TNs & timers
- **Perception (Approach):** TN 12 (mesh lane)  
- **Hold the Cut:** Use the file’s TNs; if `winded_opening`, add +1 TN on the first 2 rounds for movement-heavy actions.  
- **Door-to-Breach:** Use the file’s misfire/over-prime logic; grant **1 reroll token** if the party earned it from Approach.

**Round clocks:**  
- Approach: 1–2 minutes only (no grid).  
- Hold the Cut: 4 rounds.  
- Door-to-Breach: 3 rounds (or until breach triggers / misfire forces fallback).

---

## Flags & perks
Set these **session flags** based on outcomes:

- `trial_passed_clean` (Trial 2 pass without misfire):  
  - **Ansel perk:** `ansel_discount_session = -5` (%).  
  - **Service comp:** 1 reseat (labor only) **or** 2 dents cleared.

- `trial_passed` (messy pass):  
  - **Ansel perk:** `ansel_discount_session = -5` (%).  
  - **No service comp**; can buy normally.

- `trial_failed` (abort/extract):  
  - **No perk**; Ansel still accessible at standard prices.

> **Pricing note:** The session perk stacks with Stonewarden class affinity where applicable. GM may cap total discount.

---

## Rewards (pick 1–2)
- **Materials:** `coil_wire_bundle_std` (x1) **or** `repeater_mag_std_10` (x1).  
- **Cash:** 200–400 cp depending on performance.  
- **Story:** Rumor hook to next act (Ansel mentions an order for Veil-etched rivets gone missing).

---

## Box text seeds
**Approach:** “You crest the shale lip; the Cut yawns ahead—sandbags mended with copper wire, soot like fingerprints.”  
**Hold:** “Mesh hums against your plate as the lane tightens; boots bite; someone screams ‘Brace!’”  
**Breach:** “The fuse hisses like a snake under a door; your thumb rides the safety. How hard do you over-prime?”

---

## Fail-forward guidance
If the party underperforms, narrate harsher consequences (fatigue, chipped plate), but **do not block** Act I completion. Carry scars into prices and repair time with Ansel.
