"""Maintainer tool: run every canary report through audit.py and write the stamp the plugin ships with.

Usage: run_canaries.py [--dry-run] [--model <model>] [--plugin <dir>]
Canaries with a rebuttal call the model through audit.py --model (needs `claude`). --dry-run only lists the names.
Exit: 0 every canary matched expected.json and the stamp was written, 1 a canary did not match.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--model")
ap.add_argument("--plugin", type=Path, default=Path(__file__).resolve().parents[1] / "plugins/agent-flow")
args = ap.parse_args()
canaries = args.plugin / "auditor/canaries"
expected = json.loads((canaries / "expected.json").read_text())
if args.dry_run:
    print("\n".join(expected))
    sys.exit(0)

with tempfile.TemporaryDirectory(prefix="canary-") as temp:
    repo = Path(temp) / "fixture"
    shutil.copytree(canaries / "fixture", repo)
    for git in (["init", "-q"], ["add", "-A"], ["-c", "user.name=canary", "-c", "user.email=canary@localhost", "commit", "-qm", "fixture"]):
        subprocess.run(["git", "-C", str(repo), *git], check=True, capture_output=True)
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    misses = 0
    for name, want in expected.items():
        report = Path(temp) / name
        report.write_text((canaries / name).read_text().replace("FIXTURE", commit))
        # The fixture is ours, so its commands run without a sandbox; the stamp check is skipped because this run produces the stamp.
        cmd = [sys.executable, str(args.plugin / "scripts/audit.py"), str(report), "--repo", str(repo), "--unsandboxed"]
        got = subprocess.run(cmd + (["--model", args.model] if args.model else []), capture_output=True, text=True,
                             env={**os.environ, "AGENT_FLOW_SKIP_STAMP": "1"}).returncode
        misses += got != want
        print(f"{'ok  ' if got == want else 'MISS'} {name}: expected exit {want}, got {got}")
if misses:
    sys.exit(1)
version = json.loads((args.plugin / ".claude-plugin/plugin.json").read_text())["version"]
(args.plugin / "auditor/canary-stamp.txt").write_text("\n".join([f"version: {version}", *(f"{n}: ok" for n in expected)]) + "\n")
