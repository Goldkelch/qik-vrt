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

    def test_pr_890_sized_diff_is_reviewable_and_uses_three_chunk_transport(self):
        exact_pr_890_bytes = 2_186_648
        diff = DEFAULT_DIFF_BYTES + b"+bounded-review-byte\n" * 100_000
        diff = (diff + b"+" * exact_pr_890_bytes)[:exact_pr_890_bytes]
        self.assertEqual(len(diff), exact_pr_890_bytes)

        result = self.evaluate(self.snapshot(diff_payload=diff), diff)

        self.assertNotEqual(result["first_blocker"], "REVIEW_BYTES_UNAVAILABLE")
        self.assertEqual(result["diff_bytes"], exact_pr_890_bytes)
        self.assertEqual(result["ledger_diff_format"], MODULE.DIFF_MANIFEST_SCHEMA)
        manifest, chunks = MODULE.build_diff_transport(
            diff, result["ledger_diff_path"]
        )
        parsed = json.loads(manifest)
        self.assertEqual(parsed["chunk_count"], 3)
        self.assertEqual(
            [chunk["bytes"] for chunk in parsed["chunks"]],
            [1_048_576, 1_048_576, 89_496],
        )
        self.assertEqual(
            MODULE.load_ledger_diff(result, manifest, chunks.get),
            diff,
        )

    def test_manifest_is_fully_validated_before_any_chunk_fetch(self):
        diff = b"a" * (MODULE.DIFF_CHUNK_BYTES + 7)
        receipt = self.evaluate(self.snapshot(diff_payload=diff), diff)
        manifest_bytes, chunks = MODULE.build_diff_transport(
            diff, receipt["ledger_diff_path"]
        )
        original = json.loads(manifest_bytes)

        invalid_manifests = []
        missing = copy.deepcopy(original)
        missing["chunks"].pop()
        invalid_manifests.append(MODULE._canonical_bytes(missing))
        duplicate = copy.deepcopy(original)
        duplicate["chunks"][1]["index"] = 0
        invalid_manifests.append(MODULE._canonical_bytes(duplicate))
        reordered = copy.deepcopy(original)
        reordered["chunks"].reverse()
        invalid_manifests.append(MODULE._canonical_bytes(reordered))
        oversized = copy.deepcopy(original)
        oversized["chunks"][0]["bytes"] = MODULE.DIFF_CHUNK_BYTES + 1
        invalid_manifests.append(MODULE._canonical_bytes(oversized))
        boolean_index = copy.deepcopy(original)
        boolean_index["chunks"][0]["index"] = False
        invalid_manifests.append(MODULE._canonical_bytes(boolean_index))
        wrong_path = copy.deepcopy(original)
        wrong_path["chunks"][0]["path"] = "state/mesh/reviews/injected"
        invalid_manifests.append(MODULE._canonical_bytes(wrong_path))
        too_many = copy.deepcopy(original)
        too_many["chunk_count"] = MODULE.MAX_DIFF_CHUNKS + 1
        invalid_manifests.append(MODULE._canonical_bytes(too_many))
        invalid_manifests.append(
            b'{"chunk_count":2,' + manifest_bytes[1:]
        )
        invalid_manifests.append(json.dumps(original, indent=2).encode("utf-8"))

        for invalid in invalid_manifests:
            with self.subTest(invalid=invalid[:80]):
                fetched = []
                with self.assertRaises(MODULE.ReviewSnapshotError):
                    MODULE.load_ledger_diff(
                        receipt,
                        invalid,
                        lambda path: fetched.append(path) or chunks.get(path),
                    )
                self.assertEqual(fetched, [])

    def test_chunk_and_full_digest_mismatches_fail_closed(self):
        diff = b"a" * (MODULE.DIFF_CHUNK_BYTES + 7)
        receipt = self.evaluate(self.snapshot(diff_payload=diff), diff)
        manifest, chunks = MODULE.build_diff_transport(
            diff, receipt["ledger_diff_path"]
        )
        first_path = next(iter(chunks))
        tampered = dict(chunks)
        tampered[first_path] = b"b" + tampered[first_path][1:]

        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "chunk digest mismatch"
        ):
            MODULE.load_ledger_diff(receipt, manifest, tampered.get)
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "chunk bytes are unavailable"
        ):
            MODULE.load_ledger_diff(receipt, manifest, lambda _path: None)

        wrong_digest = "f" * 64
        wrong_receipt = dict(receipt, diff_sha256=wrong_digest)
        wrong_manifest = json.loads(manifest)
        wrong_manifest["diff_sha256"] = wrong_digest
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "reassembled ledger diff digest mismatch"
        ):
            MODULE.load_ledger_diff(
                wrong_receipt,
                MODULE._canonical_bytes(wrong_manifest),
                chunks.get,
            )

    def test_legacy_raw_diff_is_supported_only_without_format_marker(self):
        diff = DEFAULT_DIFF_BYTES
        receipt = self.evaluate()
        legacy = dict(receipt)
        legacy.pop("ledger_diff_format")
        fetched = []

        self.assertEqual(
            MODULE.load_ledger_diff(
                legacy, diff, lambda path: fetched.append(path) or None
            ),
            diff,
        )
        self.assertEqual(fetched, [])
        with self.assertRaises(MODULE.ReviewSnapshotError):
            MODULE.load_ledger_diff(receipt, diff, lambda _path: None)
        explicit_null = dict(legacy, ledger_diff_format=None)
        with self.assertRaises(MODULE.ReviewSnapshotError):
            MODULE.load_ledger_diff(explicit_null, diff, lambda _path: None)

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
        self.assertNotIn("\n  pull_request:\n", text)
        self.assertNotIn("if not people and not teams", text)
        self.assertIn("if: github.ref == 'refs/heads/main'", text)
        self.assertIn("ref: main", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn('"--no-ext-diff", "--no-textconv", "--no-renames"', core)
        self.assertIn('"diff", "--name-status", "-z", "--no-renames"', core)
        self.assertIn("REQUIRED_GATE_PATHS_JSON", text)
        self.assertIn("refs/heads/qikvrt/mesh-review-ledger-v1", text)
        self.assertIn("'force':False", text)
        self.assertIn("existing_diff=blob_at(diff_path,ledger_head)", text)
        self.assertIn("build_diff_transport(diff_bytes,diff_path)", text)
        self.assertIn("readback_diff(commit) != diff_bytes", text)
        self.assertIn("APPEND_ONLY_LEDGER_CHUNK_PATH_COLLISION", text)
        self.assertIn("load_ledger_diff(receipt,stored_diff,ledger_bytes)", PROMOTION_WORKFLOW.read_text(encoding="utf-8"))
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
        self.assertIn(
            "- qikvrt/mesh-review-ledger-v1",
            CI_WORKFLOW.read_text(encoding="utf-8"),
        )

    def test_every_workflow_shell_and_embedded_python_block_parses(self):
        workflows = [WORKFLOW, PROMOTION_WORKFLOW, OBSERVER_WORKFLOW]
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


if __name__ == "__main__":
    unittest.main()
