// Compile foundry/system/build/packs-src/<pack>/*.json into LevelDB packs (Foundry v11+ format, used by v14)
// with the official @foundryvtt/foundryvtt-cli. Run after scripts/build_foundry_packs.py (or `npm run build`).
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, "..", "build", "packs-src");
const dest = path.join(here, "..", "breath-and-the-veil", "packs");
const manifest = JSON.parse(fs.readFileSync(path.join(here, "..", "breath-and-the-veil", "system.json"), "utf8"));

for (const pack of manifest.packs) {
  const from = path.join(src, pack.name);
  if (!fs.existsSync(from)) throw new Error(`missing pack source ${from}; run scripts/build_foundry_packs.py`);
  const to = path.join(dest, pack.name);
  fs.rmSync(to, { recursive: true, force: true });
  await compilePack(from, to, { log: false });
  console.log(`packed ${pack.name}: ${fs.readdirSync(from).length} documents`);
}
