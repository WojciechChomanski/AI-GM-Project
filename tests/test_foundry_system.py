"""Foundry v14 system (foundry/system/breath-and-the-veil): pack sources build from the repo rules,
carry no hidden stats, and match the manifest. LevelDB compilation is tested by `npm test` in foundry/system."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_foundry_packs as B  # noqa: E402

SYS = os.path.join(ROOT, "foundry", "system", "breath-and-the-veil")
HIDDEN = re.compile(r"^(faith|virtue|piety|holy_?fury\w*|corruption\w*|stress\w*|reputation\w*)$", re.I)


def manifest():
    return json.load(open(os.path.join(SYS, "system.json"), encoding="utf-8"))


def built(tmp_path):
    counts = B.build(str(tmp_path))
    docs = {}
    for pack in counts:
        d = tmp_path / pack
        docs[pack] = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.iterdir())]
    return counts, docs


def hidden_keys(node, where=""):
    if isinstance(node, dict):
        for k, v in node.items():
            if HIDDEN.match(str(k)):
                yield f"{where}.{k}"
            yield from hidden_keys(v, f"{where}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from hidden_keys(v, f"{where}[{i}]")


def test_build_produces_every_manifest_pack(tmp_path):
    counts, docs = built(tmp_path)
    assert sorted(counts) == sorted(p["name"] for p in manifest()["packs"])
    assert all(n > 0 for n in counts.values()), counts
    assert counts["weapons"] == len(B.CT.WEAPONS)
    longsword = next(d for d in docs["weapons"] if d["system"]["source_id"] == "longsword")
    assert longsword["system"]["two_hand_guard_set"] == "2H_sword"
    war_hammer = [d for d in docs["weapons"] if d["system"]["armor_piercing"]]
    assert war_hammer and not any(d["system"]["weapon_type"].endswith("sword") for d in war_hammer)


def test_documents_are_valid_foundry_items(tmp_path):
    _, docs = built(tmp_path)
    types = set(manifest()["documentTypes"]["Item"])
    ids = set()
    for pack, items in docs.items():
        for d in items:
            assert re.fullmatch(r"[A-Za-z0-9]{16}", d["_id"]) and d["_key"] == f"!items!{d['_id']}"
            assert d["_id"] not in ids
            ids.add(d["_id"])
            assert d["type"] in types and d["name"]


def test_ids_are_stable_between_builds(tmp_path):
    a = {d["_id"] for ds in built(tmp_path / "a")[1].values() for d in ds}
    b = {d["_id"] for ds in built(tmp_path / "b")[1].values() for d in ds}
    assert a == b


def test_no_hidden_stats_in_packs(tmp_path):
    _, docs = built(tmp_path)
    bad = [k for items in docs.values() for d in items for k in hidden_keys(d["system"], d["name"])]
    assert bad == []
    # the stripping is real: the source data does contain hidden stats
    assert "faith" in json.dumps(B.load("stats.json"))


def test_no_hidden_stats_in_data_models():
    src = open(os.path.join(SYS, "module", "data.mjs"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("//"))
    for word in ("faith", "virtue", "piety", "holy_fury", "corruption", "stress", "reputation"):
        assert word not in code.lower(), word


def test_manifest_is_v14_and_release_ready():
    m = manifest()
    assert m["compatibility"]["minimum"] == "14"
    assert m["manifest"].endswith("/releases/latest/download/system.json")
    assert m["download"].endswith("/breath-and-the-veil.zip")
    for f in m["esmodules"] + m["styles"] + [l["path"] for l in m["languages"]]:
        assert os.path.exists(os.path.join(SYS, f)), f


def test_skills_pack_comes_from_skills_rules(tmp_path):
    counts, docs = built(tmp_path)
    src = B.load("skills.json")["skills"]
    assert counts["skills"] == len(src)
    by_id = {d["system"]["source_id"]: d for d in docs["skills"]}
    assert set(by_id) == set(src)
    for sid, e in src.items():
        d = by_id[sid]
        assert d["name"] == e["name"] and d["system"]["source_file"] == "rules/skills.json"
        assert d["system"]["rules"]["stats"] == e["stats"]
        assert d["system"]["rules"]["trained_only"] == e["trained_only"]


def test_classes_pack_has_knight_and_no_paladin(tmp_path):
    _, docs = built(tmp_path)
    names = {d["name"].lower() for d in docs["classes"]}
    ids = {d["system"]["source_id"].lower() for d in docs["classes"]}
    assert not any("paladin" in n for n in names | ids)
    assert not any("cleric" in n for n in names | ids)
    assert any("knight" == i or i.endswith("knight") for i in ids)
    assert "integration" not in ids


def test_no_gm_only_stat_keys_in_packs(tmp_path):
    _, docs = built(tmp_path)
    gm = {k.lower() for k in B.load("stat_visibility.json").get("gm_only", [])}
    bad = []
    def walk(n, w):
        if isinstance(n, dict):
            for k, v in n.items():
                if str(k).lower() in gm:
                    bad.append(f"{w}.{k}")
                walk(v, f"{w}.{k}")
        elif isinstance(n, list):
            for v in n:
                walk(v, w)
    for items in docs.values():
        for d in items:
            walk(d["system"], d["name"])
    assert bad == []

def test_version_and_pack_banners_exist():
    m = manifest()
    assert m["version"] == "0.2.0"
    assert m["download"].endswith("/releases/download/v0.2.0/breath-and-the-veil.zip")
    banners = os.path.join(SYS, "assets", "banners")
    for pack in m["packs"]:
        assert pack["banner"] == f"assets/banners/{pack['name']}.webp"
        path = os.path.join(SYS, pack["banner"])
        assert os.path.isfile(path) and os.path.getsize(path) > 0
    assert os.path.isfile(os.path.join(banners, "_fallback.webp"))


def test_build_skips_retired_paladin_even_if_a_stale_file_is_present(tmp_path, monkeypatch):
    """Root-cause guard: a leftover paladin.json in rules/classes must not re-enter the pack."""
    import shutil
    rules_classes = os.path.join(ROOT, "rules", "classes")
    stale = os.path.join(str(tmp_path), "paladin.json")
    with open(stale, "w", encoding="utf-8") as f:
        json.dump({"Paladin": {"label": "Paladin", "description": "retired", "lore": ""}}, f)
    # Point the builder at a copy of rules/classes that includes the stale file.
    dest = tmp_path / "classes"
    shutil.copytree(rules_classes, dest)
    shutil.copy(stale, dest / "paladin.json")
    monkeypatch.setattr(B, "RULES", str(tmp_path))
    # copy skills.json etc. needed? class_entries only uses RULES/classes. classes() only needs that.
    # But B.RULES is also used by load() for other packs if we call build(). Just call classes().
    docs = B.classes()
    ids = {d["system"]["source_id"].lower() for d in docs}
    names = {d["name"].lower() for d in docs}
    assert "paladin" not in ids | names
    assert any(i == "knight" or i.endswith("knight") for i in ids)


def test_actor_model_reserves_inventory_fields():
    src = open(os.path.join(SYS, "module", "data.mjs"), encoding="utf-8").read()
    for word in ("carried_weight", "carry_capacity", "backpack", "main_hand", "off_hand", "left_upper_arm", "back", "belt"):
        assert word in src, word
    assert os.path.isfile(os.path.join(ROOT, "foundry", "system", "docs", "ACTOR_MODEL.md"))


def test_class_items_carry_player_visible_career_and_honours(tmp_path):
    _, docs = built(tmp_path)
    by_id = {d["system"]["source_id"]: d for d in docs["classes"]}
    ck = by_id["Crusader_Knight"]
    rules = ck["system"]["rules"]
    assert "career" in rules and "order_path" in rules
    assert "paladin" in (rules["order_path"].get("honours") or {})
    blob = json.dumps(rules)

    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items():
                assert not B.HIDDEN_KEY.match(str(k)), k
                assert k not in ("hidden", "hidden_start"), k
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(rules)

    knight = by_id["Knight"]
    evos = (knight["system"]["rules"].get("career") or {}).get("evolutions") or []
    assert evos and any(e.get("placeholder") for e in evos)


def test_class_locks_are_normalised_onto_the_item(tmp_path):
    _, docs = built(tmp_path)
    by_id = {d["system"]["source_id"]: d for d in docs["classes"]}
    assert by_id["Crusader_Knight"]["system"]["allowed_races"] == ["Human"]
    assert by_id["Crusader_Knight"]["system"]["allowed_genders"] == ["Male"]
    assert by_id["Stonewarden"]["system"]["allowed_races"] == ["Dwarf"]
    assert by_id["Veil_Sorceress"]["system"]["allowed_genders"] == ["Female"]
    assert "Paladin" not in by_id


def test_build_skips_on_hold_cleric(tmp_path):
    docs = B.classes()
    ids = {d["system"]["source_id"].lower() for d in docs}
    names = {d["name"].lower() for d in docs}
    assert "cleric" not in ids | names
    # The rules file is still in the repo; the pack builder is what hides it.
    assert os.path.isfile(os.path.join(ROOT, "rules", "classes", "cleric.json"))


def test_actor_model_has_the_thirteen_official_zones():
    src = open(os.path.join(SYS, "module", "data.mjs"), encoding="utf-8").read()
    char = open(os.path.join(SYS, "module", "character.mjs"), encoding="utf-8").read()
    for zone in ("head", "throat", "chest", "stomach", "groin",
                 "left_upper_arm", "right_upper_arm", "left_lower_arm", "right_lower_arm",
                 "left_upper_leg", "right_upper_leg", "left_lower_leg", "right_lower_leg"):
        assert zone in src and zone in char, zone
    assert "scaledZones" in char and "pyRound" in char
