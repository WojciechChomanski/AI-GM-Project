import os, json, re, sys
from pathlib import Path

DEFAULTS = {
    "wojtek.json": {
        "strength": 35, "toughness": 35, "agility": 30, "mobility": 40,
        "dexterity": 30, "endurance": 35, "intelligence": 30, "willpower": 25,
        "perception": 30, "charisma": 25, "weapon_skill": 35
    },
    "gorthak.json": {
        "strength": 45, "toughness": 45, "agility": 25, "mobility": 30,
        "dexterity": 25, "endurance": 45, "intelligence": 20, "willpower": 30,
        "perception": 25, "charisma": 15, "weapon_skill": 40
    },
    "elara_voss.json": {
        "strength": 28, "toughness": 28, "agility": 38, "mobility": 42,
        "dexterity": 34, "endurance": 32, "intelligence": 40, "willpower": 34,
        "perception": 36, "charisma": 40, "weapon_skill": 35
    }
}

def prompt_project_path():
    print("Enter your PROJECT FOLDER path (the folder that contains 'rules' and 'scripts'):")
    p = input().strip('"').strip()
    root = Path(p)
    if not root.exists():
        print(f"[!] Path not found: {root}")
        sys.exit(1)
    if not (root / "rules").exists() or not (root / "scripts").exists():
        print(f"[!] Could not find 'rules' and 'scripts' inside: {root}")
        print("    Make sure you pasted the correct project root path.")
        sys.exit(1)
    return root

def safe_json_update(path: Path, additions: dict) -> bool:
    if not path.exists():
        print(f"[i] Skip (not found): {path.name}")
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for k, v in additions.items():
            if k not in data:
                data[k] = v
                changed = True
        if changed:
            backup = path.with_suffix(path.suffix + ".bak")
            backup.write_text(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2), encoding="utf-8")
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"[+] Updated stats in: {path.name} (backup -> {backup.name})")
        else:
            print(f"[=] Stats already present: {path.name}")
        return changed
    except Exception as e:
        print(f"[!] Failed to update {path.name}: {e}")
        return False

STATS_BLOCK_TEMPLATE = """
{indent}# --- RPG core stats (defaults = 30) ---
{indent}_gd = data if 'data' in locals() else {{}}
{indent}self.strength = _gd.get("strength", getattr(self, "strength", 30) if hasattr(self,"strength") else 30)
{indent}self.toughness = _gd.get("toughness", getattr(self, "toughness", 30) if hasattr(self,"toughness") else 30)
{indent}self.agility = _gd.get("agility", getattr(self, "agility", 30) if hasattr(self,"agility") else 30)
{indent}self.mobility = _gd.get("mobility", getattr(self, "mobility", 30) if hasattr(self,"mobility") else 30)
{indent}self.dexterity = _gd.get("dexterity", getattr(self, "dexterity", 30) if hasattr(self,"dexterity") else 30)
{indent}self.endurance = _gd.get("endurance", getattr(self, "endurance", 30) if hasattr(self,"endurance") else 30)
{indent}self.intelligence = _gd.get("intelligence", getattr(self, "intelligence", 30) if hasattr(self,"intelligence") else 30)
{indent}self.willpower = _gd.get("willpower", getattr(self, "willpower", 30) if hasattr(self,"willpower") else 30)
{indent}self.perception = _gd.get("perception", getattr(self, "perception", 30) if hasattr(self,"perception") else 30)
{indent}self.charisma = _gd.get("charisma", getattr(self, "charisma", 30) if hasattr(self,"charisma") else 30)
{indent}self.weapon_skill = _gd.get("weapon_skill", getattr(self, "weapon_skill", 30) if hasattr(self,"weapon_skill") else 30)
""".rstrip("\n")

def patch_character_py(path: Path) -> bool:
    if not path.exists():
        print(f"[!] scripts/character.py not found at: {path}")
        return False
    src = path.read_text(encoding="utf-8")

    if "class Character" not in src or "def __init__(" not in src:
        print("[!] Could not find class Character or __init__ in character.py")
        return False

    if "self.strength" in src and "self.toughness" in src and "self.weapon_skill" in src:
        print("[=] character.py already has RPG stat fields; no change.")
        return False

    # Find indent of __init__ body
    lines = src.splitlines()
    def_index = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("def __init__("):
            def_index = i
            break
    if def_index is None:
        print("[!] Could not locate __init__ block.")
        return False

    # Determine body indent: look at the next non-empty line after def
    body_indent = None
    for ln in lines[def_index+1:]:
        if ln.strip() == "":
            continue
        # Count leading spaces
        body_indent = ln[:len(ln)-len(ln.lstrip(" "))]
        break
    if body_indent is None:
        # fallback to 8 spaces
        body_indent = "        "

    # Insert stats block right after the first non-empty line after def
    insert_pos = None
    for j in range(def_index+1, len(lines)):
        if lines[j].strip() != "":
            insert_pos = j+1
            break
    if insert_pos is None:
        insert_pos = def_index+1

    block = STATS_BLOCK_TEMPLATE.format(indent=body_indent)
    new_lines = lines[:insert_pos] + [block] + lines[insert_pos:]
    new_src = "\n".join(new_lines)

    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(src, encoding="utf-8")
    path.write_text(new_src, encoding="utf-8")
    print(f"[+] Patched: {path} (backup -> {backup.name})")
    return True

def main():
    print("=== AI_GM_Project: RPG Stats Helper (ANY Folder) ===")
    root = prompt_project_path()

    # 1) Update character JSONs
    chars_dir = root / "rules" / "characters"
    updated_any = False
    for fname, defaults in DEFAULTS.items():
        updated_any |= safe_json_update(chars_dir / fname, defaults)

    # 2) Patch character.py
    updated_any |= patch_character_py(root / "scripts" / "character.py")

    if not updated_any:
        print("[=] Nothing changed (either files missing or already up to date).")
    else:
        print("[+] Stats injected successfully. You can now proceed to wire combat to use them.")

if __name__ == "__main__":
    main()
