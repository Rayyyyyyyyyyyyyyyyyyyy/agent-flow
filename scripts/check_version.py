#!/usr/bin/env python3
"""Fail when a change to plugins/agent-flow/ does not raise the plugin's version.

Usage: check_version.py <base-ref>. Claude Code only updates an installed plugin when its version changes,
so every PR that touches the plugin must bump `version` in plugin.json (semver X.Y.Z, compared numerically).
Exit 0 ok, 1 not bumped or malformed, 2 setup error.
"""
import json
import re
import subprocess
import sys

PLUGIN = "plugins/agent-flow"
MANIFEST = f"{PLUGIN}/.claude-plugin/plugin.json"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def version(text):
    v = json.loads(text).get("version", "")
    m = SEMVER.match(v)
    return (v, tuple(int(x) for x in m.groups())) if m else (v, None)


def main(argv):
    if len(argv) != 1:
        print("usage: check_version.py <base-ref>", file=sys.stderr)
        return 2
    base = argv[0]
    diff = git("diff", "--name-only", f"{base}...HEAD", "--", PLUGIN)
    if diff.returncode:
        print(f"setup error: git diff against {base} failed: {diff.stderr.strip()}", file=sys.stderr)
        return 2
    head_v, head_t = version(open(MANIFEST).read())
    if head_t is None:
        print(f"FAIL {MANIFEST}: version {head_v!r} is not X.Y.Z")
        return 1
    if not diff.stdout.split():
        print(f"OK plugin unchanged, version {head_v}")
        return 0
    old = git("show", f"{base}:{MANIFEST}")
    base_v, base_t = version(old.stdout) if old.returncode == 0 else ("", None)
    if base_t is not None and head_t <= base_t:
        print(f"FAIL {MANIFEST}: plugin changed but version {head_v} is not above {base_v}; bump it in this PR")
        return 1
    print(f"OK version {base_v or 'none'} -> {head_v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
