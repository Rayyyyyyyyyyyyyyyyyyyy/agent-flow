# Workflow detail

Order: align the environment, receive, gather facts, confirm with the user, cut tickets and open the Plan PR, implement, review, evidence check, merge; then report. Do the thinking yourself (breaking down, deciding); give execution to implementer subagents and judgment of the result to a review in a separate context. Independent work may run in parallel subagents.

Commit after each step. Commit and push to working branches without asking. Every change reaches the default branch through a PR.

## 0. Align the environment

- Source of truth is this session's own list of available skills and agents, not a fixed vendor list. Read each candidate's description; read its `SKILL.md` before relying on what it does.
- A skill marked `disable-model-invocation: true` cannot be called through the Skill tool: find its `SKILL.md` (user skills under `~/.claude/skills/<name>/`, plugin skills under `~/.claude/plugins/cache/*/*/*/skills/<name>/`) and follow it as written.
- Steps to fill: grill a vague request (step 1), research (2), spec and tickets (4), implement with test-first (5), review (6), PR body (every PR), retrospective (after 8, optional). Front-end, security or domain skills join the step they serve.
- Record `.agent-flow/skills.md`:

  ```markdown
  | Step | Skill | Invoke | Why |
  |---|---|---|---|
  | 4 tickets | <name> | Skill tool, or read <path> | <one line> |
  ```

- Write the settings chosen skills expect, all pointing at this layout: spec `docs/<topic>/spec.md`, tickets `docs/<topic>/tickets/<NN>-<slug>.md` in the format of [tickets.md](tickets.md), glossary `GLOSSARY.md`, decisions `docs/adr/`. For example, a ticket skill that reads `docs/agents/issue-tracker.md` gets one saying tickets are local markdown files at that path, with that format, and that its own ticket template yields to [tickets.md](tickets.md).
- Redo step 0 when the installed skills change; the new `skills.md` goes in the next Plan PR.

Fallbacks, only for a step no installed skill covers:

| Step | Fallback |
|---|---|
| Grill | At most 5 questions per round, each with your recommended answer. |
| Research | A subagent reads primary sources and returns only quoted lines with their path or URL. |
| Spec | `spec.md` with: Problem, Solution, User stories, Implementation decisions, Testing decisions, Out of scope. |
| Tickets | [tickets.md](tickets.md). |
| Implement | One subagent per ready ticket, one worktree each off the integration branch; write the failing Verify first, see it fail, then implement; merge each into the integration branch, resolving conflicts in a separate subagent. |
| Review | One subagent with only: the diff, the ticket files, `foundation.md`, the Verify results. It reports findings with a concrete failing case each. |
| PR body | What changed, how it was checked (commands and results), the ticket files. |

## 1. Receive the request

| The user gives | You do | Start when |
|---|---|---|
| **Goal**: a result they want | Write it as a finish line | Written |
| **Direction**: end point undecided | Research, propose 2-3 candidate finish lines, each with cost and a recommendation | The user picks one |
| **Seed**: a loose idea | Grill: research feasibility and similar work; ask only what cannot be found (preferences, resources, limits); then propose 2-3 concepts with finish lines | The user picks one |

When unsure which, treat it as the more mature kind and say how you judged. Put the user's words in `discussion.md` verbatim ([records.md](records.md)).

Finish line rules:

- Results, not methods. The user's words bound the scope. A larger version or better route goes into Decisions as an option; work to the original words meanwhile.
- Every line has external evidence: a test, a command, a measured number, a reproduction from raw data. If only the user can judge it, write `evidence: user judges`.
- Apply the four questions from [records.md](records.md).

## 2. Gather facts

Research order: official docs, source code, web search, then a trial run. Keep large documents out of the coordinator: research goes to a subagent or the chosen research skill, which returns quoted lines and their source. If the network or a site is blocked, switch source; if a site is truly needed, tell the user which and why.

`docs/<topic>/foundation.md` holds what the work rests on: one fact per line, each with its source; `assumption:` marks a fact with none. Tickets cite it; implementers and the review take facts from it rather than finding their own.

Then write the repo's own rules and verify, fitted to this repo and inside the Boundaries in SKILL.md (they may tighten a boundary, never loosen one):

- Verify commands: what proves a change works here (tests, build, lint, type check). Prefer what the repo already runs. Note what they do not cover.
- End-to-end tests: only when the repo needs them; many do not. A method that spends usage or creates external resources is asked in step 3, with its cost.
- Merge conditions: `merge_gate.py` always requires CI green, the evidence check, a merged Plan PR, no locked-path change after it and no kill switch. The repo may add conditions; it may not remove one.
- Where: lasting rules go in the repo's `CLAUDE.md` or `AGENTS.md`; rules for this goal only go in `docs/<topic>/`. Record what you wrote under Decisions. If the default branch has no rule requiring a PR and green CI, set it when the plan allows (`gh api` branch protection, requiring `evidence-check`); if not allowed, say so in Decisions, and `merge_gate.py` is the guard.

Missing infrastructure that blocks evidence (raw data or logs, version and commit mapping, a reproducible environment) becomes early tickets. Using secrets, money or the user's own data, a need for accounts you do not have, and browser use go to the user first (Boundaries, Ask first).

## 3. Confirm with the user

One message: the restated goal, the finish line, the task list (one line per planned ticket: what it delivers, what blocks it), the skills from step 0, and every item that needs a yes upfront (a verification method that spends usage or creates external resources, with its estimated cost). Ask whether the tasks and goal are right. Wait for the answer; record it in `discussion.md` (Original words for the user's words, Decisions for what changed). This is the only planned question round; later questions are only those Boundaries requires.

## 4. Cut tickets and open the Plan PR

Write `docs/<topic>/spec.md`, then the ticket files by [tickets.md](tickets.md). You decide the breakdown and record why in Decisions. Where a chosen skill would ask the user (granularity, test seams), take your recommended answer and list each such choice in the Plan PR body.

Once per batch, start a fresh subagent with only the ticket paths. Ask: what would you build for each ticket, and where must you guess? Fix the tickets for guesses that would change a Verify result or an interface between tickets.

Run `python3 .agent-flow/verify.py docs/<topic>/tickets` on the unimplemented tree. Commands meant to fail must fail for the stated reason; each must finish by itself, leaving no server or process running.

Copy `${CLAUDE_PLUGIN_ROOT}/scripts/verify.py` to `.agent-flow/verify.py` when it is missing or differs. Add this job to the repo's CI workflow (create `.github/workflows/ci.yml` if none runs on pull requests), with the repo's own setup steps so its Verify commands can run:

```yaml
  evidence-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # the repo's setup steps (runtime, dependency install) go here
      - run: python3 .agent-flow/verify.py ${{ github.event_name == 'pull_request' && github.base_ref != github.event.repository.default_branch && '--check-only' || '' }}
```

PRs into an integration branch (the Plan PR) only validate the tickets; PRs into the default branch run every Verify command. CI runs only verify commands: no deploy, no secrets.

Branches: push `agent-flow/<topic>` from the default branch, then `agent-flow/<topic>-plan` carrying `discussion.md`, `foundation.md`, `spec.md`, the tickets, `.agent-flow/` (skills map, `verify.py`, config if any), CI changes and repo rules. Open the Plan PR into `agent-flow/<topic>`.

Session phases: once the Plan PR is open, tell the user to review and merge it, then start implementation in a fresh session with the exact line: `Run agent-flow: resume from docs/<topic>/discussion.md.` With `plan: agent`, land it yourself and continue. A coordinating session that has handled many tickets suggests a fresh session the same way instead of continuing.

## 5. Implement

With the chosen implementation skill on `agent-flow/<topic>`. Each implementer gets only pointers: its ticket file, `foundation.md`, `discussion.md`, its worktree, the integration branch, the Verify commands. Always include: "Any judgment or 'I guess' you make yourself, however small, counts as a guess; report it." Report back: status (`DONE`, `GUESSED`, `BLOCKED`), commit, each Verify command with its result, the guess list, what was not verified.

Judge each guess: correct ones are recorded in the integration PR body; wrong ones are reverted and re-dispatched. A ticket that is wrong itself needs a new Plan PR (Locks). After a subagent ends, check for leftover processes (`pgrep -fl`, `lsof` to confirm the owner before killing).

Follow-ups inside the finish line become tickets in a new Plan PR; anything beyond it goes into Decisions as a question.

Stuck means: the same problem survives three different approaches; or the next step needs something only the user can give. Save the work, tell the user with options and a recommendation, and continue unblocked work.

## 6. Review

Deterministic checks first: every Verify command passes locally and CI is green. Then one review of `git diff <default branch>...agent-flow/<topic>` with the chosen review skill. Point it at the ticket files, `foundation.md` and the Verify results rather than pasting them. Beyond its own checks it answers: does each Verify command really test its criterion; does the diff stay inside each ticket's Scope and out of its Out of scope. One round; after fixes, re-check only the findings that failed. Record the review's cumulative tokens for the report.

## 7. Evidence check

The `evidence-check` CI job on the integration PR. A red job is fixed in code, never by changing a ticket, test or CI (Never, Locks).

## 8. Merge

`land.py <pr> [--worktree <dir>] [--repo-root <dir>]` runs the `merge_gate.py` checks, updates the branch and waits for checks when it is behind, merges with a merge commit (`gh pr merge <n> --merge`), and only after `gh pr view --json state` says MERGED removes the worktree and deletes the local and remote branch. Do not poll or clean up by hand. Any failure prints why and touches nothing. Never squash, so `git revert -m 1 <sha>` undoes it. Deploy and publish are outside the Method: ask first.

## Report

Close with: finish line items, each with its evidence and result; the `user judges` items for the user; which checks failed or did not run; what was merged; guesses taken and fallbacks used; the review's cumulative tokens; number of questions to the user and the reason for each. Format: [grounded-answer.md](grounded-answer.md).
