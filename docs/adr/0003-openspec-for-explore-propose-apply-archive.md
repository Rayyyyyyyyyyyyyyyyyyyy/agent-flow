# OpenSpec runs explore, propose, apply and archive; agent-flow only reads what it leaves

Status: accepted (2026-11-24)

The Owner chose OpenSpec for four steps of the Method in every Calling repo: `/opsx:explore` for a direction or seed, `/opsx:propose` for the spec and the work breakdown (replacing agent-flow's own ticket files), `/opsx:apply` for implementation, and `/opsx:archive` after merge, which folds each change into `openspec/specs/` so the repo keeps its current specs. agent-flow runs these commands as the user would and reads the files they leave; installing OpenSpec and `openspec init` are the user's, and `doctor.py` only checks that `openspec list --json` works. The Verify commands move under each `#### Scenario:` in the change's specs, which are locked after the Plan PR; `tasks.md` stays unlocked so apply can tick it. Archive gets its own PR kind, limited by `merge_gate.py` to the change's OpenSpec paths.

## Considered options

- Let step 0 pick OpenSpec like any other skill (ADR 0002 unchanged): the ticket format, locks and gate would have to support both OpenSpec and other ticket skills.
- Keep agent-flow tickets and use OpenSpec only for the narrative: two sources for the same work that drift apart.

## Consequences

- ADR 0002 now covers only the steps OpenSpec does not: research, test-first inside apply, review, PR body, retrospective.
- A Calling repo needs Node and OpenSpec; doctor stops the run until the user installs and inits it.
- `/opsx:apply` works through `tasks.md` in one session; parallel work comes from agent-flow giving each `## N.` group (with its `Blocked by:` line) to its own subagent and worktree.
- What archive's sync writes into `openspec/specs/` happens after the Evidence check and affects no gate.
