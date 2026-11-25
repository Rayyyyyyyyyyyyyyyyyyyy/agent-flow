#!/usr/bin/env python3
"""Land a PR or MR in one call: merge gate, update if behind (GitLab: refuse), merge commit, then clean up. Exit 0 merged, 1 blocked or failed, 2 setup error."""
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
    mr = f"projects/:fullpath/merge_requests/{a.pr}"
    try:
        on_gitlab = merge_gate.forge(Path(root)) == "gitlab"
        if on_gitlab:
            m = merge_gate.glab(root, mr + "?include_diverged_commits_count=true")
            info = {"headRefName": m["source_branch"], "mergeStateStatus": "", "headRefOid": m["sha"],
                    "behind": int(m["diverged_commits_count"])}
        else:
            info = json.loads(run(["gh", "pr", "view", a.pr, "--json", "headRefName,mergeStateStatus"], root)[1])
    except (ValueError, KeyError, TypeError) as e:
        print(f"setup error: gh pr view or glab api failed or gave no JSON (installed and logged in?): {e}", file=sys.stderr)
        return 2
    if on_gitlab and info["behind"]:  # GitLab has no merge-based branch update; its rebase would drop the reviewed commits
        return fail(f"MR is {info['behind']} commit(s) behind its target: merge the target into {info['headRefName']} "
                    "with a merge commit, push, wait for CI, then run land.py again")
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
    try:  # read before the gate: the merge then refuses any commit pushed after it, which the gate never saw
        sha = (info["headRefOid"] if on_gitlab else
               json.loads(run(["gh", "pr", "view", a.pr, "--json", "headRefOid"], root)[1])["headRefOid"])
    except (ValueError, KeyError):
        return fail("could not read the PR head commit")
    rc = merge_gate.main([a.pr, "--repo-root", root])
    if rc:
        return rc
    if on_gitlab:
        try:  # merges only while the head is still `sha`; squash off even when the project defaults it on
            merge_gate.glab(root, mr + "/merge", "-X", "PUT", "-f", "sha=" + sha, "-F", "squash=false")
        except ValueError as e:
            return fail(f"merge: {e}")
    else:
        rc, out = run(["gh", "pr", "merge", a.pr, "--merge", "--match-head-commit", sha], root)
        if rc:
            return fail("merge: " + out)
    try:
        state = (merge_gate.glab(root, mr)["state"] if on_gitlab else
                 json.loads(run(["gh", "pr", "view", a.pr, "--json", "state"], root)[1])["state"]).upper()
    except (ValueError, KeyError, AttributeError):
        return fail("merge returned 0 but the PR state is unreadable; worktree and branches left in place")
    if state != "MERGED":
        return fail(f"merge not confirmed (state {state}); worktree and branches left in place")
    branch = info["headRefName"]
    # --repo-root may be the worktree being removed, so clean up from the main checkout
    rc, common = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root)
    if rc:
        return fail("merged, but could not locate the main checkout: " + common)
    main_dir = str(Path(common).parent)
    # the forge may already have deleted the source branch on merge (GitLab "Delete source branch", GitHub auto-delete)
    gone = run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], main_dir)[0] == 2
    steps = ([["git", "worktree", "remove", a.worktree]] if a.worktree else []) + [
        ["git", "branch", "-D", branch]] + ([] if gone else [["git", "push", "origin", "--delete", branch]])
    for cmd in steps:
        rc, out = run(cmd, main_dir)
        if rc:
            return fail("merged, but cleanup stopped at `" + " ".join(cmd) + "`: " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
