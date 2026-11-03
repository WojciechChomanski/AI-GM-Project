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
