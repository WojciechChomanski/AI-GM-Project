// node --test tools/   (after `npm run build`)
// Checks: manifest is valid for v14, data models load and contain NO hidden-stat fields,
// every LevelDB pack extracts and no document carries hidden-stat keys.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { extractPack } from "@foundryvtt/foundryvtt-cli";

const here = path.dirname(fileURLToPath(import.meta.url));
const sys = path.join(here, "..", "breath-and-the-veil");
const manifest = JSON.parse(fs.readFileSync(path.join(sys, "system.json"), "utf8"));
const HIDDEN = /^(faith|virtue|piety|holy_?fury\w*|corruption\w*|stress\w*|reputation\w*)$/i;

// Minimal stand-ins for foundry.data.fields so the real data.mjs can be imported outside Foundry.
class Field { constructor(a, b) { this.options = (a && !(a instanceof Field) ? a : b) || {}; this.inner = a instanceof Field ? a : null; } }
class SchemaField extends Field { constructor(fields, o) { super(o); this.fields = fields; } }
class ArrayField extends Field { constructor(el, o) { super(o); this.element = el; } }
globalThis.foundry = { abstract: { TypeDataModel: class {} }, data: { fields: {
  SchemaField, ArrayField, NumberField: Field, StringField: Field, HTMLField: Field, BooleanField: Field, ObjectField: Field } } };

function keys(schema, prefix = "") {
  const out = [];
  for (const [k, f] of Object.entries(schema)) {
    out.push(prefix + k);
    if (f instanceof SchemaField) out.push(...keys(f.fields, `${prefix}${k}.`));
    if (f instanceof ArrayField && f.element instanceof SchemaField) out.push(...keys(f.element.fields, `${prefix}${k}[].`));
  }
  return out;
}

test("manifest targets v14 and declares every model type", async () => {
  assert.equal(manifest.id, "breath-and-the-veil");
  assert.equal(String(manifest.compatibility.minimum), "14");
  assert.match(manifest.manifest, /releases\/latest\/download\/system\.json$/);
  const { ACTOR_MODELS, ITEM_MODELS } = await import(pathToFileURL(path.join(sys, "module", "data.mjs")));
  assert.deepEqual(Object.keys(manifest.documentTypes.Actor).sort(), Object.keys(ACTOR_MODELS).sort());
  assert.deepEqual(Object.keys(manifest.documentTypes.Item).sort(), Object.keys(ITEM_MODELS).sort());
});

test("data models have no hidden-stat fields", async () => {
  const { ACTOR_MODELS, ITEM_MODELS } = await import(pathToFileURL(path.join(sys, "module", "data.mjs")));
  for (const [type, M] of Object.entries({ ...ACTOR_MODELS, ...ITEM_MODELS })) {
    for (const k of keys(M.defineSchema())) {
      assert.ok(!k.split(/[.\[\]]+/).some((p) => HIDDEN.test(p)), `${type}.${k} is a hidden stat`);
    }
  }
});

function walk(node, where, bad) {
  if (Array.isArray(node)) node.forEach((v, i) => walk(v, `${where}[${i}]`, bad));
  else if (node && typeof node === "object") for (const [k, v] of Object.entries(node)) {
    if (HIDDEN.test(k)) bad.push(`${where}.${k}`);
    walk(v, `${where}.${k}`, bad);
  }
}

test("every pack extracts, matches its type, and carries no hidden-stat keys", async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "bv-packs-"));
  const types = { weapons: "weapon", armor: "armor", classes: "class", races: "race", genders: "gender",
    talents: "talent", flaws: "flaw", advantages: "advantage", skills: "skill" };
  for (const pack of manifest.packs) {
    const out = path.join(tmp, pack.name);
    await extractPack(path.join(sys, pack.path), out, { log: false });
    const docs = fs.readdirSync(out).map((f) => JSON.parse(fs.readFileSync(path.join(out, f), "utf8")));
    assert.ok(docs.length > 0, `${pack.name} is empty`);
    const bad = [];
    for (const d of docs) {
      assert.equal(d.type, types[pack.name], `${pack.name}/${d.name}`);
      walk(d.system, `${pack.name}/${d.name}`, bad);
    }
    assert.deepEqual(bad, [], "hidden-stat keys in packs");
  }
});
