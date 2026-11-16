// Auto-copied from rules/inventory.json. Tests require them to match.
export default {
  "meta": {
    "version": "0.3.0",
    "status": "Carry capacity, race multipliers and light/medium/heavy bands are ported from approved rules. Overloaded actions, backpack sizes and some slot assumptions are PLACEHOLDERS (listed below).",
    "code": "scripts/inventory.py",
    "foundry": "foundry/system/breath-and-the-veil/module/inventory.mjs",
    "doc": "foundry/system/docs/INVENTORY.md",
    "sources": {
      "carry_capacity": "rules/combat_rules.json carry_capacity and scripts/strength.py carry_capacity",
      "male_multiplier": "rules/combat_rules.json carry_capacity.male_multiplier (1.15). This is not the compound Power factor of 1.6, which is only for clinch, grapple, shove, drag and march contests (docs/STRENGTH.md section 2).",
      "power_curve": "docs/STRENGTH.md / scripts/strength.py \u2014 used for contests, not for carry capacity in kilograms",
      "dwarf_multiplier": "rules/lore/dwarves.json mechanics.base_modifiers.carry_capacity_multiplier (1.5); also rules/traits/age_bands_dwarf_v0_5.json",
      "ogre_multiplier": "rules/races.json ability Logistics Beast, applied as race_mult=3 in docs/STRENGTH.md and scripts/strength.py",
      "ox_back": "rules/talents/physical.json ox_back.effects.carry_mult (1.15)",
      "load_bands": "rules/combat_rules.json load_bands",
      "action_economy_encumbrance": "rules/combat/action_economy_v0_1.json encumbrance (AP and speed; different thresholds than load_bands \u2014 see conflict note)",
      "march_cliff": "scripts/strength.py march_cost_per_km: steep extra cost past half capacity",
      "clinch": "docs/STRENGTH.md section 4: being clinched means carrying them. Stamina uses Power ratio; inventory adds the opponent's mass in kg when set.",
      "item_weights": "rules/weapons.json weight and rules/armors.json weight"
    }
  },
  "carry_capacity": {
    "formula": "base_kg = 20 + strength * 1.5",
    "base": 20,
    "per_strength": 1.5,
    "male_multiplier": 1.15,
    "female_multiplier": 1.0,
    "race_multipliers": {
      "Human": 1.0,
      "Elf": 1.0,
      "Dwarf": 1.5,
      "Ogre": 3.0
    },
    "talent_multipliers": {
      "ox_back": 1.15
    }
  },
  "load_bands": [
    {
      "name": "light",
      "max_ratio": 0.2,
      "source": "rules/combat_rules.json load_bands",
      "female_stamina_regen_pct": 20,
      "male_stamina_regen_pct": 0
    },
    {
      "name": "medium",
      "max_ratio": 0.5,
      "source": "rules/combat_rules.json load_bands",
      "female_stamina_drain_pct": 0,
      "male_stamina_drain_pct": 0
    },
    {
      "name": "heavy",
      "max_ratio": 1.0,
      "source": "rules/combat_rules.json load_bands",
      "female_stamina_drain_pct": 30,
      "female_dex_aim_penalty": -10,
      "male_stamina_drain_pct": 15,
      "male_agility_penalty": -5
    },
    {
      "name": "overloaded",
      "max_ratio": null,
      "min_ratio": 1.0,
      "placeholder": true,
      "notes": "Not in combat_rules.json. Added for Foundry 0.3 so going over capacity has a named tier. Walking is still allowed. Sprint and acrobatics are blocked. Climbing is much harder. Unaided rope climb is blocked (user example: a 70-80 kg man carrying 60-70 kg extra should not climb a rope without help \u2014 see design questions, because the current capacity formula gives an average STR 35 man about 83 kg, so 70 kg is still under the cap)."
    }
  ],
  "action_economy_encumbrance": {
    "source": "rules/combat/action_economy_v0_1.json",
    "conflict": "These thresholds do not match combat_rules.json load_bands (0.2 / 0.5 / 1.0). Inventory uses load_bands for the named tier the player sees, and applies these AP and speed penalties separately from the load ratio.",
    "bands": [
      {
        "name": "light",
        "max_ratio": 0.5,
        "ap_penalty": 0,
        "speed_penalty_pct": 0
      },
      {
        "name": "medium",
        "max_ratio": 0.8,
        "ap_penalty": 1,
        "speed_penalty_pct": 10
      },
      {
        "name": "heavy",
        "max_ratio": 1.0,
        "ap_penalty": 2,
        "speed_penalty_pct": 25
      },
      {
        "name": "overloaded",
        "max_ratio": null,
        "ap_penalty": 3,
        "speed_penalty_pct": 40,
        "placeholder": true,
        "notes": "action_economy has no overloaded band. PLACEHOLDER: -3 AP and -40% speed, still able to walk."
      }
    ]
  },
  "action_restrictions": {
    "placeholder": true,
    "source": "Not in existing rules. Requested for Foundry 0.3. Numbers marked placeholder.",
    "by_tier": {
      "light": {
        "blocked": [],
        "penalties": {}
      },
      "medium": {
        "blocked": [],
        "penalties": {}
      },
      "heavy": {
        "blocked": [],
        "penalties": {
          "climb": {
            "athletics_penalty": -20,
            "placeholder": true,
            "notes": "Climbing is harder when heavily loaded."
          }
        }
      },
      "overloaded": {
        "blocked": [
          "sprint",
          "acrobatics",
          "rope_climb_unaided"
        ],
        "penalties": {
          "climb": {
            "athletics_penalty": -40,
            "placeholder": true,
            "notes": "Climbing is much harder when over the limit. Unaided rope climb is impossible."
          }
        }
      }
    }
  },
  "equip_slots": {
    "armor_zones": [
      "head",
      "throat",
      "chest",
      "stomach",
      "groin",
      "left_upper_arm",
      "right_upper_arm",
      "left_lower_arm",
      "right_lower_arm",
      "left_upper_leg",
      "right_upper_leg",
      "left_lower_leg",
      "right_lower_leg"
    ],
    "hands": [
      "main_hand",
      "off_hand"
    ],
    "worn": [
      "back",
      "belt"
    ],
    "notes": "Armour occupies every zone in its coverage list (rules/armors.json). Two pieces may be worn together only if their coverage does not overlap. A two-handed weapon occupies both hands. Loose pieces (helm, gorget, gauntlets, greaves) are still an open PR and will slot into these same zones."
  },
  "two_handed": {
    "type_prefixes": [
      "2H_"
    ],
    "assumed_types": [
      "polearm",
      "staff"
    ],
    "assumed_source_ids": [
      "longbow",
      "recurve_bow",
      "crossbow",
      "arbalest"
    ],
    "placeholder": [
      "assumed_types",
      "assumed_source_ids"
    ],
    "notes": "Types that start with 2H_ are two-handed in the data. Polearms, staves and the listed bows/crossbows are assumed two-handed until confirmed. Longsword uses the actor's current grip (one_hand or two_hands). Sling stays one-handed even though its type is ranged."
  },
  "physical_item_types": [
    "weapon",
    "armor",
    "gear"
  ],
  "non_physical_item_types": [
    "class",
    "race",
    "gender",
    "talent",
    "flaw",
    "advantage",
    "skill"
  ],
  "backpacks": {
    "placeholder": true,
    "notes": "No backpack, satchel or pack with a capacity in kg exists in the rules. These four containers are PLACEHOLDERS for playtesting. Volume is not enforced (no item has a volume number).",
    "items": [
      {
        "id": "belt_pouch",
        "name": "Belt Pouch",
        "slot": "belt",
        "weight": 0.2,
        "capacity_kg": 2,
        "capacity_volume": null,
        "description": "A small pouch on the belt. PLACEHOLDER capacity."
      },
      {
        "id": "satchel",
        "name": "Satchel",
        "slot": "back",
        "weight": 0.8,
        "capacity_kg": 8,
        "capacity_volume": null,
        "description": "A shoulder satchel. PLACEHOLDER capacity."
      },
      {
        "id": "travellers_backpack",
        "name": "Traveller's Backpack",
        "slot": "back",
        "weight": 1.5,
        "capacity_kg": 20,
        "capacity_volume": null,
        "description": "A standard travelling pack. PLACEHOLDER capacity."
      },
      {
        "id": "large_pack",
        "name": "Large Pack",
        "slot": "back",
        "weight": 2.5,
        "capacity_kg": 30,
        "capacity_volume": null,
        "description": "A large pack for long marches. PLACEHOLDER capacity."
      }
    ]
  },
  "missing_weights": {
    "placeholder": true,
    "notes": "These weapons have no weight in rules/weapons.json. Inventory treats a missing weight as 0 and flags the item, rather than inventing a number in the rules file.",
    "weapons": [
      "warhammer",
      "longsword",
      "shortsword"
    ]
  },
  "gaps": [
    "No official backpack or container list (placeholder packs above).",
    "No item volumes, so volume checks are not enforced.",
    "No shield catalogue with weights; shields cannot be dragged as items yet.",
    "warhammer, longsword and shortsword have no weight in rules/weapons.json.",
    "Ogre Brute heavy_lift (500 kg extra, 5 stamina, active ability) is not applied automatically; it is an activated class ability, not a permanent bonus.",
    "Coin weight from rules/system/currency_v0_6d.json (50 coins per kg, pouch relief) is not wired into Foundry yet.",
    "Action restrictions for sprint, acrobatics, climb and unaided rope climb are placeholders.",
    "Overloaded AP and speed penalties are placeholders (action_economy has no band past 1.0)."
  ]
};
