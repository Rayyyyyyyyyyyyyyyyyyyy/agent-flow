# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`agent-flow` is a Claude Code plugin, and the repo is also its marketplace (`.claude-plugin/marketplace.json` points at `plugins/agent-flow/`). The plugin ships one skill (`skills/agent-flow/SKILL.md` + `references/`) that takes a goal to a merged PR, and the deterministic Python scripts the skill calls. Repo-level tooling (`scripts/`, `tests/`, CI) lives outside the plugin directory and is not shipped.

Source of truth for design and current state:
- `docs/agent-flow/spec.md` — problem, decisions, scope.
- `docs/agent-flow/contracts.md` — the interfaces between scripts (CLI, exit codes, ticket format, branches, paths). A change to a contract updates this file in the same PR.
- `docs/agent-flow/discussion.md` — finish line, user decisions, and `## Open questions` (the hand-off: what to do next and what must be asked first).

## Commands

Python 3 stdlib only; no install step.

```bash
python3 -m unittest discover -s tests -v          # all tests
python3 -m unittest tests.test_verify -v          # one file
python3 -m unittest tests.test_merge_gate.MergeGateTest -v   # one class
python3 scripts/no_cjk.py plugins/agent-flow      # shipped text must be CJK-free
python3 scripts/check_package.py                  # personal-data / packaging checks
claude plugin validate .                          # manifest validation
```

CI (`.github/workflows/ci.yml`) runs all of the above on macOS and Ubuntu and installs the plugin into a fresh HOME.

## Architecture

Vocabulary: `GLOSSARY.md`. Why it is shaped this way: `docs/adr/0001` (locked Verify commands checked by CI), `docs/adr/0002` (skills chosen from the environment).

The skill (`skills/agent-flow/SKILL.md`, steps 0-8) runs in a Calling repo and uses that session's installed skills for most steps. The plugin's own pieces, in `plugins/agent-flow/scripts/`:

1. `doctor.py`: preflight the skill runs first.
2. `verify.py`: the Evidence check. Parses `docs/<topic>/tickets/*.md` criteria and runs each `Verify:` command (`shell=False`, exit code decides). The skill copies it to the Calling repo's `.agent-flow/verify.py` for its `evidence-check` CI job; stdlib only.
3. `merge_gate.py`: CI green; Plan PR (`agent-flow/<topic>-plan`) only with `plan: agent`; other PRs need a passing `evidence-check`, a merged Plan PR, and no locked-path change since it; no `agent-flow:owner-judges` label; no kill switch.
4. `land.py`: imports `merge_gate.main`, updates a BEHIND branch, merges with a merge commit (`--match-head-commit`), cleans up only after `MERGED`.

Interfaces between them: `docs/agent-flow/contracts.md`.

Tests import plugin scripts by inserting `plugins/agent-flow/scripts` into `sys.path` (no `tests/__init__.py`), or run them via `subprocess` with `sys.executable`.

## Constraints on shipped files

`check_package.py` fails the build if anything under `plugins/agent-flow/` contains personal paths (`/Users/`, `/home/<name>`), email addresses, CJK characters, the words `rtk`/`ponytail`, or `Asia/Taipei`, or if a skill other than `agent-flow` is bundled. The owner's GitHub handle is forbidden in every tracked file except `README.md`, `marketplace.json`, `LICENSE`, `NOTICE`, `docs/` and `tests/` — this includes this file. Shipped text is English.

## Working rules from past decisions

- Verification methods that create external resources, run real model calls, or spend the user's usage (E2E runs, fixture repos, canaries) need the user's explicit yes first. A fabricated fixture-repo E2E was rejected and reverted for this reason.
- Check `## Open questions` in `discussion.md` before starting work; several items there are explicitly "ask the user".
