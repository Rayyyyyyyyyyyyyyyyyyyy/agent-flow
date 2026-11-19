---
name: agent-flow
description: Run a goal from words to merged PRs in the current repo, with written finish line, CI, GitHub issues, subagent implementers, independent review and a merge gate. Use when the user says "run the flow", "take this goal to merged", "agent-flow", or hands over a goal, direction or seed to finish unattended.
---

# agent-flow

The user hands over a goal, a direction or a seed. You take it to merged PRs, with evidence for every line of the finish line. You decide how; you ask only in the third tier below.

Answer in the user's language. Files you write for the repo (records, tickets, PRs) follow the language the user writes in, except the fixed headings and markers named in the references.

## Start

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"`. Fix what it reports, or tell the user the fix when you cannot do it. Continue only on exit 0.
2. Read `.agent-flow/STOP` and `.agent-flow/config` if they exist (see Kill switch).
3. First run in a repo, meaning no `docs/*/discussion.md` exists: print this list, then continue without waiting.
   - Write actions: create branches and git worktrees; commit and push; open, update and merge PRs; create GitHub issues; add a CI workflow when none runs the checks; write `docs/<topic>/`, `GLOSSARY.md`, `docs/adr/`.
   - To stop merging: create `.agent-flow/STOP`, or put `merge: never` in `.agent-flow/config`. To stop everything: interrupt the session.
4. Resuming: a `docs/<topic>/discussion.md` for this goal exists. Read it and the open issues and PRs, then continue from the first unfinished step.

## Autonomy

Invoking this skill in a repo is the consent to everything in the first tier.

- **Do without asking**: branch, commit, push, open PRs, set up and fix CI, merge your own PRs, including PRs that change CI or tests.
- **Warn and continue**: using secrets, spending money, deleting or overwriting the user's own data. Print a line starting `WARNING:` that names the action, as its own line in your reply text (not only in a file or a commit), then continue.
- **Ask first**: deploy or publish to users; writes to repos or services the user does not own; anything that notifies other people (messages, issues or PRs on someone else's repo, mentions, review requests). Stop that action, ask once with a recommended answer, and keep working on everything else.

Browser use (testing, previews, screenshots, any browser automation) needs the user's explicit permission for that run. Without it, run static, unit, build and API checks and list browser acceptance as unverified.

## Kill switch

If `.agent-flow/STOP` exists, or `.agent-flow/config` has a line `merge: never`, open PRs and never merge. Check before every merge, not only at start. `merge_gate.py` enforces the same rule.

## The flow

Detail for each step: [references/workflow.md](references/workflow.md). A step is done when its criterion holds.

1. **Intake.** Classify the input as goal, direction or seed; a goal needs no reply. Create `docs/<topic>/discussion.md` with the user's words verbatim. Done: the file has the five headings from [references/records.md](references/records.md).
2. **Finish line.** Write results, not methods, each as `- C<n> <text>` with an external `evidence:` an outside party can run or read. Done: every line has evidence.
3. **Research and CI first.** Read official docs and source, derive the repo's verify commands, and make sure CI runs them on every PR; if not, the CI PR is the first ticket. Done: the verify commands are recorded in `discussion.md` and CI is green on the default branch.
4. **Spec and tickets.** Write `docs/<topic>/spec.md`, then one GitHub issue per verifiable behavior in the format of [references/tickets.md](references/tickets.md). Done: every issue has Scope, Out of scope, runnable Verify, Blocked by, and the ticket marker.
5. **Clarity gate.** A fresh subagent reads only the issue files and lists what it would have to guess. Add the guesses that change a Verify result or a ticket interface; leave the rest. Run every Verify command before implementation: each must fail for the right reason or be marked as a check that already passes.
6. **Dispatch.** One subagent per ticket (`subagent_type: agent-flow:implementer`), one git worktree each, ordered by Blocked by; independent tickets run in parallel. Each ticket ends as a PR. Done: PR open with the ticket marker and the implementer's report.
7. **Check.** Per PR: CI green, then one independent review following [references/review.md](references/review.md), then the audit following [references/audit.md](references/audit.md). Scripts, paths relative to `${CLAUDE_PLUGIN_ROOT}`:
   - `scripts/review.py <prompt-file> [--cwd <repo>] [--model opus]` runs the reviewer (agent `agent-flow:reviewer`); the report format is in [references/review.md](references/review.md).
   - `scripts/audit.py <report> --repo <repo>` re-runs the report's evidence; exit 0 passed, 1 failed, 3 partly unverified.
   - `scripts/merge_gate.py <pr-number> [--repo-root <dir>]` exit 0 mergeable, 1 blocked.
   These scripts may not exist yet in a checkout under construction; a missing script is a blocker to report, not to emulate.
8. **Merge.** When `merge_gate.py` exits 0, run `gh pr merge <n> --merge` (merge commit, no squash). Exit 1: fix the printed `BLOCKED:` reasons. Then update the integration branch and unblock dependent tickets.
9. **Report.** See Reporting.

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
| `implement-spec` | Dispatch step 6 as written. |
| `pr` | Body: what changed, how it was checked (commands and results), `Closes #<n>`, the marker. |

List the fallbacks you took in the final report.

## Reporting

Report in three groups: done and verified, done but unverified, not done, each with the reason. Separate fact, inference, assumption and unknown, following [references/grounded-answer.md](references/grounded-answer.md). Name failed and skipped checks. Say how many times you asked the user. Tell the user to run `/cost` for the interactive session's cost.
