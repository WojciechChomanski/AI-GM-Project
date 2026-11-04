"""Builds the Foundry VTT (Custom System Builder 6.0.2) files for Breath combat v1 from the repo rules.

    python foundry/csb/build_csb.py

Outputs (committed; a test fails if they are stale):
  breath-templates.json           actor template "Breath Character (Combat v1)" + item templates
                                  "Breath Weapon" and "Breath Armor" (one CSB "Import templates" file)
  macros/breath-attack.macro.js   attack button: guard, maneuver, target zone, damage type -> POST /combat/attack
  macros/apply-damage.macro.js    zone damage / bleeding (knight v1), accepts a preset from Breath Attack
Base: src/breath-knight-v1-template.json (knight v1 sheet: 13 zones, bleeding, GM body box).
Hidden stats: rules/stat_visibility.json gm_only (faith, virtue, piety, holy fury, corruption) are GM-only (role 4).
Every component dict mirrors the CSB 6.0.2 toJSON() key set (same helpers as knight v1)."""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import foundry_export as FE  # noqa: E402

GM = 4
WEAPON_TPL_ID, ARMOR_TPL_ID, ACTOR_TPL_ID = "BvWeaponTplV1000", "BvArmorTplV10000", "BvCombatTplV1000"
CSB = {"custom-system-builder": {"version": "6.0.2"}}


def base(key, type_, **kw):
    d = {"key": key, "colSpan": 1, "rowSpan": 1, "cssClass": "", "role": 0, "editRole": 0, "permission": 0,
         "tooltip": "", "visibilityFormula": "", "editableFormula": "", "escapeHTML": False, "type": type_}
    d.update(kw)
    return d


def panel(key, contents, title="", flow="vertical", titleStyle="default", css="", colSpan=1, role=0):
    d = base(key, "panel", cssClass=css, colSpan=colSpan, role=role)
    d.update({"contents": contents, "flow": flow, "align": "center", "verticalAlign": "top", "collapsible": False,
              "defaultCollapsed": True, "title": title, "titleStyle": titleStyle})
    return d


def label(value, key="", prefix="", suffix="", style="label", tooltip="", css="", colSpan=1, role=0):
    d = base(key, "label", tooltip=tooltip, cssClass=css, colSpan=colSpan, role=role)
    d.update({"size": "full-size", "value": value, "prefix": prefix, "suffix": suffix, "rollMessage": "",
              "altRollMessage": "", "rollMessageToChat": True, "altRollMessageToChat": True, "style": style})
    return d


def num(key, lbl, default=0, minv="", maxv="", tooltip="", editRole=0, css="", role=0):
    d = base(key, "numberField", tooltip=tooltip, editRole=editRole, cssClass=css, role=role)
    d.update({"size": "full-size", "label": lbl, "defaultValue": str(default), "allowDecimal": False, "minVal": minv,
              "maxVal": maxv, "allowRelative": True, "showControls": False, "controlsStyle": "hover", "inputStyle": "text"})
    return d


def text(key, lbl, default="", tooltip="", editRole=0, css="", role=0, colSpan=1):
    d = base(key, "textField", tooltip=tooltip, editRole=editRole, cssClass=css, role=role, colSpan=colSpan)
    d.update({"size": "full-size", "label": lbl, "defaultValue": default, "charList": "", "maxLength": None, "autocomplete": ""})
    return d


def walk(c):
    yield c
    for x in c.get("contents", []) or []:
        yield from walk(x)


def gm_only_keys():
    vis = json.load(open(os.path.join(ROOT, "rules", "stat_visibility.json"), encoding="utf-8-sig"))
    alias = {"holy_fury_stacks": "holy_fury"}                  # sheet key for the same stat
    return {alias.get(k, k) for k in vis["gm_only"]}


# ---------------------------------------------------------------- actor template
def actor_template():
    src = json.load(open(os.path.join(HERE, "src", "breath-knight-v1-template.json"), encoding="utf-8"))
    tpl = copy.deepcopy(src["actors"][0])
    tpl["name"], tpl["id"] = "Breath Character (Combat v1)", ACTOR_TPL_ID
    body = tpl["data"]["body"]["contents"]
    hidden = gm_only_keys()
    for p in body:
        if p["key"] == "faith_panel":                         # Faith / Virtue / Piety / Holy Fury: GM only
            p["role"], p["title"] = GM, "GM only: Faith"
            p["contents"].append(num("corruption_level", "Corruption", 0, "0", "100", role=GM, editRole=GM,
                                     tooltip="GM only. Shown to the player only very late (rules/stat_visibility.json)."))
            for c in p["contents"]:
                c["role"], c["editRole"] = GM, GM
    found = {c["key"] for p in body for c in walk(p) if c.get("role") == GM}
    assert hidden <= found, hidden - found
    combat = panel("combat_panel", [
        text("weapon_in_hand", "Weapon in hand (weapon_id)", "", tooltip="weapon_id of a Breath Weapon item on this actor; empty = first weapon item"),
        text("grip", "Grip", "two_hands", tooltip="two_hands or one_hand (longsword: all 10 greatsword guards in two hands)"),
        num("shield_equipped", "Shield (0/1)", 0, "0", "1"),
        text("current_guard", "Current guard", "", tooltip="Written by Breath Attack; a guard change costs 1 stamina"),
        text("previous_guard", "Previous guard", "", editRole=GM),
        num("disarmed", "Disarmed (0/1)", 0, "0", "1", editRole=GM),
        text("conditions_json", "Conditions (engine)", "[]", editRole=GM, colSpan=3,
             tooltip="Stored between attacks: limb disabled, unbalanced, lose next maneuver... (engine output)"),
    ], title="Combat", flow="grid-3", titleStyle="title", css="bv-combat")
    gm_combat = panel("gm_combat_panel", [
        text("race", "Race", "Human", editRole=GM), text("gender", "Gender", "Male", editRole=GM),
        text("class_name", "Class (engine key)", "Crusader_Knight", editRole=GM),
        text("fight_state_json", "Fight state (engine)", "{}", editRole=GM, colSpan=3,
             tooltip="trick used, free guard changes used. Clear to {} at the start of a new fight."),
        text("mastery_json", "Mastery uses and perk picks", "{}", editRole=GM, colSpan=3,
             tooltip="character.progression dict (mastery uses per family, perk picks) - from the GM console / backend"),
    ], title="GM: combat setup", flow="grid-3", titleStyle="title", css="bv-gm", role=GM)
    body.insert(1, combat)
    body.insert(2, gm_combat)
    tpl["data"]["display"].update({"width": 780, "height": 950})
    return tpl


# ---------------------------------------------------------------- item templates
def item_template(name, tid, sample_props, numeric, long_text=()):
    fields = []
    for k, v in sample_props.items():
        if k in numeric:
            fields.append(num(k, k, 0, editRole=GM))
        else:
            fields.append(text(k, k, "", editRole=GM, colSpan=3 if k in long_text else 1))
    return {"id": tid, "type": "_equippableItemTemplate", "name": name,
            "data": {"header": {"contents": [label("${name}$", style="title")], "key": "custom_header", "type": "panel"},
                     "body": {"contents": [panel("props_panel", fields, title=name, flow="grid-3", titleStyle="title")],
                              "key": "custom_body", "type": "panel"},
                     "display": {"width": 640, "height": 600, "fix_size": False, "pp_width": 64, "pp_height": 64},
                     "hidden": []},
            "flags": copy.deepcopy(CSB)}


def build():
    w = FE.weapon_item("longsword")["system"]["props"]
    a = FE.armor_item("Heavy_Medium", "standard", json.load(open(os.path.join(ROOT, "rules", "armors.json"),
                                                                 encoding="utf-8-sig"))["Heavy_Medium"]["standard"])["system"]["props"]
    num_w = {k for k, v in w.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    num_a = {k for k, v in a.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    out = {"isCustomSystemExport": True, "actors": [actor_template()],
           "items": [item_template("Breath Weapon", WEAPON_TPL_ID, w, num_w,
                                   ("guards_json", "maneuvers_json", "guards_two_hand_json", "maneuvers_two_hand_json", "maneuvers", "guards")),
                     item_template("Breath Armor", ARMOR_TPL_ID, a, num_a, ("coverage",))]}
    with open(os.path.join(HERE, "breath-templates.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent="\t", ensure_ascii=False)
        f.write("\n")
    # ---- macros
    os.makedirs(os.path.join(HERE, "macros"), exist_ok=True)
    attack = ("// Breath and the Veil - Breath Attack macro (Foundry v14 + CSB 6.0.2). Macro type: Script. Name it \"Breath Attack\".\n"
              "// Generated by foundry/csb/build_csb.py. Needs the local combat bridge: foundry/csb/COMBAT_BRIDGE.md\n"
              "// EDIT THESE to match your .env (API_USERNAME / API_PASSWORD) and BREATH_PORT:\n"
              "const BREATH_BRIDGE = { url: 'http://127.0.0.1:8000/combat/attack', user: 'admin', password: 'secret' };\n"
              + open(os.path.join(HERE, "src", "attack_body.js"), encoding="utf-8").read())
    open(os.path.join(HERE, "macros", "breath-attack.macro.js"), "w", encoding="utf-8").write(attack)
    arm = json.load(open(os.path.join(ROOT, "rules", "armors.json"), encoding="utf-8-sig"))
    cat = {}
    for key, block in arm.items():
        s = block.get("standard") if isinstance(block, dict) else None
        if isinstance(s, dict) and "coverage" in s:
            cat[key] = {"name": s["name"], "coverage": s["coverage"], "armor_rating": s["armor_rating"]}
            if "dwarven" in block:
                cat[key + ":dwarven"] = {k: block["dwarven"][k] for k in ("name", "coverage", "armor_rating")}
    rules = open(os.path.join(HERE, "src", "breath-rules.js"), encoding="utf-8").read().replace(
        "if (typeof module !== 'undefined') module.exports = BreathRules;\n", "")
    apply = ("// Breath and the Veil - Apply Damage macro (Foundry v14 + CSB 6.0.2). Macro type: Script. Name it \"Apply Damage\".\n"
             "// Generated by foundry/csb/build_csb.py. ARMOR_CATALOG = rules/armors.json (standard; ':dwarven' = Forged).\n"
             + rules + "const ARMOR_CATALOG = " + json.dumps(cat) + ";\n"
             + open(os.path.join(HERE, "src", "apply_damage_body.js"), encoding="utf-8").read())
    open(os.path.join(HERE, "macros", "apply-damage.macro.js"), "w", encoding="utf-8").write(apply)
    return out


if __name__ == "__main__":
    o = build()
    print("templates:", [t["name"] for t in o["actors"] + o["items"]])
