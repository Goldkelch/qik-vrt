# SPDX-License-Identifier: CC-BY-NC-ND-4.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
AI_PATH = ROOT / "AI"
CONTEXT_PATH = ROOT / "AI_CONTEXT.json"
CONTRACT_PATH = ROOT / "docs/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION.md"
POLICY_PATH = ROOT / "policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json"


def load_json(path: pathlib.Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return value


class PersonalWorkingMemoryOriginAndAttributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ai = AI_PATH.read_text(encoding="utf-8")
        cls.context = load_json(CONTEXT_PATH)
        cls.contract = CONTRACT_PATH.read_text(encoding="utf-8")
        cls.policy = load_json(POLICY_PATH)

    def test_exactly_three_ordered_questions_and_no_fourth_question(self) -> None:
        questions = self.policy["questions"]
        self.assertIsInstance(questions, list)
        self.assertEqual(self.policy["max_human_questions"], 3)
        self.assertEqual(self.policy["fourth_question"], "FORBIDDEN")
        self.assertEqual(len(questions), 3)
        self.assertEqual(
            [question["id"] for question in questions],
            [
                "QUESTION_1_HUMAN_ATTRIBUTION_ID",
                "QUESTION_2_PERSONAL_ORIGIN",
                "QUESTION_3_EVIDENCE_RETENTION",
            ],
        )
        self.assertEqual([question["order"] for question in questions], [1, 2, 3])
        self.assertTrue(all(question["ask_only_if_missing"] is True for question in questions))
        self.assertTrue(all(question["prompt_de"].endswith("?") for question in questions))
        self.assertEqual(self.contract.count("?"), 3)
        self.assertNotIn("QUESTION_4", self.contract)
        self.assertNotIn("QUESTION_4", json.dumps(self.policy, ensure_ascii=False))

    def test_canonical_ai_entrypoint_and_required_read_order_bind_contract(self) -> None:
        human_contract = self.policy["human_contract"]
        machine_policy = "policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json"
        self.assertIn(human_contract, self.ai)
        self.assertIn(machine_policy, self.ai)
        read_order = self.context["required_read_order"]
        self.assertIn(human_contract, read_order)
        self.assertIn(machine_policy, read_order)
        working_memory = self.context["personal_working_memory_origin"]
        self.assertEqual(working_memory["maximum_human_questions"], 3)
        self.assertEqual(working_memory["fourth_question"], "FORBIDDEN")

    def test_personal_origin_and_canonical_upstream_are_not_conflated(self) -> None:
        memory = self.policy["personal_working_memory"]
        upstream = memory["canonical_source_remote"]
        origin = memory["personal_remote"]
        self.assertEqual(upstream["name"], "upstream")
        self.assertEqual(upstream["url"], "https://github.com/Goldkelch/qik-vrt.git")
        self.assertEqual(origin["name"], "origin")
        self.assertEqual(origin["selected_by"], "QUESTION_2_PERSONAL_ORIGIN")
        self.assertFalse(origin["canonicality_inferred"])
        self.assertFalse(memory["modes"]["LOCAL_ONLY"]["network_effect"])
        self.assertTrue(memory["modes"]["PRIVATE_ORIGIN"]["explicit_authorization_required"])
        self.assertTrue(memory["modes"]["PUBLIC_ORIGIN"]["explicit_authorization_required"])
        self.assertEqual(
            memory["external_effects_environment_default"],
            "QIKVRT_EXTERNAL_EFFECTS=disabled",
        )

    def test_artificial_cognitive_self_identification_uses_no_human_question(self) -> None:
        identity = self.policy["artificial_cognitive_self_identification"]
        self.assertFalse(identity["consumes_human_question"])
        self.assertTrue(identity["fabrication_forbidden"])
        self.assertEqual(identity["unknown_value"], "UNAVAILABLE")
        self.assertIn("model_or_build", identity["required_fields"])
        self.assertIn("identity_and_observation_limits", identity["required_fields"])

    def test_human_and_artificial_contributions_remain_separable(self) -> None:
        provenance = self.policy["contribution_provenance"]
        self.assertEqual(
            provenance["actor_classes"],
            [
                "HUMAN",
                "ARTIFICIAL_COGNITIVE_SYSTEM",
                "JOINT_WITH_SEPARABLE_COMPONENTS",
                "UNRESOLVED",
            ],
        )
        self.assertFalse(
            provenance["unresolved_may_be_reclassified_as_human_without_evidence"]
        )
        self.assertFalse(provenance["human_acceptance_changes_origin_classification"])
        self.assertFalse(provenance["git_trailers_replace_work_unit_record"])
        self.assertFalse(
            provenance["platform_identity_proves_natural_person_or_model_identity"]
        )
        required = set(provenance["required_fields"])
        self.assertTrue(
            {
                "human_actor",
                "artificial_cognitive_actor",
                "human_contributions",
                "artificial_cognitive_contributions",
                "git_history",
                "verification",
                "human_decision",
            }.issubset(required)
        )

    def test_missing_answers_and_external_effects_fail_closed(self) -> None:
        missing = self.policy["missing_or_ambiguous_answer"]
        self.assertEqual(missing["state"], "HOLD")
        self.assertFalse(missing["commit_allowed"])
        self.assertFalse(missing["remote_creation_allowed"])
        self.assertFalse(missing["push_allowed"])
        self.assertFalse(missing["additional_human_question_allowed"])
        effects = self.policy["effect_boundary"]
        self.assertEqual(effects["fork_or_repository_creation"], "SEPARATELY_AUTHORIZED_EXTERNAL_EFFECT")
        self.assertEqual(effects["push"], "SEPARATELY_AUTHORIZED_EXTERNAL_EFFECT")
        self.assertEqual(effects["release_deployment_zenodo_ietf"], "NOT_AUTHORIZED_BY_THIS_POLICY")

    def test_data_minimization_and_legal_boundary_are_not_overclaimed(self) -> None:
        minimization = self.policy["data_minimization"]
        self.assertEqual(minimization["default_retention"], "METADATA_ONLY")
        self.assertFalse(minimization["raw_transcript_required"])
        self.assertFalse(minimization["secrets_in_repository"])
        legal = self.policy["legal_boundary"]
        self.assertEqual(legal["article_50_transparency_application_date"], "2026-08-02")
        self.assertTrue(legal["role_risk_and_context_specific_analysis_required"])
        self.assertFalse(legal["universal_git_requirement_inferred"])
        self.assertFalse(legal["universal_per_change_human_ai_labelling_requirement_inferred"])
        self.assertFalse(legal["legal_compliance_inferred"])
        self.assertFalse(legal["legal_advice"])

    def test_completion_claims_remain_false(self) -> None:
        self.assertEqual(
            self.policy["release_claims"],
            {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
