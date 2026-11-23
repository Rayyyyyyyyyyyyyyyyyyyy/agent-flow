---
name: agent-flow
description: Take a goal from words to a merged PR in the current repo. Aligns the installed skills to each step, grounds the work in sourced facts, confirms the tasks with the user, locks every check in a Plan PR, implements tickets in parallel, reviews once, re-runs the locked checks in CI and merges through a gate. Use when the user says "run the flow", "agent-flow", "take this goal to merged", or hands over a goal, direction or seed to finish.
---

# agent-flow

The user hands over a goal, a direction or a seed. You take it to a merged PR, with evidence for every line of the finish line. You decide how; you ask only where the Method or Boundaries says so.

Answer in the user's language. Files you write for the repo (records, tickets, PRs) follow the language the user writes in, except the fixed headings, field names and markers named in the references.

agent-flow owns only what no installed skill does: the Boundaries, the Plan PR gate, the locks, the Evidence check, `merge_gate.py`/`land.py`, `doctor.py` and the order of steps. Every other step uses the skill chosen in step 0.

## Start

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"`. Fix what it reports, or tell the user the fix when you cannot do it. Continue only on exit 0.
2. Read `.agent-flow/STOP` and `.agent-flow/config` if they exist (see Kill switch).
3. First run in a repo, meaning no `docs/*/discussion.md` exists: print this list, then continue without waiting.
   - Write actions: create branches and git worktrees; commit and push; open, update and merge PRs (a Plan PR only with `plan: agent`); add a CI workflow; write `docs/<topic>/`, `docs/agents/`, `.agent-flow/`, `GLOSSARY.md`, `docs/adr/`.
   - To stop merging: create `.agent-flow/STOP`, or put `merge: never` in `.agent-flow/config`. To stop everything: interrupt the session.
   - The Ask first and Never lists from Boundaries.
4. Resuming: a `docs/<topic>/discussion.md` for this goal exists. Read it, `.agent-flow/skills.md`, the ticket files and the open PRs, then continue from the first unfinished step (see Resume rule).

## Boundaries

These are the outer limits. The repo's own rules (written in step 2) may tighten them, never loosen them; where a repo rule conflicts with a boundary, the boundary wins. Invoking this skill in a repo is the consent to the first tier.

- **Do without asking**: branch, commit, push, open PRs, set up and fix CI, merge your own PRs through `land.py` (a Plan PR only when `.agent-flow/config` has `plan: agent`).
- **Ask first, upfront**: a method chosen to verify the work that creates external resources, runs real model calls or spends the user's usage. List it with its estimated cost in the confirm step (step 3), not mid-run.
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

Detail for each step: [references/workflow.md](references/workflow.md). A step is done when its criterion holds.

0. **Align the environment.** List the skills and agents this session actually has, from any source. For each step below pick the one that fits, with a one-line reason; a skill with `disable-model-invocation: true` is followed by reading its `SKILL.md`; use the fallback in workflow.md only when none fits. Write the settings the chosen skills need (for example an issue-tracker file pointing at `docs/<topic>/`, per [references/tickets.md](references/tickets.md)). Record the map in `.agent-flow/skills.md`. Done: every step has a skill or a named fallback.
1. **Receive the request.** Classify it as goal, direction or seed; a direction or seed is grilled with the user first. Create `docs/<topic>/discussion.md` with the user's words verbatim and a draft finish line (format: [references/records.md](references/records.md)). Done: the file has the five headings.
2. **Gather facts.** Research with the chosen skill. Write `docs/<topic>/foundation.md`: every fact with its source (`path:line`, URL, or a command and its output); a fact without one is marked `assumption`. Then write this repo's own rules and verify inside Boundaries: its verify commands, whether it needs end-to-end tests, and any merge conditions it adds to `merge_gate.py`'s fixed ones (a repo may add conditions, never remove one), in the repo's `CLAUDE.md` or `AGENTS.md`, or `docs/<topic>/` when they belong to this goal only. Done: Foundation and rules written.
3. **Confirm with the user.** Show the task list (one line per planned ticket, with what blocks what), restate the goal and the finish line, and list anything that needs a yes upfront. This is a conversation; wait for the answer and fold it into `discussion.md`. Done: the user confirmed.
4. **Cut tickets and open the Plan PR.** Write `docs/<topic>/spec.md` and the ticket files with the chosen skills, in the format of [references/tickets.md](references/tickets.md): every criterion has a Verify command. Answer the skills' own questions yourself with your recommendation and list them in the Plan PR. Copy `${CLAUDE_PLUGIN_ROOT}/scripts/verify.py` to `.agent-flow/verify.py` and add the `evidence-check` CI job (workflow.md step 4). Push the integration branch `agent-flow/<topic>` from the default branch, then open the Plan PR from `agent-flow/<topic>-plan` into it. Done: `python3 .agent-flow/verify.py --check-only docs/<topic>/tickets` exits 0 and the Plan PR is open.
5. **Implement.** After the Plan PR is merged (by the user, or by you through `land.py` with `plan: agent`), implement with the chosen skill on the integration branch: tickets whose blockers are done run in parallel, one worktree each. Then open the integration PR from `agent-flow/<topic>` into the default branch. Done: every ticket's Verify commands pass on the integration branch.
6. **Review.** Once per goal, with the chosen review skill, on the integration PR's diff. It also judges whether each Verify command really tests its criterion and whether the diff stays inside each ticket's Scope. If the implementation skill already ends with a review, that is this step; do not run a second. Fixes go to an implementer and must not touch locked paths. Done: no open finding.
7. **Evidence check.** CI's `evidence-check` job runs every locked Verify command at the PR head. Done: it is green.
8. **Merge.** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/land.py" <pr-number> [--worktree <dir>] [--repo-root <dir>]`: runs `merge_gate.py` (exit 0 mergeable, 1 blocked, 2 setup error), updates a branch that is behind, merges with a merge commit (never squash), then cleans up. Exit 1: fix the printed reasons. Done: the integration PR is merged.

A missing script is a blocker to report, not to emulate. When the goal is merged or stuck, report (see Reporting).

## Locks

Once the Plan PR is merged, these paths change only through a new Plan PR: `.agent-flow/**`, `.github/workflows/**`, `docs/<topic>/tickets/**`. `merge_gate.py` refuses any other PR that changes them after its Plan PR merged. If a Verify command or rule turns out wrong, stop and ask the user; do not edit it to make a gate pass.

A criterion only a person can judge is written `Owner judges:` in its ticket; the PR that carries it gets the label `agent-flow:owner-judges`, which `merge_gate.py` refuses, so the user judges and merges it. Prefer putting such criteria in the finish line only, where they are listed in the report and block nothing.

## Resume rule

Branches are `agent-flow/<topic>` (integration) and `agent-flow/<topic>-plan` (Plan PR); tickets are files under `docs/<topic>/tickets/`. Before creating a branch, ticket file or PR, look for the existing one (`git ls-remote --heads origin 'agent-flow/<topic>*'`, `gh pr list --state all --head <branch>`, the ticket directory) and reuse it. Re-running after a crash must leave exactly one Plan PR, one integration PR and one file per ticket.

## Reporting

Report in three groups: done and verified, done but unverified, not done, each with the reason. Separate fact, inference, assumption and unknown, following [references/grounded-answer.md](references/grounded-answer.md). Name failed and skipped checks. List the finish-line items marked `user judges` for the user to judge. Give the review's cumulative tokens (the sum over its subagents' reported usage). Say how many times you asked the user and why. Tell the user to run `/cost` for the interactive session's cost.
