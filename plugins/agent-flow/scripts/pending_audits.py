"""List review reports that still need a passing audit.

Usage: pending_audits.py [repo]   run before the final report.
Checks every worktree of repo: for each docs/<topic>/reviews/review-<round>.md (latest round only), the .audit.md next to it
must record the report's current sha256 and end `Result: passed`.
Exit: 0 nothing pending, 1 something pending (listed one per line).
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def problem(report: Path) -> str | None:
    """Why this report's audit does not count, or None when it does."""
    audit = report.with_name(report.stem + ".audit.md")
    text = audit.read_text() if audit.is_file() else ""
    if f"Report sha256: {sha256(report)}" not in text.splitlines():
        return "no audit, or the report changed after its audit"
    if text.rstrip().splitlines()[-1] != "Result: passed":
        return "audit did not pass"
    return None


def pending(repo: Path) -> list[str]:
    listing = subprocess.run(["git", "-C", str(repo), "worktree", "list", "--porcelain"], capture_output=True, text=True).stdout
    roots = [Path(l[9:]) for l in listing.splitlines() if l.startswith("worktree ")] or [repo]
    out = []
    for root in roots:
        latest = {}
        for report in root.glob("docs/*/reviews/review-*.md"):
            if m := re.fullmatch(r"review-(\d+)\.md", report.name):
                if int(m[1]) > latest.get(report.parent, (-1, None))[0]:
                    latest[report.parent] = (int(m[1]), report)
        out += [f"{r}: {why}" for _, r in sorted(latest.values()) if (why := problem(r))]
    return out


if __name__ == "__main__":
    found = pending(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    print("\n".join(found) or "no review report is waiting for an audit")
    sys.exit(1 if found else 0)
