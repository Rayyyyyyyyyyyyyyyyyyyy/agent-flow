"""Re-run a review report's evidence at the reviewed commit and write <report>.audit.md.

Usage: audit.py <report> --repo <repo> [--unsandboxed] [--model <model>]
Exit: 0 passed, 1 failed, 3 partly unverified, 2 usage or setup error. Format: docs/agent-flow/contracts.md.
"""
import argparse
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
ITEM = re.compile(r"^### (\S+) — (PASS|FAIL|UNKNOWN)\s*$")
REBUT_ITEM = re.compile(r"^### (\S+)\s*$")
REBUTTAL = "## Rebuttal"
SOURCE = re.compile(r"^(Command|Reproduce|Position): `(.+)`\s*$")
EXPECT = re.compile(r"^(Output contains|Actual contains|Contains): `(.+)`\s*$")
EXIT_MARK = re.compile(r"\[exit -?\d+\]")
VERDICT_WORD = re.compile(r"PASS|FAIL|UNKNOWN|Rebuttal")
READONLY = {"grep", "test", "ls", "cat", "head", "tail", "wc"}
GIT_READONLY = {"diff", "show", "log", "status", "rev-parse", "ls-files", "grep"}
GIT_WRITES = ("--output", "-O", "--open-files-in-pager", "--ext-diff")
METACHARS = set(";&|<>$`\\(){}*?[]~!#\"'\n")  # shortcut: quotes count as metacharacters, so quoted args become project commands
RUN_TIMEOUT = 600


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
    problems, items, rebuttals, cur, rebutting = [], [], [], None, False
    for line in text.splitlines():
        if line.rstrip() == REBUTTAL:
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
    env.update(TMPDIR=str(scratch), CI="1")
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
        add = subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(tree), report["commit"]], capture_output=True, text=True)
        if add.returncode:
            raise SystemExit(f"cannot open a worktree at {report['commit']}: {add.stderr.strip()}")
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
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(tree)], capture_output=True)
    return problems, unverified, log


def judge_rebuttals(report: dict, text: str, log: list[str], model: str) -> list[str]:
    prompt = "\n\n".join(["Judge each rebuttal in this review report. The rerun log shows what its commands printed. "
                          "For each rebuttal ID write one line `<ID>: upheld` or `<ID>: not upheld`.", text, "\n\n".join(log)])
    with tempfile.TemporaryDirectory(prefix="audit-model-") as cwd:
        done = subprocess.run(["claude", "-p", "--model", model, "--tools", "", "--no-session-persistence", "--strict-mcp-config"],
                              input=prompt, cwd=cwd, capture_output=True, text=True, timeout=1800)
    replies = re.findall(r"^\W*(\S+?):\s*(upheld|not upheld)\s*$", done.stdout if done.returncode == 0 else "", re.M)
    return [f"rebuttal {r['id']} not upheld by the model" for r in report["rebuttals"] if replies.count((r["id"], "upheld")) != 1 or (r["id"], "not upheld") in replies]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=Path)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--unsandboxed", action="store_true")
    ap.add_argument("--model", default="opus")
    args = ap.parse_args(argv)
    version = json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())["version"]
    stamp_file = PLUGIN / "auditor/canary-stamp.txt"
    try:
        text = args.report.read_text()
        stamp = stamp_file.read_text().splitlines()[0].removeprefix("version: ") if stamp_file.exists() else "none"
        if stamp != version and not os.environ.get("AGENT_FLOW_SKIP_STAMP"):
            raise SystemExit(f"canary stamp is for {stamp}, plugin is {version}; maintainer must run scripts/run_canaries.py")
        report = parse(text)
        problems, unverified, log = verify(report, args.repo.resolve(), args.unsandboxed)
    except (OSError, SystemExit) as e:
        print(e if isinstance(e, OSError) else e.code, file=sys.stderr)
        return 2
    if report["rebuttals"] and not problems:
        problems += judge_rebuttals(report, text, log, args.model)
    result = "failed" if problems else "partly unverified" if unverified else "passed"
    out = [f"# Audit: {args.report.name}"]
    if args.unsandboxed:
        out.append("WARNING: project commands ran without a sandbox")
    out += [f"Plugin version: {version}", f"Reviewed commit: {report['commit']}", "", "## Problems", *([f"- {p}" for p in problems] or ["- none"]),
            "", "## Rerun log", "\n\n".join(log) or "(none)"]
    if unverified:
        out += ["", "## Run these yourself", *[f"- `{c}`" for c in unverified]]
    out += ["", f"Result: {result}"]
    args.report.with_name(re.sub(r"\.md$", "", args.report.name) + ".audit.md").write_text("\n".join(out) + "\n")
    return {"passed": 0, "failed": 1, "partly unverified": 3}[result]


if __name__ == "__main__":
    sys.exit(main())
