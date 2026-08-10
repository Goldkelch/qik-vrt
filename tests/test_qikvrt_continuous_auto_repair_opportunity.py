# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "state/autonomy/CONTINUOUS_AUTO_REPAIR_OPPORTUNITY_CONTRACT_V1.json"
)
SELF_HEAL_WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_self_heal.yml"
VERIFICATION_WORKFLOW = (
    ROOT / ".github/workflows/qikvrt_continuous_auto_repair_opportunity.yml"
)


class ContinuousAutoRepairOpportunityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.workflow = SELF_HEAL_WORKFLOW.read_text(encoding="utf-8")
        self.verification = VERIFICATION_WORKFLOW.read_text(encoding="utf-8")

    def test_extension_preserves_base_contract_and_every_instance_scope(self) -> None:
        base_path = ROOT / self.contract["extends"]
        self.assertTrue(base_path.is_file())
        self.assertEqual(
            self.contract["precedence"]["scope"],
            "WORKFLOW_TRIGGER_AND_OPPORTUNITY_ADMISSION_ONLY",
        )
        self.assertTrue(
            self.contract["precedence"]
            ["base_contract_remains_authoritative_for_repair_handlers_and_effect_boundary"]
        )
        applicability = self.contract["applicability"]
        self.assertEqual(
            applicability["repository_instances"],
            "EVERY_CONFORMING_REPOSITORY_INSTANCE",
        )
        self.assertEqual(
            applicability["authority_mirror_order"],
            "AUTHORITY_THEN_MIRROR",
        )
        self.assertTrue(applicability["portable_paths_must_remain_byte_identical"])
        self.assertTrue(applicability["local_instance_identity_remains_distinct"])

    def test_opportunities_are_main_bound_with_a_five_minute_fallback(self) -> None:
        opportunities = self.contract["opportunities"]
        self.assertEqual(opportunities["workflow_run_branch"], "main")
        self.assertEqual(opportunities["schedule_fallback"], "*/5 * * * *")
        self.assertEqual(opportunities["busy_polling"], "FORBIDDEN")
        self.assertEqual(
            opportunities["authorized_ai_boot"],
            "ONE_BOUNDED_REPAIR_PASS_AFTER_BOOT_READINESS",
        )
        self.assertIn('- cron: "*/5 * * * *"', self.workflow)
        self.assertIn("  push:\n    branches: [main]", self.workflow)
        self.assertIn("  workflow_run:", self.workflow)
        self.assertEqual(self.workflow.count("    branches: [main]"), 2)
        self.assertIn("    types: [completed]", self.workflow)
        for source in opportunities["workflow_run_sources"]:
            self.assertIn(f'      - "{source}"', self.workflow)

    def test_single_writer_coalesces_without_cancelling_active_repair(self) -> None:
        serialization = self.contract["serialization"]
        self.assertEqual(serialization["maximum_active_writers_per_repository"], 1)
        self.assertFalse(serialization["cancel_active_writer_for_new_opportunity"])
        self.assertTrue(serialization["coalesce_redundant_pending_opportunities"])
        self.assertEqual(serialization["unchanged_semantic_fingerprint"], "NOOP")
        self.assertFalse(
            serialization["closed_candidate_branch_is_reopened_automatically"]
        )
        self.assertIn(
            "group: qikvrt-autonomous-self-heal-${{ github.repository }}",
            self.workflow,
        )
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertNotIn("cancel-in-progress: true", self.workflow)

    def test_created_or_resumed_candidate_is_continuable_and_deduplicated(self) -> None:
        continuation = self.contract["candidate_continuation"]
        self.assertTrue(continuation["create_or_resume_open_draft"])
        self.assertTrue(continuation["exact_head_verification_after_create_or_resume"])
        self.assertEqual(
            continuation["duplicate_exact_head_verification_when_status_exists"],
            "FORBIDDEN",
        )
        self.assertFalse(continuation["proposal_workflow_may_merge"])
        self.assertIn(continuation["draft_opt_in_marker"], self.workflow)
        self.assertIn(continuation["expected_head_promotion_marker"], self.workflow)
        self.assertIn("qikvrt_autonomous_exact_head_verify", self.workflow)
        self.assertIn("QIKVRT autonomous exact-head verification", self.workflow)
        self.assertIn("pending|success|failure|error", self.workflow)
        self.assertIn(
            "candidate branch exists without an open PR; preserve explicit lifecycle disposition",
            self.workflow,
        )

    def test_effect_boundary_and_completion_nonclaims_are_preserved(self) -> None:
        boundary = self.contract["effect_boundary"]
        self.assertTrue(all(value == "FORBIDDEN" for value in boundary.values()))
        self.assertTrue(
            all(value is False for value in self.contract["completion_claims"].values())
        )
        self.assertNotIn("gh pr merge", self.workflow)
        self.assertNotIn("git push --force", self.workflow)
        self.assertNotIn("git push -f", self.workflow)
        self.assertIn("statuses: write", self.workflow)

    def test_contract_verification_workflow_is_exact_head_and_read_only(self) -> None:
        self.assertIn(
            "name: QIKVRT continuous auto-repair opportunity contract",
            self.verification,
        )
        self.assertIn("contents: read", self.verification)
        self.assertNotIn("contents: write", self.verification)
        self.assertNotIn("pull-requests: write", self.verification)
        self.assertIn("persist-credentials: false", self.verification)
        self.assertIn(
            "tests.test_qikvrt_continuous_auto_repair_opportunity",
            self.verification,
        )
        self.assertIn("tools/qikvrt_integrity.py verify", self.verification)
        self.assertNotIn("gh pr merge", self.verification)
        self.assertNotIn("git push", self.verification)


if __name__ == "__main__":
    unittest.main()
