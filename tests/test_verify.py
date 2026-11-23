import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))
import verify

PY = sys.executable
TICKET = """# Add the thing

Status: open
Blocked by: none

## Acceptance

- [ ] passing criterion
  Verify: `{py} -c "pass"`
- [ ] owner criterion
  Owner judges: open the page and look
"""


class VerifyTest(unittest.TestCase):
    def run_verify(self, *tickets, args=()):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        d = root / "docs/t/tickets"
        d.mkdir(parents=True)
        for i, body in enumerate(tickets, 1):
            (d / f"{i:02d}-x.md").write_text(body.replace("{py}", PY))
        out, cwd = io.StringIO(), os.getcwd()
        os.chdir(root)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                code = verify.main(list(args))
        finally:
            os.chdir(cwd)
        return code, out.getvalue()

    def test_pass_and_owner_listed(self):
        code, out = self.run_verify(TICKET)
        self.assertEqual(code, 0, out)
        self.assertIn("PASS docs/t/tickets/01-x.md:8", out)
        self.assertIn("OWNER docs/t/tickets/01-x.md:10: owner criterion", out)

    def test_failing_command_fails(self):
        code, out = self.run_verify(TICKET + '- [ ] broken\n  Verify: `{py} -c "raise SystemExit(3)"`\n')
        self.assertEqual(code, 1)
        self.assertIn("(exit 3)", out)

    def test_missing_command_fails(self):
        code, out = self.run_verify(TICKET + "- [ ] no evidence\n")
        self.assertEqual(code, 1)
        self.assertIn("has no Verify command", out)

    def test_heading_ends_a_criterion(self):
        code, out = self.run_verify("- [ ] a\n## Notes\n  Verify: `{py} -c pass`\n")
        self.assertEqual(code, 1)
        self.assertIn("has no Verify command", out)

    def test_pipes_and_shell_wrappers_rejected(self):
        for cmd in ("npm test | tail -1", "make; echo ok", "make && true", "make > out", "echo $?", "sh -c 'make'"):
            code, out = self.run_verify(f"- [ ] c\n  Verify: `{cmd}`\n")
            self.assertEqual(code, 1, cmd)
            self.assertIn("ERROR", out, cmd)

    def test_check_only_runs_nothing(self):
        code, out = self.run_verify('- [ ] c\n  Verify: `{py} -c "raise SystemExit(1)"`\n', args=["--check-only"])
        self.assertEqual((code, out), (0, ""))

    def test_check_only_still_validates(self):
        self.assertEqual(self.run_verify("- [ ] c\n", args=["--check-only"])[0], 1)

    def test_no_tickets(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        cwd = os.getcwd()
        os.chdir(root)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(verify.main([]), 2)
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
