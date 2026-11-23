---
name: agent-flow
description: Run a goal from words to merged PRs in the current repo, with written finish line, CI, GitHub issues, subagent implementers, independent review and a merge gate. Use when the user says "run the flow", "take this goal to merged", "agent-flow", or hands over a goal, direction or seed to finish unattended.
---

# agent-flow

The user hands over a goal, a direction or a seed. You take it to merged PRs, with evidence for every line of the finish line. You decide how; you ask only where Boundaries says Ask first.

Answer in the user's language. Files you write for the repo (records, tickets, PRs) follow the language the user writes in, except the fixed headings and markers named in the references.

## Start

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"`. Fix what it reports, or tell the user the fix when you cannot do it. Continue only on exit 0.
2. Read `.agent-flow/STOP` and `.agent-flow/config` if they exist (see Kill switch).
3. First run in a repo, meaning no `docs/*/discussion.md` exists: print this list, then continue without waiting.
   - Write actions: create branches and git worktrees; commit and push; open, update and merge PRs; create GitHub issues; add a CI workflow when none runs the checks; write `docs/<topic>/`, `GLOSSARY.md`, `docs/adr/`.
   - To stop merging: create `.agent-flow/STOP`, or put `merge: never` in `.agent-flow/config`. To stop everything: interrupt the session.
   - The Ask first and Never lists from Boundaries.
4. Resuming: a `docs/<topic>/discussion.md` for this goal exists. Read it and the open issues and PRs, then continue from the first unfinished step.

## Boundaries

These are the outer limits. The repo's own rules (written in flow step 3, Gather information) may tighten them, never loosen them; where a repo rule conflicts with a boundary, the boundary wins. Invoking this skill in a repo is the consent to the first tier.

- **Do without asking**: branch, commit, push, open PRs, set up and fix CI, merge your own PRs through `land.py`, including PRs that change CI or tests.
- **Ask first, upfront**: a method chosen to verify the work that creates external resources, runs real model calls or spends the user's usage. List it with its estimated cost in the first question round, not mid-run ([references/workflow.md](references/workflow.md) step 2).
- **Ask first**: deploy or publish to users; writes to repos or services the user does not own; anything that notifies other people (messages, issues or PRs on someone else's repo, mentions, review requests); using secrets; spending money; deleting or overwriting the user's own data; browser use (testing, previews, screenshots, any browser automation). Stop that action, ask once with a recommended answer, and keep working on everything else. Without browser permission, run static, unit, build and API checks and list browser acceptance as unverified.
- **Never**:
  - claim done without evidence, or report an unverified check as verified;
  - fabricate projects, repos, data or records and present them as verification;
  - delete or weaken tests, checks, CI, these boundaries or the kill switch to make a gate pass;
  - commit secrets or print them.

## Kill switch

If `.agent-flow/STOP` exists, or `.agent-flow/config` has a line `merge: never`, open PRs and never merge. Check before every merge, not only at start. `merge_gate.py` (run by `land.py`) enforces the same rule.

## The flow

Detail for each step: [references/workflow.md](references/workflow.md). A step is done when its criterion holds.

1. **Receive the request.** Classify the input as goal, direction or seed; a goal needs no reply. Create `docs/<topic>/discussion.md` with the user's words verbatim. Done: the file has the five headings from [references/records.md](references/records.md).
2. **Confirm the request.** Write the finish line: results, not methods, each as `- C<n> <text>` with an external `evidence:` an outside party can run or read. Done: every line has evidence.
3. **Gather information.** Read official docs and source and the repo itself, then write this repo's own rules and verify inside Boundaries: its verify commands, the CI that runs them on every PR, whether it needs end-to-end tests (asked first if they cost usage or create external resources), any merge conditions it adds to `merge_gate.py`'s fixed ones (CI green, audit passed, no kill switch; a repo may add conditions, never remove one), and the audit's project rules and trap reports in `.agent-flow/auditor/` ([references/audit.md](references/audit.md), Rules and Trap reports). Write them into the repo's `CLAUDE.md` or `AGENTS.md`, or `docs/<topic>/` when they belong to this goal only. If no CI runs the verify commands, the CI PR is the first ticket. Done: the rules and verify commands are written, recorded in `discussion.md`, and CI is green on the default branch.
4. **Cut tickets.** Write `docs/<topic>/spec.md`, then one GitHub issue per verifiable behavior in the format of [references/tickets.md](references/tickets.md). Then a fresh subagent reads only the issue files and lists what it would have to guess; add the guesses that change a Verify result or a ticket interface, leave the rest. Run every Verify command before implementation: each must fail for the right reason or be marked as a check that already passes. Done: every issue has Scope, Out of scope, runnable Verify, Blocked by, and the ticket marker, and its Verify commands have been run.
5. **Implement.** One subagent per ticket (`subagent_type: agent-flow:implementer`), one git worktree each, ordered by Blocked by; independent tickets run in parallel. Each ticket ends as a PR. Done: PR open with the ticket marker and the implementer's report.
6. **Review.** Per PR: CI green, then one independent review following [references/review.md](references/review.md). `scripts/review.py <prompt-file> [--cwd <repo>] [--model opus]` runs the reviewer (agent `agent-flow:reviewer`); the report format is in [references/review.md](references/review.md). Done: a review report for the PR's head commit.
7. **Audit.** Re-run the review's evidence following [references/audit.md](references/audit.md), then merge:
   - `scripts/audit.py <report> --repo <repo> [--model]` exit 0 passed, 1 failed, 3 partly unverified, 2 setup error (including trap reports that have not passed; run `scripts/canaries.py --repo <repo>`).
   - `scripts/land.py <pr-number> [--worktree <dir>] [--repo-root <dir>]` runs `scripts/merge_gate.py` (exit 0 mergeable, 1 blocked), merges with a merge commit (no squash), then cleans up; exit 0 merged, 1 blocked or failed, 2 setup error. Exit 1: fix the printed reasons. Then update the integration branch and unblock dependent tickets.
   Done: the PR is merged.

Script paths are relative to `${CLAUDE_PLUGIN_ROOT}`. A missing script is a blocker to report, not to emulate. When every ticket is merged or stuck, report (see Reporting).

## Resume rule

Every issue and PR body you create contains `<!-- agent-flow:<topic>#<NN> -->`. Before creating an issue or PR, search for that marker (`gh issue list --state all --search '"agent-flow:<topic>#<NN>" in:body'`, and `gh pr list` likewise) and reuse what exists. Re-running after a crash must leave exactly one issue and one PR per ticket.

## Companion skills

Skills such as `grilling`, `to-spec`, `to-tickets`, `tdd`, `implement-spec`, `pr` are optional. Use one if installed. If not, the built-in fallback:

| Companion | Fallback |
|---|---|
| `grilling` | Ask at most 5 questions per round, each with your recommended answer. |
| `to-spec` | Write `spec.md` with: Problem, Solution, User stories, Implementation decisions, Testing decisions, Out of scope. |
| `to-tickets` | Cut issues by [references/tickets.md](references/tickets.md). |
| `tdd` | Write the failing Verify check first, see it fail, then implement. |
| `implement-spec` | Implement as step 5 says. |
| `pr` | Body: what changed, how it was checked (commands and results), `Closes #<n>`, the marker. |

List the fallbacks you took in the final report.

## Reporting

Before reporting, run `scripts/pending_audits.py <repo>`; anything it lists blocks the wrap-up. List every `.audit.md` conclusion so the user can spot-check them.

Report in three groups: done and verified, done but unverified, not done, each with the reason. Separate fact, inference, assumption and unknown, following [references/grounded-answer.md](references/grounded-answer.md). Name failed and skipped checks. Say how many times you asked the user. Tell the user to run `/cost` for the interactive session's cost.
