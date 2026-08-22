# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_owner_origin_access_audit",
    ROOT / "tools/qikvrt_owner_origin_access_audit.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def artifact_manifest() -> dict[str, object]:
    return {
        "schema": MODULE.ARTIFACT_SCHEMA,
        "artifact_id": "artifact-example-v1",
        "work_unit_id": "work-unit-example-v1",
        "origin_principal": "Ingolf Lohmann",
        "authority_repository": "Goldkelch/qik-vrt",
        "repository_role": "AUTHORITY",
        "canonical_authority_claimed": True,
        "source_sha256": "1" * 64,
        "output_sha256": "2" * 64,
        "open_representation": {
            "format": "UTF-8 Markdown",
            "stable_locator": "docs/example.md",
            "owner_openable": True,
            "exportable": True,
            "reconstructable": True,
            "decoder_documented": True,
        },
        "access_paths": [
            {
                "locator": "docs/example.md",
                "owner_accessible": True,
                "expiring": False,
            }
        ],
        "provenance": {
            "human_origin_principal": "Ingolf Lohmann",
            "tool_contributions": ["FORMALIZE", "VERIFY"],
            "human_and_tool_contributions_separable": True,
        },
        "license": {
            "id": "CC-BY-NC-ND-4.0",
            "source": "policy/OWNER_ORIGIN_ACCESS_AUDIT_AND_ENFORCEMENT_V1.json",
            "legal_compliance_inferred": False,
        },
    }


def license_evidence(status: str) -> dict[str, object]:
    return {
        "schema": MODULE.EVIDENCE_SCHEMA,
        "artifact_bytes_verified": True,
        "provenance_verified": True,
        "license_text_bound": True,
        "authorization_status": status,
        "actor_identity_verified": False,
        "conduct_verified": False,
        "jurisdiction_bound": False,
        "exact_license_version_bound": False,
        "authorization_status_evidenced": False,
    }


class OwnerOriginAccessAuditTests(unittest.TestCase):
    def test_policy_binds_origin_rights_layers_and_role_local_hierarchy(self) -> None:
        result = MODULE.validate_policy(MODULE.load_json(MODULE.policy_path()))
        self.assertEqual(result["origin_principal"], "Ingolf Lohmann")
        self.assertEqual(result["owner_access_invariant"], "BOUND")
        self.assertEqual(result["role_local_hierarchy"], "BOUND")
        self.assertFalse(result["automated_external_legal_action"])

    def test_owner_accessible_durable_open_representation_is_accepted(self) -> None:
        result = MODULE.validate_artifact_manifest(artifact_manifest())
        self.assertEqual(result["access_state"], "OWNER_ACCESS_CONTRACT_SATISFIED")
        self.assertFalse(result["legal_violation_asserted"])
        self.assertFalse(result["external_effect"])

    def test_ephemeral_or_unopenable_only_access_fails_closed(self) -> None:
        manifest = artifact_manifest()
        manifest["access_paths"] = [
            {"locator": "temporary://artifact", "owner_accessible": True, "expiring": True}
        ]
        with self.assertRaisesRegex(MODULE.AuditError, "only expiring"):
            MODULE.validate_artifact_manifest(manifest)
        manifest = artifact_manifest()
        manifest["open_representation"]["owner_openable"] = False
        with self.assertRaisesRegex(MODULE.AuditError, "owner_openable"):
            MODULE.validate_artifact_manifest(manifest)

    def test_mirror_cannot_claim_canonical_authority(self) -> None:
        manifest = artifact_manifest()
        manifest["repository_role"] = "MIRROR"
        manifest["canonical_authority_claimed"] = True
        with self.assertRaisesRegex(MODULE.AuditError, "Mirror"):
            MODULE.validate_artifact_manifest(manifest)
        manifest["canonical_authority_claimed"] = False
        result = MODULE.validate_artifact_manifest(manifest)
        self.assertEqual(result["repository_role"], "MIRROR")

    def test_unknown_or_incomplete_license_evidence_never_becomes_accusation(self) -> None:
        result = MODULE.classify_license_evidence(license_evidence("UNKNOWN"))
        self.assertEqual(result["state"], "POTENTIAL_VIOLATION_UNVERIFIED")
        for key in (
            "legal_violation_asserted",
            "public_accusation_permitted",
            "external_notice_permitted",
            "damages_claim_permitted",
            "court_or_regulatory_filing_permitted",
            "external_effect",
        ):
            self.assertFalse(result[key])

    def test_even_exact_internal_candidate_requires_owner_or_counsel_decision(self) -> None:
        evidence = license_evidence("NOT_AUTHORIZED")
        for key in (
            "actor_identity_verified",
            "conduct_verified",
            "jurisdiction_bound",
            "exact_license_version_bound",
            "authorization_status_evidenced",
        ):
            evidence[key] = True
        result = MODULE.classify_license_evidence(evidence)
        self.assertEqual(result["state"], "EVIDENCED_BREACH_CANDIDATE_INTERNAL_ONLY")
        self.assertTrue(result["owner_or_authorized_counsel_decision_required"])
        self.assertFalse(result["legal_violation_asserted"])
        self.assertFalse(result["external_notice_permitted"])

    def test_47_languages_do_not_create_47_legal_jurisdictions(self) -> None:
        policy = MODULE.load_json(MODULE.policy_path())
        orientation = policy["normative_orientation"]
        self.assertEqual(orientation["owner_declared_natural_language_count"], 47)
        self.assertFalse(orientation["natural_language_support_verified_by_this_policy"])
        self.assertFalse(orientation["translation_creates_jurisdictional_legal_effect"])
        self.assertFalse(orientation["translation_eliminates_legal_defences"])

    def test_audio_sources_are_hash_bound_without_raw_audio_or_verbatim_transcript(self) -> None:
        result = MODULE.validate_work_unit(MODULE.load_json(MODULE.work_unit_path()))
        self.assertEqual(result["source_count"], 2)
        self.assertTrue(result["source_hashes_bound"])
        self.assertFalse(result["raw_audio_committed"])
        self.assertFalse(result["verbatim_transcript_published"])
        self.assertFalse(result["external_effect"])

    def test_cli_self_check_is_deterministic_and_false_completion_free(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(ROOT / "tools/qikvrt_owner_origin_access_audit.py"), "--self-check"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        value = json.loads(completed.stdout)
        self.assertFalse(value["pass"])
        self.assertFalse(value["final_pass"])
        self.assertFalse(value["effect_ack_done"])


if __name__ == "__main__":
    unittest.main()
