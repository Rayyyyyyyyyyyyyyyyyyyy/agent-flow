import contextlib
import io
import json
import os
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


def fake_gh(bindir, checks, head="agent-flow/t", labels=(), plans=PLAN, changed=("src/a.py",), compare_fails=False):
    view = {"baseRefName": "main", "headRefName": head, "headRefOid": "head1",
            "labels": [{"name": l} for l in labels]}
    (bindir / "gh").write_text(
        "#!/bin/sh\ncase \"$*\" in\n"
        "\"pr checks 7 --json name,state,bucket\") echo '%s';;\n"
        "\"pr view 7 --json baseRefName,headRefName,headRefOid,labels\") echo '%s';;\n"
        "\"pr list --base %s --head %s-plan --state merged --json mergeCommit\") echo '%s';;\n"
        "\"api repos/{owner}/{repo}/compare/plan1...head1 --jq .files[].filename\"|"
        "\"api repos/{owner}/{repo}/compare/main...head1 --jq .files[].filename\") %s;;\n"
        "esac\n" % (json.dumps(checks), json.dumps(view), head, head, json.dumps(plans),
                     "echo '{\"message\": \"Not Found\"}'; exit 1" if compare_fails else "printf '%s\\n'" % "\\n".join(changed)))
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
        with mock.patch.dict(os.environ, {"PATH": str(bindir)}), contextlib.redirect_stdout(out):
            code = merge_gate.main(["7", "--repo-root", str(root)])
        return code, out.getvalue()

    def test_passes(self):
        self.assertEqual(self.gate(), (0, ""))

    def test_failed_compare_is_setup_error(self):  # gh prints its error body on stdout; it is not a file list
        self.assertEqual(self.gate(compare_fails=True)[0], 2)

    def test_compare_at_its_300_file_limit_is_setup_error(self):
        self.assertEqual(self.gate(changed=tuple(f"src/{i}.py" for i in range(300)))[0], 2)

    def test_unknown_forge_is_setup_error(self):  # a typo must not fall back to GitHub silently
        self.assertEqual(self.gate(config="forge: gitlb\n")[0], 2)

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
        for path in (".agent-flow/verify.py", ".github/workflows/ci.yml", "openspec/config.yaml",
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

    def test_reasons_one_per_line(self):
        code, out = self.gate(plans=[], stop=True)
        self.assertEqual([l[:8] for l in out.splitlines()], ["BLOCKED:"] * 2)

    def test_setup_error_without_gh(self):
        self.assertEqual(self.gate(gh=False)[0], 2)


# a fake glab accepts only origin's host and maps origin's project (o/r) back to `:fullpath`
GLAB_HEADER = ("#!/bin/sh\nset -f\n[ \"$1 $2 $3\" = \"api --hostname gitlab.example.dev\" ] || { echo \"wrong host: $*\" >&2; exit 1; }\n"
               "shift 3\na=\"$*\"\ncase $a in *projects/o%2Fr*) a=\"${a%%projects/o%2Fr*}projects/:fullpath${a#*projects/o%2Fr}\";; esac\n"
               "set -- api $a\n")


def fake_glab(bindir, jobs, head="agent-flow/t", labels=(), pipe_sha="head1", pipe_status="success", plans=({"merge_commit_sha": "plan1", "sha": "x"},),
              diffs=({"old_path": "src/a.py", "new_path": "src/a.py"},), timeout=False):
    mr = {"target_branch": "main", "source_branch": head, "sha": "head1", "labels": list(labels),
          "head_pipeline": {"id": 9, "sha": pipe_sha, "status": pipe_status}}
    q = head.replace("/", "%2F") if plans is not None else "never-asked"  # plans=None: a lookup fails
    (bindir / "glab").write_text(
        GLAB_HEADER + "case \"$*\" in\n"
        "\"api projects/:fullpath/merge_requests/7\") echo '%s';;\n"
        "\"api projects/:fullpath/pipelines/9/jobs --paginate\") echo '%s';;\n"
        "\"api projects/:fullpath/merge_requests?state=merged&source_branch=%s-plan&target_branch=%s --paginate\") echo '%s';;\n"
        "\"api projects/:fullpath/repository/compare?from=plan1&to=head1\"|"
        "\"api projects/:fullpath/repository/compare?from=main&to=head1\") echo '%s';;\n"
        "*) echo 404 >&2; exit 1;;\nesac\n" % (json.dumps(mr), json.dumps(jobs), q, q, json.dumps(list(plans or ())),
                                               json.dumps({"diffs": list(diffs), "compare_timeout": timeout})))
    (bindir / "glab").chmod(0o755)


JOBS = [{"name": "test", "status": "success"}, {"name": "evidence-check", "status": "success"},
        {"name": "lint", "status": "failed", "allow_failure": True}, {"name": "deploy", "status": "skipped"}]


class GitLabGateTest(unittest.TestCase):
    def gate(self, jobs=JOBS, broken=False, **kw):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / ".agent-flow").mkdir()
        (root / ".agent-flow/config").write_text("forge: gitlab\n")
        fake_glab(root, jobs, **kw)
        if broken:
            (root / "glab").write_text("#!/bin/sh\nexit 1\n")
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": str(root)}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
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

    def test_pipeline_of_older_commit_blocks(self):
        self.assertIn("BLOCKED: CI has no passing check", self.gate(pipe_sha="old")[1])

    def test_locked_paths_after_plan_block(self):
        for d in ({"old_path": ".gitlab-ci.yml", "new_path": ".gitlab-ci.yml"},
                  {"old_path": ".agent-flow/verify.py", "new_path": "src/moved.py"}):
            code, out = self.gate(diffs=(d,))
            self.assertEqual(code, 1, d)
            self.assertIn("changes locked paths", out)

    def test_fast_forward_plan_uses_its_sha(self):
        self.assertEqual(self.gate(plans=({"merge_commit_sha": None, "sha": "plan1"},))[0], 0)

    def test_no_merged_plan_blocks(self):
        self.assertIn("no merged Plan PR", self.gate(plans=())[1])

    def test_owner_label_blocks(self):
        self.assertIn("owner-judges", self.gate(labels=["agent-flow:owner-judges"])[1])

    def test_archive_mr(self):
        files = ({"old_path": "openspec/changes/t/specs/c/spec.md", "new_path": "openspec/changes/archive/2026-11-25-t/specs/c/spec.md"},)
        # plans=None makes a Plan MR lookup fail: an archive MR, like a GitHub archive PR, never asks
        self.assertEqual(self.gate(head="agent-flow/t-archive", jobs=JOBS[:1], plans=None, diffs=files), (0, ""))

    def test_plan_mr_does_not_look_up_a_plan_mr(self):
        code, out = self.gate(head="agent-flow/t-plan", plans=None)
        self.assertEqual(code, 1)
        self.assertIn("Plan PR: the Owner merges it", out)

    def test_failed_pipeline_blocks_when_jobs_pass(self):  # a trigger (bridge) job is not in the jobs list
        code, out = self.gate(pipe_status="failed")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED: CI not green: pipeline", out)

    def test_running_pipeline_blocks(self):
        self.assertIn("CI not green: pipeline", self.gate(pipe_status="running")[1])

    def test_possibly_truncated_compare_is_setup_error(self):
        many = tuple({"old_path": f"src/{i}.py", "new_path": f"src/{i}.py"} for i in range(500))
        self.assertEqual(self.gate(diffs=many)[0], 2)

    def test_incomplete_compare_is_setup_error(self):
        self.assertEqual(self.gate(timeout=True)[0], 2)

    def test_glab_failure_is_setup_error(self):
        self.assertEqual(self.gate(broken=True)[0], 2)

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

    def test_gitlab_in_a_github_project_name_is_github(self):
        self.assertEqual(merge_gate.forge(self.repo(origin="git@github.com:o/gitlab-tools.git")), "github")

    def test_forge_from_origin_url(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "remote", "add", "origin", "git@gitlab.example.dev:o/r.git"], check=True)
        self.assertEqual(merge_gate.forge(root), "gitlab")
        subprocess.run(["git", "-C", str(root), "remote", "set-url", "origin", "git@github.com:o/r.git"], check=True)
        self.assertEqual(merge_gate.forge(root), "github")


if __name__ == "__main__":
    unittest.main()
