#!/usr/bin/env python3
"""Exit 0 only when the agent may merge a PR. Exit 1 blocked (one `BLOCKED:` line per reason), 2 setup error.

Plan PR (head `<branch>-plan`, base `<branch>`): CI green and `plan: agent` in `.agent-flow/config`;
otherwise the Owner merges it. Archive PR (head `agent-flow/<topic>-archive`): CI green and every changed file
under `openspec/specs/`, `openspec/changes/<topic>/` or `openspec/changes/archive/<date>-<topic>/`. Any other PR: CI green including the `evidence-check`
job, a merged Plan PR for its head branch, and no change to a locked path (or a `protect:` glob from
`.agent-flow/config`) since that Plan PR merged.
Always: no `agent-flow:owner-judges` label, no kill switch.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

LOCKED = re.compile(r"(\.agent-flow/|\.github/workflows/|openspec/config\.yaml$|openspec/changes/[^/]+/specs/)")
EVIDENCE_CHECK = "evidence-check"
OWNER_LABEL = "agent-flow:owner-judges"


def changed(base, head):
    """Files changed from base to head; ValueError when the list cannot be trusted."""
    try:
        r = subprocess.run(("gh", "api", f"repos/{{owner}}/{{repo}}/compare/{base}...{head}", "--jq", ".files[].filename"),
                           capture_output=True, text=True)
    except OSError as e:
        raise ValueError(e)
    if r.returncode:  # gh prints its error body on stdout, which would read as file names
        raise ValueError("gh api compare failed: " + (r.stderr or r.stdout).strip())
    files = r.stdout.split()
    if len(files) >= 300:  # the compare API stops listing at 300 files without saying so
        raise ValueError("compare lists 300 or more files and may be cut short; the Owner checks this PR")
    return files


def gh(*args):
    try:
        # no check: `gh pr checks` exits non-zero while checks are pending but still prints JSON
        return subprocess.run(("gh",) + args, capture_output=True, text=True).stdout
    except OSError:
        return ""


def config(root):
    cfg = root / ".agent-flow/config"
    pairs = [l.split(":", 1) for l in cfg.read_text().splitlines() if ":" in l] if cfg.is_file() else []
    return {k.strip().lower(): v.strip().lower() for k, v in pairs}


def protected(root):
    """The `protect: <glob>` lines of `.agent-flow/config`, case kept: repo paths the Calling repo locks too."""
    cfg = root / ".agent-flow/config"
    lines = cfg.read_text().splitlines() if cfg.is_file() else []
    return [l.split(":", 1)[1].strip() for l in lines if l.split(":", 1)[0].strip().lower() == "protect" and ":" in l]


def is_locked(path, globs):
    return bool(LOCKED.match(path)) or any(fnmatch.fnmatchcase(path, g) for g in globs)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args(argv)
    root = Path(a.repo_root)
    try:
        checks = json.loads(gh("pr", "checks", a.pr, "--json", "name,state,bucket"))
        view = json.loads(gh("pr", "view", a.pr, "--json", "baseRefName,headRefName,headRefOid,labels"))
        head = view["headRefName"]
        try:  # only a PR other than a Plan or archive PR needs its Plan PR; none found blocks it
            plans = [] if head.endswith(("-plan", "-archive")) else json.loads(
                gh("pr", "list", "--base", head, "--head", head + "-plan", "--state", "merged", "--json", "mergeCommit") or "[]")
        except json.JSONDecodeError:
            plans = []
        return gate(root, checks, view, [p["mergeCommit"]["oid"] for p in plans], changed)
    except (ValueError, KeyError, TypeError) as e:
        print(f"setup error: a gh call failed or gave no usable JSON (installed and logged in?): {e}", file=sys.stderr)
        return 2


def gate(root, checks, view, plans, changed_files):
    """BLOCKED reasons for one PR from its checks, view, merged Plan PR commits and a changed_files(base, head)."""
    cfg = config(root)
    blocked = []
    buckets = [c["bucket"] for c in checks]
    bad = [c["name"] for c in checks if c["bucket"] not in ("pass", "skipping")]
    if bad:
        blocked.append("CI not green: " + ", ".join(bad))
    elif "pass" not in buckets:
        blocked.append("CI has no passing check")
    if OWNER_LABEL in [l["name"] for l in view.get("labels", [])]:
        blocked.append(f"labelled {OWNER_LABEL}: the Owner judges and merges it")
    head = view["headRefName"]
    if head.endswith("-archive"):
        topic = re.escape(head.removeprefix("agent-flow/").removesuffix("-archive"))
        ok = re.compile(rf"openspec/(specs/|changes/{topic}/|changes/archive/\d{{4}}-\d{{2}}-\d{{2}}-{topic}/)")
        outside = [f for f in changed_files(view["baseRefName"], view["headRefOid"]) if not ok.match(f)]
        if outside:
            blocked.append("archive PR changes files outside this change's OpenSpec paths: " + ", ".join(outside))
    elif head.endswith("-plan"):
        if cfg.get("plan") != "agent":
            blocked.append("Plan PR: the Owner merges it (or set `plan: agent` in .agent-flow/config)")
    else:
        if not any(c["name"] == EVIDENCE_CHECK and c["bucket"] == "pass" for c in checks):
            blocked.append(f"CI has no passing {EVIDENCE_CHECK} job")
        if not plans:
            blocked.append(f"no merged Plan PR ({head}-plan into {head})")
        else:
            globs = protected(root)
            locked = [f for f in changed_files(plans[0], view["headRefOid"]) if is_locked(f, globs)]
            if locked:
                blocked.append("changes locked paths after the Plan PR (needs a new Plan PR): " + ", ".join(locked))
    if (root / ".agent-flow/STOP").exists():
        blocked.append(".agent-flow/STOP exists")
    if cfg.get("merge") == "never":
        blocked.append(".agent-flow/config says merge: never")
    for r in blocked:
        print("BLOCKED: " + r)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
