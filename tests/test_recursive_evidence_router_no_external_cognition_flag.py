import json
import pathlib
import unittest


class StableAutonomyFlagTest(unittest.TestCase):
    def test_stable_end_state_requires_no_external_cognition(self):
        path = pathlib.Path(__file__).resolve().parents[1] / "contracts" / "QIKVRT_UNIVERSAL_TERMINAL_RECURSIVE_EVIDENCE_INVARIANT.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        self.assertIs(contract["stable_end_state_requires_external_cognition"], False)
        self.assertIn("routing_knowledge_repository_native", contract["autonomy"])
        self.assertIn("validation_rules_repository_native", contract["autonomy"])
        self.assertIn("proof_dependencies_repository_native", contract["autonomy"])
        self.assertIn("reconstruction_knowledge_repository_native", contract["autonomy"])


if __name__ == "__main__":
    unittest.main()
