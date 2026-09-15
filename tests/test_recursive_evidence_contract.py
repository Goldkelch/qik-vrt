import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "QIKVRT_UNIVERSAL_TERMINAL_RECURSIVE_EVIDENCE_INVARIANT.json"


class RecursiveEvidenceContractTest(unittest.TestCase):
    def test_autonomy_and_compatibility_are_explicit(self):
        data = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertFalse(data["stable_end_state_requires_external_cognition"])
        self.assertFalse(data["predecessor_evidence_transfer"])
        self.assertTrue(data["compatibility"]["preserve_existing_interfaces"])
        self.assertTrue(data["compatibility"]["preserve_receipt_provenance"])
        self.assertTrue(data["compatibility"]["preserve_exact_subject_semantics"])

    def test_shortcuts_cannot_delete_or_transfer_evidence(self):
        data = json.loads(CONTRACT.read_text(encoding="utf-8"))
        shortcuts = data["shortcuts"]
        self.assertTrue(shortcuts["allowed"])
        self.assertFalse(shortcuts["evidence_deletion"])
        self.assertFalse(shortcuts["predecessor_evidence_transfer"])
        self.assertTrue(shortcuts["complete_provenance_path_reconstructible"])
        self.assertTrue(shortcuts["fresh_validation_required"])

    def test_evidence_history_and_current_validity_are_distinct(self):
        data = json.loads(CONTRACT.read_text(encoding="utf-8"))
        mono = data["monotonicity"]
        self.assertEqual("append_only", mono["evidence_history"])
        self.assertEqual("non_monotonic", mono["assertion_validity"])
        self.assertEqual("requires_fresh_validation", mono["current_admissibility"])
        self.assertTrue(mono["supersession_is_evidence"])


if __name__ == "__main__":
    unittest.main()
