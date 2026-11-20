# Spec: agent-flow v0.1

## Problem Statement

A developer who uses Claude Code can get code written, but not a finished, checked change: nobody writes the finish line, splits the work, keeps implementation and review in separate contexts, re-runs the review's evidence, or merges only when the gates are green. The author's method that does this lives in one private-feeling repo (skill-workflow) and only works when a session is opened there.

## Solution

`agent-flow` is a public Claude Code plugin. A developer installs it once, opens Claude Code in their own repo and runs `/agent-flow:agent-flow <goal>`. The agent writes the finish line into `docs/<topic>/discussion.md`, adds CI if missing, cuts GitHub issues, dispatches an implementer subagent per ticket in its own worktree, runs the deterministic gate, one independent reviewer, an audit that re-runs the reviewer's evidence, and merges. The plugin ships outer boundaries that no project rule may loosen, and tells the agent to write the calling repo's own rules and verify inside them. It asks before actions that affect other people and before using secrets, spending money or deleting the user's own data, and stops merging when a kill switch is present. All of this runs in the calling repo; this repo only provides it.

## User Stories

1. As a developer, I want to install the plugin with two commands, so that I can try it in minutes.
2. As a developer, I want a `doctor` check that tells me exactly what is missing and how to fix it, so that I do not fail halfway through a run.
3. As a developer, I want to give a goal in one sentence and get a written finish line with external evidence per line, so that "done" is checkable.
4. As a developer, I want my project record to live in my repo (`docs/<topic>/discussion.md`, `GLOSSARY.md`, `docs/adr/`), so that it is versioned with the code.
5. As a developer, I want the agent to add CI when my repo has none, so that every PR is verified.
6. As a developer, I want tickets as GitHub issues with scope, out-of-scope and runnable verify commands, so that I can follow progress where I already work.
7. As a developer, I want each ticket implemented in its own worktree by a subagent, so that parallel work does not collide.
8. As a developer, I want one independent reviewer and an audit that re-runs the reviewer's evidence, so that a review cannot pass on claims alone.
9. As a developer, I want audit to work on macOS and Linux, and to say "unverified" instead of "passed" when it cannot sandbox project code, so that I am never misled.
10. As a developer, I want the agent to merge its own PRs when the gates pass, without asking me, so that the flow finishes unattended.
11. As a developer, I want to be asked before the agent uses secrets, spends money or deletes my own data, so that nothing surprising happens.
12. As a developer, I want the agent to stop and ask before anything that affects other people (deploys, other people's repos, notifications), so that I stay responsible for those.
13. As a developer, I want a STOP file or `merge: never` setting, so that I can keep PRs open for my own review.
14. As a developer, I want to re-run after a crash without duplicate issues or PRs.
15. As a developer, I want to see what the run cost.
16. As a maintainer, I want the shipped text free of personal data and third-party skills, so that the license is clean.
17. As a maintainer, I want canaries (trap reports for the auditor) to run on my machine before a release, not on every user's machine.

## Implementation Decisions

- Repo layout: the repo is the marketplace (`.claude-plugin/marketplace.json`, name `agent-flow`); the plugin lives in `plugins/agent-flow/` (`.claude-plugin/plugin.json`, `skills/agent-flow/SKILL.md` + `references/`, `agents/`, `scripts/`). Repo-level tooling (`scripts/check_package.py`, `tests/`, CI) stays outside the plugin directory.
- Source of the method: skill-workflow at commit 31114d7 (`CLAUDE.md`, `method/WORKFLOW.md`, `method/AUDIT.md`, `method/agents/issue-tracker.md`, `method/policies/P00-GROUNDED-ANSWER.md`, `.claude/agents/implementer.md`, `.claude/agents/reviewer.md`, `scripts/review.py`, `scripts/audit.py`, `scripts/audit_canary.py`, `.claude/auditor/`). Port, generalise, translate to English; drop personal settings.
- Records: `docs/<topic>/discussion.md` (verbatim words, finish line, authorizations, decisions, open questions/frontier), `docs/<topic>/spec.md`, `GLOSSARY.md`, `docs/adr/`; work log in issues and PRs. Review reports and `.audit.md` live in `docs/<topic>/reviews/`.
- Boundaries (C6): do / ask first / never, plus the kill switch; project rules may tighten, never loosen. CI and test changes are merged by the agent like any other PR.
- Merge gate: a script decides mergeability: CI green (via `gh`), latest audit passed with no `unverified`, no `.agent-flow/STOP`, `merge` not `never` in `.agent-flow/config`. Branch protection is set when the plan allows; otherwise the gate script is the only guard and doctor says so.
- Audit: evidence kinds are file position (read directly), read-only commands from an argv allowlist (run with `shell=False`), and project commands (run only inside a sandbox: macOS Seatbelt, Linux bwrap, one module). Without a sandbox, project commands are `unverified`. Rules come from the installed plugin version, recorded in `.audit.md`. No `claude` call on the deterministic path.
- Canaries: maintainer-only script, run before tagging; stamp ships in the plugin.
- Cost: `review.py` prints tokens and $; interactive users use `/cost`.
- v0.1 ships two roles: implementer and reviewer.

## Testing Decisions

- Unit tests (`python3 -m unittest`) for every script: package checks, discussion checker, doctor checks, audit evidence parsing / allowlist / three states / sandbox detection, merge gate, review/audit version anchor.
- CI matrix macOS + Ubuntu; one Ubuntu job installs bwrap and must execute the sandbox path; one job without sandbox asserts `unverified` and a blocked merge.
- No end-to-end harness: E2E is a per-project choice (2026-11-20). Criteria a script cannot check are `evidence: user judges`.
- Prior art: skill-workflow `tests/` (portability, review, audit tests).

## Out of Scope

Designer, writer, researcher, planner roles; srt; native Windows (WSL2 documented); retro and method log; integration with agency-agents or grilling; upgrade migration; uninstall beyond a README section.

## Further Notes

Finish line and decisions: `docs/agent-flow/discussion.md`. Sandbox research: `docs/research/sandbox-for-audit-reruns.md`.
