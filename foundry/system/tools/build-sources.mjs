// Runs scripts/build_foundry_packs.py with whichever Python is installed (python3, python, or py on Windows).
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const script = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..", "scripts", "build_foundry_packs.py");
for (const py of [process.env.PYTHON, "python3", "python", "py"].filter(Boolean)) {
  const r = spawnSync(py, [script], { stdio: "inherit" });
  if (r.error?.code === "ENOENT") continue;
  process.exit(r.status ?? 1);
}
console.error("Python 3 not found; set PYTHON=/path/to/python");
process.exit(1);
