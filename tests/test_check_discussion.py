import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_discussion.py"
HEADINGS = ["Original words", "Finish line", "Authorizations", "Decisions", "Open questions"]


def doc(finish="- C1 it works, evidence: `make test` exits 0\n", headings=HEADINGS):
    return "# t\n\n" + "".join(f"## {h}\n\n{finish if h == 'Finish line' else 'x'}\n\n" for h in headings)


def check(text):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "discussion.md"
        p.write_text(text)
        r = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
    return r.returncode, r.stdout


class CheckDiscussion(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(check(doc())[0], 0)

    def test_evidence_on_following_line(self):
        self.assertEqual(check(doc("- C1 it works\n  Evidence: run it\n"))[0], 0)

    def test_evidence_case_insensitive(self):
        self.assertEqual(check(doc("- C1 it works, Evidence: run it\n"))[0], 0)

    def test_missing_evidence(self):
        code, out = check(doc("- C1 ok, evidence: x\n- C2 no proof here\n"))
        self.assertEqual(code, 1)
        self.assertIn("C2", out)

    def test_missing_heading(self):
        self.assertEqual(check(doc(headings=HEADINGS[:-1]))[0], 1)

    def test_wrong_order(self):
        self.assertEqual(check(doc(headings=HEADINGS[1:] + HEADINGS[:1]))[0], 1)

    def test_extra_second_level_heading(self):
        self.assertEqual(check(doc() + "## Notes\n")[0], 1)

    def test_no_finish_line_items(self):
        self.assertEqual(check(doc("nothing\n"))[0], 1)


if __name__ == "__main__":
    unittest.main()
