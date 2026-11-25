import contextlib
import io
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))
import doctor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_merge_gate import GLAB_HEADER  # noqa: E402

GIT = 'case "$*" in "remote get-url origin") echo git@github.com:o/r.git;; esac'
GH = '''case "$*" in
"auth status") echo "Token scopes: 'repo', 'workflow'";;
*permissions.push*) echo true;;
*.private*) echo false;;
esac'''
OPENSPEC = 'case "$*" in "list --json") echo \'{"changes":[]}\';; *) exit 1;; esac'
GOOD = {"git": GIT, "gh": GH, "openspec": OPENSPEC}


class DoctorTest(unittest.TestCase):
    def doctor(self, **tools):
        """Run doctor with fake executables (overrides of GOOD; None removes) as the only PATH."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        for name, body in {**GOOD, **tools}.items():
            if body is None:
                continue
            p = Path(d) / name
            p.write_text("#!/bin/sh\n" + body + "\n")
            p.chmod(p.stat().st_mode | stat.S_IEXEC)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": d}), contextlib.redirect_stdout(out):
            code = doctor.main()
        return code, out.getvalue()

    def test_all_good(self):
        code, out = self.doctor()
        self.assertEqual((code, out), (0, ""))

    def test_git_missing(self):
        code, out = self.doctor(git=None)
        self.assertEqual(code, 1)
        self.assertIn("FAIL git", out)
        self.assertIn("Fix:", out)

    def test_gh_missing(self):
        code, out = self.doctor(gh=None)
        self.assertEqual(code, 1)
        self.assertIn("FAIL gh not installed", out)

    def test_gh_not_logged_in(self):
        code, out = self.doctor(gh='case "$*" in "auth status") exit 1;; esac')
        self.assertEqual(code, 1)
        self.assertIn("gh auth login", out)

    def test_no_origin(self):
        code, out = self.doctor(git="exit 1")
        self.assertEqual(code, 1)
        self.assertIn("FAIL origin", out)

    def test_no_push_access(self):
        code, out = self.doctor(gh=GH.replace("echo true", "echo false"))
        self.assertEqual(code, 1)
        self.assertIn("FAIL push access", out)

    def test_openspec_missing(self):
        code, out = self.doctor(openspec=None)
        self.assertEqual(code, 1)
        self.assertIn("FAIL openspec not installed", out)
        self.assertIn("npm install -g @fission-ai/openspec", out)

    def test_openspec_not_initialised(self):
        code, out = self.doctor(openspec="exit 1")
        self.assertEqual(code, 1)
        self.assertIn("FAIL OpenSpec cannot read this repo", out)
        self.assertIn("openspec init", out)

    def test_python_too_old(self):
        with mock.patch.object(doctor.sys, "version_info", (3, 10, 0)):
            code, out = self.doctor()
        self.assertEqual(code, 1)
        self.assertIn("FAIL python", out)

    def test_no_branch_protection_warns_only(self):
        gh = GH.replace("echo false", "echo true").replace(
            "esac", '*plan.name*) echo free;;\nesac'
        )
        code, out = self.doctor(gh=gh)
        self.assertEqual(code, 0)
        self.assertIn("merge gate script is the only guard", out)

    def test_https_remote_without_workflow_scope_warns(self):
        git = GIT.replace("git@github.com:o/r.git", "https://github.com/o/r.git")
        gh = GH.replace(", 'workflow'", "")
        code, out = self.doctor(git=git, gh=gh)
        self.assertEqual(code, 0)
        self.assertIn("gh auth refresh -s workflow", out)


GITLAB = {"git": GIT.replace("github.com", "gitlab.example.dev"), "gh": None,
          "glab": GLAB_HEADER.replace("#!/bin/sh\n", "").replace('[ "$1 $2 $3"', '[ "$*" = "auth status --hostname gitlab.example.dev" ] && exit 0\n[ "$1 $2 $3"') + 'case "$*" in "auth status") true;; "api user") echo \'{"id": 5}\';; '
                  '"api projects/:fullpath") echo \'{"merge_method": "merge", "default_branch": "main", '
                  '"permissions": {"project_access": null, "group_access": null}}\';; '
                  '"api projects/:fullpath/members/all/5") echo \'{"access_level": 40}\';; '
                  '*) exit 1;; esac'}


class GitLabDoctorTest(DoctorTest):
    def doctor(self, **tools):
        return super().doctor(**{**GITLAB, **tools})

    def test_all_good(self):  # role inherited from a parent group: `permissions` null, members/all has it
        self.assertEqual(self.doctor(), (0, ""))

    def test_glab_missing(self):
        self.assertIn("FAIL glab not installed", self.doctor(glab=None)[1])

    def test_no_push_access(self):
        code, out = self.doctor(glab=GITLAB["glab"].replace('{"access_level": 40}', '{"access_level": 20}'))
        self.assertEqual(code, 1)
        self.assertIn("FAIL push access", out)

    def test_fast_forward_merge_method_fails(self):
        code, out = self.doctor(glab=GITLAB["glab"].replace('"merge"', '"ff"'))
        self.assertEqual(code, 1)
        self.assertIn("merge method is ff", out)

    # GitHub-only checks
    test_gh_missing = test_gh_not_logged_in = test_no_branch_protection_warns_only = None
    test_https_remote_without_workflow_scope_warns = test_no_origin = None


if __name__ == "__main__":
    unittest.main()
