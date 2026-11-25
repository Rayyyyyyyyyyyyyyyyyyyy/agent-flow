"""The shipped rules state the boundaries (C6), resume (C13), cost (C14), repo rules (C16),
Environment alignment (C17), propose, confirm and Plan PR (C18), locks (C19), test check (C20),
owner-judged items (C22), archive (C23), code review and review evidence (C25)."""
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

    def test_floor(self):  # C25
        for s in ["the floor every Calling repo keeps", "count a task as done without code-level evidence",
                  "merge without a review evidence record that passes every task", "no evidence, no merge",
                  "the reviewer is never the implementer"]:
            self.assertIn(s, BOUNDARIES)
        for s in ["abstract method", "sets only the floor", "each task in its `tasks.md` is accepted only on a code review's evidence",
                  "its Verify commands are the program tests CI runs"]:
            self.assertIn(s, SKILL)

    def test_boundaries_printed_on_first_run(self):
        self.assertIn("The Ask first and Never lists from Boundaries.", SKILL)


class Method(unittest.TestCase):
    def test_steps_in_order(self):
        steps = ["0. **Align the environment.**", "1. **Receive the request.**", "2. **Gather facts.**",
                 "3. **Propose and open the Plan PR.**", "4. **Confirm with the user.**", "5. **Apply.**",
                 "6. **Code review.**", "7. **Test check.**", "8. **Merge.**", "9. **Archive.**"]
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

    def test_apply_one_group_first(self):  # P1
        s = step(5)
        for t in ["one task group at a time", "run in parallel, one subagent and one worktree each",
                  "only when `.agent-flow/config` has `apply: parallel`", "for its group only", "test-first"]:
            self.assertIn(t, s)
        for t in ["`Blocked by: 1, 2`", "Task groups run one at a time", "one agent delivers mergeable work before many"]:
            self.assertIn(t, WORKFLOW)
        self.assertIn("parallel apply can now be switched on", SKILL)

    def test_briefs_and_reports(self):  # P4
        for t in ["$(git rev-parse --git-common-dir)/agent-flow/<topic>/", "`group-N-brief.md`", "`group-N-report.md`",
                  "Never paste earlier groups' history", "starts no subagents of its own",
                  "returns only the status, the commit, one line of test results and its concerns"]:
            self.assertIn(t, WORKFLOW)

    def test_fix_loop(self):  # P6
        for t in ["Rounds 1-3 go back to the same implementer", "Rounds 4-5 go to a fresh implementer one model tier above",
                  "Never fix in the coordinating session", "a problem survives round 5"]:
            self.assertIn(t, WORKFLOW)

    def test_rulings(self):  # P7
        self.assertIn("`Ruling: <what you decided> - <why> - <what it costs if wrong>`", WORKFLOW)
        self.assertIn("List each `Ruling:`", SKILL)

    def test_checks_over_prose(self):  # P2
        self.assertIn("a mistake seen twice becomes a lint rule, test or `protect:` glob", step(2))
        for t in ["A mistake seen twice", "failure message says how to fix it", "`protect: <glob>`"]:
            self.assertIn(t, WORKFLOW)

    def test_archive(self):  # C23
        s = step(9)
        for t in ["`agent-flow/<topic>-archive`", "`land.py`"]:
            self.assertIn(t, s)

    def test_subagent_models_by_size(self):  # P3
        for t in ["| Model |", "`haiku` for `small`, `sonnet` for `medium`, `opus` for `large`",
                  "runs on `sonnet` when every group is `small`, else on `opus`", "one tier above the group's model",
                  "`Size: small`", "`Size: medium`", "`Size: large`", "fresh subagent (`model: sonnet`)",
                  "`model:` from its group's size"]:
            self.assertIn(t, WORKFLOW)
        self.assertIn("names what blocks it and its size", step(3))

    def test_review_once(self):
        s = step(6)
        for t in ["Once per goal", "really tests its Scenario", "do not run a second", "handed over as one file",
                  "adds a workaround or a comment excusing one"]:
            self.assertIn(t, s)

    def test_code_review_per_task(self):  # C25
        s = step(6)
        for t in ["a reviewer that is not the implementer", "code-review skill",
                  "each task in `openspec/changes/<topic>/tasks.md`", "`PASS` or `FAIL`", "`file:line` in the diff",
                  "the test that covers it or why none does", "That per-task table is the evidence",
                  "review evidence record", "a new complete table for the new head"]:
            self.assertIn(t, s)
        self.assertIn("runs every locked Verify command", step(7))
        self.assertIn("program tests", step(7))
        self.assertIn("review evidence for every task on the current code", step(8))
        self.assertIn("Link the review evidence record", SKILL)

    def test_review_evidence_record(self):  # C25
        for t in ["code-review skill: it reads the code", "`openspec/changes/<topic>/tasks.md`, one verdict per task",
                  "<!-- agent-flow:review commit=<full sha of the reviewed head> -->", "| Task | Verdict | Evidence |",
                  "A ticked box is not evidence", "`gh pr comment <n> --body-file <file>`", "reads the latest such comment",
                  "every commit added after the reviewed one is a merge", "never post a record for a review that did not happen",
                  "implemented nothing in this change", "keeps the review evidence valid"]:
            self.assertIn(t, WORKFLOW)

    def test_review_package(self):  # P5, P9
        for t in ["`review-package.md`", "It does not re-run Verify commands", "a package of the fix diff",
                  "a comment that explains one away", "listed under Open questions, not fixed here"]:
            self.assertIn(t, WORKFLOW)


class Locks(unittest.TestCase):  # C19, C22
    def test_locked_paths_and_owner_label(self):
        locks = SKILL[SKILL.index("## Locks"):SKILL.index("## Resume rule")]
        for t in ["`.agent-flow/**`", "`.github/workflows/**`", "`openspec/config.yaml`",
                  "`openspec/changes/<topic>/specs/**`", "`tasks.md` is not locked", "stop and ask the user",
                  "`agent-flow:owner-judges`"]:
            self.assertIn(t, locks)

    def test_guard_hook(self):  # P8
        self.assertIn("`guard.py` hook", BOUNDARIES)
        locks = SKILL[SKILL.index("## Locks"):SKILL.index("## Resume rule")]
        for t in ["`protect: <glob>`", "`guard.py` hook denies", "`merge_gate.py` still checks every PR"]:
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
