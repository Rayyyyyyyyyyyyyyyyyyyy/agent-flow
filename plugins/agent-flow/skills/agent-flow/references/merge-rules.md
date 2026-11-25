# Merge rules

The floor for every PR or MR agent-flow merges: the Plan PR with `plan: agent`, the integration PR and the archive PR. Every rule must hold before `land.py` runs. The merge check (SKILL.md step 8) checks each one itself through the forge's CLI (`gh` for GitHub, `glab` for GitLab), read-only. A Calling repo adds its own rules in `.agent-flow/merge-rules.md`, locked like the rest of `.agent-flow/`; it may add rules, never remove or loosen one.

How to check:

- Run the command and read its output. A PR body, a report file, CI's summary line or another agent's word is not evidence.
- A command that fails, times out, is paged short or returns something you cannot read is `FAIL`, never `PASS`.
- Write one row per rule, `| Rule | PASS or FAIL | Command | What it showed |`, under the PR head sha the check ran on.
- GitLab (glab 1.x): add `-R <origin URL>` to every `glab mr` and `glab ci` command, and run `glab api` as `glab api --hostname <origin host> projects/<project>/...`, `<project>` being origin's project path URL-encoded (`group%2Fproject`). glab's default project and its `:id`/`:fullpath` placeholders follow an `upstream` remote when one exists, which would check another project.

## M1 Same code

The CI result, the review evidence and this check are all for the current head sha. A merge from the target branch added after the review (by `land.py`) is the only allowed difference; any other commit after them is `FAIL`. The merge itself pins the head (`gh pr merge --match-head-commit <sha>`; on GitLab the merge API with `sha`, which `land.py` calls).

- GitHub: `gh pr view <n> --json headRefOid,statusCheckRollup,comments`
- GitLab: `glab mr view <n> -F json` (`sha`, `head_pipeline.sha`)

## M2 Up to date with the target

A branch behind its target is updated and CI runs again on the result; a conflict is `FAIL` until resolved, and the resolving commit goes through CI and review like any other.

- GitHub: `gh pr view <n> --json mergeStateStatus,mergeable`
- GitLab: `glab api projects/<project>/merge_requests/<n>?include_diverged_commits_count=true` (`detailed_merge_status`, `has_conflicts`, `diverged_commits_count`). GitLab cannot update a branch with a merge, so `land.py` stops on a behind MR; merging the target into it with a merge commit and pushing is the update.

## M3 The diff is the change

Read the changed files, not the description. `FAIL` when the diff:

- changes a file outside the proposal's scope;
- changes a locked or `protect:` path outside a Plan PR, or the archive PR changes anything outside its change's OpenSpec paths;
- changes CI, test, lint, formatter or type-checker config outside a Plan PR;
- deletes or skips a test, or loosens one (an assertion removed, a tolerance raised, `skip`, `only` or `xfail` added).

- GitHub: `gh pr diff <n> --name-only`, then `gh pr diff <n>`
- GitLab: `glab mr diff <n> --raw`

## M4 Independent approval

PRs that need review evidence (step 6): the review evidence record is by a reviewer that is neither the PR author nor an implementer of this change, and it is newer than the last commit other than a merge from the target. The Plan PR and the archive PR are exempt, as in `merge_gate.py`.

- GitHub: `gh pr view <n> --json author,comments,reviews,commits`
- GitLab: `glab mr view <n> -F json` (`author`), `glab api projects/<project>/merge_requests/<n>/notes --paginate`, `glab api projects/<project>/merge_requests/<n>/approvals`

## M5 The platform enforces it

The target branch is protected: changes only through a PR or MR, the required checks must pass, and administrators cannot bypass it. Without that, anyone with write access, an agent included, can merge past every other rule. `FAIL` when protection is missing, unless the platform cannot provide it (doctor's warning) and the user accepted that under Decisions in `discussion.md`; then write that in the row.

- GitHub: `gh api repos/{owner}/{repo}/branches/<target>/protection` (404 means none)
- GitLab: `glab api projects/<project>/protected_branches/<target, URL-encoded>` (404 means none; `push_access_levels`, `merge_access_levels`, `allow_force_push`), `glab api projects/<project>` (`only_allow_merge_if_pipeline_succeeds`)

## M6 Merge commit

The merge is a merge commit: never squash, never rebase, so the reviewed sha stays in history and `git revert -m 1 <sha>` undoes it. `land.py` does this; a merge by any other command is `FAIL`. On GitLab the merge method is a project setting: `merge_gate.py` refuses unless it is a merge commit and squash is not required, and `land.py` merges with squash off.

- GitLab: `glab api projects/<project>` (`merge_method` is `merge`, `squash_option` is not `always`)

## M7 Nothing open

`FAIL` when any of these holds:

- a CI check is pending, failed, cancelled or missing;
- a review thread or finding is unresolved;
- the PR or MR is a draft;
- it carries the `agent-flow:owner-judges` label;
- the kill switch is set (`.agent-flow/STOP`, `merge: never`).

- GitHub: `gh pr checks <n>`, `gh pr view <n> --json isDraft,labels,reviewDecision`
- GitLab: `glab mr view <n> -F json` (`draft`, `blocking_discussions_resolved`, `labels`, `head_pipeline.status`), `glab ci status -b <source branch>`

## M8 After the merge

Checked once `land.py` returns. The state is `MERGED` (GitHub) or `merged` (GitLab) before anything is cleaned up; CI on the merge commit in the target branch is green; if the repo deploys, the deploy is confirmed or its rollback is known. A `FAIL` here is reported as not done; reverting is the user's call (Ask first).

- GitHub: `gh pr view <n> --json state,mergeCommit`, `gh run list --commit <merge sha>`
- GitLab: `glab mr view <n> -F json` (`state`, `merge_commit_sha`), `glab ci list --sha <merge sha> -F json`
