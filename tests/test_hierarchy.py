import unittest

from hac.hierarchy import HierarchyVerifier
from hac.model import Contract, Rule, seal_contract

from helpers import contract_fixture, reseal


class HierarchyTests(unittest.TestCase):
    def test_valid_hierarchy_and_effective_rules(self):
        root, child = contract_fixture()
        verifier = HierarchyVerifier((root, child))
        self.assertEqual(verifier.validate(), ())
        self.assertEqual(len(verifier.effective_rules("child")), 3)
        self.assertEqual(verifier.effective_limits("child")["usd"], 200)

    def test_invalid_seal_is_detected(self):
        root, child = contract_fixture()
        changed = reseal(child, intent="changed")
        object.__setattr__(changed, "seal", child.seal)
        codes = {i.code for i in HierarchyVerifier((root, changed)).validate()}
        self.assertIn("INVALID_SEAL", codes)

    def test_permission_escalation_is_detected(self):
        root, child = contract_fixture()
        child = reseal(child, permissions=frozenset({*child.permissions, "delete"}))
        codes = {i.code for i in HierarchyVerifier((root, child)).validate()}
        self.assertIn("PERMISSION_ESCALATION", codes)

    def test_unauthorized_issuer_is_detected(self):
        root, child = contract_fixture()
        child = reseal(child, issuer="agent:intruder")
        codes = {i.code for i in HierarchyVerifier((root, child)).validate()}
        self.assertIn("UNAUTHORIZED_ISSUER", codes)

    def test_parent_digest_mismatch_is_detected(self):
        root, child = contract_fixture()
        child = reseal(child, parent_digest="0" * 64)
        codes = {i.code for i in HierarchyVerifier((root, child)).validate()}
        self.assertIn("PARENT_DIGEST_MISMATCH", codes)

    def test_inherited_rule_cannot_be_rewritten(self):
        root, child = contract_fixture()
        child = reseal(
            child,
            rules=(
                *child.rules,
                Rule("root.verify", "forbid", "rewrite", {"action": "other"}),
            ),
        )
        codes = {i.code for i in HierarchyVerifier((root, child)).validate()}
        self.assertIn("RULE_REWRITE", codes)

    def test_sibling_budget_conservation(self):
        root, child = contract_fixture()
        sibling = seal_contract(
            Contract(
                id="sibling",
                name="Sibling",
                issuer=root.subject,
                subject="agent:other",
                intent="Other work",
                permissions=frozenset({"read"}),
                resources=frozenset({"*"}),
                limits={"usd": 400, "actions": 10},
                parent_id=root.id,
                parent_digest=root.digest,
            )
        )
        codes = {i.code for i in HierarchyVerifier((root, child, sibling)).validate()}
        self.assertIn("BUDGET_OVERALLOCATION", codes)

    def test_missing_parent_is_detected(self):
        _, child = contract_fixture()
        codes = {i.code for i in HierarchyVerifier((child,)).validate()}
        self.assertIn("MISSING_PARENT", codes)


if __name__ == "__main__":
    unittest.main()

