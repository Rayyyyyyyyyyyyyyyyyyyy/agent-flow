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
On GitLab (origin host contains `gitlab`, or `forge: gitlab` in the config) a PR is a merge request, read through
`glab api` on origin's project and host; the project must merge with merge commits and must not require squash.
A forge read that fails or has an unexpected shape is a setup error (exit 2) or a BLOCKED reason, never a pass.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

LOCKED = re.compile(r"(\.agent-flow/|\.github/workflows/|\.gitlab-ci\.yml$|openspec/config\.yaml$|openspec/changes/[^/]+/specs/)")
TEST_CHECK = "evidence-check"  # CI job name kept from before ADR 0005, where it runs the program tests
OWNER_LABEL = "agent-flow:owner-judges"
REVIEW_MARK = re.compile(r"<!-- agent-flow:review commit=([0-9a-f]{40}) -->")
TASK = re.compile(r"\s*- \[([ xX])\] (\d+(?:\.\d+)*)\b")
ROW = re.compile(r"\|\s*(\d+(?:\.\d+)*)\s*\|\s*([^|]*?)\s*\|(.*)\|\s*$")
FILES_JQ = ".files[] | .filename, .previous_filename // empty"  # a rename's old path counts as changed too


def gh(*args, check=True):
    """stdout of `gh <args>`; ValueError when it fails, since gh prints an HTTP error body on stdout."""
    try:
        r = subprocess.run(("gh",) + args, capture_output=True, text=True)
    except OSError as e:
        raise ValueError(e)
    if check and r.returncode:
        raise ValueError(f"gh {' '.join(args[:2])} failed: " + (r.stderr or r.stdout).strip())
    return r.stdout


def changed(base, head):
    """Files changed from base to head on GitHub; ValueError when the list cannot be trusted."""
    files = [f for f in gh("api", f"repos/{{owner}}/{{repo}}/compare/{base}...{head}", "--jq", FILES_JQ).splitlines() if f]
    if len(files) >= 300:  # the compare API stops listing at 300 files without saying so
        raise ValueError("compare lists 300 or more files and may be cut short; the Owner checks this PR")
    return files


def commits(base, head):
    """(base is in head's history, {sha: parent count} of the commits in head and not in base) on GitHub."""
    data = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/compare/{base}...{head}"))
    if data["total_commits"] != len(data["commits"]):  # the compare API lists at most 250 commits
        raise ValueError(f"compare lists {len(data['commits'])} of {data['total_commits']} commits")
    return data["status"] in ("identical", "ahead"), {c["sha"]: len(c["parents"]) for c in data["commits"]}


def github(root, pr):
    """(checks, view, plan merge shas, reads, blocked) for a GitHub PR."""
    # no check: `gh pr checks` exits non-zero while checks are pending but still prints JSON
    checks = json.loads(gh("pr", "checks", pr, "--json", "name,state,bucket", check=False))
    view = json.loads(gh("pr", "view", pr, "--json", "baseRefName,headRefName,headRefOid,labels"))
    head = view["headRefName"]
    plans = [] if head.endswith(("-plan", "-archive")) else [p["mergeCommit"]["oid"] for p in json.loads(
        gh("pr", "list", "--base", head, "--head", head + "-plan", "--state", "merged", "--json", "mergeCommit"))]

    def comments():
        cs = json.loads(gh("pr", "view", pr, "--json", "comments"))["comments"]
        return [c["body"] for c in sorted(cs, key=lambda c: c["createdAt"])]

    def tasks(path, ref):
        return gh("api", f"repos/{{owner}}/{{repo}}/contents/{path}?ref={ref}", "-H", "Accept: application/vnd.github.raw")

    return checks, view, plans, SimpleNamespace(changed=changed, commits=commits, tasks=tasks, comments=comments), []


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


def glab(root, path, *flags, raw=False):
    """`glab api` on origin's project, parsed (or raw text); ValueError on any failure so a read never fails open.

    `:fullpath` is filled from origin here: glab's own placeholder follows an `upstream` remote when one exists.
    """
    host, project = origin(root)
    path = path.replace(":fullpath", urllib.parse.quote(project, safe=""))
    try:
        r = subprocess.run(("glab", "api", "--hostname", host, path) + flags, cwd=root, capture_output=True, text=True)
    except OSError as e:
        raise ValueError(e)
    if r.returncode:  # glab prints the HTTP error body on stdout, which must not read as data
        raise ValueError(f"glab api {path} failed: " + (r.stderr or r.stdout).strip())
    return r.stdout if raw else json.loads(r.stdout)


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
    """A GitLab job or pipeline status in `gh pr checks` bucket terms."""
    s = job["status"]
    if s == "success":
        return "pass"
    if s == "skipped" or (job.get("allow_failure") and s in ("failed", "manual")):
        return "skipping"
    return "fail" if s in ("failed", "canceled") else "pending"


def gitlab(root, pr):
    """(checks, view, plan merge shas, reads, blocked) for a GitLab MR, in the shapes the GitHub path uses."""
    q = lambda s: urllib.parse.quote(s, safe="")  # noqa: E731
    mr = glab(root, f"projects/:fullpath/merge_requests/{pr}")
    proj = glab(root, "projects/:fullpath")
    blocked = []
    if proj["merge_method"] != "merge":  # fast-forward and semi-linear need a rebase, which drops the reviewed commits
        blocked.append(f"project merge method is {proj['merge_method']}, not merge commit "
                       "(Settings > Merge requests > Merge method: Merge commit)")
    if proj["squash_option"] == "always":
        blocked.append("project requires squash on merge, which drops the reviewed commits "
                       "(Settings > Merge requests > Squash commits when merging: not Require)")
    checks = []
    # every pipeline of the head sha, not only head_pipeline: a job without `rules:` runs only in the branch pipeline,
    # while head_pipeline is the MR pipeline, so reading that alone would skip the repo's own tests
    # shortcut: a merged results pipeline runs on the merge ref (another sha), so it reads as no pipeline and the MR
    # stays blocked; check that ref's parents to support it once a Calling repo uses one
    latest = {}  # the newest pipeline per ref; an older one on the same ref is a retry it superseded
    for p in glab(root, f"projects/:fullpath/pipelines?sha={mr['sha']}", "--paginate"):
        if p["sha"] == mr["sha"] and p["id"] > latest.get(p["ref"], {"id": -1})["id"]:
            latest[p["ref"]] = p
    for ref, pipe in sorted(latest.items()):
        jobs = glab(root, f"projects/:fullpath/pipelines/{pipe['id']}/jobs", "--paginate")
        # the pipeline's own status also covers trigger (bridge) jobs, which the jobs list leaves out
        checks += [{"name": f"pipeline {ref}", "bucket": bucket(pipe)}] + [{"name": j["name"], "bucket": bucket(j)} for j in jobs]
    view = {"baseRefName": mr["target_branch"], "headRefName": mr["source_branch"], "headRefOid": mr["sha"],
            "labels": [{"name": l} for l in mr["labels"]]}
    head = view["headRefName"]
    plans = [] if head.endswith(("-plan", "-archive")) else glab(
        root, f"projects/:fullpath/merge_requests?state=merged&source_branch={q(head + '-plan')}"
              f"&target_branch={q(head)}", "--paginate")

    def compare(a, b):
        c = glab(root, f"projects/:fullpath/repository/compare?from={q(a)}&to={q(b)}")
        if c["compare_timeout"]:
            raise ValueError("compare incomplete")
        return c

    def changed_files(base, to):
        d = compare(base, to)["diffs"]
        # GitLab truncates diffs at its diff_max_files setting (500 at the lowest) without saying so
        if len(d) >= 500:
            raise ValueError("compare lists 500 or more files and may be truncated; the Owner checks this PR")
        return sorted({p for x in d for p in (x["old_path"], x["new_path"])})

    def commit_map(base, to):  # base is in to's history when the reverse compare lists no commit
        return (not compare(to, base)["commits"],
                {c["id"]: len(c["parent_ids"]) for c in compare(base, to)["commits"]})

    def notes():
        ns = glab(root, f"projects/:fullpath/merge_requests/{pr}/notes?sort=asc&order_by=created_at", "--paginate")
        return [n["body"] for n in sorted(ns, key=lambda n: n["id"]) if not n["system"]]

    def tasks(path, ref):
        return glab(root, f"projects/:fullpath/repository/files/{q(path)}/raw?ref={q(ref)}", raw=True)

    # merge_commit_sha is null after a fast-forward merge; the source head is then on the target
    return (checks, view, [p["merge_commit_sha"] or p["sha"] for p in plans],
            SimpleNamespace(changed=changed_files, commits=commit_map, tasks=tasks, comments=notes), blocked)


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


def review_reasons(view, reads):
    """Why the review evidence record does not let this PR merge (ADR 0005); empty when it does."""
    head, oid, base = view["headRefName"], view["headRefOid"], view["baseRefName"]
    path = f"openspec/changes/{head.removeprefix('agent-flow/')}/tasks.md"
    try:
        raw = reads.tasks(path, oid)
    except ValueError:
        raw = ""
    tasks = [m.groups() for m in map(TASK.match, raw.splitlines()) if m]
    if not tasks:
        return [f"no review evidence possible: no task lines read from {path} at the PR head"]
    reasons = []
    unticked = [t for box, t in tasks if box == " "]
    if unticked:
        reasons.append(f"tasks not ticked in {path}: " + ", ".join(unticked))
    try:
        records = [(m.group(1), b) for b in reads.comments() if (m := REVIEW_MARK.match(b.lstrip()))]
    except (ValueError, KeyError, TypeError, AttributeError):
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
    # shortcut: a merge's own edits are not inspected; read each merge's diff if reviews start being bypassed that way
    try:
        (in_history, since), (_, own) = reads.commits(sha, oid), reads.commits(base, oid)
    except (ValueError, KeyError, TypeError):
        return reasons + [f"could not compare the reviewed commit {sha[:12]} with the PR head"]
    if not in_history:
        reasons.append(f"review evidence is stale: reviewed commit {sha[:12]} is not in the PR head's history")
    else:
        added = [c[:12] for c, parents in since.items() if c in own and parents < 2]
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
        facts = gitlab if forge(root) == "gitlab" else github
        return gate(root, *facts(root, a.pr))
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"setup error: a gh or glab call failed or gave no usable JSON (installed and logged in?): {e}", file=sys.stderr)
        return 2


def gate(root, checks, view, plans, reads, blocked):
    """Print the BLOCKED reasons for one PR from its checks, view, merged Plan PR commits and forge reads."""
    cfg = config(root)
    buckets = [c["bucket"] for c in checks]
    bad = [c["name"] for c in checks if c["bucket"] not in ("pass", "skipping")]
    if bad:
        blocked.append("CI not green: " + ", ".join(bad))
    elif "pass" not in buckets:
        blocked.append("CI has no passing check")
    if OWNER_LABEL in [l["name"] for l in view["labels"]]:
        blocked.append(f"labelled {OWNER_LABEL}: the Owner judges and merges it")
    head = view["headRefName"]
    if head.endswith("-archive"):
        topic = re.escape(head.removeprefix("agent-flow/").removesuffix("-archive"))
        ok = re.compile(rf"openspec/(specs/|changes/{topic}/|changes/archive/\d{{4}}-\d{{2}}-\d{{2}}-{topic}/)")
        outside = [f for f in reads.changed(view["baseRefName"], view["headRefOid"]) if not ok.match(f)]
        if outside:
            blocked.append("archive PR changes files outside this change's OpenSpec paths: " + ", ".join(outside))
    elif head.endswith("-plan"):
        if cfg.get("plan") != "agent":
            blocked.append("Plan PR: the Owner merges it (or set `plan: agent` in .agent-flow/config)")
    else:
        if not any(c["name"] == TEST_CHECK and c["bucket"] == "pass" for c in checks):
            blocked.append(f"CI has no passing {TEST_CHECK} job")
        if not plans:
            blocked.append(f"no merged Plan PR ({head}-plan into {head})")
        else:
            globs = protected(root)
            locked = [f for f in reads.changed(plans[0], view["headRefOid"]) if is_locked(f, globs)]
            if locked:
                blocked.append("changes locked paths after the Plan PR (needs a new Plan PR): " + ", ".join(locked))
        blocked += review_reasons(view, reads)
    if (root / ".agent-flow/STOP").exists():
        blocked.append(".agent-flow/STOP exists")
    if cfg.get("merge") == "never":
        blocked.append(".agent-flow/config says merge: never")
    for r in blocked:
        print("BLOCKED: " + r)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
