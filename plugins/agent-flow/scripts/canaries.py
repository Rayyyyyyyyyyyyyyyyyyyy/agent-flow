"""Run the project's trap reports: planted-flaw reports must fail the audit, clean ones must pass.

Usage: canaries.py --repo <repo> [--force]
Trap reports live in <repo>/.agent-flow/auditor/canaries/ with expected.json ({"<report>.md": "passed"|"failed"});
they cite the project's own code at real commits. Every report goes through the model path (model calls).
Skips when rules, trap reports, audit.py, the tier map and `claude --version` are unchanged since the last full pass.
Exit: 0 every trap report matched and .agent-flow/auditor/canary-stamp.txt was written, 1 a mismatch, 2 setup error.
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import audit


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    repo = args.repo.resolve()
    canaries = repo / audit.PROJECT / "canaries"
    stamp_file = repo / audit.PROJECT / "canary-stamp.txt"
    try:
        expected = json.loads((canaries / "expected.json").read_text())
        rules, note = audit.load_rules(repo)
        current = audit.stamp(repo, rules)
        if not args.force and stamp_file.is_file() and stamp_file.read_text().strip() == current:
            print("rules, trap reports, audit.py, tier map and claude version unchanged; skipped")
            return 0
        out = Path(tempfile.mkdtemp(prefix="agent-flow-canaries-"))
        misses = 0
        for name, want in expected.items():
            report = out / name
            shutil.copyfile(canaries / name, report)
            got = audit.audit(report, repo, rules, note, always_model=True)
            misses += got != want
            print(f"{'OK  ' if got == want else 'MISS'} {name}: expected {want}, got {got}")
    except (OSError, ValueError, SystemExit) as e:
        print(e.code if isinstance(e, SystemExit) else e, file=sys.stderr)
        return 2
    print(f"audit output in {out}")
    if misses:
        print(f"{misses} trap report(s) did not match; the auditor is not fit for this project")
        return 1
    stamp_file.write_text(current + "\n")
    print(f"all matched; wrote {stamp_file.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
