# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
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

REVIEW_SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_executor_for_promotion_test",
    ROOT / "tools/qikvrt_requested_review_executor.py",
)
assert REVIEW_SPEC and REVIEW_SPEC.loader
REVIEW_MODULE = importlib.util.module_from_spec(REVIEW_SPEC)
sys.modules[REVIEW_SPEC.name] = REVIEW_MODULE
REVIEW_SPEC.loader.exec_module(REVIEW_MODULE)


class ExpectedHeadPromotionTests(unittest.TestCase):
    def test_workflow_pins_the_trusted_evaluator_and_fences_live_main(self):
        workflow = (ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("ref: ${{ github.workflow_sha }}", workflow)
        self.assertNotIn("ref: main", workflow)
        self.assertIn('TRUSTED_EVALUATOR_SHA: ${{ github.workflow_sha }}', workflow)
        self.assertIn(
            'git/ref/heads/main" --jq \'.object.sha\')" = "$TRUSTED_EVALUATOR_SHA"',
            workflow,
        )

    def promotion_pr(self, **overrides):
        value = {
            "number": 459,
            "state": "open",
            "body": MODULE.PROMOTION_MARKER + "\n\nExact self-heal candidate.",
            "user": {"login": "github-actions[bot]"},
            "base": {"ref": "main", "sha": "a" * 40},
            "head": {
                "ref": "automation/self-heal-1234567890abcdef",
                "sha": "b" * 40,
                "repo": {"full_name": "example/qik-vrt"},
            },
        }
        value.update(overrides)
        return value

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

    def test_ready_green_exact_head_holds_without_exact_base_cas(self):
        result = MODULE.evaluate_promotion(self.snapshot())
        self.assertEqual(
            (result["state"], result["phase"], result["first_blocker"]),
            ("BLOCK", "REQUEST_EXACT_BASE_CAS_AUTHORITY", "HEAD1_BASE_CAS_UNAVAILABLE"),
        )
        self.assertEqual(
            result["next_action"],
            "REQUEST_HISTORY_PRESERVING_EXACT_BASE_CAS_AUTHORITY",
        )
        self.assertEqual(result["verification_state"], "HOLD_UNVERIFIED")
        self.assertFalse(result["completion_claims"]["MERGE"])

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

    def test_draft_requests_ready_authority_without_mutation(self):
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
        self.assertEqual(
            (result["state"], result["phase"], result["first_blocker"]),
            (
                "BLOCK",
                "REQUEST_READY_RECLASSIFICATION_AUTHORITY",
                "READY_RECLASSIFICATION_CAS_UNAVAILABLE",
            ),
        )
        self.assertEqual(
            result["next_action"],
            "REQUEST_HISTORY_PRESERVING_READY_RECLASSIFICATION_AUTHORITY",
        )
        self.assertEqual(result["verification_state"], "HOLD_UNVERIFIED")

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
        self.assertEqual(result["first_blocker"], "HEAD1_BASE_CAS_UNAVAILABLE")

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
        self.assertEqual(result["first_blocker"], "HEAD1_BASE_CAS_UNAVAILABLE")

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

    def test_newer_pending_mesh_status_breaks_final_promotion_fence(self):
        success = {
            "id": 41,
            "context": MODULE.REVIEW_GATE,
            "state": "success",
            "created_at": "2026-08-22T10:00:00Z",
            "description": (
                "Technical observation complete; independent approval required; "
                f"fp={'a' * 64}"
            ),
        }
        pending = {
            "id": 42,
            "context": MODULE.REVIEW_GATE,
            "state": "pending",
            "created_at": "2026-08-22T10:01:00Z",
            "description": f"Mesh WAIT; D0=1; fp={'b' * 64}",
        }
        fence = MODULE.mesh_review_status_projection([success], MODULE.REVIEW_GATE)

        with self.assertRaisesRegex(
            MODULE.PromotionBlock,
            "requested-review execution is 'pending' at final fence",
        ):
            MODULE.require_unchanged_mesh_review_status(
                fence,
                [success, pending],
                MODULE.REVIEW_GATE,
            )

        self.assertEqual(
            MODULE.require_unchanged_mesh_review_status(
                fence,
                [success],
                MODULE.REVIEW_GATE,
            ),
            fence,
        )

    def test_promotion_marker_is_trusted_body_bound_and_revocable(self):
        pull_request = self.promotion_pr()
        binding = MODULE.trusted_promotion_marker(
            pull_request, "example/qik-vrt"
        )
        self.assertEqual(binding["source"], "TRUSTED_AUTONOMOUS_SELF_HEAL_PR_BODY")

        edited = self.promotion_pr(
            body=MODULE.PROMOTION_MARKER + "\n\nEdited candidate description."
        )
        with self.assertRaisesRegex(
            MODULE.PromotionBlock, "promotion marker body changed before mutation"
        ):
            MODULE.require_unchanged_promotion_marker(
                binding["body_sha256"], edited, "example/qik-vrt"
            )

        with self.assertRaisesRegex(
            MODULE.PromotionBlock, "workflow identity"
        ):
            MODULE.trusted_promotion_marker(
                self.promotion_pr(user={"login": "untrusted-user"}),
                "example/qik-vrt",
            )

        with self.assertRaisesRegex(
            MODULE.PromotionBlock, "has no promotion marker"
        ):
            MODULE.trusted_promotion_marker(
                self.promotion_pr(body="marker exists only in an issue comment"),
                "example/qik-vrt",
            )

    def test_workflow_reobserves_independent_authority_separately(self):
        workflow = (ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml").read_text(encoding="utf-8")
        self.assertIn('REVIEW_STATUS_CONTEXT: "QIKVRT requested review execution"', workflow)
        self.assertIn('"QIKVRT required code-owner review"', workflow)
        self.assertIn("evaluate_required_review", workflow)
        self.assertIn("code_owner_review_gate", workflow)
        self.assertIn("independent Code Owner gate changed", workflow)
        self.assertIn("mesh_review_status_projection", workflow)
        self.assertIn(
            "MESH_REVIEW_LEDGER_REF: refs/heads/qikvrt/mesh-review-ledger-v1",
            workflow,
        )
        self.assertIn("ledger_commit=gh_json", workflow)
        self.assertIn("ref=urllib.parse.quote(ledger_commit,safe='')", workflow)
        self.assertIn("prepare_diff_transport_ledger_entries", workflow)
        self.assertIn("reassemble_diff_transport", workflow)
        self.assertIn("manifest_ledger_path=root+'.chunks.json'", workflow)
        self.assertIn("receipt.get('ledger_diff_path') != manifest_ledger_path", workflow)
        self.assertIn("receipt.get('diff_transport') != manifest", workflow)
        self.assertIn("expected_path=f'{root}.chunks/{index:08d}.bin'", workflow)
        self.assertIn("manifest_bytes != canonical_manifest or packets != canonical_packets", workflow)
        self.assertIn("diff_path.write_bytes(complete_diff)", workflow)
        self.assertNotIn("ledger_bytes(root+'.diff')", workflow)
        self.assertIn("tools/qikvrt_requested_review_executor.py','verify'", workflow)
        self.assertIn("'--expected-diff',str(diff_path)", workflow)
        self.assertIn("status and ledger fingerprints differ", workflow)
        self.assertIn("fresh Mesh receipt is not TECHNICAL_CONTINUE", workflow)
        self.assertIn("require_unchanged_mesh_review_status", workflow)
        self.assertIn("require_unchanged_promotion_marker", workflow)
        self.assertNotIn("marked = any(marker in", workflow)
        self.assertIn("final promotion fence", workflow)
        self.assertNotIn('gh pr ready', workflow)
        self.assertNotIn('pull-requests: write', workflow)
        self.assertGreater(
            workflow.rindex("tools/qikvrt_requested_review_executor.py','verify'"),
            workflow.index("require_unchanged_mesh_review_status"),
        )
        self.assertLess(
            workflow.rindex("tools/qikvrt_requested_review_executor.py','verify'"),
            workflow.index("HOLD_UNVERIFIED: no repository mutation follows"),
        )
        self.assertNotIn('pulls/${PR_NUMBER}/merge', workflow)
        self.assertNotIn("gh pr merge", workflow)

    def test_promotion_chunk_transport_rejects_incomplete_or_drifted_packets(self):
        packet_bytes = REVIEW_MODULE.REVIEW_DIFF_CHUNK_BYTES
        diff = b"a" * packet_bytes + b"b" * packet_bytes + b"c" * 17
        root = "state/mesh/reviews/pr-459/head/fingerprint"
        manifest_path = root + ".chunks.json"
        transport = REVIEW_MODULE.build_diff_transport(diff, root)
        manifest_bytes, packets = REVIEW_MODULE.prepare_diff_transport_ledger_entries(
            transport, diff, manifest_path
        )
        manifest = json.loads(manifest_bytes.decode("utf-8"))

        self.assertEqual(
            REVIEW_MODULE.reassemble_diff_transport(manifest, packets),
            diff,
        )
        self.assertEqual(
            manifest_bytes,
            REVIEW_MODULE._pretty_json_bytes(manifest),
        )

        with self.assertRaisesRegex(
            REVIEW_MODULE.ReviewSnapshotError, "packet count is invalid"
        ):
            REVIEW_MODULE.reassemble_diff_transport(manifest, packets[:-1])
        with self.assertRaisesRegex(
            REVIEW_MODULE.ReviewSnapshotError, "packet count is invalid"
        ):
            REVIEW_MODULE.reassemble_diff_transport(manifest, packets + [b"surplus"])
        with self.assertRaisesRegex(
            REVIEW_MODULE.ReviewSnapshotError, "packet digest mismatch"
        ):
            REVIEW_MODULE.reassemble_diff_transport(
                manifest, [packets[1], packets[0], packets[2]]
            )
        with self.assertRaisesRegex(
            REVIEW_MODULE.ReviewSnapshotError, "packet digest mismatch"
        ):
            REVIEW_MODULE.reassemble_diff_transport(
                manifest, [packets[0], packets[1], b"d" * 17]
            )

        tampered_manifest = dict(manifest)
        tampered_manifest["total_bytes"] += 1
        with self.assertRaisesRegex(
            REVIEW_MODULE.ReviewSnapshotError, "manifest digest mismatch"
        ):
            REVIEW_MODULE.reassemble_diff_transport(tampered_manifest, packets)
        with self.assertRaisesRegex(
            REVIEW_MODULE.ReviewSnapshotError, "does not bind"
        ):
            REVIEW_MODULE.prepare_diff_transport_ledger_entries(
                manifest, diff, root + "-other.chunks.json"
            )


if __name__ == "__main__":
    unittest.main()
