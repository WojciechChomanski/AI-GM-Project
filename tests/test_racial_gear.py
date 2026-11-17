import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import racial_gear as G  # noqa: E402
import inventory as I  # noqa: E402
import skills  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_humans_have_no_forbidden_weapons():
    races = json.load(open(os.path.join(ROOT, "rules/races.json"), encoding="utf-8-sig"))
    assert races["Human"]["equipment"]["forbidden_weapons"] == []
    assert G.forbidden_groups("Human") == []
    for key in ("claymore", "wheellock_pistol", "mace", "longbow", "crossbow"):
        assert G.can_equip("Human", key) is True


def test_mapper_maps_loose_words_to_real_types_and_keys():
    # swords, including sabres; shortsword is its own group
    assert G.in_group("hungarian_hussar_sabre", "sword")
    assert G.in_group("claymore", "sword")
    assert G.in_group("arming_sword", "sword")
    assert not G.in_group("shortsword", "sword")
    assert G.in_group("shortsword", "shortsword")
    assert G.in_group("gladius", "shortsword")
    # daggers and spears (not every polearm)
    assert G.in_group("rondel_dagger", "dagger")
    assert G.in_group("spear", "spear") and G.in_group("lance", "spear") and G.in_group("boar_spear", "spear")
    assert not G.in_group("poleaxe", "spear") and not G.in_group("halberd", "spear")
    # bows vs crossbows
    assert G.in_group("longbow", "bow") and G.in_group("composite_bow", "bow")
    assert not G.in_group("crossbow", "bow") and not G.in_group("arbalest", "bow")
    assert G.in_group("crossbow", "crossbow") and G.in_group("arbalest", "crossbow")
    assert G.in_group("light_crossbow", "crossbow")
    assert not G.in_group("sling", "bow")
    # hammers, axes, guns
    assert G.in_group("warhammer", "hammer") and G.in_group("ogre_forge_hammer", "hammer")
    assert G.in_group("battle_axe", "axe") and G.in_group("throwing_axe", "axe") and G.in_group("francisca", "axe")
    assert G.in_group("matchlock_musket", "gunpowder")
    assert G.in_group("rifled_gun", "gunpowder")
    assert G.in_group("hand_cannon", "gunpowder")
    assert G.in_group("flintlock_musket", "gunpowder")
    # aliases
    assert G.resolve_alias("sword_1h") == "arming_sword"
    assert G.resolve_alias("sword_2h") == "greatsword"
    assert G.resolve_alias("staff") == "quarterstaff"


def test_elf_hard_blocks_include_extra_bans_and_shields():
    msg = "Elves will not hide behind a shield."
    assert G.refuse_reason("Elf", {"type": "shield", "item_kind": "shield", "name": "Pavise"}) == msg
    assert G.refuse_reason("Elf", {"type": "gear", "item_kind": "shield", "source_id": "buckler"}) == msg
    assert G.refuse_reason("Elf", "crossbow")
    assert G.refuse_reason("Elf", "arbalest")
    assert G.refuse_reason("Elf", "matchlock_musket")
    assert G.refuse_reason("Elf", "warhammer")
    assert G.refuse_reason("Elf", "battle_axe")
    # still allowed: bows, swords, knives
    assert G.can_equip("Elf", "composite_bow")
    assert G.can_equip("Elf", "arming_sword")
    assert G.can_equip("Elf", "dagger")


def test_dwarf_hard_blocks_blades_and_bows_not_guns():
    assert G.refuse_reason("Dwarf", "hungarian_hussar_sabre") == "Dwarves will not bear a blade the elves use."
    assert G.refuse_reason("Dwarf", "shortsword")
    assert G.refuse_reason("Dwarf", "dagger")
    assert G.refuse_reason("Dwarf", "spear")
    assert G.refuse_reason("Dwarf", "longbow") == "Dwarves will not draw a bow the elves favor."
    assert G.can_equip("Dwarf", "crossbow")
    assert G.can_equip("Dwarf", "rifled_gun")
    assert G.can_equip("Dwarf", "warhammer")
    assert G.can_equip("Dwarf", "battle_axe")


def test_inventory_refuses_a_forbidden_drop_entirely():
    sword = {"type": "weapon", "name": "Sabre", "source_id": "hungarian_hussar_sabre",
             "system": {"source_id": "hungarian_hussar_sabre", "weapon_type": "1H_sword", "weight": 2}}
    result = I.place_item([], sword, race="Dwarf")
    assert result["ok"] is False
    assert result["message"] == "Dwarves will not bear a blade the elves use."
    shield = {"type": "gear", "name": "Heater", "item_kind": "shield", "system": {"item_kind": "shield", "weight": 3}}
    result = I.place_item([], shield, race="Elf")
    assert result["ok"] is False and "shield" in result["message"].lower()
    # A human may take both
    assert I.place_item([], sword, race="Human")["ok"] is True


def test_dwarves_can_never_ride():
    assert G.can_ride("Dwarf") is False
    assert G.ride_error("Dwarf") == "Dwarves will not ride, as the elves do."
    assert "Dwarves will not ride" in skills.lock_error("riding", "Dwarf", "Male")
    assert G.can_ride("Human") and G.can_ride("Elf")
    # Ogres cannot ride either, but that is mass, not spite
    assert G.can_ride("Ogre") is False


def test_ogres_have_no_bans_medium_is_improvised():
    assert G.forbidden_groups("Ogre") == []
    ogre = {"race": "Ogre", "mass": 600, "strength": 65}
    assert G.can_equip("Ogre", "hungarian_hussar_sabre", ogre)
    assert G.can_equip("Ogre", "crossbow", ogre)
    assert G.can_equip("Ogre", "ogre_claymore", ogre)
    mods = G.improvised_modifiers(ogre, "arming_sword")
    assert mods["active"] is True
    assert mods["skill_penalty"] == -20
    assert mods["durability_loss_mult"] == 3
    assert mods["no_stances"] and mods["no_maneuvers"] and mods["no_mastery"]
    dagger = G.improvised_modifiers(ogre, "dagger")
    assert dagger["skill_penalty"] == -50
    # native large gear is not improvised
    assert G.improvised_modifiers(ogre, "ogre_mace")["active"] is False
    # a human cannot wield large ogre gear
    human = {"race": "Human", "mass": 80, "strength": 50}
    ok, reason = G.can_wield(human, "ogre_branch")
    assert ok is False and "ogre" in reason.lower()
    # existing min_STR still blocks a weak wielder of a heavy medium weapon
    weak = {"race": "Human", "mass": 80, "strength": 10}
    flail = G.load_weapon("flail")
    ok, reason = G.can_wield(weak, flail)
    assert ok is False


def test_ogre_native_weapons_and_rare_claymore():
    for key, dmg, weight, dura, min_str in [
        ("ogre_branch", 16, 25, 40, 55),
        ("ogre_rock_maul", 20, 45, 30, 60),
        ("ogre_iron_shod_club", 18, 35, 70, 58),
        ("ogre_mace", 22, 50, 90, 62),
        ("ogre_anchor_flail", 20, 40, 60, 60),
        ("ogre_forge_hammer", 24, 60, 90, 65),
    ]:
        w = G.load_weapon(key)
        assert w["size_class"] == "large"
        assert w["base_damage"] == dmg and w["weight"] == weight
        assert w["durability"] == dura and w["min_STR"] == min_str
    clay = G.load_weapon("ogre_claymore")
    assert clay["size_class"] == "large"
    assert clay["base_damage"] == 30 and clay["weight"] == 55
    assert clay["durability"] == 120 and clay["min_STR"] == 68
    assert clay["quality"] == "legendary" and clay["gold_cost_multiplier"] == 10
    assert clay["requires"] == "master_smith"
    assert "machine-mark" in clay["notes"].lower() or "machine-mark" in clay["notes"]


def test_axe_edge_decays_to_a_club_without_a_smith():
    state = {"edge": 5, "is_axe": True}
    for _ in range(5):
        state = G.after_fight_without_smith(state, "battle_axe")
    assert state["edge"] == 0
    assert G.counts_as_club(state)
    assert state["type"] == "improvised" and state["damage_type"] == "blunt"


def test_medium_armour_covers_half_ogre_zones():
    armor = {
        "size_class": "medium",
        "coverage": ["chest", "left_upper_arm", "right_upper_arm", "stomach"],
    }
    ogre = {"race": "Ogre", "mass": 600}
    kept = G.filter_armor_coverage(ogre, armor)
    assert len(kept) == 2
    assert "chest" in kept and "stomach" in kept
    scrap = G.filter_armor_coverage(ogre, {
        "size_class": "large",
        "coverage": ["chest", "stomach", "groin", "left_upper_arm"],
    })
    assert len(scrap) == 4


def test_k1_rogue_kits_respect_bans():
    rogue = json.load(open(os.path.join(ROOT, "rules/classes/rogue.json"), encoding="utf-8-sig"))
    by = rogue["Rogue"]["proficiencies"]["weapons_by_race"]
    for w in by["Elf"]:
        assert G.can_equip("Elf", w)
    for w in by["Dwarf"]:
        assert G.can_equip("Dwarf", w)
    assert "light_crossbow" not in by["Elf"]
    assert "dagger" not in by["Dwarf"] and "shortsword" not in by["Dwarf"]


def test_k3_missing_ids_exist_or_alias():
    for key in ("flintlock", "composite_bow", "throwing_knife", "light_crossbow",
                "sword_1h", "sword_2h", "staff", "wand"):
        assert G.load_weapon(key), key


def test_k6_armor_preference_matches_variant_keys():
    races = json.load(open(os.path.join(ROOT, "rules/races.json"), encoding="utf-8-sig"))
    assert races["Elf"]["equipment"]["armor_preference"] == "elven"
    assert races["Dwarf"]["equipment"]["armor_preference"] == "dwarven"
    armors = json.load(open(os.path.join(ROOT, "rules/armors.json"), encoding="utf-8-sig"))
    assert "elven" in armors["Light_Heavy"] and "dwarven" in armors["Medium_Heavy"]


def test_k7_ogre_templates_are_not_in_human_chainmail():
    brute = json.load(open(os.path.join(ROOT, "rules/classes/ogre_brute.json"), encoding="utf-8-sig"))
    armor = json.dumps(brute)
    assert "Light_Heavy" not in armor
    assert "Ogre_Scrap" in armor
    rock = json.load(open(os.path.join(ROOT, "rules/characters/Rock.json"), encoding="utf-8-sig"))
    assert rock["armor"] == ["Ogre_Scrap"]
    gorthak = json.load(open(os.path.join(ROOT, "rules/characters/gorthak.json"), encoding="utf-8-sig"))
    assert gorthak["armor"] == ["Ogre_Scrap"]


def test_gunpowder_weapons_have_reload_and_misfire_placeholders():
    for key in ("matchlock_musket", "arquebus", "wheellock_pistol", "rifled_gun", "hand_cannon"):
        w = G.load_weapon(key)
        assert w["type"] == "gunpowder"
        assert w.get("reload_rounds", 0) >= 2
        assert w.get("misfire_chance", 0) > 0
        assert "PLACEHOLDER" in (w.get("notes") or w.get("status") or "")
    assert G.load_weapon("hand_cannon")["size_class"] == "large"
    arb = G.load_weapon("repeater_arbalest")
    assert arb["type"] == "ranged" and G.in_group(arb, "crossbow")
    assert "PLACEHOLDER" in arb["notes"]


def test_no_improvised_only_and_every_weapon_has_size_class():
    races = json.load(open(os.path.join(ROOT, "rules/races.json"), encoding="utf-8-sig"))
    assert not races["Ogre"]["equipment"].get("restrictions", {}).get("improvised_only")
    weapons = json.load(open(os.path.join(ROOT, "rules/weapons.json"), encoding="utf-8-sig"))
    missing = [k for k, v in weapons.items() if isinstance(v, dict) and v.get("size_class") not in ("medium", "large")]
    assert missing == []


def test_foundry_rules_copy_matches_python():
    src = json.load(open(os.path.join(ROOT, "rules/racial_gear.json"), encoding="utf-8-sig"))
    text = open(os.path.join(ROOT, "foundry/system/breath-and-the-veil/module/racial-gear-rules.mjs"),
                encoding="utf-8").read()
    start = text.index("{")
    end = text.rindex("}") + 1
    copy = json.loads(text[start:end])
    assert copy == src
