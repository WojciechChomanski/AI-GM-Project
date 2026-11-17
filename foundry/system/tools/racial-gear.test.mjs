import { test } from "node:test";
import assert from "node:assert/strict";
import { refuseReason, canEquip, isShield, sizeClass } from "../breath-and-the-veil/module/racial-gear.mjs";
import { placeItem } from "../breath-and-the-veil/module/inventory.mjs";

test("dwarves are refused a sabre and elves a shield on drop", () => {
  const sabre = { type: "weapon", name: "Sabre", system: { source_id: "hungarian_hussar_sabre", weapon_type: "1H_sword", weight: 2 } };
  const shield = { type: "gear", name: "Heater", system: { item_kind: "shield", weight: 3, slot: "off_hand" } };
  assert.equal(refuseReason("Dwarf", sabre), "Dwarves will not bear a blade the elves use.");
  assert.ok(isShield(shield));
  assert.equal(refuseReason("Elf", shield), "Elves will not hide behind a shield.");
  const d = placeItem([], sabre, "two_hands", "Dwarf");
  assert.equal(d.ok, false);
  const e = placeItem([], shield, "two_hands", "Elf");
  assert.equal(e.ok, false);
  assert.equal(placeItem([], sabre, "two_hands", "Human").ok, true);
  assert.equal(canEquip("Ogre", sabre), true);
  assert.equal(sizeClass({ system: { size_class: "large" } }), "large");
  assert.equal(refuseReason("Human", { system: { source_id: "ogre_claymore", size_class: "large" } }),
    "This is sized for an ogre; it cannot be wielded.");
});
