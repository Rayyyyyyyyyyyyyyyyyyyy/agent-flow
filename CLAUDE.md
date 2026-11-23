# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`agent-flow` is a Claude Code plugin, and the repo is also its marketplace (`.claude-plugin/marketplace.json` points at `plugins/agent-flow/`). The plugin ships one skill (`skills/agent-flow/SKILL.md` + `references/`) that takes a goal to merged PRs, two subagents (`agents/implementer.md`, `agents/reviewer.md`) and the deterministic Python scripts the skill calls. Repo-level tooling (`scripts/`, `tests/`, CI) lives outside the plugin directory and is not shipped.

Source of truth for design and current state:
- `docs/agent-flow/spec.md` — problem, decisions, scope.
- `docs/agent-flow/contracts.md` — the interfaces between scripts (CLI, exit codes, report/audit formats, paths). A change to a contract updates this file in the same PR.
- `docs/agent-flow/discussion.md` — finish line, user decisions, and `## Open questions` (the hand-off: what to do next and what must be asked first).

## Commands

Python 3 stdlib only; no install step.

```bash
python3 -m unittest discover -s tests -v          # all tests
python3 -m unittest tests.test_audit -v           # one file
python3 -m unittest tests.test_sandbox.NoSandbox -v   # one class
python3 scripts/no_cjk.py plugins/agent-flow      # shipped text must be CJK-free
python3 scripts/check_package.py                  # personal-data / packaging checks
claude plugin validate .                          # manifest validation
```

CI (`.github/workflows/ci.yml`) runs all of the above on macOS and Ubuntu, installs the plugin into a fresh HOME, and has two sandbox jobs: `AGENT_FLOW_REQUIRE_SANDBOX=bwrap` (must execute the bwrap path) and `AGENT_FLOW_SANDBOX=none` (must yield `unverified`).

The plugin ships no canaries or stamp; trap reports are per Calling repo (`.agent-flow/auditor/`).

## Architecture

This section describes the current code. The 2026-11-23 realignment (`docs/adr/0001`, `docs/adr/0002`, `GLOSSARY.md`) replaces review/audit/sandbox with locked Verify commands run by CI and skills chosen from the environment; until those tickets land, the code below is what runs.

The per-PR pipeline, each step a separate script in `plugins/agent-flow/scripts/`:

1. `review.py` runs the reviewer in a lean `claude -p` (reviewer.md body as the whole system prompt, only Read/Write/Bash) and writes a report in the format defined in `contracts.md` (`### C<n> — PASS|FAIL` with `Command:`/`Position:` evidence).
2. `audit.py` re-runs that evidence at the reviewed commit and writes `<report>.audit.md`, ending `Result: passed|failed|...`. Evidence kinds: file positions (read directly), read-only commands from an argv allowlist (`shell=False`), and project commands, which run only inside `sandbox.py` (macOS Seatbelt or Linux bwrap). No sandbox ⇒ `unverified` (exit 3), never `passed`. The deterministic path makes no model calls.
3. `merge_gate.py` decides mergeability: CI green via `gh`, the highest-round audit in the PR diff ends `Result: passed`, and no kill switch (`.agent-flow/STOP`, or `merge: never` in `.agent-flow/config`).
4. `land.py` imports `merge_gate.main`, updates a BEHIND branch, merges with a merge commit (`--match-head-commit`), and cleans up worktree/branches only after the PR is `MERGED`.

`doctor.py` is the preflight the skill runs first.

Tests import plugin scripts by inserting `plugins/agent-flow/scripts` into `sys.path` (no `tests/__init__.py`), or run them via `subprocess` with `sys.executable`.

## Constraints on shipped files

`check_package.py` fails the build if anything under `plugins/agent-flow/` contains personal paths (`/Users/`, `/home/<name>`), email addresses, CJK characters, the words `rtk`/`ponytail`, or `Asia/Taipei`, or if a skill other than `agent-flow` is bundled. The owner's GitHub handle is forbidden in every tracked file except `README.md`, `marketplace.json`, `LICENSE`, `NOTICE`, `docs/` and `tests/` — this includes this file. Shipped text is English.

## Working rules from past decisions

- Verification methods that create external resources, run real model calls, or spend the user's usage (E2E runs, fixture repos, canaries) need the user's explicit yes first. A fabricated fixture-repo E2E was rejected and reverted for this reason.
- Check `## Open questions` in `discussion.md` before starting work; several items there are explicitly "ask the user".
