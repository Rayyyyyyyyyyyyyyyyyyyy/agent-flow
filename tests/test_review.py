import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts/review.py"
sys.path.insert(0, str(SCRIPT.parent))
import review  # noqa: E402

FAKE = """#!/usr/bin/env python3
import json, sys
a = sys.argv[1:]
json.dump({"argv": a, "sys": open(a[a.index("--system-prompt-file") + 1]).read()}, open(sys.argv[0] + ".log", "w"))
sys.stdin.read()
print(json.dumps({"result": "LGTM", "total_cost_usd": 0.456,
                  "usage": {"input_tokens": 1, "iterations": [{"input_tokens": 1, "cache_read_input_tokens": 20,
                            "cache_creation_input_tokens": 300, "output_tokens": 4000}]}}))
"""


class Review(unittest.TestCase):
    def test_lean_call_and_output(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fake = d / "claude"
            fake.write_text(FAKE)
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            (d / "reviewer.md").write_text("---\nname: reviewer\nmodel: opus\n---\nBODY TEXT\n")
            (d / "prompt.md").write_text("check it")
            # point the script at a fixture reviewer.md; the real one lives in plugins/agent-flow/agents/
            runner = f"import sys, pathlib; sys.path.insert(0, {str(SCRIPT.parent)!r}); import review; " \
                     f"review.REVIEWER = pathlib.Path({str(d / 'reviewer.md')!r}); sys.argv = ['review.py', {str(d / 'prompt.md')!r}, '--model', 'sonnet']; sys.exit(review.main())"
            env = {**os.environ, "PATH": f"{d}{os.pathsep}{os.environ['PATH']}"}
            done = subprocess.run([sys.executable, "-c", runner], env=env, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            log = json.loads((d / "claude.log").read_text())
            argv = log["argv"]
            self.assertEqual(argv[argv.index("--model") + 1], "sonnet")
            self.assertEqual(argv[argv.index("--output-format") + 1], "json")
            self.assertEqual(argv[argv.index("--tools") + 1], "Read,Write,Bash")
            self.assertIn("--strict-mcp-config", argv)
            self.assertEqual(log["sys"], "BODY TEXT\n")
            self.assertNotIn("---", log["sys"])
            self.assertEqual(done.stdout, "LGTM\n\n[review tokens: 4321; cost $0.46]\n")

    def test_body_without_frontmatter_is_unchanged(self):
        self.assertEqual(review.body("plain\n"), "plain\n")


if __name__ == "__main__":
    unittest.main()
