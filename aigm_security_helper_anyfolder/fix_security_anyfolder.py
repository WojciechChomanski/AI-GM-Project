import os, re, sys
from pathlib import Path

def prompt_project_path():
    print("Enter your PROJECT FOLDER path (the folder that contains chat_api.py):")
    p = input().strip('"').strip()
    root = Path(p)
    if not root.exists():
        print(f"[!] Path not found: {root}")
        sys.exit(1)
    if not (root / "chat_api.py").exists():
        print(f"[!] chat_api.py not found in: {root}")
        print("    Make sure you pasted the correct project root path.")
        sys.exit(1)
    return root

def prompt_api_key(env_path: Path):
    existing = None
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("OPENAI_API_KEY="):
                existing = line.split("=",1)[1].strip()
                break
    if existing and existing.startswith("sk-") and len(existing) > 20:
        print("[i] Found existing OPENAI_API_KEY in .env; reusing it.")
        return existing

    print("Paste your OpenAI API key (starts with 'sk-') and press ENTER:")
    key = input().strip()
    if not key.startswith("sk-"):
        print("[!] That doesn't look like an OpenAI key. You can re-run this script later.")
        sys.exit(1)

    # write/update .env
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        lines = [ln for ln in lines if not ln.startswith("OPENAI_API_KEY=")]
    lines.append(f"OPENAI_API_KEY={key}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[+] Saved key to {env_path}")
    return key

DOTENV_HEADER = (
    "import os\n"
    "from dotenv import load_dotenv\n"
    "load_dotenv()\n"
)

def ensure_dotenv_header(src: str) -> str:
    if "from dotenv import load_dotenv" in src and "load_dotenv()" in src:
        return src  # already present
    lines = src.splitlines()
    insert_at = 0
    for i, ln in enumerate(lines[:50]):
        if ln.startswith("import ") or ln.startswith("from "):
            insert_at = i + 1
        elif ln.strip() and not (ln.startswith("#") or ln.startswith('"') or ln.startswith("'")):
            insert_at = i
            break
    lines.insert(insert_at, DOTENV_HEADER)
    return "\n".join(lines)

def replace_hardcoded_keys(src: str) -> str:
    import re
    src = re.sub(r'openai\.api_key\s*=\s*["\']sk-[^"\']+["\']',
                 'openai.api_key = os.getenv("OPENAI_API_KEY")', src)
    src = re.sub(r'OpenAI\s*\(\s*api_key\s*=\s*["\']sk-[^"\']+["\']\s*\)',
                 'OpenAI(api_key=os.getenv("OPENAI_API_KEY"))', src)
    return src

def maybe_force_client_api_key(src: str) -> str:
    if 'client = OpenAI(' in src and 'api_key=' not in src and 'openai.api_key' not in src:
        src = src.replace('client = OpenAI(',
                          'client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), ')
    return src

def patch_file(path):
    if not path.exists():
        print(f"[i] Skip (not found): {path}")
        return False
    original = path.read_text(encoding="utf-8", errors="ignore")
    updated = original
    updated = ensure_dotenv_header(updated)
    updated = replace_hardcoded_keys(updated)
    updated = maybe_force_client_api_key(updated)

    if updated != original:
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(original, encoding="utf-8")
        path.write_text(updated, encoding="utf-8")
        print(f"[+] Patched: {path} (backup -> {backup.name})")
        return True
    else:
        print(f"[=] No changes needed: {path}")
        return False

def main():
    print("=== AI_GM_Project: Security Fix (ANY Folder) ===")
    root = prompt_project_path()
    env_path = root / ".env"
    prompt_api_key(env_path)

    changed = False
    for filename in ["chat_api.py", "chat_with_wojtek.py"]:
        changed |= patch_file(root / filename)

    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text(
            "# secrets\n.env\n*.env\n.env.*\n\n# local artifacts\nchat_logs/\nmemory_logs/\n\n# python\n__pycache__/\n*.pyc\n\n# OS\n.DS_Store\nThumbs.db\n",
            encoding="utf-8"
        )
        print(f"[+] Created: {gi}")
    else:
        print("[=] .gitignore already exists (left unchanged).")

    print("\nAll done. If you see '[+]' lines above, your files were updated safely.\n"
          "Open PowerShell in that folder and run:\n"
          "  uvicorn chat_api:app --reload\n")

if __name__ == "__main__":
    main()
