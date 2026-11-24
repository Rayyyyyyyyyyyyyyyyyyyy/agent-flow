"""scripts/check_version.py: a change to the plugin must raise its version."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_version.py"
MANIFEST = "plugins/agent-flow/.claude-plugin/plugin.json"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=cwd, check=True,
                   capture_output=True)


class CheckVersionTest(unittest.TestCase):
    def repo(self, base_version):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        git(d, "init", "-q", "-b", "main")
        (d / "plugins/agent-flow/.claude-plugin").mkdir(parents=True)
        self.write(d, base_version)
        (d / "README.md").write_text("x\n")
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "base")
        git(d, "checkout", "-q", "-b", "pr")
        return d

    def write(self, d, v, skill="a\n"):
        body = {"name": "agent-flow"} if v is None else {"name": "agent-flow", "version": v}
        (d / MANIFEST).write_text(json.dumps(body))
        (d / "plugins/agent-flow/SKILL.md").write_text(skill)

    def check(self, d, v, skill="b\n"):
        self.write(d, v, skill)
        git(d, "add", "-A")
        git(d, "commit", "-q", "--allow-empty", "-m", "pr")
        return subprocess.run([sys.executable, str(SCRIPT), "main"], cwd=d, capture_output=True, text=True)

    def test_bump_passes(self):
        for new in ("0.1.1", "0.2.0", "1.0.0", "0.1.10"):
            self.assertEqual(self.check(self.repo("0.1.9" if new == "0.1.10" else "0.1.0"), new).returncode, 0, new)

    def test_plugin_change_without_bump_fails(self):
        for new in ("0.1.0", "0.0.9"):
            p = self.check(self.repo("0.1.0"), new)
            self.assertEqual(p.returncode, 1, new)
            self.assertIn("bump it in this PR", p.stdout)

    def test_first_version_passes(self):
        self.assertEqual(self.check(self.repo(None), "0.1.0").returncode, 0)

    def test_untouched_plugin_needs_no_bump(self):
        d = self.repo("0.1.0")
        (d / "README.md").write_text("y\n")
        git(d, "commit", "-q", "-am", "docs")
        self.assertEqual(subprocess.run([sys.executable, str(SCRIPT), "main"], cwd=d, capture_output=True).returncode, 0)

    def test_malformed_version_fails(self):
        self.assertEqual(self.check(self.repo("0.1.0"), "v0.2").returncode, 1)


if __name__ == "__main__":
    unittest.main()
