import hashlib
import json
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
FREEZE = ROOT / "state/work_units/ROUND_TRIP_FINAL_BYTE_FREEZE_V1.json"


class RoundTripFinalByteFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(FREEZE.read_text(encoding="utf-8"))

    def test_primary_publication_scope_is_exact_and_closed(self):
        files = self.data["primary_publication_files"]
        self.assertEqual(
            [item["path"] for item in files],
            [
                "docs/publications/2026-08-07-universum-als-round-trip/DAS_UNIVERSUM_ALS_ROUND_TRIP_DE.md",
                "docs/publications/2026-08-07-universum-als-round-trip/ROUND_TRIP_PROMOTED_FORMAL_RESULTS_V1.md",
            ],
        )

    def test_primary_bytes_match_sha256_and_git_blob(self):
        for item in self.data["primary_publication_files"]:
            path = ROOT / item["path"]
            raw = path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
            blob = subprocess.check_output(
                ["git", "-C", str(ROOT), "hash-object", item["path"]], text=True
            ).strip()
            self.assertEqual(blob, item["git_blob_sha1"])

    def test_evidence_bindings_match_current_bytes(self):
        bindings = self.data["evidence_bindings"]
        for name in ["publication_requirement", "corpus_temporal_precedence_receipt"]:
            item = bindings[name]
            path = ROOT / item["path"]
            raw = path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
            blob = subprocess.check_output(
                ["git", "-C", str(ROOT), "hash-object", item["path"]], text=True
            ).strip()
            self.assertEqual(blob, item["git_blob_sha1"])

        item = bindings["promoted_formal_results_work_unit"]
        blob = subprocess.check_output(
            ["git", "-C", str(ROOT), "hash-object", item["path"]], text=True
        ).strip()
        self.assertEqual(blob, item["git_blob_sha1"])

    def test_corpus_projection_is_temporally_resolved_not_rewritten(self):
        status = self.data["corpus_status"]
        self.assertTrue(status["historical_correction_requirements_preserved"])
        self.assertEqual(status["historical_correction_requirement_count"], 6)
        self.assertEqual(status["current_unresolved_correction_subject_ids"], [])

    def test_scientific_boundary_remains_fail_closed(self):
        boundary = self.data["scientific_boundary"]
        self.assertTrue(boundary["formal_establishment_is_model_relative"])
        self.assertEqual(boundary["physical_correspondence"], "NOT_ESTABLISHED")
        self.assertEqual(boundary["empirical_confirmation"], "NOT_INFERRED")
        self.assertEqual(boundary["independent_validation"], "NOT_INFERRED")
        self.assertFalse(boundary["physical_c_value_empirically_bound"])
        self.assertFalse(boundary["scientific_consensus"])

    def test_external_effects_and_completion_remain_false(self):
        state = self.data["publication_state"]
        self.assertTrue(state["primary_publication_bytes_frozen"])
        self.assertFalse(state["zenodo_upload_bundle_frozen"])
        self.assertFalse(state["pre_effect_return_receipt_materialized"])
        self.assertFalse(state["exact_artifact_zenodo_authorization_established"])
        self.assertFalse(state["zenodo_effect_executed"])
        self.assertEqual(set(self.data["external_effects"].values()), {"NONE"})
        self.assertEqual(
            self.data["completion_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )


if __name__ == "__main__":
    unittest.main()
