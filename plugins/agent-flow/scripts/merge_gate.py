#!/usr/bin/env python3
"""Exit 0 only when a PR may be merged: CI green, latest audit passed, no kill switch. Exit 1 blocked, 2 setup error."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def gh(*args):
    try:
        # no check: `gh pr checks` exits non-zero while checks are pending but still prints JSON
        return subprocess.run(("gh",) + args, capture_output=True, text=True).stdout
    except OSError:
        return ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args(argv)
    root = Path(a.repo_root)
    try:
        checks = json.loads(gh("pr", "checks", a.pr, "--json", "name,state,bucket"))
    except json.JSONDecodeError:
        print("setup error: gh pr checks gave no JSON (is gh installed?)", file=sys.stderr)
        return 2
    blocked = []
    buckets = [c["bucket"] for c in checks]
    bad = [c["name"] for c in checks if c["bucket"] not in ("pass", "skipping")]
    if bad:
        blocked.append("CI not green: " + ", ".join(bad))
    elif "pass" not in buckets:
        blocked.append("CI has no passing check")
    rounds = {}
    for f in gh("pr", "diff", a.pr, "--name-only").split():
        m = re.fullmatch(r"docs/[^/]+/reviews/review-(\d+)\.audit\.md", f)
        if m:
            rounds[int(m[1])] = f
    if not rounds:
        blocked.append("no audit file in the PR")
    else:
        f = rounds[max(rounds)]
        lines = (root / f).read_text().splitlines() if (root / f).is_file() else []
        report = root / f.replace(".audit.md", ".md")
        if not lines or lines[-1] != "Result: passed":
            blocked.append(f"latest audit did not pass: {f}")
        elif not report.is_file() or f"Report sha256: {hashlib.sha256(report.read_bytes()).hexdigest()}" not in lines:
            blocked.append(f"report changed after its audit, or is missing: {report.relative_to(root)}")
    if (root / ".agent-flow/STOP").exists():
        blocked.append(".agent-flow/STOP exists")
    cfg = root / ".agent-flow/config"
    if cfg.is_file() and any(re.fullmatch(r"\s*merge\s*:\s*never\s*", l, re.I) for l in cfg.read_text().splitlines()):
        blocked.append(".agent-flow/config says merge: never")
    for r in blocked:
        print("BLOCKED: " + r)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
