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
Also in `docs/<topic>/`: `foundation.md`, `spec.md`, `tickets/<NN>-<slug>.md`. Skill map: `.agent-flow/skills.md`.

## Branches (Calling repo)

Integration branch `agent-flow/<topic>`, cut from the default branch. Plan PR: head `agent-flow/<topic>-plan`, base `agent-flow/<topic>`. Integration PR: head `agent-flow/<topic>`, base the default branch.

## Ticket format (parsed by verify.py)

- A criterion is a line `- [ ] <text>` or `- [x] <text>`.
- Under it, indented: one or more `Verify: `<command>`` lines, or an `Owner judges: <text>` line. A `#` heading ends the criterion.
- A Verify command must not contain `|`, `;`, `&`, `>`, `<`, `$(`, `$?`, nor be `sh|bash|zsh|dash|fish ... -c ...`. It runs with `shell=False` (`shlex.split`) from the cwd, timeout 900 s; exit 0 is PASS.

## verify.py

- CLI: `verify.py [--check-only] [<tickets dir> ...]`; default dirs: `docs/*/tickets` under the cwd. Stdlib only; a Calling repo runs a copy at `.agent-flow/verify.py`.
- Output lines: `ERROR <file>:<line>: <reason>`, `PASS <file>:<line>: <command>`, `FAIL <file>:<line>: <command> (exit <n>)` plus up to 20 indented output lines, `OWNER <file>:<line>: <criterion>`.
- Exit 0 all passed (owner-judged criteria listed, not run), 1 a failure or a malformed ticket, 2 no ticket files. `--check-only` validates and runs nothing.

## merge_gate.py

- CLI: `merge_gate.py <pr-number> [--repo-root <dir>]`; exit 0 mergeable, 1 blocked (reasons printed one per line, each starting `BLOCKED:`), 2 setup error.
- Reads `gh pr checks <n> --json name,state,bucket` and `gh pr view <n> --json baseRefName,headRefName,headRefOid,labels`.
- CI: green when every bucket is `pass` or `skipping` and at least one is `pass`.
- Label `agent-flow:owner-judges` blocks.
- Plan PR (head ends `-plan`): blocked unless `.agent-flow/config` has `plan: agent`.
- Any other PR: a check named `evidence-check` must pass (the reason starts `CI ` so `land.py` treats it as pending); `gh pr list --base <head> --head <head>-plan --state merged --json mergeCommit` must return a Plan PR; `gh api repos/{owner}/{repo}/compare/<plan merge oid>...<headRefOid>` must list no file under `.agent-flow/`, `.github/workflows/` or `docs/*/tickets/`.
- Kill switch, read from `--repo-root` (default cwd): `.agent-flow/STOP` exists, or `.agent-flow/config` has `merge: never`. Config lines are `key: value`, case-insensitive.

## land.py

- CLI: `land.py <pr-number> [--worktree <dir>] [--repo-root <dir>]`; imports `merge_gate.main`, so its BLOCKED lines and exit codes pass through. Exit 0 merged, 1 blocked or failed, 2 setup error.
- Order: if `gh pr view <n> --json headRefName,mergeStateStatus` says `BEHIND`, first run the gate and stop on any reason not starting `BLOCKED: CI` (no remote write), then `gh pr update-branch <n>` and `gh pr checks <n> --watch`; run the full gate; `gh pr merge <n> --merge --match-head-commit <headRefOid>`; only when `gh pr view <n> --json state` is `MERGED`, `git worktree remove <dir>`, `git branch -D <branch>`, `git push origin --delete <branch>`. Any earlier failure prints why and changes nothing.

## Required CI checks (this repo)

`verify (macos-latest)`, `verify (ubuntu-latest)`.
