#!/usr/bin/env python3
"""Land a PR in one call: merge gate, update if behind, merge commit, then clean up. Exit 0 merged, 1 blocked or failed, 2 setup error."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import merge_gate


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def fail(why):
    print("FAILED: " + why)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--worktree")
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args(argv)
    root = a.repo_root
    try:
        info = json.loads(run(["gh", "pr", "view", a.pr, "--json", "headRefName,mergeStateStatus"], root)[1])
    except (OSError, json.JSONDecodeError):
        print("setup error: gh pr view gave no JSON (is gh installed?)", file=sys.stderr)
        return 2
    if info["mergeStateStatus"] == "BEHIND":
        rc, out = run(["gh", "pr", "update-branch", a.pr], root)
        if rc:
            return fail("update-branch: " + out)
        run(["gh", "pr", "checks", a.pr, "--watch"], root)  # result is judged by the gate below
    rc = merge_gate.main([a.pr, "--repo-root", root])
    if rc:
        return rc
    rc, out = run(["gh", "pr", "merge", a.pr, "--merge"], root)
    if rc:
        return fail("merge: " + out)
    state = json.loads(run(["gh", "pr", "view", a.pr, "--json", "state"], root)[1])["state"]
    if state != "MERGED":
        return fail(f"merge not confirmed (state {state}); worktree and branches left in place")
    branch = info["headRefName"]
    steps = ([["git", "worktree", "remove", a.worktree]] if a.worktree else []) + [
        ["git", "branch", "-D", branch], ["git", "push", "origin", "--delete", branch]]
    for cmd in steps:
        rc, out = run(cmd, root)
        if rc:
            return fail("merged, but cleanup stopped at `" + " ".join(cmd) + "`: " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
