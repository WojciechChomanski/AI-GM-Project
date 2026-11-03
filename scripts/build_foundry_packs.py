# file: scripts/build_foundry_packs.py
"""Build Foundry v14 compendium pack SOURCES for the Breath and the Veil system from the repo rules JSON.

Output: foundry/system/build/packs-src/<pack>/<id>.json (one Foundry Item document per file).
Then `node foundry/system/tools/compile-packs.mjs` turns them into LevelDB packs in
foundry/system/breath-and-the-veil/packs/<pack> using the official @foundryvtt/foundryvtt-cli.
Or run both: `cd foundry/system && npm run build`.

Hidden stats (faith, virtue, piety, holy fury, corruption, stress, reputation) are stripped from every
document: they belong to the Breath backend only.
Weapon data reuses scripts/foundry_export.weapon_item (on main since PR 12)."""
import hashlib
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import combat_techniques as CT  # noqa: E402
import foundry_export as FE  # noqa: E402

ROOT = CT.ROOT
RULES = os.path.join(ROOT, "rules")
OUT = os.path.join(ROOT, "foundry", "system", "build", "packs-src")
SYSTEM_ID = "breath-and-the-veil"
HIDDEN_KEY = re.compile(r"^(faith|virtue|piety|holy_fury\w*|corruption\w*|stress\w*|reputation\w*)$", re.I)
ICONS = {"weapon": "icons/svg/sword.svg", "armor": "icons/svg/shield.svg", "class": "icons/svg/book.svg",
         "race": "icons/svg/mystery-man.svg", "gender": "icons/svg/mystery-man.svg", "talent": "icons/svg/aura.svg",
         "flaw": "icons/svg/hazard.svg", "advantage": "icons/svg/upgrade.svg", "skill": "icons/svg/book.svg"}


def load(*parts):
    with open(os.path.join(RULES, *parts), encoding="utf-8-sig") as f:
        return json.load(f)


def strip_hidden(node):
    """Remove hidden-stat keys at any depth (and string list entries naming them)."""
    if isinstance(node, dict):
        return {k: strip_hidden(v) for k, v in node.items() if not HIDDEN_KEY.match(str(k))}
    if isinstance(node, list):
        return [strip_hidden(v) for v in node if not (isinstance(v, str) and HIDDEN_KEY.match(v))]
    return node


def doc_id(pack, key):
    """Stable 16-char Foundry id, so re-builds update instead of duplicating."""
    h = hashlib.sha256(f"{SYSTEM_ID}:{pack}:{key}".encode()).hexdigest()
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    n = int(h, 16)
    return "".join(alphabet[(n >> (6 * i)) % 62] for i in range(16))


def para(*texts):
    return "".join(f"<p>{html.escape(str(t))}</p>" for t in texts if t)


def item(pack, key, name, itype, source_file, description="", rules=None, **fields):
    _id = doc_id(pack, key)
    system = {"source_id": key, "source_file": source_file, "description": description,
              "rules": strip_hidden(rules or {}), **strip_hidden(fields)}
    return {"_id": _id, "_key": f"!items!{_id}", "name": name, "type": itype, "img": ICONS[itype],
            "system": system, "effects": [], "flags": {}, "folder": None, "sort": 0, "ownership": {"default": 0}}


def split(s):
    return [x for x in str(s or "").split(",") if x]


def weapons():
    out = []
    for key in CT.WEAPONS:
        p = FE.weapon_item(key)["system"]["props"]
        w = CT.weapon_data(key)
        out.append(item("weapons", key, p["weapon_label"], "weapon", "rules/weapons.json",
                        para(w.get("description"), w.get("lore")),
                        rules={"guards": json.loads(p["guards_json"]), "maneuvers": json.loads(p["maneuvers_json"])},
                        weapon_type=p["weapon_type"], base_damage=int(p["base_damage"] or 0),
                        damage_type=p["damage_type"], damage_types=split(p["damage_types"]),
                        stamina_cost=int(p["stamina_cost"] or 0), min_str=int(p["min_str"] or 0),
                        weight=p["weight"] or 0, durability=int(p["durability"] or 0),
                        armor_piercing=bool(p["armor_piercing"]), guard_set=p["guard_set"],
                        two_hand_guard_set=p["two_hand_guard_set"], default_guard=p["default_guard"],
                        guards=split(p["guards"]), maneuvers=split(p["maneuvers"]), features=split(p["features"]),
                        equipped=False))
    return out


def armor():
    out = []
    for tier, variants in load("armors.json").items():
        for variant, s in variants.items():
            r = s["armor_rating"]
            md = int(s.get("max_durability", 0) or 0)
            out.append(item("armor", f"{tier}.{variant}", s["name"], "armor", "rules/armors.json", para(s.get("lore")),
                            tier=tier, variant=variant,
                            rating={"slashing": r["slashing"], "piercing": r["piercing"], "blunt": r["blunt"]},
                            rigid=bool(s.get("rigid")), coverage=list(s.get("coverage", [])),
                            stamina_penalty=int(s.get("stamina_penalty", 0) or 0), weight=s.get("weight", 0) or 0,
                            durability={"value": md, "max": md}, equipped=False))
    return out


def class_entries():
    for fn in sorted(os.listdir(os.path.join(RULES, "classes"))):
        if not fn.endswith(".json") or fn == "template.json":
            continue
        d = load("classes", fn)
        for k, c in d.items():
            if k != "meta" and isinstance(c, dict):
                yield fn, k, c


def classes():
    """One item per class key. If two files define the same key (a copy-paste slip in rules/classes), keep the
    file whose name matches the key and report the other."""
    out, entries = [], list(class_entries())
    owners = {}
    for fn, k, c in entries:
        if k in owners and fn[:-5].lower() != k.lower():
            print(f"warning: rules/classes/{fn} redefines class {k}; skipped", file=sys.stderr)
            continue
        owners[k] = fn
    for fn, k, c in entries:
        if owners.get(k) != fn:
            continue
        r = c.get("restrictions") or {}
        out.append(item("classes", k, c.get("label") or k.replace("_", " "), "class", f"rules/classes/{fn}",
                        para(c.get("description"), c.get("lore")),
                        rules={x: v for x, v in c.items() if x not in ("description", "lore")},
                        allowed_races=list(c.get("allowed_races") or r.get("races") or []),
                        allowed_genders=list(c.get("allowed_genders") or r.get("genders") or [])))
    return out


def races():
    return [item("races", k, k, "race", "rules/races.json", para(r.get("description"), r.get("lore")),
                 rules={x: v for x, v in r.items() if x not in ("description", "lore")})
            for k, r in load("races.json").items()]


def genders():
    out = []
    for k, s in load("stats.json").items():
        race, _, gender = k.partition("_")
        out.append(item("genders", k, f"{race} {gender}", "gender", "rules/stats.json",
                        para(f"Starting stats and caps for a {gender.lower()} {race.lower()}."),
                        rules=s, race=race, gender=gender))
    return out


def talents():
    out, names = [], {}
    for fn in sorted(os.listdir(os.path.join(RULES, "talents"))):
        if not fn.endswith(".json"):
            continue
        d = load("talents", fn)
        group = (d.get("meta") or {}).get("group", fn[:-5])
        for k, t in d.items():
            if k == "meta" or not isinstance(t, dict):
                continue
            names[k] = t
            out.append(item("talents", k, t.get("name", k), "talent", f"rules/talents/{fn}", para(t.get("description")),
                            rules={x: v for x, v in t.items() if x not in ("name", "description", "cp")},
                            group=group, cp=int(t.get("cp", 0) or 0)))
    return out, names


def creation(pack, fn, itype, talent_names):
    out = []
    for k, e in load("creation", fn).items():
        if k == "meta" or not isinstance(e, dict):
            continue
        ref = e.get("talent_ref", "")
        base = {**talent_names.get(ref, {}), **e} if ref else e
        cp = base.get("cp", 0)
        cp = cp[0] if isinstance(cp, list) and cp else cp
        extra = {"talent_ref": ref} if itype == "advantage" else {}
        out.append(item(pack, k, base.get("name", k.replace("_", " ").title()), itype, f"rules/creation/{fn}",
                        para(base.get("description")),
                        rules={x: v for x, v in base.items() if x not in ("name", "description", "cp")},
                        cp=int(cp or 0) if not isinstance(cp, str) else 0, **extra))
    return out


def skills():
    """No skills rules file exists yet: collect class skills and skill trees so they appear as items."""
    found = {}
    for fn, k, c in class_entries():
        for s in (c.get("skills") or {}):
            found.setdefault(s, {"from_classes": []})["from_classes"].append(k)
        for s, info in (c.get("skill_trees") or {}).items():
            e = found.setdefault(s, {"from_classes": []})
            e["from_classes"].append(k)
            e.update({x: v for x, v in info.items()} if isinstance(info, dict) else {})
    return [item("skills", s, s.replace("_", " ").title(), "skill", "rules/classes/*.json",
                 para(e.get("focus")), rules=e, rank=0) for s, e in sorted(found.items())]


def build(out_dir=OUT):
    t, names = talents()
    packs = {"weapons": weapons(), "armor": armor(), "classes": classes(), "races": races(), "genders": genders(),
             "talents": t, "flaws": creation("flaws", "flaws.json", "flaw", names),
             "advantages": creation("advantages", "advantages.json", "advantage", names), "skills": skills()}
    shutil.rmtree(out_dir, ignore_errors=True)
    for pack, docs in packs.items():
        d = os.path.join(out_dir, pack)
        os.makedirs(d, exist_ok=True)
        for doc in docs:
            with open(os.path.join(d, f"{doc['_id']}.json"), "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False, sort_keys=True)
                f.write("\n")
    return {k: len(v) for k, v in packs.items()}


if __name__ == "__main__":
    counts = build()
    print("pack sources:", ", ".join(f"{k} {v}" for k, v in counts.items()))
