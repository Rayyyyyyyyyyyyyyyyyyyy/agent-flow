"""Check a docs/<topic>/discussion.md against docs/agent-flow/contracts.md.

usage: check_discussion.py <discussion.md>   exit 0 valid, 1 invalid (prints file:line: reason)
"""
import re
import sys
from pathlib import Path

HEADINGS = ["Original words", "Finish line", "Authorizations", "Decisions", "Open questions"]
path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
errors = []

found = [(n, m.group(1).strip()) for n, line in enumerate(lines, 1) if (m := re.match(r"## (.*)", line))]
if [h for _, h in found] != HEADINGS:
    errors.append((1, f"second-level headings must be exactly {HEADINGS}, got {[h for _, h in found]}"))

start = next((n for n, h in found if h == "Finish line"), None)
if start:
    end = next((n for n, _ in found if n > start), len(lines) + 1)
    items = []  # [first line number, id, text]
    for n in range(start + 1, end):
        line = lines[n - 1]
        if m := re.match(r"- (C\d+)\b", line):
            items.append([n, m.group(1), line])
        elif items:
            items[-1][2] += "\n" + line
    if not items:
        errors.append((start, "Finish line has no '- C<n> <text>' items"))
    errors += [(n, f"{cid} has no 'evidence:'") for n, cid, text in items if "evidence:" not in text.lower()]

for n, msg in errors:
    print(f"{path}:{n}: {msg}")
sys.exit(1 if errors else 0)
