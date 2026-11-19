"""Sandbox for report commands: macOS Seatbelt (sandbox-exec) or Linux bwrap."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

SECRETS = [".ssh", ".claude", ".config", ".aws", ".gnupg", ".netrc"]


def _argv(kind: str, writable: list[Path]) -> list[str]:
    home = Path.home().resolve()
    paths = [p.resolve() for p in writable]
    if kind == "seatbelt":
        allowed = " ".join(f'(subpath "{p}")' for p in paths)
        secrets = " ".join(f'(subpath "{home / s}")' for s in SECRETS)
        return ["sandbox-exec", "-p",
                f'(version 1)(allow default)(deny file-write*)(allow file-write* {allowed} (literal "/dev/null") (subpath "/dev/fd"))'
                f'(deny file-read* {secrets})'
                # Local test servers still work; nothing the command reads can leave the machine.
                '(deny network-outbound)(allow network-outbound (remote ip "localhost:*") (remote unix-socket))']
    argv = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--unshare-net", "--die-with-parent"]
    for p in paths:
        argv += ["--bind", str(p), str(p)]
    for s in SECRETS:
        p = home / s
        if p.is_dir():
            argv += ["--tmpfs", str(p)]
        elif p.exists():
            argv += ["--ro-bind", "/dev/null", str(p)]
    return argv


def _kind() -> str | None:
    if os.environ.get("AGENT_FLOW_SANDBOX") == "none":
        return None
    kind = "seatbelt" if sys.platform == "darwin" and shutil.which("sandbox-exec") else "bwrap" if shutil.which("bwrap") else None
    if kind:
        # Probe: nested sandbox-exec and Ubuntu 24.04 user-namespace limits make an installed binary unusable.
        try:
            probe = subprocess.run([*_argv(kind, []), "/bin/sh", "-c", "true"], capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return kind if probe.returncode == 0 else None
    return None


def available() -> str | None:
    return _kind()


def run(cmd: str, cwd: Path, writable: list[Path], timeout: int = 600) -> tuple[int, str]:
    kind = available()
    if not kind:
        raise RuntimeError("no sandbox available")
    # Only what a test run needs: tokens in the session's environment must not reach the sandbox.
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "TERM", "USER") if k in os.environ}
    env.update(TMPDIR=str(writable[-1]), CI="1")
    done = subprocess.run([*_argv(kind, writable), "/bin/sh", "-c", cmd], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=timeout)
    return done.returncode, done.stdout + done.stderr
