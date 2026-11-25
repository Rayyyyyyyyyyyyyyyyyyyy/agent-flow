# Workflow detail

Order: align the environment, receive, gather facts, propose and open the Plan PR, confirm with the user, apply, review, evidence check, merge, archive; then report. Do the thinking yourself (breaking down, deciding); give execution to implementer subagents and judgment of the result to a review in a separate context. Independent work may run in parallel subagents.

What the Method leaves open you decide yourself and keep going: record each such decision under Decisions as `Ruling: <what you decided> - <why> - <what it costs if wrong>`. Stop only for what Boundaries lists as Ask first, or when every way forward is a guess.

Commit after each step. Commit and push to working branches without asking. Every change reaches the default branch through a PR.

## Running OpenSpec

- Run `/opsx:explore`, `/opsx:propose`, `/opsx:apply` and `/opsx:archive` as the user would. If the session lists them as skills or commands, invoke them; otherwise find their files under the repo's `.claude/` or the user's `~/.claude/` and follow them as written.
- Read their results from the repo: `openspec list --json`, `openspec status --change <topic> --json`, and the files under `openspec/`. How OpenSpec inits, syncs or archives is OpenSpec's business; do not edit its schema or reorganise its files.
- Installing OpenSpec and `openspec init` are the user's (doctor prints the fix).

## 0. Align the environment

- For the steps OpenSpec does not cover, the source of truth is this session's own list of available skills and agents, not a fixed vendor list. Read each candidate's description; read its `SKILL.md` before relying on what it does.
- A skill marked `disable-model-invocation: true` cannot be called through the Skill tool: find its `SKILL.md` (user skills under `~/.claude/skills/<name>/`, plugin skills under `~/.claude/plugins/cache/*/*/*/skills/<name>/`) and follow it as written.
- Steps to fill: research (step 2), test-first inside apply (5), review (6), PR body (every PR), retrospective (after 9, optional). Front-end, security or domain skills join the step they serve.
- Record `.agent-flow/skills.md`:

  ```markdown
  | Step | Skill | Invoke | Model | Why |
  |---|---|---|---|---|
  | 6 review | <name> | Skill tool, or read <path> | opus | <one line> |
  ```

- Subagent models, by alias, from each task group's size (step 3): `haiku` for `small`, `sonnet` for `medium`, `opus` for `large`. The guess check (step 3) runs on `sonnet`. The review (step 6) runs on `sonnet` when every group is `small`, else on `opus`. Fix-loop rounds 4-5 (step 5) run one tier above the group's model. A small model takes more turns on multi-step work, so `small` is only for a group whose tasks spell out the whole change. Write the mapping in the Model column; a Calling repo may change it there. Pass the alias as `model` on every subagent call, including the ones a chosen skill starts without naming a model.

- Point the chosen skills at this layout: the change `openspec/changes/<topic>/`, records `docs/<topic>/`, glossary `GLOSSARY.md`, decisions `docs/adr/`. A review skill that looks for the originating spec gets `openspec/changes/<topic>/`.
- Redo step 0 when the installed skills change; the new `skills.md` goes in the next Plan PR.

Fallbacks, only for a step no installed skill covers:

| Step | Fallback |
|---|---|
| Research | A subagent reads primary sources and returns only quoted lines with their path or URL. |
| Test-first | Write the failing Verify command's test first, see it fail for the stated reason, then implement. |
| Review | One subagent with only: the review package file, `openspec/changes/<topic>/`, `foundation.md`, the report files. It reports findings with a concrete failing case each. |
| PR body | What changed, how it was checked (commands and results), the OpenSpec change. |

## 1. Receive the request

| The user gives | You do | Moves on when |
|---|---|---|
| **Goal**: a result they want | Write it as a finish line; no explore | Written |
| **Direction**: end point undecided | `/opsx:explore` with the user; offer 2-3 candidate finish lines, each with cost and a recommendation | The user picks one and says to move on |
| **Seed**: a loose idea | `/opsx:explore` with the user: research feasibility and similar work; ask only what cannot be found (preferences, resources, limits) | The user says to move on |

When unsure which, treat it as the more mature kind and say how you judged. Put the user's words in `discussion.md` verbatim ([records.md](records.md)). Explore is the user's discussion: do not end it, propose or implement from it on your own.

Finish line rules:

- Results, not methods. The user's words bound the scope. A larger version or better route goes into Decisions as an option; work to the original words meanwhile.
- Every line has external evidence: a test, a command, a measured number, a reproduction from raw data. If only the user can judge it, write `evidence: user judges`.
- Apply the four questions from [records.md](records.md).

## 2. Gather facts

Research order: official docs, source code, web search, then a trial run. Keep large documents out of the coordinator: research goes to a subagent or the chosen research skill, which returns quoted lines and their source. If the network or a site is blocked, switch source; if a site is truly needed, tell the user which and why.

`docs/<topic>/foundation.md` holds what the work rests on: one fact per line, each with its source; `assumption:` marks a fact with none. The proposal and design cite it; implementers and the review take facts from it rather than finding their own.

Then write the repo's own rules and verify. They can only be written after reading this repo, and they sit inside the Boundaries in SKILL.md (they may tighten a boundary, never loosen one):

- Verify commands: what proves a change works here (tests, build, lint, type check). Prefer what the repo already runs. Note what they do not cover.
- End-to-end tests: only when the repo needs them; many do not. A method that spends usage or creates external resources is asked in step 4, with its cost.
- Checks over prose: a rule that can be checked is written as a check, not as a line in `CLAUDE.md`. A mistake seen twice (a repeated review finding, guess or failure in this repo's records) becomes a lint rule, a test or a Verify command whose failure message says how to fix it. Config that makes such checks pass or fail (lint, formatter, type checker, test runner config) is locked with `protect: <glob>` lines in `.agent-flow/config`, one glob per line, matched against repo-relative paths.
- Merge conditions: `merge_gate.py` always requires CI green, the evidence check, a merged Plan PR, no locked-path change after it and no kill switch. The repo may add conditions; it may not remove one.
- Where: lasting rules go in the repo's `CLAUDE.md` or `AGENTS.md`; rules for this goal only go in `docs/<topic>/`. Record what you wrote under Decisions. If the default branch has no rule requiring a PR and green CI, set it when the plan allows (`gh api` branch protection, requiring `evidence-check`); if not allowed, say so in Decisions, and `merge_gate.py` is the guard.

Missing infrastructure that blocks evidence (raw data or logs, version and commit mapping, a reproducible environment) becomes the first task groups. Using secrets, money or the user's own data, a need for accounts you do not have, and browser use go to the user first (Boundaries, Ask first).

## 3. Propose and open the Plan PR

Run `/opsx:propose <topic>`. You decide the breakdown and record why in Decisions. Where propose would ask the user, take your recommended answer and list each such choice in the Plan PR body. The proposal's scope and non-goals come from the finish line; cite `foundation.md` for facts.

Every Scenario in `openspec/changes/<topic>/specs/**/spec.md` is one verifiable behavior. Under its WHEN/THEN lines, indented, it carries one or more Verify commands, or one `Owner judges:` line:

```markdown
#### Scenario: <behavior>
- **WHEN** <condition>
- **THEN** <observable outcome>
  Verify: `<command>`

#### Scenario: <behavior only a person can judge>
- **THEN** <outcome>
  Owner judges: <what to look at and what counts as pass>
```

- The exit code alone decides: 0 is PASS. One command, run as written from the repo root without a shell: no `|`, `;`, `&`, `>`, `<`, `$(`, `$?`, and no `sh -c` wrapper. Put a multi-step check in a script in the repo and call it.
- The command tests the behavior, not that a string exists in a file.
- Before implementation it fails for the reason the Scenario states; it finishes by itself and leaves no server or process running.
- A change to a user interface has Scenarios for waiting, empty results, failure, repeated actions, keyboard operation, and where focus lands after re-render. A front-end page is usually one task group per component plus one that assembles the page, blocked by them.
- `Owner judges:` is the exception. Any PR carrying such a Scenario gets the label `agent-flow:owner-judges`; the user judges and merges it.
- A change with no code (docs, config) still has a Verify command (a check or a build).

`tasks.md` holds implementation steps only, no Verify lines. Each `## N.` group is one unit of work and its first line names its blockers: `Blocked by: 1, 2` or `Blocked by: none`. Its second line names its size, which picks the implementer's model (step 0): `Size: small` (the tasks spell out the whole change in one or two files), `Size: medium` (several files, or integration between parts) or `Size: large` (design judgment or broad knowledge of the repo).

Once per change, start a fresh subagent (`model: sonnet`) with only `openspec/changes/<topic>/`. Ask: what would you build for each task group, and where must you guess? Fix the artifacts for guesses that would change a Verify result or an interface between groups.

Run `python3 .agent-flow/verify.py openspec/changes/<topic>/specs` on the unimplemented tree. Commands meant to fail must fail for the stated reason; each must finish by itself, leaving no server or process running.

Copy `${CLAUDE_PLUGIN_ROOT}/scripts/verify.py` to `.agent-flow/verify.py` when it is missing or differs. Add this job to the repo's CI workflow, replacing an `evidence-check` job that differs from it (create `.github/workflows/ci.yml` if none runs on pull requests), with the repo's own setup steps so its Verify commands can run:

```yaml
  evidence-check:
    if: ${{ startsWith(github.head_ref, 'agent-flow/') }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # the repo's setup steps (runtime, dependency install) go here
      - run: python3 .agent-flow/verify.py --head "$REF"
        env:
          REF: ${{ github.head_ref }}
```

`--head` picks the specs from the branch name (contracts: `verify.py`). The job reads only this change's specs, so other OpenSpec changes in the repo, written without Verify lines, do not fail it. The Plan PR only validates the specs; the integration PR runs every Verify command; the archive PR validates the archived copy, which gives it a passing check even when the repo's own CI runs only on the default branch. The job is skipped on PRs that are not agent-flow's. CI runs only verify commands: no deploy, no secrets.

Branches: push `agent-flow/<topic>` from the default branch, then `agent-flow/<topic>-plan` carrying `discussion.md`, `foundation.md`, `openspec/changes/<topic>/`, `.agent-flow/` (skills map, `verify.py`, config if any), CI changes and repo rules. Open the Plan PR into `agent-flow/<topic>`.

## 4. Confirm with the user

One message: the restated goal, the finish line, the task groups (what each delivers, what blocks it), the Plan PR link, the skills from step 0, and every item that needs a yes upfront (a verification method that spends usage or creates external resources, with its estimated cost). Ask whether the change and goal are right. Wait for the answer; record it in `discussion.md` (Original words for the user's words, Decisions for what changed). Changes the user asks for go into the Plan PR before it merges. This is the only planned question round after explore; later questions are only those Boundaries requires.

Session phases: tell the user to review and merge the Plan PR, then start apply in a fresh session with the exact line: `Run agent-flow: resume from docs/<topic>/discussion.md.` With `plan: agent`, land it yourself after the user's yes and continue. A coordinating session that has handled many task groups suggests a fresh session the same way instead of continuing.

## 5. Apply

On `agent-flow/<topic>`. Task groups run one at a time, in blocker order. Only with `apply: parallel` in `.agent-flow/config` do groups whose blockers are merged run at the same time, one subagent and one worktree each. The user sets it once a goal's groups merged without an open review finding: one agent delivers mergeable work before many run.

Work files live outside the tree, in `$(git rev-parse --git-common-dir)/agent-flow/<topic>/`: every worktree sees them and they are never committed. Before dispatching group N, write `group-N-brief.md` there: the group's text from `tasks.md`, the Verify commands it serves, interfaces and decisions from groups already merged, and your resolution of any ambiguity you noticed. Exact values (numbers, names, signatures) appear only in the brief.

Each implementer (`model:` from its group's size, step 0) gets one task group: one line on where the group fits, the brief path introduced as "read this first: it is your requirements", pointers to `openspec/changes/<topic>/`, `foundation.md`, `discussion.md`, its worktree and the integration branch, and the report path `group-N-report.md`. Never paste earlier groups' history into a dispatch. It runs `/opsx:apply <topic>` for its group only, test-first with the chosen skill, and ticks the group's tasks. It starts no subagents of its own, reviewers included. Always include: "Any judgment or 'I guess' you make yourself, however small, counts as a guess; report it." It writes the full report to the report file: status (`DONE`, `GUESSED`, `BLOCKED`), commit, each Verify command with its result, the guess list, what was not verified. It returns only the status, the commit, one line of test results and its concerns.

Merge each group into the integration branch, resolving conflicts in a separate subagent. Judge each guess: correct ones are recorded in the integration PR body; wrong ones are reverted and re-dispatched. A Scenario that is wrong itself needs a new Plan PR (Locks). After a subagent ends, check for leftover processes (`pgrep -fl`, `lsof` to confirm the owner before killing).

Follow-ups inside the finish line become new Scenarios and tasks in a new Plan PR; anything beyond it goes into Decisions as a question.

Fix loop, for a group whose Verify commands fail and for review findings (step 6). Rounds 1-3 go back to the same implementer (or a fresh one given the brief, the report file and the open findings). Rounds 4-5 go to a fresh implementer one model tier above, told: "a prior implementer tried this N times; the report file says what was tried". Every round fixes, re-runs the tests that cover the change, and appends the command and its output to the report file. Never fix in the coordinating session. After round 5, rule on each open finding yourself (`Ruling:`) when the spec settles it.

Stuck means: a problem survives round 5 and the spec does not settle it; or the next step needs something only the user can give. Save the work, tell the user with options and a recommendation, and continue unblocked work.

## 6. Review

Deterministic checks first: every Verify command passes locally and CI is green. Then write the review package to the work directory (step 5): `git log --oneline`, `git diff --stat` and `git diff -U10` of `<default branch>...agent-flow/<topic>`, redirected into `review-package.md`, so the diff never passes through your own context. One review of that file with the chosen review skill; every subagent it starts runs on the review model (step 0). Point it at the package, `openspec/changes/<topic>/`, `foundation.md` and the report files rather than pasting them. It does not re-run Verify commands: their results are in CI and the report files.

Beyond its own checks it answers: does each Verify command really test its Scenario; does the diff stay inside the proposal's scope and out of its non-goals; does the diff add a workaround, or a comment that explains one away instead of fixing it? Each of those is a finding. Workarounds that were in the repo before this goal are listed under Open questions, not fixed here.

One round. Findings go through the fix loop (step 5); the re-review gets only the open findings and a package of the fix diff (from the head the review saw). A finding of a kind this repo's records already show becomes a check (step 2), proposed in a new Plan PR. Record the review's cumulative tokens for the report.

## 7. Evidence check

The `evidence-check` CI job on the integration PR. A red job is fixed in code, never by changing a spec, test or CI (Never, Locks).

## 8. Merge

`land.py <pr> [--worktree <dir>] [--repo-root <dir>]` runs the `merge_gate.py` checks, updates the branch and waits for checks when it is behind, merges with a merge commit (`gh pr merge <n> --merge`), and only after `gh pr view --json state` says MERGED removes the worktree and deletes the local and remote branch. Do not poll or clean up by hand. Any failure prints why and touches nothing. Never squash, so `git revert -m 1 <sha>` undoes it. Deploy and publish are outside the Method: ask first.

## 9. Archive

From the updated default branch, create `agent-flow/<topic>-archive` and run `/opsx:archive <topic>`; it moves the change under `openspec/changes/archive/` and updates `openspec/specs/`, the repo's current specs. Answer its questions with your recommendation (sync the specs). Open the PR into the default branch and land it with `land.py`; `merge_gate.py` lets it through only when every changed file is under `openspec/specs/`, `openspec/changes/<topic>/` or `openspec/changes/archive/<date>-<topic>/`.

## Report

Close with: finish line items, each with its evidence and result; the `user judges` items for the user; which checks failed or did not run; what was merged and archived; guesses taken, rulings made and fallbacks used; the review's cumulative tokens; number of questions to the user and the reason for each. Format: [grounded-answer.md](grounded-answer.md).
