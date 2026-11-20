# Review

Run the deterministic gate first, then one independent review. Anything a command can verify never goes to an LLM.

## 1. Deterministic gate

Run the project's verify commands and every finish-line item's verify command. CI on the PR runs them again. On failure, return to implementation; no reviewer is started.

## 2. One review

Start a `reviewer` that took no part in the implementation. Give it the original words, the finish line, the project's test and CI commands, the location of the work, the diff range, and an **evidence pack**:

- the diff itself;
- the commands the gate ran, with an output summary;
- for each finish-line item, file excerpts as `path:line` plus the original text.

The reviewer works from the pack. It does not re-run a gate command whose output is in the pack; it writes that command into the report so the audit re-runs it in a sandbox. Write the dispatch message to a file and start the reviewer with `review.py <prompt-file> --cwd <repo>`. Aim for at most 25k tokens per review; trim the pack when it runs over.

The reviewer:

- judges every finish-line item PASS, FAIL or UNKNOWN, re-running the external evidence itself. The implementer's report is never evidence.
- reviews what the gate cannot: intent against the spec, shortcuts around the problem (sleep or timeout, swallowed errors, tests changed to pass), security and data risk. Only a problem that changes behavior, rules or acceptance results is a FAIL. Wording, comments and stale phrasing go under `## Findings outside the criteria`, which never blocks a merge.

## 3. Report

Save to `docs/<topic>/reviews/review-<round>.md`, in this format:

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
- Every evidence source line (`Command`, `Reproduce`, `Position`) is followed by one expectation line (`Output contains`, `Actual contains`, `Contains`). Expectations are at least 2 characters, except `[exit N]`, which matches the exit-code line `audit.py` appends to command output. To check an exit code, write ``Output contains: `[exit 0]` ``.
- An item may carry several evidence pairs. Pick an expectation that appears only on success: write `OK`, not `Ran 33 tests`, which a failing run prints too.
- A code problem is an item too: each behavior-changing problem is one FAIL whose `Criterion` names the standard or spec line it breaks. With no problems, a PASS item states the range checked, with evidence.

### Which commands the audit runs how

- `Position` is read directly from the file.
- A read-only command (on the argv allowlist in `audit.py`) runs without a shell.
- Any other command is a project command: it runs only inside the sandbox (no network, no `claude`, writes confined to a temporary worktree). If the evidence needs the network or `claude`, give a `Position` instead, or mark the item UNKNOWN and say what is missing.

## 4. After the report

Audit every report (see `audit.md`). The main session never edits the audit.

- **FAIL**: if the evidence holds, fix, re-run the gate, and start a new reviewer for the next round. If it does not hold, write a `## Rebuttal` in the same report with evidence, then audit again.
- **Next round reviews**: items that were FAIL, items the audit found unsound or under-evidenced, and items touching files this fix changed. Other audited PASS items are not re-reviewed.
- **Review passes** when the latest round has no FAIL and every item has an audited PASS in some round (or an UNKNOWN left for the user to judge).
- **At most two rounds.** If round 2 still has a FAIL, or an item went from PASS to FAIL, stop and list the remaining problems for the user. Do not run a third round.
- **UNKNOWN**: if the missing tool, environment or permission can be supplied, supply it and review again. Otherwise list the item as "done but unverified" and say what is missing.
- Merge only through `scripts/land.py <pr-number>`, which runs the merge gate and prints why when blocked.
