from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = (
    ROOT
    / "docs/publications/2026-08-25-intelligent-terminal-self-scaling-mesh"
)
ARTICLE = PUBLICATION / "DAS_INTELLIGENTE_TERMINAL_UND_DAS_SELBSTSKALIERENDE_QIK_VRT_MESH_DE.md"
AUDIT = PUBLICATION / "PRIMARY_SOURCE_AUDIT.json"
CLAIMS = PUBLICATION / "CLAIM_MATRIX.json"
WORK_UNIT = ROOT / "state/work_units/ISSUE_888_INTELLIGENT_TERMINAL_MESH_CONCEPT_ARTICLE_V1.json"


class Issue888IntelligentTerminalMeshArticleTests(unittest.TestCase):
    def test_article_is_complete_attributed_and_issue_bound(self) -> None:
        text = ARTICLE.read_text(encoding="utf-8")
        self.assertIn("# Das intelligente Terminal und das selbstskalierende QIK-VRT Mesh", text)
        self.assertIn("Ingolf Lohmann – konzeptioneller Urheber und Product Owner", text)
        self.assertIn("Ausarbeitung: OpenAI Codex (GPT-5)", text)
        self.assertIn("Issue #888", text)
        self.assertEqual(len(re.findall(r"^## (?:[1-9]|1[0-4])\.", text, re.MULTILINE)), 14)
        self.assertNotIn("\ufffc", text)
        self.assertNotIn("⁠￼", text)

    def test_primary_sources_are_explicit_and_current_status_is_not_overstated(self) -> None:
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        source_ids = {item["id"] for item in audit["sources"]}
        self.assertEqual(
            source_ids,
            {
                "RFC1034",
                "RFC1035",
                "RFC5321",
                "SQL92",
                "WEBDRIVER",
                "KIM2000",
                "JACQUES2007",
                "MA2012",
                "MA2013",
            },
        )
        sql92 = next(item for item in audit["sources"] if item["id"] == "SQL92")
        webdriver = next(item for item in audit["sources"] if item["id"] == "WEBDRIVER")
        self.assertEqual(sql92["current_status"], "WITHDRAWN")
        self.assertEqual(
            sql92["article_usage"],
            "HISTORICAL_COMPATIBILITY_PROFILE_NOT_CURRENT_NORM",
        )
        self.assertEqual(webdriver["publication_status"], "WORKING_DRAFT")
        self.assertEqual(webdriver["publication_date"], "2026-07-02")

    def test_quantum_interpretation_and_channel_boundaries_fail_closed(self) -> None:
        audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        boundaries = audit["audit_boundaries"]
        self.assertTrue(boundaries["experimental_quantum_phenomenon_core_observed"])
        self.assertTrue(boundaries["compatible_with_retrocausal_interpretation"])
        self.assertFalse(boundaries["ontic_backward_causation_uniquely_proved"])
        self.assertFalse(
            boundaries[
                "locally_readable_controllable_future_to_past_channel_established"
            ]
        )
        self.assertTrue(boundaries["virtual_reverse_replay_implementable"])
        self.assertFalse(
            boundaries["virtual_reverse_replay_is_physical_retrocausality"]
        )

    def test_claim_matrix_separates_concept_implementation_and_effect(self) -> None:
        matrix = json.loads(CLAIMS.read_text(encoding="utf-8"))
        claims = matrix["claims"]
        self.assertTrue(claims["intelligent_terminal_architecture_specified"])
        self.assertTrue(claims["bounded_one_terminal_zero_to_eight_workers_specified"])
        for key in (
            "full_issue_888_implementation_on_authority_main",
            "public_dns_authority",
            "public_smtp_delivery",
            "general_internet_reachability",
            "firefox_inside_m68000_guest",
            "physical_megast_execution",
            "authority_mirror_synchronization",
            "independent_approval",
            "deployment",
            "external_publication",
            "doi_assigned",
            "arxiv_identifier_assigned",
            "pass",
            "final_pass",
            "general_effect_ack_done",
            "controllable_physical_backward_channel",
        ):
            self.assertFalse(claims[key], key)
        distinctions = set(matrix["required_distinctions"])
        self.assertIn("CONCEPT_ARTICLE != IMPLEMENTATION_COMPLETE", distinctions)
        self.assertIn("TRANSPORT_ACK != EFFECT_ACK", distinctions)
        self.assertIn(
            "VIRTUAL_REVERSE_REPLAY != PHYSICAL_BACKWARD_SIGNAL",
            distinctions,
        )

    def test_work_unit_is_current_main_bound_and_not_issue_completion(self) -> None:
        work = json.loads(WORK_UNIT.read_text(encoding="utf-8"))
        self.assertEqual(work["issue"], 888)
        self.assertEqual(
            work["authority_base_head"],
            "fb744e5b5925d61c6b473e27aab3606f237f7e6d",
        )
        self.assertEqual(
            work["authority_base_tree"],
            "3642fcb3601a62bd478326faa01bc5ce9b083d0a",
        )
        self.assertEqual(
            work["article_role"],
            "CONCEPTUAL_COMPANION_NOT_IMPLEMENTATION_CARRIER",
        )
        self.assertFalse(work["issue_completion_effect"])
        self.assertFalse(work["authority_effect"])
        self.assertFalse(work["publication_effect"])
        self.assertEqual(
            work["next_action"],
            "RUN_FRESH_EXACT_HEAD_REPOSITORY_GATES_THEN_REVIEW_AS_DOCUMENTATION_CANDIDATE",
        )


if __name__ == "__main__":
    unittest.main()
