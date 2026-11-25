# Review is code review against tasks.md; its per-task evidence table gates merge

Status: accepted (2026-11-25)

agent-flow is an abstract method run in other repos, so it cannot write their acceptance criteria; it can only set the floor. The Calling repo's OpenSpec change says what is accepted, and the Owner decided that each task in its `tasks.md` is the unit of acceptance, that CI and review are different checks (CI runs the program tests, the reviewer reads code), and that the evidence is the review checking the code task by task (`docs/agent-flow/discussion.md`, Decisions 2026-11-25). Until now the review only reported findings, nothing recorded which task it had checked, and "evidence" meant the CI job. We decided: the locked Verify commands stay as ADR 0001 set them and are the program tests the CI job runs (the job keeps its name `evidence-check`); step 6 is a code review by a reviewer that implemented nothing in the change, which gives every task in `tasks.md` `PASS` or `FAIL` with code-level evidence (`file:line` in the diff, and the covering test or why none) and posts that table as a PR comment naming the reviewed commit. `merge_gate.py` refuses an implementation PR unless the latest such comment covers every task with `PASS` and evidence, every task is ticked, and only merges were added after the reviewed commit, so `land.py` updating a branch that is behind keeps the review valid.

## Consequences

- The gate catches a skipped, incomplete, failed or stale review, not a forged one: the comment is posted with the same `gh` login the agent uses, so nothing proves who wrote it or that the review happened. The Boundaries forbid posting a record for a review that did not happen; the Owner can read the table on the PR.
- A merge commit's own edits are not inspected, so a change hidden in a merge after the review passes the staleness rule; the compare API lists at most 250 commits.
- Any fix after the review needs a new complete table for the new head, which costs a re-review round; the re-review re-judges only the tasks the fix touches or that failed and carries the other rows over.
- Calling repos that already have the `evidence-check` job need no CI change; their next integration PR needs a review evidence record.

## Considered options

- Review table in a committed file under `openspec/changes/<topic>/`: a commit after the review changes the head it names, and the file would need its own lock rules.
- Gate on a GitHub review approval: the agent cannot approve its own PR, and an approval carries no per-task evidence.
- Keep the review advisory and let CI alone gate: CI runs only what was fixed at the Plan PR and says nothing about whether the code does each task.
