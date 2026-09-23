import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/standards/QIKVRT_UNICODE_DATA_EXCHANGE_V1.md"
POLICY = ROOT / "policy/QIKVRT_UNICODE_DATA_EXCHANGE_V1.json"
ADOPTION = ROOT / "state/mesh/QIKVRT_UNICODE_DATA_EXCHANGE_ADOPTION_V1.json"
CONTEXT = ROOT / "AI_CONTEXT.json"
MESH = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"


class UnicodeDataExchangeStandardTests(unittest.TestCase):
    def test_normative_files_exist(self):
        for path in (DOC, POLICY, ADOPTION):
            self.assertTrue(path.is_file(), path)

    def test_text_profile_is_canonical(self):
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["standard_id"], "QIKVRT-UTF8-UNICODE-EXCHANGE-V1")
        self.assertEqual(policy["transport"]["encoding"], "UTF-8")
        self.assertEqual(policy["transport"]["unicode_normalization"], "NFC")
        self.assertEqual(policy["transport"]["line_ending"], "LF")
        self.assertEqual(policy["transport"]["canonical_math_notation"], "UNICODE")
        self.assertFalse(policy["scope"]["replaces_existing_json_or_binary_protocols"])
        self.assertEqual(
            policy["progress_rule"],
            "STABLE ∧ NOT_DONE ⇒ SEARCH_FOR_MISSING_TRANSITION",
        )

    def test_required_read_order_binds_standard(self):
        context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        required = context["required_read_order"]
        paths = [
            "docs/standards/QIKVRT_UNICODE_DATA_EXCHANGE_V1.md",
            "policy/QIKVRT_UNICODE_DATA_EXCHANGE_V1.json",
            "state/mesh/QIKVRT_UNICODE_DATA_EXCHANGE_ADOPTION_V1.json",
        ]
        positions = [required.index(path) for path in paths]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(context["unicode_data_exchange_standard"]["required_for_conforming_nodes"])

    def test_mesh_split_acceptance_requires_standard(self):
        mesh = json.loads(MESH.read_text(encoding="utf-8"))
        self.assertTrue(mesh["data_exchange_standard"]["required_for_node_acceptance"])
        order = mesh["mesh_node_split_acceptance"]["connection_order"]
        self.assertIn("DATA_EXCHANGE_STANDARD_BOUND", order)
        self.assertLess(
            order.index("DATA_EXCHANGE_STANDARD_BOUND"),
            order.index("SEED_QUEUE_ACCEPTANCE"),
        )

    def test_effect_boundaries_are_preserved(self):
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("TRANSPORT_ACK ≠ EFFECT_ACK", text)
        self.assertIn("EXECUTE ≠ DONE", text)
        self.assertIn("OBSERVE ≠ DONE", text)
        self.assertIn("EFFECT_ACK_DONE", text)


if __name__ == "__main__":
    unittest.main()
