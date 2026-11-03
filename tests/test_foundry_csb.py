"""Foundry CSB combat sheet: build is current, GM-only stats are role 4, the
attack macro's payload is accepted by the engine."""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSB = os.path.join(ROOT, "foundry", "csb")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
OUTS = ["breath-templates.json", "macros/breath-attack.macro.js", "macros/apply-damage.macro.js"]


def _read(p):
    return open(os.path.join(CSB, p), encoding="utf-8").read()


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _templates():
    return json.loads(_read("breath-templates.json"))


def test_build_output_is_current():
    before = {p: _read(p) for p in OUTS}
    subprocess.run([sys.executable, os.path.join(CSB, "build_csb.py")], check=True, cwd=ROOT,
                   stdout=subprocess.DEVNULL)
    for p in OUTS:
        assert _read(p) == before[p], f"{p} is stale - run foundry/csb/build_csb.py"


def _keys_with_role(tpl):
    out = {}
    for n in _walk(tpl):
        key = n.get("key")
        if key:
            out[key] = n.get("visibilityRole") or n.get("role")
    return out


def test_gm_only_stats_are_role_4():
    data = _templates()
    actor = data["actors"][0]
    vis = json.load(open(os.path.join(ROOT, "rules", "stat_visibility.json"), encoding="utf-8-sig"))
    text = json.dumps(actor)
    for key in ("faith", "virtue", "piety", "holy_fury", "corruption_level", "fight_state_json"):
        assert f'"key": "{key}"' in text, key
    # every gm-only key sits inside a panel whose visibility role is 4 (GM)
    def find(node, inherited=None):
        role = node.get("role", inherited) if isinstance(node, dict) else inherited
        if isinstance(node, dict):
            if node.get("key") in ("faith", "virtue", "piety", "holy_fury", "corruption_level"):
                assert str(role) == "4", (node.get("key"), role)
            for v in node.values():
                find(v, role)
        elif isinstance(node, list):
            for v in node:
                find(v, role)
    find(actor)
    assert vis  # visibility file loads; build asserts coverage itself


def test_item_templates_have_contract_keys():
    data = _templates()
    names = {t["name"]: t for t in data["items"]}
    weapon, armor = names["Breath Weapon"], names["Breath Armor"]
    wtext, atext = json.dumps(weapon), json.dumps(armor)
    sample = json.load(open(os.path.join(CSB, "weapons_items.json"), encoding="utf-8"))[0]["system"]["props"]
    for k in ("weapon_id", "armor_piercing", "two_hand_guard_set", "guards_json", "maneuvers_json",
              "guards_two_hand_json", "maneuvers_two_hand_json"):
        assert k in sample, k
        assert f'"key": "{k}"' in wtext, k
    assert "durability" in atext


def test_two_hand_longsword_export_has_ten_guards():
    items = json.load(open(os.path.join(CSB, "weapons_items.json"), encoding="utf-8"))
    ls = next(i for i in items if i["system"]["props"]["weapon_id"] == "longsword")["system"]["props"]
    assert len(json.loads(ls["guards_two_hand_json"])) == 10
    assert json.loads(ls["maneuvers_two_hand_json"])


def test_macro_payload_keys_accepted_by_engine():
    import combat_engine as ce
    src = _read("macros/breath-attack.macro.js")
    assert "/combat/attack" in src and "BREATH_BRIDGE" in src
    for k in ("stance", "previous_stance", "maneuver", "trigger", "aimed_zone", "damage_type", "use_trick", "grip"):
        assert re.search(rf"\b{k}\b", src), k
    def combatant(name, weapon, armor, **extra):  # mirrors combatant() in src/attack_body.js
        d = {"name": name, "race": "Human", "gender": "Male", "class_name": "", "total_hp": 100, "max_stamina": 100,
             "armor_weight": 0, "inventory_weight": 0, "shield_equipped": False, "weapon_equipped": True,
             "weapon": weapon, "armor": armor, "strength": 40, "dexterity": 30, "weapon_skill": 40,
             "progression": {}, "conditions": [], "disarmed": False, "virtue": 0, "piety": 0,
             "corruption_level": 0, "grip": "two_hands"}
        d.update(extra)
        return d
    attacker = combatant("Konrad", "longsword", ["Heavy_Light"], stance="half_sword", previous_stance="vom_tag",
                         maneuver="Half-Sword Thrust", trigger="always", aimed_zone="head",
                         damage_type="piercing", use_trick=False, fight_state={})
    defender = combatant("Bandit", "battle_axe", ["Heavy_Medium"], stance="neutral")
    for k in attacker:
        if k not in ("name",):
            assert re.search(rf"\b{k}\b", src), f"macro does not send {k}"
    res = ce.CombatEngine().attack_roll(attacker, defender)
    for k in ("hit", "damage", "damage_type", "fight_state", "armor_wear"):
        assert k in res, k
    assert res.get("maneuver") in (None, "Half-Sword Thrust") or "Half-Sword" in str(res)
