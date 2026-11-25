# Verify commands are fixed before implementation and checked by CI, not by a reviewer-fed audit

Status: accepted (2026-11-23); amended 2026-11-25 by ADR 0005: the Verify commands are the program tests CI runs, and "evidence" now means the review's per-task table

The Base let the reviewer choose each criterion's evidence command and expected text, then re-ran them in `audit.py` under a local sandbox. That let a criterion pass on evidence that did not test it (a sandbox-blocked command still printed the expected `exit=1`; Position-only items passed behaviour criteria; criteria the reviewer left out could not fail; "user judges" items counted as passed). We decided instead that every Scenario in the goal's OpenSpec change carries a Verify command written at propose, merged in the Plan PR, and locked: an integration PR that touches the rule files, CI, `openspec/config.yaml` or the change's specs is refused by `merge_gate.py` (ADR 0003). The test check (CI job `evidence-check`, called the Evidence check until ADR 0005) runs every locked Verify command at the PR head and judges by exit code (no pipes, `;` or `echo $?`); the CI runner is the sandbox. `merge_gate.py` also refuses a PR when any Scenario lacks a Verify command. The reviewer no longer chooses or runs the tests; since ADR 0005 it reviews the code against each task and its per-task table is the evidence the gate requires.

## Consequences

- A Calling repo without CI gets CI as its first task group; a criterion that cannot run in CI (local hardware, secrets) is `owner-judges` and is never merged by the agent.
- Changing a Verify command mid-run means stopping and asking the Owner.

## Considered options

- Keep the sandbox audit and add coverage checks: keeps a 16.7K script and two platform-specific sandboxes doing what CI already does at the right commit.
- Reviewer keeps choosing evidence, audited by a model: the same party sets and marks the test.
