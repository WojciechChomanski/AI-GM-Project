// Compile foundry/system/build/packs-src/<pack>/*.json into LevelDB packs (Foundry v11+ format, used by v14)
// with the official @foundryvtt/foundryvtt-cli. Run after scripts/build_foundry_packs.py (or `npm run build`).
//
// Always run `npm run build` (sources + compile) before zipping a release. The v0.1.0 zip was cut from
// stale local LevelDB packs compiled on 3 Nov 2026 (Paladin still present, Knight missing, a bogus
// "integration" class). paladin.json was already gone from rules at the v0.1.0 tag; a clean rebuild
// would not have included it. This script refuses to compile a classes pack that fails verifyClassPack.
import { compilePack } from "@foundryvtt/foundryvtt-cli";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { verifyClassPack } from "./verify-class-pack.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, "..", "build", "packs-src");
const dest = path.join(here, "..", "breath-and-the-veil", "packs");
const manifest = JSON.parse(fs.readFileSync(path.join(here, "..", "breath-and-the-veil", "system.json"), "utf8"));

function classDocs() {
  const dir = path.join(src, "classes");
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")));
}

fs.rmSync(dest, { recursive: true, force: true });

for (const pack of manifest.packs) {
  const from = path.join(src, pack.name);
  if (!fs.existsSync(from)) throw new Error(`missing pack source ${from}; run scripts/build_foundry_packs.py`);
  if (pack.name === "classes") {
    const errs = verifyClassPack(classDocs());
    if (errs.length) throw new Error(`refusing to compile classes pack:\n- ${errs.join("\n- ")}`);
  }
  const to = path.join(dest, pack.name);
  fs.rmSync(to, { recursive: true, force: true });
  await compilePack(from, to, { log: false });
  console.log(`packed ${pack.name}: ${fs.readdirSync(from).length} documents`);
}
