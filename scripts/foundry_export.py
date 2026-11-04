# file: scripts/foundry_export.py
"""Export weapons (with damage types, guards, maneuvers) and armour (ratings by damage type) as CSB
Equippable Items for Foundry VTT. Contract: foundry/csb/WEAPON_ITEM_CONTRACT.md.
Run: python scripts/foundry_export.py   -> foundry/csb/weapons_items.json, foundry/csb/armor_items.json"""
import json
import os

import combat_techniques as CT

OUT = os.path.join(CT.ROOT, "foundry", "csb")
CONTRACT_VERSION = "1.0"


def weapon_item(key):
    w = CT.weapon_data(key)
    gs = CT.guard_set(w) or {}
    guards = CT.guards_for(w)
    mans = [m for m in CT.maneuvers_for(w)
            if not m["effects"].get("requires_feature") or m["effects"]["requires_feature"] in w.get("features", [])]
    props = {
        "item_kind": "Weapon", "contract_version": CONTRACT_VERSION, "weapon_id": key, "weapon_label": w.get("name", key),
        "weapon_type": w.get("type", ""), "source_file": "rules/weapons.json",
        "base_damage": w.get("base_damage", 0), "damage_type": w.get("damage_type", ""),
        "damage_types": ",".join(w.get("damage_types", [])), "stamina_cost": w.get("stamina_cost", 0),
        "min_str": w.get("min_STR", 0) or 0, "weight": w.get("weight", 0), "durability": w.get("durability", 0),
        "armor_piercing": int(bool(w.get("armor_piercing"))), "two_hand_guard_set": w.get("two_hand_guard_set", ""),
        "features": ",".join(w.get("features", [])), "guard_set": w.get("guard_set") or "",
        "default_guard": gs.get("default_stance", "neutral") if guards else "neutral",
        "guards": ",".join(guards) or "offensive,neutral,defensive",
        "guard_change_stamina": CT.GUARD_CHANGE_COST,
        "guards_json": json.dumps({g: CT.guard_info(w, g) for g in guards}, ensure_ascii=False),
        "maneuvers": ",".join(m["name"] for m in mans),
        "maneuvers_json": json.dumps(mans, ensure_ascii=False),
        "guards_two_hand_json": "", "maneuvers_two_hand_json": "",
    }
    if w.get("two_hand_guard_set"):          # longsword: the full 2H_sword set in two hands
        w2 = CT.grip(w, True)
        m2 = [m for m in CT.maneuvers_for(w2)
              if not m["effects"].get("requires_feature") or m["effects"]["requires_feature"] in w2.get("features", [])]
        props["guards_two_hand_json"] = json.dumps({g: CT.guard_info(w2, g) for g in CT.guards_for(w2)}, ensure_ascii=False)
        props["maneuvers_two_hand_json"] = json.dumps(m2, ensure_ascii=False)
    return {"name": w.get("name", key), "type": "equippableItem", "img": "icons/svg/sword.svg",
            "system": {"unique": False, "template": "", "props": props}}


def armor_item(tier, variant, spec):
    r = spec["armor_rating"]
    props = {"item_kind": "Armor", "contract_version": CONTRACT_VERSION, "armor_tier": tier, "armor_variant": variant,
             "armor_label": spec["name"], "source_file": "rules/armors.json",
             "armor_slashing": r["slashing"], "armor_piercing": r["piercing"], "armor_blunt": r["blunt"],
             "rigid": int(bool(spec.get("rigid"))), "coverage": ",".join(spec.get("coverage", [])),
             "stamina_penalty": spec.get("stamina_penalty", 0), "weight": spec.get("weight", 0),
             "max_durability": spec.get("max_durability", 0)}
    return {"name": spec["name"], "type": "equippableItem", "img": "icons/svg/shield.svg",
            "system": {"unique": False, "template": "", "props": props}}


def export(out_dir=OUT):
    os.makedirs(out_dir, exist_ok=True)
    weapons = [weapon_item(k) for k in CT.WEAPONS]
    with open(os.path.join(CT.ROOT, "rules", "armors.json"), encoding="utf-8-sig") as f:
        armors = json.load(f)
    arm = [armor_item(t, v, s) for t, vs in armors.items() for v, s in vs.items()]
    for name, data in (("weapons_items.json", weapons), ("armor_items.json", arm)):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return len(weapons), len(arm)


if __name__ == "__main__":
    print("exported %d weapons, %d armours" % export())
