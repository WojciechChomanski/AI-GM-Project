import os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
TOOLS.mkdir(exist_ok=True)

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
    # insert after first import block if possible, else at top
    lines = src.splitlines()
    insert_at = 0
    for i, ln in enumerate(lines[:50]):
        # naive rule: put after last initial import line
        if ln.startswith("import ") or ln.startswith("from "):
            insert_at = i + 1
        elif ln.strip() and not (ln.startswith("#") or ln.startswith('"') or ln.startswith("'")):
            # hit a non-import, non-comment line: insert here
            insert_at = i
            break
    lines.insert(insert_at, DOTENV_HEADER)
    return "\n".join(lines)

def replace_hardcoded_keys(src: str) -> str:
    # Replace patterns like: openai.api_key = "sk-..."
    src = re.sub(r'openai\.api_key\s*=\s*["\']sk-[^"\']+["\']',
                 'openai.api_key = os.getenv("OPENAI_API_KEY")', src)

    # Replace OpenAI(api_key="sk-...") or OpenAI(api_key='sk-...')
    src = re.sub(r'OpenAI\s*\(\s*api_key\s*=\s*["\']sk-[^"\']+["\']\s*\)',
                 'OpenAI(api_key=os.getenv("OPENAI_API_KEY"))', src)

    # If there's OpenAI() without api_key, leave it (library will read env var)
    return src

def maybe_force_client_api_key(src: str) -> str:
    """
    If we see 'client = OpenAI(' but no api_key arg, and the code doesn't set openai.api_key,
    we can inject api_key for safety.
    """
    if 'client = OpenAI(' in src and 'api_key=' not in src and 'openai.api_key' not in src:
        src = src.replace('client = OpenAI(', 'client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), ')
    return src

def patch_file(path: Path):
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
    print("=== AI_GM_Project: Security Fix ===")
    env_path = ROOT / ".env"
    prompt_api_key(env_path)

    changed = False
    for filename in ["chat_api.py", "chat_with_wojtek.py"]:
        changed |= patch_file(ROOT / filename)

    # Also suggest .gitignore if missing (we won't overwrite the user's existing one)
    gi = ROOT / ".gitignore"
    if not gi.exists():
        gi.write_text(
            "# secrets\n.env\n*.env\n.env.*\n\n# local artifacts\nchat_logs/\nmemory_logs/\n\n# python\n__pycache__/\n*.pyc\n\n# OS\n.DS_Store\nThumbs.db\n",
            encoding="utf-8"
        )
        print(f"[+] Created: {gi}")
    else:
        print("[=] .gitignore already exists (left unchanged).")

    print("\nAll done. If you see '[+]' lines above, your files were updated safely.\n"
          "You can now run:\n"
          "  uvicorn chat_api:app --reload\n")

if __name__ == "__main__":
    main()
