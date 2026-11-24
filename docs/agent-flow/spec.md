# Spec: agent-flow v0.1

Rewritten 2026-11-23 (realignment). Vocabulary: `GLOSSARY.md`. Decisions: `docs/agent-flow/discussion.md`, `docs/adr/`.

## Problem Statement

The Owner can get code written by Claude Code, but not a finished, checked change: nobody writes the finish line, grounds the work in sourced facts, splits it into tickets that can run in parallel, keeps the tests fixed so they cannot be bent to go green, or merges only when the evidence passes. The Owner's method that does this (skill-workflow) only works inside its own repo, re-implements steps that installed skills already do, spends too many tokens on review, and lets the reviewer choose its own evidence.

## Solution

`agent-flow` is a Claude Code plugin. The Owner (first user; others are a by-product) installs it and runs `/agent-flow:agent-flow <goal>` in a Calling repo. The Method runs there:

0. Environment alignment: list the installed skills and agents, pick one per step with a reason, write the settings they need, record `.agent-flow/skills.md`; `doctor.py` checks the tools.
1. Receive the request (a vague one is grilled first).
2. Gather facts into `docs/<topic>/foundation.md`, each with a source; unsourced facts are assumptions.
3. Confirm the task list and re-confirm the goal with the Owner, in conversation.
4. Cut tickets into `docs/<topic>/tickets/`, every criterion with a Verify command; open the Plan PR (finish line, Foundation, rules, tickets), merged by the Owner unless `plan: agent`.
5. Implement with the chosen implementation skill: ready tickets in parallel, one integration branch and one PR per goal.
6. Review with the chosen review skill, once, reporting cumulative tokens.
7. Evidence check: CI runs every locked Verify command.
8. Merge through `merge_gate.py` and `land.py`.

agent-flow itself owns only what no skill provides: the Boundaries, the Plan PR gate, the locks, the Evidence check rules, `merge_gate.py`/`land.py`, `doctor.py`, and the order of steps.

## User Stories

1. As the Owner, I want to call the Method from any of my repos with one slash command, so that I do not have to open skill-workflow.
2. As the Owner, I want the agent to use the skills I already have installed for each step, so that nothing is reinvented and better skills apply as I install them.
3. As the Owner, I want every fact the work rests on to carry its source, so that implementation is grounded.
4. As the Owner, I want to confirm the task list and goal before tickets are cut, so that the run does what I meant.
5. As the Owner, I want to see every Verify command in the Plan PR before anything is built, so that I approve the test, not just the code.
6. As the Owner, I want Verify commands locked once merged, so that no agent can change the rules to make a gate pass.
7. As the Owner, I want ready tickets implemented in parallel, so that the goal finishes sooner.
8. As the Owner, I want one review per goal that only judges what a script cannot, so that review costs fewer tokens.
9. As the Owner, I want CI to re-run every Verify command and the merge gate to refuse missing or weakened evidence, so that a pass means a pass.
10. As the Owner, I want criteria only I can judge kept out of agent merges, so that nothing unjudged lands.
11. As the Owner, I want to be asked before anything that affects other people, secrets, money or my own data, and a STOP file or `merge: never` to stop merges.
12. As the Owner, I want to re-run after a crash without duplicate tickets, branches or PRs.

## Implementation Decisions

- Repo layout unchanged: the repo is the marketplace; the plugin lives in `plugins/agent-flow/`; repo tooling (`scripts/`, `tests/`, CI) stays outside it.
- Base: skill-workflow `31114d7`, frozen. Port faithfully; change only on the Owner's request or when a real run gets stuck.
- Skills are chosen per Calling repo from its environment, never bundled or declared as dependencies (ADR 0002). Non-invocable skills are followed by reading their `SKILL.md`.
- Tickets are repo files; GitHub issues, if used, only track status.
- Verify commands are fixed in the Plan PR and locked; the Evidence check is a CI job; `merge_gate.py` refuses: locked paths touched, a criterion without a Verify command, pipes / `;` / `$?` in a Verify command, the Evidence check job not green, an unapproved Plan PR, the `agent-flow:owner-judges` label, the kill switch (ADR 0001).
- Removed: `audit.py`, `sandbox.py`, `canaries.py`, `pending_audits.py`, `review.py`, `agents/reviewer.md`, `agents/implementer.md`, and `references/` text that a chosen skill covers.

## Testing Decisions

- Unit tests (`python3 -m unittest`) for every script: package checks, discussion checker, doctor checks, merge gate (each refusal), rule greps for each finish-line item a script cannot run.
- CI matrix macOS + Ubuntu, plus the fresh-HOME install job.
- No end-to-end harness here: the Owner's experiment-repo run is the proof (C10).

## Out of Scope

Release polish (#13: CHANGELOG, tag, pinned install) until the Method is done; the README exists but is revised at release; native Windows (WSL2 documented); upgrade migration; uninstall beyond a README section.
