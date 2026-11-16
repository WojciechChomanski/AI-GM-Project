// Breath and the Veil - Foundry VTT v14 system entry point.
import { ACTOR_MODELS, ITEM_MODELS } from "./data.mjs";
import { BreathActorSheet, BreathItemSheet, applyIdentity, previewAssignment, IDENTITY } from "./sheets.mjs";
import { registerInventory } from "./inventory.mjs";

const ID = "breath-and-the-veil";

registerInventory();

Hooks.once("init", () => {
  Object.assign(CONFIG.Actor.dataModels, ACTOR_MODELS);
  Object.assign(CONFIG.Item.dataModels, ITEM_MODELS);
  const DSC = foundry.applications.apps.DocumentSheetConfig;
  DSC.registerSheet(Actor, ID, BreathActorSheet, { makeDefault: true, label: "BREATH.SheetActor" });
  DSC.registerSheet(Item, ID, BreathItemSheet, { makeDefault: true, label: "BREATH.SheetItem" });
  game.settings.register(ID, "backendUrl", {
    name: "BREATH.Setting.backendUrl", hint: "BREATH.Setting.backendUrlHint",
    scope: "client", config: true, restricted: true, type: String, default: "http://127.0.0.1:8000",
  });
  const Hb = globalThis.Handlebars;
  if (Hb && !Hb.helpers.join) {
    Hb.registerHelper("join", (arr) => Array.isArray(arr) ? arr.join(", ") : (arr ?? ""));
  }
  console.log(`${ID} | initialised`);
});

function characterParent(item) {
  const actor = item.parent;
  return actor && actor.type === "character" ? actor : null;
}

Hooks.on("preCreateItem", (item, data, options) => {
  const actor = characterParent(item);
  if (!actor || !IDENTITY.has(item.type) || options?.breathApply) return;
  const check = previewAssignment(actor, item);
  if (!check.ok) {
    ui.notifications?.error(check.reasons.join(" "));
    return false;
  }
});

Hooks.on("createItem", async (item, options) => {
  const actor = characterParent(item);
  if (!actor || options?.breathApply) return;
  if (!IDENTITY.has(item.type)) return;
  const extras = actor.items.filter((i) => i.type === item.type && i.id !== item.id);
  if (extras.length) await actor.deleteEmbeddedDocuments("Item", extras.map((i) => i.id));
  // Dropping a Gender that names a race: keep details in sync; a matching Race item
  // may be added by the user from the pack (we do not auto-import from the pack here,
  // to avoid a second createItem cycle). details.race is still filled by applyIdentity.
  await applyIdentity(actor);
});

Hooks.on("deleteItem", async (item, options) => {
  const actor = characterParent(item);
  if (!actor || options?.breathApply) return;
  if (!IDENTITY.has(item.type)) return;
  await applyIdentity(actor);
});
