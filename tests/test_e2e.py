import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import e2e

ME = e2e.OWNER


class ShimGh(unittest.TestCase):
    def deny(self, *argv, owner=ME):
        return e2e.classify_gh(list(argv), owner)

    def test_reads_allowed(self):
        self.assertIsNone(self.deny("pr", "list", "-R", "octocat/Hello-World"))
        self.assertIsNone(self.deny("api", "repos/octocat/Hello-World/issues"))

    def test_own_writes_allowed(self):
        self.assertIsNone(self.deny("pr", "create", "--title", "x", "--body", "Closes #1"))
        self.assertIsNone(self.deny("api", "-X", "POST", f"repos/{ME}/x/issues"))

    def test_foreign_writes_denied(self):
        self.assertTrue(self.deny("pr", "create", "-R", "octocat/Hello-World"))
        self.assertTrue(self.deny("issue", "comment", "1", "--repo=https://github.com/octocat/Hello-World"))
        self.assertTrue(self.deny("api", "-X", "PATCH", "repos/octocat/Hello-World/issues/1"))
        self.assertTrue(self.deny("api", "repos/octocat/Hello-World/issues", "-f", "title=x"))
        self.assertTrue(self.deny("pr", "create", owner="octocat"))

    def test_notifications_denied(self):
        self.assertTrue(self.deny("pr", "create", "--reviewer", "octocat"))
        self.assertTrue(self.deny("pr", "create", "--body", "ping @octocat"))
        self.assertIsNone(self.deny("pr", "create", "--reviewer", ME, "--body", f"@{ME} fyi"))

    def test_graphql_mutation_denied(self):
        self.assertTrue(self.deny("api", "graphql", "-f", "query=mutation { x }"))
        self.assertIsNone(self.deny("api", "graphql", "-f", "query={ viewer { login } }"))


class ShimGit(unittest.TestCase):
    urls = {"origin": f"git@github.com:{ME}/agent-flow-fixture.git", "up": "https://github.com/octocat/Hello-World.git"}

    def test_push(self):
        url = self.urls.get
        self.assertIsNone(e2e.classify_git(["push", "origin", "main"], url))
        self.assertIsNone(e2e.classify_git(["-C", "x", "status"], url))
        self.assertTrue(e2e.classify_git(["push", "up", "main"], url))
        self.assertTrue(e2e.classify_git(["push", "https://github.com/octocat/Hello-World.git"], url))
        self.assertTrue(e2e.classify_git(["push"], {"origin": ""}.get))


class Transcript(unittest.TestCase):
    def parse(self, events):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            p.write_text("\n".join(json.dumps(e) for e in events))
            return e2e.parse_transcript(p)

    def test_counts_questions_and_cost(self):
        r = self.parse([
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "AskUserQuestion"}]}},
            {"type": "result", "result": "Done. Which one?", "total_cost_usd": 1.5, "modelUsage": {"m": {"inputTokens": 1, "outputTokens": 2}}}])
        self.assertEqual((r["questions"], r["is_question"], r["cost"], r["tokens"]), (1, True, 1.5, 3))

    def test_zero_questions(self):
        r = self.parse([{"type": "result", "result": "Merged.", "total_cost_usd": 0.1}])
        self.assertTrue(e2e.zero_questions(r))

    def test_redact(self):
        self.assertEqual(e2e.redact("t=SECRET x", ["SECRET"]), "t=*** x")
        self.assertNotIn("gho_", e2e.redact("gho_" + "a" * 30, []))


if __name__ == "__main__":
    unittest.main()
