"""guard.py: the PreToolUse hook that applies the locks and the Ask-first list before a tool runs (C24)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "plugins/agent-flow/scripts/guard.py"
HOOKS = ROOT / "plugins/agent-flow/hooks/hooks.json"


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class GuardTest(unittest.TestCase):
    def repo(self, branch="agent-flow/t", agent_flow=True, config=None):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        git(d, "init", "-q", "-b", "main")
        git(d, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "x")
        if branch != "main":
            git(d, "checkout", "-q", "-b", branch)
        if agent_flow:
            (d / ".agent-flow").mkdir()
            if config:
                (d / ".agent-flow/config").write_text(config)
        return d

    def run_guard(self, cwd, tool, raw=None, **inp):
        payload = raw if raw is not None else json.dumps({"tool_name": tool, "tool_input": inp, "cwd": str(cwd)})
        p = subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True, text=True, cwd=cwd)
        self.assertEqual(p.returncode, 0, p.stderr)
        if not p.stdout.strip():
            return None, ""
        out = json.loads(p.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PreToolUse")
        return out["permissionDecision"], out["permissionDecisionReason"]

    def test_edit_locked_path_denied_on_integration_branch(self):
        d = self.repo()
        for path in (".agent-flow/verify.py", ".github/workflows/ci.yml", ".gitlab-ci.yml", "openspec/config.yaml",
                     "openspec/changes/t/specs/cap/spec.md"):
            decision, reason = self.run_guard(d, "Edit", file_path=str(d / path))
            self.assertEqual(decision, "deny", path)
            self.assertIn("new Plan PR", reason)
        self.assertEqual(self.run_guard(d, "Write", file_path=str(d / "src/a.py"))[0], None)
        self.assertEqual(self.run_guard(d, "Edit", file_path=str(d / "openspec/changes/t/tasks.md"))[0], None)

    def test_plan_branch_and_default_branch_may_edit_locked_paths(self):
        for br in ("agent-flow/t-plan", "main"):
            d = self.repo(branch=br)
            self.assertEqual(self.run_guard(d, "Edit", file_path=str(d / ".agent-flow/verify.py"))[0], None, br)

    def test_protect_globs(self):
        d = self.repo(config="protect: .eslintrc*\n")
        self.assertEqual(self.run_guard(d, "Write", file_path=str(d / ".eslintrc.json"))[0], "deny")
        self.assertEqual(self.run_guard(d, "Bash", command="sed -i s/a/b/ .eslintrc.json")[0], "deny")

    def test_repo_without_agent_flow_is_untouched(self):
        d = self.repo(agent_flow=False)
        self.assertEqual(self.run_guard(d, "Edit", file_path=str(d / ".github/workflows/ci.yml"))[0], None)
        self.assertEqual(self.run_guard(d, "Bash", command="git push --force")[0], None)

    def test_bash_writes_to_locked_paths_denied(self):
        d = self.repo()
        for cmd in ("echo x > .agent-flow/config", "cp /tmp/x .github/workflows/ci.yml",
                    "sed -i s/a/b/ openspec/changes/t/specs/cap/spec.md", "git checkout main -- .agent-flow/verify.py",
                    "cd . && rm openspec/config.yaml"):
            self.assertEqual(self.run_guard(d, "Bash", command=cmd)[0], "deny", cmd)
        for cmd in ("python3 .agent-flow/verify.py", "cat .agent-flow/skills.md", "cp .agent-flow/verify.py /tmp/v.py",
                    "git diff main -- .github/workflows/ci.yml 2>&1"):
            self.assertEqual(self.run_guard(d, "Bash", command=cmd)[0], None, cmd)

    def test_destructive_commands_ask(self):
        d = self.repo(branch="main")
        for cmd in ("git push --force origin x", "git push -f", "git push origin +x", "git push origin --delete x",
                    "git push origin :x", "git reset --hard HEAD~1", "git clean -fdx", "git checkout -- src/a.py",
                    "git checkout .", "git restore src/a.py", "git branch -D x", "git stash drop",
                    "git worktree remove --force ../w", "rm -rf build", "sudo rm -r /tmp/x", "gh repo delete o/r --yes", "glab release delete v1",
                    "git -C sub reset --hard", "bash -c 'git reset --hard'", "ls && git clean -f"):
            decision, reason = self.run_guard(d, "Bash", command=cmd)
            self.assertEqual(decision, "ask", cmd)
            self.assertIn("Ask first", reason)
        for cmd in ("git push -u origin agent-flow/t", "git checkout -b x", "git restore --staged a.py",
                    "git branch -d x", "rm -f a.txt", "git clean -n", "git worktree remove ../w",
                    "python3 land.py 7"):
            self.assertEqual(self.run_guard(d, "Bash", command=cmd)[0], None, cmd)

    def test_fail_closed(self):
        d = self.repo()
        self.assertEqual(self.run_guard(d, "Bash", raw="not json")[0], "deny")
        self.assertEqual(self.run_guard(d, "Bash", command="echo 'unbalanced")[0], "ask")

    def test_hooks_json_runs_guard_before_edits_and_bash(self):
        entry = json.loads(HOOKS.read_text())["hooks"]["PreToolUse"][0]
        for tool in ("Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"):
            self.assertIn(tool, entry["matcher"].split("|"))
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/guard.py", entry["hooks"][0]["command"])


if __name__ == "__main__":
    unittest.main()
