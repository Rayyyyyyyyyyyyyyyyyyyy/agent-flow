"""Run one reviewer pass in a lean `claude -p`: the plugin's reviewer.md body as the whole system prompt,
only Read/Write/Bash, no Skills listing, MCP servers or user-level hooks. Prints the reply, tokens and cost.

usage: python3 review.py <prompt-file> [--cwd <repo>] [--model opus]
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

REVIEWER = Path(__file__).resolve().parent.parent / "agents" / "reviewer.md"


def last_context(usage: dict) -> int:
    """Tokens of the final request: what the reviewer held at the end (the same measure as a subagent's tokens)."""
    it = (usage.get("iterations") or [usage])[-1]
    return sum(it.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"))


def body(text: str) -> str:
    """reviewer.md without its YAML frontmatter."""
    if text.startswith("---\n"):
        return text.split("\n---\n", 1)[1]
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", type=Path)
    ap.add_argument("--cwd", type=Path, default=Path.cwd())
    ap.add_argument("--model", default="opus")
    a = ap.parse_args()
    with tempfile.NamedTemporaryFile("w", suffix=".md") as sp:
        sp.write(body(REVIEWER.read_text()))
        sp.flush()
        cmd = ["claude", "-p", "--system-prompt-file", sp.name, "--model", a.model,
               "--tools", "Read,Write,Bash", "--allowedTools", "Bash", "Read", "Write",
               "--disable-slash-commands", "--strict-mcp-config", "--setting-sources", "project",
               "--no-session-persistence", "--output-format", "json"]
        done = subprocess.run(cmd, input=a.prompt.read_text(), cwd=a.cwd, capture_output=True, text=True)
    if done.returncode:
        print(done.stderr or done.stdout, file=sys.stderr)
        return done.returncode
    out = json.loads(done.stdout)
    print(out.get("result", ""))
    print(f"\n[review tokens: {last_context(out.get('usage', {}))}; cost ${out.get('total_cost_usd', 0):.2f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
