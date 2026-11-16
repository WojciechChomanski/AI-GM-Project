// node --test tools/   (after `npm run build`)
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  computeCharacter, canAssign, classLocks, classPageView, carryCapacity,
  computeHp, computeStamina, omitHidden, isHiddenStat, portraitPath, classIconPath,
  actorSystemPatch, ATTRIBUTES, scaledZones,
} from "../breath-and-the-veil/module/character.mjs";
import { verifyClassPack } from "./verify-class-pack.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, "..", "build", "packs-src");

function loadPack(name) {
  const dir = path.join(src, name);
  return fs.readdirSync(dir).filter((f) => f.endsWith(".json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")));
}

function bySource(docs, id) {
  return docs.find((d) => d.system?.source_id === id || d.name === id);
}

const races = loadPack("races");
const genders = loadPack("genders");
const classes = loadPack("classes");

test("packs-src is present (run npm run build first)", () => {
  assert.ok(fs.existsSync(path.join(src, "classes")));
  assert.deepEqual(verifyClassPack(classes), []);
});

test("human male crusader knight fills visible stats, caps, hp and stamina", () => {
  const computed = computeCharacter({
    raceItem: bySource(races, "Human"),
    genderItem: bySource(genders, "Human_Male"),
    classItem: bySource(classes, "Crusader_Knight"),
  });
  assert.equal(computed.ok, true);
  assert.equal(computed.details.race, "Human");
  assert.equal(computed.details.gender, "Male");
  assert.equal(computed.details.class_name, "Crusader_Knight");
  assert.equal(computed.details.mass, 80);
  // Human male STR 35 + class 12, cap 50
  assert.equal(computed.attributes.strength.value, 47);
  assert.equal(computed.attributes.strength.max, 50);
  assert.equal(computed.resources.hp.max, 115); // sum of official scaled zones
  assert.equal(computed.resources.stamina.max, 110); // 100 + stamina_max_flat 10
  const expectedZones = { chest: 24, left_upper_leg: 15, right_upper_leg: 15, stomach: 13, head: 8,
    left_upper_arm: 7, right_upper_arm: 7, left_lower_leg: 7, right_lower_leg: 7,
    left_lower_arm: 3, right_lower_arm: 3, throat: 3, groin: 3 };
  for (const [id, max] of Object.entries(expectedZones)) {
    assert.equal(computed.resources.zones[id].max, max, id);
    assert.equal(computed.resources.zones[id].value, max, id);
  }
  const zoneSum = Object.values(computed.resources.zones).reduce((a, z) => a + z.max, 0);
  assert.equal(zoneSum, computed.resources.hp.max);
  assert.equal(computed.inventory.carry_capacity, (20 + 47 * 1.5) * 1.15);
  for (const key of Object.keys(computed.attributes)) {
    assert.ok(ATTRIBUTES.includes(key), key);
    assert.ok(!isHiddenStat(key), key);
  }
  const blob = JSON.stringify(computed);
  for (const word of ["faith", "virtue", "piety", "holy_fury", "corruption", "stress", "reputation"]) {
    assert.equal(blob.toLowerCase().includes(`"${word}"`), false, word);
  }
  assert.ok(computed.features.some((f) => /basic strike/i.test(f.name)));
  assert.ok(actorSystemPatch(computed)["system.details.race"] === "Human");
});

test("race and gender locks reject illegal drops", () => {
  const dwarf = bySource(races, "Dwarf");
  const humanFemale = bySource(genders, "Human_Female");
  const humanMale = bySource(genders, "Human_Male");
  const ck = bySource(classes, "Crusader_Knight");
  const vs = bySource(classes, "Veil_Sorceress");
  const stone = bySource(classes, "Stonewarden");

  assert.equal(canAssign({
    race: "Human", gender: "Female", classItem: ck, raceItem: bySource(races, "Human"),
  }).ok, false);
  assert.equal(computeCharacter({
    raceItem: bySource(races, "Human"), genderItem: humanFemale, classItem: ck,
  }).ok, false);

  assert.equal(canAssign({
    race: "Dwarf", gender: "Male", classItem: vs, raceItem: dwarf,
  }).ok, false);

  // Dwarves are male-only even without a class.
  assert.equal(canAssign({ race: "Dwarf", gender: "Female", raceItem: dwarf }).ok, false);
  assert.equal(canAssign({ race: "Ogre", gender: "Female", raceItem: bySource(races, "Ogre") }).ok, false);

  assert.equal(canAssign({
    race: "Dwarf", gender: "Male", classItem: stone, raceItem: dwarf,
  }).ok, true);

  assert.equal(canAssign({
    race: "Elf", gender: "Female", classItem: vs, raceItem: bySource(races, "Elf"),
  }).ok, true);

  // Locks are taken from race_lock / restrictions, not only allowed_races fields.
  const ckLocks = classLocks(ck);
  assert.deepEqual(ckLocks.races, ["Human"]);
  assert.deepEqual(ckLocks.genders, ["Male"]);
});

test("elf female veil sorceress applies intelligence bonus and female-only magic lock", () => {
  const computed = computeCharacter({
    raceItem: bySource(races, "Elf"),
    genderItem: bySource(genders, "Elf_Female"),
    classItem: bySource(classes, "Veil_Sorceress"),
  });
  assert.equal(computed.ok, true);
  const start = bySource(genders, "Elf_Female").system.rules.starting_stats.intelligence;
  const cap = bySource(genders, "Elf_Female").system.rules.max_stats.intelligence;
  assert.equal(computed.attributes.intelligence.value, Math.min(start + 14, cap));
  assert.equal(computed.attributes.intelligence.max, cap);
  // Elf stamina_bonus 10
  assert.equal(computed.resources.stamina.max, 110);
});

test("carry capacity uses sex, dwarf and ogre multipliers", () => {
  assert.equal(carryCapacity({ strength: 35, gender: "Male", race: "Human" }), (20 + 35 * 1.5) * 1.15);
  assert.equal(carryCapacity({ strength: 35, gender: "Female", race: "Human" }), (20 + 35 * 1.5));
  assert.equal(carryCapacity({ strength: 40, gender: "Male", race: "Dwarf" }), (20 + 40 * 1.5) * 1.15 * 1.5);
  assert.equal(carryCapacity({ strength: 50, gender: "Male", race: "Ogre" }), (20 + 50 * 1.5) * 1.15 * 3);
  assert.equal(carryCapacity({ strength: 35, gender: "Male", race: "Human", talents: ["ox_back"] }),
    (20 + 35 * 1.5) * 1.15 * 1.15);
});

test("hp formula matches zone_hp.hp_multiplier", () => {
  assert.equal(computeHp({ raceHpBonus: 20, classHpPercent: 15 }), Math.round(100 * 1.2 * 1.15));
  assert.equal(computeHp({ raceHpBonus: 100, classHpPercent: 0 }), 200);
  assert.equal(computeStamina({ raceBonus: 15, classFlat: 8 }), 123);
});

test("class page shows career, ranks, skills and Paladin as an honour, never hidden gates", () => {
  const page = classPageView(bySource(classes, "Crusader_Knight"));
  assert.match(page.name, /Crusader Knight/i);
  assert.ok(page.progression.length >= 4);
  assert.ok(page.pathName);
  assert.ok(page.ranks.length >= 3);
  assert.ok(page.honours.some((h) => /paladin/i.test(h.name) || h.id === "paladin"));
  const blob = JSON.stringify(page).toLowerCase();
  for (const word of ["virtue", "piety", "faith", "corruption_level", "holy_fury_stacks"]) {
    // Honour/ability flavour may mention "corruption" as fiction; numeric hidden keys must be gone.
    assert.equal(blob.includes(`"${word}"`), false, word);
  }
  for (const rank of page.ranks) {
    assert.ok(!rank.requires.some((r) => /virtue|piety|faith/i.test(r)), rank.requires);
  }
  const pal = page.honours.find((h) => /paladin/i.test(h.name) || h.id === "paladin");
  assert.ok(pal);
  assert.ok(!pal.requires.some((r) => /virtue|piety|corruption/i.test(r)), pal.requires);
});

test("worldly knight has career evolutions labelled placeholder when the rules say so", () => {
  const page = classPageView(bySource(classes, "Knight"));
  assert.ok(page.skills.some((s) => s.source_id === "riding"));
  assert.ok(page.evolutions.some((e) => e.placeholder));
});

test("omitHidden drops hidden keys and the hidden/hidden_start blocks", () => {
  const cleaned = omitHidden({
    strength: 35, faith: 20, requires: { sessions_min: 6, hidden: { virtue: 75 }, reputation: 40 },
    hidden_start: { piety: 60 },
  });
  assert.deepEqual(cleaned, { strength: 35, requires: { sessions_min: 6 } });
  assert.equal(isHiddenStat("holy_fury_stacks"), true);
  assert.equal(isHiddenStat("weapon_skill"), false);
});

test("art paths fall back when the race-gender or class file is missing", () => {
  const exists = (p) => p.endsWith("_fallback.webp");
  assert.match(portraitPath("Human", "Male", { exists }), /_fallback\.webp$/);
  assert.match(classIconPath("Crusader_Knight", { exists }), /_fallback\.webp$/);
  const raw = portraitPath("Human", "Male");
  assert.match(raw.preferred, /portraits\/human-male\.webp$/);
});

test("class drop requires race and gender first", () => {
  const ck = bySource(classes, "Crusader_Knight");
  const noIdentity = canAssign({ classItem: ck });
  assert.equal(noIdentity.ok, false);
  assert.match(noIdentity.reasons.join(" "), /Race and a Gender/i);
  assert.equal(canAssign({ race: "Human", classItem: ck }).ok, false);
  assert.equal(canAssign({ gender: "Male", classItem: ck }).ok, false);
  const withItems = canAssign({
    race: "Human", gender: "Male", classItem: ck,
    raceItem: bySource(races, "Human"), genderItem: bySource(genders, "Human_Male"),
    requireIdentityItems: true,
  });
  assert.equal(withItems.ok, true);
  const itemsMissing = canAssign({
    race: "Human", gender: "Male", classItem: ck, requireIdentityItems: true,
  });
  assert.equal(itemsMissing.ok, false);
});

test("scaledZones matches scripts/zone_hp.scaled_zones (leftovers to chest)", () => {
  assert.deepEqual(scaledZones(1), {
    chest: 20, left_upper_leg: 13, right_upper_leg: 13, stomach: 11, head: 7,
    left_upper_arm: 6, right_upper_arm: 6, left_lower_leg: 6, right_lower_leg: 6,
    left_lower_arm: 3, right_lower_arm: 3, throat: 3, groin: 3,
  });
  assert.deepEqual(scaledZones(1.15), {
    chest: 24, left_upper_leg: 15, right_upper_leg: 15, stomach: 13, head: 8,
    left_upper_arm: 7, right_upper_arm: 7, left_lower_leg: 7, right_lower_leg: 7,
    left_lower_arm: 3, right_lower_arm: 3, throat: 3, groin: 3,
  });
  assert.equal(computeHp({ raceHpBonus: 20, classHpPercent: 15 }), 138);
  assert.equal(Object.values(scaledZones(1.38)).reduce((a, b) => a + b, 0), 138);
});

test("classes pack does not contain Cleric", () => {
  const ids = classes.flatMap((d) => [d.system?.source_id, d.name]).map((x) => String(x).toLowerCase());
  assert.ok(!ids.includes("cleric"));
  const errs = verifyClassPack([...classes, { name: "Cleric", source_id: "Cleric" }]);
  assert.ok(errs.some((e) => /cleric/i.test(e)));
});
