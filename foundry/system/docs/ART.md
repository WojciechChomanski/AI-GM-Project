# Art assets (Witcher comic style)

All player-facing pictures live under `foundry/system/breath-and-the-veil/assets/`. They follow the approved v5 Witcher 3 Wild Hunt loading-screen look: dark heavy-inked comic panels, painted storybook texture, cinematic lighting, muted earthy colours with one strong colour mood (icy blue, warm brown, or blood red). Midtones stay open and readable — a dark mood is not the same as an underexposed picture. Figures sit in an environment, not on blank parchment. `_fallback.webp` files stay as a last resort. Weapon and armour item icons are a later batch.

| Kind | Path | Notes |
|---|---|---|
| Compendium banners | `assets/banners/<pack>.webp` | 1160×280 (4× Foundry's 290×70 slot). Manifest path is `assets/banners/<pack>.webp`. |
| Portraits | `assets/portraits/<race>-<gender>.webp` | 1024×1024. Playable only: `human-male`, `human-female`, `elf-male`, `elf-female`, `dwarf-male`, `ogre-male`. No female dwarf or female ogre. |
| Class icons | `assets/icons/classes/<id>.webp` | 768×768. `id` is the class key in lower case (`crusader_knight.webp`). Paladin is not a class, so there is no paladin icon. |
| Test map | `assets/maps/test-crossroads.webp` | 4096×4096. See below. |

Item `img` fields in the packs use the Foundry path `systems/breath-and-the-veil/assets/...`. Race items use the male portrait of that race as a stand-in face. Weapons and armour still use Foundry's default SVG icons until the item-icon batch.

## Test Crossroads scene

Pack: `scenes` (Compendium → Scenes → **Test Crossroads**). Import it with one click, then activate the scene.

| | |
|---|---|
| File | `assets/maps/test-crossroads.webp` (thumb: `test-crossroads-thumb.webp`) |
| Canvas | 4096 × 4096 px |
| Grid | square, **128 px** per square, **1 square = 1 m** |
| Size | 32 × 32 m |

The map is a ruined village crossroads: four houses for cover, stone fences along the roads (a wall you can try to climb, or walk around through the junction), and a stream with a wooden footbridge in the south-east.

Starting walls are included: road fences, the south bank of the stream (the footbridge is a gap), and each house as a loop with a closed door. Token vision and fog exploration are off so the first test is easy to see; turn them on when you want fog of war. The fences are full movement-blocking walls — climbing them is a skill check the GM can call, or the wall can later be marked as terrain.

Grid notes are also stored on the scene at `flags.breath-and-the-veil.grid`.
