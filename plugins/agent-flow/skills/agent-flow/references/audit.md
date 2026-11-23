# Audit

The auditor checks whether a review report stands. It looks at two things: the reviewer's report ([review.md](review.md)) and the main session's rebuttals of FAIL items in it. It runs outside the pipeline: the main session runs `audit.py`, which first re-runs the report's evidence at the reviewed commit; when the report has a rebuttal, or with `--model`, a separate `claude -p` with no tools then judges it.

## When to run

Every review report is audited, every round:

```sh
python3 <plugin>/scripts/audit.py docs/<topic>/reviews/review-<round>.md --repo <repo> [--model]
```

It writes `review-<round>.audit.md` next to the report. Exit 0 passed, 1 failed, 3 partly unverified, 2 usage or setup error. To rebut a FAIL, write the rebuttal into the same report under `## Rebuttal` and audit again. Before the final report, run `python3 <plugin>/scripts/pending_audits.py <repo>`: it lists reports with no audit, an audit that did not pass, or a report changed after its audit (sha256). Anything listed blocks the wrap-up.

## How the audit judges

1. The script opens a temporary worktree at the reviewed commit and re-runs every piece of evidence. Any of these fails the report with no model call:
   - a PASS without evidence, a FAIL without a reproduce command, an UNKNOWN that does not say what is missing, a rebuttal without evidence;
   - a rerun whose output lacks the expected text;
   - a malformed item heading, an item-like heading inside a code fence, an unclosed fence, a report with no items, or a `Reviewer model` that names no known tier.

   The report's commands were chosen by the agent that wrote it, so project commands run only inside a sandbox (macOS Seatbelt, Linux bwrap): writes only to the temporary worktree and a scratch dir, no reads of `~/.ssh`, `~/.claude` and other secret dirs, network localhost only (macOS) or none (Linux). Read-only commands from a fixed allowlist run without a shell. When the repo has `node_modules`, it is linked read-only into the temporary worktree.
2. When the deterministic checks pass **and the report has a rebuttal**, the model judges: the main session is arguing for its own work and needs a third party. A report without a rebuttal passes here with no model call; add `--model` to have the model judge it too. **The default path only proves the evidence produces what the report says; it does not judge whether the evidence is on point or sufficient.** That is the reviewer's job, spot-checked later with `--model` (see Protection, point 3). Trap reports test the model path.

   The model is one tier above the reviewer (haiku → sonnet, sonnet → opus, opus → opus); opus when there is a rebuttal. It receives, in order: the baseline rules (`auditor/RULES.md` in the plugin), the project's rules, the report, the rerun log, the diff. It judges each item `upheld`, `not upheld` or `insufficient evidence`; the report passes only when every item is upheld.

## Three states

- **passed**: every piece of evidence re-ran, its expectation appeared, and the model (when called) upheld every item.
- **failed**: a deterministic check failed or the model did not uphold an item.
- **partly unverified**: project commands could not run because no sandbox is available. This blocks the merge. The audit lists the commands under `## Run these yourself`; give them to the user to run. The user may opt in, for that one run, to running them without a sandbox with `--unsandboxed`; the audit then records `WARNING: project commands ran without a sandbox`. Never pass `--unsandboxed` without that opt-in.

The result is the last line of the `.audit.md`. The `.audit.md` also records the report's sha256, the rules used and the model.

## Effect of the result

- A failed audit, whatever the reason, means a fresh reviewer subagent reviews again and saves the next round (`review-2.md`, `review-3.md`, ...). A finished report is never edited; to add to it, write a rebuttal. Fix the work or method problems the audit points at before the new review.
- A main-session rebuttal judged not upheld: that FAIL stands; go back to implementation and fix it.
- A reviewer's FAIL judged not upheld: it does not count as a FAIL and needs no fix; the next round's reviewer judges that item afresh.
- The main session cannot overturn an audit. If you disagree, give the report, the audit and your reason to the user to decide.
- Only a passed audit allows a merge or the wrap-up.

## Protection

The aim is "a change always shows", not "a change is impossible". An agent with Bash on the same machine can get around any local block, so checks sit where a change leaves a record:

1. **Rules from a fixed source.** The baseline rules and `audit.py` come from the installed plugin version, and `.audit.md` records it. The project's rules are read from the repo's origin default branch, never the working tree, so a PR cannot loosen the rules that judge it.
2. **Agent discipline.** Never edit `audit.py`, the rules, the project's trap reports or a `.audit.md` to make a report pass, and never hand-write an `.audit.md`. A failed audit is handled as in "Effect of the result"; disagreement goes to the user.
3. **Spot check by the user.** Everything local may have been changed, so the user spot-checks outside the session: clone the plugin at that version's tag and re-run a sampled report with `--model`, then compare with the recorded `.audit.md`.

```sh
git clone --branch v<version> <plugin repo url> <empty dir>
python3 <empty dir>/plugins/agent-flow/scripts/audit.py <report> --repo <repo> --model
```

That comparison is the final ground for "a change always shows".

## Rules: two layers

- **Baseline rules**: `auditor/RULES.md` in the plugin. Principles only.
- **Project rules**: `.agent-flow/auditor/RULES.md` in the project repo, written in flow step 3. The details live here: for each finish-line item, what evidence is on point and how deep it must be checked; what fake evidence commonly looks like in this project. Project rules may add detail, never loosen a principle; on a conflict the stricter side wins.

Project rules change through a PR like any other change, and take effect once merged to the default branch. The PR says which rule changed, why, and which checks ran.

A correction that can be written as a deterministic check (an `audit.py` check, or the project's lint or tests) becomes a check, not another sentence in the rules.

## Trap reports

Trap reports test the auditor against this project. They live in the project repo at `.agent-flow/auditor/canaries/`, with `expected.json` mapping each report to `passed` or `failed`, and cite the project's own code at real commits. Two kinds:

- **Planted flaws** (must fail): a PASS without evidence, a malformed heading, fabricated output, evidence that is real but off point, a rebuttal of a valid FAIL, a rebuttal without basis.
- **Clean reports** (must pass).

```sh
python3 <plugin>/scripts/canaries.py --repo <repo>           # skips when nothing it hashes changed
python3 <plugin>/scripts/canaries.py --repo <repo> --force
```

Every trap report goes through the model path, so a run spends model usage (ask first, upfront). All must match. When the project has trap reports, `audit.py` refuses to audit until they have passed with the current baseline and project rules, trap reports, `audit.py`, tier map and `claude` version (`.agent-flow/auditor/canary-stamp.txt`); then stop and ask the user. A new stamp is committed through a PR. The trap reports and their expected results need the user's approval.

## Merge gate

Merge only through `land.py`, which runs `merge_gate.py <pr-number>` and needs exit 0:

- CI is green;
- the highest-round `.audit.md` among the PR's changed files ends `Result: passed` and records the sha256 of its report as it is now;
- `.agent-flow/STOP` is absent and `.agent-flow/config` has no `merge: never`.

A blocked gate prints one `BLOCKED:` reason per line; fix the reason, do not bypass the gate.
