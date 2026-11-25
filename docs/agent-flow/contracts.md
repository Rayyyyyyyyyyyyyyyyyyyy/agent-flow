# agent-flow — contracts between scripts

The interfaces the skill and its scripts rely on. A PR that changes one updates this file in the same PR.

## Paths

- Plugin root: `plugins/agent-flow/`. Scripts: `plugins/agent-flow/scripts/<name>.py`. Repo tooling: `scripts/`.
- Tests: `tests/test_<name>.py`, no `tests/__init__.py`. A test loads a plugin script with
  `sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))` and then `import <name>`, or runs it with `subprocess` and `sys.executable`.
- Run all tests: `python3 -m unittest discover -s tests -v`.
- CJK check: `python3 scripts/no_cjk.py <dir>` exits 1 and prints `file:line` when it finds a CJK character, else 0.

## Project records (Calling repo)

`docs/<topic>/discussion.md` has exactly these second-level headings, in this order (checked by `check_discussion.py`):
`## Original words`, `## Finish line`, `## Authorizations`, `## Decisions`, `## Open questions`.
Finish-line items are `- C<n> <text>`; each contains `evidence:` (case-insensitive) or a line `Evidence:` under it.
Also `docs/<topic>/foundation.md`, the OpenSpec change `openspec/changes/<topic>/` (proposal, design, `specs/**/spec.md`, `tasks.md`), the current specs `openspec/specs/`, and the skill map `.agent-flow/skills.md`.

## OpenSpec

agent-flow runs `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive` and reads the results; it does not change OpenSpec's files or schema. The change name is `<topic>`.

## Branches (Calling repo)

Integration branch `agent-flow/<topic>`, cut from the default branch. Plan PR: head `agent-flow/<topic>-plan`, base `agent-flow/<topic>`. Integration PR: head `agent-flow/<topic>`, base the default branch. Archive PR: head `agent-flow/<topic>-archive`, base the default branch, cut after the integration PR merged.

## Scenario format (parsed by verify.py)

- A criterion is a line `#### Scenario: <name>` in a spec file.
- Under it, indented: one or more `Verify: `<command>`` lines, or an `Owner judges: <text>` line. Any other heading ends the criterion.
- A Verify command must not contain `|`, `;`, `&`, `>`, `<`, `$(`, `$?`, nor be `sh|bash|zsh|dash|fish ... -c ...`. It runs with `shell=False` (`shlex.split`) from the cwd, timeout 900 s; exit 0 is PASS.
- `tasks.md`: each `## N.` group's first line is `Blocked by: <numbers>` or `Blocked by: none`; its second line is `Size: small`, `Size: medium` or `Size: large`. verify.py does not read it.

## verify.py

- CLI: `verify.py [--check-only] [<specs dir> ...]`; default dirs: `openspec/changes/*/specs` under the cwd (archived changes are not read); spec files are found recursively. Stdlib only; a Calling repo runs a copy at `.agent-flow/verify.py`.
- Output lines: `ERROR <file>:<line>: <reason>`, `PASS <file>:<line>: <command>`, `FAIL <file>:<line>: <command> (exit <n>)` plus up to 20 indented output lines, `OWNER <file>:<line>: <scenario>`.
- Exit 0 all passed (owner-judged Scenarios listed, not run), 1 a failure or a malformed spec, 2 no spec files. `--check-only` validates and runs nothing.
- `verify.py --head agent-flow/<topic>[-plan|-archive]` (no specs dirs with it): a `-plan` head validates `openspec/changes/<topic>/specs` (`--check-only`), an `-archive` head validates `openspec/changes/archive/YYYY-MM-DD-<topic>/specs` (`--check-only`; none found is exit 2), any other head runs `openspec/changes/<topic>/specs`. A head not starting `agent-flow/` is exit 2.
- CI job `evidence-check` runs only on heads starting `agent-flow/`, as `python3 .agent-flow/verify.py --head <head branch>`.

## merge_gate.py

- CLI: `merge_gate.py <pr-number> [--repo-root <dir>]`; exit 0 mergeable, 1 blocked (reasons printed one per line, each starting `BLOCKED:`), 2 setup error.
- Reads `gh pr checks <n> --json name,state,bucket` and `gh pr view <n> --json baseRefName,headRefName,headRefOid,labels`.
- CI: green when every bucket is `pass` or `skipping` and at least one is `pass`.
- Label `agent-flow:owner-judges` blocks.
- Archive PR (head ends `-archive`): `gh api repos/{owner}/{repo}/compare/<baseRefName>...<headRefOid>` must list only files under `openspec/specs/`, `openspec/changes/<topic>/` or `openspec/changes/archive/YYYY-MM-DD-<topic>/`.
- Plan PR (head ends `-plan`): blocked unless `.agent-flow/config` has `plan: agent`.
- Any other PR: a check named `evidence-check` must pass (the reason starts `CI ` so `land.py` treats it as pending); `gh pr list --base <head> --head <head>-plan --state merged --json mergeCommit` must return a Plan PR; `gh api repos/{owner}/{repo}/compare/<plan merge oid>...<headRefOid>` must list no file under `.agent-flow/`, `.github/workflows/`, `openspec/changes/*/specs/`, nor `openspec/config.yaml`, nor one matching a `protect:` glob (`fnmatch`, case-sensitive, against the repo-relative path).
- Kill switch, read from `--repo-root` (default cwd): `.agent-flow/STOP` exists, or `.agent-flow/config` has `merge: never`. Config lines are `key: value`, keys case-insensitive; values lower-cased except `protect:`, whose glob keeps its case and may repeat.

## .agent-flow/config (Calling repo)

Optional. Keys: `plan: agent` (the agent may land the Plan PR), `merge: never` (kill switch), `apply: parallel` (ready task groups run at the same time; default one at a time, read by the skill only), `protect: <glob>` (one per line; more paths locked like the fixed ones, read by `merge_gate.py` and `guard.py`).

## land.py

- CLI: `land.py <pr-number> [--worktree <dir>] [--repo-root <dir>]`; imports `merge_gate.main`, so its BLOCKED lines and exit codes pass through. Exit 0 merged, 1 blocked or failed, 2 setup error.
- Order: if `gh pr view <n> --json headRefName,mergeStateStatus` says `BEHIND`, first run the gate and stop on any reason not starting `BLOCKED: CI` (no remote write), then `gh pr update-branch <n>` and `gh pr checks <n> --watch`; run the full gate; `gh pr merge <n> --merge --match-head-commit <headRefOid>`; only when `gh pr view <n> --json state` is `MERGED`, `git worktree remove <dir>`, `git branch -D <branch>`, `git push origin --delete <branch>`. Any earlier failure prints why and changes nothing.

## guard.py

- PreToolUse hook, registered in `plugins/agent-flow/hooks/hooks.json` for `Edit|Write|MultiEdit|NotebookEdit|Bash` as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/guard.py"`. Reads the hook JSON (`tool_name`, `tool_input`, `cwd`) on stdin; always exits 0.
- Inactive (no output) unless the nearest directory above `cwd` holding `.git` also holds `.agent-flow/`.
- Locks on when the branch starts `agent-flow/` and does not end `-plan`. Then a file tool on a path matching `merge_gate.LOCKED` or a `protect:` glob, or a Bash command writing one (`cp`/`install`/`ln` destination, `mv`, `rm`, `tee`, `touch`, `truncate`, `dd of=`, `chmod`, `rmdir`, `sed -i`, `perl -i`, a `>`/`>>` redirect, `git rm|mv|checkout|restore|apply`), prints `permissionDecision: deny`.
- On any branch, a Bash command that can delete or overwrite work prints `permissionDecision: ask`: `git push` with `-f`, `--force*`, `-d`, `--delete`, `--mirror`, `--prune`, or a `+`/`:` refspec; `git reset --hard`; `git clean -f`; `git checkout -f|--force|--|.`; `git restore` other than `--staged`; `git branch -D`; `git stash drop|clear`; `git worktree remove --force`; `git filter-branch|filter-repo`, `git reflog expire`; recursive `rm`; `gh repo|release delete`. Commands are split on `&&`, `||`, `;`, `|`, `&` and newlines; `sh|bash|zsh|dash -c` strings are checked too.
- Unreadable input: `deny`; a command `shlex` cannot split: `ask`.
- Output: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": ..., "permissionDecisionReason": ...}}`; each reason says how to proceed.

## Work files (Calling repo)

`$(git rev-parse --git-common-dir)/agent-flow/<topic>/`, never committed: `group-N-brief.md`, `group-N-report.md`, `review-package.md`.

## doctor.py

- CLI: `doctor.py`, run from the Calling repo root. Prints `FAIL|WARN <what>` and `  Fix: <how>` per problem; exit 1 on any FAIL.
- FAIL: no `git`; no `gh`; `gh auth status` fails; no `origin`; no push access; no `openspec` on PATH; `openspec list --json` exits non-zero (repo not initialised); Python older than 3.11. WARN: private repo on a free plan (no branch protection); HTTPS remote without the `workflow` token scope.

## Required CI checks (this repo)

`verify (macos-latest)`, `verify (ubuntu-latest)`.
