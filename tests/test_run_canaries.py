import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/agent-flow"
RUN = ROOT / "scripts/run_canaries.py"
NAMES = list(json.loads((PLUGIN / "auditor/canaries/expected.json").read_text()))
FAKE_CLAUDE = """#!/bin/sh
echo called >> "$CLAUDE_LOG"
if grep -q 'C2 — FAIL'; then echo 'C2: upheld'; else echo 'C3: not upheld'; fi
"""


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.plugin = self.tmp / "plugin"
        shutil.copytree(PLUGIN, self.plugin, ignore=shutil.ignore_patterns("canary-stamp.txt"))
        self.version = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())["version"]
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.log = self.tmp / "claude.log"
        (self.bin / "claude").write_text(FAKE_CLAUDE)
        (self.bin / "claude").chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}", CLAUDE_LOG=str(self.log), AGENT_FLOW_SANDBOX="none")
        self.env.pop("AGENT_FLOW_SKIP_STAMP", None)

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(RUN), "--plugin", str(self.plugin), *args], capture_output=True, text=True, env=self.env)


class RunCanaries(Case):
    def test_dry_run_lists_one_name_per_line_and_writes_nothing(self):
        done = self.run_script("--dry-run")
        self.assertEqual((done.returncode, done.stdout.splitlines()), (0, NAMES), done.stderr)
        self.assertFalse((self.plugin / "auditor/canary-stamp.txt").exists())
        self.assertFalse(self.log.exists())

    def test_all_matching_writes_stamp(self):
        done = self.run_script()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        stamp = (self.plugin / "auditor/canary-stamp.txt").read_text().splitlines()
        self.assertEqual(stamp, [f"version: {self.version}", *(f"{n}: ok" for n in NAMES)])

    def test_mismatch_writes_no_stamp(self):
        (self.plugin / "auditor/canaries/clean-all.md").write_text("# Review: x round 1\n\nReviewed commit: FIXTURE\n")
        done = self.run_script()
        self.assertEqual(done.returncode, 1)
        self.assertFalse((self.plugin / "auditor/canary-stamp.txt").exists())

    def test_matching_stamp_never_invokes_claude(self):
        self.assertEqual(self.run_script().returncode, 0)
        self.log.unlink()
        repo = self.tmp / "target"
        repo.mkdir()
        for args in (["init", "-q"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(repo), *args], check=True)
        (repo / "a.txt").write_text("hello\n")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "i"], check=True)
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        report = self.tmp / "review-1.md"
        report.write_text(f"# Review: t round 1\n\nReviewer model: opus\nReviewed commit: {sha}\n\n### C1 — PASS\nCriterion: x\nCommand: `cat a.txt`\nOutput contains: `hello`\n")
        done = subprocess.run([sys.executable, str(self.plugin / "scripts/audit.py"), str(report), "--repo", str(repo)], capture_output=True, text=True, env=self.env)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
