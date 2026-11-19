import contextlib
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))
import merge_gate

GREEN = [{"name": "verify", "state": "SUCCESS", "bucket": "pass"}, {"name": "x", "state": "SKIPPED", "bucket": "skipping"}]
AUDIT = "docs/t/reviews/review-%d.audit.md"


class MergeGateTest(unittest.TestCase):
    def gate(self, checks=GREEN, audits=None, stop=False, config=None, gh=True):
        """audits: {round: last line}; the diff lists every round. Returns (exit code, output)."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        audits = {1: "Result: passed"} if audits is None else audits
        for n, last in audits.items():
            p = root / (AUDIT % n)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# Audit\n" + last + "\n")
        (root / ".agent-flow").mkdir()
        if stop:
            (root / ".agent-flow/STOP").write_text("")
        if config is not None:
            (root / ".agent-flow/config").write_text(config)
        bindir = root / "bin"
        bindir.mkdir()
        if gh:
            diff = "\n".join(["src/a.py"] + [AUDIT % n for n in audits])
            (bindir / "gh").write_text(
                "#!/bin/sh\ncase \"$*\" in\n"
                "\"pr checks 7 --json name,state,bucket\") echo '%s';;\n"
                "\"pr diff 7 --name-only\") echo '%s';;\nesac\n" % (json.dumps(checks), diff))
            (bindir / "gh").chmod(0o755)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": str(bindir)}), contextlib.redirect_stdout(out):
            code = merge_gate.main(["7", "--repo-root", str(root)])
        return code, out.getvalue()

    def test_passes(self):
        self.assertEqual(self.gate()[0], 0)

    def test_failing_check_blocks(self):
        code, out = self.gate(checks=GREEN + [{"name": "bad", "state": "FAILURE", "bucket": "fail"}])
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED:", out)

    def test_pending_check_blocks(self):
        self.assertEqual(self.gate(checks=GREEN + [{"name": "p", "state": "PENDING", "bucket": "pending"}])[0], 1)

    def test_no_passing_check_blocks(self):
        self.assertEqual(self.gate(checks=[GREEN[1]])[0], 1)

    def test_failed_audit_blocks(self):
        self.assertEqual(self.gate(audits={1: "Result: failed"})[0], 1)

    def test_partly_unverified_audit_blocks(self):
        self.assertEqual(self.gate(audits={1: "Result: partly unverified"})[0], 1)

    def test_missing_audit_blocks(self):
        self.assertEqual(self.gate(audits={})[0], 1)

    def test_latest_round_decides(self):
        self.assertEqual(self.gate(audits={1: "Result: failed", 2: "Result: passed"})[0], 0)
        self.assertEqual(self.gate(audits={2: "Result: passed", 10: "Result: failed"})[0], 1)

    def test_stop_file_blocks(self):
        self.assertEqual(self.gate(stop=True)[0], 1)

    def test_merge_never_blocks(self):
        self.assertEqual(self.gate(config="x: 1\nmerge: never\n")[0], 1)

    def test_other_config_passes(self):
        self.assertEqual(self.gate(config="merge: auto\n")[0], 0)

    def test_reasons_one_per_line(self):
        code, out = self.gate(audits={1: "Result: failed"}, stop=True)
        self.assertEqual([l[:8] for l in out.splitlines()], ["BLOCKED:"] * 2)

    def test_setup_error_without_gh(self):
        self.assertEqual(self.gate(gh=False)[0], 2)


if __name__ == "__main__":
    unittest.main()
