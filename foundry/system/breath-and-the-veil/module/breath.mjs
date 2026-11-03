// Breath and the Veil - Foundry VTT v14 system entry point.
import { ACTOR_MODELS, ITEM_MODELS } from "./data.mjs";
import { BreathActorSheet, BreathItemSheet } from "./sheets.mjs";

const ID = "breath-and-the-veil";

Hooks.once("init", () => {
  Object.assign(CONFIG.Actor.dataModels, ACTOR_MODELS);
  Object.assign(CONFIG.Item.dataModels, ITEM_MODELS);
  const DSC = foundry.applications.apps.DocumentSheetConfig;
  DSC.registerSheet(Actor, ID, BreathActorSheet, { makeDefault: true, label: "BREATH.SheetActor" });
  DSC.registerSheet(Item, ID, BreathItemSheet, { makeDefault: true, label: "BREATH.SheetItem" });
  // Phase 2+: backend URL setting (GM-only, client scope so it is stored only in the GM's browser).
  game.settings.register(ID, "backendUrl", { name: "BREATH.Setting.backendUrl", hint: "BREATH.Setting.backendUrlHint",
    scope: "client", config: true, restricted: true, type: String, default: "http://127.0.0.1:8000" });
  console.log(`${ID} | initialised`);
});
