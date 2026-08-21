# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_expected_head_promotion",
    ROOT / "tools/qikvrt_expected_head_promotion.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ExpectedHeadPromotionTests(unittest.TestCase):
    def code_owner_gate(self, **overrides):
        value = {
            "gate_state": "success",
            "first_blocker": None,
            "detail": "@Goldkelch approved the current head",
            "head_sha": "b" * 40,
        }
        value.update(overrides)
        return value

    def snapshot(self, **overrides):
        value = {
            "pr_number": 459,
            "current_main_sha": "a" * 40,
            "base_sha": "a" * 40,
            "expected_head_sha": "b" * 40,
            "current_head_sha": "b" * 40,
            "draft": False,
            "mergeable": True,
            "external_effect": "NONE",
            "required_gates": [
                "QIKVRT CI",
                "QIKVRT repository evidence materialization",
                "QIKVRT Collective Proposal Review",
                "QIK-VRT global claim completion",
                "QIKVRT requested review execution",
            ],
            "workflow_runs": [
                {"name": "QIKVRT CI", "status": "completed", "conclusion": "success", "run_number": 10},
                {"name": "QIKVRT repository evidence materialization", "status": "completed", "conclusion": "success", "run_number": 20},
                {"name": "QIKVRT Collective Proposal Review", "status": "completed", "conclusion": "success", "run_number": 30},
                {"name": "QIK-VRT global claim completion", "status": "completed", "conclusion": "success", "run_number": 40},
                {"name": "QIKVRT requested review execution", "status": "completed", "conclusion": "success", "run_number": 50},
                {"name": "QIKVRT conditional probe", "status": "completed", "conclusion": "skipped", "run_number": 1},
            ],
            "code_owner_review_gate": self.code_owner_gate(),
            "competing_writer_overlaps": [],
        }
        value.update(overrides)
        return value

    def test_ready_green_exact_head_is_promotable_for_merge(self):
        result = MODULE.evaluate_promotion(self.snapshot())
        self.assertEqual((result["state"], result["phase"]), ("PROMOTABLE", "MERGE"))

    def test_bot_review_success_cannot_mask_code_owner_failure(self):
        result = MODULE.evaluate_promotion(
            self.snapshot(
                code_owner_review_gate=self.code_owner_gate(
                    gate_state="failure",
                    first_blocker="CODE_OWNER_RULE_NOT_ENFORCED",
                    detail="native rule is not enforced",
                )
            )
        )
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_code_owner_gate_head_must_match(self):
        result = MODULE.evaluate_promotion(
            self.snapshot(code_owner_review_gate=self.code_owner_gate(head_sha="c" * 40))
        )
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_STALE")

    def test_draft_advances_to_ready_without_review_authority(self):
        snapshot = self.snapshot(
            draft=True,
            code_owner_review_gate=self.code_owner_gate(
                gate_state="failure",
                first_blocker="CODE_OWNER_RULE_NOT_ENFORCED",
            ),
        )
        snapshot["workflow_runs"] = [
            run for run in snapshot["workflow_runs"]
            if run["name"] != "QIKVRT requested review execution"
        ]
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual((result["state"], result["phase"]), ("PROMOTABLE", "READY_FOR_REVIEW"))

    def test_projection_only_overlap_is_not_competing_writer(self):
        result = MODULE.evaluate_promotion(
            self.snapshot(
                competing_writer_overlaps=[
                    {
                        "pr_number": 452,
                        "paths": [
                            "REPOSITORY_FILE_MANIFEST.json",
                            "REPOSITORY_FILE_MANIFEST.json.sha256",
                            "SHA256SUMS.txt",
                        ],
                    }
                ]
            )
        )
        self.assertEqual((result["state"], result["phase"]), ("PROMOTABLE", "MERGE"))

    def test_semantic_overlap_still_blocks(self):
        result = MODULE.evaluate_promotion(
            self.snapshot(
                competing_writer_overlaps=[
                    {
                        "pr_number": 452,
                        "paths": [
                            "REPOSITORY_FILE_MANIFEST.json",
                            "tools/qikvrt_expected_head_promotion.py",
                        ],
                    }
                ]
            )
        )
        self.assertEqual(result["first_blocker"], "COMPETING_WRITER_OVERLAP")
        self.assertIn("tools/qikvrt_expected_head_promotion.py", result["detail"])

    def test_old_action_required_run_is_superseded_by_newer_success(self):
        snapshot = self.snapshot()
        snapshot["workflow_runs"].extend(
            [
                {"name": "QIKVRT CI", "status": "completed", "conclusion": "action_required", "run_number": 9},
                {"name": "QIKVRT repository evidence materialization", "status": "completed", "conclusion": "action_required", "run_number": 19},
            ]
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual((result["state"], result["phase"]), ("PROMOTABLE", "MERGE"))

    def test_ready_candidate_without_bot_review_gate_blocks(self):
        snapshot = self.snapshot()
        snapshot["workflow_runs"] = [
            run for run in snapshot["workflow_runs"]
            if run["name"] != "QIKVRT requested review execution"
        ]
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_MISSING")

    def test_failed_internal_gate_blocks(self):
        snapshot = self.snapshot()
        snapshot["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "completed", "conclusion": "failure", "run_number": 11}
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_NOT_GREEN")

    def test_head_drift_blocks(self):
        result = MODULE.evaluate_promotion(self.snapshot(current_head_sha="c" * 40))
        self.assertEqual(result["first_blocker"], "HEAD_DRIFT")

    def test_base_drift_blocks(self):
        result = MODULE.evaluate_promotion(self.snapshot(current_main_sha="c" * 40))
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")

    def test_external_effect_blocks(self):
        result = MODULE.evaluate_promotion(self.snapshot(external_effect="ZENODO"))
        self.assertEqual(result["first_blocker"], "EXTERNAL_EFFECT_BOUNDARY")

    def test_non_mergeable_candidate_blocks(self):
        result = MODULE.evaluate_promotion(self.snapshot(mergeable=False))
        self.assertEqual(result["first_blocker"], "NOT_MERGEABLE")

    def test_workflow_reobserves_independent_authority_separately(self):
        workflow = (ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml").read_text(encoding="utf-8")
        self.assertIn('REVIEW_STATUS_CONTEXT: "QIKVRT requested review execution"', workflow)
        self.assertIn('"QIKVRT required code-owner review"', workflow)
        self.assertIn("evaluate_required_review", workflow)
        self.assertIn("code_owner_review_gate", workflow)
        self.assertIn("independent Code Owner gate changed", workflow)


if __name__ == "__main__":
    unittest.main()
