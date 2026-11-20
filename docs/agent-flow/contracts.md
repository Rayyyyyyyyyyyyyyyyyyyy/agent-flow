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

- CLI: `audit.py <report> --repo <repo> [--unsandboxed] [--model <model>]`.
- Exit codes: 0 passed, 1 failed, 3 partly unverified, 2 usage or setup error (bad report path, stamp mismatch, git failure).
- Output file: `<report without .md>.audit.md`. First line `# Audit: <report file name>`. Contains `Plugin version: <version from plugin.json>` and, with `--unsandboxed`, the line `WARNING: project commands ran without a sandbox`. Unverified commands are listed under `## Run these yourself`. Last line exactly `Result: passed`, `Result: failed` or `Result: partly unverified`.

## sandbox.py

- `available() -> str | None`: `"seatbelt"`, `"bwrap"` or `None`. The environment variable `AGENT_FLOW_SANDBOX=none` forces `None`.
- `run(cmd: str, cwd: Path, writable: list[Path], timeout: int = 600) -> tuple[int, str]`: runs `/bin/sh -c cmd` inside the sandbox; returns exit code and combined output. Raises `RuntimeError` when no sandbox is available.
- Denied reads: `~/.ssh`, `~/.claude`, `~/.config`, `~/.aws`, `~/.gnupg`, `~/.netrc`. Writes only to `writable` (resolved real paths), `/dev/null`, `/dev/fd`. Network: macOS localhost only; Linux none.

## merge_gate.py

- CLI: `merge_gate.py <pr-number> [--repo-root <dir>]`; exit 0 mergeable, 1 blocked (reasons printed one per line, each starting `BLOCKED:`), 2 setup error.
- CI: `gh pr checks <n> --json name,state,bucket`; green when every bucket is `pass` or `skipping` and at least one is `pass`.
- Audit: among files changed in the PR (`gh pr diff <n> --name-only`) matching `docs/*/reviews/review-*.audit.md`, take the highest round; its last line must be `Result: passed`.
- Kill switch: read from `--repo-root` (default cwd): `.agent-flow/STOP` exists, or `.agent-flow/config` has a line `merge: never`.

## land.py

- CLI: `land.py <pr-number> [--worktree <dir>] [--repo-root <dir>]`; imports `merge_gate.main`, so its BLOCKED lines and exit codes pass through. Exit 0 merged, 1 blocked or failed, 2 setup error.
- Order: if `gh pr view <n> --json headRefName,mergeStateStatus` says `BEHIND`, run `gh pr update-branch <n>` and `gh pr checks <n> --watch`; run the gate; `gh pr merge <n> --merge`; only when `gh pr view <n> --json state` is `MERGED`, `git worktree remove <dir>`, `git branch -D <branch>`, `git push origin --delete <branch>`. Any earlier failure prints why and changes nothing.

## review.py

- CLI: `review.py <prompt-file> [--cwd <repo>] [--model opus]`; prints the reviewer's final text, then one line `[review tokens: <last-context tokens>; cost $<total_cost_usd with 2 decimals>]`.

## Canary stamp

- `plugins/agent-flow/auditor/canary-stamp.txt`: line 1 `version: <plugin version>`, then one line per canary `<name>: ok`.
- audit.py exits 2 with `canary stamp is for <x>, plugin is <y>; maintainer must run scripts/run_canaries.py` when versions differ. Tests that are not about the stamp set `AGENT_FLOW_SKIP_STAMP=1`.

## Required CI checks

`verify (macos-latest)`, `verify (ubuntu-latest)`; #8 adds `sandbox (ubuntu-bwrap)` and `sandbox (none)`.
