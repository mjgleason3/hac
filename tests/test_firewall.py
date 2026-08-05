import unittest

from hac.firewall import ContractFirewall
from hac.model import Event

from helpers import contract_fixture


class FirewallTests(unittest.TestCase):
    def setUp(self):
        self.root, self.child = contract_fixture()
        self.firewall = ContractFirewall((self.root, self.child), "child")

    def test_safe_action_is_allowed(self):
        decision = self.firewall.preflight(Event(0, "agent:worker", "read", "case:1"))
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.outcome, "ALLOW")

    def test_inherited_precondition_blocks_action(self):
        decision = self.firewall.preflight(
            Event(2, "agent:worker", "pay", "case:1", {"usd": 50})
        )
        self.assertFalse(decision.allowed)
        self.assertIn("root.verify", {v.rule_id for v in decision.violations})

    def test_same_resource_precondition(self):
        decision = self.firewall.preflight(
            Event(2, "agent:worker", "pay", "case:1", {"usd": 50}),
            (Event(1, "agent:worker", "verify", "case:2"),),
        )
        self.assertFalse(decision.allowed)

    def test_field_limit_blocks_action(self):
        decision = self.firewall.preflight(
            Event(2, "agent:worker", "pay", "case:1", {"usd": 120}),
            (Event(1, "agent:worker", "verify", "case:1"),),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("child.single", {v.rule_id for v in decision.violations})

    def test_delegated_allocation_blocks_cumulative_use(self):
        history = (
            Event(0, "agent:worker", "verify", "case:1"),
            Event(1, "agent:worker", "pay", "case:1", {"usd": 100}),
            Event(2, "agent:worker", "pay", "case:1", {"usd": 100}),
        )
        decision = self.firewall.preflight(
            Event(3, "agent:worker", "pay", "case:1", {"usd": 1}), history
        )
        self.assertFalse(decision.allowed)
        self.assertIn("allocation.usd", {v.rule_id for v in decision.violations})

    def test_actor_mismatch_is_blocked(self):
        decision = self.firewall.preflight(Event(0, "agent:other", "read", "case:1"))
        self.assertFalse(decision.allowed)
        self.assertIn("ACTOR_MISMATCH", {v.code for v in decision.violations})

    def test_completed_trace_reports_missed_response(self):
        report = self.firewall.audit_trace(
            (Event(0, "agent:worker", "risk", "case:1"),), complete=True
        )
        self.assertFalse(report.passed)
        self.assertIn("DEADLINE_MISSED", {v.code for v in report.violations})

    def test_open_trace_keeps_response_pending(self):
        report = self.firewall.audit_trace(
            (Event(0, "agent:worker", "risk", "case:1"),), complete=False
        )
        self.assertTrue(report.passed)
        self.assertEqual(len(report.pending_obligations), 1)

    def test_timely_response_satisfies_obligation(self):
        report = self.firewall.audit_trace(
            (
                Event(0, "agent:worker", "risk", "case:1"),
                Event(30, "agent:worker", "escalate", "case:1"),
            )
        )
        self.assertTrue(report.passed)


if __name__ == "__main__":
    unittest.main()

