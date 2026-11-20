# Audit: review-2.md
Plugin version: 0.0.0
Reviewed commit: 6e232721c94ef88a7fc7686df3be2c33ef47ffc8

## Problems
- none

## Rerun log
C1 `plugins/agent-flow/skills/agent-flow/references/workflow.md:48` expects `Run agent-flow: resume from docs/<topic>/discussion.md and the open issues.`: match
```

One subagent per ticket (`subagent_type: agent-flow:implementer`), one worktree each: `git worktree add ../<repo>-<NN> -b <topic>/<NN> <integration branch>`. Message and report format: [tickets.md](tickets.md). After a subagent ends, check for leftover processes (`pgrep -fl`, `lsof` to confirm the owner before killing) and remove its worktree when its PR is merged.

Session phases: once the finish line and tickets are agreed, tell the user to start implementation in a fresh session and give the exact line to type: `Run agent-flow: resume from docs/<topic>/discussion.md and the open issues.` The long design conversation is not carried into ticket coordination. A coordinating session that has handled many tickets suggests a fresh session the same way instead of continuing.

Follow-ups that belong to the finish line become new tickets; anything beyond it goes into Decisions as a question.


```

C2 `plugins/agent-flow/skills/agent-flow/references/workflow.md:26` expects `a doc lookup or research goes to a subagent that returns only the quoted lines and their source URL or path`: match
```

## 3. Research and CI first

Research order: official docs, source code, web search, then a trial run. Record sources. Keep large documents out of the coordinator: a doc lookup or research goes to a subagent that returns only the quoted lines and their source URL or path. If the network or a site is blocked, switch source; if a site is truly needed, tell the user which and why.

Find the repo's verify commands in its `package.json`, CI config, `CLAUDE.md` or `AGENTS.md`. Record them. If PRs have no CI running them, adding CI is ticket 01: CI runs only the verify commands, with no deploy and no secrets. If the default branch has no rule requiring a PR and green CI, set it when the plan allows (`gh api` branch protection); if not allowed, say so in Decisions, and `merge_gate.py` is the guard.


```

C3 `python3 -m unittest tests.test_land.LandTest.test_stop_file_blocks_before_update_branch tests.test_land.LandTest.test_gate_blocked_never_merges 2>&1 | tail -1` expects `OK`: match
```
OK

[exit 0]
```

C4 `python3 -m unittest tests.test_land.LandTest.test_merge_ok_but_not_merged_deletes_nothing tests.test_land.LandTest.test_merge_refused_touches_nothing tests.test_land.LandTest.test_merged_then_cleaned 2>&1 | tail -1` expects `OK`: match
```
OK

[exit 0]
```

C5 `plugins/agent-flow/scripts/land.py:55` expects `"--merge", "--match-head-commit", sha]`: match
```
        sha = json.loads(run(["gh", "pr", "view", a.pr, "--json", "headRefOid"], root)[1])["headRefOid"]
    except (json.JSONDecodeError, KeyError):
        return fail("could not read the PR head commit")
    rc, out = run(["gh", "pr", "merge", a.pr, "--merge", "--match-head-commit", sha], root)
    if rc:
        return fail("merge: " + out)
    try:

```

C6 `plugins/agent-flow/skills/agent-flow/references/workflow.md:21` expects `runs only after the user's explicit yes`: match
```

- Results, not methods. The user's words bound the scope. First ask what the user wants to happen after this is done; a larger version or better route goes into Decisions as an option, and you work to the original words meanwhile.
- Every line has external evidence: a test, a command, a measured number, a reproduction from raw data. If only the user can judge it, write `evidence: user judges`.
- Each evidence item names how it will be proven. A method that creates external resources (repos, services), runs real model calls, or spends the user's usage is listed with its estimated cost and runs only after the user's explicit yes. Until then run only checks that create nothing external and spend no model usage. This is an exception to asking only what cannot be found: ask it in the first question round of Intake (one round, at most 5 questions), not mid-run.
- Apply the four questions from [records.md](records.md).

## 3. Research and CI first

```

C7 `python3 -m unittest discover -s tests 2>&1 | tail -1` expects `OK`: match
```
OK (skipped=9)

[exit 0]
```

C8 `python3 scripts/no_cjk.py plugins/agent-flow; echo exit=$?` expects `exit=0`: match
```
exit=0

[exit 0]
```

Result: passed
