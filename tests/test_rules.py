"""The shipped rules state the boundaries (C6), resume (C13), cost (C14), repo rules (C16),
Environment alignment (C17), propose, confirm and Plan PR (C18), locks (C19), Evidence check (C20),
owner-judged items (C22), archive (C23)."""
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1] / "plugins/agent-flow/skills/agent-flow"
SKILL = (SKILL_DIR / "SKILL.md").read_text()
WORKFLOW = (SKILL_DIR / "references/workflow.md").read_text()
BOUNDARIES = SKILL[SKILL.index("## Boundaries"):SKILL.index("## Kill switch")]


def step(n):
    return SKILL[SKILL.index(f"{n}. **"):SKILL.index(f"{n + 1}. **") if n < 9 else SKILL.index("## Locks")]


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
                  "weaken tests, checks, CI, these boundaries or the kill switch", "change a locked path outside a Plan PR",
                  "commit secrets or print them"]:
            self.assertIn(s, BOUNDARIES)

    def test_boundaries_printed_on_first_run(self):
        self.assertIn("The Ask first and Never lists from Boundaries.", SKILL)


class Method(unittest.TestCase):
    def test_steps_in_order(self):
        steps = ["0. **Align the environment.**", "1. **Receive the request.**", "2. **Gather facts.**",
                 "3. **Propose and open the Plan PR.**", "4. **Confirm with the user.**", "5. **Apply.**",
                 "6. **Review.**", "7. **Evidence check.**", "8. **Merge.**", "9. **Archive.**"]
        positions = [SKILL.index(s) for s in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("10. **", SKILL)

    def test_openspec_commands(self):
        for n, cmd in [(1, "`/opsx:explore`"), (3, "`/opsx:propose <topic>`"), (5, "`/opsx:apply <topic>`"),
                       (9, "`/opsx:archive <topic>`")]:
            self.assertIn(cmd, step(n))
        self.assertIn("the user decides when the discussion moves on to propose", step(1))
        self.assertIn("A goal goes straight to its finish line", step(1))

    def test_environment_alignment(self):  # C17
        s = step(0)
        for t in ["OpenSpec covers explore, propose, apply and archive", "actually has, from any source", "one-line reason", "`disable-model-invocation: true`",
                  "reading its `SKILL.md`", "fallback", "`.agent-flow/skills.md`"]:
            self.assertIn(t, s)

    def test_foundation_and_repo_rules(self):  # C16
        s = step(2)
        for t in ["`docs/<topic>/foundation.md`", "marked `assumption`", "own rules and verify inside Boundaries",
                  "end-to-end tests", "`CLAUDE.md` or `AGENTS.md`", "may add conditions, never remove one"]:
            self.assertIn(t, s)

    def test_confirm_before_apply(self):  # C18
        s = step(4)
        for t in ["task groups", "Restate the goal", "wait for the answer", "Merging the Plan PR is the go-ahead"]:
            self.assertIn(t, s)

    def test_plan_pr(self):  # C18, C20
        s = step(3)
        for t in ["Every `#### Scenario:`", "Verify command or an `Owner judges:` line", "`.agent-flow/verify.py`",
                  "`evidence-check` CI job", "`agent-flow/<topic>-plan`", "--check-only openspec/changes/<topic>/specs"]:
            self.assertIn(t, s)
        self.assertIn("evidence-check:", WORKFLOW)
        self.assertIn("python3 .agent-flow/verify.py", WORKFLOW)

    def test_apply_in_parallel(self):
        s = step(5)
        for t in ["run in parallel, one subagent and one worktree each", "for its group only", "test-first"]:
            self.assertIn(t, s)
        self.assertIn("`Blocked by: 1, 2`", WORKFLOW)

    def test_archive(self):  # C23
        s = step(9)
        for t in ["`agent-flow/<topic>-archive`", "`land.py`"]:
            self.assertIn(t, s)

    def test_subagent_models(self):
        for t in ["| Model |", "`sonnet` for apply implementers", "`opus` for every review subagent",
                  "Each implementer (`model: sonnet`)", "fresh subagent (`model: sonnet`)", "runs on `model: opus`"]:
            self.assertIn(t, WORKFLOW)

    def test_review_once(self):
        s = step(6)
        for t in ["Once per goal", "really tests its Scenario", "do not run a second"]:
            self.assertIn(t, s)


class Locks(unittest.TestCase):  # C19, C22
    def test_locked_paths_and_owner_label(self):
        locks = SKILL[SKILL.index("## Locks"):SKILL.index("## Resume rule")]
        for t in ["`.agent-flow/**`", "`.github/workflows/**`", "`openspec/config.yaml`",
                  "`openspec/changes/<topic>/specs/**`", "`tasks.md` is not locked", "stop and ask the user",
                  "`agent-flow:owner-judges`"]:
            self.assertIn(t, locks)

    def test_scenario_format(self):
        for t in ["#### Scenario: <behavior>", "  Verify: `<command>`", "  Owner judges:", "exit code alone decides",
                  "no `|`, `;`"]:
            self.assertIn(t, WORKFLOW)


class Resume(unittest.TestCase):  # C13
    def test_reuse_before_create(self):
        rule = SKILL[SKILL.index("## Resume rule"):SKILL.index("## Reporting")]
        for t in ["look for the existing one", "reuse it",
                  "exactly one Plan PR, one integration PR, one archive PR and one OpenSpec change"]:
            self.assertIn(t, rule)


class Reporting(unittest.TestCase):  # C14
    def test_cost_and_user_judges(self):
        rep = SKILL[SKILL.index("## Reporting"):]
        for t in ["cumulative tokens", "`user judges`", "`/cost`"]:
            self.assertIn(t, rep)


if __name__ == "__main__":
    unittest.main()
