# Each step uses a skill chosen from the installed environment, not a bundled or hard-wired one

Status: accepted (2026-11-23); for explore, propose, apply and archive superseded by ADR 0003

The first port rewrote steps that existing skills already do (ticket format, records, review), which is reinventing the wheel and drifted from the Base, which picked skills from its catalogue per task. We decided that agent-flow owns only what no skill provides (Boundaries, the Plan PR gate, the locks, the test check, the review evidence gate, `merge_gate.py`/`land.py`, and the order of steps). Every other step uses a skill chosen during Environment alignment, the Method's first step in a Calling repo: list the skills and agents the session actually has (from any source, not one vendor), pick one per step with a one-line reason, write the settings the chosen skills need (for example an issue-tracker file pointing at `docs/<topic>/`), and record the map in `.agent-flow/skills.md`. A skill with `disable-model-invocation: true` is followed by reading its `SKILL.md`, as the Base did. A step with no suitable skill falls back to agent-flow's own minimal instruction.

## Considered options

- Declare a plugin dependency (`dependencies` in `plugin.json`) on one skill vendor: ties the Method to that vendor and ignores what the Owner already has installed.
- Bundle MIT copies of the skills: forks them, breaks the first-party-only package rule, and needs tracking upstream.
- Keep skills as optional companions with agent-flow's own fallbacks for every step: the fallbacks are the reinvented wheels.

## Consequences

- Whether a skill from another plugin can be invoked through the Skill tool is undocumented; the Owner's first experiment-repo run settles it.
- Interactive points inside chosen skills (test seams) are answered by the agent with its recommendation and shown in the Plan PR, except the confirm step, which stays a conversation with the Owner.
