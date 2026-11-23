"""Re-run a review report's evidence at the reviewed commit and write <report>.audit.md.

Usage: audit.py <report> --repo <repo> [--unsandboxed] [--model]
The model (one tier above the reviewer, opus for rebuttals) judges the report only when it has a rebuttal, or with --model.
Rules: the plugin's auditor/RULES.md plus the project's .agent-flow/auditor/RULES.md on its origin default branch.
Exit: 0 passed, 1 failed, 3 partly unverified, 2 usage or setup error. Format: docs/agent-flow/contracts.md.
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import sandbox

PLUGIN = Path(__file__).resolve().parents[1]
PROJECT = ".agent-flow/auditor"
NEXT_TIER = {"haiku": "sonnet", "sonnet": "opus", "opus": "opus"}
ITEM = re.compile(r"^### (\S+) — (PASS|FAIL|UNKNOWN)\s*$")
REBUT_ITEM = re.compile(r"^### (\S+)\s*$")
REBUTTAL = "## Rebuttal"
SOURCE = re.compile(r"^(Command|Reproduce|Position): `(.+)`\s*$")
EXPECT = re.compile(r"^(Output contains|Actual contains|Contains): `(.+)`\s*$")
EXIT_MARK = re.compile(r"\[exit -?\d+\]")
VERDICT_WORD = re.compile(r"PASS|FAIL|UNKNOWN|Rebuttal")
# A verdict written outside a proper heading (`C2 — PASS`, `**C2 — PASS**`) would escape the checks.
LOOSE_ITEM = re.compile(r"^\W*\S+\s*[—–\-:]+\s*\W*(PASS|FAIL|UNKNOWN)\b")
FIELD = re.compile(r"^(Command|Reproduce|Position|Output contains|Actual contains|Contains|Criterion|Expected|Missing|Reason):")
READONLY = {"grep", "test", "ls", "cat", "head", "tail", "wc"}
GIT_READONLY = {"diff", "show", "log", "status", "rev-parse", "ls-files", "grep"}
GIT_WRITES = ("--output", "-O", "--open-files-in-pager", "--ext-diff")
METACHARS = set(";&|<>$`\\(){}*?[]~!#\"'\n")  # shortcut: quotes count as metacharacters, so quoted args become project commands
RUN_TIMEOUT = 600
DIFF_LIMIT = 200_000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def readonly(cmd: str) -> bool:
    if METACHARS & set(cmd):
        return False
    argv = cmd.split()
    if not argv or any(a.startswith("/") or ".." in a for a in argv):
        return False
    if argv[0] == "git":
        return len(argv) > 1 and argv[1] in GIT_READONLY and not any(a.startswith(GIT_WRITES) for a in argv)
    return argv[0] in READONLY


def parse(text: str) -> dict:
    head = {k: (m.group(1) if (m := re.search(rf"^{label}:\s*(\S+)", text, re.M)) else None)
            for k, label in (("model", "Reviewer model"), ("commit", "Reviewed commit"), ("base", "Base"))}
    head["tier"] = next((t for t in NEXT_TIER if t in (head["model"] or "").lower()), None)
    problems, items, rebuttals, cur, rebutting, fenced = [], [], [], None, False, False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            fenced = not fenced
        elif fenced:
            # A fence cannot hide a malformed item.
            if stripped.startswith("#") and VERDICT_WORD.search(stripped):
                problems.append(f"item-like heading inside a code fence: {stripped}")
        elif not stripped.startswith("#") and not FIELD.match(stripped) and LOOSE_ITEM.match(stripped):
            problems.append(f"item not written as a heading: {stripped}")
        elif line.rstrip() == REBUTTAL:
            rebutting, cur = True, None
        elif m := ITEM.match(line):
            if rebutting:
                problems.append(f"item after the rebuttal section: {line.strip()}")
            cur = {"id": m.group(1), "verdict": m.group(2), "evidence": [], "missing": False}
            items.append(cur)
        elif line.startswith("#") and VERDICT_WORD.search(line) and not (rebutting and REBUT_ITEM.match(line)):
            problems.append(f"malformed heading: {line.strip()}")
        elif rebutting and (m := REBUT_ITEM.match(line)):
            cur = {"id": m.group(1), "evidence": []}
            rebuttals.append(cur)
        elif cur is None:
            continue
        elif m := SOURCE.match(line):
            cur["evidence"].append({"kind": "loc" if m.group(1) == "Position" else "cmd", "src": m.group(2), "expect": None})
        elif m := EXPECT.match(line):
            if cur["evidence"] and cur["evidence"][-1]["expect"] is None:
                cur["evidence"][-1]["expect"] = m.group(2)
            else:
                problems.append(f"{cur['id']}: expectation without a source line: {line.strip()}")
        elif re.match(r"^Missing:\s*\S", line):
            cur["missing"] = True
    if fenced:
        problems.append("unclosed code fence")
    if not items:
        problems.append("no items in the report")
    for i in items:
        if i["verdict"] == "UNKNOWN":
            if not i["missing"]:
                problems.append(f"{i['id']} UNKNOWN does not say what is missing")
        elif not i["evidence"]:
            problems.append(f"{i['id']} {i['verdict']} has no evidence")
    for r in rebuttals:
        if not any(i["id"] == r["id"] and i["verdict"] == "FAIL" for i in items):
            problems.append(f"rebuttal {r['id']} matches no FAIL item")
        if not r["evidence"]:
            problems.append(f"rebuttal {r['id']} has no evidence")
    for owner in items + rebuttals:
        for e in owner["evidence"]:
            if e["expect"] is None or (len(e["expect"].strip()) < 2 and not EXIT_MARK.fullmatch(e["expect"])):
                problems.append(f"{owner['id']}: `{e['src']}` has no expectation or one shorter than 2 characters")
    if not head["commit"]:
        problems.append("missing Reviewed commit")
    if not head["tier"]:
        problems.append(f"Reviewer model names no known tier ({', '.join(NEXT_TIER)}): {head['model']}")
    return {**head, "items": items, "rebuttals": rebuttals, "problems": problems}


def look(loc: str, tree: Path) -> str:
    path, _, line = loc.rpartition(":")
    target = (tree / path).resolve()
    if not line.isdigit() or not target.is_relative_to(tree.resolve()) or not target.is_file():
        return f"[not found {loc}]"
    lines = target.read_text(errors="replace").splitlines()
    # Reviewers are often off by a line or two; the window keeps a real citation from failing on that.
    return "\n".join(lines[max(int(line) - 4, 0): int(line) + 3])


def execute(cmd: str, tree: Path, scratch: Path, how: str) -> tuple[str, str]:
    """how: 'argv' (shell=False), 'sandbox', 'plain'. Returns (output, exit mark)."""
    # Only what a test run needs: tokens in the session's environment must not reach the output or .audit.md.
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "TERM", "USER") if k in os.environ}
    env.update(TMPDIR=str(scratch), npm_config_cache=str(scratch / "npm"), CI="1")
    try:
        if how == "sandbox":
            code, out = sandbox.run(cmd, tree, [tree, scratch], RUN_TIMEOUT)
        else:
            done = subprocess.run(shlex.split(cmd) if how == "argv" else ["/bin/sh", "-c", cmd],
                                  cwd=tree, env=env, capture_output=True, text=True, timeout=RUN_TIMEOUT)
            code, out = done.returncode, done.stdout + done.stderr
    except subprocess.TimeoutExpired:
        return f"[timeout {RUN_TIMEOUT}s]", "[timeout]"
    return out, f"[exit {code}]"


def verify(report: dict, repo: Path, unsandboxed: bool) -> tuple[list[str], list[str], list[str]]:
    """Return (problems, unverified commands, rerun log)."""
    problems, unverified, log = list(report["problems"]), [], []
    if not report["commit"]:
        return problems, unverified, log
    checks = [(i["id"], e) for i in report["items"] + report["rebuttals"] for e in i["evidence"] if e["expect"]]
    with tempfile.TemporaryDirectory(prefix="audit-") as temp:
        temp = Path(temp).resolve()
        tree, scratch = temp / "tree", temp / "scratch"
        scratch.mkdir()
        add = git(repo, "worktree", "add", "-q", "--detach", str(tree), report["commit"])
        if add.returncode:
            raise SystemExit(f"cannot open a worktree at {report['commit']}: {add.stderr.strip()}")
        if (repo / "node_modules").is_dir():
            # shortcut: reuses the repo's installed deps as-is (read-only under the sandbox); a lockfile change in the reviewed commit is not reinstalled.
            (tree / "node_modules").symlink_to((repo / "node_modules").resolve())
        try:
            for owner, ev in checks:
                if ev["kind"] == "loc":
                    out, mark = look(ev["src"], tree), ""
                elif readonly(ev["src"]):
                    out, mark = execute(ev["src"], tree, scratch, "argv")
                elif unsandboxed:
                    out, mark = execute(ev["src"], tree, scratch, "plain")
                elif sandbox.available():
                    out, mark = execute(ev["src"], tree, scratch, "sandbox")
                else:
                    unverified.append(ev["src"])
                    log.append(f"{owner} `{ev['src']}`: unverified (no sandbox)")
                    continue
                # The exit mark is ours, not the command's: only an exact `[exit N]` expectation may match it.
                ok = ev["expect"] == mark if EXIT_MARK.fullmatch(ev["expect"]) else ev["expect"] in out
                log.append(f"{owner} `{ev['src']}` expects `{ev['expect']}`: {'match' if ok else 'mismatch'}\n```\n{out[-2000:]}\n{mark}\n```")
                if not ok:
                    problems.append(f"{owner} `{ev['src']}` rerun does not contain `{ev['expect']}`")
        finally:
            git(repo, "worktree", "remove", "--force", str(tree))
    return problems, unverified, log


def load_rules(repo: Path) -> tuple[str, str]:
    """Baseline rules from the installed plugin; project rules from the repo's origin default branch, never the working tree."""
    texts, notes = [(PLUGIN / "auditor/RULES.md").read_text()], [f"plugin auditor/RULES.md"]
    if git(repo, "remote", "get-url", "origin").returncode:
        return texts[0], notes[0] + "; project: no origin, no project rules"
    if git(repo, "fetch", "-q", "origin").returncode:
        raise SystemExit("git fetch origin failed; not using possibly stale project rules")
    ref = git(repo, "rev-parse", "--abbrev-ref", "origin/HEAD").stdout.strip() or "origin/main"
    show = git(repo, "show", f"{ref}:{PROJECT}/RULES.md")
    sha = git(repo, "rev-parse", "--short", ref).stdout.strip()
    if show.returncode == 0:
        texts.append(show.stdout)
        notes.append(f"project {ref}@{sha} {PROJECT}/RULES.md")
    else:
        notes.append(f"project {ref}@{sha}: no {PROJECT}/RULES.md")
    return "\n\n".join(texts), "; ".join(notes)


def diff(report: dict, repo: Path) -> str:
    args = ["diff", report["base"], report["commit"]] if report["base"] else ["show", report["commit"]]
    out = git(repo, *args).stdout
    return out if len(out) <= DIFF_LIMIT else out[:DIFF_LIMIT] + f"\n[diff truncated, {len(out)} characters]"


def claude(model: str, prompt: str) -> str:
    # No tools: the auditor reads only what the script hands it and cannot touch files.
    with tempfile.TemporaryDirectory(prefix="audit-model-") as cwd:
        done = subprocess.run(["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence", "--strict-mcp-config"],
                              input=prompt, cwd=cwd, capture_output=True, text=True, timeout=1800)
    return done.stdout if done.returncode == 0 else f"[claude exit {done.returncode}] {done.stderr[-2000:]}"


def model_passed(reply: str, report: dict) -> bool:
    verdicts, results = {}, []
    for raw in reply.splitlines():
        line = re.sub(r"^\s*(?:[-*]\s+)?", "", raw).replace("**", "")
        if m := re.match(r"^(Rebuttal \S+?|\S+?)\s*:\s*(not upheld|insufficient evidence|upheld)\b", line, re.I):
            if m.group(1) in verdicts:
                return False  # Two verdicts for one item: neither can be trusted.
            verdicts[m.group(1)] = m.group(2).lower()
        elif m := re.match(r"^Result\s*:\s*(passed|failed)\b", line, re.I):
            results.append(m.group(1).lower())
    rebutted = {r["id"] for r in report["rebuttals"]}
    # A rebutted FAIL is judged through its rebuttal only.
    wanted = [i["id"] for i in report["items"] if i["id"] not in rebutted] + [f"Rebuttal {r}" for r in rebutted]
    # Pass/fail comes from the item verdicts; the model's own Result line is only a consistency check against them.
    return results in ([], ["passed"]) and bool(wanted) and all(verdicts.get(w) == "upheld" for w in wanted)


def stamp(repo: Path, rules: str) -> str:
    """Hash of what the project's trap reports test; a change means they must pass again (canaries.py)."""
    d = hashlib.sha256(rules.encode())
    # The tier map names aliases; the CLI version is the closest local signal that an alias now means a new model.
    try:
        d.update(subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.encode())
    except OSError:
        d.update(b"no claude")
    d.update(json.dumps(NEXT_TIER, sort_keys=True).encode())
    d.update(Path(__file__).read_bytes())
    canaries = repo / PROJECT / "canaries"
    for p in sorted(p for p in canaries.rglob("*") if p.is_file()):
        d.update(p.relative_to(canaries).as_posix().encode() + b"\0" + p.read_bytes())
    return d.hexdigest()


def trap_gate(repo: Path, rules: str) -> None:
    """Refuse to audit while the project's trap reports have not passed with the current rules, auditor and model."""
    if not (repo / PROJECT / "canaries/expected.json").is_file():
        return
    stamp_file = repo / PROJECT / "canary-stamp.txt"
    if not stamp_file.is_file() or stamp_file.read_text().strip() != stamp(repo, rules):
        raise SystemExit(f"the project's trap reports ({PROJECT}/canaries/) have not passed with the current rules, auditor and model; "
                         f"run scripts/canaries.py --repo {repo} (model calls) and stop to ask the user if any fails")


def audit(report_path: Path, repo: Path, rules: str, note: str, unsandboxed: bool = False, always_model: bool = False, runner=None) -> str:
    """Write <report>.audit.md; return passed, failed or partly unverified. Raises SystemExit on setup errors."""
    runner = runner or claude
    text = report_path.read_text()
    report = parse(text)
    problems, unverified, log = verify(report, repo, unsandboxed)
    model = "opus" if report["rebuttals"] else NEXT_TIER.get(report["tier"], "opus")
    if problems:
        reply, model = "(deterministic checks failed; no model call)", "none"
    elif not report["rebuttals"] and not always_model:
        reply, model = "(no rebuttal; deterministic checks only, no model call)", "none"
    else:
        # Rules stay first and unchanged between runs so the prompt cache can reuse them.
        prompt = "\n\n".join([rules, "# Report under audit", text, "# Rerun log", "\n\n".join(log) or "(none)", "# Diff", diff(report, repo)])
        reply = runner(model, prompt)
        if not model_passed(reply, report):
            problems.append("the model did not uphold every verdict (see Model verdict)")
    result = "failed" if problems else "partly unverified" if unverified else "passed"
    version = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())["version"]
    out = [f"# Audit: {report_path.name}"]
    if unsandboxed:
        out.append("WARNING: project commands ran without a sandbox")
    out += [f"Plugin version: {version}", f"Report sha256: {sha256(report_path)}", f"Reviewed commit: {report['commit']}",
            f"Rules: {note}", f"Model: {model}", "", "## Problems", *([f"- {p}" for p in problems] or ["- none"]),
            "", "## Rerun log", "\n\n".join(log) or "(none)", "", "## Model verdict", reply.strip()]
    if unverified:
        out += ["", "## Run these yourself", *[f"- `{c}`" for c in unverified]]
    out += ["", f"Result: {result}"]
    report_path.with_name(re.sub(r"\.md$", "", report_path.name) + ".audit.md").write_text("\n".join(out) + "\n")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=Path)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--unsandboxed", action="store_true")
    ap.add_argument("--model", action="store_true", help="let the model judge a report that has no rebuttal too")
    args = ap.parse_args(argv)
    repo = args.repo.resolve()
    try:
        rules, note = load_rules(repo)
        trap_gate(repo, rules)
        result = audit(args.report.resolve(), repo, rules, note, args.unsandboxed, args.model)
    except (OSError, SystemExit) as e:
        print(e if isinstance(e, OSError) else e.code, file=sys.stderr)
        return 2
    return {"passed": 0, "failed": 1, "partly unverified": 3}[result]


if __name__ == "__main__":
    sys.exit(main())
