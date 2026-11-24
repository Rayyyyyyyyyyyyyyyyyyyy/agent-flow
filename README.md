# agent-flow

A Claude Code plugin that takes a goal from words to a merged, checked PR in the repo you run it in.

You say what you want. The agent writes the finish line, gathers sourced facts, confirms the task list with you, cuts tickets whose every criterion has a fixed `Verify:` command, locks those commands in a Plan PR, implements tickets in parallel, reviews once, re-runs every locked command in CI, and merges only through a gate script that refuses missing or weakened evidence.

Status: `0.0.0`, pre-release. The Method is implemented and unit-tested; it has not yet been proven end to end on a real goal.

## Requirements

- Claude Code
- `git`, and the GitHub CLI `gh`, logged in (`gh auth login`)
- Python 3.11+ (stdlib only, nothing to install)
- A Calling repo with an `origin` on GitHub that you can push to

The skill runs `doctor.py` first and prints the fix for anything missing. It warns when the token lacks the `workflow` scope (`gh auth refresh -s workflow`) or when a private repo on a free plan has no branch protection.

Windows: use WSL2.

## Install

```bash
claude plugin marketplace add Rayyyyyyyyyyyyyyyyyyyy/agent-flow
claude plugin install agent-flow@agent-flow
```

Or inside a session: `/plugin marketplace add Rayyyyyyyyyyyyyyyyyyyy/agent-flow`, then `/plugin install agent-flow@agent-flow`.

## Use

Open Claude Code in the repo you want changed and hand it a goal:

```text
/agent-flow:agent-flow add CSV export to the reports page
```

The skill also triggers on "run the flow" or "take this goal to merged". Openers that work:

```text
Goal: <what>. It is done when <finish line>.
Direction: I want <area> to get better; talk with me first about how far this run should go.
Seed: I have an idea, <idea>. Research it first and only ask what you cannot look up.
Continue <topic> from where it stopped.
```

A direction or seed is grilled with you before any work starts.

To pick up after a crash or on another machine, run the same command with the same goal (or the last opener above). The agent reads `docs/<topic>/discussion.md`, the tickets and the open PRs, and continues from the first unfinished step without duplicating branches, tickets or PRs.

### Cloud sessions and other machines

- The other session sees only what is pushed. agent-flow pushes its records and branches as it goes; push your own local changes before handing over.
- The plugin must be installed there too. For a cloud session, commit this to the Calling repo's `.claude/settings.json`:

  ```json
  {
    "extraKnownMarketplaces": {
      "agent-flow": { "source": { "source": "github", "repo": "Rayyyyyyyyyyyyyyyyyyyy/agent-flow" } }
    },
    "enabledPlugins": { "agent-flow@agent-flow": true }
  }
  ```

- Installed skills can differ between machines. Step 0 picks from what that session has and records the map in `.agent-flow/skills.md`; check it if results look different.

## What a run does

| Step | What happens |
|------|--------------|
| 0 Align | Picks one installed skill per step, with a reason; writes `.agent-flow/skills.md` |
| 1 Receive | Records your words verbatim and a draft finish line in `docs/<topic>/discussion.md` |
| 2 Gather | Writes `docs/<topic>/foundation.md`: every fact with a source, the rest marked `assumption`; writes the repo's own rules |
| 3 Confirm | Shows you the task list and the goal and waits for your answer |
| 4 Plan PR | Writes tickets in `docs/<topic>/tickets/`, adds the `evidence-check` CI job, opens the Plan PR |
| 5 Implement | After the Plan PR is merged, ready tickets run in parallel on `agent-flow/<topic>` |
| 6 Review | One review of the integration PR, reporting its token use |
| 7 Evidence check | CI re-runs every locked `Verify:` command at the PR head |
| 8 Merge | `land.py` runs `merge_gate.py`, updates a branch that is behind, and merges with a merge commit |

agent-flow brings no skills of its own for research, implementation or review. It uses whatever this session has installed (see `docs/adr/0002`).

## Safety

- **Plan PR**: you merge it yourself, which is your approval of every `Verify:` command before anything is built. Put `plan: agent` in `.agent-flow/config` to let the agent merge it.
- **Locks**: after the Plan PR merges, `.agent-flow/**`, `.github/workflows/**` and `docs/<topic>/tickets/**` change only through a new Plan PR. The gate refuses any other PR that touches them.
- **Owner-judged criteria**: a PR labelled `agent-flow:owner-judges` is never merged by the agent.
- **Kill switch**: create `.agent-flow/STOP`, or put `merge: never` in `.agent-flow/config`. PRs still open; nothing merges. Interrupt the session to stop everything.
- **Asks first**: deploying or publishing, writing to repos or services you do not own, notifying other people, using secrets, spending money, deleting your data, any browser use, and verification that creates external resources or spends your usage.

Running the skill in a repo is your consent to branch, commit, push, open PRs, set up CI and merge its own PRs through the gate. The full rules are in `plugins/agent-flow/skills/agent-flow/SKILL.md`.

## Files it writes in your repo

```text
.agent-flow/skills.md         step-to-skill map
.agent-flow/verify.py         copy of the Evidence check script, run by CI
.agent-flow/config            optional: plan: agent, merge: never
.github/workflows/...         the evidence-check job
docs/<topic>/discussion.md    your words, finish line, decisions, open questions
docs/<topic>/foundation.md    sourced facts
docs/<topic>/spec.md
docs/<topic>/tickets/NN-*.md
```

## Uninstall

```bash
claude plugin uninstall agent-flow@agent-flow
claude plugin marketplace remove agent-flow
```

Files already written in your repos stay; delete `.agent-flow/` and the `evidence-check` job by hand if you no longer want them.

## Develop

```bash
python3 -m unittest discover -s tests -v
python3 scripts/no_cjk.py plugins/agent-flow
python3 scripts/check_package.py
claude plugin validate .
```

Design: `docs/agent-flow/spec.md`. Interfaces between scripts: `docs/agent-flow/contracts.md`. Vocabulary: `GLOSSARY.md`. Decisions: `docs/adr/`.

## License

MIT. See `LICENSE` and `NOTICE`.
