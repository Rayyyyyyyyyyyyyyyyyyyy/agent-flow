#!/usr/bin/env python3
"""Exit 0 only when the agent may merge a PR. Exit 1 blocked (one `BLOCKED:` line per reason), 2 setup error.

Plan PR (head `<branch>-plan`, base `<branch>`): CI green and `plan: agent` in `.agent-flow/config`;
otherwise the Owner merges it. Archive PR (head `agent-flow/<topic>-archive`): CI green and every changed file
under `openspec/specs/`, `openspec/changes/<topic>/` or `openspec/changes/archive/<date>-<topic>/`. Any other PR: CI green including the `evidence-check`
job, a merged Plan PR for its head branch, and no change to a locked path (or a `protect:` glob from
`.agent-flow/config`) since that Plan PR merged.
Always: no `agent-flow:owner-judges` label, no kill switch.
On GitLab (origin host contains `gitlab`, or `forge: gitlab` in the config) a PR is a merge request, read through
`glab api` on origin's project and host.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

LOCKED = re.compile(r"(\.agent-flow/|\.github/workflows/|\.gitlab-ci\.yml$|openspec/config\.yaml$|openspec/changes/[^/]+/specs/)")
EVIDENCE_CHECK = "evidence-check"
OWNER_LABEL = "agent-flow:owner-judges"


def origin(root):
    """(host, project path) of the `origin` remote; ValueError when it is missing or not a host URL."""
    try:
        r = subprocess.run(("git", "remote", "get-url", "origin"), cwd=root, capture_output=True, text=True)
    except OSError as e:
        raise ValueError(e)
    url = r.stdout.strip()
    if "://" in url:
        u = urllib.parse.urlsplit(url)
        host = (u.hostname or "") + (f":{u.port}" if u.port and u.scheme in ("http", "https") else "")
        path = u.path
    elif m := re.fullmatch(r"(?:[^@/]+@)?([^:/]+):(.+)", url):  # scp-like: git@host:group/project.git
        host, path = m.groups()
    else:
        raise ValueError(f"origin is not a host URL: {url!r}")
    path = path.strip("/").removesuffix(".git")
    if not host or "/" not in path:
        raise ValueError(f"origin is not a project URL: {url!r}")
    return host, path


def glab(root, path, *flags):
    """`glab api` on origin's project, parsed; raises ValueError on any failure so a GitLab read never fails open.

    `:fullpath` is filled from origin here: glab's own placeholder follows an `upstream` remote when one exists.
    """
    host, project = origin(root)
    path = path.replace(":fullpath", urllib.parse.quote(project, safe=""))
    try:
        r = subprocess.run(("glab", "api", "--hostname", host, path) + flags, cwd=root, capture_output=True, text=True)
    except OSError as e:
        raise ValueError(e)
    if r.returncode:
        raise ValueError(r.stderr)
    return json.loads(r.stdout)


def forge(root):
    """`github` or `gitlab`: the config's `forge:` key, else whether origin's host names gitlab. ValueError on a bad key."""
    if cfg := config(root).get("forge"):
        if cfg not in ("github", "gitlab"):
            raise ValueError(f".agent-flow/config has forge: {cfg}; use github or gitlab")
        return cfg
    try:
        return "gitlab" if "gitlab" in origin(root)[0].lower() else "github"
    except ValueError:
        return "github"


def bucket(job):
    """A GitLab job status in `gh pr checks` bucket terms."""
    s = job["status"]
    if s == "success":
        return "pass"
    if s == "skipped" or (job.get("allow_failure") and s in ("failed", "manual")):
        return "skipping"
    return "fail" if s in ("failed", "canceled") else "pending"


def gitlab_facts(root, pr):
    """(checks, view, plan merge shas, changed(base, head)) for a GitLab MR, in the shapes the GitHub path uses."""
    q = urllib.parse.quote
    mr = glab(root, f"projects/:fullpath/merge_requests/{pr}")
    pipe = mr.get("head_pipeline") or {}
    checks = []
    # shortcut: a merged results pipeline runs on the merge ref (another sha), so it reads as no pipeline and the MR
    # stays blocked; check that ref's parents to support it once a Calling repo uses one
    if pipe.get("sha") == mr["sha"]:  # a pipeline of an older commit says nothing about this one
        jobs = glab(root, f"projects/:fullpath/pipelines/{pipe['id']}/jobs", "--paginate")
        # the pipeline's own status also covers trigger (bridge) jobs, which the jobs list leaves out
        checks = [{"name": "pipeline", "bucket": bucket(pipe)}] + [{"name": j["name"], "bucket": bucket(j)} for j in jobs]
    view = {"baseRefName": mr["target_branch"], "headRefName": mr["source_branch"], "headRefOid": mr["sha"],
            "labels": [{"name": l} for l in mr["labels"]]}
    head = view["headRefName"]
    plans = [] if head.endswith(("-plan", "-archive")) else glab(
        root, f"projects/:fullpath/merge_requests?state=merged&source_branch={q(head + '-plan', safe='')}"
              f"&target_branch={q(head, safe='')}", "--paginate")

    def diff(base, to):
        c = glab(root, f"projects/:fullpath/repository/compare?from={q(base, safe='')}&to={q(to, safe='')}")
        if c.get("compare_timeout"):
            raise ValueError("compare incomplete")
        # GitLab truncates diffs at its diff_max_files setting (500 at the lowest) without saying so
        if len(c["diffs"]) >= 500:
            raise ValueError("compare lists 500 or more files and may be truncated; the Owner checks this PR")
        return sorted({p for d in c["diffs"] for p in (d["old_path"], d["new_path"])})
    # merge_commit_sha is null after a fast-forward merge; the source head is then on the target
    return checks, view, [p.get("merge_commit_sha") or p["sha"] for p in plans], diff


def github_facts(root, pr):
    """(checks, view, plan merge shas, changed(base, head)) for a GitHub PR."""
    checks = json.loads(gh("pr", "checks", pr, "--json", "name,state,bucket"))
    view = json.loads(gh("pr", "view", pr, "--json", "baseRefName,headRefName,headRefOid,labels"))
    head = view["headRefName"]
    try:  # only a PR other than a Plan or archive PR needs its Plan PR; none found blocks it
        plans = [] if head.endswith(("-plan", "-archive")) else json.loads(
            gh("pr", "list", "--base", head, "--head", head + "-plan", "--state", "merged", "--json", "mergeCommit") or "[]")
    except json.JSONDecodeError:
        plans = []
    return checks, view, [p["mergeCommit"]["oid"] for p in plans], changed


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
        facts = gitlab_facts if forge(root) == "gitlab" else github_facts
        return gate(root, *facts(root, a.pr))
    except (ValueError, KeyError, TypeError) as e:
        print(f"setup error: a gh or glab call failed or gave no usable JSON (installed and logged in?): {e}", file=sys.stderr)
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
