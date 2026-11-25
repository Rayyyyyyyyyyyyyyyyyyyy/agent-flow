# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`agent-flow` is a Claude Code plugin, and the repo is also its marketplace (`.claude-plugin/marketplace.json` points at `plugins/agent-flow/`). The plugin ships one skill (`skills/agent-flow/SKILL.md` + `references/`) that takes a goal to a merged PR, running OpenSpec (`/opsx:*`) for explore, propose, apply and archive, and the deterministic Python scripts the skill calls. Repo-level tooling (`scripts/`, `tests/`, CI) lives outside the plugin directory and is not shipped.

Source of truth for design and current state:
- `docs/agent-flow/spec.md` — problem, decisions, scope.
- `docs/agent-flow/contracts.md` — the interfaces between scripts (CLI, exit codes, Scenario format, branches, paths). A change to a contract updates this file in the same PR.
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

CI (`.github/workflows/ci.yml`) runs all of the above on macOS and Ubuntu and installs the plugin into a fresh HOME. After `ci` passes on a push to `main`, `.github/workflows/release.yml` runs `scripts/release.py <sha>`: it creates tag and GitHub release `v<version>` once per version (`--prerelease` while 0.x; `--dry-run` prints the `gh` command).

## Architecture

Vocabulary: `GLOSSARY.md`. Why it is shaped this way: `docs/adr/0001` (locked Verify commands checked by CI), `docs/adr/0002` (skills chosen from the environment), `docs/adr/0003` (OpenSpec for explore, propose, apply, archive), `docs/adr/0004` (a hook enforces locks and Ask-first commands before tools run), `docs/adr/0005` (review is code review against `tasks.md`; its per-task evidence table gates merge).

The skill (`skills/agent-flow/SKILL.md`, steps 0-9) runs in a Calling repo: OpenSpec for explore, propose, apply and archive, that session's installed skills for research, review and the rest. agent-flow only reads what OpenSpec leaves in the repo. It is an abstract method: it sets only the floor; the Calling repo's OpenSpec change says what is accepted, `tasks.md` task by task. The plugin's own pieces, in `plugins/agent-flow/scripts/`:

1. `doctor.py`: preflight the skill runs first, including that `openspec list --json` works.
2. `verify.py`: the test check (the program tests CI runs). Parses each `#### Scenario:` in `openspec/changes/<topic>/specs/**/spec.md` and runs its `Verify:` commands (`shell=False`, exit code decides). The skill copies it to the Calling repo's `.agent-flow/verify.py` for its `evidence-check` CI job; stdlib only.
3. `merge_gate.py`: CI green; Plan PR (`agent-flow/<topic>-plan`) only with `plan: agent`; archive PR (`agent-flow/<topic>-archive`) only inside its change's OpenSpec paths; other PRs need a passing `evidence-check` (the test check job; name kept), a merged Plan PR, no locked-path or `protect:` change since it, and a review evidence record (PR comment) giving every task in `openspec/changes/<topic>/tasks.md` `PASS` on the current code; no `agent-flow:owner-judges` label; no kill switch.
4. `land.py`: imports `merge_gate.main`, reads the head commit before the gate, updates a BEHIND branch (GitHub; on GitLab it stops), merges that commit with a merge commit (`--match-head-commit`, or the GitLab merge API with `sha` and squash off), cleans up only after the PR or MR reads as merged.
5. `guard.py`: the plugin's PreToolUse hook (`hooks/hooks.json`), active only in a repo with `.agent-flow/`: denies edits and shell writes to locked or `protect:` paths on `agent-flow/*` branches except `-plan`, asks before commands that can delete work, fails closed on unreadable input (ADR 0004).

The forge is GitHub (`gh`) or GitLab (`glab`), picked by `merge_gate.forge` from `.agent-flow/config` or origin's host; every forge read fails closed. Interfaces between them: `docs/agent-flow/contracts.md`.

Tests import plugin scripts by inserting `plugins/agent-flow/scripts` into `sys.path` (no `tests/__init__.py`), or run them via `subprocess` with `sys.executable`. Fake `gh` and `glab` executables stand in for the forges; never call a real GitLab or GitHub API from a test. The fake `glab` helpers (`GLAB_HEADER`, `gitlab_api`, `fake_glab`) live in `tests/test_merge_gate.py`; `test_land.py` and `test_doctor.py` import them after inserting `tests/` too.

## Constraints on shipped files

`check_package.py` fails the build if anything under `plugins/agent-flow/` contains personal paths (`/Users/`, `/home/<name>`), email addresses, CJK characters, the words `rtk`/`ponytail`, or `Asia/Taipei`, or if a skill other than `agent-flow` is bundled. The owner's GitHub handle is forbidden in every tracked file except `README.md`, `marketplace.json`, `LICENSE`, `NOTICE`, `docs/` and `tests/` — this includes this file. Shipped text is English.

## Working rules from past decisions

- agent-flow is an abstract method tool: a change belongs here only if it is part of what the plugin owns and holds for every Calling repo; one environment's situation is met by that repo's config (`protect:`), rules and CI. GitLab support is gate and land correctness or parity with GitHub, never a check tuned to one host, and every forge read fails closed. Tests never call a real GitLab or GitHub instance.
- Verification methods that create external resources, run real model calls, or spend the user's usage (E2E runs, fixture repos, canaries) need the user's explicit yes first. A fabricated fixture-repo E2E was rejected and reverted for this reason.
- `version` in `plugin.json` is raised only to release, in its own PR: merging it to `main` publishes `v<version>`. Installed users stay on the last version until then (Claude Code updates only when the version string changes).
- Check `## Open questions` in `discussion.md` before starting work; several items there are explicitly "ask the user".
