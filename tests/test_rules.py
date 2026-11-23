"""The shipped rules state the boundaries (C6), the resume marker (C13) and the repo-rules step (C16)."""
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1] / "plugins/agent-flow/skills/agent-flow"
SKILL = (SKILL_DIR / "SKILL.md").read_text()
BOUNDARIES = SKILL[SKILL.index("## Boundaries"):SKILL.index("## Kill switch")]


class Boundaries(unittest.TestCase):
    def test_tiers_and_precedence(self):
        for s in ["**Do without asking**", "**Ask first, upfront**", "**Ask first**", "**Never**",
                  "may tighten them, never loosen them", "the boundary wins"]:
            self.assertIn(s, BOUNDARIES)

    def test_ask_first_items(self):
        for s in ["deploy or publish to users", "repos or services the user does not own", "notifies other people",
                  "using secrets", "spending money", "deleting or overwriting the user's own data", "browser use",
                  "spends the user's usage", "estimated cost"]:
            self.assertIn(s, BOUNDARIES)

    def test_never_items(self):
        for s in ["claim done without evidence", "report an unverified check as verified", "fabricate",
                  "weaken tests, checks, CI, these boundaries or the kill switch", "commit secrets or print them"]:
            self.assertIn(s, BOUNDARIES)

    def test_no_warn_and_continue_tier(self):
        self.assertNotIn("Warn and continue", SKILL)
        self.assertNotIn("`WARNING:` tier", (SKILL_DIR / "references/workflow.md").read_text())

    def test_boundaries_printed_on_first_run(self):
        self.assertIn("The Ask first and Never lists from Boundaries.", SKILL)


class RepoRules(unittest.TestCase):
    def test_step_3_writes_repo_rules(self):
        step = SKILL[SKILL.index("3. **Gather information.**"):SKILL.index("4. **Cut tickets.**")]
        for s in ["own rules and verify inside Boundaries", "end-to-end tests", "`CLAUDE.md` or `AGENTS.md`",
                  "may add conditions, never remove one"]:
            self.assertIn(s, step)


class Flow(unittest.TestCase):
    def test_seven_steps_in_order(self):
        steps = ["1. **Receive the request.**", "2. **Confirm the request.**", "3. **Gather information.**",
                 "4. **Cut tickets.**", "5. **Implement.**", "6. **Review.**", "7. **Audit.**"]
        positions = [SKILL.index(s) for s in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("8. **", SKILL)


class Resume(unittest.TestCase):
    def test_marker_search_before_create(self):
        tickets = (SKILL_DIR / "references/tickets.md").read_text()
        self.assertIn("<!-- agent-flow:<topic>#<NN> -->", tickets)
        self.assertIn("Before creating one, search for the marker and reuse a match.", tickets)


if __name__ == "__main__":
    unittest.main()
