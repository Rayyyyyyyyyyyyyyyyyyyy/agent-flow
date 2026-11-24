import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins/agent-flow/scripts"))
import merge_gate

GREEN = [{"name": "verify", "state": "SUCCESS", "bucket": "pass"},
         {"name": "evidence-check", "state": "SUCCESS", "bucket": "pass"},
         {"name": "x", "state": "SKIPPED", "bucket": "skipping"}]
PLAN = [{"mergeCommit": {"oid": "plan1"}}]


def fake_gh(bindir, checks, head="agent-flow/t", labels=(), plans=PLAN, changed=("src/a.py",)):
    view = {"baseRefName": "main", "headRefName": head, "headRefOid": "head1",
            "labels": [{"name": l} for l in labels]}
    (bindir / "gh").write_text(
        "#!/bin/sh\ncase \"$*\" in\n"
        "\"pr checks 7 --json name,state,bucket\") echo '%s';;\n"
        "\"pr view 7 --json baseRefName,headRefName,headRefOid,labels\") echo '%s';;\n"
        "\"pr list --base %s --head %s-plan --state merged --json mergeCommit\") echo '%s';;\n"
        "\"api repos/{owner}/{repo}/compare/plan1...head1 --jq .files[].filename\"|"
        "\"api repos/{owner}/{repo}/compare/main...head1 --jq .files[].filename\") printf '%s\\n';;\n"
        "esac\n" % (json.dumps(checks), json.dumps(view), head, head, json.dumps(plans), "\\n".join(changed)))
    (bindir / "gh").chmod(0o755)


class MergeGateTest(unittest.TestCase):
    def gate(self, checks=GREEN, stop=False, config=None, gh=True, **kw):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / ".agent-flow").mkdir()
        if stop:
            (root / ".agent-flow/STOP").write_text("")
        if config is not None:
            (root / ".agent-flow/config").write_text(config)
        bindir = root / "bin"
        bindir.mkdir()
        if gh:
            fake_gh(bindir, checks, **kw)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": str(bindir)}), contextlib.redirect_stdout(out):
            code = merge_gate.main(["7", "--repo-root", str(root)])
        return code, out.getvalue()

    def test_passes(self):
        self.assertEqual(self.gate(), (0, ""))

    def test_failing_check_blocks(self):
        code, out = self.gate(checks=GREEN + [{"name": "bad", "state": "FAILURE", "bucket": "fail"}])
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED: CI not green: bad", out)

    def test_pending_check_blocks(self):
        self.assertEqual(self.gate(checks=GREEN + [{"name": "p", "state": "PENDING", "bucket": "pending"}])[0], 1)

    def test_no_passing_check_blocks(self):
        self.assertEqual(self.gate(checks=[GREEN[2]])[0], 1)

    def test_missing_evidence_check_blocks(self):
        code, out = self.gate(checks=[GREEN[0]])
        self.assertEqual(code, 1)
        self.assertIn("evidence-check", out)

    def test_no_merged_plan_blocks(self):
        code, out = self.gate(plans=[])
        self.assertEqual(code, 1)
        self.assertIn("no merged Plan PR", out)

    def test_locked_paths_after_plan_block(self):
        for path in (".agent-flow/verify.py", ".github/workflows/ci.yml", "openspec/config.yaml",
                     "openspec/changes/t/specs/cap/spec.md"):
            code, out = self.gate(changed=("src/a.py", path))
            self.assertEqual(code, 1, path)
            self.assertIn("changes locked paths", out)
            self.assertIn(path, out)

    def test_unlocked_docs_pass(self):
        self.assertEqual(self.gate(changed=("docs/t/discussion.md", "openspec/changes/t/tasks.md"))[0], 0)

    def test_archive_pr_inside_openspec_passes(self):
        files = ("openspec/specs/cap/spec.md", "openspec/changes/t/specs/cap/spec.md",
                 "openspec/changes/archive/2026-11-24-t/specs/cap/spec.md")
        self.assertEqual(self.gate(head="agent-flow/t-archive", checks=[GREEN[0]], plans=[], changed=files), (0, ""))

    def test_archive_pr_outside_its_paths_blocks(self):
        for path in ("src/a.py", "openspec/config.yaml", "openspec/changes/other/specs/cap/spec.md"):
            code, out = self.gate(head="agent-flow/t-archive", checks=[GREEN[0]], changed=("openspec/specs/c/spec.md", path))
            self.assertEqual(code, 1, path)
            self.assertIn("archive PR changes files outside", out)
            self.assertIn(path, out)

    def test_plan_pr_needs_owner(self):
        code, out = self.gate(head="agent-flow/t-plan", checks=[GREEN[0]])
        self.assertEqual(code, 1)
        self.assertIn("Plan PR: the Owner merges it", out)

    def test_plan_pr_with_plan_agent(self):
        self.assertEqual(self.gate(head="agent-flow/t-plan", checks=[GREEN[0]], config="plan: agent\n")[0], 0)

    def test_owner_judges_label_blocks(self):
        code, out = self.gate(labels=["agent-flow:owner-judges"])
        self.assertEqual(code, 1)
        self.assertIn("owner-judges", out)

    def test_stop_file_blocks(self):
        self.assertEqual(self.gate(stop=True)[0], 1)

    def test_merge_never_blocks(self):
        self.assertEqual(self.gate(config="x: 1\nmerge: never\n")[0], 1)

    def test_merge_never_tolerates_case_and_spaces(self):
        for line in ("merge:never", "Merge: Never ", "  MERGE :  never"):
            self.assertEqual(self.gate(config=line + "\n")[0], 1, line)

    def test_other_config_passes(self):
        self.assertEqual(self.gate(config="merge: auto\n")[0], 0)

    def test_reasons_one_per_line(self):
        code, out = self.gate(plans=[], stop=True)
        self.assertEqual([l[:8] for l in out.splitlines()], ["BLOCKED:"] * 2)

    def test_setup_error_without_gh(self):
        self.assertEqual(self.gate(gh=False)[0], 2)


if __name__ == "__main__":
    unittest.main()
