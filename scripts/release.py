#!/usr/bin/env python3
"""Tag and publish a GitHub release for the plugin's current version, once per version.

Usage: release.py <commit-sha> [--dry-run]. Reads `version` from plugins/agent-flow/.claude-plugin/plugin.json.
If tag `v<version>` already exists (locally or on origin), prints SKIP and exits 0. Otherwise runs
`gh release create v<version> --target <sha> --title "agent-flow <version>" --generate-notes`, adding
`--prerelease` while the major version is 0. `--dry-run` prints that command instead of running it.
Exit 0 ok or skipped, 1 malformed version or gh failed, 2 usage.
"""
import json
import re
import subprocess
import sys

MANIFEST = "plugins/agent-flow/.claude-plugin/plugin.json"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def tag_exists(tag):
    local = subprocess.run(["git", "tag", "-l", tag], capture_output=True, text=True).stdout.strip()
    remote = subprocess.run(["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"], capture_output=True,
                            text=True).stdout.strip()
    return bool(local or remote)


def main(argv):
    args = [a for a in argv if a != "--dry-run"]
    if len(args) != 1:
        print("usage: release.py <commit-sha> [--dry-run]", file=sys.stderr)
        return 2
    sha = args[0]
    version = json.load(open(MANIFEST)).get("version", "")
    m = SEMVER.match(version)
    if not m:
        print(f"FAIL {MANIFEST}: version {version!r} is not X.Y.Z")
        return 1
    tag = f"v{version}"
    if tag_exists(tag):
        print(f"SKIP {tag} already exists")
        return 0
    cmd = ["gh", "release", "create", tag, "--target", sha, "--title", f"agent-flow {version}", "--generate-notes"]
    if m.group(1) == "0":
        cmd.append("--prerelease")
    if "--dry-run" in argv:
        print("DRY " + " ".join(cmd))
        return 0
    p = subprocess.run(cmd)
    if p.returncode:
        print(f"FAIL gh release create exited {p.returncode}")
        return 1
    print(f"RELEASED {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
