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
- `tasks.md`: each `## N.` group's first line is `Blocked by: <numbers>` or `Blocked by: none`; its second line is `Size: small`, `Size: medium` or `Size: large`. Tasks are lines `- [ ] <id> <text>` or `- [x] <id> <text>`, `<id>` being dot-separated numbers such as `1.1`; lines without an id are not tasks. verify.py does not read it; merge_gate.py reads the tasks (Review evidence record).

## verify.py

- The test check: the program tests CI runs. Not the evidence: that is the Review evidence record.

- CLI: `verify.py [--check-only] [<specs dir> ...]`; default dirs: `openspec/changes/*/specs` under the cwd (archived changes are not read); spec files are found recursively. Stdlib only; a Calling repo runs a copy at `.agent-flow/verify.py`.
- Output lines: `ERROR <file>:<line>: <reason>`, `PASS <file>:<line>: <command>`, `FAIL <file>:<line>: <command> (exit <n>)` plus up to 20 indented output lines, `OWNER <file>:<line>: <scenario>`.
- Exit 0 all passed (owner-judged Scenarios listed, not run), 1 a failure, a malformed spec (including unbalanced quotes in a Verify command) or no `#### Scenario:` at all, 2 no spec files. `--check-only` validates and runs nothing.
- `verify.py --head agent-flow/<topic>[-plan|-archive]` (no specs dirs with it): a `-plan` head validates `openspec/changes/<topic>/specs` (`--check-only`), an `-archive` head validates `openspec/changes/archive/YYYY-MM-DD-<topic>/specs` (`--check-only`; none found is exit 2), any other head runs `openspec/changes/<topic>/specs`. A head not starting `agent-flow/` is exit 2.
- CI job `evidence-check` (name kept from before ADR 0005 so Calling repos already set up need no change) runs only on heads starting `agent-flow/`, as `python3 .agent-flow/verify.py --head <head branch>`.

## merge_gate.py

- CLI: `merge_gate.py <pr-number> [--repo-root <dir>]`; exit 0 mergeable, 1 blocked (reasons printed one per line, each starting `BLOCKED:`), 2 setup error.
- Forge (`merge_gate.forge(root)`): `forge:` in `.agent-flow/config`, else `gitlab` when the host of `git remote get-url origin` contains `gitlab` (case-insensitive), else `github`; any other `forge:` value is a setup error (exit 2; doctor FAIL).
- Fail closed: every `gh` call except `gh pr checks` (which exits non-zero while checks are pending) and every `glab` call must exit 0 (both print an HTTP error body on stdout); a failed call, bad JSON or a missing field is a setup error (exit 2), or a BLOCKED reason inside the review evidence check.
- GitHub: reads `gh pr checks <n> --json name,state,bucket` and `gh pr view <n> --json baseRefName,headRefName,headRefOid,labels`. Changed files are `gh api repos/{owner}/{repo}/compare/<a>...<b> --jq '.files[] | .filename, .previous_filename // empty'` (a rename's old path counts); a list of 300 files (the API's silent limit) is a setup error. A commit compare whose `total_commits` differs from the length of `commits` (the API lists at most 250) is unreadable.
- GitLab: every call is `glab api --hostname <origin host> projects/<url-encoded origin path>/...` run in `--repo-root` (`merge_gate.origin`: ssh, scp-like or https origin; anything else is a setup error). glab's own `:fullpath` is not used: it follows an `upstream` remote when one exists. MR `merge_requests/<n>` (`target_branch`, `source_branch`, `sha`, `labels`, `head_pipeline`); project (`merge_method`, `squash_option`): blocked unless `merge_method` is `merge` and `squash_option` is not `always`. Checks are a `pipeline` check from `head_pipeline.status` (it covers trigger jobs, which the jobs list leaves out) plus the jobs of `pipelines/<id>/jobs --paginate` (`name`, `status`, `allow_failure`), only when `head_pipeline.sha` is the MR's `sha`, else none. Job and pipeline buckets: `success` pass; `skipped`, or `failed`/`manual` with `allow_failure`, skipping; `failed`, `canceled` fail; anything else pending. Plan MR: `merge_requests?state=merged&source_branch=<head>-plan&target_branch=<head> --paginate`, its `merge_commit_sha` or else `sha`. Compare: `repository/compare?from=<a>&to=<b>` (merge base); changed files are `old_path` and `new_path` of each of `diffs`; `compare_timeout` true or 500 or more diffs (GitLab truncates at `diff_max_files` without saying so) is a setup error; commits are `commits[]` (`id`, `parent_ids`). A merged results pipeline (on the merge ref, another sha) is not read, so such an MR has no checks and stays blocked.
- CI: green when every bucket is `pass` or `skipping` and at least one is `pass`.
- Label `agent-flow:owner-judges` blocks.
- Archive PR (head ends `-archive`): the compare from `baseRefName` to `headRefOid` must list only files under `openspec/specs/`, `openspec/changes/<topic>/` or `openspec/changes/archive/YYYY-MM-DD-<topic>/`.
- Plan PR (head ends `-plan`): blocked unless `.agent-flow/config` has `plan: agent`.
- Any other PR: a check named `evidence-check` must pass (the reason starts `CI ` so `land.py` treats it as pending); `gh pr list --base <head> --head <head>-plan --state merged --json mergeCommit` (GitLab: the Plan MR above) must return a Plan PR; the compare from the Plan PR's merge commit to `headRefOid` must list no file under `.agent-flow/`, `.github/workflows/`, `openspec/changes/*/specs/`, nor `.gitlab-ci.yml` or `openspec/config.yaml`, nor one matching a `protect:` glob (`fnmatch`, case-sensitive, against the repo-relative path); and the review evidence below must pass.
- Review evidence, for the same PRs (topic is the head without `agent-flow/`): reads `gh api repos/{owner}/{repo}/contents/openspec/changes/<topic>/tasks.md?ref=<headRefOid> -H "Accept: application/vnd.github.raw"`, `gh pr view <n> --json comments`, `gh api repos/{owner}/{repo}/compare/<reviewed sha>...<headRefOid>` and `gh api repos/{owner}/{repo}/compare/<baseRefName>...<headRefOid>`. GitLab reads `repository/files/<url-encoded path>/raw?ref=<sha>`, the MR's non-`system` notes (`merge_requests/<n>/notes --paginate`, `id`, `body`, `system`; the latest by `id` counts) and the compares above; the reviewed commit is an ancestor of the head when the compare from the head to it lists no commit. Blocked when: no task line is read; a task is not ticked; no comment carries the marker; the latest record (by `createdAt`) has no row for a task, a verdict other than exactly `PASS`, or an empty evidence cell (several rows for one task must all pass); the reviewed commit is not an ancestor of the head (compare status not `identical` or `ahead`); a commit after it that is not on the base branch has fewer than two parents; the comments or a compare are unreadable. None of these reasons starts `CI`, so `land.py` stops on them before updating a branch.
- Kill switch, read from `--repo-root` (default cwd): `.agent-flow/STOP` exists, or `.agent-flow/config` has `merge: never`. Config lines are `key: value`, keys case-insensitive; values lower-cased except `protect:`, whose glob keeps its case and may repeat.

## Review evidence record (integration PR)

- A PR comment (GitLab: an MR note) whose body starts with `<!-- agent-flow:review commit=<sha> -->` (`<sha>`: the full 40-character lowercase sha of the PR head the review read), posted with `gh pr comment <n> --body-file <file>` (GitLab: `glab api --hostname <host> projects/<project>/merge_requests/<n>/notes -F body=@<file>`).
- Then a Markdown table `| Task | Verdict | Evidence |`: one row `| <id> | PASS or FAIL | <evidence> |` per task id in `tasks.md`. Evidence is `file:line` in the diff and the test that covers it, or why none does. Other lines (header, separator, findings) are ignored.
- Only the latest record counts. After it, only merge commits may be added (`land.py`'s update from the base branch); any other commit needs a new complete record for the new head.
- The gate checks that a record exists, covers every task with `PASS` and matches the code; it cannot check who wrote it or whether the review was honest (ADR 0005).

## .agent-flow/config (Calling repo)

Optional. Keys: `plan: agent` (the agent may land the Plan PR), `merge: never` (kill switch), `apply: parallel` (ready task groups run at the same time; default one at a time, read by the skill only), `protect: <glob>` (one per line; more paths locked like the fixed ones, read by `merge_gate.py` and `guard.py`), `forge: github|gitlab` (overrides the origin URL guess).

`.agent-flow/merge-rules.md` (Calling repo, optional, locked): merge rules added to the shipped `references/merge-rules.md` (M1-M8); read by the merge check (SKILL.md step 8). It may add rules, never remove or loosen one.

## land.py

- CLI: `land.py <pr-number> [--worktree <dir>] [--repo-root <dir>]`; imports `merge_gate.main`, so its BLOCKED lines and exit codes pass through. Exit 0 merged, 1 blocked or failed, 2 setup error.
- Order: if `gh pr view <n> --json headRefName,mergeStateStatus` says `BEHIND`, first run the gate and stop on any reason not starting `BLOCKED: CI` (no remote write), then `gh pr update-branch <n>` (its merge commit keeps the review evidence valid) and `gh pr checks <n> --watch`; read `headRefOid`, then run the full gate (a commit pushed after that read is refused by the merge); `gh pr merge <n> --merge --match-head-commit <headRefOid>`; only when `gh pr view <n> --json state` is `MERGED`, `git worktree remove <dir>`, `git branch -D <branch>`, `git push origin --delete <branch>` (skipped when `git ls-remote --exit-code --heads origin <branch>` exits 2: the forge deleted it on merge). Any earlier failure prints why and changes nothing.
- GitLab: the head is `sha` of `merge_requests/<n>?include_diverged_commits_count=true`, read before the gate; a non-zero `diverged_commits_count` stops it before the gate with no remote write (GitLab has no merge-based branch update; merge the target in, push, run again); the merge is `PUT .../merge_requests/<n>/merge -f sha=<sha> -F squash=false` through the same origin-pinned `glab api`, and `state` must then read `merged`.

## guard.py

- PreToolUse hook, registered in `plugins/agent-flow/hooks/hooks.json` for `Edit|Write|MultiEdit|NotebookEdit|Bash` as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/guard.py"`. Reads the hook JSON (`tool_name`, `tool_input`, `cwd`) on stdin; always exits 0.
- Inactive (no output) unless the nearest directory above `cwd` holding `.git` also holds `.agent-flow/`.
- Locks on when the branch starts `agent-flow/` and does not end `-plan`. Then a file tool on a path matching `merge_gate.LOCKED` or a `protect:` glob, or a Bash command writing one (`cp`/`install`/`ln` destination, `mv`, `rm`, `tee`, `touch`, `truncate`, `dd of=`, `chmod`, `rmdir`, `sed -i`, `perl -i`, a `>`/`>>` redirect, `git rm|mv|checkout|restore|apply`), prints `permissionDecision: deny`.
- On any branch, a Bash command that can delete or overwrite work prints `permissionDecision: ask`: `git push` with `-f`, `--force*`, `-d`, `--delete`, `--mirror`, `--prune`, or a `+`/`:` refspec; `git reset --hard`; `git clean -f`; `git checkout -f|--force|--|.`; `git restore` other than `--staged`; `git branch -D`; `git stash drop|clear`; `git worktree remove --force`; `git filter-branch|filter-repo`, `git reflog expire`; recursive `rm`; `gh|glab repo|release delete`. Commands are split on `&&`, `||`, `;`, `|`, `&` and newlines; `sh|bash|zsh|dash -c` strings are checked too.
- Unreadable input: `deny`; a command `shlex` cannot split: `ask`.
- Output: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": ..., "permissionDecisionReason": ...}}`; each reason says how to proceed.

## Work files (Calling repo)

`$(git rev-parse --git-common-dir)/agent-flow/<topic>/`, never committed: `group-N-brief.md`, `group-N-report.md`, `review-package.md`, `review-evidence.md` (the record before it is posted), `merge-check.md` (the merge check's head sha, then `| Rule | PASS or FAIL | Command | What it showed |` per rule).

## doctor.py

- CLI: `doctor.py`, run from the Calling repo root. Prints `FAIL|WARN <what>` and `  Fix: <how>` per problem; exit 1 on any FAIL.
- GitLab (by `merge_gate.forge`): FAIL no `glab`; no usable `origin`; `glab auth status --hostname <origin host>` fails; the origin project unreadable; role below 30 (the higher of `permissions` and `projects/<project>/members/all/<user id>`, which includes roles inherited from parent groups); `merge_method` not `merge`; `squash_option` `always`. The GitHub checks below are skipped.
- FAIL: no `git`; no `gh`; `gh auth status` fails; no `origin`; no push access; no `openspec` on PATH; `openspec list --json` exits non-zero (repo not initialised); Python older than 3.11. WARN: private repo on a free plan (no branch protection); HTTPS remote without the `workflow` token scope.

## Required CI checks (this repo)

`verify (macos-latest)`, `verify (ubuntu-latest)`.
