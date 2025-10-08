# Act I — The Cut (v0.6e)

**Play time:** 60–90 minutes  
**Party:** Stonewarden + 1–2 companions  
**Theme:** Hold the line, make the breach, earn trust of Ansel the Platewright.

## Files used
- `rules/events/approach_the_cut_v0_6e.json` (setup/transition)
- `rules/events/hold_the_cut_v0_6b.json` (trial 1 — lane defense)
- `rules/events/door_to_breach_v0_6b.json` (trial 2 — over-prime tension)
- `rules/kits/stonewarden_quickstart_party_v0_6e.json` (starting party)
- Ansel pricing (optional): `rules/vendors/ansel_base_prices_v0_6d.json` + preview ask prices

## Flow at a glance
1. **Approach the Cut** → scouting, quick gear check.  
   - Success ⇒ minor edge in Trial 1 (e.g., pre-laid mesh, better position).  
   - Fail    ⇒ start “winded” or with a TN penalty for the first 2 rounds.
2. **Trial 1: Hold the Cut** (mesh + Anvil stance focus).  
   - **Pass:** morale holds, proceed to Trial 2 with +1 buffer or reroll token.  
   - **Fail:** take fatigue / light injury tag; Trial 2 starts “noisy & rushed”.
3. **Trial 2: Door-to-Breach** (over-prime vs. misfire).  
   - **Pass clean:** set **session flag** `trial_passed_clean` and audience with Ansel.  
   - **Pass messy:** set `trial_passed`; risk tags linger.  
   - **Fail (abort/extract):** set `trial_failed`; fallback intro to Ansel still possible but without perk.
4. **Aftermath:** Ansel appears; if `trial_passed` ⇒ **session perk** (Ansel: −5% ask price this session, stacks with Stonewarden affinity, GM-capped). Small material reward or comped reseat/repair.

> **Tone:** grounded, industrial-grim; tactics over heroics. Progress, not perfection.

## Stakes & outcomes
- **Strong pass:** trust earned; better prices (session), faster repairs, rumor hook unlocked.  
- **Mixed:** no perk; you can still buy/repair at Ansel’s standard terms.  
- **Fail:** scars and debt; Ansel remains skeptical (no perk; may charge rush fees).

## Table tips
- Keep **round clocks** visible (3–5 rounds per scene).  
- Say **what failure looks like** before rolls (smoke, slipping powder, jam risk).  
- Use **one reroll token** per party granted by great positioning or clean execution.

## Rewards (suggested)
- **Session perk flag:** `ansel_discount_session = -5` (percent).  
- **Material:** 1× `coil_wire_bundle_std` **or** 1× `repeater_mag_std_10`.  
- **Service:** one **reseat** comped (labor only) or 2 dents cleared.

