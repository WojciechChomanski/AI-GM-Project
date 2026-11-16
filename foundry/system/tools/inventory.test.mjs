// node --test tools/inventory.test.mjs
// Ports of the Python inventory tests: capacity, bands, placement, refusals.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  carryCapacity, loadRatio, loadTier, tierPenalties, actionAllowed, actionPenalty,
  actionEconomyPenalties, placeItem, carriedWeight, evaluate, RULES, itemWeight,
  missingWeight, actorInventoryState,
} from "../breath-and-the-veil/module/inventory.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const rulesPath = path.join(here, "..", "..", "..", "rules", "inventory.json");
const copyPath = path.join(here, "..", "breath-and-the-veil", "module", "inventory-rules.json");

const item = (extra) => {
  const { location, container_id, ...rest } = extra;
  const flags = { "breath-and-the-veil": {} };
  if (location) flags["breath-and-the-veil"].location = location;
  if (container_id) flags["breath-and-the-veil"].container_id = container_id;
  return { id: rest.id || rest.name || "x", type: rest.type || "gear", flags, ...rest };
};
const pack = (id = "travellers_backpack", location = "body") => {
  const src = RULES.backpacks.items.find((p) => p.id === id);
  return item({ ...src, type: "gear", is_container: true, location, equipped: location === "body", source_id: src.id });
};
const weapon = (id, weight, weapon_type = "1H_sword", location = "body") =>
  item({ id, name: id, type: "weapon", weight, weapon_type, location, equipped: location === "body",
    source_id: id, system: { source_id: id, weapon_type, weight } });
const armor = (id, weight, coverage, location = "body") =>
  item({ id, name: id, type: "armor", weight, coverage, location, equipped: location === "body",
    source_id: id, system: { source_id: id, coverage, weight } });

test("system copy of inventory rules matches rules/inventory.json", () => {
  const src = JSON.parse(fs.readFileSync(rulesPath, "utf8"));
  const dst = JSON.parse(fs.readFileSync(copyPath, "utf8"));
  assert.deepEqual(dst, src);
  assert.deepEqual(RULES, src);
});

test("carry capacity matches the approved formula", () => {
  assert.equal(carryCapacity(35, "M", "Human"), (20 + 35 * 1.5) * 1.15);
  assert.equal(carryCapacity(25, "F", "Human"), 20 + 25 * 1.5);
  assert.equal(carryCapacity(40, "M", "Dwarf"), (20 + 40 * 1.5) * 1.15 * 1.5);
  assert.equal(carryCapacity(70, "M", "Ogre"), (20 + 70 * 1.5) * 1.15 * 3);
  assert.equal(carryCapacity(35, "M", "Human", ["ox_back"]), (20 + 35 * 1.5) * 1.15 * 1.15);
});

test("load tiers and ported penalties", () => {
  const cap = carryCapacity(35, "M", "Human");
  assert.equal(loadTier(loadRatio(cap * 0.2, cap)), "light");
  assert.equal(loadTier(loadRatio(cap * 0.21, cap)), "medium");
  assert.equal(loadTier(loadRatio(cap * 0.51, cap)), "heavy");
  assert.equal(loadTier(loadRatio(cap + 0.01, cap)), "overloaded");
  assert.equal(tierPenalties("light", "F").stamina_regen_pct, 20);
  assert.equal(tierPenalties("heavy", "F").dex_aim_penalty, -10);
  assert.equal(tierPenalties("heavy", "M").agility_penalty, -5);
});

test("overloaded blocks sprint, acrobatics and unaided rope climb", () => {
  for (const action of ["sprint", "acrobatics", "rope_climb_unaided"]) {
    assert.equal(actionAllowed("heavy", action), true);
    assert.equal(actionAllowed("overloaded", action), false);
  }
  assert.equal(actionAllowed("overloaded", "climb"), true);
  assert.equal(actionPenalty("overloaded", "climb").athletics_penalty, -40);
  assert.equal(actionEconomyPenalties(0.9).ap_penalty, 2);
  assert.equal(actionEconomyPenalties(1.2).ap_penalty, 3);
  assert.equal(actionEconomyPenalties(1.2).placeholder, true);
});

test("70 kg on an average man is heavy, not overloaded, under the current formula", () => {
  const ev = evaluate(35, "M", "Human", [item({ id: "kit", type: "gear", weight: 70, location: "backpack" })]);
  assert.equal(ev.tier, "heavy");
  assert.equal(ev.actions.rope_climb_unaided.allowed, true);
  const over = evaluate(35, "M", "Human", [item({ id: "kit", type: "gear", weight: 90, location: "backpack" })]);
  assert.equal(over.tier, "overloaded");
  assert.equal(over.actions.sprint.allowed, false);
  assert.equal(over.actions.walk.allowed, true);
});

test("clinch mass counts as carried load", () => {
  assert.equal(evaluate(35, "M", "Human", [], [], 80).tier, "heavy");
  assert.equal(evaluate(35, "M", "Human", [], [], 90).tier, "overloaded");
});

test("drop onto free slots, then into a pack, then refuse", () => {
  const first = placeItem([], weapon("arming_sword", 5, "1H_sword", ""));
  assert.equal(first.ok, true);
  assert.equal(first.location, "body");
  const claymore = placeItem([], weapon("claymore", 12, "2H_sword", ""));
  assert.deepEqual(new Set(claymore.slots), new Set(["main_hand", "off_hand"]));
  const held = weapon("arming_sword", 5);
  const bp = pack();
  const stowed = placeItem([held, bp], weapon("messer", 5, "1H_sword", ""));
  assert.equal(stowed.ok, true);
  assert.equal(stowed.location, "backpack");
  assert.equal(stowed.container_id, "travellers_backpack");
  const refused = placeItem([held], weapon("messer", 5, "1H_sword", ""));
  assert.equal(refused.ok, false);
  assert.match(refused.message, /pack/i);
});

test("full satchel refuses another item", () => {
  const bp = pack("satchel");
  const stuffed = item({ id: "rocks", name: "Rocks", type: "gear", weight: 8, location: "backpack", container_id: "satchel" });
  const no = placeItem([bp, stuffed], item({ id: "apple", name: "Apple", type: "gear", weight: 0.5 }));
  assert.equal(no.ok, false);
  const yes = placeItem([bp, item({ id: "rocks", type: "gear", weight: 7, location: "backpack", container_id: "satchel" })],
    item({ id: "apple", name: "Apple", type: "gear", weight: 0.5 }));
  assert.equal(yes.ok, true);
});

test("overlapping armour goes to the pack; a second pack is refused", () => {
  const plate = armor("full_plate", 32.2, ["chest", "head"]);
  const bp = pack();
  const padded = armor("padded", 5, ["chest"], "");
  const stowed = placeItem([plate, bp], padded);
  assert.equal(stowed.location, "backpack");
  const helm = armor("helm", 2, ["head"]);
  const chest = armor("padded", 5, ["chest"], "");
  assert.equal(placeItem([helm], chest).location, "body");
  const second = pack("satchel", "");
  assert.equal(placeItem([bp], second).ok, false);
});

test("class items are not inventory and missing weights are flagged as zero", () => {
  assert.equal(placeItem([], { id: "knight", type: "class", name: "Knight" }).physical, false);
  const longsword = weapon("longsword", null, "sword");
  delete longsword.weight;
  longsword.system.weight = null;
  longsword.system.source_id = "longsword";
  assert.equal(itemWeight(longsword), 0);
  assert.equal(missingWeight(longsword), true);
  assert.equal(carriedWeight([pack("satchel"), weapon("arming_sword", 5),
    item({ id: "stones", type: "gear", weight: 3, location: "backpack", container_id: "satchel" })]), 0.8 + 5 + 3);
});

test("actorInventoryState fills equipped slots and backpack contents", () => {
  const actor = {
    system: { attributes: { strength: { value: 35 } }, details: { gender: "M", race: "Human" }, combat: { grip: "two_hands" } },
    items: [pack(), weapon("arming_sword", 5), item({ id: "stones", type: "gear", weight: 3, location: "backpack", container_id: "travellers_backpack" })],
    flags: {},
  };
  const state = actorInventoryState(actor);
  assert.equal(state.equipped.main_hand, "arming_sword");
  assert.equal(state.equipped.back, "travellers_backpack");
  assert.equal(state.backpack.itemId, "travellers_backpack");
  assert.deepEqual(state.backpack.contents, ["stones"]);
  assert.equal(state.carried_weight, 1.5 + 5 + 3);
  assert.equal(state.carry_capacity, carryCapacity(35, "M", "Human"));
  assert.equal(state.equipped.chest, "");
});
