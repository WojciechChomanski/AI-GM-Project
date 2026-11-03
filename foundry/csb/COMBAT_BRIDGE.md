# Combat bridge: Foundry → combat engine

The Breath Attack macro sends one swing to `POST /combat/attack` on the FastAPI app in `scripts/combat_engine.py`, running on the GM's own machine. The engine resolves guard, maneuver, zone, damage type, armour piercing and wear. The macro then writes the result back to the sheets and hands the damage to Apply Damage.

## 1. Run the bridge (GM machine)

```
pip install -r requirements-bridge.txt
python scripts/combat_engine.py        # listens on 127.0.0.1:8000
```

Optional settings go in `.env`, which is git-ignored:

| Variable | Default | Meaning |
|---|---|---|
| `API_USERNAME` / `API_PASSWORD` | `admin` / `secret` | HTTP Basic login. **Change these.** |
| `BREATH_HOST` | `127.0.0.1` | Keep it local unless players' browsers must reach it. |
| `BREATH_PORT` | `8000` | Port. |
| `BREATH_CORS_ORIGINS` | localhost and 127.0.0.1 on ports 30000 and 3000 | Comma-separated Foundry origins allowed to call the bridge. |

Check that it is running: `curl http://127.0.0.1:8000/api/healthz`.

The fetch comes from the **browser of the user who runs the macro**. Run it as the GM on the machine that hosts the bridge. If you host remotely (Forge or a VPS), put the bridge behind HTTPS and add that origin to `BREATH_CORS_ORIGINS`. An HTTPS Foundry page cannot call a plain-http bridge.

## 2. Foundry setup (CSB 6.0.2)

1. Import `breath-templates.json`. It provides:
   - the actor template "Breath Character (Combat v1)"
   - the item templates Breath Weapon and Breath Armor
2. Switch actors to the Combat v1 template.
3. Create weapon and armour items from `weapons_items.json` and `armor_items.json`.
4. Create two Script macros, with the names exactly as shown:
   - **Breath Attack**: paste `macros/breath-attack.macro.js`. If you changed the login or port, edit the `BREATH_BRIDGE` constant at the top.
   - **Apply Damage**: paste `macros/apply-damage.macro.js`.
5. To use it, select the attacker's token, target the defender, and run Breath Attack. Then pick:
   - the guard
   - the situation
   - the maneuver (best, none, or a named one)
   - the target zone, or a normal hit
   - the damage type
   - the trick option

The weapon used is the one in `weapon_in_hand`, or else the first Weapon item. When `grip` is two_hands and the weapon has a two-hand set, the dialog offers the two-hand guards. For the longsword, that is the 10 greatsword guards.

## 3. What is stored where

The engine is stateless. Everything it needs comes from the sheet, and these fields are written back to the attacker:

- `current_guard`, `previous_guard`
- `fight_state_json`, which holds per-fight trick use, binds and similar state
- `conditions_json`
- `stamina`
- `disarmed`

The defender's conditions and disarmed state are also written back. A GM-whispered chat card summarises the swing:

- attack vs defence
- the maneuver
- damage through armour
- armour wear
- stamina spent

On a hit, Apply Damage opens prefilled with armour marked as already applied, then handles zones and bleeding.

Clear `fight_state_json` (set it to `{}`) at the end of a fight.

## 4. Known gaps

- **Armour wear is not stored.** The engine reports `armor_wear`, but the sheet has no per-armour durability field, so wear is only shown in chat. Track it on the armour item by hand for now.
- **Role-hiding is cosmetic.** CSB role 4 hides Faith, Virtue, Piety, Holy Fury and Corruption on the sheet, but the data is still in the actor, and the macro sends it from the client. Players with Observer permission and the dev console can read it.
- **Normal hits sum all armour layers.** A hit with no zone uses every worn layer.
- **Loose_\* armour pieces** exist only on the open PR 3.
- **Tests:**
  - `pytest tests/test_foundry_csb.py` covers the build, roles and payload.
  - `node foundry/csb/test/attack_e2e.cjs` runs the macro against a live bridge with Foundry mocked. Set `BREATH_PORT=8765` for it, or pass the URL.
