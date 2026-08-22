from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_mesh_rights_provenance.py"
POLICY = ROOT / "policy" / "MESH_RIGHTS_PROVENANCE_AUDIT_V1.json"
AUDIO_RECEIPT = (
    ROOT
    / "evidence"
    / "audio"
    / "2026-08-22"
    / "MESH_RIGHTS_PROVENANCE_OWNER_AUDIO_V1.json"
)

SPEC = importlib.util.spec_from_file_location("qikvrt_mesh_rights_provenance", TOOL)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {TOOL}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MeshRightsProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = MODULE.load_policy(POLICY)

    def test_audio_receipt_binds_both_sources_without_raw_media_or_transcript(self) -> None:
        receipt = json.loads(AUDIO_RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["aggregate"]["files"], 2)
        self.assertEqual(receipt["aggregate"]["bytes"], 2_116_799)
        self.assertEqual(receipt["aggregate"]["duration_seconds"], "254.336000")
        self.assertEqual(
            {item["file_id"] for item in receipt["sources"]},
            {
                "file_00000000a15481f48cc247fadc5a664e",
                "file_00000000ff3081f4b76d967f8956ac61",
            },
        )
        self.assertFalse(receipt["privacy_boundary"]["raw_audio_in_repository"])
        self.assertFalse(receipt["privacy_boundary"]["verbatim_transcript_in_repository"])
        self.assertTrue(receipt["privacy_boundary"]["hashes_and_normalized_work_order_only"])

    def test_authority_exact_binding_verifies_only_technical_scope(self) -> None:
        result = MODULE.evaluate(MODULE.witness(), self.policy)
        self.assertEqual(result["decision"], "PROVENANCE_AND_NOTICE_MATCH_VERIFIED")
        self.assertEqual(result["repository_role"], "AUTHORITY")
        self.assertTrue(result["normative_authority"])
        self.assertTrue(result["technical_provenance_verified"])
        self.assertFalse(result["authorship_proven"])
        self.assertFalse(result["copying_determined"])
        self.assertFalse(result["legal_infringement_determined"])
        self.assertFalse(result["damages_determined"])
        self.assertEqual(result["external_effect"], "NONE")

    def test_mirror_exact_binding_preserves_role_without_normative_override(self) -> None:
        result = MODULE.evaluate(
            MODULE.witness("ingolf-lohmann/qik-vrt"), self.policy
        )
        self.assertEqual(result["decision"], "PROVENANCE_AND_NOTICE_MATCH_VERIFIED")
        self.assertEqual(result["repository_role"], "MIRROR")
        self.assertFalse(result["normative_authority"])
        self.assertTrue(result["technical_role_hierarchy_inferred"])
        self.assertFalse(result["human_hierarchy_inferred"])

    def test_unknown_repository_fails_closed(self) -> None:
        evidence = MODULE.witness("example/unknown")
        result = MODULE.evaluate(evidence, self.policy)
        self.assertEqual(result["decision"], "HOLD_PROVENANCE_MISMATCH")
        self.assertIn(
            "REPOSITORY_NOT_IN_BOUND_MESH_ROLE_REGISTRY", result["blockers"]
        )

    def test_artifact_digest_mismatch_fails_closed(self) -> None:
        evidence = copy.deepcopy(MODULE.witness())
        evidence["observed"]["artifact_sha256"] = "6" * 64
        result = MODULE.evaluate(evidence, self.policy)
        self.assertEqual(result["decision"], "HOLD_PROVENANCE_MISMATCH")
        self.assertIn("artifact_sha256", result["mismatches"])

    def test_missing_or_invalid_exact_binding_fails_closed(self) -> None:
        evidence = copy.deepcopy(MODULE.witness())
        evidence["observed"].pop("tree_sha")
        evidence["expected"]["path"] = "../escape"
        result = MODULE.evaluate(evidence, self.policy)
        self.assertEqual(result["decision"], "HOLD_PROVENANCE_UNVERIFIED")
        self.assertIn("observed.tree_sha", result["missing_or_invalid"])
        self.assertIn("expected.path", result["missing_or_invalid"])

    def test_ambiguous_license_notice_requires_review(self) -> None:
        evidence = copy.deepcopy(MODULE.witness())
        evidence["license"]["resolution"] = "AMBIGUOUS"
        result = MODULE.evaluate(evidence, self.policy)
        self.assertEqual(result["decision"], "HOLD_LICENSE_REVIEW")
        self.assertFalse(result["legal_infringement_determined"])

    def test_personal_data_without_all_guards_requires_review(self) -> None:
        evidence = copy.deepcopy(MODULE.witness())
        evidence["data_protection"] = {
            "personal_data_present": True,
            "lawful_basis_bound": True,
            "purpose_bound": True,
            "data_minimized": True,
            "retention_bound": True,
            "access_controlled": True,
            "data_subject_rights_path_bound": False,
        }
        result = MODULE.evaluate(evidence, self.policy)
        self.assertEqual(result["decision"], "HOLD_DATA_PROTECTION_REVIEW")
        self.assertIn(
            "MISSING_DATA_GUARD:data_subject_rights_path_bound",
            result["blockers"],
        )

    def test_automatic_legal_conclusion_is_refused(self) -> None:
        evidence = copy.deepcopy(MODULE.witness())
        evidence["claims"]["legal_infringement"] = True
        evidence["claims"]["damages"] = True
        result = MODULE.evaluate(evidence, self.policy)
        self.assertEqual(result["decision"], "HOLD_LEGAL_AUTHORITY_REQUIRED")
        self.assertIn("AUTOMATED_LEGAL_CONCLUSION_FORBIDDEN", result["blockers"])
        self.assertFalse(result["legal_infringement_determined"])
        self.assertFalse(result["damages_determined"])

    def test_effect_outside_read_only_alert_or_hold_scope_is_refused(self) -> None:
        evidence = copy.deepcopy(MODULE.witness())
        evidence["requested_effect"] = "SEND_LEGAL_DEMAND"
        result = MODULE.evaluate(evidence, self.policy)
        self.assertEqual(result["decision"], "HOLD_LEGAL_AUTHORITY_REQUIRED")
        self.assertIn("REQUESTED_EFFECT_OUTSIDE_AUTOMATED_SCOPE", result["blockers"])
        self.assertEqual(result["external_effect"], "NONE")

    def test_categorical_imperative_is_not_silently_substituted_for_law(self) -> None:
        self.assertEqual(
            self.policy["principles"]["categorical_imperative_role"],
            "OWNER_ETHICAL_HEURISTIC_NOT_LEGAL_SUBSTITUTE",
        )
        self.assertIn(
            "ETHICAL_HEURISTIC != APPLICABLE_LAW",
            self.policy["non_equivalences"],
        )

    def test_47_scope_remains_unresolved_and_not_a_jurisdiction_claim(self) -> None:
        boundary = self.policy["language_and_jurisdiction_boundary"]
        self.assertEqual(boundary["owner_spoken_number"], 47)
        self.assertEqual(boundary["status"], "UNRESOLVED_DO_NOT_NORMALIZE_SILENTLY")
        self.assertIn(
            "LANGUAGE_COUNT != COUNTRY_COUNT",
            boundary["invariants"],
        )
        self.assertIn(
            "MULTILINGUAL_PROJECTION != JURISDICTION",
            boundary["invariants"],
        )

    def test_policy_mutation_that_collapses_human_and_technical_hierarchy_fails(self) -> None:
        mutated = copy.deepcopy(self.policy)
        mutated["mesh_roles"]["authority"]["human_superiority_inferred"] = True
        with self.assertRaisesRegex(MODULE.ContractError, "human superiority"):
            MODULE.validate_policy(mutated)

    def test_cli_self_check_is_reproducible_and_claims_no_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--policy",
                    str(POLICY),
                    "--self-check",
                    "--pretty",
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            stdout_value = json.loads(completed.stdout)
            file_value = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout_value, file_value)
            self.assertFalse(file_value["pass"])
            self.assertFalse(file_value["final_pass"])
            self.assertFalse(file_value["effect_ack_done"])
            self.assertEqual(file_value["legal_effect"], "NONE")


if __name__ == "__main__":
    unittest.main()
