import contextlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))
import merge_gate

GREEN = [{"name": "verify", "state": "SUCCESS", "bucket": "pass"},
         {"name": "evidence-check", "state": "SUCCESS", "bucket": "pass"},
         {"name": "x", "state": "SKIPPED", "bucket": "skipping"}]
PLAN = [{"mergeCommit": {"oid": "plan1"}}]
REVIEWED = "a" * 40
TASKS = "## 1. Export\nBlocked by: none\nSize: small\n- [x] 1.1 Add the button\n- [x] 1.2 Write the CSV\n"
TABLE = "| Task | Verdict | Evidence |\n|---|---|---|\n| 1.1 | PASS | src/a.py:3; tests/test_a.py |\n" \
        "| 1.2 | PASS | src/a.py:9; no test: one-line format call |\n"


def review(body=TABLE, sha=REVIEWED, at="2026-11-25T01:00:00Z"):
    return {"body": f"<!-- agent-flow:review commit={sha} -->\n" + body, "createdAt": at}


def compare(status="ahead", commits=(), total=None):
    cs = [{"sha": c, "parents": [{"sha": "p"}] * n} for c, n in commits]
    return {"status": status, "total_commits": len(cs) if total is None else total, "commits": cs}


def fake_gh(bindir, checks, head="agent-flow/t", labels=(), plans=PLAN, changed=("src/a.py",), tasks=TASKS,
            comments=(review(),), since=compare("identical"), own=compare(commits=[(REVIEWED, 1)]), compare_fails=False):
    """A fake gh answering the gate's calls; comments=None leaves the comments call to fail like gh does."""
    view = {"baseRefName": "main", "headRefName": head, "headRefOid": "head1",
            "labels": [{"name": l} for l in labels]}
    topic = head.removeprefix("agent-flow/")
    files = "echo '{\"message\": \"Not Found\"}'; exit 1" if compare_fails else "printf '%s\\n'" % "\\n".join(changed)
    (bindir / "gh").write_text(
        "#!/bin/sh\ncase \"$*\" in\n"
        "\"pr checks 7 --json name,state,bucket\") echo '%s';;\n"
        "\"pr view 7 --json baseRefName,headRefName,headRefOid,labels\") echo '%s';;\n"
        "\"pr list --base %s --head %s-plan --state merged --json mergeCommit\") echo '%s';;\n"
        "\"api repos/{owner}/{repo}/compare/plan1...head1 --jq %s\"|"
        "\"api repos/{owner}/{repo}/compare/main...head1 --jq %s\") %s;;\n"
        "\"api repos/{owner}/{repo}/contents/openspec/changes/%s/tasks.md?ref=head1 -H Accept: application/vnd.github.raw\") "
        "printf '%%s' '%s';;\n"
        "\"pr view 7 --json %s\") printf '%%s' '%s';;\n"
        "\"api repos/{owner}/{repo}/compare/%s...head1\") printf '%%s' '%s';;\n"
        "\"api repos/{owner}/{repo}/compare/main...head1\") printf '%%s' '%s';;\n"
        "*) echo '{\"message\": \"Not Found\"}'; exit 1;;\n"
        "esac\n" % (json.dumps(checks), json.dumps(view), head, head, json.dumps(plans), merge_gate.FILES_JQ,
                    merge_gate.FILES_JQ, files, topic, tasks, "comments" if comments is not None else "unanswered", json.dumps({"comments": list(comments or ())}), REVIEWED,
                    json.dumps(since), json.dumps(own)))
    (bindir / "gh").chmod(0o755)


class MergeGateTest(unittest.TestCase):
    def gate(self, checks=GREEN, stop=False, config=None, gh=True, **kw):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / ".agent-flow").mkdir()
        if stop:
            (root / ".agent-flow/STOP").write_text("")
        if config is not None:
            (root / ".agent-flow/config").write_text(config)
        bindir = root / "bin"
        bindir.mkdir()
        if gh:
            fake_gh(bindir, checks, **kw)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": str(bindir)}), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            code = merge_gate.main(["7", "--repo-root", str(root)])
        return code, out.getvalue()

    def test_passes(self):
        self.assertEqual(self.gate(), (0, ""))

    def test_failed_compare_is_setup_error(self):  # gh prints its error body on stdout; it is not a file list
        self.assertEqual(self.gate(compare_fails=True)[0], 2)

    def test_compare_at_its_300_file_limit_is_setup_error(self):
        self.assertEqual(self.gate(changed=tuple(f"src/{i}.py" for i in range(300)))[0], 2)

    def test_failing_check_blocks(self):
        code, out = self.gate(checks=GREEN + [{"name": "bad", "state": "FAILURE", "bucket": "fail"}])
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED: CI not green: bad", out)

    def test_pending_check_blocks(self):
        self.assertEqual(self.gate(checks=GREEN + [{"name": "p", "state": "PENDING", "bucket": "pending"}])[0], 1)

    def test_no_passing_check_blocks(self):
        self.assertEqual(self.gate(checks=[GREEN[2]])[0], 1)

    def test_missing_evidence_check_blocks(self):
        code, out = self.gate(checks=[GREEN[0]])
        self.assertEqual(code, 1)
        self.assertIn("evidence-check", out)

    def test_no_merged_plan_blocks(self):
        code, out = self.gate(plans=[])
        self.assertEqual(code, 1)
        self.assertIn("no merged Plan PR", out)

    def test_locked_paths_after_plan_block(self):
        for path in (".agent-flow/verify.py", ".github/workflows/ci.yml", ".gitlab-ci.yml", "openspec/config.yaml",
                     "openspec/changes/t/specs/cap/spec.md"):
            code, out = self.gate(changed=("src/a.py", path))
            self.assertEqual(code, 1, path)
            self.assertIn("changes locked paths", out)
            self.assertIn(path, out)

    def test_protect_globs_block(self):
        config = "protect: .eslintrc*\nProtect: src/Generated/*.ts\n"
        for path in (".eslintrc.json", "src/Generated/api.ts"):
            code, out = self.gate(config=config, changed=("src/a.py", path))
            self.assertEqual(code, 1, path)
            self.assertIn(path, out)
        self.assertEqual(self.gate(config=config, changed=("src/generated/api.ts",))[0], 0)

    def test_unlocked_docs_pass(self):
        self.assertEqual(self.gate(changed=("docs/t/discussion.md", "openspec/changes/t/tasks.md"))[0], 0)

    def test_archive_pr_inside_openspec_passes(self):
        files = ("openspec/specs/cap/spec.md", "openspec/changes/t/specs/cap/spec.md",
                 "openspec/changes/archive/2026-11-24-t/specs/cap/spec.md")
        self.assertEqual(self.gate(head="agent-flow/t-archive", checks=[GREEN[0]], plans=[], changed=files), (0, ""))

    def test_archive_pr_outside_its_paths_blocks(self):
        for path in ("src/a.py", "openspec/config.yaml", "openspec/changes/other/specs/cap/spec.md"):
            code, out = self.gate(head="agent-flow/t-archive", checks=[GREEN[0]], changed=("openspec/specs/c/spec.md", path))
            self.assertEqual(code, 1, path)
            self.assertIn("archive PR changes files outside", out)
            self.assertIn(path, out)

    def test_plan_pr_needs_owner(self):
        code, out = self.gate(head="agent-flow/t-plan", checks=[GREEN[0]])
        self.assertEqual(code, 1)
        self.assertIn("Plan PR: the Owner merges it", out)

    def test_plan_pr_with_plan_agent(self):
        self.assertEqual(self.gate(head="agent-flow/t-plan", checks=[GREEN[0]], config="plan: agent\n")[0], 0)

    def test_owner_judges_label_blocks(self):
        code, out = self.gate(labels=["agent-flow:owner-judges"])
        self.assertEqual(code, 1)
        self.assertIn("owner-judges", out)

    def test_stop_file_blocks(self):
        self.assertEqual(self.gate(stop=True)[0], 1)

    def test_merge_never_blocks(self):
        self.assertEqual(self.gate(config="x: 1\nmerge: never\n")[0], 1)

    def test_merge_never_tolerates_case_and_spaces(self):
        for line in ("merge:never", "Merge: Never ", "  MERGE :  never"):
            self.assertEqual(self.gate(config=line + "\n")[0], 1, line)

    def test_other_config_passes(self):
        self.assertEqual(self.gate(config="merge: auto\n")[0], 0)

    def test_no_review_evidence_blocks(self):
        for comments in ((), ({"body": "LGTM", "createdAt": "x"},), (review(sha="abc"),)):
            code, out = self.gate(comments=comments)
            self.assertEqual(code, 1, comments)
            self.assertIn("BLOCKED: no review evidence:", out)

    def test_latest_review_counts(self):
        fail = review(TABLE.replace("| 1.2 | PASS", "| 1.2 | FAIL"), at="2026-11-25T02:00:00Z")
        self.assertEqual(self.gate(comments=(fail, review()))[0], 1)
        self.assertEqual(self.gate(comments=(review(), fail))[0], 1)
        self.assertEqual(self.gate(comments=(fail, review(at="2026-11-25T03:00:00Z")))[0], 0)

    def test_task_missing_from_review_blocks(self):
        code, out = self.gate(tasks=TASKS + "- [x] 2.1 Document it\n")
        self.assertEqual(code, 1)
        self.assertIn("review evidence has no row for task 2.1", out)

    def test_failed_or_unclear_verdict_blocks(self):
        for verdict in ("FAIL", "pass", "PASS?", ""):
            code, out = self.gate(comments=(review(TABLE.replace("| 1.2 | PASS", f"| 1.2 | {verdict}")),))
            self.assertEqual(code, 1, verdict)
            self.assertIn("review evidence is not PASS for task 1.2", out)

    def test_task_without_evidence_blocks(self):
        code, out = self.gate(comments=(review(TABLE.replace("src/a.py:9; no test: one-line format call", " ")),))
        self.assertEqual(code, 1)
        self.assertIn("review evidence gives no evidence for task 1.2", out)

    def test_unticked_task_blocks(self):
        code, out = self.gate(tasks=TASKS.replace("[x] 1.2", "[ ] 1.2"))
        self.assertEqual(code, 1)
        self.assertIn("tasks not ticked in openspec/changes/t/tasks.md: 1.2", out)

    def test_unreadable_tasks_blocks(self):
        code, out = self.gate(tasks='{"message": "Not Found"}')
        self.assertEqual(code, 1)
        self.assertIn("no task lines read from openspec/changes/t/tasks.md", out)

    def test_commit_after_review_blocks(self):
        code, out = self.gate(since=compare(commits=[("c" * 40, 1)]), own=compare(commits=[(REVIEWED, 1), ("c" * 40, 1)]))
        self.assertEqual(code, 1)
        self.assertIn("review evidence is stale: commits added after the review: cccccccccccc", out)

    def test_review_not_in_head_history_blocks(self):
        code, out = self.gate(since=compare("diverged"))
        self.assertEqual(code, 1)
        self.assertIn("is not in the PR head's history", out)

    def test_merge_from_base_after_review_passes(self):
        # land.py's update-branch: a merge commit plus the base commits it brings, which are not the PR's own
        since = compare(commits=[("b" * 40, 1), ("m" * 40, 2)])
        own = compare(commits=[(REVIEWED, 1), ("m" * 40, 2)])
        self.assertEqual(self.gate(since=since, own=own), (0, ""))

    def test_unreadable_compare_blocks(self):
        code, out = self.gate(own={"message": "Not Found"})
        self.assertEqual(code, 1)
        self.assertIn("could not compare the reviewed commit", out)

    def test_unreadable_comments_blocks(self):
        code, out = self.gate(comments=({"createdAt": "x"},))
        self.assertEqual(code, 1)
        self.assertIn("could not read the PR comments", out)

    def test_reasons_one_per_line(self):
        code, out = self.gate(plans=[], stop=True)
        self.assertEqual([l[:8] for l in out.splitlines()], ["BLOCKED:"] * 2)

    def test_compare_listing_fewer_commits_than_it_counts_blocks(self):  # the compare API lists at most 250
        code, out = self.gate(own=compare(commits=[(REVIEWED, 1)], total=300))
        self.assertEqual(code, 1)
        self.assertIn("could not compare the reviewed commit", out)

    def test_failed_comments_read_blocks(self):  # gh exits 1 and prints its error body on stdout
        code, out = self.gate(comments=None)
        self.assertEqual(code, 1)
        self.assertIn("could not read the PR comments", out)

    @unittest.skipUnless(shutil.which("jq"), "jq not installed")
    def test_files_jq_lists_a_renames_old_path(self):  # moving a locked file away is a change to it
        data = {"files": [{"filename": "src/x.py", "previous_filename": ".agent-flow/verify.py"}, {"filename": "a.md"}]}
        out = subprocess.run(["jq", "-r", merge_gate.FILES_JQ], input=json.dumps(data), capture_output=True, text=True).stdout
        self.assertEqual(out.split(), ["src/x.py", ".agent-flow/verify.py", "a.md"])

    def test_setup_error_without_gh(self):
        self.assertEqual(self.gate(gh=False)[0], 2)


# a fake glab accepts only origin's host and maps origin's project (o/r) back to `:fullpath`
GLAB_HEADER = ("#!/bin/sh\nset -f\n[ \"$1 $2 $3\" = \"api --hostname gitlab.example.dev\" ] || { echo \"wrong host: $*\" >&2; exit 1; }\n"
               "shift 3\na=\"$*\"\ncase $a in *projects/o%2Fr*) a=\"${a%%projects/o%2Fr*}projects/:fullpath${a#*projects/o%2Fr}\";; esac\n"
               "set -- api $a\n")
NOT_FOUND = ('{"message":"404 Not Found"}', 1)  # glab exits 1 and still prints the error body on stdout
JOBS = [{"name": "test", "status": "success"}, {"name": "evidence-check", "status": "success"},
        {"name": "lint", "status": "failed", "allow_failure": True}, {"name": "deploy", "status": "skipped"}]


def gl_compare(commits=(), diffs=(("src/a.py", "src/a.py"),), timeout=False):
    return {"commit": None, "commits": [{"id": c, "parent_ids": ["p"] * n} for c, n in commits],
            "diffs": [{"old_path": o, "new_path": n} for o, n in diffs], "compare_timeout": timeout, "compare_same_ref": False}


def note(body, i=1, system=False):
    return {"id": i, "body": body, "system": system, "author": {"username": "reviewer"}}


def gitlab_api(head="agent-flow/t", labels=(), pipe_sha="head1", pipe_status="success", jobs=JOBS,
               plans=({"merge_commit_sha": "plan1", "sha": "x"},), diffs=(("src/a.py", "src/a.py"),), timeout=False,
               project=None, tasks=TASKS, notes=(note("added 1 commit", 1, True), note(review()["body"], 2)),
               since=(), off_history=False, own=((REVIEWED, 1),), **replace):
    """The `glab api` answers for MR 7, by argument string; a value is JSON, raw text, or (stdout, exit code)."""
    q = head.replace("/", "%2F")
    mr = {"target_branch": "main", "source_branch": head, "sha": "head1", "labels": list(labels), "state": "opened",
          "head_pipeline": {"id": 9, "sha": pipe_sha, "status": pipe_status}, "diverged_commits_count": 0}
    api = {
        "projects/:fullpath/merge_requests/7": mr,
        "projects/:fullpath": project or {"merge_method": "merge", "squash_option": "default_off"},
        "projects/:fullpath/pipelines/9/jobs --paginate": jobs,
        f"projects/:fullpath/merge_requests?state=merged&source_branch={q}-plan&target_branch={q} --paginate": list(plans),
        "projects/:fullpath/repository/compare?from=plan1&to=head1": gl_compare(diffs=diffs, timeout=timeout),
        "projects/:fullpath/repository/compare?from=main&to=head1": gl_compare(own, diffs, timeout),
        "projects/:fullpath/repository/compare?from=head1&to=main": gl_compare(),
        f"projects/:fullpath/repository/compare?from={REVIEWED}&to=head1": gl_compare(since),
        f"projects/:fullpath/repository/compare?from=head1&to={REVIEWED}": gl_compare((("f" * 40, 1),) if off_history else ()),
        f"projects/:fullpath/repository/files/openspec%2Fchanges%2F{q.removeprefix('agent-flow%2F')}%2Ftasks.md/raw?ref=head1": tasks,
        "projects/:fullpath/merge_requests/7/notes?sort=asc&order_by=created_at --paginate": list(notes),
    }
    api.update(replace)
    return api


class Sh(str):
    """A fake glab answer given as shell commands instead of fixed output."""


def fake_glab(path, api, log=None):
    """Write a fake glab at path answering `api` (see gitlab_api); anything else is a 404."""
    lines = [GLAB_HEADER + (f'echo "$*" >> {shlex.quote(str(log))}\n' if log else "") + 'case "$*" in\n']
    for args, v in api.items():
        if v is None:
            continue
        if isinstance(v, Sh):
            lines.append(f'"api {args}") {v};;\n')
            continue
        out, code = v if isinstance(v, tuple) else (v if isinstance(v, str) else json.dumps(v), 0)
        lines.append(f'"api {args}") printf %s {shlex.quote(out)}; exit {code};;\n')
    lines.append(f"*) printf %s {shlex.quote(NOT_FOUND[0])}; exit 1;;\nesac\n")
    path.write_text("".join(lines))
    path.chmod(0o755)


class GitLabGateTest(unittest.TestCase):
    def gate(self, config="forge: gitlab\n", **kw):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / ".agent-flow").mkdir()
        (root / ".agent-flow/config").write_text(config)
        fake_glab(root / "glab", gitlab_api(**kw))
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": str(root)}), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()), \
                mock.patch.object(merge_gate, "origin", return_value=("gitlab.example.dev", "o/r")):
            code = merge_gate.main(["7", "--repo-root", str(root)])
        return code, out.getvalue()

    def test_passes(self):
        self.assertEqual(self.gate(), (0, ""))

    def test_failed_job_blocks(self):
        code, out = self.gate(jobs=JOBS + [{"name": "unit", "status": "failed", "allow_failure": False}])
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED: CI not green: unit", out)

    def test_blocking_manual_job_is_pending(self):
        self.assertIn("CI not green: gate", self.gate(jobs=JOBS + [{"name": "gate", "status": "manual"}])[1])

    def test_missing_evidence_check_blocks(self):
        self.assertIn("CI has no passing evidence-check job", self.gate(jobs=JOBS[:1])[1])

    def test_pipeline_of_older_commit_blocks(self):
        self.assertIn("BLOCKED: CI has no passing check", self.gate(pipe_sha="old")[1])

    def test_failed_pipeline_blocks_when_jobs_pass(self):  # a trigger (bridge) job is not in the jobs list
        code, out = self.gate(pipe_status="failed")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED: CI not green: pipeline", out)

    def test_running_pipeline_blocks(self):
        self.assertIn("CI not green: pipeline", self.gate(pipe_status="running")[1])

    def test_locked_paths_after_plan_block(self):
        for d in ((".gitlab-ci.yml", ".gitlab-ci.yml"), (".agent-flow/verify.py", "src/moved.py")):
            code, out = self.gate(diffs=(d,))
            self.assertEqual(code, 1, d)
            self.assertIn("changes locked paths", out)

    def test_fast_forward_plan_uses_its_sha(self):
        self.assertEqual(self.gate(plans=({"merge_commit_sha": None, "sha": "plan1"},))[0], 0)

    def test_no_merged_plan_blocks(self):
        self.assertIn("no merged Plan PR", self.gate(plans=())[1])

    def test_owner_label_blocks(self):
        self.assertIn("owner-judges", self.gate(labels=["agent-flow:owner-judges"])[1])

    def test_archive_mr(self):  # reads its diff against main; no Plan MR, tasks or notes (their reads would 404)
        files = (("openspec/changes/t/specs/c/spec.md", "openspec/changes/archive/2026-11-25-t/specs/c/spec.md"),)
        self.assertEqual(self.archive(files), (0, ""))
        self.assertIn("archive PR changes files outside", self.archive((("src/a.py", "src/a.py"),))[1])

    def archive(self, diffs):
        api = gitlab_api(head="agent-flow/t-archive", diffs=diffs)
        keep = ("projects/:fullpath/merge_requests/7", "projects/:fullpath", "projects/:fullpath/pipelines/9/jobs --paginate",
                "projects/:fullpath/repository/compare?from=main&to=head1")
        return self.gate(head="agent-flow/t-archive", jobs=JOBS[:1], diffs=diffs, **{k: None for k in api if k not in keep})

    def test_plan_mr_does_not_look_up_a_plan_mr(self):
        q = "agent-flow%2Ft-plan"
        code, out = self.gate(head="agent-flow/t-plan", **{
            f"projects/:fullpath/merge_requests?state=merged&source_branch={q}-plan&target_branch={q} --paginate": None})
        self.assertEqual(code, 1)
        self.assertIn("Plan PR: the Owner merges it", out)

    def test_possibly_truncated_compare_is_setup_error(self):
        self.assertEqual(self.gate(diffs=tuple((f"src/{i}.py", f"src/{i}.py") for i in range(500)))[0], 2)

    def test_incomplete_compare_is_setup_error(self):
        self.assertEqual(self.gate(timeout=True)[0], 2)

    def test_failed_mr_read_is_setup_error(self):  # exit 1 with an error body on stdout is not an MR
        self.assertEqual(self.gate(**{"projects/:fullpath/merge_requests/7": NOT_FOUND})[0], 2)

    def test_merge_method_other_than_merge_commit_blocks(self):
        for method in ("ff", "rebase_merge"):
            code, out = self.gate(project={"merge_method": method, "squash_option": "never"})
            self.assertEqual(code, 1, method)
            self.assertIn(f"project merge method is {method}", out)

    def test_required_squash_blocks(self):
        code, out = self.gate(project={"merge_method": "merge", "squash_option": "always"})
        self.assertEqual(code, 1)
        self.assertIn("project requires squash", out)
        self.assertEqual(self.gate(project={"merge_method": "merge", "squash_option": "default_on"})[0], 0)

    def test_unreadable_project_is_setup_error(self):
        self.assertEqual(self.gate(project={"merge_method": "merge"})[0], 2)

    def test_no_review_note_blocks(self):
        for notes in ((), (note("LGTM"),), (note(review()["body"], system=True),)):
            code, out = self.gate(notes=notes)
            self.assertEqual(code, 1, notes)
            self.assertIn("BLOCKED: no review evidence:", out)

    def test_latest_review_note_counts(self):
        fail = review(TABLE.replace("| 1.2 | PASS", "| 1.2 | FAIL"))["body"]
        self.assertIn("is not PASS for task 1.2", self.gate(notes=(note(review()["body"], 1), note(fail, 2)))[1])
        self.assertEqual(self.gate(notes=(note(review()["body"], 3), note(fail, 2)))[0], 0)

    def test_failed_notes_read_blocks(self):
        q = "projects/:fullpath/merge_requests/7/notes?sort=asc&order_by=created_at --paginate"
        code, out = self.gate(**{q: NOT_FOUND})
        self.assertEqual(code, 1)
        self.assertIn("could not read the PR comments", out)

    def test_failed_tasks_read_blocks(self):  # a missing tasks.md: exit 1 and a 404 body
        code, out = self.gate(tasks=('{"message":"404 File Not Found"}', 1))
        self.assertEqual(code, 1)
        self.assertIn("no task lines read from openspec/changes/t/tasks.md", out)

    def test_unticked_task_blocks(self):
        self.assertIn("tasks not ticked", self.gate(tasks=TASKS.replace("[x] 1.2", "[ ] 1.2"))[1])

    def test_commit_after_review_blocks(self):
        code, out = self.gate(since=(("c" * 40, 1),), own=((REVIEWED, 1), ("c" * 40, 1)))
        self.assertEqual(code, 1)
        self.assertIn("commits added after the review: cccccccccccc", out)

    def test_merge_from_target_after_review_passes(self):
        self.assertEqual(self.gate(since=(("b" * 40, 1), ("m" * 40, 2)), own=((REVIEWED, 1), ("m" * 40, 2))), (0, ""))

    def test_review_not_in_head_history_blocks(self):
        self.assertIn("is not in the PR head's history", self.gate(off_history=True)[1])

    def test_failed_review_compare_blocks(self):
        code, out = self.gate(**{f"projects/:fullpath/repository/compare?from={REVIEWED}&to=head1": NOT_FOUND})
        self.assertEqual(code, 1)
        self.assertIn("could not compare the reviewed commit", out)

    def test_unknown_forge_is_setup_error(self):  # a typo must not fall back to GitHub silently
        self.assertEqual(self.gate(config="forge: gitlb\n")[0], 2)


class OriginTest(unittest.TestCase):
    def repo(self, **remotes):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        for name, url in remotes.items():
            subprocess.run(["git", "-C", str(root), "remote", "add", name, url], check=True)
        return root

    def test_origin_url_forms(self):
        for url, want in [("ssh://git@gitlab.example.dev:4422/grp/sub/proj.git", ("gitlab.example.dev", "grp/sub/proj")),
                          ("git@gitlab.example.dev:grp/proj.git", ("gitlab.example.dev", "grp/proj")),
                          ("https://gitlab.example.dev:8443/grp/proj.git", ("gitlab.example.dev:8443", "grp/proj")),
                          ("https://gitlab.example.dev/grp/proj", ("gitlab.example.dev", "grp/proj"))]:
            self.assertEqual(merge_gate.origin(self.repo(origin=url)), want, url)

    def test_origin_wins_over_upstream(self):  # glab's own :fullpath follows upstream
        root = self.repo(upstream="git@gitlab.example.dev:other/proj.git", origin="git@gitlab.example.dev:mine/proj.git")
        self.assertEqual(merge_gate.origin(root), ("gitlab.example.dev", "mine/proj"))

    def test_no_usable_origin_is_setup_error(self):
        for remotes in ({}, {"origin": "/srv/git/proj.git"}):
            with self.assertRaises(ValueError):
                merge_gate.origin(self.repo(**remotes))

    def test_forge_from_origin_url(self):
        self.assertEqual(merge_gate.forge(self.repo(origin="git@gitlab.example.dev:o/r.git")), "gitlab")
        self.assertEqual(merge_gate.forge(self.repo(origin="git@github.com:o/r.git")), "github")
        self.assertEqual(merge_gate.forge(self.repo(origin="git@github.com:o/gitlab-tools.git")), "github")

    def test_glab_error_body_is_not_data(self):  # glab prints the HTTP error body on stdout and exits 1
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        fake_glab(d / "glab", {})
        with mock.patch.dict(os.environ, {"PATH": str(d)}), \
                mock.patch.object(merge_gate, "origin", return_value=("gitlab.example.dev", "o/r")):
            for raw in (False, True):
                with self.assertRaises(ValueError):
                    merge_gate.glab(str(d), "projects/:fullpath/repository/files/x/raw?ref=h", raw=raw)


if __name__ == "__main__":
    unittest.main()
