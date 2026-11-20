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

GREEN = [{"name": "verify", "state": "SUCCESS", "bucket": "pass"}]
AUDIT = "docs/t/reviews/review-1.audit.md"


def git(cwd, *args):
    return subprocess.run(("git",) + args, cwd=cwd, capture_output=True, text=True, check=True).stdout


class LandTest(unittest.TestCase):
    def land(self, refuse_merge=False, behind=False, audit="Result: passed"):
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
        (root / AUDIT).parent.mkdir(parents=True)
        (root / AUDIT).write_text("# Audit\n" + audit + "\n")
        bindir.mkdir()
        log, merged = tmp / "gh.log", tmp / "merged"
        (bindir / "gh").write_text(
            "#!/bin/sh\necho \"$*\" >> %s\ncase \"$*\" in\n"
            "\"pr view 7 --json headRefName,mergeStateStatus\") echo '{\"headRefName\":\"t/01\",\"mergeStateStatus\":\"%s\"}';;\n"
            "\"pr checks 7 --json name,state,bucket\") echo '%s';;\n"
            "\"pr diff 7 --name-only\") echo '%s';;\n"
            "\"pr merge 7 --merge\") %s;;\n"
            "\"pr view 7 --json state\") if [ -f %s ]; then echo '{\"state\":\"MERGED\"}'; else echo '{\"state\":\"OPEN\"}'; fi;;\n"
            "esac\n" % (log, "BEHIND" if behind else "CLEAN", json.dumps(GREEN), AUDIT,
                        "echo refused >&2; exit 1" if refuse_merge else "touch " + str(merged), merged))
        (bindir / "gh").chmod(0o755)
        out = io.StringIO()
        env = {"PATH": str(bindir) + os.pathsep + os.environ["PATH"]}
        with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = land.main(["7", "--worktree", str(wt), "--repo-root", str(root)])
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

    def test_merge_refused_touches_nothing(self):
        code, out = self.land(refuse_merge=True)
        self.assertEqual(code, 1)
        self.assertIn("refused", out)
        self.assertTrue(self.wt.exists())
        self.assertTrue(all(self.branches()))

    def test_gate_blocked_never_merges(self):
        code, out = self.land(audit="Result: failed")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED:", out)
        self.assertNotIn("pr merge", self.log)
        self.assertTrue(self.wt.exists())

    def test_behind_updates_branch_and_waits(self):
        code, _ = self.land(behind=True)
        self.assertEqual(code, 0)
        self.assertLess(self.log.index("pr update-branch 7"), self.log.index("pr checks 7 --watch"))
        self.assertLess(self.log.index("pr checks 7 --watch"), self.log.index("pr merge 7 --merge"))

    def test_setup_error_without_gh(self):
        with mock.patch.dict(os.environ, {"PATH": ""}), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(land.main(["7", "--repo-root", tempfile.gettempdir()]), 2)


if __name__ == "__main__":
    unittest.main()
