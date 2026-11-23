# Verify commands are fixed before implementation and checked by CI, not by a reviewer-fed audit

Status: accepted (2026-11-23)

The Base let the reviewer choose each criterion's evidence command and expected text, then re-ran them in `audit.py` under a local sandbox. That let a criterion pass on evidence that did not test it (a sandbox-blocked command still printed the expected `exit=1`; Position-only items passed behaviour criteria; criteria the reviewer left out could not fail; "user judges" items counted as passed). We decided instead that every ticket criterion carries a Verify command written when tickets are cut, merged in the Plan PR, and locked: a ticket or integration PR that touches the rule files, CI, or `docs/<topic>/tickets/` is refused by `merge_gate.py`. The Evidence check is a CI job that runs every locked Verify command at the PR head and judges by exit code (no pipes, `;` or `echo $?`); the CI runner is the sandbox. `merge_gate.py` also refuses a PR when any criterion lacks a Verify command. The reviewer no longer supplies evidence; Review only judges quality and whether each Verify command really tests its criterion.

## Consequences

- `audit.py`, `sandbox.py`, `canaries.py`, `pending_audits.py` and `review.py` are removed, with their tests and the bwrap / no-sandbox CI jobs.
- A Calling repo without CI gets CI as its first ticket; a criterion that cannot run in CI (local hardware, secrets) is `owner-judges` and is never merged by the agent.
- Changing a Verify command mid-run means stopping and asking the Owner.

## Considered options

- Keep the sandbox audit and add coverage checks: keeps a 16.7K script and two platform-specific sandboxes doing what CI already does at the right commit.
- Reviewer keeps choosing evidence, audited by a model: the same party sets and marks the test.
