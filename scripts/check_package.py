import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
HANDLE = "Rayyyyyyyyyyyyyyyyyyyy"
HANDLE_SKIP = ("README.md", ".claude-plugin/marketplace.json", "LICENSE", "NOTICE", "scripts/check_package.py")
HANDLE_SKIP_DIRS = ("docs/", "tests/")
LINE_RULES = {
    "personal path /Users/": re.compile(r"/Users/"),
    "personal path /home/<name>": re.compile(r"/home/[^/\s]+"),
    "email address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "forbidden word": re.compile(r"\b(rtk|ponytail)\b", re.I),
    "Asia/Taipei": re.compile(r"Asia/Taipei"),
    "CJK character": re.compile(r"[　-〿㐀-䶿一-鿿＀-￯]"),
}


def scan(path, rules):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return
    for n, line in enumerate(lines, 1):
        for name, rx in rules.items():
            if rx.search(line):
                print(f"{path.relative_to(root)}:{n}: {name}")
                yield 1


bad = 0
plugin = root / "plugins/agent-flow"
for p in sorted((plugin / "skills").rglob("SKILL.md")):
    if p.parent.name != "agent-flow":
        print(f"{p.relative_to(root)}:1: third-party skill")
        bad += 1
for p in sorted(plugin.rglob("*")):
    if p.is_file():
        bad += sum(scan(p, LINE_RULES))
tracked = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout.split("\n")
for f in tracked:
    if f and f not in HANDLE_SKIP and not f.startswith(HANDLE_SKIP_DIRS) and (root / f).is_file():
        bad += sum(scan(root / f, {"GitHub handle": re.compile(HANDLE)}))
sys.exit(1 if bad else 0)
