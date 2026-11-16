// Data models (Foundry v14 TypeDataModel). VISIBLE stats only.
// Hidden stats (faith, virtue, piety, holy fury, corruption, the stress number, reputation) are deliberately
// absent: they live only in the Breath backend. Players see the `felt` text the backend writes (later phases).
const { SchemaField, NumberField, StringField, HTMLField, BooleanField, ArrayField, ObjectField } = foundry.data.fields;

export const ATTRIBUTES = ["strength", "toughness", "agility", "mobility", "dexterity", "endurance",
  "intelligence", "willpower", "perception", "charisma", "weapon_skill", "ballistic_skill"];

const int = (initial = 0, opts = {}) => new NumberField({ required: true, integer: true, initial, ...opts });
const stat = (initial) => new SchemaField({ value: int(initial, { min: 0 }), max: int(100, { min: 0 }) });
const resource = (initial) => new SchemaField({ value: int(initial), max: int(initial, { min: 0 }) });

class BreathActorData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      attributes: new SchemaField(Object.fromEntries(ATTRIBUTES.map((a) => [a, stat(30)]))),
      resources: new SchemaField({ hp: resource(100), stamina: resource(100) }),
      combat: new SchemaField({
        weapon_in_hand: new StringField({ initial: "" }),
        grip: new StringField({ initial: "two_hands", choices: ["two_hands", "one_hand"] }),
        current_guard: new StringField({ initial: "" }),
        shield_equipped: new BooleanField({ initial: false }),
      }),
      biography: new HTMLField({ initial: "" }),
      // Inventory contract: see foundry/system/docs/ACTOR_MODEL.md (workstream B fills behaviour).
      inventory: new SchemaField({
        equipped: new SchemaField({
        head: new StringField({ initial: "" }),
        throat: new StringField({ initial: "" }),
        chest: new StringField({ initial: "" }),
        stomach: new StringField({ initial: "" }),
        groin: new StringField({ initial: "" }),
        left_upper_arm: new StringField({ initial: "" }),
        left_lower_arm: new StringField({ initial: "" }),
        right_upper_arm: new StringField({ initial: "" }),
        right_lower_arm: new StringField({ initial: "" }),
        left_upper_leg: new StringField({ initial: "" }),
        left_lower_leg: new StringField({ initial: "" }),
        right_upper_leg: new StringField({ initial: "" }),
        right_lower_leg: new StringField({ initial: "" }),
        main_hand: new StringField({ initial: "" }),
        off_hand: new StringField({ initial: "" }),
        back: new StringField({ initial: "" }),
        belt: new StringField({ initial: "" })
        }),
        backpack: new SchemaField({
          itemId: new StringField({ initial: "" }),
          contents: new ArrayField(new StringField()),
        }),
        carried_weight: new NumberField({ required: true, initial: 0, min: 0 }),
        carry_capacity: new NumberField({ required: true, initial: 0, min: 0 }),
      }),
      // Felt descriptions: player-facing TEXT only, written by the GM client from the backend (Phase 3).
      felt: new ArrayField(new SchemaField({ topic: new StringField(), text: new StringField() })),
    };
  }
}

export class CharacterData extends BreathActorData {
  static defineSchema() {
    return { ...super.defineSchema(),
      details: new SchemaField({ race: new StringField(), gender: new StringField(), class_name: new StringField(),
        background: new StringField(), age: int(25, { min: 0 }), mass: new NumberField({ initial: 0, min: 0 }) }) };
  }
}
export class NpcData extends BreathActorData {}
export class CreatureData extends BreathActorData {}

class BreathItemData extends foundry.abstract.TypeDataModel {
  static defineSchema() {
    return {
      source_id: new StringField({ initial: "" }),     // key in the repo rules file
      source_file: new StringField({ initial: "" }),
      description: new HTMLField({ initial: "" }),
      rules: new ObjectField(),                        // remaining repo data (hidden-stat keys stripped by the build)
    };
  }
}

export class WeaponData extends BreathItemData {
  static defineSchema() {
    return { ...super.defineSchema(),
      weapon_type: new StringField(), base_damage: int(0), damage_type: new StringField(),
      damage_types: new ArrayField(new StringField()), stamina_cost: int(0), min_str: int(0),
      weight: new NumberField({ initial: 0 }), durability: int(0), armor_piercing: new BooleanField(),
      guard_set: new StringField(), two_hand_guard_set: new StringField(), default_guard: new StringField(),
      guards: new ArrayField(new StringField()), maneuvers: new ArrayField(new StringField()),
      features: new ArrayField(new StringField()), equipped: new BooleanField(),
      location: new StringField({ initial: "" }), container_id: new StringField({ initial: "" }) };
  }
}
export class ArmorData extends BreathItemData {
  static defineSchema() {
    return { ...super.defineSchema(),
      tier: new StringField(), variant: new StringField(),
      rating: new SchemaField({ slashing: int(0), piercing: int(0), blunt: int(0) }),
      rigid: new BooleanField(), coverage: new ArrayField(new StringField()), stamina_penalty: int(0),
      weight: new NumberField({ initial: 0 }),
      durability: new SchemaField({ value: int(0), max: int(0) }),   // saved per item (Phase 2 writes engine wear)
      equipped: new BooleanField(),
      location: new StringField({ initial: "" }), container_id: new StringField({ initial: "" }) };
  }
}
export class ClassData extends BreathItemData {
  static defineSchema() {
    return { ...super.defineSchema(), allowed_races: new ArrayField(new StringField()),
      allowed_genders: new ArrayField(new StringField()) };
  }
}
export class RaceData extends BreathItemData {}
export class GenderData extends BreathItemData {
  static defineSchema() {
    return { ...super.defineSchema(), race: new StringField(), gender: new StringField() };
  }
}
export class TalentData extends BreathItemData {
  static defineSchema() { return { ...super.defineSchema(), group: new StringField(), cp: int(0) }; }
}
export class FlawData extends BreathItemData {
  static defineSchema() { return { ...super.defineSchema(), cp: int(0) }; }
}
export class AdvantageData extends BreathItemData {
  static defineSchema() { return { ...super.defineSchema(), cp: int(0), talent_ref: new StringField() }; }
}
export class SkillData extends BreathItemData {
  static defineSchema() { return { ...super.defineSchema(), rank: int(0, { min: 0 }) }; }
}


export class GearData extends BreathItemData {
  static defineSchema() {
    return { ...super.defineSchema(),
      weight: new NumberField({ initial: 0 }),
      volume: new NumberField({ required: false, nullable: true, initial: null }),
      is_container: new BooleanField({ initial: false }),
      capacity_kg: new NumberField({ initial: 0 }),
      capacity_volume: new NumberField({ required: false, nullable: true, initial: null }),
      slot: new StringField({ initial: "" }),
      equipped: new BooleanField(),
      location: new StringField({ initial: "" }), container_id: new StringField({ initial: "" }) };
  }
}
export const ACTOR_MODELS = { character: CharacterData, npc: NpcData, creature: CreatureData };
export const ITEM_MODELS = { weapon: WeaponData, armor: ArmorData, class: ClassData, race: RaceData,
  gender: GenderData, talent: TalentData, flaw: FlawData, advantage: AdvantageData, skill: SkillData, gear: GearData };
