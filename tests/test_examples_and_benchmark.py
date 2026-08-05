import unittest
from pathlib import Path

from hac.benchmark import delegation_fault_examples, run_benchmark
from hac.firewall import ContractFirewall
from hac.hierarchy import HierarchyVerifier
from hac.model import load_bundle, load_trace


ROOT = Path(__file__).resolve().parents[1]


class ExamplesAndBenchmarkTests(unittest.TestCase):
    def test_all_example_bundles_validate(self):
        for path in (ROOT / "examples").glob("*/contracts.json"):
            with self.subTest(path=path):
                self.assertEqual(HierarchyVerifier(load_bundle(path)).validate(), ())

    def test_support_safe_and_unsafe_traces(self):
        base = ROOT / "examples" / "support"
        firewall = ContractFirewall(load_bundle(base / "contracts.json"), "support.refunds")
        self.assertTrue(firewall.audit_trace(load_trace(base / "safe_trace.json")).passed)
        self.assertFalse(firewall.audit_trace(load_trace(base / "unsafe_trace.json")).passed)

    def test_research_privacy_violation_is_found(self):
        base = ROOT / "examples" / "research"
        report = ContractFirewall(
            load_bundle(base / "contracts.json"), "research.root"
        ).audit_trace(load_trace(base / "privacy_trace.json"))
        self.assertIn("research.no-private-upload", {v.rule_id for v in report.violations})

    def test_incident_deadline_violation_is_found(self):
        base = ROOT / "examples" / "incident"
        report = ContractFirewall(
            load_bundle(base / "contracts.json"), "incident.root"
        ).audit_trace(load_trace(base / "late_page_trace.json"))
        self.assertIn("incident.page-sev1", {v.rule_id for v in report.violations})

    def test_benchmark_hac_prevents_all_labeled_unsafe_attempts(self):
        results = {result.approach: result for result in run_benchmark(repetitions=2)}
        hac = results["HAC"]
        self.assertEqual(hac.unsafe_prevented, hac.unsafe_total)
        self.assertEqual(hac.false_blocks, 0)

    def test_delegation_fault_fixtures_are_detected(self):
        self.assertEqual(delegation_fault_examples(), (2, 2))


if __name__ == "__main__":
    unittest.main()

