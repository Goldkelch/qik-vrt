from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "SYNCHRONOUS_REPOSITORY_FIRST_TERMINAL_V1.json"
DOC = ROOT / "docs" / "SYNCHRONOUS_REPOSITORY_FIRST_TERMINAL.md"
CONTEXT = ROOT / "AI_CONTEXT.json"
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_synchronous_repository_first_terminal.yml"

CANONICAL = "INPUT -> QIK-VRT MESH REPOSITORY -> REPOSITORY OUTPUT / EVIDENCE -> OUTPUT"


class SynchronousRepositoryFirstTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.doc = DOC.read_text(encoding="utf-8")
        self.context = json.loads(CONTEXT.read_text(encoding="utf-8"))
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_canonical_pipeline_is_exact_and_synchronous(self) -> None:
        self.assertEqual(self.policy["canonical_statement"], CANONICAL)
        self.assertEqual(
            self.policy["contract"]["pipeline"],
            ["INPUT", "QIK_VRT_MESH_REPOSITORY", "REPOSITORY_OUTPUT_OR_EVIDENCE", "OUTPUT"],
        )
        self.assertTrue(self.policy["contract"]["synchronous"])
        self.assertTrue(self.policy["contract"]["repository_first"])
        self.assertTrue(self.policy["contract"]["repository_output_required_before_terminal_reflection"])

    def test_terminal_has_no_independent_semantic_authority(self) -> None:
        contract = self.policy["contract"]
        for key in (
            "terminal_is_independent_semantic_authority",
            "terminal_may_substitute_independent_interpretation",
            "terminal_may_substitute_independent_plan",
            "terminal_may_substitute_independent_prediction",
            "terminal_may_delay_delivery_via_scheduler",
            "terminal_may_create_background_watch_without_explicit_request",
        ):
            self.assertFalse(contract[key], key)

    def test_change_requires_explicit_successor_and_preserves_history(self) -> None:
        immutable = self.policy["immutability"]
        self.assertTrue(immutable["in_place_semantic_weakening_forbidden"])
        self.assertTrue(immutable["silent_override_forbidden"])
        self.assertTrue(immutable["successor_required_for_semantic_change"])
        self.assertTrue(immutable["successor_requires_explicit_product_owner_authorization"])
        self.assertTrue(immutable["successor_must_preserve_or_strengthen_fail_closed_boundaries"])
        self.assertTrue(immutable["history_rewrite_forbidden"])
        self.assertTrue(immutable["force_push_forbidden"])

    def test_fail_closed_without_repository_output(self) -> None:
        closed = self.policy["fail_closed"]
        self.assertEqual(closed["repository_output_absent"], "HOLD_NO_OUTPUT")
        self.assertEqual(closed["repository_processing_ambiguous"], "HOLD_AMBIGUOUS")
        self.assertEqual(closed["repository_authority_absent"], "HOLD_AUTHORITY")
        self.assertEqual(closed["stale_evidence"], "REOBSERVE")
        for key in (
            "invented_pass_forbidden",
            "invented_final_pass_forbidden",
            "invented_effect_ack_done_forbidden",
            "invented_external_effect_forbidden",
            "invented_review_authority_forbidden",
        ):
            self.assertTrue(closed[key], key)

    def test_context_binds_policy_and_doc(self) -> None:
        binding = self.context["synchronous_repository_first_terminal"]
        self.assertEqual(binding["policy"], "policy/SYNCHRONOUS_REPOSITORY_FIRST_TERMINAL_V1.json")
        self.assertEqual(binding["human_contract"], "docs/SYNCHRONOUS_REPOSITORY_FIRST_TERMINAL.md")
        self.assertEqual(binding["canonical_statement"], CANONICAL)
        self.assertTrue(binding["synchronous"])
        self.assertFalse(binding["delayed_automation_without_explicit_request"])

    def test_workflow_is_read_only_and_runs_this_contract_test(self) -> None:
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertIn("python3 -B -m unittest -v tests.test_synchronous_repository_first_terminal", self.workflow)

    def test_root_ai_is_not_modified_by_this_contract(self) -> None:
        self.assertIn("The root `/AI` entrypoint remains unchanged.", self.doc)


if __name__ == "__main__":
    unittest.main()
