"""rules/classes: one class per key, no copy-paste duplicates, Holy Judge / Ogre Ravager restored (v1.0)."""
import json, os, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = os.path.join(ROOT, "rules", "classes")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from character_loader import find_class, class_stat_bonuses  # noqa: E402

NON_CLASS = {"meta", "integration"}


def class_keys():
    out = []
    for fn in sorted(os.listdir(CLASSES)):
        if fn.endswith(".json") and fn != "template.json":
            data = json.load(open(os.path.join(CLASSES, fn), encoding="utf-8-sig"))
            out += [(fn, k) for k, v in data.items() if k not in NON_CLASS and isinstance(v, dict)]
    return out


def test_every_class_key_defined_once():
    dupes = [k for k, n in Counter(k for _, k in class_keys()).items() if n > 1]
    assert dupes == []


def test_each_file_holds_its_own_class():
    for fn, k in class_keys():
        assert k.lower() == fn[:-5].lower(), (fn, k)


def test_moved_classes_still_load():
    assert class_stat_bonuses(find_class("Outlaw_Mercenary_Warrior")) == {
        "strength": 6, "toughness": 3, "endurance": 3, "charisma": -3}
    assert class_stat_bonuses(find_class("Ogre_Behemoth"))["toughness"] == 15


def test_holy_judge_v1():
    hj = find_class("Holy_Judge")
    assert hj["race_lock"] == ["Human"] and hj["gender_lock"] == ["Male"]
    assert hj["vocation_of"] == "Crusader_Knight" and hj["power_source"] == "Breath"
    assert class_stat_bonuses(hj) == {"willpower": 9, "intelligence": 6, "perception": 6}
    # core_rules.txt: no active magic for men; Breath only as passive triggers
    for name, a in hj["abilities"].items():
        assert a["type"] in ("passive", "utility", "execution"), name
        assert "holy_damage" not in a and "spell" not in json.dumps(a).lower().replace("not a spell", "")
        if "breath_trigger" in a:
            assert a["type"] == "passive" and a["breath_trigger"]["virtue_min"] >= 70
    knight = find_class("Crusader_Knight")
    vocations = next(t for t in knight["progression"] if t.get("vocation_choice"))
    assert set(vocations["abilities_gain_by_vocation"]["Holy_Judge"]) <= set(hj["abilities"])


def test_ogre_ravager_v1():
    r = find_class("Ogre Ravager")  # Rock.json spells it with a space
    assert r["race_lock"] == ["Ogre"] and r["gender_lock"] == ["Male"]
    assert class_stat_bonuses(r) == {"strength": 12, "toughness": 9, "dexterity": -6}
    assert set(r["abilities"]["active"]) == {"flesh_rend", "devour_charge"}


def test_invented_parts_are_marked():
    for fn in ("holy_judge.json", "ogre_ravager.json"):
        meta = json.load(open(os.path.join(CLASSES, fn), encoding="utf-8"))["meta"]
        assert meta["sources"] and meta["invented"] and meta["version"] == "1.0"
