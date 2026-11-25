# agent-flow

agent-flow is the skill-workflow method abstracted into a plugin that any repo installs and calls; its Owner is its first user.

## Language

**Method**:
The rules and steps that take a request to merged, checked PRs: align the environment, receive, gather, propose, confirm, apply, code review, test check, merge, archive. It is abstract: it sets the floor, and the Calling repo's OpenSpec change says what is accepted.
_Avoid_: workflow, flow (when meaning the rules rather than one run)

**Plugin**:
The installable form of the Method; every use, the Owner's included, goes through its slash command in a Calling repo.
_Avoid_: package, packaging

**Base**:
skill-workflow at commit 31114d7, read-only, the source the Method is ported from.
_Avoid_: original, old repo, skill-flow

**Calling repo**:
A repo that has the Plugin installed and invokes it; the Method runs there and its records live there.
_Avoid_: target repo, project repo, user repo

**Owner**:
The author of agent-flow and its first user.
_Avoid_: maintainer (when meaning the user the tool is for)

**Forge**:
The host of the Calling repo's `origin`: GitHub (through `gh`) or GitLab (through `glab`). `merge_gate.py`, `land.py` and `doctor.py` pick it themselves; the Method is the same on both.
_Avoid_: provider, platform

**Merge request (MR)**:
GitLab's name for a pull request. Everything said of a PR (Plan PR, integration PR, archive PR, a PR comment) holds for an MR (an MR note).
_Avoid_: using MR where the text means both forges; say PR

## Running a goal

**Environment alignment**:
The first step in a Calling repo: choosing, from the skills actually installed, which one serves each step OpenSpec does not cover.
_Avoid_: setup, catalog, companions

**Foundation**:
The gathered facts a goal is built on, each with its source; a fact with no source is marked as an assumption.
_Avoid_: research notes, context

**OpenSpec change**:
The goal's `openspec/changes/<topic>/`: proposal, design, specs whose Scenarios carry the Verify commands, and tasks; each task in `tasks.md` is one unit of acceptance for the Review.
_Avoid_: ticket, spec (when meaning the whole change)

**Current specs**:
`openspec/specs/`, what the Calling repo does now; archive folds each merged change into it.
_Avoid_: main spec, living docs

**Plan PR**:
The PR that carries a goal's finish line, Foundation, repo rules and its OpenSpec change; its merge is the approval to apply.
_Avoid_: confirmation, spec PR

**Verify command**:
A command fixed before implementation under a Scenario, whose exit code alone decides whether that Scenario passes.
_Avoid_: evidence command, check (when meaning one written by the reviewer)

**Test check**:
CI re-running every locked Verify command, the program tests, at the PR head, with no model involved. Its CI job keeps the name `evidence-check` from before ADR 0005, so Calling repos already set up need no change.
_Avoid_: evidence check, evidence (when meaning test results), audit

**Ruling**:
A decision the agent makes alone where the Method leaves a choice open, recorded as `Ruling: what - why - cost if wrong`.
_Avoid_: assumption (when meaning a decision)

**Review**:
A code review by a model that implemented nothing in the change: it reads the diff against each task in `tasks.md` and gives each `PASS` or `FAIL` with evidence; it also judges quality, scope, and whether the Verify commands really test their Scenarios.
_Avoid_: audit, test (when meaning the review)

**Merge check**:
A subagent that wrote and reviewed nothing in the change, checking every merge rule (`references/merge-rules.md` plus the Calling repo's `.agent-flow/merge-rules.md`) read-only through `gh` or `glab` before each `land.py` run; any `FAIL` stops the merge.
_Avoid_: merge gate (that is `merge_gate.py`), approval

**Review evidence**:
The Review's per-task table (`| Task | Verdict | Evidence |`, evidence being `file:line` in the diff and the covering test, or why none), posted as a PR comment that names the reviewed commit; `merge_gate.py` merges nothing without it.
_Avoid_: approval, sign-off, evidence check
