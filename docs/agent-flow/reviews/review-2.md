# Review: agent-flow round 2

Reviewer model: opus
Reviewed commit: 6e232721c94ef88a7fc7686df3be2c33ef47ffc8
Base: 4ee4b26c574be48cd0e1af2aa49e805d1e1d6a84

### C1 — PASS
Criterion: R1 makes session phases explicit. Implementation starts in a fresh session that resumes from discussion.md and the open issues, and the user is given a one-line prompt to type.
Position: `plugins/agent-flow/skills/agent-flow/references/workflow.md:48`
Contains: `Run agent-flow: resume from docs/<topic>/discussion.md and the open issues.`

### C2 — PASS
Criterion: R2 sends large documents and research to a subagent that returns only the quoted lines and their source.
Position: `plugins/agent-flow/skills/agent-flow/references/workflow.md:26`
Contains: `a doc lookup or research goes to a subagent that returns only the quoted lines and their source URL or path`

### C3 — PASS
Criterion: R3 says that when the PR is BEHIND, land.py runs the gate's non-CI checks (audit, kill switch) before `gh pr update-branch`. Any blocked result other than CI stops before any remote write.
Command: `python3 -m unittest tests.test_land.LandTest.test_stop_file_blocks_before_update_branch tests.test_land.LandTest.test_gate_blocked_never_merges 2>&1 | tail -1`
Output contains: `OK`

### C4 — PASS
Criterion: R3 says cleanup happens only after `gh pr view --json state` reports MERGED. If the merge is refused, or reports success while the state is not MERGED, the worktree and branches are left in place.
Command: `python3 -m unittest tests.test_land.LandTest.test_merge_ok_but_not_merged_deletes_nothing tests.test_land.LandTest.test_merge_refused_touches_nothing tests.test_land.LandTest.test_merged_then_cleaned 2>&1 | tail -1`
Output contains: `OK`

### C5 — PASS
Criterion: R3 says the merge uses a merge commit pinned to the PR head with `--match-head-commit`.
Position: `plugins/agent-flow/scripts/land.py:55`
Contains: `"--merge", "--match-head-commit", sha]`

### C6 — PASS
Criterion: R4 says that any verification method that creates external resources, runs real model calls or spends the user's usage needs the user's explicit yes, asked in the first (upfront) question round.
Position: `plugins/agent-flow/skills/agent-flow/references/workflow.md:21`
Contains: `runs only after the user's explicit yes`

### C7 — PASS
Criterion: The tests pass.
Command: `python3 -m unittest discover -s tests 2>&1 | tail -1`
Output contains: `OK`

### C8 — PASS
Criterion: There are no CJK characters in plugins/agent-flow.
Command: `python3 scripts/no_cjk.py plugins/agent-flow; echo exit=$?`
Output contains: `exit=0`

條件外發現

- `plugins/agent-flow/scripts/land.py:33`: if `gh pr view` returns JSON without `mergeStateStatus` or `headRefName` (for example, an error object), `info["mergeStateStatus"]` raises KeyError. The script then crashes with a traceback instead of exiting with code 2 as the documented setup error. No remote write happens before this point, so no data is lost.
- `plugins/agent-flow/scripts/land.py:40`: in the BEHIND path, blocked reasons are told apart only by whether they start with `BLOCKED: CI`. This works today because every CI reason in `merge_gate.py` starts with "CI". If a future non-CI reason also starts with "CI", it would be wrongly let through to update-branch.

