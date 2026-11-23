import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))
import pending_audits  # noqa: E402


class PendingAudits(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.reviews = self.repo / "docs/t/reviews"
        self.reviews.mkdir(parents=True)

    def report(self, n, audit_last=None, edit=False):
        r = self.reviews / f"review-{n}.md"
        r.write_text(f"# Review round {n}\n")
        if audit_last:
            sha = hashlib.sha256(r.read_bytes()).hexdigest()
            (self.reviews / f"review-{n}.audit.md").write_text(f"# Audit\nReport sha256: {sha}\n\n{audit_last}\n")
        if edit:
            r.write_text(r.read_text() + "edited\n")

    def test_clean(self):
        self.report(1, "Result: passed")
        self.assertEqual(pending_audits.pending(self.repo), [])

    def test_missing_failed_and_edited(self):
        for kwargs, why in [({}, "no audit"), ({"audit_last": "Result: failed"}, "did not pass"),
                            ({"audit_last": "Result: passed", "edit": True}, "changed after")]:
            self.report(1, **kwargs)
            found = pending_audits.pending(self.repo)
            self.assertEqual(len(found), 1, kwargs)
            self.assertIn(why, found[0])

    def test_only_latest_round_counts(self):
        self.report(1, "Result: failed")
        self.report(2, "Result: passed")
        self.assertEqual(pending_audits.pending(self.repo), [])
        self.report(10)
        self.assertIn("review-10.md", pending_audits.pending(self.repo)[0])


if __name__ == "__main__":
    unittest.main()
