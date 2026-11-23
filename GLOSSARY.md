# agent-flow

agent-flow is the skill-workflow method abstracted into a plugin that any repo installs and calls; its Owner is its first user.

## Language

**Method**:
The rules and steps that take a request to merged, checked PRs: align the environment, receive, gather, confirm, cut tickets, implement, review, check evidence, merge.
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

## Running a goal

**Environment alignment**:
The first step in a Calling repo: choosing, from the skills actually installed, which one serves each step of the Method.
_Avoid_: setup, catalog, companions

**Foundation**:
The gathered facts a goal is built on, each with its source; a fact with no source is marked as an assumption.
_Avoid_: research notes, context

**Plan PR**:
The PR that carries a goal's finish line, Foundation, repo rules and every ticket's Verify commands; its merge is the approval to run.
_Avoid_: confirmation, spec PR

**Verify command**:
A command fixed before implementation whose exit code alone decides whether one criterion passes.
_Avoid_: evidence command, check (when meaning one written by the reviewer)

**Evidence check**:
Re-running every locked Verify command at the PR head, with no model involved.
_Avoid_: audit

**Review**:
A model's judgement of a change's quality and of whether its Verify commands really test their criteria.
_Avoid_: audit
