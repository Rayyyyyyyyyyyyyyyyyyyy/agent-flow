# Tickets

A ticket is one verifiable behavior, written so an implementer with no other context can do it and a script can check it. Whatever skill cuts the tickets, the files must follow this format: `verify.py` reads it. A front-end page is usually one ticket per component plus one ticket that assembles the page, blocked by them.

## Where

One file per ticket at `docs/<topic>/tickets/<NN>-<slug>.md`, numbered from `01` in dependency order (blockers first). Files are the source of truth; a GitHub issue, if the repo wants one, only links to the file. The directory is locked once the Plan PR merges (SKILL.md, Locks).

## Format

```markdown
# <imperative title naming the behavior>

Blocked by: 02, 03 | none

## What to build

The behavior, end to end, in a few sentences. Facts it rests on: foundation.md lines it cites.

## Scope

Files or modules the work may touch.

## Out of scope

What the implementer must not do.

## Acceptance

- [ ] <observable criterion>
  Verify: `<command>`
- [ ] <criterion only a person can judge>
  Owner judges: <what to look at and what counts as pass>
```

## Verify commands

- Each criterion has at least one `Verify:` line, or one `Owner judges:` line. `verify.py --check-only` rejects a criterion with neither.
- The exit code alone decides: 0 is PASS. One command, run as written from the repo root without a shell: no `|`, `;`, `&`, `>`, `<`, `$(`, `$?`, and no `sh -c` wrapper. Put a multi-step check in a script in the repo and call it.
- The command tests the behavior, not that a string exists in a file.
- Before implementation it fails for the reason the criterion states; it finishes by itself and leaves no server or process running.
- A ticket that changes a user interface has criteria for waiting, empty results, failure, repeated actions, keyboard operation, and where focus lands after re-render.
- `Owner judges:` is the exception. Any PR carrying such a criterion gets the label `agent-flow:owner-judges`; the user judges and merges it.
- A ticket with no code (docs, config) still has a Verify command (a check or a build); it needs no test-first step.
