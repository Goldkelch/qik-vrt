# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "AI_PERSONAL_ORIGIN_AND_CONTRIBUTION_SELF_DECLARATION_DE.md"
POLICY = ROOT / "policy" / "AI_PERSONAL_ORIGIN_AND_CONTRIBUTION_SELF_DECLARATION.json"
DISCLOSURE = ROOT / ".well-known" / "qik-vrt-self-disclosure.json"
AI_ENTRYPOINT = ROOT / "AI"


def read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class PersonalOriginAndContributionSelfDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = DOCUMENT.read_text(encoding="utf-8")
        cls.policy = read_json(POLICY)
        cls.disclosure = read_json(DISCLOSURE)
        cls.entrypoint = AI_ENTRYPOINT.read_text(encoding="utf-8")

    def test_exactly_three_human_question_groups(self) -> None:
        interaction = self.policy["interaction_contract"]
        self.assertEqual(interaction["maximum_human_questions"], 3)
        self.assertEqual(len(interaction["questions"]), 3)
        self.assertEqual(
            [question["id"] for question in interaction["questions"]],
            ["Q1", "Q2", "Q3"],
        )
        self.assertEqual(self.document.count("?"), 3)
        self.assertFalse(interaction["request_credentials_or_secrets"])

    def test_history_preserving_derived_origin_semantics(self) -> None:
        status = self.policy["system_status_boundary"]
        protocol = self.policy["origin_copy_protocol"]
        self.assertFalse(status["artificial_system_has_legal_personhood"])
        self.assertFalse(status["artificial_system_owns_target_repository"])
        self.assertTrue(
            status[
                "origin_is_operational_git_remote_not_claim_of_historical_originality"
            ]
        )
        self.assertEqual(protocol["source_repository"], "Goldkelch/qik-vrt")
        self.assertEqual(protocol["source_remote_name"], "upstream")
        self.assertEqual(protocol["personal_remote_name"], "origin")
        self.assertTrue(protocol["preserve_reachable_git_history"])
        self.assertFalse(protocol["force_push"])
        self.assertFalse(protocol["history_rewrite"])
        self.assertTrue(protocol["post_copy_reobservation_required"])

    def test_attribution_and_receipt_contract_is_fail_closed(self) -> None:
        self.assertEqual(
            self.policy["contribution_classes"],
            [
                "HUMAN_ORIGINATED",
                "AI_ORIGINATED",
                "HYBRID",
                "IMPORTED",
                "UNKNOWN",
            ],
        )
        semantics = self.policy["contribution_semantics"]
        self.assertTrue(
            semantics[
                "human_acceptance_does_not_reclassify_ai_generation_as_human_originated"
            ]
        )
        self.assertFalse(
            semantics["technical_provenance_determines_legal_authorship"]
        )
        required = set(self.policy["receipt_contract"]["required_fields"])
        self.assertTrue(
            {
                "human_contributions",
                "ai_contributions",
                "hybrid_contributions",
                "human_review",
                "base_commit",
                "base_tree",
                "receipt_sha256",
            }.issubset(required)
        )
        self.assertEqual(
            self.policy["fail_closed"]["missing_or_ambiguous_answer"],
            "BLOCK",
        )

    def test_legal_boundary_is_precise(self) -> None:
        legal = self.policy["legal_context"]
        self.assertEqual(legal["article_50_application_date"], "2026-08-02")
        self.assertTrue(legal["article_50_applies_only_within_its_scope"])
        self.assertFalse(
            legal["universal_line_level_human_ai_attribution_mandate_established"]
        )
        self.assertFalse(legal["legal_advice"])
        self.assertIn("keine allgemeine, ausnahmslose Pflicht", self.document)
        self.assertIn(
            "strengeren, technisch überprüfbaren Provenienzstandard",
            self.document,
        )

    def test_entrypoint_and_discovery_are_bound(self) -> None:
        document_path = DOCUMENT.relative_to(ROOT).as_posix()
        policy_path = POLICY.relative_to(ROOT).as_posix()
        for path in (document_path, policy_path):
            self.assertIn(path, self.entrypoint)

        capabilities = {
            entry["id"]: entry for entry in self.disclosure["capabilities"]
        }
        capability = capabilities[
            "personal_origin_copy_and_contribution_attribution"
        ]
        self.assertTrue(capability["machine_readable"])
        self.assertEqual(capability["maximum_human_questions"], 3)
        binding = self.disclosure["bindings"][
            "personal_origin_and_attribution"
        ]
        self.assertEqual(binding["human_contract"], document_path)
        self.assertEqual(binding["machine_policy"], policy_path)
        self.assertEqual(binding["source_remote_role"], "upstream")
        self.assertEqual(binding["personal_remote_role"], "origin")

    def test_no_completion_claim_is_promoted(self) -> None:
        completion = self.policy["completion_claims"]
        self.assertTrue(completion)
        self.assertTrue(all(value is False for value in completion.values()))


if __name__ == "__main__":
    unittest.main()
