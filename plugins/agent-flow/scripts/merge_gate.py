#!/usr/bin/env python3
"""Exit 0 only when the agent may merge a PR. Exit 1 blocked (one `BLOCKED:` line per reason), 2 setup error.

Plan PR (head `<branch>-plan`, base `<branch>`): CI green and `plan: agent` in `.agent-flow/config`;
otherwise the Owner merges it. Archive PR (head `agent-flow/<topic>-archive`): CI green and every changed file
under `openspec/specs/`, `openspec/changes/<topic>/` or `openspec/changes/archive/<date>-<topic>/`. Any other PR: CI green including the `evidence-check`
job (the test check), a merged Plan PR for its head branch, no change to a locked path (or a `protect:` glob from
`.agent-flow/config`) since that Plan PR merged, and review evidence: the latest PR comment starting
`<!-- agent-flow:review commit=<sha> -->` has a `| Task | Verdict | Evidence |` row with `PASS` and evidence for
every task of `openspec/changes/<topic>/tasks.md` (all ticked), and only merges were added after that commit.
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
TEST_CHECK = "evidence-check"  # CI job name kept from before ADR 0005, where it runs the program tests
OWNER_LABEL = "agent-flow:owner-judges"
REVIEW_MARK = re.compile(r"<!-- agent-flow:review commit=([0-9a-f]{40}) -->")
TASK = re.compile(r"\s*- \[([ xX])\] (\d+(?:\.\d+)*)\b")
ROW = re.compile(r"\|\s*(\d+(?:\.\d+)*)\s*\|\s*([^|]*?)\s*\|(.*)\|\s*$")


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


def protected(root):
    """The `protect: <glob>` lines of `.agent-flow/config`, case kept: repo paths the Calling repo locks too."""
    cfg = root / ".agent-flow/config"
    lines = cfg.read_text().splitlines() if cfg.is_file() else []
    return [l.split(":", 1)[1].strip() for l in lines if l.split(":", 1)[0].strip().lower() == "protect" and ":" in l]


def is_locked(path, globs):
    return bool(LOCKED.match(path)) or any(fnmatch.fnmatchcase(path, g) for g in globs)


def commits(base, head):
    """(status, {sha: parent count}) of the commits in head and not in base, or None when unreadable."""
    try:
        data = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/compare/{base}...{head}"))
        return data["status"], {c["sha"]: len(c["parents"]) for c in data["commits"]}
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def review_reasons(pr, view):
    """Why the review evidence record does not let this PR merge (ADR 0005); empty when it does."""
    head, oid, base = view["headRefName"], view["headRefOid"], view["baseRefName"]
    path = f"openspec/changes/{head.removeprefix('agent-flow/')}/tasks.md"
    raw = gh("api", f"repos/{{owner}}/{{repo}}/contents/{path}?ref={oid}", "-H", "Accept: application/vnd.github.raw")
    tasks = [m.groups() for m in map(TASK.match, raw.splitlines()) if m]
    if not tasks:
        return [f"no review evidence possible: no task lines read from {path} at the PR head"]
    reasons = []
    unticked = [t for box, t in tasks if box == " "]
    if unticked:
        reasons.append(f"tasks not ticked in {path}: " + ", ".join(unticked))
    try:
        comments = json.loads(gh("pr", "view", pr, "--json", "comments"))["comments"]
        records = [(m.group(1), c["body"]) for c in sorted(comments, key=lambda c: c.get("createdAt", ""))
                   if (m := REVIEW_MARK.match(c["body"].lstrip()))]
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return reasons + ["could not read the PR comments to find the review evidence"]
    if not records:
        return reasons + ["no review evidence: no PR comment starts with `<!-- agent-flow:review commit=<sha> -->`"]
    sha, body = records[-1]
    rows = {}
    for m in map(ROW.match, body.splitlines()):
        if m:
            rows.setdefault(m.group(1), []).append((m.group(2), m.group(3).strip()))
    ids = [t for _, t in tasks]
    for what, bad in (("has no row for", [t for t in ids if t not in rows]),
                      ("is not PASS for", [t for t in ids if any(v != "PASS" for v, _ in rows.get(t, []))]),
                      ("gives no evidence for", [t for t in ids if any(not e for _, e in rows.get(t, []))])):
        if bad:
            reasons.append(f"review evidence {what} task " + ", ".join(bad))
    # Commits after the reviewed one that are not on the base branch must be merges (land.py's update-branch).
    # shortcut: the compare API lists at most 250 commits and a merge's own edits are not inspected; read each
    # merge's diff if reviews start being bypassed that way
    since, own = commits(sha, oid), commits(base, oid)
    if since is None or own is None:
        reasons.append(f"could not compare the reviewed commit {sha[:12]} with the PR head")
    elif since[0] not in ("identical", "ahead"):
        reasons.append(f"review evidence is stale: reviewed commit {sha[:12]} is not in the PR head's history")
    else:
        added = [c[:12] for c, parents in since[1].items() if c in own[1] and parents < 2]
        if added:
            reasons.append("review evidence is stale: commits added after the review: " + ", ".join(added))
    return reasons


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
        if not any(c["name"] == TEST_CHECK and c["bucket"] == "pass" for c in checks):
            blocked.append(f"CI has no passing {TEST_CHECK} job")
        try:
            plans = json.loads(gh("pr", "list", "--base", head, "--head", head + "-plan", "--state", "merged",
                                  "--json", "mergeCommit") or "[]")
        except json.JSONDecodeError:
            plans = []
        if not plans:
            blocked.append(f"no merged Plan PR ({head}-plan into {head})")
        else:
            globs = protected(root)
            locked = [f for f in changed(plans[0]["mergeCommit"]["oid"], view["headRefOid"]) if is_locked(f, globs)]
            if locked:
                blocked.append("changes locked paths after the Plan PR (needs a new Plan PR): " + ", ".join(locked))
        blocked += review_reasons(a.pr, view)
    if (root / ".agent-flow/STOP").exists():
        blocked.append(".agent-flow/STOP exists")
    if cfg.get("merge") == "never":
        blocked.append(".agent-flow/config says merge: never")
    for r in blocked:
        print("BLOCKED: " + r)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
