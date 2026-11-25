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
import land

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_merge_gate import GLAB_HEADER  # noqa: E402

GREEN = [{"name": "verify", "state": "SUCCESS", "bucket": "pass"}, {"name": "evidence-check", "state": "SUCCESS", "bucket": "pass"}]


def git(cwd, *args):
    return subprocess.run(("git",) + args, cwd=cwd, capture_output=True, text=True, check=True).stdout


class LandTest(unittest.TestCase):
    def land(self, refuse_merge=False, behind=False, owner_label=False, stop=False, silent_merge=False, root_is_wt=False, delete_source=False):
        """Real git repo + bare origin + worktree on branch t/01; fake gh. Returns (code, out, env)."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        origin, root, wt, bindir = tmp / "origin.git", tmp / "repo", tmp / "wt", tmp / "bin"
        git(tmp, "init", "--bare", "-b", "main", str(origin))
        git(tmp, "init", "-b", "main", str(root))
        git(root, "config", "user.email", "a@b.c")
        git(root, "config", "user.name", "x")
        git(root, "commit", "--allow-empty", "-m", "init")
        git(root, "remote", "add", "origin", str(origin))
        git(root, "push", "origin", "main")
        git(root, "worktree", "add", str(wt), "-b", "t/01")
        git(wt, "push", "origin", "t/01")
        if stop:
            (root / ".agent-flow").mkdir()
            (root / ".agent-flow/STOP").write_text("")
        bindir.mkdir()
        log, merged = tmp / "gh.log", tmp / "merged"
        (bindir / "gh").write_text(
            "#!/bin/sh\necho \"$*\" >> %s\ncase \"$*\" in\n"
            "\"pr view 7 --json headRefName,mergeStateStatus\") echo '{\"headRefName\":\"t/01\",\"mergeStateStatus\":\"%s\"}';;\n"
            "\"pr checks 7 --json name,state,bucket\") echo '%s';;\n"
            "\"pr view 7 --json baseRefName,headRefName,headRefOid,labels\") echo '%s';;\n"
            "\"pr list --base t/01 --head t/01-plan --state merged --json mergeCommit\") echo '[{\"mergeCommit\":{\"oid\":\"p1\"}}]';;\n"
            "\"api repos/{owner}/{repo}/compare/p1...abc123 --jq .files[].filename\") echo src/a.py;;\n"
            "\"pr view 7 --json headRefOid\") echo '{\"headRefOid\":\"abc123\"}';;\n"
            "\"pr merge 7 --merge --match-head-commit abc123\") %s;;\n"
            "\"pr view 7 --json state\") if [ -f %s ]; then echo '{\"state\":\"MERGED\"}'; else echo '{\"state\":\"OPEN\"}'; fi;;\n"
            "esac\n" % (log, "BEHIND" if behind else "CLEAN", json.dumps(GREEN), json.dumps({"baseRefName": "main", "headRefName": "t/01", "headRefOid": "abc123", "labels": [{"name": "agent-flow:owner-judges"}] if owner_label else []}),
                        "echo refused >&2; exit 1" if refuse_merge else "true" if silent_merge else "touch " + str(merged)
                        + (" && git --git-dir=%s update-ref -d refs/heads/t/01" % origin if delete_source else ""), merged))
        (bindir / "gh").chmod(0o755)
        out = io.StringIO()
        env = {"PATH": str(bindir) + os.pathsep + os.environ["PATH"]}
        with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = land.main(["7", "--worktree", str(wt), "--repo-root", str(wt if root_is_wt else root)])
        self.root, self.wt, self.origin = root, wt, origin
        self.log = log.read_text() if log.exists() else ""
        return code, out.getvalue()

    def branches(self):
        return (git(self.root, "branch", "--list", "t/01").strip(),
                git(self.root, "ls-remote", "--heads", str(self.origin), "t/01").strip())

    def test_merged_then_cleaned(self):
        code, _ = self.land()
        self.assertEqual(code, 0)
        self.assertFalse(self.wt.exists())
        self.assertEqual(self.branches(), ("", ""))

    def test_repo_root_is_the_removed_worktree(self):
        code, out = self.land(root_is_wt=True)
        self.assertEqual(code, 0, out)
        self.assertFalse(self.wt.exists())
        self.assertEqual(self.branches(), ("", ""))

    def test_merge_refused_touches_nothing(self):
        code, out = self.land(refuse_merge=True)
        self.assertEqual(code, 1)
        self.assertIn("refused", out)
        self.assertTrue(self.wt.exists())
        self.assertTrue(all(self.branches()))

    def test_gate_blocked_never_merges(self):
        code, out = self.land(owner_label=True)
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED:", out)
        self.assertNotIn("pr merge", self.log)
        self.assertTrue(self.wt.exists())

    def test_behind_updates_branch_and_waits(self):
        code, _ = self.land(behind=True)
        self.assertEqual(code, 0)
        self.assertLess(self.log.index("pr update-branch 7"), self.log.index("pr checks 7 --watch"))
        self.assertLess(self.log.index("pr checks 7 --watch"), self.log.index("pr merge 7 --merge --match-head-commit abc123"))

    def test_head_read_before_gate(self):  # a commit pushed after the gate ran must not be merged
        self.assertEqual(self.land()[0], 0)
        self.assertLess(self.log.index("pr view 7 --json headRefOid"), self.log.index("pr checks 7 --json name,state,bucket"))

    def test_source_branch_deleted_by_the_merge(self):  # GitHub auto-delete head branches
        code, out = self.land(delete_source=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.branches(), ("", ""))

    def test_stop_file_blocks_before_update_branch(self):
        code, _ = self.land(behind=True, stop=True)
        self.assertEqual(code, 1)
        self.assertNotIn("update-branch", self.log)
        self.assertNotIn("pr merge", self.log)

    def test_merge_ok_but_not_merged_deletes_nothing(self):
        code, out = self.land(silent_merge=True)
        self.assertEqual(code, 1)
        self.assertIn("FAILED:", out)
        self.assertTrue(self.wt.exists())
        self.assertTrue(all(self.branches()))

    def test_gitlab_merged_then_cleaned(self):
        code, out = self.land_gitlab()
        self.assertEqual(code, 0, out)
        self.assertIn("api projects/:fullpath/merge_requests/7/merge -X PUT -f sha=abc123", self.log)
        self.assertFalse(self.wt.exists())
        self.assertEqual(self.branches(), ("", ""))

    def test_gitlab_merge_refused_touches_nothing(self):
        code, out = self.land_gitlab(refuse=True)
        self.assertEqual(code, 1)
        self.assertIn("FAILED: merge", out)
        self.assertTrue(self.wt.exists())
        self.assertTrue(all(self.branches()))

    def test_gitlab_deleted_source_branch_on_merge(self):  # project default "Delete source branch"
        code, out = self.land_gitlab(delete_source=True)
        self.assertEqual(code, 0, out)
        self.assertFalse(self.wt.exists())
        self.assertEqual(self.branches(), ("", ""))

    def land_gitlab(self, refuse=False, delete_source=False):
        """Like land(), with `forge: gitlab` and a fake glab; the gate's MR reads are canned."""
        self.land(refuse_merge=True)  # builds repo, origin, worktree; this gh run refuses and touches nothing
        tmp = self.root.parent
        (self.root / ".agent-flow").mkdir(exist_ok=True)
        (self.root / ".agent-flow/config").write_text("forge: gitlab\n")
        log, merged = tmp / "glab.log", tmp / "glab-merged"
        mr = {"target_branch": "main", "source_branch": "t/01", "sha": "abc123", "labels": [], "head_pipeline": {"id": 9, "sha": "abc123", "status": "success"}}
        jobs = [{"name": "test", "status": "success"}, {"name": "evidence-check", "status": "success"}]
        (tmp / "bin/glab").write_text(
            GLAB_HEADER + "echo \"$*\" >> %s\ncase \"$*\" in\n"
            "\"api projects/:fullpath/merge_requests/7\") if [ -f %s ]; then s=merged; else s=opened; fi; echo '%s' | sed s/STATE/$s/;;\n"
            "\"api projects/:fullpath/pipelines/9/jobs --paginate\") echo '%s';;\n"
            "*merge_requests?state=merged*) echo '[{\"merge_commit_sha\":\"p1\",\"sha\":\"x\"}]';;\n"
            "*repository/compare*) echo '{\"diffs\":[{\"old_path\":\"src/a.py\",\"new_path\":\"src/a.py\"}]}';;\n"
            "\"api projects/:fullpath/merge_requests/7/merge -X PUT -f sha=abc123\") %s;;\n"
            "*) exit 1;;\nesac\n" % (log, merged, json.dumps({**mr, "state": "STATE"}), json.dumps(jobs),
                                     "echo 405 >&2; exit 1" if refuse else "touch " + str(merged)
                                     + (" && git --git-dir=%s update-ref -d refs/heads/t/01" % self.origin if delete_source else "")
                                     + " && echo '{}'"))
        (tmp / "bin/glab").chmod(0o755)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": str(tmp / "bin") + os.pathsep + os.environ["PATH"]}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out), \
                mock.patch.object(land.merge_gate, "origin", return_value=("gitlab.example.dev", "o/r")):
            code = land.main(["7", "--worktree", str(self.wt), "--repo-root", str(self.root)])
        self.log = log.read_text() if log.exists() else ""
        return code, out.getvalue()

    def test_setup_error_without_gh(self):
        with mock.patch.dict(os.environ, {"PATH": ""}), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(land.main(["7", "--repo-root", tempfile.gettempdir()]), 2)


if __name__ == "__main__":
    unittest.main()
