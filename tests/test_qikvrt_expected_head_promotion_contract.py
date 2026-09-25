# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
PROMOTION_WORKFLOW = ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml"
SELF_HEAL_WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_self_heal.yml"
FULL_AUTOMATION_CANDIDATE_WORKFLOW = ROOT / ".github/workflows/qikvrt_full_automation_candidate.yml"
MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"


class ExpectedHeadPromotionContractTests(unittest.TestCase):
    def test_contract_binds_two_phase_executor(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        executor = contract["promotion_executor"]
        self.assertEqual(
            executor["decision_path"],
            "tools/qikvrt_expected_head_promotion.py",
        )
        self.assertEqual(
            executor["workflow_path"],
            ".github/workflows/qikvrt_expected_head_promotion.yml",
        )
        self.assertEqual(executor["opt_in_marker"], MARKER)
        self.assertEqual(executor["maximum_candidates_per_run"], 1)
        self.assertEqual(executor["schedule_fallback"], "*/10 * * * *")
        self.assertEqual(
            executor["two_phase_promotion"],
            [
                "REQUEST_READY_RECLASSIFICATION_AUTHORITY",
                "STOP_AND_REOBSERVE",
                "REQUEST_EXACT_BASE_CAS_AUTHORITY",
            ],
        )
        self.assertEqual(
            executor["merge_binding"],
            "DISABLED_BECAUSE_GITHUB_PULL_MERGE_SHA_DOES_NOT_BIND_REOBSERVED_BASE_AS_HEAD1",
        )
        self.assertFalse(executor["automatic_ready_mutation"])
        self.assertFalse(executor["automatic_merge_mutation"])
        self.assertFalse(executor["same_head_verification_proxy_is_competing_writer"])
        self.assertFalse(executor["stale_base_pull_request_is_current_competing_writer"])
        self.assertTrue(executor["current_base_overlapping_pull_request_is_competing_writer"])
        self.assertEqual(executor["external_effect"], "FORBIDDEN")

    def test_self_heal_candidates_opt_in_to_executor(self) -> None:
        workflow = SELF_HEAL_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(MARKER, workflow)
        self.assertIn("tests.test_qikvrt_expected_head_promotion", workflow)
        self.assertIn("This proposal workflow never promotes or merges", workflow)

    def test_executor_is_bounded_and_fail_closed_around_exact_head_merge(self) -> None:
        workflow = PROMOTION_WORKFLOW.read_text(encoding="utf-8")
        decision = pathlib.Path(
            ROOT / "tools/qikvrt_expected_head_promotion.py"
        ).read_text(encoding="utf-8")
        self.assertIn('cron: "*/10 * * * *"', workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("READY_RECLASSIFICATION_CAS_UNAVAILABLE", decision)
        self.assertIn("HEAD1_BASE_CAS_UNAVAILABLE", decision)
        self.assertIn("EXECUTE_EXACT_HEAD_MERGE", decision)
        self.assertIn("require_unchanged_promotion_marker", workflow)
        self.assertIn('-f sha="$EXPECTED_HEAD"', workflow)
        self.assertIn("-f merge_method=merge", workflow)
        self.assertIn("repos/${REPOSITORY}/pulls/${PR_NUMBER}/merge", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("statuses: write", workflow)
        self.assertNotIn("gh pr ready", workflow)
        self.assertIn("qikvrt_repository_main_integration_effect_ack_v1", workflow)
        self.assertIn("REPOSITORY_MAIN_INTEGRATION", workflow)
        self.assertIn("merge_parents", workflow)
        self.assertIn("global_release_effect_ack_done", workflow)
        compact = workflow.replace(" ", "")
        self.assertIn("other.get('base',{}).get('sha')!=current_main", compact)
        self.assertIn("other.get('head',{}).get('sha')==head", compact)

    def test_full_automation_candidate_materializer_is_integrity_only(self) -> None:
        workflow = FULL_AUTOMATION_CANDIDATE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("qikvrt-full-automation:v1", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("tools/qikvrt_integrity.py generate", workflow)
        self.assertIn("make test", workflow)
        self.assertIn("INTEGRITY_TRIO_ONLY", workflow)
        self.assertIn("REPOSITORY_FILE_MANIFEST.json.sha256", workflow)
        self.assertIn("SHA256SUMS.txt", workflow)
        self.assertIn('test "$remote_head" = "$EXPECTED_HEAD"', workflow)
        self.assertIn('test "$remote_before_push" = "$source_head"', workflow)
        self.assertIn('git push origin "HEAD:$HEAD_REF"', workflow)
        self.assertIn("qikvrt_autonomous_exact_head_verify", workflow)
        self.assertIn("actions: write", workflow)
        self.assertIn("qikvrt_batch04_integrity.yml", workflow)
        self.assertIn("qikvrt_ci.yml", workflow)
        self.assertIn("qikvrt_collective_review.yml", workflow)
        self.assertIn("qikvrt_global_completion.yml", workflow)
        self.assertIn('event:"workflow_dispatch"', workflow)
        self.assertIn("FULL_AUTOMATION_INTEGRITY_SUCCESSOR", workflow)
        self.assertIn("steps.persist.outputs.successor", workflow)
        self.assertIn("REOBSERVE_DISPATCHED", workflow)
        self.assertNotIn("pulls/${PR_NUMBER}/merge", workflow)
        self.assertNotIn("main:refs/heads/main", workflow)
        self.assertIn('"external_effect":"NONE"', workflow)
        self.assertIn('"effect_ack_done":False', workflow)

    def test_external_effect_claims_remain_fail_closed(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        claims = contract["promotion_executor"]["completion_claims"]
        self.assertFalse(claims["PASS"])
        self.assertFalse(claims["FINAL_PASS"])
        self.assertFalse(claims["EFFECT_ACK_DONE"])
        self.assertFalse(claims["AUTHORITY_MIRROR_EQUALITY"])
        forbidden = set(contract["forbidden_effects"])
        self.assertIn("zenodo_mutation", forbidden)
        self.assertIn("ietf_mutation", forbidden)
        self.assertIn("credentialed_external_write", forbidden)


if __name__ == "__main__":
    unittest.main()
