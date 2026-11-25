#!/usr/bin/env python3
"""Preflight for a first run: print what is missing and the exact fix. Exit 1 if a required piece is missing."""
import shutil
import subprocess
import sys
from pathlib import Path

import merge_gate


def run(*cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except OSError:
        return 127, ""
    return r.returncode, (r.stdout + r.stderr).strip()


def check_github(add):
    have_gh = shutil.which("gh")
    if not have_gh:
        add("FAIL", "gh not installed", "install the GitHub CLI: https://cli.github.com")
    auth_ok, auth = (False, "")
    if have_gh:
        rc, auth = run("gh", "auth", "status")
        auth_ok = rc == 0
        if not auth_ok:
            add("FAIL", "gh not logged in", "gh auth login")
    rc, url = run("git", "remote", "get-url", "origin")
    if rc != 0:
        add("FAIL", "origin remote missing", "git remote add origin <url of your GitHub repo>")
    elif auth_ok:
        rc, out = run("gh", "api", "repos/{owner}/{repo}", "-q", ".permissions.push")
        if out != "true":
            add("FAIL", "push access to origin missing", "ask the repo owner for write access, or point origin at a repo you own")
        if run("gh", "api", "repos/{owner}/{repo}", "-q", ".private")[1] == "true" and run("gh", "api", "user", "-q", ".plan.name")[1] == "free":
            add("WARN", "branch protection unavailable (private repo on a free plan): merge gate script is the only guard", "make the repo public or upgrade the plan")
        if url.startswith("https://") and "workflow" not in auth:
            add("WARN", "token lacks the workflow scope (HTTPS remote cannot push .github/workflows)", "gh auth refresh -s workflow")


def check_gitlab(add):
    if not shutil.which("glab"):
        add("FAIL", "glab not installed", "install the GitLab CLI: https://gitlab.com/gitlab-org/cli")
        return
    try:
        host = merge_gate.origin(".")[0]
    except ValueError:
        add("FAIL", "origin remote missing or not a GitLab project URL", "git remote add origin <url of your GitLab project>")
        return
    if run("glab", "auth", "status", "--hostname", host)[0] != 0:
        add("FAIL", f"glab not logged in to {host}", f"glab auth login --hostname {host}")
        return
    try:
        proj = merge_gate.glab(".", "projects/:fullpath")
        perms = proj.get("permissions") or {}
        level = max((perms.get(k) or {}).get("access_level", 0) for k in ("project_access", "group_access"))
        me = merge_gate.glab(".", "user")["id"]
    except (ValueError, AttributeError, KeyError, TypeError):
        add("FAIL", "glab cannot read the origin project", "check `glab api projects/:fullpath` in the repo root")
        return
    try:  # `permissions` omits roles inherited from a parent group; members/all includes them
        level = max(level, merge_gate.glab(".", f"projects/:fullpath/members/all/{me}")["access_level"])
    except (ValueError, KeyError, TypeError):
        pass
    if level < 30:  # 30 = Developer, the lowest role that can push
        add("FAIL", "push access to origin missing", "ask the project owner for the Developer role or higher")
    if proj.get("merge_method") != "merge":
        add("FAIL", f"merge method is {proj.get('merge_method')}, not merge commit (land.py needs merge commits)",
            "Settings > Merge requests > Merge method: Merge commit")
    if proj.get("squash_option") == "always":
        add("FAIL", "project requires squash on merge (land.py needs the reviewed commits kept)",
            "Settings > Merge requests > Squash commits when merging: anything but Require")


def main():
    problems = []  # (level, what, fix)

    def add(level, what, fix):
        problems.append((level, what, fix))

    if not shutil.which("git"):
        add("FAIL", "git not installed", "install git (macOS: xcode-select --install)")
    try:
        on_gitlab = merge_gate.forge(Path(".")) == "gitlab"
    except ValueError as e:
        add("FAIL", str(e), "set `forge: github` or `forge: gitlab` in .agent-flow/config, or remove the line")
    else:
        check_gitlab(add) if on_gitlab else check_github(add)
    if not shutil.which("openspec"):
        add("FAIL", "openspec not installed", "npm install -g @fission-ai/openspec@latest")
    elif run("openspec", "list", "--json")[0] != 0:
        add("FAIL", "OpenSpec cannot read this repo (not initialised)", "run `openspec init` in the repo root, in your own terminal")
    if sys.version_info < (3, 11):
        add("FAIL", "python %d.%d is older than 3.11" % sys.version_info[:2], "install Python 3.11 or newer")
    for level, what, fix in problems:
        print(f"{level} {what}\n  Fix: {fix}")
    return 1 if any(p[0] == "FAIL" for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
