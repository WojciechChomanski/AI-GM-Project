# Breath and the Veil: Foundry VTT v14 game system

Phase 1 of `breath-audit/FOUNDRY_INTEGRATION_PLAN.md`: a real Foundry system, with Python as the backend. CSB (`foundry/csb/`, PR 13) remains the fallback.

```
foundry/system/
  breath-and-the-veil/        <- the system Foundry loads (this folder is what gets zipped)
    system.json               manifest (v14: compatibility, documentTypes, packs, manifest/download URLs)
    module/breath.mjs         init: registers data models + sheets
    module/data.mjs           TypeDataModel classes (VISIBLE stats only)
    module/sheets.mjs         ApplicationV2 actor/item sheets
    templates/*.hbs, styles/, lang/en.json
    packs/                    generated LevelDB compendiums (git-ignored)
  tools/compile-packs.mjs     JSON sources -> LevelDB with @foundryvtt/foundryvtt-cli
  tools/system.test.mjs       node tests (manifest, models, packs)
  package.json                build tooling only
scripts/build_foundry_packs.py   repo rules JSON -> pack sources (foundry/system/build/packs-src)
ci/foundry-release.yml       tag -> tests, build, zip, GitHub release (move to .github/workflows/)
```

## Data

- **Actors:**
  - character, npc and creature
  - the 12 visible attributes (value and cap), HP, stamina, combat state, details and biography
  - `felt`: a list of `{topic, text}`
- **Items:** weapon, armour (with saved `durability.value/max`), class, race, gender, talent, flaw, advantage and skill.
- **Hidden stats are not in the system at all.** Faith, Virtue, Piety, Holy Fury, Corruption, the stress number and Reputation live only in the Python backend.
  - The build strips those keys from every compendium document.
  - Tests in both pytest and node fail if one appears.
  - Later phases fill `felt` with text only, for example "Stress: uneasy", written from the GM's client.

### Compendium sources

| Pack | Source |
|---|---|
| weapons | `rules/weapons.json` (via `scripts/foundry_export.weapon_item`) |
| armor | `rules/armors.json` |
| classes | `rules/classes/*.json` (`template.json` skipped) |
| races | `rules/races.json` |
| genders | `rules/stats.json` (one per race/gender, with starting stats and caps) |
| talents | `rules/talents/*.json` |
| flaws, advantages | `rules/creation/*.json` |
| skills | collected from the classes' `skills` and `skill_trees` (there is no skills rules file yet) |

Document ids are derived from the source key, so a rebuild updates entries instead of duplicating them.

## Build locally

Needs Python 3.11+ and Node 20+.

```
cd foundry/system
npm ci          # installs @foundryvtt/foundryvtt-cli
npm run build   # scripts/build_foundry_packs.py (via tools/build-sources.mjs), then tools/compile-packs.mjs
npm test        # node tests: manifest, data models, every pack extracts with no hidden keys
```

From the repo root, `python -m pytest -q tests` includes `tests/test_foundry_system.py`.

**Close Foundry (or the world) before rebuilding packs.** Foundry locks the LevelDB files while it runs.

## Install in Foundry

### A) From a release (normal use)

1. Foundry setup screen → **Game Systems** → **Install System**.
2. Paste the manifest URL into **Manifest URL**: `https://github.com/WojciechChomanski/AI-GM-Project/releases/latest/download/system.json`
3. Click **Install**, then create a world using **Breath and the Veil**.
4. Updates: Game Systems → **Check for Updates** → Update.

The repository must be public, or the release assets must be otherwise downloadable, for this URL to work.

### B) Dev link: run straight from the repo

1. Build once (see above), then link the folder into your Foundry user data.
   - Find the user data path under Foundry → Configuration → *User Data Path*.
   - Then run:

   ```
   # Windows (PowerShell as admin, or with Developer Mode on):
   New-Item -ItemType SymbolicLink -Path "$env:LOCALAPPDATA\FoundryVTT\Data\systems\breath-and-the-veil" `
            -Target "C:\path\to\AI-GM-Project\foundry\system\breath-and-the-veil"
   # macOS:
   ln -s ~/path/AI-GM-Project/foundry/system/breath-and-the-veil "$HOME/Library/Application Support/FoundryVTT/Data/systems/breath-and-the-veil"
   # Linux:
   ln -s ~/path/AI-GM-Project/foundry/system/breath-and-the-veil ~/.local/share/FoundryVTT/Data/systems/breath-and-the-veil
   ```

2. The folder name must be exactly `breath-and-the-veil`, matching the `id` in system.json.
3. If a release install is already present, remove it first (Game Systems → Uninstall) or the link clashes.
4. After code or template changes, reload the browser (F5). After a pack rebuild, restart the world.

## Release (you do this)

**One-time step: activate the workflow.** The bot's GitHub token may not push workflow files, so the workflow ships as `foundry/system/ci/foundry-release.yml`. Move it into place once:

```
git mv foundry/system/ci/foundry-release.yml .github/workflows/foundry-release.yml
git commit -m "Activate Foundry release workflow"
git push
```

You can also do this on GitHub: create `.github/workflows/foundry-release.yml` and paste in the contents.

1. Bump `"version"` in `system.json`. Optional: CI stamps the version from the tag anyway.
2. Commit and push to `main`.
3. Tag the commit and push the tag:

   ```
   git tag v0.1.0
   git push origin v0.1.0
   ```

4. The **Foundry system release** workflow then runs:
   - pytest
   - `npm run build` and `npm test`
   - it stamps `version` and `download` into system.json
   - it zips `breath-and-the-veil/` with LICENSE
   - it publishes a GitHub Release with `system.json` and `breath-and-the-veil.zip`

   The manifest URL always points to the latest release.

## Not verified on the build box

There is no Foundry install there, so the following were not run in Foundry:

- registering the sheets
- the Handlebars templates
- the actual install

What was verified:

- the manifest
- data models, with schemas loaded under stand-in field classes
- the packs: compiled and re-extracted with the official CLI

Report anything odd from the first real load, and include the console (F12) output.
