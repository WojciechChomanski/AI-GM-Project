const { HandlebarsApplicationMixin } = foundry.applications.api;
const { ActorSheetV2, ItemSheetV2 } = foundry.applications.sheets;
import { ATTRIBUTES } from "./data.mjs";

const ITEM_GROUPS = ["weapon", "armor", "class", "race", "gender", "talent", "advantage", "flaw", "skill"];

export class BreathActorSheet extends HandlebarsApplicationMixin(ActorSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["breath", "sheet", "actor"],
    position: { width: 720, height: 760 },
    form: { submitOnChange: true },
    window: { resizable: true },
    actions: {
      openItem: BreathActorSheet.#openItem,
      deleteItem: BreathActorSheet.#deleteItem,
    },
  };
  static PARTS = { sheet: { template: "systems/breath-and-the-veil/templates/actor-sheet.hbs" } };

  async _prepareContext(options) {
    const ctx = await super._prepareContext(options);
    const actor = this.document;
    ctx.actor = actor;
    ctx.system = actor.system;
    ctx.gripChoices = { two_hands: "BREATH.TwoHands", one_hand: "BREATH.OneHand" };
    ctx.isCharacter = actor.type === "character";
    ctx.attributes = ATTRIBUTES.map((key) => ({ key, label: game.i18n.localize(`BREATH.Attr.${key}`),
      ...actor.system.attributes[key] }));
    ctx.groups = ITEM_GROUPS.map((type) => ({ type, label: game.i18n.localize(`TYPES.Item.${type}`),
      items: actor.items.filter((i) => i.type === type) })).filter((g) => g.items.length);
    ctx.biography = await foundry.applications.ux.TextEditor.implementation.enrichHTML(actor.system.biography,
      { relativeTo: actor });
    return ctx;
  }

  static #openItem(event, target) {
    this.document.items.get(target.closest("[data-item-id]").dataset.itemId)?.sheet.render(true);
  }
  static async #deleteItem(event, target) {
    await this.document.items.get(target.closest("[data-item-id]").dataset.itemId)?.delete();
  }
}

export class BreathItemSheet extends HandlebarsApplicationMixin(ItemSheetV2) {
  static DEFAULT_OPTIONS = {
    classes: ["breath", "sheet", "item"],
    position: { width: 520, height: 560 },
    form: { submitOnChange: true },
    window: { resizable: true },
  };
  static PARTS = { sheet: { template: "systems/breath-and-the-veil/templates/item-sheet.hbs" } };

  async _prepareContext(options) {
    const ctx = await super._prepareContext(options);
    const item = this.document;
    ctx.item = item;
    ctx.system = item.system;
    ctx.typeLabel = game.i18n.localize(`TYPES.Item.${item.type}`);
    ctx.isWeapon = item.type === "weapon";
    ctx.isArmor = item.type === "armor";
    ctx.description = await foundry.applications.ux.TextEditor.implementation.enrichHTML(item.system.description,
      { relativeTo: item });
    ctx.rulesJson = JSON.stringify(item.system.rules ?? {}, null, 2);
    return ctx;
  }
}
