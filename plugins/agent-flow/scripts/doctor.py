#!/usr/bin/env python3
"""Preflight for a first run: print what is missing and the exact fix. Exit 1 if a required piece is missing."""
import os
import shutil
import subprocess
import sys


def run(*cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except OSError:
        return 127, ""
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    problems = []  # (level, what, fix)

    def add(level, what, fix):
        problems.append((level, what, fix))

    if not shutil.which("git"):
        add("FAIL", "git not installed", "install git (macOS: xcode-select --install)")
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
    if sys.version_info < (3, 11):
        add("FAIL", "python %d.%d is older than 3.11" % sys.version_info[:2], "install Python 3.11 or newer")
    if not shutil.which("claude"):
        add("FAIL", "claude CLI not installed", "npm install -g @anthropic-ai/claude-code")
    if os.environ.get("AGENT_FLOW_SANDBOX") == "none" or not (shutil.which("sandbox-exec") or shutil.which("bwrap")):
        add("WARN", "sandbox unavailable: audits run project commands unsandboxed", "Linux: install bubblewrap (apt install bubblewrap)")
    for level, what, fix in problems:
        print(f"{level} {what}\n  Fix: {fix}")
    return 1 if any(p[0] == "FAIL" for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
