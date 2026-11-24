# A hook enforces the locks and the Ask-first commands before a tool runs

Status: accepted (2026-11-24)

`merge_gate.py` catches a locked-path change only when the PR is about to merge, after the agent has already built on it, and the Ask-first list for commands that delete work was prose the agent could skip. Text in `SKILL.md` or `CLAUDE.md` is a sign, a check is a fence: the Owner chose this from Lauren Tan's talk and from gstack `careful`/`freeze` and ECC `config-protection` (P8 in `docs/agent-flow/discussion.md`). We decided the plugin ships one PreToolUse hook, `guard.py`, active only in a repo that has `.agent-flow/`: on `agent-flow/*` branches except `-plan` it denies edits and shell writes to locked paths and to `protect:` globs from `.agent-flow/config`; on any branch it asks before force pushes, `reset --hard`, `clean -f`, recursive `rm` and similar; input it cannot read is denied. `merge_gate.py` stays the authority and checks the same paths.

## Consequences

- The plugin now runs code on every edit and shell command in every session where it is installed; outside a repo with `.agent-flow/` it returns at once with no output.
- Shell writes are matched by command shape, so a script that writes a locked file (for example `python3 -c ...`) passes the hook; `merge_gate.py` still refuses the PR.
- A Calling repo locks its own lint and test config with `protect:` lines, which are themselves locked because `.agent-flow/**` is.

## Considered options

- Keep the gate only: cheap, but the agent learns about a broken lock after the work is done.
- Ship gstack or ECC as a dependency: brings their whole method and telemetry hooks; against ADR 0002.
