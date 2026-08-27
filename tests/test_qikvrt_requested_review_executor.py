# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_requested_review_executor.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_ci.yml"
PROMOTION_WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_expected_head_promotion.yml"
OBSERVER_WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_code_owner_review_observer.yml"
REQUIRED_REVIEW_GATE_WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_required_review_gate.yml"
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_executor",
    ROOT / "tools/qikvrt_requested_review_executor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

MAIN_SHA = "a" * 40
HEAD_SHA = "b" * 40
HEAD_TREE_SHA = "c" * 40
BASE_TREE_SHA = "d" * 40
MERGE_SHA = "e" * 40
REQUIRED_GATE_PATHS = {
    "QIKVRT CI": ".github/workflows/qikvrt_ci.yml",
    "QIKVRT repository evidence materialization": ".github/workflows/qikvrt_batch04_integrity.yml",
    "QIKVRT Collective Proposal Review": ".github/workflows/qikvrt_collective_review.yml",
}
REQUIRED_GATE_WORKFLOW_IDS = {
    "QIKVRT CI": 1101,
    "QIKVRT repository evidence materialization": 1201,
    "QIKVRT Collective Proposal Review": 1301,
}

DEFAULT_DIFF_BYTES = b"""diff --git a/src/a.py b/src/a.py
index 1111111111111111111111111111111111111111..2222222222222222222222222222222222222222 100644
--- a/src/a.py
+++ b/src/a.py
@@ -1 +1 @@
-return 0
+return 1
diff --git a/tests/test_a.py b/tests/test_a.py
index 3333333333333333333333333333333333333333..4444444444444444444444444444444444444444 100644
--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -1 +1 @@
-assert value == 0
+assert value == 1
"""

CONFLICT_DIFF_BYTES = DEFAULT_DIFF_BYTES + b"""+<<<<<<< HEAD
+left
+=======
+right
+>>>>>>> competing-branch
"""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def scope_sha256(changed_files: list[dict[str, object]]) -> str:
    normalized = [
        {
            "path": item["path"],
            "previous_path": item.get("previous_path"),
            "status": item["status"],
            "base_blob_sha": item["base_blob_sha"],
            "head_blob_sha": item["head_blob_sha"],
        }
        for item in sorted(changed_files, key=lambda item: str(item["path"]))
    ]
    payload = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


class RequestedReviewExecutorTests(unittest.TestCase):
    def selector_pr(self, **overrides):
        value = {
            "number": 867,
            "state": "open",
            "base": {"ref": "main", "sha": MAIN_SHA},
            "head": {
                "sha": HEAD_SHA,
                "repo": {"full_name": "example/qik-vrt"},
            },
        }
        value.update(overrides)
        return value

    def git_commit(self, sha, tree_sha, parents=()):
        return {
            "sha": sha,
            "tree": {"sha": tree_sha},
            "parents": [{"sha": parent} for parent in parents],
        }

    def review_intake(
        self,
        *,
        action: str = "",
        actor: str | None = None,
        reviewer: str | None = None,
        team: str | None = None,
        labels: list[str] | None = None,
        event_payload_sha256: str | None = None,
    ) -> dict[str, object]:
        return MODULE._review_intake(
            {
                "source": "PULL_REQUEST_EVENT",
                "event_name": "pull_request_target",
                "event_action": action,
                "event_payload_sha256": event_payload_sha256 or sha256_bytes(b"review event"),
                "event_actor": actor,
                "requested_reviewer": reviewer,
                "requested_team": team,
                "native_delivery_identity": "UNAVAILABLE_TO_GITHUB_ACTIONS",
            },
            [] if labels is None else labels,
            [reviewer] if action == "review_requested" and reviewer else [],
            [team] if action == "review_requested" and team else [],
        )

    def changed_files(self) -> list[dict[str, object]]:
        return [
            {
                "path": "src/a.py",
                "status": "modified",
                "base_blob_sha": "1" * 40,
                "head_blob_sha": "2" * 40,
            },
            {
                "path": "tests/test_a.py",
                "status": "modified",
                "base_blob_sha": "3" * 40,
                "head_blob_sha": "4" * 40,
            },
        ]

    def workflow_run(
        self,
        name: str,
        *,
        identifier: int,
        run_number: int,
        run_attempt: int = 1,
        status: str = "completed",
        conclusion: str | None = "success",
        head_sha: str = HEAD_SHA,
        path: str | None = None,
        workflow_id: int | None = None,
        event: str = "pull_request",
        jobs_total: int = 1,
        jobs: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        if jobs is None:
            jobs = [] if jobs_total == 0 else [
                {
                    "id": identifier * 1000 + offset,
                    "status": "completed" if status == "completed" else status,
                    "conclusion": conclusion if status == "completed" else None,
                }
                for offset in range(1, jobs_total + 1)
            ]
        return {
            "id": identifier,
            "workflow_id": workflow_id or REQUIRED_GATE_WORKFLOW_IDS.get(name, identifier + 1000),
            "name": name,
            "path": path or REQUIRED_GATE_PATHS.get(
                name,
                ".github/workflows/qikvrt_conditional_probe.yml",
            ),
            "event": event,
            "jobs_total": jobs_total,
            "jobs": jobs,
            "status": status,
            "conclusion": conclusion,
            "run_number": run_number,
            "run_attempt": run_attempt,
            "head_sha": head_sha,
        }

    def workflow_runs(self) -> list[dict[str, object]]:
        return [
            self.workflow_run("QIKVRT CI", identifier=101, run_number=10),
            self.workflow_run(
                "QIKVRT repository evidence materialization",
                identifier=201,
                run_number=20,
            ),
            self.workflow_run(
                "QIKVRT Collective Proposal Review",
                identifier=301,
                run_number=30,
            ),
            self.workflow_run(
                "QIK-VRT global claim completion",
                identifier=401,
                run_number=40,
            ),
            self.workflow_run(
                "QIKVRT conditional probe",
                identifier=501,
                run_number=1,
                conclusion="skipped",
            ),
        ]

    def snapshot(self, *, diff_payload: bytes = DEFAULT_DIFF_BYTES, **overrides):
        changed_files = self.changed_files()
        value = {
            "repository": "example/qik-vrt",
            "repository_role": "AUTHORITY",
            "pr_number": 349,
            "pr_state": "open",
            "pr_title_sha256": sha256_bytes(b"Test pull request"),
            "pr_body_sha256": sha256_bytes(b"Initial review body"),
            "head_repository": "example/qik-vrt",
            "trusted_evaluator_blob_sha": "e" * 40,
            "trusted_workflow_blob_sha": "f" * 40,
            "current_main_sha": MAIN_SHA,
            "current_main_tree_sha": BASE_TREE_SHA,
            "base_sha": MAIN_SHA,
            "base_tree_sha": BASE_TREE_SHA,
            "head_sha": HEAD_SHA,
            "observed_head_sha": HEAD_SHA,
            "tree_sha": HEAD_TREE_SHA,
            "observed_tree_sha": HEAD_TREE_SHA,
            "draft": False,
            # Mesh review is repository-initiated; a human review request is not
            # a precondition for the substantive technical disposition.
            "requested_reviewers": [],
            "requested_team_reviewers": [],
            "changed_files": changed_files,
            "scope_sha256": scope_sha256(changed_files),
            "diff_sha256": sha256_bytes(diff_payload),
            "diff_bytes": len(diff_payload),
            "diff_complete": True,
            "review_threads": [],
            "unresolved_review_threads": 0,
            "discussion_items": [],
            "active_writers": [],
            "required_gates": [
                "QIKVRT CI",
                "QIKVRT repository evidence materialization",
                "QIKVRT Collective Proposal Review",
            ],
            "required_gate_paths": REQUIRED_GATE_PATHS,
            "required_gate_workflow_ids": REQUIRED_GATE_WORKFLOW_IDS,
            "required_gate_events": {
                name: "pull_request" for name in REQUIRED_GATE_PATHS
            },
            "workflow_runs": self.workflow_runs(),
        }
        value.update(overrides)
        return value

    def evaluate(self, snapshot=None, diff_payload: bytes = DEFAULT_DIFF_BYTES):
        result = MODULE.evaluate(
            self.snapshot() if snapshot is None else snapshot,
            diff_payload,
        )
        self.assert_safety_boundaries(result)
        return result

    def finding_ids(self, result: dict[str, object]) -> list[str]:
        return [finding["finding_id"] for finding in result["findings"]]

    def assert_safety_boundaries(self, result: dict[str, object]) -> None:
        self.assertEqual(result["verification_state"], "HOLD_UNVERIFIED")
        self.assertFalse(result["derived_action"]["productive_effect"])
        self.assertEqual(result["derived_action"]["effect_ack"], "HOLD_UNVERIFIED")
        completion_claims = result["completion_claims"]
        self.assertTrue(completion_claims)
        self.assertTrue(all(value is False for value in completion_claims.values()))

    def assert_receipt_boundaries(self, result: dict[str, object]) -> None:
        self.assertEqual(result["schema"], "qikvrt_mesh_repository_review_receipt_v1")
        self.assertIsInstance(result["findings"], list)
        fingerprint = result["evidence_fingerprint"]
        self.assertIsInstance(fingerprint, str)
        self.assertEqual(len(fingerprint), 64)
        self.assertTrue(all(character in "0123456789abcdef" for character in fingerprint))
        ledger_path = result["ledger_path"]
        self.assertIsInstance(ledger_path, str)
        self.assertIn(HEAD_SHA, ledger_path)
        self.assertTrue(ledger_path.endswith(".json"))

    def test_clean_exact_mesh_review_without_requested_reviewer_approves(self):
        result = self.evaluate()

        self.assert_receipt_boundaries(result)
        self.assertEqual(result["mesh_disposition"], "APPROVE")
        self.assertIsNone(result["first_blocker"])
        self.assertIn("EXACT_DIFF_BOUND", self.finding_ids(result))
        self.assertIn("EXACT_HEAD_GATES_NON_ADVERSE", self.finding_ids(result))
        self.assertEqual(
            result["derived_action"],
            {
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "next_action": "REQUEST_EXACT_HEAD_CODE_OWNER_REOBSERVATION",
                "productive_effect": False,
                "effect_ack": "HOLD_UNVERIFIED",
            },
        )

    def test_review_intake_classifies_requester_reviewer_and_declared_reason(self):
        cases = {
            "security": (
                self.review_intake(
                    action="review_requested",
                    actor="ingolf-lohmann",
                    reviewer="Goldkelch",
                    labels=["qikvrt-review:security"],
                ),
                "P0_SECURITY_OR_INTEGRITY",
                0,
            ),
            "owner-to-code-owner": (
                self.review_intake(
                    action="review_requested",
                    actor="ingolf-lohmann",
                    reviewer="Goldkelch",
                    labels=["qikvrt-review:owner"],
                ),
                "P1_PRODUCT_OWNER_TO_REQUIRED_CODE_OWNER",
                1,
            ),
            "code-owner-target": (
                self.review_intake(
                    action="review_requested",
                    actor="other-maintainer",
                    reviewer="Goldkelch",
                ),
                "P2_REQUIRED_CODE_OWNER_REQUEST",
                2,
            ),
            "ordinary-request": (
                self.review_intake(
                    action="review_requested",
                    actor="other-maintainer",
                    reviewer="other-reviewer",
                ),
                "P3_EXPLICIT_REVIEW_REQUEST",
                3,
            ),
            "automatic-reobservation": (
                self.review_intake(
                    action="review_request_removed",
                    actor="other-maintainer",
                    reviewer="Goldkelch",
                ),
                "P4_AUTOMATIC_ELIGIBLE_EVENT",
                4,
            ),
        }
        fingerprints: set[str] = set()
        for label, (intake, priority_class, rank) in cases.items():
            with self.subTest(label=label):
                self.assertEqual(intake["priority_class"], priority_class)
                self.assertEqual(intake["priority_rank"], rank)
                result = self.evaluate(self.snapshot(review_intake=intake))
                self.assertEqual(result["review_intake"], intake)
                fingerprints.add(result["evidence_fingerprint"])
        self.assertEqual(len(fingerprints), len(cases))

    def test_ambiguous_review_reason_is_receipt_bound_and_fail_closed(self):
        intake = self.review_intake(
            action="review_requested",
            actor="ingolf-lohmann",
            reviewer="Goldkelch",
            labels=["qikvrt-review:owner", "qikvrt-review:security"],
        )
        result = self.evaluate(self.snapshot(review_intake=intake))

        self.assertEqual(intake["reason_state"], "AMBIGUOUS_FAIL_CLOSED")
        self.assertEqual(result["mesh_disposition"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "REVIEW_REASON_AMBIGUOUS")
        self.assertEqual(result["derived_action"]["d0"], 2)
        self.assert_receipt_boundaries(result)

    def test_review_intake_cannot_claim_a_higher_policy_rank(self):
        intake = self.review_intake(
            action="review_requested",
            actor="other-maintainer",
            reviewer="other-reviewer",
        )
        intake["priority_class"] = "P0_SECURITY_OR_INTEGRITY"
        intake["priority_rank"] = 0

        result = self.evaluate(self.snapshot(review_intake=intake))
        self.assertEqual(result["mesh_disposition"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "INVALID_REVIEW_SNAPSHOT")

    def test_event_payload_digest_is_fingerprint_bound(self):
        first = self.review_intake(
            action="review_requested",
            actor="ingolf-lohmann",
            reviewer="Goldkelch",
            event_payload_sha256=sha256_bytes(b"first native event"),
        )
        second = self.review_intake(
            action="review_requested",
            actor="ingolf-lohmann",
            reviewer="Goldkelch",
            event_payload_sha256=sha256_bytes(b"second native event"),
        )

        first_result = self.evaluate(self.snapshot(review_intake=first))
        second_result = self.evaluate(self.snapshot(review_intake=second))
        self.assertNotEqual(
            first_result["evidence_fingerprint"],
            second_result["evidence_fingerprint"],
        )

    def test_removed_requested_target_is_a_fingerprint_bound_reobservation(self):
        intake = MODULE._review_intake(
            {
                "source": "PULL_REQUEST_EVENT",
                "event_name": "pull_request_target",
                "event_action": "review_requested",
                "event_actor": "ingolf-lohmann",
                "requested_reviewer": "Goldkelch",
                "requested_team": None,
                "native_delivery_identity": "UNAVAILABLE_TO_GITHUB_ACTIONS",
            },
            [],
            [],
            [],
        )
        result = self.evaluate(self.snapshot(review_intake=intake))
        self.assertEqual(intake["request_state"], "STALE_EXPLICIT_REQUEST")
        self.assertFalse(intake["requested_target_observed"])
        self.assertEqual(result["mesh_disposition"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "REVIEW_REQUEST_STALE")
        self.assertEqual(result["derived_action"]["d0"], 2)

    def test_requested_reviewer_observation_is_login_case_insensitive(self):
        intake = MODULE._review_intake(
            {
                "source": "PULL_REQUEST_EVENT",
                "event_name": "pull_request_target",
                "event_action": "review_requested",
                "event_actor": "ingolf-lohmann",
                "requested_reviewer": "Goldkelch",
                "requested_team": None,
                "native_delivery_identity": "UNAVAILABLE_TO_GITHUB_ACTIONS",
            },
            [],
            ["goldkelch"],
            [],
        )

        self.assertTrue(intake["requested_target_observed"])
        self.assertEqual(intake["request_state"], "ACTIVE_EXPLICIT_REQUEST")

    def test_chunked_materialized_diff_above_legacy_two_mebibytes_is_reviewable(self):
        diff = b"+" * (2 * MODULE.REVIEW_DIFF_CHUNK_BYTES + 1)
        snapshot = self.snapshot(
            diff_payload=diff,
            diff_sha256=sha256_bytes(diff),
            diff_bytes=len(diff),
            diff_complete=True,
        )
        result = self.evaluate(snapshot, diff)

        self.assertNotEqual(result["first_blocker"], "REVIEW_BYTES_UNAVAILABLE")
        self.assertEqual(result["mesh_disposition"], "APPROVE")
        self.assert_receipt_boundaries(result)
        self.assertEqual(result["diff_sha256"], sha256_bytes(diff))
        self.assertEqual(result["diff_bytes"], len(diff))
        transport = result["diff_transport"]
        self.assertEqual(transport["packet_count"], 3)
        self.assertEqual(
            MODULE.reassemble_diff_transport(
                transport,
                [
                    diff[: MODULE.REVIEW_DIFF_CHUNK_BYTES],
                    diff[MODULE.REVIEW_DIFF_CHUNK_BYTES : 2 * MODULE.REVIEW_DIFF_CHUNK_BYTES],
                    diff[2 * MODULE.REVIEW_DIFF_CHUNK_BYTES :],
                ],
            ),
            diff,
        )
        plan = MODULE.plan_ledger_update(
            MODULE._pretty_json_bytes(result),
            MODULE._pretty_json_bytes(transport),
            None,
            None,
            None,
        )
        self.assertEqual(plan["action"], "INITIALIZE_ORPHAN_ROOT")
        with mock.patch.object(
            MODULE,
            "observe_repository",
            return_value=(snapshot, diff),
        ):
            report, _fresh, _observed_diff = MODULE.verify_current_receipt(
                result,
                MODULE._pretty_json_bytes(result),
                diff,
                "example/qik-vrt",
                349,
                999,
                list(REQUIRED_GATE_PATHS),
                REQUIRED_GATE_PATHS,
                [],
            )
        self.assertTrue(report["exact"])

    def test_diff_transport_is_one_mebibyte_ordered_and_fail_closed(self):
        diff = b"a" * MODULE.REVIEW_DIFF_CHUNK_BYTES + b"b" * 17
        transport = MODULE.build_diff_transport(diff, "state/mesh/reviews/example")

        self.assertEqual(transport["packet_bytes"], 1024 * 1024)
        self.assertEqual(transport["packet_count"], 2)
        self.assertEqual([item["bytes"] for item in transport["packets"]], [1024 * 1024, 17])
        self.assertEqual(MODULE.reassemble_diff_transport(transport, [diff[: 1024 * 1024], diff[1024 * 1024 :]]), diff)
        with self.assertRaisesRegex(MODULE.ReviewSnapshotError, "packet digest mismatch"):
            MODULE.reassemble_diff_transport(transport, [diff[: 1024 * 1024], b"c" * 17])
        malformed = dict(transport)
        malformed["packet_count"] = 3
        malformed["manifest_sha256"] = MODULE._canonical_sha256(
            {key: value for key, value in malformed.items() if key != "manifest_sha256"}
        )
        with self.assertRaisesRegex(MODULE.ReviewSnapshotError, "packet count is invalid"):
            MODULE.reassemble_diff_transport(
                malformed,
                [diff[: 1024 * 1024], diff[1024 * 1024 :]],
            )

        oversized_packet = {
            "schema": MODULE.REVIEW_DIFF_TRANSPORT_SCHEMA,
            "packet_bytes": MODULE.REVIEW_DIFF_CHUNK_BYTES,
            "packet_count": 1,
            "total_bytes": len(diff),
            "sha256": sha256_bytes(diff),
            "manifest_path": "state/mesh/reviews/example.chunks.json",
            "packets": [{
                "index": 0,
                "offset": 0,
                "bytes": len(diff),
                "sha256": sha256_bytes(diff),
                "path": "state/mesh/reviews/example.chunks/00000000.bin",
            }],
            "delivery": MODULE.REVIEW_DIFF_TRANSPORT_DELIVERY,
        }
        oversized_packet["manifest_sha256"] = MODULE._canonical_sha256(oversized_packet)
        with self.assertRaisesRegex(MODULE.ReviewSnapshotError, "packet order is invalid"):
            MODULE.reassemble_diff_transport(oversized_packet, [diff])

    def test_diff_transport_must_bind_the_exact_ledger_manifest_path(self):
        diff = b"a" * MODULE.REVIEW_DIFF_CHUNK_BYTES + b"b"
        path = "state/mesh/reviews/pr-349/head/fingerprint.chunks.json"
        transport = MODULE.build_diff_transport(
            diff, path[: -len(".chunks.json")]
        )
        manifest, packets = MODULE.prepare_diff_transport_ledger_entries(
            transport, diff, path
        )

        self.assertEqual(manifest, MODULE._pretty_json_bytes(transport))
        self.assertEqual(packets, [diff[: MODULE.REVIEW_DIFF_CHUNK_BYTES], b"b"])
        with self.assertRaisesRegex(MODULE.ReviewSnapshotError, "does not bind"):
            MODULE.prepare_diff_transport_ledger_entries(
                transport, diff, path + ".wrong"
            )

    def test_same_head_pull_request_body_change_creates_new_receipt_identity(self):
        first = self.evaluate()
        changed = self.snapshot(pr_body_sha256=sha256_bytes(b"Edited review body"))
        second = self.evaluate(changed)

        self.assertNotEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])
        self.assertNotEqual(first["ledger_path"], second["ledger_path"])
        self.assertNotEqual(first["receipt_payload_sha256"], second["receipt_payload_sha256"])

    def test_nonterminal_required_gate_waits_and_reobserves(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            self.workflow_run(
                "QIKVRT CI",
                identifier=102,
                run_number=11,
                status="in_progress",
                conclusion=None,
            )
        )

        result = self.evaluate(snap)

        self.assertEqual(result["mesh_disposition"], "WAIT")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_NOT_TERMINAL")
        self.assertEqual(result["derived_action"]["d0"], 1)
        self.assertEqual(result["derived_action"]["state"], "HOLD")
        self.assertFalse(result["derived_action"]["productive_effect"])

    def test_missing_required_gate_waits_and_reobserves(self):
        snap = self.snapshot()
        snap["workflow_runs"] = [
            run
            for run in snap["workflow_runs"]
            if run["name"] != "QIKVRT repository evidence materialization"
        ]

        result = self.evaluate(snap)

        self.assertEqual(result["mesh_disposition"], "WAIT")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_MISSING")
        self.assertEqual(result["derived_action"]["d0"], 2)
        self.assertEqual(result["derived_action"]["state"], "REOBSERVE")

    def test_failed_gate_requests_changes_and_holds(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            self.workflow_run(
                "QIKVRT CI",
                identifier=102,
                run_number=11,
                conclusion="failure",
            )
        )

        result = self.evaluate(snap)

        self.assertEqual(result["mesh_disposition"], "REQUEST_CHANGES")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_FAILED")
        self.assertEqual(result["derived_action"]["d0"], 1)
        self.assertEqual(result["derived_action"]["state"], "HOLD")
        self.assertFalse(result["derived_action"]["productive_effect"])

    def test_required_gate_name_from_untrusted_workflow_path_reobserves(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            self.workflow_run(
                "QIKVRT CI",
                identifier=102,
                run_number=11,
                path=".github/workflows/spoofed_ci.yml",
            )
        )

        result = self.evaluate(snap)

        self.assertEqual(result["mesh_disposition"], "WAIT")
        self.assertEqual(result["first_blocker"], "UNTRUSTED_GATE_BINDING")
        self.assertEqual(result["derived_action"]["d0"], 2)
        self.assertEqual(result["derived_action"]["state"], "REOBSERVE")

    def test_draft_continuation_requires_trusted_gate_identity_first(self):
        snap = self.snapshot(draft=True)
        snap["workflow_runs"].append(
            self.workflow_run(
                "QIKVRT CI",
                identifier=102,
                run_number=11,
                path=".github/workflows/spoofed_ci.yml",
            )
        )

        result = self.evaluate(snap)

        self.assertEqual(result["first_blocker"], "UNTRUSTED_GATE_BINDING")
        self.assertNotEqual(result["first_blocker"], "DRAFT")

    def test_required_workflow_name_with_distinct_identity_fails_closed(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            self.workflow_run(
                "QIKVRT CI",
                identifier=102,
                run_number=11,
                workflow_id=9999,
                path=".github/workflows/spoofed_ci.yml",
                conclusion="failure",
            )
        )

        result = self.evaluate(snap)

        self.assertEqual(result["mesh_disposition"], "WAIT")
        self.assertEqual(result["first_blocker"], "UNTRUSTED_GATE_BINDING")
        self.assertIn("ambiguous across 2 stable identities", result["detail"])
        self.assertEqual(result["verification_state"], "HOLD_UNVERIFIED")
        self.assertTrue(
            all(value is False for value in result["completion_claims"].values())
        )

    def test_candidate_run_named_like_mesh_executor_is_not_omitted(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            self.workflow_run(
                "QIKVRT requested review executor",
                identifier=801,
                run_number=1,
                workflow_id=8801,
                path=".github/workflows/candidate_name_collision.yml",
                conclusion="failure",
            )
        )

        result = self.evaluate(snap)

        self.assertEqual(result["mesh_disposition"], "REQUEST_CHANGES")
        self.assertEqual(result["first_blocker"], "APPLICABLE_GATE_FAILED")
        self.assertIn("QIKVRT requested review executor", result["detail"])

    def test_required_gate_identity_event_and_jobs_are_fail_closed(self):
        cases = {
            "workflow-id": {"workflow_id": 9999},
            "event": {"event": "workflow_dispatch"},
            "zero-job": {"jobs_total": 0},
        }
        for label, arguments in cases.items():
            with self.subTest(label=label):
                snap = self.snapshot()
                snap["workflow_runs"].append(
                    self.workflow_run(
                        "QIKVRT CI",
                        identifier=102,
                        run_number=11,
                        **arguments,
                    )
                )
                result = self.evaluate(snap)
                expected = "ZERO_JOB_GATE" if label == "zero-job" else "UNTRUSTED_GATE_BINDING"
                self.assertEqual(result["first_blocker"], expected)
                self.assertEqual(result["derived_action"]["d0"], 2)
                self.assertEqual(result["derived_action"]["state"], "REOBSERVE")

    def test_skipped_only_gate_has_zero_executed_job_and_reobserves(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            self.workflow_run(
                "QIKVRT CI",
                identifier=102,
                run_number=11,
                jobs=[
                    {
                        "id": 102001,
                        "status": "completed",
                        "conclusion": "skipped",
                    }
                ],
            )
        )

        result = self.evaluate(snap)

        self.assertEqual(result["mesh_disposition"], "WAIT")
        self.assertEqual(result["first_blocker"], "ZERO_EXECUTED_JOB_GATE")
        self.assertIn("ZERO_EXECUTED_JOB_GATE", self.finding_ids(result))
        self.assertEqual(result["derived_action"]["d0"], 2)
        self.assertEqual(result["derived_action"]["state"], "REOBSERVE")

    def test_optional_skipped_only_gate_remains_non_adverse(self):
        result = self.evaluate()

        probe = next(
            run
            for run in result["latest_workflows"]
            if run["name"] == "QIKVRT conditional probe"
        )
        self.assertEqual(result["mesh_disposition"], "APPROVE")
        self.assertEqual(probe["conclusion"], "skipped")
        self.assertEqual(probe["jobs"][0]["conclusion"], "skipped")

    def test_job_id_status_and_conclusion_are_fingerprint_bound(self):
        baseline = self.snapshot()
        gate = next(
            run for run in baseline["workflow_runs"] if run["name"] == "QIKVRT CI"
        )
        gate["jobs_total"] = 2
        gate["jobs"] = [
            {"id": 101001, "status": "completed", "conclusion": "success"},
            {"id": 101002, "status": "completed", "conclusion": "success"},
        ]
        first = self.evaluate(copy.deepcopy(baseline))

        mutations = {
            "id": {"id": 101003, "status": "completed", "conclusion": "success"},
            "status": {"id": 101002, "status": "in_progress", "conclusion": "success"},
            "conclusion": {"id": 101002, "status": "completed", "conclusion": "skipped"},
        }
        for label, replacement in mutations.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(baseline)
                changed_gate = next(
                    run
                    for run in changed["workflow_runs"]
                    if run["name"] == "QIKVRT CI"
                )
                changed_gate["jobs"][1] = replacement
                result = self.evaluate(changed)
                self.assertEqual(result["mesh_disposition"], "APPROVE")
                self.assertNotEqual(
                    result["evidence_fingerprint"], first["evidence_fingerprint"]
                )
                self.assertEqual(
                    next(
                        run
                        for run in result["latest_workflows"]
                        if run["name"] == "QIKVRT CI"
                    )["jobs"],
                    sorted(changed_gate["jobs"], key=lambda job: job["id"]),
                )

    def test_workflow_projection_cannot_be_overwritten_by_display_name(self):
        snap = self.snapshot()
        alias_name = "Alias"
        colliding_display_name = (
            "Alias [workflow_id=9001 path=.github/workflows/a.yml "
            "event=pull_request]"
        )
        snap["workflow_runs"].extend(
            [
                self.workflow_run(
                    alias_name,
                    identifier=9001,
                    run_number=1,
                    workflow_id=9001,
                    path=".github/workflows/a.yml",
                ),
                self.workflow_run(
                    alias_name,
                    identifier=9002,
                    run_number=1,
                    workflow_id=9002,
                    path=".github/workflows/b.yml",
                ),
                self.workflow_run(
                    colliding_display_name,
                    identifier=9003,
                    run_number=1,
                    workflow_id=9003,
                    path=".github/workflows/c.yml",
                ),
            ]
        )
        first = self.evaluate(snap)
        changed = copy.deepcopy(snap)
        changed_alias = next(
            run
            for run in changed["workflow_runs"]
            if run["workflow_id"] == 9001
        )
        changed_alias["jobs"][0]["id"] += 1
        second = self.evaluate(changed)

        self.assertEqual(first["mesh_disposition"], "APPROVE")
        self.assertEqual(second["mesh_disposition"], "APPROVE")
        self.assertEqual(len(first["latest_workflows"]), len(snap["workflow_runs"]))
        self.assertNotEqual(
            first["evidence_fingerprint"], second["evidence_fingerprint"]
        )
        self.assertNotEqual(
            first["receipt_payload_sha256"], second["receipt_payload_sha256"]
        )

    def test_paginated_job_observation_is_complete_and_order_stable(self):
        pages = [
            {
                "total_count": 2,
                "jobs": [
                    {"id": 22, "status": "completed", "conclusion": "success"}
                ],
            },
            {
                "total_count": 2,
                "jobs": [
                    {"id": 11, "status": "completed", "conclusion": "skipped"}
                ],
            },
        ]
        with mock.patch.object(MODULE, "_run_json", return_value=pages) as run_json:
            jobs = MODULE._gh_jobs("repos/example/qik-vrt/actions/runs/7/jobs?per_page=100")

        self.assertEqual([job["id"] for job in jobs], [22, 11])
        run_json.assert_called_once_with(
            (
                "gh",
                "api",
                "--paginate",
                "--slurp",
                "repos/example/qik-vrt/actions/runs/7/jobs?per_page=100",
            )
        )

    def test_incomplete_paginated_job_observation_fails_closed(self):
        pages = [
            {
                "total_count": 2,
                "jobs": [
                    {"id": 11, "status": "completed", "conclusion": "success"}
                ],
            }
        ]
        with mock.patch.object(MODULE, "_run_json", return_value=pages):
            with self.assertRaisesRegex(
                MODULE.ReviewObservationError,
                "workflow-job projection is incomplete",
            ):
                MODULE._gh_jobs(
                    "repos/example/qik-vrt/actions/runs/7/jobs?per_page=100"
                )

    def test_workflow_observation_projects_every_job(self):
        raw_run = self.workflow_run("QIKVRT CI", identifier=101, run_number=10)
        raw_run.pop("jobs_total")
        raw_run.pop("jobs")
        raw_jobs = [
            {"id": 12, "status": "completed", "conclusion": "skipped"},
            {"id": 11, "status": "completed", "conclusion": "success"},
        ]
        with (
            mock.patch.object(MODULE, "_gh_runs", return_value=[raw_run]),
            mock.patch.object(MODULE, "_gh_jobs", return_value=raw_jobs) as gh_jobs,
        ):
            runs = MODULE._workflow_observation("example/qik-vrt", HEAD_SHA)

        self.assertEqual(runs[0]["jobs_total"], 2)
        self.assertEqual(
            runs[0]["jobs"],
            [
                {"id": 11, "status": "completed", "conclusion": "success"},
                {"id": 12, "status": "completed", "conclusion": "skipped"},
            ],
        )
        gh_jobs.assert_called_once_with(
            "repos/example/qik-vrt/actions/runs/101/jobs?per_page=100"
        )

    def test_workflow_api_order_cannot_change_receipt_for_same_run_set(self):
        first = self.snapshot()
        first["workflow_runs"].extend(
            [
                self.workflow_run(
                    "Z applicable",
                    identifier=701,
                    run_number=1,
                    event="workflow_dispatch",
                ),
                self.workflow_run(
                    "A applicable",
                    identifier=702,
                    run_number=1,
                    jobs_total=0,
                ),
            ]
        )
        second = copy.deepcopy(first)
        second["workflow_runs"] = list(reversed(second["workflow_runs"]))
        for run in second["workflow_runs"]:
            run["jobs"] = list(reversed(run["jobs"]))

        first_result = self.evaluate(first)
        second_result = self.evaluate(second)

        self.assertEqual(first_result, second_result)
        self.assertEqual(first_result["first_blocker"], "UNTRUSTED_GATE_BINDING")
        self.assertEqual(
            first_result["receipt_payload_sha256"],
            second_result["receipt_payload_sha256"],
        )

    def test_diff_digest_mismatch_is_a_fail_closed_blocker(self):
        snap = self.snapshot()
        altered = DEFAULT_DIFF_BYTES + b"unexpected"

        result = self.evaluate(snap, altered)

        self.assertEqual(result["mesh_disposition"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "DIFF_DIGEST_MISMATCH")
        self.assertEqual(result["derived_action"]["d0"], 2)
        self.assertEqual(result["derived_action"]["state"], "REOBSERVE")

    def test_missing_or_incomplete_diff_is_a_fail_closed_blocker(self):
        snap = self.snapshot(
            diff_payload=b"",
            diff_complete=False,
            diff_sha256=sha256_bytes(b""),
            diff_bytes=0,
        )

        result = self.evaluate(snap, b"")

        self.assert_receipt_boundaries(result)
        self.assertEqual(result["mesh_disposition"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "DIFF_INCOMPLETE")
        self.assertEqual(result["derived_action"]["d0"], 2)
        self.assertEqual(result["derived_action"]["state"], "REOBSERVE")

    def test_scope_base_head_and_tree_drift_invalidate_review_evidence(self):
        cases = {
            "scope": ({"scope_sha256": "0" * 64}, "SCOPE_DIGEST_MISMATCH"),
            "base": ({"current_main_sha": "e" * 40}, "BASE_DRIFT"),
            "head": ({"observed_head_sha": "e" * 40}, "HEAD_DRIFT"),
            "base-tree": ({"current_main_tree_sha": "e" * 40}, "BASE_TREE_DRIFT"),
            "head-tree": ({"observed_tree_sha": "e" * 40}, "TREE_DRIFT"),
        }
        for label, (overrides, blocker) in cases.items():
            with self.subTest(label=label):
                result = self.evaluate(self.snapshot(**overrides))
                self.assertEqual(result["mesh_disposition"], "COMMENT_WITH_BLOCKER")
                self.assertEqual(result["first_blocker"], blocker)
                self.assertEqual(result["derived_action"]["d0"], 2)
                self.assertEqual(result["derived_action"]["state"], "REOBSERVE")
                self.assertFalse(result["derived_action"]["productive_effect"])

    def test_unresolved_review_thread_blocks_and_holds(self):
        result = self.evaluate(
            self.snapshot(
                review_threads=[
                    {
                        "id": "PRRT_kwDOAA_example",
                        "is_resolved": False,
                        "body_sha256": "e" * 64,
                    }
                ],
                unresolved_review_threads=1,
            )
        )

        self.assertEqual(result["mesh_disposition"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "UNRESOLVED_REVIEW_THREADS")
        self.assertEqual(result["derived_action"]["d0"], 1)
        self.assertEqual(result["derived_action"]["state"], "HOLD")

    def test_draft_waits_without_claiming_review_completion(self):
        result = self.evaluate(self.snapshot(draft=True))

        self.assertEqual(result["mesh_disposition"], "WAIT")
        self.assertEqual(result["first_blocker"], "DRAFT")
        self.assertEqual(result["derived_action"]["d0"], 1)
        self.assertEqual(result["derived_action"]["state"], "HOLD")
        self.assertEqual(
            result["derived_action"]["next_action"],
            "REQUEST_HISTORY_PRESERVING_READY_RECLASSIFICATION_AUTHORITY",
        )
        self.assertEqual(result["verification_state"], "HOLD_UNVERIFIED")

    def test_active_writer_waits_for_the_single_writer_lease(self):
        active_writer = {
            "id": 901,
            "name": "QIK-VRT autonomous bounded self-heal",
            "status": "in_progress",
            "head_sha": MAIN_SHA,
            "workflow_id": 7001,
            "path": ".github/workflows/qikvrt_autonomous_self_heal.yml",
            "event": "workflow_dispatch",
            "run_number": 9,
            "run_attempt": 1,
        }

        result = self.evaluate(self.snapshot(active_writers=[active_writer]))

        self.assertEqual(result["mesh_disposition"], "WAIT")
        self.assertEqual(result["first_blocker"], "COMPETING_WRITER_ACTIVE")
        self.assertEqual(result["derived_action"]["d0"], 1)
        self.assertEqual(result["derived_action"]["state"], "HOLD")
        self.assertEqual(
            result["derived_action"]["next_action"],
            "WAIT_FOR_SINGLE_WRITER_LEASE",
        )
        self.assertFalse(result["derived_action"]["productive_effect"])

    def test_every_repository_writer_queue_state_is_active(self):
        for status in MODULE.ACTIVE_WRITER_STATES:
            with self.subTest(status=status):
                writer = {
                    "id": 902,
                    "name": "QIK-VRT autonomous bounded self-heal",
                    "status": status,
                    "head_sha": MAIN_SHA,
                    "workflow_id": 7001,
                    "path": ".github/workflows/qikvrt_autonomous_self_heal.yml",
                    "event": "workflow_dispatch",
                    "run_number": 10,
                    "run_attempt": 1,
                }
                result = self.evaluate(self.snapshot(active_writers=[writer]))
                self.assertEqual(result["first_blocker"], "COMPETING_WRITER_ACTIVE")
                self.assertEqual(result["derived_action"]["d0"], 1)

    def test_same_head_changed_gate_attempt_changes_evidence_fingerprint(self):
        first_snapshot = self.snapshot()
        second_snapshot = copy.deepcopy(first_snapshot)
        second_snapshot["workflow_runs"].append(
            self.workflow_run(
                "QIKVRT CI",
                identifier=102,
                run_number=10,
                run_attempt=2,
            )
        )

        first = self.evaluate(first_snapshot)
        second = self.evaluate(second_snapshot)

        self.assertEqual(first["mesh_disposition"], "APPROVE")
        self.assertEqual(second["mesh_disposition"], "APPROVE")
        self.assertNotEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])

    def test_identical_snapshot_has_stable_evidence_fingerprint(self):
        snap = self.snapshot()

        first = self.evaluate(copy.deepcopy(snap))
        second = self.evaluate(copy.deepcopy(snap))

        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])
        self.assertEqual(first["ledger_path"], second["ledger_path"])
        self.assertEqual(first["findings"], second["findings"])

    def test_same_head_every_disposition_input_gets_a_distinct_ledger_path(self):
        baseline = self.evaluate(self.snapshot())
        discussion = {
            "kind": "ISSUE_COMMENT",
            "id": "77",
            "author": "reviewer",
            "author_association": "MEMBER",
            "state": None,
            "commit_id": None,
            "updated_at": "2026-08-22T20:00:00Z",
            "body_sha256": "9" * 64,
        }
        cases = {
            "draft": {"draft": True},
            "reviewer": {"requested_reviewers": ["Goldkelch"]},
            "observed-head": {"observed_head_sha": "9" * 40},
            "declared-scope": {"scope_sha256": "8" * 64},
            "declared-diff": {"diff_sha256": "7" * 64},
            "diff-complete": {"diff_complete": False},
            "discussion": {"discussion_items": [discussion]},
        }
        for label, overrides in cases.items():
            with self.subTest(label=label):
                result = self.evaluate(self.snapshot(**overrides))
                self.assertNotEqual(
                    result["evidence_fingerprint"],
                    baseline["evidence_fingerprint"],
                )
                self.assertNotEqual(result["ledger_path"], baseline["ledger_path"])
                self.assertNotEqual(
                    result["receipt_payload_sha256"],
                    baseline["receipt_payload_sha256"],
                )

    def test_reobservation_compares_fingerprint_and_receipt_payload(self):
        expected = self.evaluate(self.snapshot())
        changed = self.snapshot(draft=True)
        with mock.patch.object(
            MODULE,
            "observe_repository",
            return_value=(changed, DEFAULT_DIFF_BYTES),
        ):
            report, fresh, observed_diff = MODULE.verify_current_receipt(
                expected,
                MODULE._pretty_json_bytes(expected),
                DEFAULT_DIFF_BYTES,
                "example/qik-vrt",
                349,
                999,
                list(REQUIRED_GATE_PATHS),
                REQUIRED_GATE_PATHS,
                [],
            )
        self.assertFalse(report["exact"])
        self.assertEqual(report["state"], "HOLD_UNVERIFIED")
        self.assertEqual(report["first_blocker"], "CAUSAL_REVIEW_EVIDENCE_DRIFT")
        self.assertNotEqual(fresh["evidence_fingerprint"], expected["evidence_fingerprint"])
        self.assertEqual(observed_diff, DEFAULT_DIFF_BYTES)

    def test_reobservation_rejects_tampered_receipt_or_stored_diff(self):
        snapshot = self.snapshot()
        expected = self.evaluate(snapshot)
        tampered = copy.deepcopy(expected)
        tampered["detail"] = "tampered ledger receipt"
        cases = {
            "receipt": (tampered, DEFAULT_DIFF_BYTES, "expected_receipt_self_seal"),
            "diff": (expected, DEFAULT_DIFF_BYTES + b"tampered", "stored_diff_bytes"),
        }
        for label, (receipt, stored_diff, failed_check) in cases.items():
            with self.subTest(label=label), mock.patch.object(
                MODULE,
                "observe_repository",
                return_value=(snapshot, DEFAULT_DIFF_BYTES),
            ):
                report, _fresh, _diff = MODULE.verify_current_receipt(
                    receipt,
                    MODULE._pretty_json_bytes(receipt),
                    stored_diff,
                    "example/qik-vrt",
                    349,
                    999,
                    list(REQUIRED_GATE_PATHS),
                    REQUIRED_GATE_PATHS,
                    [],
                )
            self.assertFalse(report["exact"])
            self.assertFalse(report["checks"][failed_check])

    def test_reobservation_rejects_semantically_identical_receipt_bytes(self):
        snapshot = self.snapshot()
        expected = self.evaluate(snapshot)
        minified = json.dumps(
            expected, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertNotEqual(minified, MODULE._pretty_json_bytes(expected))

        with mock.patch.object(
            MODULE,
            "observe_repository",
            return_value=(snapshot, DEFAULT_DIFF_BYTES),
        ):
            report, _fresh, _diff = MODULE.verify_current_receipt(
                expected,
                minified,
                DEFAULT_DIFF_BYTES,
                "example/qik-vrt",
                349,
                999,
                list(REQUIRED_GATE_PATHS),
                REQUIRED_GATE_PATHS,
                [],
            )

        self.assertFalse(report["exact"])
        self.assertTrue(report["checks"]["expected_receipt_self_seal"])
        self.assertTrue(report["checks"]["stored_receipt_parses_as_expected"])
        self.assertFalse(report["checks"]["stored_receipt_bytes"])

    def test_own_mesh_projection_is_excluded_from_causal_discussion(self):
        own = {
            "id": 1,
            "body": "<!-- qikvrt-mesh-review:v1 head=abc -->",
            "user": {"login": "github-actions[bot]"},
            "submitted_at": "2026-08-22T20:00:00Z",
            "state": "COMMENTED",
        }
        foreign = {
            "id": 2,
            "body": "Please re-check the invariant.",
            "user": {"login": "reviewer"},
            "created_at": "2026-08-22T20:01:00Z",
            "author_association": "MEMBER",
        }

        def pages(endpoint):
            if endpoint.endswith("/reviews?per_page=100"):
                return [own]
            if endpoint.endswith("/comments?per_page=100") and "/issues/" in endpoint:
                return [foreign]
            return []

        with mock.patch.object(MODULE, "_gh_pages", side_effect=pages):
            observed = MODULE._discussion_observation("example/qik-vrt", 349)
        self.assertEqual([item["id"] for item in observed], ["2"])

    def test_status_dedup_considers_only_latest_context_projection(self):
        fingerprint = "a" * 64
        approved = {
            "id": 10,
            "context": "QIKVRT requested review execution",
            "state": "success",
            "created_at": "2026-08-22T10:00:00Z",
            "description": f"Mesh APPROVE; D0=3; fp={fingerprint}",
        }
        waiting = {
            "id": 11,
            "context": "QIKVRT requested review execution",
            "state": "pending",
            "created_at": "2026-08-22T10:01:00Z",
            "description": f"Mesh WAIT; D0=1; fp={'b' * 64}",
        }
        reapproved = {
            **approved,
            "id": 12,
            "created_at": "2026-08-22T10:02:00Z",
        }

        self.assertTrue(
            MODULE.latest_status_matches_projection(
                [approved], approved["context"], "success", fingerprint
            )
        )
        self.assertFalse(
            MODULE.latest_status_matches_projection(
                [approved, waiting], approved["context"], "success", fingerprint
            )
        )
        self.assertTrue(
            MODULE.latest_status_matches_projection(
                [approved, waiting, reapproved],
                approved["context"],
                "success",
                fingerprint,
            )
        )

    def test_exact_diff_bytes_ignore_ambient_git_diff_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)

            def git(*arguments: str) -> str:
                return subprocess.check_output(
                    ["git", *arguments], cwd=repository, text=True
                ).strip()

            git("init", "-q")
            git("config", "user.name", "QIKVRT Test")
            git("config", "user.email", "qikvrt@example.invalid")
            (repository / "a.txt").write_text("a0\na1\na2\n", encoding="utf-8")
            (repository / "b.txt").write_text("b0\nb1\nb2\n", encoding="utf-8")
            git("add", "a.txt", "b.txt")
            git("commit", "-q", "-m", "base")
            base = git("rev-parse", "HEAD")
            (repository / "a.txt").write_text("a0\nchanged\na2\n", encoding="utf-8")
            (repository / "b.txt").write_text("b0\nchanged\nb2\n", encoding="utf-8")
            git("add", "a.txt", "b.txt")
            git("commit", "-q", "-m", "head")
            head = git("rev-parse", "HEAD")

            expected = MODULE._canonical_git_diff(base, head, cwd=repository)
            order = repository / "diff-order"
            order.write_text("b.txt\na.txt\n", encoding="utf-8")
            for key, value in (
                ("color.ui", "always"),
                ("diff.noprefix", "true"),
                ("diff.mnemonicPrefix", "true"),
                ("diff.algorithm", "histogram"),
                ("diff.context", "9"),
                ("diff.indentHeuristic", "true"),
                ("diff.orderFile", str(order)),
                ("diff.outputIndicatorNew", ">"),
                ("diff.outputIndicatorOld", "<"),
                ("diff.outputIndicatorContext", "."),
            ):
                git("config", key, value)

            with mock.patch.dict(os.environ, {"GIT_DIFF_OPTS": "-U9"}):
                observed = MODULE._canonical_git_diff(base, head, cwd=repository)

            self.assertEqual(observed, expected)

    def test_append_only_ledger_planner_covers_root_duplicate_append_and_collision(self):
        receipt = b'{"receipt":1}\n'
        diff = b"diff bytes"
        head = "1" * 40

        initialized = MODULE.plan_ledger_update(receipt, diff, None, None, None)
        self.assertEqual(initialized["action"], "INITIALIZE_ORPHAN_ROOT")
        self.assertIsNone(initialized["parent"])

        appended = MODULE.plan_ledger_update(receipt, diff, head, None, None)
        self.assertEqual(appended["action"], "APPEND_FAST_FORWARD")
        self.assertEqual(appended["parent"], head)
        self.assertFalse(appended["force"])

        duplicate = MODULE.plan_ledger_update(receipt, diff, head, receipt, diff)
        self.assertEqual(duplicate["action"], "NOOP_IDENTICAL_RECEIPT")

        for existing_receipt, existing_diff in (
            (receipt, None),
            (None, diff),
            (b"different", diff),
            (receipt, b"different"),
        ):
            with self.subTest(
                existing_receipt=existing_receipt,
                existing_diff=existing_diff,
            ):
                collision = MODULE.plan_ledger_update(
                    receipt, diff, head, existing_receipt, existing_diff
                )
                self.assertEqual(collision["action"], "HOLD")
                self.assertEqual(
                    collision["first_blocker"],
                    "APPEND_ONLY_LEDGER_PATH_COLLISION",
                )
                self.assertEqual(collision["state"], "HOLD_UNVERIFIED")
                self.assertTrue(
                    all(
                        value is False
                        for value in collision["completion_claims"].values()
                    )
                )

    def test_conflict_marker_is_a_deterministic_review_finding(self):
        snap = self.snapshot(diff_payload=CONFLICT_DIFF_BYTES)

        result = self.evaluate(snap, CONFLICT_DIFF_BYTES)
        repeated = self.evaluate(copy.deepcopy(snap), CONFLICT_DIFF_BYTES)

        self.assertEqual(result["mesh_disposition"], "REQUEST_CHANGES")
        self.assertEqual(result["first_blocker"], "MESH_DIFF_CONFLICT_MARKER")
        self.assertIn("MESH_DIFF_CONFLICT_MARKER", self.finding_ids(result))
        self.assertEqual(result["findings"], repeated["findings"])
        self.assertEqual(result["evidence_fingerprint"], repeated["evidence_fingerprint"])
        self.assertEqual(result["derived_action"]["d0"], 1)
        self.assertEqual(result["derived_action"]["state"], "HOLD")
        self.assertFalse(result["derived_action"]["productive_effect"])

    def test_workflow_is_trusted_main_diff_bound_append_only_and_comment_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        core = (ROOT / "tools/qikvrt_requested_review_executor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "converted_to_draft",
            text,
        )
        self.assertIn("issue_comment:", text)
        self.assertIn("pull_request_target:", text)
        self.assertIn("reopened, closed]", text)
        self.assertNotIn("\n  pull_request:\n", text)
        self.assertNotIn("\n  schedule:\n", text)
        self.assertNotIn("BOUNDED_SCHEDULE_ROTATION", text)
        self.assertNotIn("RUN_NUMBER", text)
        self.assertNotIn("_gh_pages", text)
        self.assertIn("select_review_subject", text)
        self.assertIn("qikvrt-mesh-review-selection-", text)
        self.assertIn("EVENT_NAME: ${{ github.event_name }}", text)
        self.assertIn("EVENT_ACTION: ${{ github.event.action || '' }}", text)
        self.assertIn(
            "EVENT_EXPECTED_BASE: ${{ github.event.pull_request.base.sha || '' }}",
            text,
        )
        self.assertIn(
            "EVENT_EXPECTED_MERGE: ${{ github.event.pull_request.merge_commit_sha || '' }}",
            text,
        )
        self.assertIn("REQUESTED_HEAD: ${{ inputs.head || '' }}", text)
        self.assertIn("GITHUB_EVENT_PATH", text)
        self.assertIn("event_payload_sha256", text)
        self.assertIn("qikvrt-review-event-context.json", text)
        self.assertIn("--event-context-file /tmp/qikvrt-review-event-context.json", text)
        self.assertIn("EXPECTED_SELECTOR_HEAD", text)
        self.assertIn('--expected-head "$EXPECTED_SELECTOR_HEAD"', text)
        self.assertNotIn("if not people and not teams", text)
        self.assertIn("if: github.ref == 'refs/heads/main'", text)
        self.assertIn("ref: main", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn('"--no-ext-diff", "--no-textconv", "--no-renames"', core)
        self.assertIn('"diff", "--name-status", "-z", "--no-renames"', core)
        self.assertIn("REVIEW_INTAKE_SCHEMA", core)
        self.assertIn("GITHUB_ACTIONS_NO_CROSS_EVENT_PRIORITY_GUARANTEE", core)
        self.assertIn("REQUIRED_GATE_PATHS_JSON", text)
        self.assertIn("refs/heads/qikvrt/mesh-review-ledger-v1", text)
        self.assertIn("'force':False", text)
        self.assertIn("existing_diff=blob_at(diff_path,ledger_head)", text)
        self.assertIn("prepare_diff_transport_ledger_entries", core)
        self.assertIn("prepare_diff_transport_ledger_entries", text)
        self.assertIn(
            "prepare_diff_transport_ledger_entries,\n"
            "              reassemble_diff_transport,",
            text,
        )
        self.assertIn("blob_at(diff_path,commit) != _pretty_json_bytes(transport)", text)
        self.assertIn("'parents':[]", text)
        self.assertIn("pre-ledger-cas", text)
        self.assertIn("post-ledger-cas", text)
        self.assertIn("pre-review-comment", text)
        self.assertIn("post-status", text)
        self.assertIn("event=COMMENT", text)
        self.assertNotIn("event=APPROVE", text)
        self.assertNotIn("event=REQUEST_CHANGES", text)
        self.assertNotIn("<<EOF", text)
        self.assertNotIn("git push", text)
        self.assertIn("if-no-files-found: error", text)
        self.assertIn("include-hidden-files: true", text)
        self.assertIn("latest_status_matches_projection", text)
        self.assertIn("D0: ${{ steps.ledger.outputs.d0 }}", text)
        self.assertIn(
            "NEXT_ACTION: ${{ steps.ledger.outputs.next_action }}",
            text,
        )
        self.assertNotIn("D0: ${{ steps.decision.outputs.d0 }}", text)
        self.assertNotIn(
            "NEXT_ACTION: ${{ steps.decision.outputs.next_action }}",
            text,
        )
        self.assertIn("HOLD_UNVERIFIED", text)
        self.assertIn("independent Code-Owner approval: **not implied**", text)
        observer = OBSERVER_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("PULL_REQUEST_BASE_NOT_MAIN", observer)
        self.assertIn("INELIGIBLE_EVENT_TARGET", observer)
        self.assertNotIn("BLOCK: pull request is not based on main", observer)
        self.assertIn(
            "- qikvrt/mesh-review-ledger-v1",
            CI_WORKFLOW.read_text(encoding="utf-8"),
        )

    def test_exact_event_selection_is_diagnostic_and_fail_closed(self):
        cases = {
            "not-open": (
                self.selector_pr(state="closed"),
                "PULL_REQUEST_NOT_OPEN",
            ),
            "not-main": (
                self.selector_pr(base={"ref": "agent/qikvrt-mesh-heartbeat-v1"}),
                "PULL_REQUEST_BASE_NOT_MAIN",
            ),
            "foreign-head": (
                self.selector_pr(head={"sha": HEAD_SHA, "repo": {"full_name": "fork/qik-vrt"}}),
                "PULL_REQUEST_HEAD_NOT_ROLE_LOCAL",
            ),
        }
        for label, (observed, expected_reason) in cases.items():
            with self.subTest(label=label):
                fetches: list[int] = []

                def fetch(number):
                    fetches.append(number)
                    return observed

                result = MODULE.select_review_subject(
                    repository="example/qik-vrt",
                    requested_pr="",
                    event_pr="867",
                    event_name="pull_request_target",
                    expected_head=HEAD_SHA,
                    workflow_event="",
                    workflow_prs=[],
                    fetch_pull_request=fetch,
                )
                self.assertEqual(fetches, [867])
                self.assertEqual(result["state"], "INELIGIBLE_EVENT_TARGET")
                self.assertEqual(result["pr_number"], 867)
                self.assertIsNone(result["candidate_pr_number"])
                self.assertEqual(result["first_blocker"], expected_reason)
                self.assertIn(expected_reason, result["eligibility_reasons"])
                self.assertFalse(result["review_execution"])
                self.assertFalse(result["review_observation_started"])
                self.assertEqual(result["external_effect"], "NONE")
                self.assertTrue(all(value is False for value in result["completion_claims"].values()))
                self.assertEqual(
                    result["observed_subject"]["base_ref"], observed["base"]["ref"]
                )

    def test_closed_merge_adoption_is_exact_and_never_executes_review(self):
        observed = self.selector_pr(
            state="closed",
            merged=True,
            merge_commit_sha=MERGE_SHA,
        )
        fetched_commits: list[str] = []

        def fetch_commit(sha):
            fetched_commits.append(sha)
            return {
                MAIN_SHA: self.git_commit(MAIN_SHA, BASE_TREE_SHA),
                HEAD_SHA: self.git_commit(HEAD_SHA, HEAD_TREE_SHA),
                MERGE_SHA: self.git_commit(
                    MERGE_SHA,
                    HEAD_TREE_SHA,
                    (MAIN_SHA, HEAD_SHA),
                ),
            }[sha]

        result = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="pull_request_target",
            event_action="closed",
            expected_head=HEAD_SHA,
            expected_base=MAIN_SHA,
            expected_merge=MERGE_SHA,
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: observed,
            fetch_git_commit=fetch_commit,
        )

        self.assertEqual(fetched_commits, [MAIN_SHA, HEAD_SHA, MERGE_SHA])
        self.assertEqual(result["state"], "MERGE_ADOPTION_REOBSERVED")
        self.assertEqual(result["selection_basis"], "EXACT_CLOSED_MERGE_ADOPTION")
        self.assertEqual(result["pr_number"], 867)
        self.assertIsNone(result["candidate_pr_number"])
        self.assertTrue(result["adoption_reobservation"])
        self.assertFalse(result["review_execution"])
        self.assertFalse(result["review_observation_started"])
        self.assertEqual(result["external_effect"], "NONE")
        self.assertEqual(
            result["observed_subject"]["merge_parents"],
            [MAIN_SHA, HEAD_SHA],
        )
        self.assertEqual(
            result["observed_subject"]["merge_tree_sha"], HEAD_TREE_SHA
        )
        self.assertEqual(
            result["observed_subject"]["head_tree_sha"], HEAD_TREE_SHA
        )
        self.assertTrue(
            all(value is False for value in result["completion_claims"].values())
        )

    def test_closed_merge_adoption_fails_closed_on_history_or_tree_drift(self):
        observed = self.selector_pr(
            state="closed",
            merged=True,
            merge_commit_sha=MERGE_SHA,
        )
        cases = {
            "history": (
                self.git_commit(MERGE_SHA, HEAD_TREE_SHA, (HEAD_SHA, MAIN_SHA)),
                "MERGE_ADOPTION_PARENT_HISTORY_MISMATCH",
            ),
            "tree": (
                self.git_commit(MERGE_SHA, "f" * 40, (MAIN_SHA, HEAD_SHA)),
                "MERGE_ADOPTION_CANDIDATE_TREE_MISMATCH",
            ),
        }
        for label, (merge_commit, blocker) in cases.items():
            with self.subTest(label=label):
                commits = {
                    MAIN_SHA: self.git_commit(MAIN_SHA, BASE_TREE_SHA),
                    HEAD_SHA: self.git_commit(HEAD_SHA, HEAD_TREE_SHA),
                    MERGE_SHA: merge_commit,
                }
                result = MODULE.select_review_subject(
                    repository="example/qik-vrt",
                    requested_pr="",
                    event_pr="867",
                    event_name="pull_request_target",
                    event_action="closed",
                    expected_head=HEAD_SHA,
                    expected_base=MAIN_SHA,
                    expected_merge=MERGE_SHA,
                    workflow_event="",
                    workflow_prs=[],
                    fetch_pull_request=lambda number: observed,
                    fetch_git_commit=lambda sha: commits[sha],
                )
                self.assertEqual(result["state"], "INELIGIBLE_EVENT_TARGET")
                self.assertEqual(result["first_blocker"], blocker)
                self.assertFalse(result["review_execution"])
                self.assertFalse(result["adoption_reobservation"])

    def test_closed_unmerged_event_is_not_a_review_candidate(self):
        result = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="pull_request_target",
            event_action="closed",
            expected_head=HEAD_SHA,
            expected_base=MAIN_SHA,
            expected_merge="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.selector_pr(
                number=number,
                state="closed",
                merged=False,
                merge_commit_sha=None,
            ),
        )
        self.assertEqual(result["state"], "INELIGIBLE_EVENT_TARGET")
        self.assertEqual(result["first_blocker"], "PULL_REQUEST_CLOSED_WITHOUT_MERGE")
        self.assertFalse(result["review_execution"])
        self.assertFalse(result["adoption_reobservation"])

    def test_closed_merge_adoption_requires_event_base_and_merge_binding(self):
        observed = self.selector_pr(
            state="closed",
            merged=True,
            merge_commit_sha=MERGE_SHA,
        )
        missing_base = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="pull_request_target",
            event_action="closed",
            expected_head=HEAD_SHA,
            expected_base="",
            expected_merge=MERGE_SHA,
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.fail("missing base must not fetch"),
        )
        self.assertEqual(missing_base["first_blocker"], "PULL_REQUEST_EVENT_BASE_MISSING")

        missing_merge = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="pull_request_target",
            event_action="closed",
            expected_head=HEAD_SHA,
            expected_base=MAIN_SHA,
            expected_merge="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: observed,
        )
        self.assertEqual(
            missing_merge["first_blocker"],
            "PULL_REQUEST_EVENT_MERGE_COMMIT_MISSING",
        )
        self.assertFalse(missing_merge["review_execution"])

    def test_exact_event_selection_accepts_only_one_eligible_subject(self):
        result = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="pull_request_target",
            expected_head=HEAD_SHA,
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.selector_pr(number=number),
        )
        self.assertEqual(result["state"], "CANDIDATE")
        self.assertEqual(result["pr_number"], 867)
        self.assertTrue(result["review_execution"])
        self.assertEqual(result["eligibility_reasons"], [])

    def test_invalid_conflicting_or_unobservable_exact_target_never_executes(self):
        invalid = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="not-a-number",
            event_pr="",
            event_name="workflow_dispatch",
            expected_head="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.fail("invalid token must not fetch"),
        )
        self.assertEqual(invalid["state"], "INELIGIBLE_EVENT_TARGET")
        self.assertEqual(invalid["first_blocker"], "INVALID_EXACT_PULL_REQUEST_NUMBER")

        conflict = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="867",
            event_pr="868",
            event_name="workflow_dispatch",
            expected_head="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.fail("conflicting targets must not fetch"),
        )
        self.assertEqual(conflict["state"], "AMBIGUOUS_EVENT_SUBJECT")
        self.assertEqual(
            conflict["first_blocker"], "CONFLICTING_EXACT_PULL_REQUEST_SUBJECTS"
        )

        unavailable = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="pull_request_target",
            expected_head=HEAD_SHA,
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: (_ for _ in ()).throw(
                MODULE.ReviewObservationError("GitHub API unavailable")
            ),
        )
        self.assertEqual(unavailable["state"], "REOBSERVE_EXACT_EVENT_TARGET")
        self.assertEqual(
            unavailable["first_blocker"], "PULL_REQUEST_OBSERVATION_UNAVAILABLE"
        )
        self.assertFalse(unavailable["review_execution"])

        missing_head = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="pull_request_target",
            expected_head="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.fail("missing event head must not fetch"),
        )
        self.assertEqual(missing_head["state"], "REOBSERVE_EXACT_EVENT_TARGET")
        self.assertEqual(
            missing_head["first_blocker"], "PULL_REQUEST_EVENT_HEAD_MISSING"
        )

        issue_comment = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="issue_comment",
            expected_head="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.selector_pr(number=number),
        )
        self.assertEqual(issue_comment["state"], "CANDIDATE")

        unsupported = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="workflow_run",
            expected_head="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.fail("unsupported source must not fetch"),
        )
        self.assertEqual(unsupported["state"], "INELIGIBLE_EVENT_TARGET")
        self.assertEqual(
            unsupported["first_blocker"], "UNSUPPORTED_EXACT_EVENT_SOURCE"
        )

    def test_explicit_dispatch_requires_the_exact_head(self):
        missing = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="867",
            event_pr="",
            event_name="workflow_dispatch",
            expected_head="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.fail("missing head must not fetch"),
        )
        self.assertEqual(missing["state"], "REOBSERVE_EXACT_EVENT_TARGET")
        self.assertEqual(missing["first_blocker"], "WORKFLOW_DISPATCH_HEAD_MISSING")

        exact = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="867",
            event_pr="",
            event_name="workflow_dispatch",
            expected_head=HEAD_SHA,
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.selector_pr(number=number),
        )
        self.assertEqual(exact["state"], "CANDIDATE")
        self.assertEqual(exact["expected_head"], HEAD_SHA)

    def test_exact_selector_head_is_enforced_before_repository_observation(self):
        with mock.patch.object(
            MODULE,
            "_gh_one",
            return_value={"head": {"sha": HEAD_SHA}},
        ) as observed:
            with self.assertRaisesRegex(
                MODULE.ReviewObservationError,
                "exact selector event",
            ):
                MODULE.observe_repository(
                    "example/qik-vrt",
                    867,
                    1,
                    [],
                    {},
                    [],
                    expected_head="a" * 40,
                )
        self.assertEqual(observed.call_count, 1)

    def test_eventless_selection_never_enumerates_or_executes_review(self):
        result = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="",
            event_name="issue_comment",
            expected_head="",
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.fail("no event must not fetch a pull request"),
        )
        self.assertEqual(result["state"], "NO_EVENT_SUBJECT")
        self.assertEqual(result["first_blocker"], "NO_EXACT_EVENT_OR_DISPATCH_SUBJECT")
        self.assertFalse(result["review_execution"])

    def test_ambiguous_workflow_run_never_selects_one_pr_arbitrarily(self):
        result = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="",
            event_name="workflow_run",
            expected_head=HEAD_SHA,
            workflow_event="pull_request",
            workflow_prs=[
                {"number": 41, "url": "https://api.github.com/repos/example/qik-vrt/pulls/41"},
                {"number": 42, "url": "https://api.github.com/repos/example/qik-vrt/pulls/42"},
            ],
            fetch_pull_request=lambda number: self.fail("ambiguous event must not fetch a pull request"),
        )
        self.assertEqual(result["state"], "AMBIGUOUS_EVENT_SUBJECT")
        self.assertEqual(result["first_blocker"], "WORKFLOW_RUN_MULTIPLE_PULL_REQUESTS")
        self.assertFalse(result["review_execution"])

    def test_workflow_run_selection_is_repo_head_and_event_bound(self):
        same_repository_event = [
            {
                "number": 867,
                "url": "https://api.github.com/repos/example/qik-vrt/pulls/867",
            }
        ]
        candidate = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="",
            event_name="workflow_run",
            expected_head=HEAD_SHA,
            workflow_event="pull_request",
            workflow_prs=same_repository_event,
            fetch_pull_request=lambda number: self.selector_pr(number=number),
        )
        self.assertEqual(candidate["state"], "CANDIDATE")

        cross_repository = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="",
            event_name="workflow_run",
            expected_head=HEAD_SHA,
            workflow_event="pull_request",
            workflow_prs=[
                {
                    "number": 867,
                    "url": "https://api.github.com/repos/other/qik-vrt/pulls/867",
                }
            ],
            fetch_pull_request=lambda number: self.fail("cross-repository event must not fetch"),
        )
        self.assertEqual(cross_repository["state"], "INELIGIBLE_EVENT_TARGET")
        self.assertEqual(
            cross_repository["first_blocker"],
            "WORKFLOW_RUN_PULL_REQUEST_NOT_ROLE_LOCAL",
        )

        scheduled = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="",
            event_name="workflow_run",
            expected_head=HEAD_SHA,
            workflow_event="schedule",
            workflow_prs=same_repository_event,
            fetch_pull_request=lambda number: self.fail("scheduled event must not fetch"),
        )
        self.assertEqual(scheduled["state"], "INELIGIBLE_EVENT_TARGET")
        self.assertEqual(
            scheduled["first_blocker"], "SCHEDULED_OR_MANUAL_WORKFLOW_RUN_FORBIDDEN"
        )

        drifted = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="",
            event_name="workflow_run",
            expected_head=HEAD_SHA,
            workflow_event="pull_request",
            workflow_prs=same_repository_event,
            fetch_pull_request=lambda number: self.selector_pr(
                number=number,
                head={"sha": "a" * 40, "repo": {"full_name": "example/qik-vrt"}},
            ),
        )
        self.assertEqual(drifted["state"], "REOBSERVE_EXACT_EVENT_TARGET")
        self.assertEqual(drifted["first_blocker"], "EVENT_TARGET_HEAD_DRIFT")

    def test_every_workflow_shell_and_embedded_python_block_parses(self):
        workflows = [
            WORKFLOW,
            PROMOTION_WORKFLOW,
            OBSERVER_WORKFLOW,
            REQUIRED_REVIEW_GATE_WORKFLOW,
        ]
        for workflow in workflows:
            with self.subTest(workflow=workflow.name):
                lines = workflow.read_text(encoding="utf-8").splitlines()
                run_blocks: list[str] = []
                index = 0
                while index < len(lines):
                    if lines[index].startswith("        run: |"):
                        index += 1
                        block: list[str] = []
                        while index < len(lines):
                            line = lines[index]
                            if line and not line.startswith("          "):
                                break
                            block.append(line[10:] if line.startswith("          ") else "")
                            index += 1
                        run_blocks.append("\n".join(block) + "\n")
                        continue
                    index += 1

                self.assertTrue(run_blocks)
                for number, block in enumerate(run_blocks, start=1):
                    completed = subprocess.run(
                        ["bash", "-n"],
                        input=block,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        f"{workflow.name} run block {number}: {completed.stderr}",
                    )

                    block_lines = block.splitlines()
                    cursor = 0
                    while cursor < len(block_lines):
                        if block_lines[cursor].startswith("python3 -B - <<'PY'"):
                            cursor += 1
                            source: list[str] = []
                            while cursor < len(block_lines) and block_lines[cursor] != "PY":
                                source.append(block_lines[cursor])
                                cursor += 1
                            self.assertLess(
                                cursor,
                                len(block_lines),
                                f"{workflow.name} run block {number}: unterminated Python heredoc",
                            )
                            compile(
                                "\n".join(source) + "\n",
                                f"{workflow.name}-run-{number}",
                                "exec",
                            )
                        cursor += 1


    def test_submitted_pull_request_review_selects_one_exact_subject(self):
        result = MODULE.select_review_subject(
            repository="example/qik-vrt",
            requested_pr="",
            event_pr="867",
            event_name="pull_request_review",
            expected_head=HEAD_SHA,
            workflow_event="",
            workflow_prs=[],
            fetch_pull_request=lambda number: self.selector_pr(number=number),
        )
        self.assertEqual(result["state"], "CANDIDATE")
        self.assertEqual(result["event_source"], "PULL_REQUEST_EVENT")
        self.assertEqual(result["expected_head"], HEAD_SHA)


if __name__ == "__main__":
    unittest.main()
