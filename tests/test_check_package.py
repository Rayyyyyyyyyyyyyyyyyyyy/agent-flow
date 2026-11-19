import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_package.py"
HANDLE = "Rayyyyyyyyyyyyyyyyyyyy"


def run(files):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for name, text in files.items():
            f = root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        r = subprocess.run([sys.executable, str(SCRIPT), d], capture_output=True, text=True)
        return r.returncode, r.stdout


class CheckPackage(unittest.TestCase):
    def fails(self, files, rule):
        code, out = run(files)
        self.assertEqual(code, 1, out)
        self.assertRegex(out, rf"^\S+:\d+: {rule}$")

    def test_clean(self):
        self.assertEqual(run({"plugins/agent-flow/skills/agent-flow/SKILL.md": "hello\n"})[0], 0)

    def test_third_party_skill(self):
        self.fails({"plugins/agent-flow/skills/other/SKILL.md": "x\n"}, "third-party skill")

    def test_users_path(self):
        self.fails({"plugins/agent-flow/a.md": "/Users/bob\n"}, "personal path /Users/")

    def test_home_path(self):
        self.fails({"plugins/agent-flow/a.md": "/home/bob\n"}, "personal path /home/<name>")

    def test_email(self):
        self.fails({"plugins/agent-flow/a.md": "a@b.com\n"}, "email address")

    def test_forbidden_word(self):
        self.fails({"plugins/agent-flow/a.md": "use RTK\n"}, "forbidden word")

    def test_timezone(self):
        self.fails({"plugins/agent-flow/a.md": "Asia/Taipei\n"}, "Asia/Taipei")

    def test_cjk(self):
        self.fails({"plugins/agent-flow/a.md": "中文\n"}, "CJK character")

    def test_handle(self):
        self.fails({"scripts/x.py": HANDLE + "\n"}, "GitHub handle")

    def test_handle_allowed_in_readme(self):
        self.assertEqual(run({"README.md": HANDLE + "\n"})[0], 0)


if __name__ == "__main__":
    unittest.main()
