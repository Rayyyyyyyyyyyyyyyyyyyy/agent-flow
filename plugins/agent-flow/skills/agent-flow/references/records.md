# Project records

Records live in the user's repo and are versioned with the code. Work log lives in PRs, not in a separate log file. Repo know-how (commands, conventions) belongs in the repo's `CLAUDE.md` or `AGENTS.md`.

| File | Holds |
|---|---|
| `docs/<topic>/discussion.md` | The goal record, below |
| `docs/<topic>/spec.md` | The spec |
| `docs/<topic>/foundation.md` | Facts the goal rests on, each with its source |
| `docs/<topic>/tickets/<NN>-<slug>.md` | Tickets ([tickets.md](tickets.md)) |
| `.agent-flow/skills.md` | Which installed skill serves each step |
| `GLOSSARY.md` | Domain terms |
| `docs/adr/NNNN-<title>.md` | Decisions that are hard to reverse, surprising, or a real trade-off |

`<topic>` is a short lowercase slug of the goal.

## discussion.md

Exactly these second-level headings, in this order. A script checks them.

```markdown
# <topic> - discussion

## Original words

> the user's words, verbatim; later additions appended below, each with its date

## Finish line

- C1 <result> evidence: <what outside the agent proves it: a command and its expected output, a file position, a measured number>
- C2 <result>
  Evidence: <same>

## Authorizations

> only what the user said, quoted, with the date. Never write one yourself.

## Decisions

- YYYY-MM-DD user|agent: <decision> (<reason>)

## Open questions

- <what is unresolved, and the next step>
```

Rules:

- Each finish-line item starts `- C<n> ` and carries `evidence:` (any case) on the line or an `Evidence:` line under it.
- Write results, not methods. Keep to the user's words; a bigger version or better route goes to Decisions as an option.
- A line only the user can judge says `evidence: user judges`.
- Before accepting a line, ask: what would the best person in this field do beyond this? Which rawest data does it start from? Which method and tools? What outside evidence settles it? Fold the first three answers into the line or the verify commands.
- Record the verify commands and the CI status (file, commands it runs) under Decisions.

## GLOSSARY.md

One entry per term the work coins or fixes the meaning of: `**Term**: one-sentence definition. Avoid: <synonyms not to use>`. Use the terms in tickets and code names. Update it when a decision changes a meaning.

## ADR

Write one only when a decision is hard to reverse, surprising without context, and a real trade-off. Format: title, `Status: accepted`, Context, Decision, Consequences, each one to three sentences. Link it from the Decisions line.
