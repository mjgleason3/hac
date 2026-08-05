import unittest

from hac.authority import Keyring
from hac.ledger import ContractLedger
from hac.manager import ContractManager
from hac.model import Event

from helpers import contract_fixture


class AuthorityAndManagerTests(unittest.TestCase):
    def setUp(self):
        self.root, self.child = contract_fixture()
        self.keyring = Keyring(
            {
                "human:owner": b"owner-key-for-tests",
                "agent:lead": b"lead-key-for-tests",
            }
        )
        self.root_cap = self.keyring.mint(
            issuer="human:owner",
            subject="agent:lead",
            actions=self.root.permissions,
            resources={"*"},
            expires_at=100,
            remaining_depth=2,
            contract_digest=self.root.digest,
        )

    def test_attenuating_capability_chain_authorizes(self):
        child_cap = self.keyring.delegate(
            self.root_cap,
            issuer="agent:lead",
            subject="agent:worker",
            actions=self.child.permissions,
            resources={"*"},
            expires_at=90,
            contract_digest=self.child.digest,
        )
        allowed, reason = self.keyring.authorize(
            (self.root_cap, child_cap),
            subject="agent:worker",
            action="read",
            resource="case:1",
            now=20,
            contract_digest=self.child.digest,
        )
        self.assertTrue(allowed, reason)

    def test_capability_escalation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "attenuate"):
            self.keyring.delegate(
                self.root_cap,
                issuer="agent:lead",
                subject="agent:worker",
                actions={*self.child.permissions, "delete"},
                resources={"*"},
                expires_at=90,
                contract_digest=self.child.digest,
            )

    def test_capability_contract_binding_is_checked(self):
        child_cap = self.keyring.delegate(
            self.root_cap,
            issuer="agent:lead",
            subject="agent:worker",
            actions={"read"},
            resources={"*"},
            expires_at=90,
            contract_digest=self.child.digest,
        )
        allowed, reason = self.keyring.authorize(
            (self.root_cap, child_cap),
            subject="agent:worker",
            action="read",
            resource="case:1",
            now=20,
            contract_digest="wrong",
        )
        self.assertFalse(allowed)
        self.assertIn("different contract", reason)

    def test_expired_capability_is_rejected(self):
        allowed, reason = self.keyring.authorize(
            (self.root_cap,),
            subject="agent:lead",
            action="read",
            resource="case:1",
            now=101,
            contract_digest=self.root.digest,
        )
        self.assertFalse(allowed)
        self.assertIn("expired", reason)

    def test_manager_builds_valid_ledger_and_firewall(self):
        manager = ContractManager((self.root, self.child))
        summary = manager.summary()
        self.assertEqual(summary.contracts, 2)
        self.assertTrue(summary.ledger_valid)
        self.assertTrue(
            manager.firewall("child").preflight(Event(0, "agent:worker", "read")).allowed
        )

    def test_ledger_rejects_wrong_approver(self):
        ledger = ContractLedger()
        with self.assertRaisesRegex(ValueError, "declared issuer"):
            ledger.activate(self.root, approved_by="agent:intruder")


if __name__ == "__main__":
    unittest.main()

