import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))
import audit  # noqa: E402
import canaries  # noqa: E402


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


class ProjectTraps(unittest.TestCase):
    """Trap reports cite the project's own code; a clean one must pass, a planted flaw must fail."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "calc.py").write_text("print(20 + 3)\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "code")
        commit = git(self.repo, "rev-parse", "HEAD")
        self.traps = self.repo / ".agent-flow/auditor/canaries"
        self.traps.mkdir(parents=True)
        head = f"Reviewer model: sonnet\nReviewed commit: {commit}\n\n"
        (self.traps / "clean.md").write_text(head + "### C1 — PASS\nCriterion: sum\nPosition: `calc.py:1`\nContains: `20 + 3`\n")
        (self.traps / "irrelevant.md").write_text(head + "### C1 — PASS\nCriterion: negative input errors\nPosition: `calc.py:1`\nContains: `20 + 3`\n")
        (self.traps / "expected.json").write_text(json.dumps({"clean.md": "passed", "irrelevant.md": "failed"}))

    def run_traps(self, judge):
        calls = []
        def fake(model, prompt):
            calls.append(model)
            return judge(prompt)
        out = io.StringIO()
        with mock.patch.object(audit, "claude", fake), contextlib.redirect_stdout(out):
            code = canaries.main(["--repo", str(self.repo)])
        return code, calls, out.getvalue()

    @staticmethod
    def fit_auditor(prompt):
        report = prompt.split("# Report under audit")[1]
        return "C1: not upheld - off point\n" if "negative input" in report else "C1: upheld - on point\n"

    def test_fit_auditor_writes_stamp_and_unlocks_audit(self):
        code, calls, out = self.run_traps(self.fit_auditor)
        self.assertEqual(code, 0, out)
        self.assertEqual(calls, ["opus", "opus"])  # every trap goes through the model, one tier above sonnet
        stamp = (self.repo / ".agent-flow/auditor/canary-stamp.txt").read_text().strip()
        rules, _ = audit.load_rules(self.repo)
        self.assertEqual(stamp, audit.stamp(self.repo, rules))
        audit.trap_gate(self.repo, rules)  # no SystemExit
        self.assertFalse(list(self.traps.glob("*.audit.md")))  # outputs stay out of the repo
        self.assertEqual(self.run_traps(self.fit_auditor)[1], [])  # unchanged: skipped, no model calls

    def test_auditor_that_misses_off_point_evidence_fails(self):
        code, _, out = self.run_traps(lambda prompt: "C1: upheld - looks fine\n")
        self.assertEqual(code, 1)
        self.assertIn("MISS irrelevant.md", out)
        self.assertFalse((self.repo / ".agent-flow/auditor/canary-stamp.txt").exists())

    def test_changed_trap_needs_a_new_pass(self):
        self.run_traps(self.fit_auditor)
        (self.traps / "clean.md").write_text((self.traps / "clean.md").read_text() + "\n")
        rules, _ = audit.load_rules(self.repo)
        with self.assertRaises(SystemExit):
            audit.trap_gate(self.repo, rules)

    def test_missing_expected_is_setup_error(self):
        (self.traps / "expected.json").unlink()
        self.assertEqual(self.run_traps(self.fit_auditor)[0], 2)


if __name__ == "__main__":
    unittest.main()
