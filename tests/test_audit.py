import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"
sys.path.insert(0, str(SCRIPTS))
import audit  # noqa: E402
import sandbox  # noqa: E402

VERSION = json.loads((SCRIPTS.parent / ".claude-plugin/plugin.json").read_text())["version"]


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


HEADER = "# Review: t round 1\n\nReviewer model: opus\nReviewed commit: {commit}\n\n"


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.repo = self.tmp / "target"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "hello.py").write_text("print('hello 42')\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "init")
        self.commit = git(self.repo, "rev-parse", "HEAD")

    def run_audit(self, body, *flags, env=None, header=True):
        report = self.tmp / "review-1.md"
        report.write_text((HEADER.format(commit=self.commit) if header else "") + body)
        full_env = dict(os.environ, AGENT_FLOW_SKIP_STAMP="1", AGENT_FLOW_SANDBOX="none", **(env or {}))
        done = subprocess.run([sys.executable, str(SCRIPTS / "audit.py"), str(report), "--repo", str(self.repo), *flags],
                              capture_output=True, text=True, env=full_env)
        out = self.tmp / "review-1.audit.md"
        return done.returncode, (out.read_text() if out.exists() else ""), done


class Position(Case):
    def test_position_contains(self):
        code, text, _ = self.run_audit("### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello 42`\n")
        self.assertEqual(code, 0)
        self.assertEqual(text.splitlines()[-1], "Result: passed")

    def test_position_runs_no_process(self):
        tree = self.tmp / "tree"
        tree.mkdir()
        (tree / "hello.py").write_text("print('hello 42')\n")
        with mock.patch.object(audit.subprocess, "run", side_effect=AssertionError("process started")):
            self.assertIn("hello 42", audit.look("hello.py:1", tree))
            self.assertIn("not found", audit.look("../x:1", tree))
        # Checked at the reviewed commit, not the working tree.
        (self.repo / "hello.py").write_text("changed\n")
        self.assertEqual(self.run_audit("### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `changed`\n")[0], 1)


class Allowlist(Case):
    def test_allowlisted_command_runs_without_sandbox(self):
        code, text, _ = self.run_audit("### C1 — PASS\nCriterion: x\nCommand: `cat hello.py`\nOutput contains: `hello 42`\n")
        self.assertEqual(code, 0, text)

    def test_allowlist_decision(self):
        for cmd in ["cat a", "git log -1", "git diff HEAD", "grep -n x a", "test -f a", "ls", "head -1 a", "tail a", "wc -l a", "git grep x"]:
            self.assertTrue(audit.readonly(cmd), cmd)
        for cmd in ["python3 hello.py", "git commit -m x", "git push", "sed -i s/a/b/ f", "git"]:
            self.assertFalse(audit.readonly(cmd), cmd)

    def test_bypass_attempts_are_project_commands(self):
        for cmd in ["cat hello.py; id", "cat a | wc", "cat $(id)", "cat `id`", "cat a > b", "ls && id", "cat /etc/passwd",
                    "cat ../x", "git diff --output=x", "git log -O/bin/sh", "git -c core.pager=id log", "cat a\nid"]:
            self.assertFalse(audit.readonly(cmd), cmd)

    def test_bypass_writes_nothing(self):
        code, _, _ = self.run_audit("### C1 — PASS\nCriterion: x\nCommand: `git diff --output=pwned HEAD`\nOutput contains: `zz`\n")
        self.assertEqual(code, 3)
        self.assertFalse(list(self.tmp.rglob("pwned")))


class Unverified(Case):
    def test_project_command_without_sandbox_is_unverified(self):
        code, text, _ = self.run_audit("### C1 — PASS\nCriterion: x\nCommand: `python3 hello.py`\nOutput contains: `hello 42`\n")
        self.assertEqual(code, 3)
        self.assertEqual(text.splitlines()[-1], "Result: partly unverified")
        self.assertIn("## Run these yourself", text)
        self.assertIn("python3 hello.py", text.split("## Run these yourself")[1])

    def test_project_command_uses_sandbox_when_available(self):
        calls = []
        def fake_run(cmd, cwd, writable, timeout=600):
            calls.append((cmd, cwd, writable))
            return 0, "hello 42\n"
        report = self.tmp / "r.md"
        report.write_text(HEADER.format(commit=self.commit) + "### C1 — PASS\nCriterion: x\nCommand: `python3 hello.py`\nOutput contains: `hello 42`\n")
        with mock.patch.object(sandbox, "available", return_value="seatbelt"), mock.patch.object(sandbox, "run", fake_run), \
                mock.patch.dict(os.environ, {"AGENT_FLOW_SKIP_STAMP": "1"}):
            code = audit.main([str(report), "--repo", str(self.repo)])
        self.assertEqual(code, 0)
        self.assertEqual(calls[0][0], "python3 hello.py")

    def test_available_honors_none(self):
        with mock.patch.dict(os.environ, {"AGENT_FLOW_SANDBOX": "none"}):
            self.assertIsNone(sandbox.available())
            with self.assertRaises(RuntimeError):
                sandbox.run("true", Path("."), [])


class Unsandboxed(Case):
    def test_unsandboxed_runs_and_warns_on_second_line(self):
        code, text, _ = self.run_audit("### C1 — PASS\nCriterion: x\nCommand: `python3 hello.py`\nOutput contains: `hello 42`\n", "--unsandboxed")
        self.assertEqual(code, 0, text)
        lines = text.splitlines()
        self.assertEqual(lines[0], "# Audit: review-1.md")
        self.assertEqual(lines[1], "WARNING: project commands ran without a sandbox")


class Version(Case):
    def test_version_recorded(self):
        _, text, _ = self.run_audit("### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello`\n")
        self.assertIn(f"Plugin version: {VERSION}", text)

    def test_stamp_mismatch_exits_2(self):
        env = {k: v for k, v in os.environ.items() if k != "AGENT_FLOW_SKIP_STAMP"}
        report = self.tmp / "r.md"
        report.write_text(HEADER.format(commit=self.commit) + "### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello`\n")
        plugin = self.tmp / "plugin"
        shutil.copytree(SCRIPTS.parent, plugin)
        (plugin / "auditor/canary-stamp.txt").write_text("version: 9.9.9\n")
        done = subprocess.run([sys.executable, str(plugin / "scripts/audit.py"), str(report), "--repo", str(self.repo)], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 2)
        self.assertIn(f"canary stamp is for 9.9.9, plugin is {VERSION}", done.stderr)


class NoClaude(Case):
    def stub(self):
        d = self.tmp / "bin"
        d.mkdir()
        (d / "claude").write_text(f"#!/bin/sh\ntouch {self.tmp}/called\nexit 1\n")
        (d / "claude").chmod(0o755)
        return {"PATH": f"{d}{os.pathsep}{os.environ['PATH']}"}

    def test_no_claude_on_deterministic_path(self):
        body = ("### C1 — PASS\nCriterion: x\nCommand: `cat hello.py`\nOutput contains: `hello 42`\n"
                "### C2 — FAIL\nCriterion: y\nReproduce: `cat hello.py`\nActual contains: `nope`\nExpected: z\n")
        env = self.stub()
        self.run_audit(body, env=env)
        self.run_audit("### C1 — PASS\nCriterion: x\nCommand: `cat hello.py`\nOutput contains: `hello 42`\n", env=env)
        self.assertFalse((self.tmp / "called").exists())

    def test_claude_called_for_rebuttal(self):
        body = ("### C2 — FAIL\nCriterion: y\nReproduce: `cat hello.py`\nActual contains: `hello 42`\nExpected: z\n\n"
                "## Rebuttal\n### C2\nReason: spec\nCommand: `cat hello.py`\nOutput contains: `hello`\n")
        code, text, _ = self.run_audit(body, env=self.stub())
        self.assertTrue((self.tmp / "called").exists())
        self.assertEqual(code, 1)


class ExitCodes(Case):
    def test_exit_codes(self):
        self.assertEqual(self.run_audit("### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello`\n")[0], 0)
        self.assertEqual(self.run_audit("### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `absent`\n")[0], 1)
        self.assertEqual(self.run_audit("### C1 — PASS\nCriterion: x\nCommand: `python3 hello.py`\nOutput contains: `hello`\n")[0], 3)
        code, _, done = self.run_audit("")
        self.assertEqual(code, 1)  # no items: malformed
        done = subprocess.run([sys.executable, str(SCRIPTS / "audit.py"), str(self.tmp / "missing.md"), "--repo", str(self.repo)],
                              capture_output=True, text=True, env=dict(os.environ, AGENT_FLOW_SKIP_STAMP="1"))
        self.assertEqual(done.returncode, 2)

    def test_failure_beats_unverified(self):
        body = ("### C1 — PASS\nCriterion: x\nCommand: `python3 hello.py`\nOutput contains: `hello`\n"
                "### C2 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `absent`\n")
        self.assertEqual(self.run_audit(body)[0], 1)

    def test_bad_commit_exits_2(self):
        self.commit = "0" * 40
        self.assertEqual(self.run_audit("### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello`\n")[0], 2)

    def test_malformed_reports_fail_with_reason(self):
        for body in ["### C1 — PASS\nCriterion: x\n",
                     "### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\n",
                     "### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `h`\n",
                     "### C1 - PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello`\n",
                     "### C1 — UNKNOWN\nCriterion: x\n",
                     "### C1 — PASS\nCriterion: x\nContains: `hello`\n"]:
            code, text, _ = self.run_audit(body)
            self.assertEqual(code, 1, body)
            self.assertEqual(text.splitlines()[-1], "Result: failed")
        code, text, _ = self.run_audit("### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello`\n", header=False)
        self.assertEqual(code, 1)
        self.assertIn("Reviewed commit", text)


if __name__ == "__main__":
    unittest.main()
