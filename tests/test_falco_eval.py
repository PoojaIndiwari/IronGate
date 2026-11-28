"""Tests for the Falco condition evaluator and for the shipped rules (run in CI on every PR)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

import falco_eval  # noqa: E402
import test_falco_rules as replay  # noqa: E402


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.ev = falco_eval.Evaluator({"names": ["a", "b"]})
        self.event = {"evt.type": "execve", "evt.dir": "<", "container.id": "abc", "proc.name": "a"}

    def test_macros_lists_and_operators(self):
        self.assertTrue(self.ev.matches("spawned_process and container and proc.name in (names)", self.event))
        self.assertFalse(self.ev.matches("spawned_process and not container", self.event))
        self.assertTrue(self.ev.matches('proc.name startswith "a" and not proc.name contains z', self.event))

    def test_missing_field_never_matches(self):
        self.assertFalse(self.ev.matches("fd.name startswith /etc", self.event))
        self.assertFalse(self.ev.matches("fd.name != /etc", self.event))

    def test_unknown_macro_is_an_error(self):
        with self.assertRaises(ValueError):
            self.ev.matches("spawned_process and not_a_macro", self.event)


class ShippedRuleTests(unittest.TestCase):
    def setUp(self):
        self.lists, self.rules = replay.parse_rules_file(replay.RULES_PATH)

    def test_rules_are_valid(self):
        self.assertEqual(replay.validate_rules(self.lists, self.rules), [])

    def fire(self, event):
        return replay.evaluate_event(event, self.lists, self.rules)

    def test_imds_is_caught_without_a_recorded_connect_address(self):
        event = {"evt.type": "execve", "evt.dir": "<", "container.id": "abc", "k8s.ns.name": "paynest",
                 "proc.name": "wget", "proc.cmdline": "wget -T 3 http://169.254.169.254/"}
        self.assertEqual(self.fire(event), ["Paynest Contact IMDS"])

    def test_miner_is_caught_when_the_pool_is_unreachable(self):
        event = {"evt.type": "execve", "evt.dir": "<", "container.id": "abc", "k8s.ns.name": "paynest",
                 "proc.name": "python3", "proc.exe": "python3", "proc.cmdline": "python3 m.py -o stratum+tcp://x:3333"}
        self.assertEqual(self.fire(event), ["Paynest Crypto Miner Signs"])

    def test_every_fixture_passes(self):
        import json
        for line in replay.CASES_PATH.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            with self.subTest(row["case"]):
                self.assertEqual(self.fire(row["event"]), row["expected"])


if __name__ == "__main__":
    unittest.main()
