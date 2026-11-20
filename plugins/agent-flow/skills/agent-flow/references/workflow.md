# Workflow detail

Order: intake, finish line, research and CI, spec and tickets, clarity gate, dispatch, check, merge, report. Do the work yourself where thinking is needed (breaking down, deciding); give execution to implementer subagents and judgment of the result to a reviewer in a separate context. Independent work may run in parallel subagents.

Commit after each step. Commit and push to working branches without asking. Every change reaches the default branch through a PR.

## 1. Intake

| The user gives | You do | Start when |
|---|---|---|
| **Goal**: a result they want | Write it as a finish line | Written |
| **Direction**: end point undecided | Research, propose 2-3 candidate finish lines, each with cost and a recommendation | The user picks one |
| **Seed**: a loose idea | Research feasibility and similar work; ask only what cannot be found (preferences, resources, limits), at most 5 questions per round, each with a suggested answer; then propose 2-3 concepts with finish lines | The user picks one |

When unsure which, treat it as the more mature kind and say how you judged. Put the user's words in `discussion.md` verbatim (format: [records.md](records.md)).

## 2. Finish line

- Results, not methods. The user's words bound the scope. First ask what the user wants to happen after this is done; a larger version or better route goes into Decisions as an option, and you work to the original words meanwhile.
- Every line has external evidence: a test, a command, a measured number, a reproduction from raw data. If only the user can judge it, write `evidence: user judges`.
- Each evidence item names how it will be proven. A method that creates external resources (repos, services), runs real model calls, or spends the user's usage is listed with its estimated cost and runs only after the user's explicit yes. Until then run only checks that create nothing external and spend no model usage. This is the one exception to the no-questions default: ask it in the single upfront question round, not mid-run.
- Apply the four questions from [records.md](records.md).

## 3. Research and CI first

Research order: official docs, source code, web search, then a trial run. Record sources. Keep large documents out of the coordinator: a doc lookup or research goes to a subagent that returns only the quoted lines and their source URL or path. If the network or a site is blocked, switch source; if a site is truly needed, tell the user which and why.

Find the repo's verify commands in its `package.json`, CI config, `CLAUDE.md` or `AGENTS.md`. Record them. If PRs have no CI running them, adding CI is ticket 01: CI runs only the verify commands, with no deploy and no secrets. If the default branch has no rule requiring a PR and green CI, set it when the plan allows (`gh api` branch protection); if not allowed, say so in Decisions, and `merge_gate.py` is the guard.

Missing infrastructure that blocks evidence (raw data or logs, version and commit mapping, a reproducible environment) becomes early tickets. Using secrets, money or the user's own data in this step triggers the `WARNING:` tier; a need for accounts you do not have, or for browser use, goes to the user.

## 4. Spec and tickets

Write `docs/<topic>/spec.md`, then tickets by [tickets.md](tickets.md). You decide the breakdown and record why in Decisions; do not quiz the user. Each ticket is one verifiable behavior.

## 5. Clarity gate

Anything needing a trade-off, a design choice or a question to the user is settled by you before dispatch, then written into the ticket.

Once per batch, before first dispatch, start a fresh subagent. Give it only the ticket locations. Ask: what would you build for each ticket, and where must you guess? Add only guesses that would change a Verify result or an interface between tickets; the rest the implementer reports as `GUESSED`.

Then run every ticket's Verify commands on the unimplemented tree. Those meant to fail must fail for the stated reason. Each command must be correct and finish by itself, leaving no server or process running.

## 6. Dispatch

One subagent per ticket (`subagent_type: agent-flow:implementer`), one worktree each: `git worktree add ../<repo>-<NN> -b <topic>/<NN> <integration branch>`. Message and report format: [tickets.md](tickets.md). After a subagent ends, check for leftover processes (`pgrep -fl`, `lsof` to confirm the owner before killing) and remove its worktree when its PR is merged.

Session phases: once the finish line and tickets are agreed, tell the user to start implementation in a fresh session and give the exact line to type: `Run agent-flow: resume from docs/<topic>/discussion.md and the open issues.` The long design conversation is not carried into ticket coordination. A coordinating session that has handled many tickets suggests a fresh session the same way instead of continuing.

Follow-ups that belong to the finish line become new tickets; anything beyond it goes into Decisions as a question.

Stuck means: the same problem, including a FAIL on the same finish-line item, survives three different approaches; or the next step needs something only the user can give. Save the work, tell the user with options and a recommendation, and continue unblocked work.

## 7. Check and merge

Deterministic checks come first: the verify commands, each finish-line item's evidence, and CI on the PR. Fix failures before any reviewer runs. Then review and audit per [review.md](review.md) and [audit.md](audit.md), and merge only through `land.py`.

Landing is one call: `land.py <pr> [--worktree <dir>] [--repo-root <dir>]` runs the `merge_gate.py` checks, updates the branch and waits for checks when it is behind, merges with a merge commit (`gh pr merge <n> --merge`), and only after `gh pr view --json state` says MERGED removes the worktree and deletes the local and remote branch. Do not poll or clean up by hand. Any failure prints why and touches nothing. Never squash, so `git revert -m 1 <sha>` undoes it. Record each merge and its evidence in the final report. Deploy and publish are outside the flow: ask first.

## 8. Report

Close with: finish line items, each with its evidence and result; which checks failed or did not run; what was merged; guesses taken and fallbacks used; number of questions to the user and the reason for each. Format: [grounded-answer.md](grounded-answer.md).
