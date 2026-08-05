import unittest

from hac.compiler import RequirementCompiler


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.compiler = RequirementCompiler()

    def test_never(self):
        result = self.compiler.compile("Never export private data.")
        self.assertEqual(result.rule.kind, "forbid")
        self.assertEqual(result.rule.params["action"], "export_private_data")
        self.assertIn("G !action", result.formula)

    def test_requires_before(self):
        result = self.compiler.compile("Require verify identity before issue refund.")
        self.assertEqual(result.rule.kind, "requires_before")
        self.assertEqual(result.rule.params["required"], "verify_identity")

    def test_response_within(self):
        result = self.compiler.compile(
            "After risk detected, require escalate within 10 minutes."
        )
        self.assertEqual(result.rule.kind, "response_within")
        self.assertEqual(result.rule.params["within_seconds"], 600)
        self.assertIn("F_[0,600]", result.formula)

    def test_field_limit(self):
        result = self.compiler.compile("Keep risk score <= 0.25.")
        self.assertEqual(result.rule.params["field"], "risk_score")
        self.assertEqual(result.rule.params["value"], 0.25)

    def test_count_limit(self):
        result = self.compiler.compile("Limit retry payment to 2 times.")
        self.assertEqual(result.rule.kind, "count_limit")
        self.assertEqual(result.rule.params["max"], 2)

    def test_ambiguous_input_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.compiler.compile("Do the right thing most of the time")


if __name__ == "__main__":
    unittest.main()

