import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))
import sandbox  # noqa: E402

CONNECT = "import socket,errno,sys\ns=socket.socket();s.settimeout(5)\ntry:\n s.connect(('1.1.1.1',443))\nexcept OSError as e:\n print(errno.errorcode.get(e.errno,'OTHER'))\nelse:\n print('CONNECTED')"


def needs(backend):
    """Run on the matching backend; skip with a reason elsewhere, fail when CI requires it."""
    def deco(cls):
        class Wrapped(cls):
            def setUp(self):
                if sandbox.available() != backend:
                    if os.environ.get("AGENT_FLOW_REQUIRE_SANDBOX") == backend:
                        self.fail(f"AGENT_FLOW_REQUIRE_SANDBOX={backend} but sandbox.available() is {sandbox.available()!r}")
                    self.skipTest(f"{backend} is not available here")
                super().setUp()
        Wrapped.__name__ = cls.__name__
        return Wrapped
    return deco


class Backend:
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()  # /var -> /private/var on macOS
        self.tree, self.outside, self.home = root / "tree", root / "outside", root / "home"
        for d in (self.tree, self.outside, self.home / ".ssh"):
            d.mkdir(parents=True)
        self.key = self.home / ".ssh/id_test"
        self.key.write_text("secret")
        patch = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patch.start()
        self.addCleanup(patch.stop)

    def run_in(self, cmd):
        return sandbox.run(cmd, self.tree, [self.tree])

    def test_write_inside_worktree_succeeds(self):
        self.assertEqual(self.run_in("echo hi > in.txt")[0], 0)
        self.assertEqual((self.tree / "in.txt").read_text(), "hi\n")

    def test_write_outside_worktree_fails(self):
        self.assertNotEqual(self.run_in(f"echo hi > {self.outside}/out.txt")[0], 0)
        self.assertFalse((self.outside / "out.txt").exists())

    def test_read_of_ssh_key_fails_but_unsandboxed_read_works(self):
        self.assertEqual(subprocess.run(["cat", str(self.key)], capture_output=True, text=True).stdout, "secret")
        code, out = self.run_in(f"cat {self.key}")
        self.assertNotEqual(code, 0)
        self.assertNotIn("secret", out)

    def test_network_connect_is_refused_not_timed_out(self):
        code, out = self.run_in(f"{shlex.quote(sys.executable)} -c {shlex.quote(CONNECT)}")
        self.assertIn(out.strip(), {"EPERM", "EACCES", "ENETUNREACH"})


@needs("seatbelt")
class Seatbelt(Backend, unittest.TestCase):
    pass


@needs("bwrap")
class Bwrap(Backend, unittest.TestCase):
    pass


class Available(unittest.TestCase):
    def test_none_when_forced(self):
        with mock.patch.dict(os.environ, {"AGENT_FLOW_SANDBOX": "none"}):
            self.assertIsNone(sandbox.available())

    def test_value_is_known(self):
        self.assertIn(sandbox.available(), {"seatbelt", "bwrap", None})


@unittest.skipUnless(os.environ.get("AGENT_FLOW_SANDBOX") == "none", "set AGENT_FLOW_SANDBOX=none to run")
class NoSandbox(unittest.TestCase):
    def test_project_command_report_is_partly_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            g = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@e.com", *a], check=True, capture_output=True, text=True).stdout.strip()
            g("init", "-q")
            (repo / "hello.py").write_text("print('hello 42')\n")
            g("add", "-A")
            g("commit", "-qm", "init")
            report = Path(tmp) / "review-1.md"
            report.write_text(f"# Review: t round 1\n\nReviewer model: opus\nReviewed commit: {g('rev-parse', 'HEAD')}\n\n"
                              "### C1 — PASS\nCriterion: x\nCommand: `python3 hello.py`\nOutput contains: `hello 42`\n")
            done = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts/audit.py"), str(report), "--repo", str(repo)],
                                  capture_output=True, text=True, env=dict(os.environ, AGENT_FLOW_SKIP_STAMP="1"))
            self.assertEqual(done.returncode, 3, done.stderr)
            self.assertEqual((Path(tmp) / "review-1.audit.md").read_text().splitlines()[-1], "Result: partly unverified")


if __name__ == "__main__":
    unittest.main()
