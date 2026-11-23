#!/usr/bin/env python3
"""Evidence check: run every ticket criterion's Verify command; exit code alone decides.

usage: verify.py [--check-only] [<tickets dir> ...]   default: every docs/*/tickets under the cwd
A criterion is a line `- [ ] <text>` (or `- [x]`) in a ticket file, followed by an indented
`Verify: `<command>`` line (one or more) or an `Owner judges: <how>` line.
Exit 0 every command passed (owner-judged criteria are listed, not run), 1 a command failed or a
ticket is malformed, 2 no tickets found.

Stdlib only, so a Calling repo's CI can run a copy of it (`.agent-flow/verify.py`) without the plugin.
"""
import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

CRITERION = re.compile(r"\s*- \[[ xX]\] (.+)")
VERIFY = re.compile(r"\s+Verify: `([^`]+)`\s*$")
OWNER = re.compile(r"\s+Owner judges: \S")
FORBIDDEN = ["|", ";", "&", ">", "<", "$(", "$?", "\n"]
SHELLS = {"sh", "bash", "zsh", "dash", "fish"}
TIMEOUT = 900


def parse(path):
    """Return ([(line, criterion, [commands], owner)], [(line, error)]) for one ticket file."""
    items, errors, cur = [], [], None
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if m := CRITERION.fullmatch(line):
            cur = [n, m[1].strip(), [], False]
            items.append(cur)
        elif line.startswith("#"):
            cur = None  # a heading ends the criterion above it
        elif cur and (m := VERIFY.match(line)):
            cur[2].append(m[1])
        elif cur and OWNER.match(line):
            cur[3] = True
    for n, text, cmds, owner in items:
        if not cmds and not owner:
            errors.append((n, f"criterion has no Verify command and is not owner-judged: {text}"))
        for c in cmds:
            bad = [t for t in FORBIDDEN if t in c]
            argv = shlex.split(c) if not bad else []
            if bad:
                errors.append((n, f"Verify command uses {' '.join(bad)} (exit code must come from one command): {c}"))
            elif argv and Path(argv[0]).name in SHELLS and "-c" in argv:
                errors.append((n, f"Verify command wraps a shell: {c}"))
    return items, errors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true", help="validate tickets, run nothing")
    ap.add_argument("dirs", nargs="*")
    a = ap.parse_args(argv)
    dirs = [Path(d) for d in a.dirs] or sorted(Path(".").glob("docs/*/tickets"))
    files = sorted(f for d in dirs for f in d.glob("*.md"))
    if not files:
        print("no ticket files found", file=sys.stderr)
        return 2
    failed = False
    for f in files:
        items, errors = parse(f)
        for n, msg in errors:
            print(f"ERROR {f}:{n}: {msg}")
            failed = True
        if errors or a.check_only:
            continue
        for n, text, cmds, owner in items:
            if owner:
                print(f"OWNER {f}:{n}: {text}")
            for c in cmds:
                try:
                    p = subprocess.run(shlex.split(c), capture_output=True, text=True, timeout=TIMEOUT)
                    code, out = p.returncode, (p.stdout + p.stderr).strip()
                except (OSError, subprocess.TimeoutExpired) as e:
                    code, out = 127, str(e)
                if code == 0:
                    print(f"PASS {f}:{n}: {c}")
                else:
                    failed = True
                    print(f"FAIL {f}:{n}: {c} (exit {code})\n" + "\n".join("  " + l for l in out.splitlines()[-20:]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
