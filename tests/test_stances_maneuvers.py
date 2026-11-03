"""Stances, maneuvers, damage types, armour defeat and weapon perks (owner t98u).
Docs: docs/COMBAT_STANCES_MANEUVERS.md"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import combat_techniques as CT
import combat_engine as CE
import progression as P
import stance_logic
from maneuver_handler import ManeuverHandler

ROOT = os.path.join(os.path.dirname(__file__), "..")
ARMORS = json.load(open(os.path.join(ROOT, "rules", "armors.json")))
PERKS = json.load(open(os.path.join(ROOT, "rules", "weapon_perks.json")))
IMPACT_TYPES = {"2H_hammer", "1H_blunt", "1H_axe", "2H_axe", "polearm", "staff"}


class R:
    """Fixed dice: randint pops values (default 50); defence is always a Parry unless told."""
    def __init__(self, *v, defence="Parry"):
        self.v, self.d = list(v), defence

    def randint(self, a, b):
        return self.v.pop(0) if self.v else 50

    def choice(self, seq):
        return self.d


def fighter(weapon="dagger", armor=(), **kw):
    d = dict(name="F", race="Human", total_hp=100, max_stamina=100, armor_weight=0, inventory_weight=0,
             shield_equipped=False, weapon_equipped=True, weapon=weapon, armor=list(armor), weapon_skill=40)
    d.update(kw)
    return d


def hit(att, dfn, *rolls, **kw):
    return CE.engine.attack_roll(att, dfn, rng=R(*(rolls or (99, 1)), **kw))


# ---------- data integrity ----------
def test_every_maneuver_points_at_a_real_guard_and_has_no_crit():
    for gs, mans in CT.MANEUVERS.items():
        guards = CT.GUARD_SETS[gs]["stances"]
        for m in mans:
            assert all(s in guards for s in CT.as_list(m["stance_required"])), (gs, m["name"])
            assert all(t in CT._WM["_meta"]["triggers"] for t in CT.as_list(m["trigger"])), m["name"]
            assert not [k for k in m["effects"] if "crit" in k], m["name"]
    for fam, ladder in PERKS["ladders"].items():
        assert "crit" not in json.dumps(ladder).replace("crits", ""), fam


def test_weapon_guard_trees_and_no_sword_guards_on_impact_weapons():
    for k, w in CT.WEAPONS.items():
        gs = w.get("guard_set")
        assert set(w["stance_tree"]) <= set(CT.GUARD_SETS[gs]["stances"] if gs else []), k
        if w["type"] in IMPACT_TYPES or k == "lucerno_hammer":
            assert not {"half_sword", "vom_tag", "wrath_guard"} & set(w["stance_tree"]), k
        if w["type"] == "2H_sword":
            assert len(w["stance_tree"]) == 10, k                  # greatswords reach all 10 guards
    for g in ("crater_maker", "counterweight", "impact_form"):  # the war hammer's guards now exist
        assert g in CT.GUARD_SETS["2H_hammer"]["stances"]
    # impact families have fewer guards than swords
    assert max(len(CT.GUARD_SETS[s]["stances"]) for s in ("2H_hammer", "1H_blunt", "axe", "polearm")) < 6


def test_every_2h_guard_has_a_maneuver():
    used = {s for m in CT.MANEUVERS["2H_sword"] for s in CT.as_list(m["stance_required"])}
    assert used == set(CT.GUARD_SETS["2H_sword"]["stances"])


def test_damage_types_and_armor_defeat_only_on_impact():
    for k, w in CT.WEAPONS.items():
        assert w["damage_types"] and set(w["damage_types"]) <= set(CT.DAMAGE_TYPE_NAMES), k
        assert w["damage_type"] == w["damage_types"][0]
        assert 0 <= w["armor_defeat"] <= CT.ARMOR_DEFEAT_MAX
        fam = P.weapon_family(w)
        if w["armor_defeat"]:
            assert fam in CT.DAMAGE_TYPES["armor_defeat"]["only_families"], k
        if w["type"] in ("2H_sword", "1H_sword", "sword", "shortsword", "dagger"):
            assert w["armor_defeat"] == 0 and not w["percussive"], k
    assert CT.WEAPONS["greatsword"]["damage_types"] == ["slashing", "piercing"]
    assert CT.WEAPONS["warhammer"]["damage_types"] == ["blunt", "piercing"]


def test_new_armour_table_values():
    def r(t):
        return tuple(ARMORS[t]["standard"]["armor_rating"][x] for x in ("slashing", "piercing", "blunt"))
    assert r("Heavy_Medium") == (14, 10, 7)       # Full Plate: was 10/9/8
    assert r("Light_Heavy") == (7, 4, 2)          # Light Chainmail: was 5/4/3
    assert r("Light_Light") == (3, 2, 1)          # Padded Cloth: was 2/1/1
    for t, vs in ARMORS.items():
        for v, s in vs.items():
            a = s["armor_rating"]
            assert a["slashing"] >= a["piercing"] >= a["blunt"], (t, v)   # cuts stopped best, impact worst
            assert s["rigid"] == ("Plate" in s["name"] or "Breastplate" in s["name"])


# ---------- one source of truth for stances ----------
def test_stances_single_source():
    assert CT.stance_modifiers("offensive") == (3, -3) and CT.stance_modifiers("defensive") == (-3, 5)
    for f in ("adventure_new.py", "adventure.py"):                 # were +-10 hard-coded
        src = open(os.path.join(ROOT, "scripts", f), encoding="utf-8").read()
        body = src[src.index("def stance_mods"):src.index("def stance_mods") + 400]
        assert "stance_modifiers" in body and "+= 10" not in body
    assert stance_logic.apply_stance_modifiers(None, None, "defensive", "defense") == 5
    assert CT.stance_modifiers("half_sword", "greatsword") == (-3, 5)
    assert CT.stance_modifiers("posta_di_donna", "greatsword") == (5, -3)
    # a guard the weapon cannot reach falls back to its default guard
    g = CT.guard_info("warhammer", "half_sword")
    assert g["id"] == "impact_form" and not g["valid"]


def test_list_matching_bug_fixed():
    assert [m["name"] for m in CT.valid_maneuvers("arming_sword", "wrath_guard", "after_parry")] == \
        ["Parry and Riposte", "Disarm Attempt"]
    assert "Aimed Head Strike" in [m["name"] for m in CT.valid_maneuvers("arming_sword", "half_sword", "always", "head")]
    assert "Aimed Head Strike" not in [m["name"] for m in CT.valid_maneuvers("arming_sword", "half_sword", "always")]


def test_one_maneuver_not_summed():
    out = ManeuverHandler().get_bonus_effects("1H_sword", "wrath_guard", "after_parry")
    assert out["maneuver"] in ("Parry and Riposte", "Disarm Attempt")
    assert out["attack_bonus"] in (5, -2)                        # one maneuver, never 5 + -2


def test_half_sword_thrust_normal_and_features_gate():
    assert "Half-Sword Thrust" in [m["name"] for m in CT.valid_maneuvers("greatsword", "half_sword", "always")]
    assert "Beak Thrust" in [m["name"] for m in CT.valid_maneuvers("chekan", "middle_guard")]
    assert "Beak Thrust" not in [m["name"] for m in CT.valid_maneuvers("mace", "middle_guard")]
    assert "Spike Thrust" not in [m["name"] for m in CT.valid_maneuvers("quarterstaff", "posta_breve_serpentina")]


# ---------- tool philosophy vs armour (end to end through combat_engine) ----------
def dmg(weapon, stance, armour, maneuver=None, trigger="always"):
    return hit(fighter(weapon, stance=stance, maneuver=maneuver if maneuver else False, trigger=trigger),
               fighter(armor=[armour], name="D"))


def test_tool_philosophy_vs_plate_mail_and_cloth():
    plate = {w: dmg(w, s, "Heavy_Medium")["damage"] for w, s in
             (("greatsword", "wrath_guard"), ("warhammer", "impact_form"), ("dane_axe", "middle_guard"),
              ("mace", "middle_guard"), ("halberd", "posta_breve_serpentina"))}
    # swords are poor vs plate even at full damage; impact weapons clearly better
    assert plate["greatsword"] <= 1
    assert plate["warhammer"] > plate["dane_axe"] > plate["greatsword"]
    assert plate["mace"] > plate["greatsword"] and plate["halberd"] > plate["greatsword"]
    # half-sword thrust and Mordhau are the sword's answers, still below a war hammer
    hs = dmg("greatsword", "half_sword", "Heavy_Medium", "Half-Sword Thrust")
    mh = dmg("greatsword", "vom_tag", "Heavy_Medium", "Mordhau", "after_block")
    assert hs["damage_type"] == "piercing" and mh["damage_type"] == "blunt"
    assert plate["greatsword"] < mh["damage"] < hs["damage"] < plate["warhammer"]
    assert mh["damage"] < plate["mace"]                          # a real mace still beats a mordhau
    # piercing beats cutting vs mail; cutting is best on bare skin
    mail = dmg("greatsword", "wrath_guard", "Light_Heavy")
    assert mail["damage_type"] == "piercing"
    bare = dmg("greatsword", "wrath_guard", "Unarmored")
    assert bare["damage_type"] == "slashing" and bare["damage"] == 12 + 2
    assert bare["damage"] > dmg("warhammer", "impact_form", "Unarmored")["damage"] - 6


def test_requested_damage_type_and_percussive():
    r = hit(fighter("greatsword", stance="wrath_guard", maneuver=False, damage_type="slashing"),
            fighter(armor=["Heavy_Medium"], name="D"))
    assert r["damage_type"] == "slashing" and r["damage"] == 0
    spec = ARMORS["Heavy_Medium"]["standard"]
    assert CT.armor_rating(spec, "slashing", percussive=True) == spec["armor_rating"]["blunt"]
    assert CT.armor_rating(ARMORS["Light_Heavy"]["standard"], "slashing", percussive=True) == 7  # mail not rigid


# ---------- maneuver effects ----------
def test_limb_disable_disarm_unbalance_and_conditions_flow():
    a = fighter("greatsword", stance="vom_tag", maneuver="Krumphau")
    r = hit(a, fighter(name="D"))
    assert r["maneuver"] == "Krumphau" and r["zone"] in CT.ARMS
    assert {"type": "limb_disabled", "zone": r["zone"], "value": 10, "duration": "fight"} in r["defender_conditions"]
    # the disabled arm costs the defender 10 on their own attack later
    d = fighter("dagger", conditions=r["defender_conditions"], maneuver=False)
    base = hit(fighter("dagger", maneuver=False), fighter(name="X"), 50, 50)["atk_total"]
    assert hit(d, fighter(name="X"), 50, 50)["atk_total"] == base - 10
    # Break Thrust: disarm roll (forced) + unbalance next defence
    r = hit(fighter("greatsword", stance="porta_di_ferro", maneuver="Break Thrust", trigger="after_parry"),
            fighter(name="D"), 99, 1, 5)
    assert r["defender_disarmed"] and any(c["type"] == "unbalanced" for c in r["defender_conditions"])
    nxt = hit(fighter("dagger", maneuver=False), fighter(name="D", conditions=r["defender_conditions"]), 50, 50)
    assert nxt["def_total"] == 50 + 3 - 10 and not any(c["type"] == "unbalanced" for c in nxt["defender_conditions"])


def test_lose_next_maneuver_and_strip_shield_and_ignore_shield():
    r = hit(fighter("arming_sword", stance="half_sword", maneuver="Pommel Strike", trigger="after_block"), fighter(name="D"))
    assert r["damage_type"] == "blunt"
    rung = hit(fighter("greatsword", stance="vom_tag", conditions=r["defender_conditions"]), fighter(name="E"))
    assert rung["maneuver"] is None and "no maneuver" in rung["maneuver_note"]
    shield = fighter(name="S", shield_equipped=True)
    blocked = hit(fighter("dagger", maneuver=False), shield, 50, 50, defence="Block")["def_total"]
    flail = hit(fighter("flail", stance="high_guard", maneuver="Around the Shield"), shield, 50, 50, defence="Block")
    assert flail["maneuver"] == "Around the Shield" and flail["def_total"] < blocked
    hook = hit(fighter("dane_axe", stance="low_guard", maneuver="Bearded Hook", trigger="after_block"), fighter(name="S"))
    nxt = hit(fighter("dagger", maneuver=False), dict(shield, conditions=hook["defender_conditions"]), 50, 50, defence="Block")
    assert nxt["def_total"] < blocked


def test_aimed_head_strike_relief_and_cap():
    r = hit(fighter("arming_sword", stance="vom_tag", maneuver="Aimed Head Strike", aimed_zone="head"), fighter(name="D"))
    assert r["maneuver"] == "Aimed Head Strike" and r["aimed_penalty"] == 40 - 5
    # Gap-Finder perk + the maneuver's relief still cap at 5
    c = fighter("arming_sword", stance="vom_tag", maneuver="Aimed Head Strike", aimed_zone="head")
    P.record_mastery(c, "one_hand_sword", 900); P.choose_perk(c, "one_hand_sword", 4, "gap_finder")
    r = hit(c, fighter(armor=["Heavy_Medium"], name="D"))
    assert r["aimed_penalty"] == 35


# ---------- guard change and stamina ----------
def test_guard_change_costs_one_stamina_and_perk_makes_one_free():
    base = hit(fighter("greatsword", stance="vom_tag", maneuver=False), fighter(name="D"))
    moved = hit(fighter("greatsword", stance="vom_tag", previous_stance="wrath_guard", maneuver=False), fighter(name="D"))
    assert moved["guard_change_cost"] == 1 and moved["stamina_spent"] == base["stamina_spent"] + 1
    c = fighter("greatsword", stance="vom_tag", previous_stance="wrath_guard", maneuver=False)
    P.record_mastery(c, "greatsword", 50)
    r = hit(c, fighter(name="D"))
    assert r["guard_change_cost"] == 0 and r["fight_state"]["free_changes_used"] == 1
    c["fight_state"] = r["fight_state"]
    assert hit(c, fighter(name="D"))["guard_change_cost"] == 1      # only one free per round


def test_stamina_floor_and_perk_reduction_cap():
    c = fighter("greatsword", stance="half_sword", maneuver="Half-Sword Thrust")
    before = hit(c, fighter(name="D"))["stamina_spent"]
    P.record_mastery(c, "greatsword", 400)
    assert hit(c, fighter(name="D"))["stamina_spent"] == before - 1          # Practiced Counters
    fx = P.perk_effects(c, "greatsword")
    assert fx["maneuver_stamina"]["Half-Sword Thrust"] >= -2
    d = fighter("dagger", maneuver=False); P.record_mastery(d, "dagger", 2000)
    assert hit(d, fighter(name="D"))["stamina_spent"] >= 2


# ---------- perks, tricks and caps ----------
def test_ladders_have_seven_perks_and_to_hit_rank2():
    for fam in ("greatsword", "one_hand_sword", "warhammer", "mace", "axe", "spear"):
        slots = P._ladder_slots(fam)
        assert len(slots) == 7, fam
        assert sum(1 for _, _, o in slots if len(o) == 2) == 3, fam
        c = fighter(); P.record_mastery(c, fam, 150)
        assert P.mastery_modifiers(c, {"type": {"greatsword": "2H_sword", "one_hand_sword": "1H_sword", "warhammer": "2H_hammer",
                                                "mace": "1H_blunt", "axe": "1H_axe", "spear": "polearm"}[fam]})["to_hit"] == 5


def test_only_weapon_in_hand_counts_and_picks_are_permanent():
    c = fighter(); P.record_mastery(c, "greatsword", 2000)
    assert P.active_perks(c, "warhammer") == []
    assert "fluid_guards" in [p["id"] for p in P.active_perks(c, "claymore")]
    P.choose_perk(c, "greatsword", 2, "wider_use")
    try:
        P.choose_perk(c, "greatsword", 2, "practiced_half_sword"); assert False
    except ValueError:
        pass
    assert "Zwerchhau" in [m["name"] for m in CT.valid_maneuvers("greatsword", "ochs", "always", perks=P.perk_effects(c, "greatsword"))]


def test_armor_defeat_cap_and_crater_once_per_fight():
    c = fighter("warhammer", stance="crater_maker", maneuver=False)
    assert hit(c, fighter(armor=["Heavy_Medium"], name="D"))["armor_defeat"] == 1
    P.record_mastery(c, "warhammer", 2000)
    assert hit(c, fighter(armor=["Heavy_Medium"], name="D"))["armor_defeat"] == 2        # Through the Plate, cap 2
    P.choose_perk(c, "warhammer", 5, "crater")
    c["use_trick"] = True
    r = hit(c, fighter(armor=["Heavy_Medium"], name="D"))
    assert r["trick"] == "crater" and r["armor_defeat"] == 3 and r["fight_state"]["trick_used"]
    c["fight_state"] = r["fight_state"]
    r2 = hit(c, fighter(armor=["Heavy_Medium"], name="D"))
    assert r2["trick"] is None and r2["armor_defeat"] == 2 and r2["notes"]
    # a sword never gets armour defeat, even at Master
    s = fighter("greatsword", stance="vom_tag", maneuver=False); P.record_mastery(s, "greatsword", 2000)
    assert hit(s, fighter(armor=["Heavy_Medium"], name="D"))["armor_defeat"] == 0


def test_seamless_guards_uses_any_guard_maneuver_once():
    c = fighter("greatsword", stance="wrath_guard", previous_stance="vom_tag", maneuver="Break Thrust",
                trigger="after_parry", use_trick=True)
    P.record_mastery(c, "greatsword", 2000); P.choose_perk(c, "greatsword", 5, "seamless_guards")
    r = hit(c, fighter(name="D"))
    assert r["maneuver"] == "Break Thrust" and r["guard_change_cost"] == 0 and r["trick"] == "seamless_guards"


def test_edge_on_flesh_only_vs_light_and_damage_cap():
    c = fighter("greatsword", stance="wrath_guard", maneuver=False)
    base = hit(c, fighter(name="D"))["damage"]
    P.record_mastery(c, "greatsword", 900)
    assert hit(c, fighter(name="D"))["damage"] == base + 1
    plate = hit(c, fighter(armor=["Heavy_Medium"], name="D", ), )
    assert plate["damage"] <= 1
    assert P.CEIL["damage"] == 2


def test_ring_on_head_once_per_foe():
    c = fighter("mace", stance="high_guard", maneuver="Overhead Smash", aimed_zone="head")
    P.record_mastery(c, "mace", 900)
    r = hit(c, fighter(armor=["Heavy_Medium"], name="Knight"))
    assert any(c_["type"] == "lose_next_maneuver" for c_ in r["defender_conditions"]) and r["fight_state"]["rung"] == ["Knight"]
    c["fight_state"] = r["fight_state"]
    r2 = hit(c, fighter(armor=["Heavy_Medium"], name="Knight"))
    assert not any(c_["type"] == "lose_next_maneuver" for c_ in r2["defender_conditions"])


# ---------- Foundry export ----------
def test_foundry_export(tmp_path):
    import foundry_export as FE
    nw, na = FE.export(str(tmp_path))
    assert nw == len(CT.WEAPONS) and na == sum(len(v) for v in ARMORS.values())
    items = json.load(open(tmp_path / "weapons_items.json"))
    gs = next(i for i in items if i["system"]["props"]["weapon_id"] == "greatsword")["system"]["props"]
    for k in ("damage_type", "damage_types", "guards", "default_guard", "guard_change_stamina", "maneuvers_json",
              "armor_defeat", "stamina_cost"):
        assert k in gs
    assert "Half-Sword Thrust" in gs["maneuvers"] and len(gs["guards"].split(",")) == 10
    arm = json.load(open(tmp_path / "armor_items.json"))
    fp = next(i for i in arm if i["system"]["props"]["armor_label"] == "Full Plate")["system"]["props"]
    assert (fp["armor_slashing"], fp["armor_piercing"], fp["armor_blunt"], fp["rigid"]) == (14, 10, 7, 1)
    # the committed export is current
    committed = json.load(open(os.path.join(ROOT, "foundry", "csb", "weapons_items.json")))
    assert committed == items
