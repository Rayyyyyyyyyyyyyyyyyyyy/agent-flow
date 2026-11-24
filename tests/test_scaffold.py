import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Scaffold(unittest.TestCase):
    def test_marketplace_lists_plugin(self):
        m = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual(m["name"], "agent-flow")
        self.assertEqual(m["plugins"][0]["source"], "./plugins/agent-flow")
        p = json.loads((ROOT / "plugins/agent-flow/.claude-plugin/plugin.json").read_text())
        # no pinned version: installs track the commit SHA, so every merge reaches users
        self.assertNotIn("version", p)
        self.assertNotIn("version", m["plugins"][0])


if __name__ == "__main__":
    unittest.main()
