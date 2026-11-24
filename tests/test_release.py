"""scripts/release.py: one GitHub release per plugin version, pre-release while 0.x."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/release.py"
WORKFLOW = ROOT / ".github/workflows/release.yml"
MANIFEST = "plugins/agent-flow/.claude-plugin/plugin.json"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=cwd, check=True,
                   capture_output=True)


class ReleaseTest(unittest.TestCase):
    def repo(self, version, tags=()):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        git(d, "init", "-q", "-b", "main")
        (d / "plugins/agent-flow/.claude-plugin").mkdir(parents=True)
        (d / MANIFEST).write_text(json.dumps({"name": "agent-flow", "version": version}))
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "x")
        for t in tags:
            git(d, "tag", t)
        return d

    def run_release(self, d):
        return subprocess.run([sys.executable, str(SCRIPT), "abc123", "--dry-run"], cwd=d, capture_output=True,
                              text=True)

    def test_new_zero_version_is_a_prerelease(self):
        p = self.run_release(self.repo("0.1.0"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), 'DRY gh release create v0.1.0 --target abc123 --title agent-flow 0.1.0 '
                                           '--generate-notes --prerelease')

    def test_one_point_oh_is_a_full_release(self):
        out = self.run_release(self.repo("1.0.0")).stdout
        self.assertIn("v1.0.0", out)
        self.assertNotIn("--prerelease", out)

    def test_existing_tag_skips(self):
        p = self.run_release(self.repo("0.1.0", tags=("v0.1.0",)))
        self.assertEqual((p.returncode, p.stdout.strip()), (0, "SKIP v0.1.0 already exists"))

    def test_malformed_version_fails(self):
        self.assertEqual(self.run_release(self.repo("v0.2")).returncode, 1)

    def test_workflow_runs_after_green_ci_on_main_pushes(self):
        w = WORKFLOW.read_text()
        for t in ["workflows: [ci]", "types: [completed]", "branches: [main]", "contents: write",
                  "github.event.workflow_run.conclusion == 'success'", "github.event.workflow_run.event == 'push'",
                  "python3 scripts/release.py ${{ github.event.workflow_run.head_sha }}"]:
            self.assertIn(t, w)


if __name__ == "__main__":
    unittest.main()
