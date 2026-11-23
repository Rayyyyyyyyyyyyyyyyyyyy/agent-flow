# agent-flow v0.1 — contracts between tickets

Every ticket follows these. A ticket that needs to change one says so in its PR and updates this file in the same PR.

## Paths

- Plugin root: `plugins/agent-flow/`. Scripts: `plugins/agent-flow/scripts/<name>.py`. Repo tooling: `scripts/`.
- Tests: `tests/test_<name>.py`, no `tests/__init__.py`. A test loads a plugin script with
  `sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))` and then `import <name>`, or runs it with `subprocess` and `sys.executable`.
- Run all tests: `python3 -m unittest discover -s tests -v`.
- CJK check before #2 exists: `python3 scripts/no_cjk.py <dir>` (added in #1) exits 1 and prints `file:line` when it finds a CJK character, else 0.

## Project records (written by the skill, checked by `check_discussion.py`)

`docs/<topic>/discussion.md` has exactly these second-level headings, in this order:
`## Original words`, `## Finish line`, `## Authorizations`, `## Decisions`, `## Open questions`.
Finish-line items are `- C<n> <text>`; each contains `evidence:` (case-insensitive) or a line `Evidence:` under it.
Specs: `docs/<topic>/spec.md`. Review reports: `docs/<topic>/reviews/review-<round>.md`; audits next to them as `review-<round>.audit.md`.

## Ticket marker

Every issue and PR body created by the flow contains `<!-- agent-flow:<topic>#<NN> -->`.

## Review report format (written by the reviewer, parsed by audit.py)

```
# Review: <topic> round <n>

Reviewer model: <model>
Reviewed commit: <full sha>
Base: <full sha>            (optional)

### C1 — PASS
Criterion: <text>
Command: `<command run from the repo root>`
Output contains: `<text>`

### C2 — PASS
Criterion: <text>
Position: `<repo-relative path>:<line>`
Contains: `<text>`

### C3 — FAIL
Criterion: <text>
Reproduce: `<command>`
Actual contains: `<text>`
Expected: <text>

### C4 — UNKNOWN
Criterion: <text>
Missing: <what would be needed>

## Rebuttal
### C3
Reason: <text>
Command: `<command>`
Output contains: `<text>`
```

- Item headings are exactly `### <ID> — PASS|FAIL|UNKNOWN` (em dash). Other headings must not contain PASS, FAIL, UNKNOWN or Rebuttal.
- Every evidence source line (`Command`, `Reproduce`, `Position`) is followed by one expectation line (`Output contains`, `Actual contains`, `Contains`). Expectations are at least 2 characters, except `[exit N]`, which matches the exit-code line audit.py appends to command output.
- An item may carry several evidence pairs.

## audit.py

- CLI: `audit.py <report> --repo <repo> [--unsandboxed] [--model]`. `--model` lets the model judge a report without a rebuttal; a report with a rebuttal is always judged by the model.
- `Reviewer model:` must name a tier (`haiku`, `sonnet`, `opus`, as a substring). The judging model is one tier up (haiku→sonnet, sonnet→opus, opus→opus), opus when there is a rebuttal.
- Rules: `plugins/agent-flow/auditor/RULES.md`, then the project's `.agent-flow/auditor/RULES.md` read with `git show <origin default branch>:<path>` after `git fetch origin` (no origin: baseline only; fetch failure: exit 2). Prompt order: rules, `# Report under audit`, report, `# Rerun log`, log, `# Diff`, `git diff <base> <commit>` or `git show <commit>` (≤ 200,000 characters).
- Model reply: one line per item `<ID>: upheld|not upheld|insufficient evidence - <basis>`, per rebuttal `Rebuttal <ID>: ...`, at most one `Result: passed|failed`. Passes only when every item (rebutted FAILs via their rebuttal) is `upheld`, no item is judged twice, and any Result line says passed.
- Trap gate: when `<repo>/.agent-flow/auditor/canaries/expected.json` exists and `<repo>/.agent-flow/auditor/canary-stamp.txt` differs from `audit.stamp(repo, rules)` (sha256 of rules, `claude --version`, tier map, `audit.py`, every file under `canaries/`), exit 2 naming `canaries.py`.
- Exit codes: 0 passed, 1 failed, 3 partly unverified, 2 usage or setup error (bad report path, git failure, trap gate).
- Output file: `<report without .md>.audit.md`. First line `# Audit: <report file name>`. Then, with `--unsandboxed`, the line `WARNING: project commands ran without a sandbox`; `Plugin version: <version from plugin.json>`, `Report sha256: <hex>`, `Reviewed commit:`, `Rules: <sources>`, `Model: <model or none>`; sections `## Problems`, `## Rerun log`, `## Model verdict`, and `## Run these yourself` listing unverified commands. Last line exactly `Result: passed`, `Result: failed` or `Result: partly unverified`.

## canaries.py

- CLI: `canaries.py --repo <repo> [--force]`. Reads `<repo>/.agent-flow/auditor/canaries/expected.json` (`{"<report>.md": "passed"|"failed"}`), audits a copy of each report (outside the repo) against `<repo>` on the model path, prints `OK` or `MISS` per report. Exit 0 all matched and the stamp was written, 1 a mismatch (no stamp), 2 setup error. Skips with exit 0 when the stamp already matches, unless `--force`.

## pending_audits.py

- CLI: `pending_audits.py [repo]`. In every worktree, the latest `docs/*/reviews/review-<n>.md` per directory must have a `.audit.md` with the line `Report sha256: <its current sha256>` and last line `Result: passed`. Exit 0 none pending, 1 pending (one line each).

## sandbox.py

- `available() -> str | None`: `"seatbelt"`, `"bwrap"` or `None`. The environment variable `AGENT_FLOW_SANDBOX=none` forces `None`.
- `run(cmd: str, cwd: Path, writable: list[Path], timeout: int = 600) -> tuple[int, str]`: runs `/bin/sh -c cmd` inside the sandbox; returns exit code and combined output. Raises `RuntimeError` when no sandbox is available.
- Denied reads: `~/.ssh`, `~/.claude`, `~/.config`, `~/.aws`, `~/.gnupg`, `~/.netrc`. Writes only to `writable` (resolved real paths), `/dev/null`, `/dev/fd`. Network: macOS localhost only; Linux none.

## merge_gate.py

- CLI: `merge_gate.py <pr-number> [--repo-root <dir>]`; exit 0 mergeable, 1 blocked (reasons printed one per line, each starting `BLOCKED:`), 2 setup error.
- CI: `gh pr checks <n> --json name,state,bucket`; green when every bucket is `pass` or `skipping` and at least one is `pass`.
- Audit: among files changed in the PR (`gh pr diff <n> --name-only`) matching `docs/*/reviews/review-*.audit.md`, take the highest round; its last line must be `Result: passed` and it must contain `Report sha256: <sha256 of review-<n>.md in --repo-root>`.
- Kill switch: read from `--repo-root` (default cwd): `.agent-flow/STOP` exists, or `.agent-flow/config` has a line `merge: never`.

## land.py

- CLI: `land.py <pr-number> [--worktree <dir>] [--repo-root <dir>]`; imports `merge_gate.main`, so its BLOCKED lines and exit codes pass through. Exit 0 merged, 1 blocked or failed, 2 setup error.
- Order: if `gh pr view <n> --json headRefName,mergeStateStatus` says `BEHIND`, first run the gate's non-CI checks (audit, kill switch; blocked means no remote write), then `gh pr update-branch <n>` and `gh pr checks <n> --watch`; run the full gate; `gh pr merge <n> --merge --match-head-commit <headRefOid>`; only when `gh pr view <n> --json state` is `MERGED`, `git worktree remove <dir>`, `git branch -D <branch>`, `git push origin --delete <branch>`. Any earlier failure prints why and changes nothing.

## review.py

- CLI: `review.py <prompt-file> [--cwd <repo>] [--model opus]`; prints the reviewer's final text, then one line `[review tokens: <last-context tokens>; cost $<total_cost_usd with 2 decimals>]`.

## Required CI checks

`verify (macos-latest)`, `verify (ubuntu-latest)`; #8 adds `sandbox (ubuntu-bwrap)` and `sandbox (none)`.
