import re
import sys
from pathlib import Path

CJK = re.compile(r"[　-〿㐀-䶿一-鿿＀-￯]")

bad = False
for p in sorted(Path(sys.argv[1]).rglob("*")):
    if not p.is_file():
        continue
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        continue
    for n, line in enumerate(lines, 1):
        if CJK.search(line):
            print(f"{p}:{n}")
            bad = True
sys.exit(1 if bad else 0)
