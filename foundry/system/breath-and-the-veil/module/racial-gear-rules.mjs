// Copied from rules/racial_gear.json — keep in sync.
export default {
  "meta": {
    "version": "0.1",
    "status": "PLACEHOLDER",
    "note": "Hard racial equipment blocks and ogre size rules. Numbers flagged PLACEHOLDER were taken from the Breath Keeper draft where they survived, or invented to fit the era when the draft was truncated (gunpowder stats, half-zone selection, some costs). Cultural bans are visible rules, not hidden stats. Kinbreaker, stress and reputation taboos are not used.",
    "sources": [
      "lore/core/lore_master.md (Doctrine of Spite)",
      "lore/era_1670.json tech_level",
      "rules/races.json",
      "rules/weapons.json",
      "docs/RACIAL_GEAR.md"
    ]
  },
  "messages": {
    "elf_hammer_or_axe": "Elves will not take up a hammer or axe of the dwarven forges.",
    "elf_crossbow": "Elves will not span a crossbow.",
    "elf_gunpowder": "Elves will not take up a gunpowder weapon.",
    "elf_shield": "Elves will not hide behind a shield.",
    "dwarf_blade": "Dwarves will not bear a blade the elves use.",
    "dwarf_bow": "Dwarves will not draw a bow the elves favor.",
    "dwarf_ride": "Dwarves will not ride, as the elves do.",
    "too_large": "This is sized for an ogre; it cannot be wielded.",
    "too_weak": "You lack the strength to fight with this."
  },
  "races": {
    "Human": {
      "forbidden_groups": [],
      "may_ride": true
    },
    "Elf": {
      "forbidden_groups": [
        "hammer",
        "axe",
        "crossbow",
        "gunpowder",
        "shield"
      ],
      "may_ride": true
    },
    "Dwarf": {
      "forbidden_groups": [
        "sword",
        "shortsword",
        "dagger",
        "spear",
        "bow"
      ],
      "may_ride": false
    },
    "Ogre": {
      "forbidden_groups": [],
      "may_ride": false,
      "ride_reason": "mass"
    }
  },
  "groups": {
    "sword": {
      "types": [
        "1H_sword",
        "2H_sword",
        "sword"
      ],
      "key_substrings": [
        "sabre",
        "saber",
        "szabla",
        "katana"
      ],
      "exclude_types": [
        "shortsword",
        "dagger"
      ],
      "exclude_keys": [
        "shortsword"
      ]
    },
    "shortsword": {
      "types": [
        "shortsword"
      ],
      "keys": [
        "shortsword"
      ]
    },
    "dagger": {
      "types": [
        "dagger"
      ]
    },
    "spear": {
      "keys": [
        "spear",
        "lance",
        "boar_spear"
      ],
      "key_substrings": [
        "_spear"
      ]
    },
    "bow": {
      "key_substrings": [
        "bow"
      ],
      "exclude_keys": [
        "crossbow",
        "arbalest",
        "light_crossbow"
      ],
      "exclude_substrings": [
        "crossbow",
        "arbalest"
      ]
    },
    "crossbow": {
      "keys": [
        "crossbow",
        "arbalest",
        "light_crossbow"
      ],
      "key_substrings": [
        "crossbow",
        "arbalest"
      ]
    },
    "hammer": {
      "types": [
        "2H_hammer"
      ],
      "key_substrings": [
        "hammer"
      ]
    },
    "axe": {
      "types": [
        "1H_axe",
        "2H_axe"
      ],
      "key_substrings": [
        "axe",
        "francisca"
      ]
    },
    "gunpowder": {
      "types": [
        "gunpowder"
      ],
      "key_substrings": [
        "musket",
        "arquebus",
        "pistol",
        "flintlock",
        "rifled_gun",
        "hand_cannon"
      ]
    },
    "shield": {
      "types": [
        "shield"
      ],
      "item_kinds": [
        "shield"
      ]
    }
  },
  "aliases": {
    "sword_1h": "arming_sword",
    "sword_2h": "greatsword",
    "staff": "quarterstaff",
    "flintlock": "flintlock_musket"
  },
  "size": {
    "default": "medium",
    "classes": [
      "medium",
      "large"
    ],
    "large_mass_threshold": 150,
    "note": "Human, elf and dwarf gear defaults to medium. Native ogre gear is large. A large weapon is refused to anyone of mass 150 or less (human max STR 50 is inside the -15 grip grace of some draft min_STR values, so size, not min_STR alone, is what always blocks it)."
  },
  "ogre_improvised": {
    "status": "PLACEHOLDER",
    "skill_penalty": -20,
    "dagger_extra_penalty": -30,
    "durability_loss_mult": 3,
    "no_stances": true,
    "no_maneuvers": true,
    "no_mastery": true,
    "note": "A medium weapon in ogre hands counts as improvised, like a man using a toy sword."
  },
  "axe_edge": {
    "status": "PLACEHOLDER",
    "max": 5,
    "loss_per_fight_without_smith": 1,
    "at_zero": "club",
    "note": "An axe without smith upkeep loses 1 edge per fight. At 0 it is blunt and counts as a club."
  },
  "ogre_armor": {
    "status": "PLACEHOLDER",
    "medium_coverage_fraction": 0.5,
    "round": "down",
    "keep_priority": [
      "chest",
      "stomach",
      "throat",
      "head",
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
    "note": "Medium armour on an ogre covers only half its listed zones (torso kept first). Fraction and zone order are placeholders."
  },
  "gunpowder_placeholders": {
    "status": "PLACEHOLDER",
    "note": "Reload times in rounds and misfire chances were invented for a 1580-1670 pike-and-shot era after the draft mid-section was truncated."
  }
};
