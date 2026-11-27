"""Which runs get Linear: reads for the runs that answer people or build, saves only for the owner's own orders, and
nothing at all with `linear` off. The connector is blocked in every other run."""
import unittest
from unittest import mock

from lib import claude, linear
from lib.settings import CONFIG

SAVE = linear.PREFIX + "save_issue"
READ = linear.PREFIX + "get_issue"
BLOCKED = "mcp__claude_ai_Linear__*"


class LinearPerRunKind(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(CONFIG, {"linear": True})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_orders_read_and_save(self):
        for kind in ("order", "answer"):
            self.assertIn(SAVE, linear.tools(kind))
            self.assertIn(READ, linear.tools(kind))

    def test_runs_that_answer_people_or_build_only_read(self):
        for kind in ("bot", "person", "build", "prfix"):
            self.assertIn(READ, linear.tools(kind), kind)
            self.assertNotIn(SAVE, linear.tools(kind), kind)

    def test_other_runs_get_nothing_and_keep_it_blocked(self):
        for kind in ("daily", "datadog", "audit", "knowledge", "commitments", "prthreads", "calls"):
            self.assertEqual([], linear.tools(kind), kind)
        self.assertIn(BLOCKED, claude.blocked_connectors())
        self.assertNotIn(BLOCKED, claude.blocked_connectors(("Linear",)))

    def test_off_in_the_config(self):
        with mock.patch.dict(CONFIG, {"linear": False}):
            for kind in ("order", "bot", "build"):
                self.assertEqual([], linear.tools(kind), kind)

    def test_guard_and_runs_name_the_same_tools(self):
        self.assertTrue(set(linear.WRITE).isdisjoint(linear.READ))
        self.assertFalse(any(name.startswith(("delete", "merge", "create")) for name in linear.READ + linear.WRITE))


if __name__ == "__main__":
    unittest.main()
