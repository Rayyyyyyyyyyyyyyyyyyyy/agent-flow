# Tickets

A ticket is one verifiable behavior, written so an implementer with no other context can do it and a reviewer can check it.

## Where

- Repo has a GitHub remote and `gh` is logged in: one GitHub issue per ticket.
- Otherwise (local fallback): one file per ticket at `docs/<topic>/issues/<NN>-<slug>.md`, numbered from `01`, with a `Status:` line near the top (`open`, `claimed`, `done`) and comments appended under `## Comments`. Resolving a ticket sets `Status: done` and appends the commit.

## Marker

Every issue (or file) and every PR body contains `<!-- agent-flow:<topic>#<NN> -->` with `<NN>` the two-digit ticket number. Before creating one, search for the marker and reuse a match. Search: `gh issue list --state all --search '"agent-flow:<topic>#<NN>" in:body'` and `gh pr list --state all --search '"agent-flow:<topic>#<NN>" in:body'`; in the local fallback, grep `docs/<topic>/issues/`.

## Required fields

```markdown
**What to build:** the behavior, end to end, in a few sentences.

**Blocked by:** #<n>, or "none".

**Scope:** files or modules the work may touch.

**Out of scope:** what the implementer must not do.

- [ ] acceptance criterion, observable

**Verify:**
- `<command run as written>` -> <result that means PASS>

<!-- agent-flow:<topic>#<NN> -->
```

- Title: imperative, names the behavior.
- Verify: every command runs as written from the repo root and says what PASS looks like. A check that needs a person or a browser says so and says how.
- A ticket that changes a user interface lists how it handles waiting, empty results, failure, repeated actions, keyboard operation, and where focus lands after re-render.
- Tickets that change CI or tests are ordinary tickets; the agent merges them.
- A ticket with no code (docs, config) needs no test-first step.

## Dispatch message to the implementer

Only: ticket location (issue number or file path), `docs/<topic>/discussion.md` path, working directory, integration branch, verify commands. Always include: "Any judgment or 'I guess' you make yourself, however small, counts as a guess, so the status cannot be DONE."

Report back: status (`DONE`, `GUESSED`, `BLOCKED`), PR URL, commit, each Verify command with its result, the guess list, what was not verified.

Handling a report: judge each guess. Correct guesses go into the ticket as a comment; wrong ones: revert those commits, fix the ticket, re-dispatch. `GUESSED` with all guesses correct counts as `DONE`. `BLOCKED` goes back to cutting tickets (step 4). A second `BLOCKED`, or a second revert, on one ticket means stuck.
