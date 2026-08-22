# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_owner_principal_authorship",
    ROOT / "tools/qikvrt_owner_principal_authorship.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class OwnerPrincipalAuthorshipTests(unittest.TestCase):
    def policy(self) -> dict[str, object]:
        return MODULE.load_json(MODULE.policy_path())

    def work_unit(self) -> dict[str, object]:
        return MODULE.load_json(MODULE.work_unit_path())

    def test_declares_ingolf_lohmann_as_sole_human_principal_and_author(self) -> None:
        result = MODULE.validate_policy(self.policy())
        self.assertEqual(result["declared_sole_principal"], "Ingolf Lohmann")
        self.assertEqual(result["declared_sole_human_author"], "Ingolf Lohmann")
        self.assertFalse(result["machine_systems_declared_coauthors"])

    def test_canonical_semantic_statement_is_hash_and_length_bound(self) -> None:
        declaration = self.policy()["owner_authorship_declaration"]
        raw = declaration["canonical_semantic_statement"].encode("utf-8")
        self.assertEqual(len(raw), MODULE.CANONICAL_DECLARATION_UTF8_BYTES)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), MODULE.CANONICAL_DECLARATION_SHA256)
        self.assertEqual(
            declaration["canonical_semantic_statement_sha256"],
            MODULE.CANONICAL_DECLARATION_SHA256,
        )

    def test_machine_systems_are_tools_not_coauthors(self) -> None:
        declaration = self.policy()["owner_authorship_declaration"]
        self.assertEqual(
            set(declaration["machine_tool_participants"]),
            MODULE.EXPECTED_MACHINE_TOOLS,
        )
        self.assertFalse(declaration["machine_systems_declared_coauthors"])
        self.assertFalse(declaration["chatgpt_declared_sole_or_dominant_developer"])

    def test_personal_profile_and_other_records_are_source_surfaces_not_silently_verified(self) -> None:
        declaration = self.policy()["owner_authorship_declaration"]
        self.assertEqual(set(declaration["source_surfaces"]), MODULE.EXPECTED_SOURCE_SURFACES)
        self.assertFalse(declaration["external_source_surfaces_verified_by_this_repository"])

    def test_third_party_and_platform_provenance_is_not_rewritten(self) -> None:
        declaration = self.policy()["owner_authorship_declaration"]
        self.assertFalse(declaration["third_party_authorship_or_license_rewritten"])
        self.assertFalse(declaration["platform_software_or_model_authorship_claimed"])
        self.assertFalse(declaration["statutory_copyright_for_every_artifact_adjudicated"])

    def test_owner_declaration_does_not_manufacture_scientific_or_patent_proof(self) -> None:
        declaration = self.policy()["owner_authorship_declaration"]
        self.assertFalse(
            declaration["scientific_or_physical_claims_independently_validated_by_declaration"]
        )
        self.assertFalse(declaration["novelty_or_patentability_independently_proved_by_declaration"])
        integration = self.policy()["integration_boundary"]
        self.assertFalse(integration["owner_declaration_proves_quantum_causality_as_empirical_physics"])

    def test_additive_integration_does_not_require_mastery_of_every_component_domain(self) -> None:
        integration = self.policy()["integration_boundary"]
        self.assertTrue(
            integration["human_selection_arrangement_and_integration_are_declared_creative_contributions"]
        )
        self.assertFalse(
            integration["additive_integration_requires_personal_mastery_of_every_component_domain"]
        )

    def test_owner_chat_declaration_is_semantically_bound_without_verbatim_publication(self) -> None:
        result = MODULE.validate_work_unit(self.work_unit())
        self.assertEqual(result["source_binding"], "CANONICAL_SEMANTIC_STATEMENT_HASH_BOUND")
        self.assertFalse(result["verbatim_source_committed"])
        self.assertFalse(result["external_effect"])

    def test_tamper_or_machine_coauthor_promotion_fails_closed(self) -> None:
        policy = copy.deepcopy(self.policy())
        policy["owner_authorship_declaration"]["canonical_semantic_statement"] += " altered"
        with self.assertRaisesRegex(MODULE.DeclarationError, "statement changed"):
            MODULE.validate_policy(policy)
        policy = copy.deepcopy(self.policy())
        policy["owner_authorship_declaration"]["machine_systems_declared_coauthors"] = True
        with self.assertRaisesRegex(MODULE.DeclarationError, "must remain false"):
            MODULE.validate_policy(policy)

    def test_cli_is_deterministic_and_false_completion_free(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/qikvrt_owner_principal_authorship.py"),
                "--pretty",
            ],
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
