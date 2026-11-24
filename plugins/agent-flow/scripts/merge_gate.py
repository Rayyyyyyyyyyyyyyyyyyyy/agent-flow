#!/usr/bin/env python3
"""Exit 0 only when the agent may merge a PR. Exit 1 blocked (one `BLOCKED:` line per reason), 2 setup error.

Plan PR (head `<branch>-plan`, base `<branch>`): CI green and `plan: agent` in `.agent-flow/config`;
otherwise the Owner merges it. Archive PR (head `agent-flow/<topic>-archive`): CI green and every changed file
under `openspec/specs/`, `openspec/changes/<topic>/` or `openspec/changes/archive/<date>-<topic>/`. Any other PR: CI green including the `evidence-check`
job, a merged Plan PR for its head branch, and no change to a locked path since that Plan PR merged.
Always: no `agent-flow:owner-judges` label, no kill switch.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

LOCKED = re.compile(r"(\.agent-flow/|\.github/workflows/|openspec/config\.yaml$|openspec/changes/[^/]+/specs/)")
EVIDENCE_CHECK = "evidence-check"
OWNER_LABEL = "agent-flow:owner-judges"


def changed(base, head):
    # shortcut: the compare API lists at most 300 files; enough for one goal, page it if goals grow
    return gh("api", f"repos/{{owner}}/{{repo}}/compare/{base}...{head}", "--jq", ".files[].filename").split()


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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args(argv)
    root = Path(a.repo_root)
    try:
        checks = json.loads(gh("pr", "checks", a.pr, "--json", "name,state,bucket"))
        view = json.loads(gh("pr", "view", a.pr, "--json", "baseRefName,headRefName,headRefOid,labels"))
    except json.JSONDecodeError:
        print("setup error: gh gave no JSON (is gh installed and logged in?)", file=sys.stderr)
        return 2
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
        outside = [f for f in changed(view["baseRefName"], view["headRefOid"]) if not ok.match(f)]
        if outside:
            blocked.append("archive PR changes files outside this change's OpenSpec paths: " + ", ".join(outside))
    elif head.endswith("-plan"):
        if cfg.get("plan") != "agent":
            blocked.append("Plan PR: the Owner merges it (or set `plan: agent` in .agent-flow/config)")
    else:
        if not any(c["name"] == EVIDENCE_CHECK and c["bucket"] == "pass" for c in checks):
            blocked.append(f"CI has no passing {EVIDENCE_CHECK} job")
        try:
            plans = json.loads(gh("pr", "list", "--base", head, "--head", head + "-plan", "--state", "merged",
                                  "--json", "mergeCommit") or "[]")
        except json.JSONDecodeError:
            plans = []
        if not plans:
            blocked.append(f"no merged Plan PR ({head}-plan into {head})")
        else:
            locked = [f for f in changed(plans[0]["mergeCommit"]["oid"], view["headRefOid"]) if LOCKED.match(f)]
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
