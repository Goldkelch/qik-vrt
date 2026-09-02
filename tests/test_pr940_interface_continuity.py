# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json"
ARTICLE = ROOT / "docs/PR940_BEWEISAPPARAT_UND_SCHNITTSTELLENKONTINUITAET.md"
CONTEXT = ROOT / "AI_CONTEXT.json"
ENTRYPOINT = ROOT / "AI"


class TestPr940InterfaceContinuity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.article = ARTICLE.read_text(encoding="utf-8")
        cls.context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        cls.entrypoint = ENTRYPOINT.read_text(encoding="utf-8")

    def test_case_is_exactly_bound_and_does_not_borrow_pr922(self):
        continuity = self.policy["interaction_continuity"]
        binding = continuity["case_binding"]
        self.assertEqual(binding["pull_request"], 940)
        self.assertEqual(binding["head_sha"], "a4032924ea9116afd61332102aca3f22327a56cb")
        self.assertEqual(binding["head_tree_sha"], "f9d7db43f9eb88ea0ff565dd4ddf3e6247fea5dc")
        self.assertFalse(continuity["cross_pull_request_evidence_transfer"])
        self.assertIn("PR-922-Evidenz wird weder übernommen", self.article)

    def test_progress_and_internal_checks_do_not_end_authorized_work(self):
        continuity = self.policy["interaction_continuity"]
        self.assertFalse(continuity["progress_update_ends_work_ring"])
        self.assertFalse(continuity["successful_internal_check_ends_work_ring"])
        self.assertIn(
            "EXECUTE_WHILE_THAT_ACTION_IS_SAFE_DETERMINISTIC_AND_ALREADY_AUTHORIZED",
            continuity["required_client_behavior"],
        )
        self.assertIn("While one safe, deterministic and already authorized next action", self.entrypoint)

    def test_return_boundary_is_fail_closed(self):
        continuity = self.policy["interaction_continuity"]
        self.assertEqual(
            set(continuity["return_allowed_only_at"]),
            {
                "REQUESTED_SCOPE_VERIFIABLY_COMPLETE",
                "CONCRETE_EXTERNAL_OR_PERMISSION_BLOCK_WITH_NO_AUTHORIZED_REPAIR",
                "GENUINELY_NONDETERMINISTIC_OWNER_CHOICE_REQUIRED",
            },
        )
        self.assertFalse(continuity["approval_merge_publication_or_effect_ack_inferred"])
        adaptation = self.context["human_machine_interface_adaptation"]
        self.assertEqual(adaptation["interaction_continuity_case"], str(ARTICLE.relative_to(ROOT)))

    def test_article_preserves_epistemic_and_effect_boundaries(self):
        for phrase in (
            "Urheber- und Deutungsthese",
            "keine Zustimmung",
            "keinen Merge",
            "keine Publikation",
            "kein `FINAL_PASS`",
            "`EFFECT_ACK_DONE`",
        ):
            self.assertIn(phrase, self.article)


if __name__ == "__main__":
    unittest.main()
