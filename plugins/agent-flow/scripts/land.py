#!/usr/bin/env python3
"""Land a PR in one call: merge gate, update if behind, merge commit, then clean up. Exit 0 merged, 1 blocked or failed, 2 setup error."""
import argparse
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

import merge_gate


def run(cmd, cwd):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except OSError as e:
        return 127, str(e)
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
        out = io.StringIO()  # CI may still be running; every other BLOCKED reason stops before any remote write
        with contextlib.redirect_stdout(out):
            rc = merge_gate.main([a.pr, "--repo-root", root])
        fatal = [l for l in out.getvalue().splitlines() if not l.startswith("BLOCKED: CI")]
        if rc == 2 or (rc and fatal):
            print("\n".join(fatal))
            return rc
        rc, out = run(["gh", "pr", "update-branch", a.pr], root)
        if rc:
            return fail("update-branch: " + out)
        run(["gh", "pr", "checks", a.pr, "--watch"], root)  # result is judged by the gate below
    rc = merge_gate.main([a.pr, "--repo-root", root])
    if rc:
        return rc
    try:
        sha = json.loads(run(["gh", "pr", "view", a.pr, "--json", "headRefOid"], root)[1])["headRefOid"]
    except (json.JSONDecodeError, KeyError):
        return fail("could not read the PR head commit")
    rc, out = run(["gh", "pr", "merge", a.pr, "--merge", "--match-head-commit", sha], root)
    if rc:
        return fail("merge: " + out)
    try:
        state = json.loads(run(["gh", "pr", "view", a.pr, "--json", "state"], root)[1])["state"]
    except (json.JSONDecodeError, KeyError):
        return fail("merge returned 0 but the PR state is unreadable; worktree and branches left in place")
    if state != "MERGED":
        return fail(f"merge not confirmed (state {state}); worktree and branches left in place")
    branch = info["headRefName"]
    # --repo-root may be the worktree being removed, so clean up from the main checkout
    rc, common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root)
    if rc:
        return fail("merged, but could not locate the main checkout: " + common)
    main_dir = str(Path(common).parent)
    steps = ([["git", "worktree", "remove", a.worktree]] if a.worktree else []) + [
        ["git", "branch", "-D", branch], ["git", "push", "origin", "--delete", branch]]
    for cmd in steps:
        rc, out = run(cmd, main_dir)
        if rc:
            return fail("merged, but cleanup stopped at `" + " ".join(cmd) + "`: " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
