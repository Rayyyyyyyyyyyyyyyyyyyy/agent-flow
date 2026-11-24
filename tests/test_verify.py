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
SPEC = """## ADDED Requirements

### Requirement: The thing
The system SHALL do the thing.

#### Scenario: passing criterion
- **WHEN** a
- **THEN** b
  Verify: `{py} -c "pass"`

#### Scenario: owner criterion
- **THEN** it looks right
  Owner judges: open the page and look
"""


class VerifyTest(unittest.TestCase):
    def run_verify(self, *specs, args=()):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        for i, body in enumerate(specs, 1):
            f = root / f"openspec/changes/t/specs/cap{i}/spec.md"
            f.parent.mkdir(parents=True)
            f.write_text(body.replace("{py}", PY))
        (root / "openspec/changes/archive/2026-01-01-old/specs/c").mkdir(parents=True)
        (root / "openspec/changes/archive/2026-01-01-old/specs/c/spec.md").write_text("#### Scenario: archived\n")
        out, cwd = io.StringIO(), os.getcwd()
        os.chdir(root)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                code = verify.main(list(args))
        finally:
            os.chdir(cwd)
        return code, out.getvalue()

    def test_pass_and_owner_listed(self):
        code, out = self.run_verify(SPEC)
        self.assertEqual(code, 0, out)  # the archived spec has no Verify line and is not read
        self.assertIn("PASS openspec/changes/t/specs/cap1/spec.md:6", out)
        self.assertIn("OWNER openspec/changes/t/specs/cap1/spec.md:11: owner criterion", out)

    def test_failing_command_fails(self):
        code, out = self.run_verify(SPEC + '#### Scenario: broken\n- **THEN** x\n  Verify: `{py} -c "raise SystemExit(3)"`\n')
        self.assertEqual(code, 1)
        self.assertIn("(exit 3)", out)

    def test_missing_command_fails(self):
        code, out = self.run_verify(SPEC + "#### Scenario: no evidence\n- **THEN** x\n")
        self.assertEqual(code, 1)
        self.assertIn("has no Verify command", out)

    def test_heading_ends_a_scenario(self):
        code, out = self.run_verify("#### Scenario: a\n### Requirement: next\n  Verify: `{py} -c pass`\n")
        self.assertEqual(code, 1)
        self.assertIn("has no Verify command", out)

    def test_pipes_and_shell_wrappers_rejected(self):
        for cmd in ("npm test | tail -1", "make; echo ok", "make && true", "make > out", "echo $?", "sh -c 'make'"):
            code, out = self.run_verify(f"#### Scenario: c\n  Verify: `{cmd}`\n")
            self.assertEqual(code, 1, cmd)
            self.assertIn("ERROR", out, cmd)

    def test_check_only_runs_nothing(self):
        code, out = self.run_verify('#### Scenario: c\n  Verify: `{py} -c "raise SystemExit(1)"`\n', args=["--check-only"])
        self.assertEqual((code, out), (0, ""))

    def test_check_only_still_validates(self):
        self.assertEqual(self.run_verify("#### Scenario: c\n", args=["--check-only"])[0], 1)

    def test_no_specs(self):
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
