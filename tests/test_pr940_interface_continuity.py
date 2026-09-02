# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json"
ARTICLE = ROOT / "docs/PR940_BEWEISAPPARAT_UND_SCHNITTSTELLENKONTINUITAET.md"
CONTEXT = ROOT / "AI_CONTEXT.json"
ENTRYPOINT = ROOT / "AI"
WORK_UNIT = ROOT / "state/work_units/PR940_PROOF_APPARATUS_INTERFACE_CONTINUITY_V1.json"


class TestPr940InterfaceContinuity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.article = ARTICLE.read_text(encoding="utf-8")
        cls.context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        cls.entrypoint = ENTRYPOINT.read_text(encoding="utf-8")
        cls.work_unit = json.loads(WORK_UNIT.read_text(encoding="utf-8"))

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

    def test_software_catastrophe_and_zenodo_statements_remain_attributed_and_bound(self):
        self.assertIn("Die Softwarekatastrophe: Befund, Diagnose und Grenze", self.article)
        self.assertIn("Softwarekatastrophe, die sich künstliche", self.article)
        self.assertIn("Sie war für PR 940 nicht autorisiert.", self.article)
        self.assertIn("Softwarekatastrophe bleibt damit eine Ingolf Lohmann zugeordnete", self.article)
        self.assertIn("allgemeine Vergleichsbehauptung über die Fähigkeiten aller Menschen", self.article)

    def test_work_unit_output_bindings_match_current_article_and_test_bytes(self):
        outputs = {entry["path"]: entry for entry in self.work_unit["outputs"]}
        for path in (ARTICLE, Path(__file__)):
            relative = str(path.relative_to(ROOT))
            data = path.read_bytes()
            self.assertEqual(outputs[relative]["bytes"], len(data))
            self.assertEqual(outputs[relative]["sha256"], hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    unittest.main()
