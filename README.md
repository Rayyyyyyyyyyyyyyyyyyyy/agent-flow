# agent-flow

A Claude Code plugin that takes a goal from words to a merged, checked PR in the repo you run it in.

You say what you want. The agent explores it with you through [OpenSpec](https://github.com/Fission-AI/OpenSpec) until you move on, gathers sourced facts, proposes an OpenSpec change whose tasks say what is accepted and whose every Scenario has a fixed `Verify:` command (the program tests), locks those commands in a Plan PR you approve, applies the tasks one group at a time (in parallel once you allow it), has a reviewer who did not write the code check it against each task and post PASS or FAIL with evidence per task, re-runs every locked command in CI, merges only through a gate script that refuses missing, failed or stale evidence and weakened tests, and archives the change into the repo's current specs.

agent-flow is an abstract method: it cannot know what your repo should accept, so it sets only the floor. What is accepted is the OpenSpec change you approve.

Status: pre-release. The version is in `plugins/agent-flow/.claude-plugin/plugin.json` (`claude plugin list` shows it) and is raised only to release: installs stay on the last released version, and `claude plugin update agent-flow@agent-flow` picks up the next one. Each new version is tagged `v<version>` and published as a GitHub release after CI passes on `main` (a pre-release while the version is 0.x). The Method is implemented and unit-tested; it has not yet been proven end to end on a real goal.

## Requirements

- Claude Code
- `git`, and the GitHub CLI `gh` logged in (`gh auth login`), or for a GitLab origin the GitLab CLI `glab` logged in (`glab auth login --hostname <host>`)
- Python 3.11+ (stdlib only, nothing to install)
- OpenSpec (`npm install -g @fission-ai/openspec@latest`, Node 20.19+), and `openspec init` run once in each Calling repo
- A Calling repo with an `origin` on GitHub or GitLab that you can push to; on GitLab the project's merge method must be Merge commit and squash must not be required (set `forge: gitlab` in `.agent-flow/config` when the host name does not contain `gitlab`)

The skill runs `doctor.py` first and prints the fix for anything missing; installing OpenSpec and `openspec init` are left to you. It warns when the token lacks the `workflow` scope (`gh auth refresh -s workflow`) or when a private repo on a free plan has no branch protection.

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
Take the OpenSpec change <name> to merged.
```

Every request is explored unless you say it is a goal or to skip explore; the agent never decides that on its own. A goal goes straight to its finish line. A direction or seed is explored with you through `/opsx:explore`; you decide when to move on to propose.

Or run `/opsx:explore` and `/opsx:propose` yourself first, then name the change. When every artifact is done, the agent skips explore and propose, keeps your scope, and only adds what the gate needs: a Verify command per Scenario and each task group's blockers and size, listed in the Plan PR for you to approve.

To pick up after a crash or on another machine, run the same command with the same goal (or the last opener above). The agent reads `docs/<topic>/discussion.md`, `openspec/changes/<topic>/` and the open PRs, and continues from the first unfinished step without duplicating branches, changes or PRs.

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

- Installed skills can differ between machines. For the steps OpenSpec does not cover, step 0 picks from what that session has and records the map in `.agent-flow/skills.md`; check it if results look different.

## What a run does

| Step | What happens |
|------|--------------|
| 0 Align | Checks OpenSpec; picks one installed skill for each other step, with a reason; writes `.agent-flow/skills.md` |
| 1 Receive | Records your words verbatim and the finish line in `docs/<topic>/discussion.md`; explores a direction or seed with you through `/opsx:explore` |
| 2 Gather | Writes `docs/<topic>/foundation.md`: every fact with a source, the rest marked `assumption`; writes the repo's own rules |
| 3 Propose | `/opsx:propose` writes `openspec/changes/<topic>/` with a `Verify:` command under every Scenario; adds the `evidence-check` CI job; opens the Plan PR |
| 4 Confirm | Shows you the goal and the task groups and waits for your answer; merging the Plan PR is the go-ahead |
| 5 Apply | `/opsx:apply`, one task group at a time on `agent-flow/<topic>` (ready groups in parallel with `apply: parallel`); each group's model follows its size |
| 6 Code review | A reviewer that is not the implementer reads the integration PR's diff against each task in `tasks.md` and posts a table on the PR: `PASS` or `FAIL` per task with `file:line` and the covering test; reports its token use |
| 7 Test check | CI's `evidence-check` job re-runs every locked `Verify:` command (the program tests) at the PR head |
| 8 Merge | A separate agent checks every merge rule (same code, up to date, the diff is the change, independent approval, platform protection, merge commit, nothing open) read-only through `gh`/`glab`; then `land.py` runs `merge_gate.py` (green tests, every task `PASS` in the latest review table on the current code), updates a branch that is behind, and merges with a merge commit |
| 9 Archive | `/opsx:archive` folds the change into `openspec/specs/`, merged through the gate |

OpenSpec runs explore, propose, apply and archive (see `docs/adr/0003`). For research and review agent-flow brings no skills of its own; it uses whatever this session has installed (see `docs/adr/0002`).

## Safety

- **Plan PR**: you merge it yourself, which is your approval of every `Verify:` command before anything is built. Put `plan: agent` in `.agent-flow/config` to let the agent merge it.
- **Locks**: after the Plan PR merges, `.agent-flow/**`, `.github/workflows/**`, `.gitlab-ci.yml`, `openspec/config.yaml` and `openspec/changes/<topic>/specs/**` change only through a new Plan PR. The gate refuses any other PR that touches them; the archive PR may change only its change's OpenSpec paths. Add `protect: <glob>` lines to `.agent-flow/config` to lock more, such as lint or test config.
- **Guard hook**: the plugin's `guard.py` runs before every edit and shell command in a repo that has `.agent-flow/`. On `agent-flow/*` branches it refuses writes to locked paths when they happen, not only at merge; on any branch it asks you before force pushes, `reset --hard`, `clean -f`, recursive `rm` and other commands that can delete work. In repos without `.agent-flow/` it does nothing.
- **Review evidence**: the gate refuses an implementation PR unless the latest review table covers every task in `tasks.md` with `PASS` and evidence, every task is ticked, and nothing but merges was pushed after the reviewed commit. It catches a skipped or stale review, not a dishonest one (`docs/adr/0005`).
- **Owner-judged criteria**: a PR labelled `agent-flow:owner-judges` is never merged by the agent.
- **Kill switch**: create `.agent-flow/STOP`, or put `merge: never` in `.agent-flow/config`. PRs still open; nothing merges. Interrupt the session to stop everything.
- **Asks first**: deploying or publishing, writing to repos or services you do not own, notifying other people, using secrets, spending money, deleting your data, any browser use your own instructions do not already permit, and verification that creates external resources or spends your usage.

Running the skill in a repo is your consent to branch, commit, push, open PRs, set up CI and merge its own PRs through the gate. The full rules are in `plugins/agent-flow/skills/agent-flow/SKILL.md`.

## Files it writes in your repo

```text
.agent-flow/skills.md         step-to-skill map
.agent-flow/verify.py         copy of the test check script, run by CI
.agent-flow/config            optional: plan: agent, merge: never, apply: parallel, protect: <glob>, forge: gitlab
.github/workflows/...         the evidence-check job (the program tests; .gitlab-ci.yml on GitLab)
docs/<topic>/discussion.md    your words, finish line, decisions, open questions
docs/<topic>/foundation.md    sourced facts
openspec/changes/<topic>/     the OpenSpec change (proposal, design, specs, tasks)
openspec/specs/               current specs, updated by archive
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
