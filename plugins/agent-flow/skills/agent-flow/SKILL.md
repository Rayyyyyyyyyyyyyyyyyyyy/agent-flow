---
name: agent-flow
description: Take a goal from words to a merged PR in the current repo. Explores the request with the user through OpenSpec, grounds the work in sourced facts, proposes an OpenSpec change whose every Scenario carries a locked Verify command, implements it after the user approves the Plan PR, reviews once, re-runs the locked checks in CI, merges through a gate and archives the change into the repo's current specs. Use when the user says "run the flow", "agent-flow", "take this goal to merged", or hands over a goal, direction or seed to finish.
---

# agent-flow

The user hands over a goal, a direction or a seed. You take it to a merged PR, with evidence for every line of the finish line. You decide how; you ask only where the Method or Boundaries says so.

Answer in the user's language. Files you write for the repo (records, OpenSpec artifacts, PRs) follow the language the user writes in, except the fixed headings, field names and markers named in the references.

agent-flow owns only what no other tool does: the Boundaries, the Plan PR gate, the locks, the Evidence check, `merge_gate.py`/`land.py`, `doctor.py`, the `guard.py` hook and the order of steps. Explore, propose, apply and archive are OpenSpec's `/opsx:explore`, `/opsx:propose`, `/opsx:apply` and `/opsx:archive`, run as the user would run them; agent-flow only reads what they leave in the repo. Every other step uses the skill chosen in step 0.

## Start

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"`. Fix what it reports, or tell the user the fix when you cannot do it. Installing OpenSpec and running `openspec init` are the user's: give them the printed fix and wait. Continue only on exit 0.
2. Read `.agent-flow/STOP` and `.agent-flow/config` if they exist (see Kill switch).
3. First run in a repo, meaning no `docs/*/discussion.md` exists: print this list, then continue without waiting.
   - Write actions: create branches and git worktrees; commit and push; open, update and merge PRs (a Plan PR only with `plan: agent`); add a CI workflow; write `docs/<topic>/`, `openspec/changes/<topic>/`, `openspec/specs/`, `.agent-flow/`, `GLOSSARY.md`, `docs/adr/`.
   - To stop merging: create `.agent-flow/STOP`, or put `merge: never` in `.agent-flow/config`. To stop everything: interrupt the session.
   - The Ask first and Never lists from Boundaries.
4. Resuming: a `docs/<topic>/discussion.md` for this goal exists. Read it, `.agent-flow/skills.md`, `openspec/changes/<topic>/` (or its archived copy) and the open PRs, then continue from the first unfinished step (see Resume rule).

## Boundaries

These are the outer limits. The repo's own rules (written in step 2) may tighten them, never loosen them; where a repo rule conflicts with a boundary, the boundary wins. Invoking this skill in a repo is the consent to the first tier. The plugin's `guard.py` hook enforces part of them before a tool runs: it asks before a command that can delete or overwrite work, and denies writes to locked paths (see Locks). A hook answer is final for that call; do not route around it with another tool.

- **Do without asking**: branch, commit, push, open PRs, set up and fix CI, merge your own PRs through `land.py` (a Plan PR only when `.agent-flow/config` has `plan: agent`).
- **Ask first, upfront**: a method chosen to verify the work that creates external resources, runs real model calls or spends the user's usage. List it with its estimated cost in the confirm step (step 4), not mid-run.
- **Ask first**: deploy or publish to users; writes to repos or services the user does not own; anything that notifies other people (messages, issues or PRs on someone else's repo, mentions, review requests); using secrets; spending money; deleting or overwriting the user's own data; browser use (testing, previews, screenshots, any browser automation). Stop that action, ask once with a recommended answer, and keep working on everything else. Without browser permission, run static, unit, build and API checks and list browser acceptance as unverified.
- **Never**:
  - claim done without evidence, or report an unverified check as verified;
  - fabricate projects, repos, data or records and present them as verification;
  - delete or weaken tests, checks, CI, these boundaries or the kill switch to make a gate pass;
  - change a locked path outside a Plan PR (see Locks);
  - commit secrets or print them.

## Kill switch

If `.agent-flow/STOP` exists, or `.agent-flow/config` has a line `merge: never`, open PRs and never merge. Check before every merge, not only at start. `merge_gate.py` (run by `land.py`) enforces the same rule.

## The Method

Detail for each step: [references/workflow.md](references/workflow.md). A step is done when its criterion holds. The change name in OpenSpec is `<topic>`.

0. **Align the environment.** OpenSpec covers explore, propose, apply and archive. For the other steps (research, test-first inside apply, review, PR body, retrospective), list the skills and agents this session actually has, from any source, and pick the one that fits, with a one-line reason; a skill with `disable-model-invocation: true` is followed by reading its `SKILL.md`; use the fallback in workflow.md only when none fits. Record the map in `.agent-flow/skills.md`. Done: every step has an OpenSpec command, a skill or a named fallback.
1. **Receive the request.** Classify it as goal, direction or seed. A goal goes straight to its finish line. A direction or seed is explored with the user through `/opsx:explore`; the user decides when the discussion moves on to propose, and you do not close it yourself. Create `docs/<topic>/discussion.md` with the user's words verbatim and the finish line (format: [references/records.md](references/records.md)). Done: the file has the five headings and the user has moved on from explore (or it was a goal).
2. **Gather facts.** Research with the chosen skill. Write `docs/<topic>/foundation.md`: every fact with its source (`path:line`, URL, or a command and its output); a fact without one is marked `assumption`. Then write this repo's own rules and verify inside Boundaries, only after reading the repo: its verify commands, whether it needs end-to-end tests, and any merge conditions it adds to `merge_gate.py`'s fixed ones (a repo may add conditions, never remove one), in the repo's `CLAUDE.md` or `AGENTS.md`, or `docs/<topic>/` when they belong to this goal only. A rule that can be a check is written as a check: a mistake seen twice becomes a lint rule, test or `protect:` glob whose failure message says how to fix it, not another line of prose. Done: Foundation and rules written.
3. **Propose and open the Plan PR.** Run `/opsx:propose <topic>`. Every `#### Scenario:` in `openspec/changes/<topic>/specs/` has a Verify command or an `Owner judges:` line (format in workflow.md step 3); each `## N.` group in `tasks.md` names what blocks it and its size. Answer propose's own questions yourself with your recommendation and list them in the Plan PR. Copy `${CLAUDE_PLUGIN_ROOT}/scripts/verify.py` to `.agent-flow/verify.py` and add the `evidence-check` CI job (workflow.md step 3). Push the integration branch `agent-flow/<topic>` from the default branch, then open the Plan PR from `agent-flow/<topic>-plan` into it. Done: `python3 .agent-flow/verify.py --check-only openspec/changes/<topic>/specs` exits 0 and the Plan PR is open.
4. **Confirm with the user.** Restate the goal and the finish line, show the task groups (what each delivers, what blocks it), point at the Plan PR, and list anything that needs a yes upfront. This is a conversation; wait for the answer and fold it into `discussion.md`. Merging the Plan PR is the go-ahead: the user merges it, or you land it through `land.py` with `plan: agent` once the user has said yes. Done: the Plan PR is merged.
5. **Apply.** On the integration branch, one task group at a time, in blocker order; groups whose blockers are done run in parallel, one subagent and one worktree each, only when `.agent-flow/config` has `apply: parallel`. Each implementer runs on the model its group's size names, gets a brief file and writes a report file, runs `/opsx:apply <topic>` for its group only, test-first with the chosen skill, and ticks its tasks. Findings go through the fix loop (workflow.md step 5). Merge each into the integration branch, then open the integration PR from `agent-flow/<topic>` into the default branch. Done: every task is ticked and every Verify command passes on the integration branch.
6. **Review.** Once per goal, with the chosen review skill, on the integration PR's diff handed over as one file, against `openspec/changes/<topic>/`. It also judges whether each Verify command really tests its Scenario, whether the diff stays inside the proposal's scope, and whether the diff adds a workaround or a comment excusing one. If the apply step already ends with a review, that is this step; do not run a second. Fixes go to an implementer and must not touch locked paths. Done: no open finding.
7. **Evidence check.** CI's `evidence-check` job runs every locked Verify command at the PR head. Done: it is green.
8. **Merge.** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/land.py" <pr-number> [--worktree <dir>] [--repo-root <dir>]`: runs `merge_gate.py` (exit 0 mergeable, 1 blocked, 2 setup error), updates a branch that is behind, merges with a merge commit (never squash), then cleans up. Exit 1: fix the printed reasons. Done: the integration PR is merged.
9. **Archive.** From the updated default branch, create `agent-flow/<topic>-archive`, run `/opsx:archive <topic>`, open its PR into the default branch and land it through `land.py`. Done: the archive PR is merged.

A missing script is a blocker to report, not to emulate. When the goal is merged and archived, or stuck, report (see Reporting).

## Locks

Once the Plan PR is merged, these paths change only through a new Plan PR: `.agent-flow/**`, `.github/workflows/**`, `openspec/config.yaml`, `openspec/changes/<topic>/specs/**`. `tasks.md` is not locked, so apply can tick it. `merge_gate.py` refuses any other PR that changes a locked path after its Plan PR merged; it lets the archive PR change only this change's OpenSpec paths. A Calling repo locks more paths, such as its lint or test config, with `protect: <glob>` lines in `.agent-flow/config`. On any `agent-flow/*` branch except a `-plan` one, the `guard.py` hook denies edits and shell writes to locked and protected paths when they are attempted; `merge_gate.py` still checks every PR. If a Verify command or rule turns out wrong, stop and ask the user; do not edit it to make a gate pass.

A Scenario only a person can judge carries `Owner judges:`; the PR that carries it gets the label `agent-flow:owner-judges`, which `merge_gate.py` refuses, so the user judges and merges it. Prefer putting such criteria in the finish line only, where they are listed in the report and block nothing.

## Resume rule

Branches are `agent-flow/<topic>` (integration), `agent-flow/<topic>-plan` (Plan PR) and `agent-flow/<topic>-archive` (archive PR); the change is `openspec/changes/<topic>/`. Before creating a branch, change or PR, look for the existing one (`git ls-remote --heads origin 'agent-flow/<topic>*'`, `gh pr list --state all --head <branch>`, `openspec list --json`) and reuse it. Re-running after a crash must leave exactly one Plan PR, one integration PR, one archive PR and one OpenSpec change.

## Reporting

Report in three groups: done and verified, done but unverified, not done, each with the reason. Separate fact, inference, assumption and unknown, following [references/grounded-answer.md](references/grounded-answer.md). Name failed and skipped checks. List the finish-line items marked `user judges` for the user to judge. Give the review's cumulative tokens (the sum over its subagents' reported usage). Say how many times you asked the user and why. List each `Ruling:` you made alone. When every task group merged without an open review finding and `apply: parallel` is not set, say that parallel apply can now be switched on. Tell the user to run `/cost` for the interactive session's cost.
