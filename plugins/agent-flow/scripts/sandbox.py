"""Sandbox for report commands. Backends arrive in #8; until then nothing is available."""
import os
from pathlib import Path


def available() -> str | None:
    if os.environ.get("AGENT_FLOW_SANDBOX") == "none":
        return None
    return None  # shortcut: no backend yet, #8 adds seatbelt and bwrap


def run(cmd: str, cwd: Path, writable: list[Path], timeout: int = 600) -> tuple[int, str]:
    raise RuntimeError("no sandbox available")
