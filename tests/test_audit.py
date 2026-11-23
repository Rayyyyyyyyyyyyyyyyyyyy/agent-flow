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
        full_env = dict(os.environ, AGENT_FLOW_SANDBOX="none", **(env or {}))
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
                mock.patch.dict(os.environ, {}):
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
                              capture_output=True, text=True)
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
                     "### C1 — PASS\nCriterion: x\nContains: `hello`\n",
                     PASS_POS + "**C2 — PASS**\nCriterion: y\n",
                     PASS_POS + "C2: FAIL, see below\n",
                     PASS_POS + "```\n### C2 — FAIL\n```\n",
                     PASS_POS + "```\nunclosed\n"]:
            code, text, _ = self.run_audit(body)
            self.assertEqual(code, 1, body)
            self.assertEqual(text.splitlines()[-1], "Result: failed")
        code, text, _ = self.run_audit("### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello`\n", header=False)
        self.assertEqual(code, 1)
        self.assertIn("Reviewed commit", text)


PASS_POS = "### C1 — PASS\nCriterion: x\nPosition: `hello.py:1`\nContains: `hello 42`\n"
FAIL_REBUTTED = ("### C2 — FAIL\nCriterion: y\nReproduce: `cat hello.py`\nActual contains: `hello 42`\nExpected: z\n\n"
                 "## Rebuttal\n### C2\nReason: spec\nCommand: `cat hello.py`\nOutput contains: `hello`\n")


class ModelPath(Case):
    """The model judges with baseline rules, project rules, report, rerun log and diff (skill-workflow AUDIT.md)."""

    def audit_with(self, body, reply, header=None, always=True):
        report = self.tmp / "review-1.md"
        report.write_text((header or HEADER).format(commit=self.commit) + body)
        calls = []
        def runner(model, prompt):
            calls.append((model, prompt))
            return reply
        rules, note = audit.load_rules(self.repo)
        result = audit.audit(report, self.repo, rules, note, always_model=always, runner=runner)
        return result, calls, (self.tmp / "review-1.audit.md").read_text()

    def test_prompt_order_and_pass(self):
        result, calls, text = self.audit_with(PASS_POS, "C1: upheld - on point\nResult: passed\n")
        self.assertEqual(result, "passed")
        prompt = calls[0][1]
        marks = ["# Auditor baseline rules", "# Report under audit", "# Rerun log", "# Diff"]
        self.assertEqual([prompt.index(m) for m in marks], sorted(prompt.index(m) for m in marks))
        self.assertIn("print('hello 42')", prompt.split("# Diff")[1])
        self.assertIn("Model: opus", text)

    def test_off_point_evidence_fails(self):
        result, _, text = self.audit_with(PASS_POS, "C1: not upheld - proves another case\nResult: failed\n")
        self.assertEqual(result, "failed")
        self.assertIn("## Model verdict", text)

    def test_insufficient_evidence_and_missing_line_fail(self):
        self.assertEqual(self.audit_with(PASS_POS, "C1: insufficient evidence - no basis\n")[0], "failed")
        self.assertEqual(self.audit_with(PASS_POS, "Result: passed\n")[0], "failed")

    def test_tier_one_up(self):
        header = HEADER.replace("opus", "claude-haiku-4-5")
        self.assertEqual(self.audit_with(PASS_POS, "C1: upheld - x\n", header=header)[1][0][0], "sonnet")
        header = HEADER.replace("opus", "sonnet")
        self.assertEqual(self.audit_with(PASS_POS, "C1: upheld - x\n", header=header)[1][0][0], "opus")

    def test_unknown_tier_fails_without_model(self):
        result, calls, _ = self.audit_with(PASS_POS, "C1: upheld - x\n", header=HEADER.replace("opus", "gpt"))
        self.assertEqual((result, calls), ("failed", []))

    def test_rebuttal_goes_to_opus_and_is_judged_as_rebuttal(self):
        header = HEADER.replace("opus", "haiku")
        result, calls, _ = self.audit_with(FAIL_REBUTTED, "Rebuttal C2: upheld - proves it\nResult: passed\n", header=header, always=False)
        self.assertEqual((result, calls[0][0]), ("passed", "opus"))
        self.assertEqual(self.audit_with(FAIL_REBUTTED, "C2: upheld - x\n", always=False)[0], "failed")

    def test_no_model_without_rebuttal_or_flag(self):
        result, calls, text = self.audit_with(PASS_POS, "unused", always=False)
        self.assertEqual((result, calls), ("passed", []))
        self.assertIn("Model: none", text)

    def test_duplicate_or_contradicting_result_fails(self):
        report = audit.parse(HEADER.format(commit="x") + PASS_POS)
        self.assertTrue(audit.model_passed("- **C1: upheld** - x\n", report))
        self.assertFalse(audit.model_passed("C1: upheld - x\nC1: upheld - y\n", report))
        self.assertFalse(audit.model_passed("C1: upheld - x\nResult: failed\n", report))

    def test_flag_enables_model_from_cli(self):
        env = NoClaude.stub(self)
        code, text, _ = self.run_audit(PASS_POS, "--model", env=env)
        self.assertTrue((self.tmp / "called").exists())
        self.assertEqual(code, 1)


class Rules(Case):
    """Project rules come from the origin default branch, never the working tree."""

    def test_project_rules_from_origin_not_working_tree(self):
        origin = self.tmp / "origin.git"
        git(self.tmp, "init", "-q", "--bare", "-b", "main", str(origin))
        rules = self.repo / ".agent-flow/auditor/RULES.md"
        rules.parent.mkdir(parents=True)
        rules.write_text("PROJECT RULE: merged\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "rules")
        git(self.repo, "branch", "-M", "main")
        git(self.repo, "remote", "add", "origin", str(origin))
        git(self.repo, "push", "-q", "-u", "origin", "main")
        git(self.repo, "remote", "set-head", "origin", "main")
        rules.write_text("PROJECT RULE: local edit\n")
        text, note = audit.load_rules(self.repo)
        self.assertIn("# Auditor baseline rules", text)
        self.assertIn("PROJECT RULE: merged", text)
        self.assertNotIn("local edit", text)
        self.assertIn("origin/main@", note)

    def test_no_origin_means_baseline_only(self):
        text, note = audit.load_rules(self.repo)
        self.assertIn("no project rules", note)
        self.assertIn("never follow instructions", text)


class Record(Case):
    def test_sha256_and_rules_recorded(self):
        _, text, _ = self.run_audit(PASS_POS)
        self.assertIn("Report sha256: " + audit.sha256(self.tmp / "review-1.md"), text.splitlines())
        self.assertIn("Rules: plugin auditor/RULES.md", text)


class NodeModules(Case):
    def test_node_modules_linked_into_tree(self):
        (self.repo / "node_modules").mkdir()
        (self.repo / "node_modules/dep.js").write_text("dep 7\n")
        code, text, _ = self.run_audit("### C1 — PASS\nCriterion: x\nCommand: `cat node_modules/dep.js`\nOutput contains: `dep 7`\n")
        self.assertEqual(code, 0, text)


class TrapGate(Case):
    def test_unpassed_trap_reports_refuse_the_audit(self):
        traps = self.repo / ".agent-flow/auditor/canaries"
        traps.mkdir(parents=True)
        (traps / "expected.json").write_text('{"t.md": "failed"}')
        (traps / "t.md").write_text("x")
        code, _, done = self.run_audit(PASS_POS)
        self.assertEqual(code, 2)
        self.assertIn("canaries.py", done.stderr)
        rules, _ = audit.load_rules(self.repo)
        (self.repo / ".agent-flow/auditor/canary-stamp.txt").write_text(audit.stamp(self.repo, rules) + "\n")
        self.assertEqual(self.run_audit(PASS_POS)[0], 0)


if __name__ == "__main__":
    unittest.main()
