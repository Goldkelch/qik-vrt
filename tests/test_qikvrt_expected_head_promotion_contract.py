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
        self.assertEqual(
            executor["schedule_fallback"],
            "DISABLED_NON_POLLING_EVENT_EDGES_ONLY",
        )
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

    def test_executor_is_bounded_and_fails_closed_before_merge(self) -> None:
        workflow = PROMOTION_WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("cron:", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("READY_RECLASSIFICATION_CAS_UNAVAILABLE", pathlib.Path(
            ROOT / "tools/qikvrt_expected_head_promotion.py"
        ).read_text(encoding="utf-8"))
        self.assertIn('exit 0', workflow)
        self.assertIn("require_unchanged_promotion_marker", workflow)
        self.assertIn("HEAD^1", workflow)
        self.assertNotIn('-f sha="$EXPECTED_HEAD"', workflow)
        self.assertNotIn("repos/${REPOSITORY}/pulls/${PR_NUMBER}/merge", workflow)
        self.assertNotIn("gh pr ready", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        compact = workflow.replace(" ", "")
        self.assertIn("other.get('base',{}).get('sha')!=current_main", compact)
        self.assertIn("other.get('head',{}).get('sha')==head", compact)

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
