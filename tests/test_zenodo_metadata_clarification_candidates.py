#!/usr/bin/env python3
"""Static safety checks for the historical and successor metadata preparations."""

from __future__ import annotations

import hashlib
import json
import pathlib
import unittest

from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_metadata_edit as edit


ROOT = pathlib.Path(__file__).resolve().parents[1]
V1 = ROOT / "release/round-trip-canonical-publication-zenodo-metadata-clarification-v1"
V2 = ROOT / "release/round-trip-canonical-publication-zenodo-metadata-clarification-v2"
TITLE = "Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP"


class ZenodoMetadataClarificationCandidateTests(unittest.TestCase):
    def test_historical_v1_preparation_is_preserved_and_nonexecutable(self) -> None:
        after = V1 / "ZENODO_METADATA_AFTER.json"
        request = json.loads((V1 / "METADATA_CORRECTION_REQUEST.json").read_text(encoding="utf-8"))
        metadata = json.loads(after.read_text(encoding="utf-8"))
        self.assertEqual(request["state"], "PREPARED_NOT_AUTHORIZED")
        self.assertTrue(metadata["prereserve_doi"])
        self.assertEqual(
            hashlib.sha256(after.read_bytes()).hexdigest(),
            "b996dbb350dd0bd3461573b7ce0f6e04e1c24fb6df7f665754f8d76c4403c1cf",
        )

    def test_v2_draft_is_nonexecutable_and_removes_reserved_doi(self) -> None:
        status = json.loads((V2 / "PREPARATION_STATUS.json").read_text(encoding="utf-8"))
        metadata = json.loads((V2 / "METADATA_AFTER_DRAFT.json").read_text(encoding="utf-8"))
        self.assertEqual(
            status["state"],
            "PREPARATION_NOT_EXECUTABLE_PENDING_FRESH_PUBLIC_BASELINE",
        )
        self.assertFalse(status["draft_metadata"]["execution_candidate"])
        self.assertNotIn("prereserve_doi", metadata)
        self.assertEqual(metadata["title"], TITLE)
        self.assertEqual(metadata["upload_type"], "publication")
        self.assertEqual(metadata["publication_type"], "workingpaper")
        self.assertEqual(
            edit._validate_edit_metadata(metadata, "v2 metadata after draft"),
            metadata,
        )

    def test_v2_contains_search_terms_without_promoting_claim_status(self) -> None:
        metadata = json.loads((V2 / "METADATA_AFTER_DRAFT.json").read_text(encoding="utf-8"))
        status = json.loads((V2 / "PREPARATION_STATUS.json").read_text(encoding="utf-8"))
        keywords = set(metadata["keywords"])
        self.assertTrue(
            {
                "Retrokausalität",
                "observer-relative retrocausality",
                "Eigenzeit",
                "verteilte Systeme",
                "Delayed-Choice-Experiment",
                "Quantenradierer",
                "temporal provenance",
            }.issubset(keywords)
        )
        self.assertFalse(status["release_claims"]["PASS"])
        self.assertFalse(status["release_claims"]["EFFECT_ACK_DONE"])

    def test_v2_scaffolds_require_a_fresh_public_baseline(self) -> None:
        capture = json.loads(
            (V2 / "FRESH_PUBLIC_RECORD_CAPTURE_TEMPLATE.json").read_text(encoding="utf-8")
        )
        normalization = json.loads(
            (V2 / "METADATA_BEFORE_NORMALIZATION_TEMPLATE.json").read_text(encoding="utf-8")
        )
        inventory = json.loads(
            (V2 / "IMMUTABLE_FILE_INVENTORY_TEMPLATE.json").read_text(encoding="utf-8")
        )
        local = json.loads((V2 / "LOCAL_PREPARATION_MANIFEST.json").read_text(encoding="utf-8"))

        for value in (capture, normalization, inventory):
            self.assertEqual(value["state"], "TEMPLATE_NOT_EVIDENCE_NOT_EXECUTABLE")
        self.assertIsNone(capture["fresh_capture_required"]["capture"]["response_etag"])
        self.assertIsNone(capture["fresh_capture_required"]["capture"]["record_revision"])
        self.assertIsNone(normalization["future_materialization"]["sha256"])
        self.assertEqual(normalization["normalization_rules"]["forbidden_key_action"], "BLOCK_DO_NOT_SILENTLY_REMOVE_OR_REWRITE")
        self.assertIn("prereserve_doi", normalization["normalization_rules"]["forbidden_keys"])
        self.assertEqual(inventory["fresh_inventory_required"]["future_materialization"]["entries"], [])
        self.assertEqual(inventory["historical_cross_check_not_usable_for_execution"]["file_count"], 54)
        self.assertEqual(local["state"], "PREPARATION_NOT_EXECUTABLE_PENDING_FRESH_PUBLIC_BASELINE")
        self.assertIsNone(local["materialized_execution_inputs"]["metadata_before"])
        self.assertEqual(local["external_effects"]["zenodo_metadata_edit"], "NOT_EXECUTED")

    def test_v2_proof_scaffold_does_not_claim_a_receipt_or_authorization(self) -> None:
        scaffold = json.loads(
            (V2 / "PROOF_RETURN_AND_AUTHORIZATION_SCAFFOLD.json").read_text(encoding="utf-8")
        )
        self.assertEqual(scaffold["state"], "TEMPLATE_NOT_EVIDENCE_NOT_EXECUTABLE")
        self.assertEqual(scaffold["dependencies"][1]["required_schema"], "qikvrt_prepublication_return_receipt_v2")
        self.assertTrue(scaffold["dependencies"][1]["owner_return_required_before_next_step"])
        self.assertEqual(scaffold["explicit_absences"]["owner_authorization"], "NOT_MATERIALIZED")
        self.assertFalse(scaffold["release_claims"]["PASS"])
        self.assertFalse(scaffold["release_claims"]["EFFECT_ACK_DONE"])

    def test_execution_manifest_template_is_rejected_fail_closed(self) -> None:
        template_path = V2 / "METADATA_EDIT_EXECUTION_MANIFEST_TEMPLATE.json"
        with self.assertRaisesRegex(zenodo.ZenodoError, "invalid metadata-edit manifest keys"):
            edit.load_manifest(template_path, ROOT)

    def test_v2_preparation_checksum_manifest_is_exact(self) -> None:
        sums_path = V2 / "SHA256SUMS"
        checked: set[pathlib.Path] = set()
        for line in sums_path.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            checked.add(path)
        expected = {path for path in V2.iterdir() if path.is_file() and path.name != "SHA256SUMS"}
        self.assertEqual(checked, expected)


if __name__ == "__main__":
    unittest.main()
