# Audit

The audit checks that a review report stands: it re-runs the report's evidence. Run it on every report, every round:

```sh
python3 <plugin>/scripts/audit.py docs/<topic>/reviews/review-<round>.md --repo <repo>
```

It writes `review-<round>.audit.md` next to the report. Exit 0 passed, 1 failed, 3 partly unverified, 2 usage or setup error. The audit makes no `claude` call.

## Three states

- **passed**: every piece of evidence re-ran and its expectation appeared.
- **failed**: evidence is missing or malformed (a PASS without evidence, a FAIL without a reproduce command, an UNKNOWN without `Missing`, a Rebuttal without evidence), or an expectation did not appear. Fix what the audit points at, then save a new review as the next round. A finished report is never edited; add a Rebuttal instead.
- **partly unverified**: project commands could not run because no sandbox (macOS Seatbelt, Linux bwrap) is available. This blocks the merge. The audit lists the commands under `## Run these yourself`; give them to the user to run. The user may opt in, for that one run, to running them without a sandbox with `--unsandboxed`. The audit then records `WARNING: project commands ran without a sandbox`. Never pass `--unsandboxed` without that opt-in.

The result is the last line of the `.audit.md`: `Result: passed`, `Result: failed` or `Result: partly unverified`.

## Rules come from the installed plugin

The rules and `audit.py` are the ones in the installed plugin version, not the working tree. `.audit.md` records `Plugin version: <version>`. Never edit `audit.py`, the canaries or a `.audit.md` to make a report pass. If you disagree with an audit, give the report, the audit and your reason to the user; the main session cannot overturn it.

Spot-check, done by the user outside the session: clone the repo at that version's tag and re-run the audit.

```sh
git clone --branch v<version> <plugin repo url> <empty dir>
python3 <empty dir>/plugins/agent-flow/scripts/audit.py <report> --repo <repo>
```

The result must match the recorded `.audit.md`.

Canaries (trap reports the auditor must reject) are run by the maintainer before a release, never on a user's machine. Their stamp ships in the plugin; `audit.py` refuses to run when it is for another version.

## Merge gate

Merge only through `land.py`, which runs `merge_gate.py <pr-number>` and needs exit 0:

- CI is green;
- the highest-round `.audit.md` among the PR's changed files ends `Result: passed`;
- `.agent-flow/STOP` is absent and `.agent-flow/config` has no `merge: never`.

A blocked gate prints one `BLOCKED:` reason per line; fix the reason, do not bypass the gate.
