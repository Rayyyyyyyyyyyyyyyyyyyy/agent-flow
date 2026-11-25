# Spec: agent-flow v0.1

Vocabulary: `GLOSSARY.md`. Decisions: `docs/agent-flow/discussion.md`, `docs/adr/`.

## Problem Statement

The Owner can get code written by Claude Code, but not a finished, checked change: nobody writes the finish line, grounds the work in sourced facts, splits it into work that can run in parallel, keeps the tests fixed so they cannot be bent to go green, merges only when the evidence passes, or keeps a record of what the repo does now. The Owner's method that does this (skill-workflow) only works inside its own repo, re-implements steps that existing tools already do, spends too many tokens on review, and lets the reviewer choose its own evidence.

## Solution

`agent-flow` is a Claude Code plugin. The Owner (first user; others are a by-product) installs it and OpenSpec, runs `openspec init` once per repo, and runs `/agent-flow:agent-flow <goal>` in a Calling repo. The Method runs there:

0. Environment alignment: `doctor.py` checks the tools, OpenSpec included; for the steps OpenSpec does not cover, pick one installed skill per step with a reason and record `.agent-flow/skills.md`.
1. Receive the request: a goal goes straight to its finish line; a direction or seed is explored with the Owner through `/opsx:explore` until the Owner moves on.
2. Gather facts into `docs/<topic>/foundation.md`, each with a source; unsourced facts are assumptions. Write the repo's own rules after reading it.
3. Propose: `/opsx:propose <topic>` writes `openspec/changes/<topic>/`; every Scenario carries a Verify command; open the Plan PR.
4. Confirm with the Owner; merging the Plan PR is the go-ahead (the agent merges it only with `plan: agent`).
5. Apply: `/opsx:apply`, task groups in parallel, one worktree each, test-first; one integration branch and one PR per goal.
6. Review with the chosen review skill, once, reporting cumulative tokens.
7. Evidence check: CI runs every locked Verify command.
8. Merge through `merge_gate.py` and `land.py`.
9. Archive: `/opsx:archive` folds the change into `openspec/specs/`, merged through the gate.

agent-flow itself owns only what no other tool provides: the Boundaries, the Plan PR gate, the locks, the Evidence check rules, `merge_gate.py`/`land.py`, `doctor.py`, and the order of steps.

## User Stories

1. As the Owner, I want to call the Method from any of my repos with one slash command, so that I do not have to open skill-workflow.
2. As the Owner, I want explore, propose, apply and archive done by OpenSpec as I would run it myself, and the other steps by skills I already have, so that nothing is reinvented.
3. As the Owner, I want to decide when exploring ends, so that nothing is proposed before I am ready.
4. As the Owner, I want every fact the work rests on to carry its source, so that implementation is grounded.
5. As the Owner, I want to see the proposal, specs, tasks and every Verify command in the Plan PR before anything is built, so that I approve the test, not just the code.
6. As the Owner, I want Verify commands locked once merged, so that no agent can change the rules to make a gate pass.
7. As the Owner, I want ready task groups applied in parallel, so that the goal finishes sooner.
8. As the Owner, I want one review per goal that only judges what a script cannot, so that review costs fewer tokens.
9. As the Owner, I want CI to re-run every Verify command and the merge gate to refuse missing or weakened evidence, so that a pass means a pass.
10. As the Owner, I want criteria only I can judge kept out of agent merges, so that nothing unjudged lands.
11. As the Owner, I want each merged change archived into the current specs, so that the repo keeps a record of what it does now.
12. As the Owner, I want to be asked before anything that affects other people, secrets, money or my own data, and a STOP file or `merge: never` to stop merges.
13. As the Owner, I want to re-run after a crash without duplicate changes, branches or PRs.

## Implementation Decisions

- Repo layout: the repo is the marketplace; the plugin lives in `plugins/agent-flow/`; repo tooling (`scripts/`, `tests/`, CI) stays outside it.
- Base: skill-workflow `31114d7`, frozen; where the Owner changed the Method, the Owner's decision wins.
- OpenSpec is fixed for explore, propose, apply and archive; agent-flow runs its commands and reads its files, and leaves installing and `openspec init` to the user (ADR 0003). Other steps use skills chosen per Calling repo, never bundled or declared as dependencies (ADR 0002).
- Verify commands sit under Scenarios in `openspec/changes/<topic>/specs/`, are fixed in the Plan PR and locked with `.agent-flow/**`, `.github/workflows/**`, `.gitlab-ci.yml` and `openspec/config.yaml`; `tasks.md` is not locked. The Evidence check is a CI job; `merge_gate.py` refuses: locked paths touched, a Scenario without a Verify command, pipes / `;` / `$?` in a Verify command, the Evidence check job not green, an unapproved Plan PR, an archive PR outside its OpenSpec paths, the `agent-flow:owner-judges` label, the kill switch (ADR 0001).
- Forges: GitHub through `gh`, GitLab through `glab api` (a PR is a merge request; the evidence-check job lives in `.gitlab-ci.yml`). The forge is `forge:` in `.agent-flow/config`, else GitLab when origin's URL contains `gitlab`.

## Testing Decisions

- Unit tests (`python3 -m unittest`) for every script: package checks, discussion checker, doctor checks, verify, merge gate (each refusal), land, rule greps for each finish-line item a script cannot run.
- CI matrix macOS + Ubuntu, plus the fresh-HOME install job.
- No end-to-end harness here: the Owner's experiment-repo run is the proof (C10).

## Out of Scope

Release polish (#13: CHANGELOG, pinned install) until the Method is done; tags and GitHub releases are automatic per version, pre-releases while 0.x; the README is revised at release; native Windows (WSL2 documented); upgrade migration; uninstall beyond a README section.
