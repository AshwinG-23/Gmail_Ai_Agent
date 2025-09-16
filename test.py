import os
import re
from pathlib import Path

# Common secret patterns (pattern -> placeholder)
patterns = {
    r"sk_(live|test)_[0-9a-zA-Z]+": "STRIPE_KEY_PLACEHOLDER",
    r"AKIA[0-9A-Z]{16}": "AWS_ACCESS_KEY_PLACEHOLDER",
    r"(?i)aws(.{0,20})?(secret|key).{0,20}[0-9a-zA-Z/+]{40}": "AWS_SECRET_KEY_PLACEHOLDER",
    r"AIza[0-9A-Za-z-_]{35}": "GOOGLE_API_KEY_PLACEHOLDER",
    r"eyJ[a-zA-Z0-9_-]+?\.[a-zA-Z0-9._-]+?\.[a-zA-Z0-9._-]+": "JWT_PLACEHOLDER",
    r"(?i)(secret|password|apikey|token).{0,20}['\"][0-9a-zA-Z-_]{16,}['\"]": "GENERIC_SECRET_PLACEHOLDER",
}

# Load ignored paths from .gitignore
def load_gitignore():
    ignore_paths = set()
    if Path(".gitignore").exists():
        with open(".gitignore", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ignore_paths.add(line.rstrip("/"))
    return ignore_paths

def is_ignored(path, ignore_paths):
    for rule in ignore_paths:
        if rule in str(path):
            return True
    return False

def clean_file(filepath):
    changed = False
    try:
        with open(filepath, "r", errors="ignore") as f:
            content = f.read()

        original_content = content

        for pattern, placeholder in patterns.items():
            content = re.sub(pattern, placeholder, content)

        if content != original_content:
            with open(filepath, "w", errors="ignore") as f:
                f.write(content)
            changed = True
    except Exception:
        pass
    return changed

def scan_and_clean(root_dir="."):
    ignore_paths = load_gitignore()
    for root, _, files in os.walk(root_dir):
        # Always skip .git itself
        if ".git" in root:
            continue
        for file in files:
            filepath = Path(root) / file
            if is_ignored(filepath, ignore_paths):
                continue
            if clean_file(filepath):
                print(f"[CLEANED] Replaced secrets in {filepath}")

if __name__ == "__main__":
    print("🔎 Scanning and cleaning potential secrets (respecting .gitignore)...")
    scan_and_clean(".")
    print("\n✅ Scan & clean complete. All detected secrets replaced with placeholders.")
