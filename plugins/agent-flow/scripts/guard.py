#!/usr/bin/env python3
"""PreToolUse hook: the locks and the Ask-first list acting when a tool is about to run, not only at merge.

Active only in a git repo whose root has `.agent-flow/`; anywhere else it prints nothing and exits 0.
- Edit, Write, MultiEdit, NotebookEdit on a locked path (merge_gate.LOCKED or a `protect:` glob in
  `.agent-flow/config`) while on an `agent-flow/*` branch that is not a `-plan` branch: deny.
- Bash that writes to such a path on such a branch (cp, mv, rm, tee, touch, sed -i, a `>` redirect,
  git rm/mv/checkout/restore/apply): deny.
- Bash that can delete or overwrite work on any branch (force push, remote branch delete, reset --hard,
  clean -f, checkout -f or `-- <path>`, restore, branch -D, stash drop/clear, worktree remove --force,
  history rewrites, recursive rm, gh repo/release delete): ask.
Input it cannot read or parse is denied (fail-closed). merge_gate.py stays the authority; this is the early fence.
"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_gate import is_locked, protected  # noqa: E402

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SEPARATORS = {"&&", "||", ";", "|", "&", ";;", "|&"}
WRITERS = {"cp", "mv", "rm", "tee", "touch", "truncate", "dd", "install", "ln", "chmod", "rmdir"}
GIT_WRITERS = {"rm", "mv", "checkout", "restore", "apply"}
LOCK_FIX = ("fix the code instead; if a Verify command, CI or a repo rule is itself wrong, "
            "stop and ask the user for a new Plan PR")


def decide(decision, reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                             "permissionDecisionReason": reason}}))
    return 0


def repo_root(cwd):
    for d in [cwd, *cwd.parents]:
        if (d / ".git").exists():
            return d
    return None


def branch(root):
    try:
        return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, capture_output=True,
                              text=True).stdout.strip()
    except OSError:
        return ""


def rel(root, cwd, path):
    p = Path(os.path.realpath(cwd / os.path.expanduser(path)))
    try:
        return p.relative_to(os.path.realpath(root)).as_posix()
    except ValueError:
        return None


def segments(command):
    """Split a shell command into simple commands (lists of words). Raises ValueError on bad quoting."""
    out = []
    for line in command.splitlines():
        lex = shlex.shlex(line, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        cur = []
        for tok in lex:
            if tok in SEPARATORS:
                out.append(cur)
                cur = []
            else:
                cur.append(tok)
        out.append(cur)
    return [s for s in out if s]


def strip_prefix(words):
    while words and ("=" in words[0] and not words[0].startswith("=") or words[0] in ("sudo", "command", "env", "exec",
                                                                                       "nohup", "time", "xargs")):
        words = words[1:]
    return words


def git_args(words):
    """The words after `git` and its global options (-C <dir>, -c <k=v>)."""
    rest = words[1:]
    while rest and rest[0] in ("-C", "-c", "--git-dir", "--work-tree"):
        rest = rest[2:]
    while rest and rest[0].startswith("--") and "=" in rest[0]:
        rest = rest[1:]
    return rest


def destructive(words):
    """A reason this simple command can delete or overwrite work, or None."""
    if not words:
        return None
    prog = os.path.basename(words[0])
    flags = [w for w in words[1:] if w.startswith("-")]
    if prog in ("sh", "bash", "zsh", "dash") and "-c" in words:
        i = words.index("-c")
        return command_reason(words[i + 1]) if i + 1 < len(words) else None
    if prog == "rm" and any(f in ("-r", "-R", "--recursive") or (not f.startswith("--") and set("rR") & set(f))
                            for f in flags):
        return "recursive rm"
    if prog == "gh" and len(words) > 2 and words[1] in ("repo", "release") and words[2] == "delete":
        return f"gh {words[1]} delete"
    if prog != "git":
        return None
    args = git_args(words)
    if not args:
        return None
    sub, rest = args[0], args[1:]
    rflags = [w for w in rest if w.startswith("-")]
    if sub == "push" and (any(f in ("-f", "-d", "--delete", "--mirror", "--prune") or f.startswith("--force")
                              for f in rflags) or any(w.startswith(("+", ":")) for w in rest)):
        return "force push or remote branch delete"
    if sub == "reset" and "--hard" in rflags:
        return "reset --hard"
    if sub == "clean" and any(f == "--force" or (not f.startswith("--") and "f" in f) for f in rflags):
        return "clean -f"
    if sub == "checkout" and ("-f" in rflags or "--force" in rflags or "--" in rest or "." in rest):
        return "checkout over uncommitted changes"
    if sub == "restore" and not (rflags and all(f in ("--staged", "-S") for f in rflags)):
        return "restore over uncommitted changes"
    if sub == "branch" and any(f == "-D" or f == "--force" for f in rflags):
        return "branch -D"
    if sub == "stash" and rest[:1] and rest[0] in ("drop", "clear"):
        return f"stash {rest[0]}"
    if sub == "worktree" and rest[:1] == ["remove"] and ("-f" in rflags or "--force" in rflags):
        return "worktree remove --force"
    if sub in ("filter-branch", "filter-repo") or (sub == "reflog" and rest[:1] == ["expire"]):
        return "history rewrite"
    return None


def command_reason(command):
    for words in segments(command):
        reason = destructive(strip_prefix(words))
        if reason:
            return reason
    return None


def locked_writes(words, root, cwd, globs):
    words = strip_prefix(words)
    if not words:
        return []
    prog = os.path.basename(words[0])
    targets = []
    for i, w in enumerate(words):
        if w in (">", ">>", ">|", "&>") and i + 1 < len(words):
            targets.append(words[i + 1])
    writer = (prog in WRITERS or (prog in ("sed", "perl") and any(w.startswith("-i") or w == "-pi" for w in words))
              or (prog == "git" and git_args(words)[:1] and git_args(words)[0] in GIT_WRITERS))
    if writer:
        operands = [w for w in words[1:] if not w.startswith("-")]
        if prog in ("cp", "install", "ln"):
            operands = operands[-1:]  # only the destination is written
        elif prog == "dd":
            operands = [w[3:] for w in operands if w.startswith("of=")]
        targets += operands
    paths = [rel(root, cwd, t) for t in targets]
    return [p for p in paths if p and is_locked(p, globs)]


def main():
    try:
        data = json.load(sys.stdin)
        tool = data["tool_name"]
        inp = data.get("tool_input") or {}
        cwd = Path(data.get("cwd") or os.getcwd())
    except (ValueError, KeyError, TypeError):
        return decide("deny", "agent-flow guard could not read its hook input; re-run the tool call")
    root = repo_root(cwd)
    if root is None or not (root / ".agent-flow").is_dir():
        return 0
    br = branch(root)
    locks_on = br.startswith("agent-flow/") and not br.endswith("-plan")
    globs = protected(root)
    if tool in FILE_TOOLS:
        path = inp.get("file_path") or inp.get("notebook_path") or ""
        r = rel(root, cwd, path) if path else None
        if locks_on and r and is_locked(r, globs):
            return decide("deny", f"agent-flow lock: {r} is locked on {br} after its Plan PR; {LOCK_FIX}.")
        return 0
    if tool != "Bash":
        return 0
    command = inp.get("command") or ""
    try:
        parts = segments(command)
        reason = command_reason(command)
    except ValueError:
        return decide("ask", "agent-flow guard could not parse this command; confirm it is safe before running")
    if locks_on:
        hits = [p for words in parts for p in locked_writes(words, root, cwd, globs)]
        if hits:
            return decide("deny", f"agent-flow lock: this command writes {', '.join(hits)}, locked on {br} "
                                  f"after its Plan PR; {LOCK_FIX}.")
    if reason:
        return decide("ask", f"agent-flow Ask first: {reason} can delete or overwrite work. Run it only if the user "
                             "agreed; land.py already removes merged branches and worktrees.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
