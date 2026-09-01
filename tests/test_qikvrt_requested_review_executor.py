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
LEGACY_FANOUT_WORKFLOW = (
    ROOT / ".github" / "workflows" / "qikvrt_authority_review_report_fanout.yml"
)
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
    def test_github_workflow_expression_tokens_are_line_closed(self):
        offenders = []
        workflows = ROOT / ".github" / "workflows"
        for path in sorted((*workflows.glob("*.yml"), *workflows.glob("*.yaml"))):
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if "${{" in line and "}}" not in line:
                    offenders.append(f"{path.relative_to(ROOT)}:{line_number}")
        self.assertEqual([], offenders)

    def test_review_contract_normalizes_semantic_document_whitespace(self):
        contract = (
            ROOT / ".github" / "workflows" / "qikvrt_requested_review_contract.yml"
        ).read_text(encoding="utf-8")
        documentation = (
            ROOT / "docs" / "DELEGATED_NATIVE_ACCOUNT_REVIEW_AUTOMATION.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "delegated platform-account action",
            " ".join(documentation.split()),
        )
        self.assertIn("tr '\\n' ' '", contract)

    def selector_pr(self, **overrides):
        value = {
            "number": 867,
            "state": "open",
            "base": {"ref": "main"},
            "head": {
                "sha": HEAD_SHA,
                "repo": {"full_name": "example/qik-vrt"},
            },
        }
        value.update(overrides)
        return value

    def mesh_ledger_delegation(self, **receipt_overrides):
        writer_id = 4242
        receipt = {
            "schema": MODULE.MESH_LEDGER_PROTECTION_SCHEMA,
            "repository": "example/qik-vrt",
            "ledger_ref": MODULE.LEDGER_REF,
            "ref_initialized": True,
            "genesis_commit_sha": "9" * 40,
            "ruleset_id": 19344903,
            "ruleset_name": "QIKVRT Mesh review ledger writer",
            "ruleset_enforcement": "active",
            "ruleset_source_type": "Repository",
            "ruleset_source": "example/qik-vrt",
            "ruleset_target": "branch",
            "ref_name_include": [MODULE.LEDGER_REF],
            "ref_name_exclude": [],
            "required_rule_types": ["deletion", "non_fast_forward", "update"],
            "writer_integration_id": writer_id,
            "writer_app_slug": "qikvrt-outbox-ledger-authority",
            "sole_bypass_actors": [
                {
                    "actor_id": writer_id,
                    "actor_type": "Integration",
                    "bypass_mode": "always",
                }
            ],
            "writer_workflow_path": MODULE.TRUSTED_WORKFLOW_PATH,
            "writer_environment": MODULE.MESH_LEDGER_AUTHORITY_ENVIRONMENT,
            "writer_secret_name": MODULE.MESH_LEDGER_WRITER_SECRET,
            "repository_scope_secret_names_absent": list(
                MODULE.MESH_LEDGER_FORBIDDEN_BROAD_SECRET_NAMES
            ),
            "repository_owner": {
                "login": "example",
                "id": 1001,
                "type": "User",
            },
            "organization_scope_secret_names_absent": [],
            "organization_scope_readback": "NOT_APPLICABLE_USER_OWNER",
            "settings_readback_complete": True,
            "verified_at": "2026-09-01T10:00:00Z",
            "verifier_login": "authority-admin",
        }
        receipt.update(receipt_overrides)
        return {
            "schema": MODULE.MESH_LEDGER_DELEGATION_SCHEMA,
            "delegation_id": MODULE.MESH_LEDGER_DELEGATION_ID,
            "state": "ACTIVE",
            "repositories": ["example/qik-vrt"],
            "ledger_authority_boundary": {
                "environment": MODULE.MESH_LEDGER_AUTHORITY_ENVIRONMENT,
                "credential": MODULE.MESH_LEDGER_WRITER_SECRET,
                "credential_scope": "ENVIRONMENT_ONLY",
                "external_configuration_verified": True,
                "external_readback_receipts": [receipt],
            },
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

    def test_clean_exact_mesh_review_without_requested_reviewer_continues(self):
        result = self.evaluate()

        self.assert_receipt_boundaries(result)
        self.assertEqual(result["mesh_disposition"], "TECHNICAL_CONTINUE")
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
                self.assertEqual(
                    result["review_intake"], MODULE._semantic_review_intake(intake)
                )
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

    def test_initial_transport_zero_sentinel_is_not_a_mesh_predecessor(self):
        intake = MODULE._review_intake(
            {
                "source": "WORKFLOW_DISPATCH_PR",
                "event_name": "workflow_dispatch",
                "predecessor_successor_fingerprint": "0" * 64,
                "transport_intent_sha256": "a" * 64,
                "transport_attempt": 1,
            },
            [],
        )
        self.assertIsNone(intake["predecessor_successor_fingerprint"])
        self.assertEqual(intake["transport_intent_sha256"], "a" * 64)
        self.assertEqual(intake["transport_attempt"], 1)
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "transport locator is incomplete"
        ):
            MODULE._review_intake(
                {
                    "event_name": "workflow_dispatch",
                    "transport_intent_sha256": "a" * 64,
                },
                [],
            )

    def test_event_payload_digest_is_transport_provenance_not_semantics(self):
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
        self.assertEqual(
            first_result["evidence_fingerprint"],
            second_result["evidence_fingerprint"],
        )
        self.assertNotEqual(
            MODULE.build_review_transport_provenance(first)["provenance_payload_sha256"],
            MODULE.build_review_transport_provenance(second)["provenance_payload_sha256"],
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
        self.assertEqual(result["mesh_disposition"], "TECHNICAL_CONTINUE")
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
        self.assertEqual(plan["action"], "HOLD")
        self.assertEqual(
            plan["first_blocker"],
            "MESH_REVIEW_LEDGER_EXTERNAL_GENESIS_REQUIRED",
        )
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
        self.assertEqual(result["mesh_disposition"], "TECHNICAL_CONTINUE")
        self.assertEqual(probe["conclusion"], "skipped")
        self.assertEqual(probe["jobs"][0]["conclusion"], "skipped")

    def test_job_result_is_semantic_but_job_id_is_provenance(self):
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
                self.assertEqual(result["mesh_disposition"], "TECHNICAL_CONTINUE")
                assertion = self.assertEqual if label == "id" else self.assertNotEqual
                assertion(result["evidence_fingerprint"], first["evidence_fingerprint"])
                self.assertEqual(
                    next(
                        run
                        for run in result["latest_workflows"]
                        if run["name"] == "QIKVRT CI"
                    )["jobs"],
                    sorted(
                        [
                            {
                                "status": job["status"],
                                "conclusion": job["conclusion"],
                            }
                            for job in changed_gate["jobs"]
                        ],
                        key=lambda job: (job["status"], str(job["conclusion"])),
                    ),
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

        self.assertEqual(first["mesh_disposition"], "TECHNICAL_CONTINUE")
        self.assertEqual(second["mesh_disposition"], "TECHNICAL_CONTINUE")
        self.assertEqual(len(first["latest_workflows"]), len(snap["workflow_runs"]))
        self.assertEqual(
            first["evidence_fingerprint"], second["evidence_fingerprint"]
        )
        self.assertEqual(
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

    def test_paginated_run_observation_binds_total_and_unique_ids(self):
        pages = [
            {"total_count": 2, "workflow_runs": [{"id": 22}]},
            {"total_count": 2, "workflow_runs": [{"id": 11}]},
        ]
        with mock.patch.object(MODULE, "_run_json", return_value=pages) as run_json:
            runs = MODULE._gh_runs(
                "repos/example/qik-vrt/actions/runs?status=in_progress&per_page=100"
            )
        self.assertEqual([run["id"] for run in runs], [22, 11])
        run_json.assert_called_once_with(
            (
                "gh",
                "api",
                "--paginate",
                "--slurp",
                "repos/example/qik-vrt/actions/runs?status=in_progress&per_page=100",
            )
        )

    def test_incomplete_or_shifted_run_pagination_fails_closed(self):
        cases = (
            (
                [{"total_count": 2, "workflow_runs": [{"id": 11}]}],
                "projection is incomplete",
            ),
            (
                [
                    {"total_count": 2, "workflow_runs": [{"id": 11}]},
                    {"total_count": 2, "workflow_runs": [{"id": 11}]},
                ],
                "invalid or duplicate id",
            ),
            (
                [
                    {"total_count": 2, "workflow_runs": [{"id": 11}]},
                    {"total_count": 3, "workflow_runs": [{"id": 12}]},
                ],
                "total_count changed",
            ),
        )
        for pages, blocker in cases:
            with self.subTest(blocker=blocker), mock.patch.object(
                MODULE, "_run_json", return_value=pages
            ), self.assertRaisesRegex(MODULE.ReviewObservationError, blocker):
                MODULE._gh_runs(
                    "repos/example/qik-vrt/actions/runs?status=in_progress&per_page=100"
                )

    def test_duplicate_job_id_from_page_shift_fails_closed(self):
        pages = [
            {
                "total_count": 2,
                "jobs": [{"id": 11, "status": "completed", "conclusion": "success"}],
            },
            {
                "total_count": 2,
                "jobs": [{"id": 11, "status": "completed", "conclusion": "success"}],
            },
        ]
        with mock.patch.object(MODULE, "_run_json", return_value=pages), self.assertRaisesRegex(
            MODULE.ReviewObservationError, "invalid or duplicate id"
        ):
            MODULE._gh_jobs(
                "repos/example/qik-vrt/actions/runs/7/jobs?per_page=100"
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

    def test_same_head_identical_gate_rerun_does_not_change_semantics(self):
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

        self.assertEqual(first["mesh_disposition"], "TECHNICAL_CONTINUE")
        self.assertEqual(second["mesh_disposition"], "TECHNICAL_CONTINUE")
        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])

    def test_identical_snapshot_has_stable_evidence_fingerprint(self):
        snap = self.snapshot()

        first = self.evaluate(copy.deepcopy(snap))
        second = self.evaluate(copy.deepcopy(snap))

        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])
        self.assertEqual(first["ledger_path"], second["ledger_path"])
        self.assertEqual(first["findings"], second["findings"])

    def test_transport_only_intake_changes_do_not_create_a_successor(self):
        def intake(intent: str, attempt: int, predecessor: str, payload: str):
            return MODULE._review_intake(
                {
                    "source": "WORKFLOW_DISPATCH_PR",
                    "event_name": "workflow_dispatch",
                    "event_action": "",
                    "event_payload_sha256": payload,
                    "event_actor": "github-actions[bot]",
                    "predecessor_successor_fingerprint": predecessor,
                    "transport_intent_sha256": intent,
                    "transport_attempt": attempt,
                    "native_delivery_identity": "UNAVAILABLE_TO_GITHUB_ACTIONS",
                },
                [],
            )

        first_intake = intake("1" * 64, 1, "2" * 64, "3" * 64)
        second_intake = intake("4" * 64, 1, "5" * 64, "6" * 64)
        first = self.evaluate(self.snapshot(review_intake=first_intake))
        second = self.evaluate(self.snapshot(review_intake=second_intake))
        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])
        self.assertEqual(first, second)
        first_provenance = MODULE.build_review_transport_provenance(first_intake)
        second_provenance = MODULE.build_review_transport_provenance(second_intake)
        self.assertNotEqual(
            first_provenance["provenance_payload_sha256"],
            second_provenance["provenance_payload_sha256"],
        )

    def test_identical_gate_result_rerun_ids_are_provenance_not_semantics(self):
        first_snapshot = self.snapshot()
        second_snapshot = copy.deepcopy(first_snapshot)
        replacement = self.workflow_run(
            "QIKVRT CI",
            identifier=9101,
            run_number=99,
            run_attempt=2,
        )
        second_snapshot["workflow_runs"][0] = replacement
        first = self.evaluate(first_snapshot)
        second = self.evaluate(second_snapshot)
        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])
        self.assertEqual(first, second)
        first_provenance = MODULE.build_review_transport_provenance(
            None, workflow_runs=first_snapshot["workflow_runs"]
        )
        second_provenance = MODULE.build_review_transport_provenance(
            None, workflow_runs=second_snapshot["workflow_runs"]
        )
        self.assertNotEqual(
            first_provenance["provenance_payload_sha256"],
            second_provenance["provenance_payload_sha256"],
        )

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

    def test_reobservation_preserves_workflow_progress_as_bound_successor(self):
        waiting_snapshot = self.snapshot()
        waiting_snapshot["workflow_runs"][0] = self.workflow_run(
            "QIKVRT CI",
            identifier=101,
            run_number=10,
            status="in_progress",
            conclusion=None,
        )
        expected = self.evaluate(waiting_snapshot)
        self.assertEqual(expected["first_blocker"], "REQUIRED_GATE_NOT_TERMINAL")

        fresh_snapshot = self.snapshot()
        with mock.patch.object(
            MODULE,
            "observe_repository",
            return_value=(fresh_snapshot, DEFAULT_DIFF_BYTES),
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
        self.assertTrue(report["ledger_safe"])
        self.assertTrue(report["progress_successor"])
        self.assertEqual(report["state"], "PROGRESS_SUCCESSOR_OBSERVED")
        self.assertEqual(
            report["first_blocker"],
            "WORKFLOW_PROGRESS_SUCCESSOR_REQUIRED",
        )
        self.assertTrue(report["checks"]["causal_binding"])
        self.assertNotEqual(
            fresh["evidence_fingerprint"], expected["evidence_fingerprint"]
        )
        self.assertEqual(observed_diff, DEFAULT_DIFF_BYTES)

    def test_reobservation_never_admits_decision_input_drift_as_progress(self):
        expected = self.evaluate(self.snapshot())
        changed_scope = self.changed_files()
        changed_scope[0] = {**changed_scope[0], "path": "renamed.txt"}
        cases = {
            "draft": self.snapshot(draft=True),
            "reviewer": self.snapshot(requested_reviewers=["Goldkelch"]),
            "team": self.snapshot(requested_team_reviewers=["authority-team"]),
            "head": self.snapshot(head_sha="1" * 40),
            "tree": self.snapshot(tree_sha="2" * 40),
            "base": self.snapshot(base_sha="3" * 40),
            "base-tree": self.snapshot(base_tree_sha="4" * 40),
            "current-main": self.snapshot(current_main_sha="5" * 40),
            "current-main-tree": self.snapshot(current_main_tree_sha="6" * 40),
            "base-ref": self.snapshot(base_ref="release"),
            "scope": self.snapshot(
                changed_files=changed_scope,
                scope_sha256=scope_sha256(changed_scope),
            ),
            "discussion": self.snapshot(
                discussion_items=[{
                    "kind": "ISSUE_COMMENT",
                    "id": "88",
                    "author": "reviewer",
                    "author_association": "MEMBER",
                    "state": None,
                    "commit_id": None,
                    "updated_at": "2026-08-29T17:00:00Z",
                    "body_sha256": "8" * 64,
                }]
            ),
            "review-thread": self.snapshot(
                review_threads=[{
                    "id": "PRRT_1",
                    "is_resolved": False,
                    "body_sha256": "7" * 64,
                }],
                unresolved_review_threads=1,
            ),
        }
        for label, fresh_snapshot in cases.items():
            with self.subTest(label=label), mock.patch.object(
                MODULE,
                "observe_repository",
                return_value=(fresh_snapshot, DEFAULT_DIFF_BYTES),
            ):
                report, _fresh, _diff = MODULE.verify_current_receipt(
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
            self.assertFalse(report["ledger_safe"])
            self.assertFalse(report["progress_successor"])
            self.assertFalse(report["checks"]["causal_binding"])
            self.assertEqual(report["state"], "HOLD_UNVERIFIED")

    def test_unknown_future_receipt_field_is_causally_bound_by_default(self):
        snapshot = self.snapshot()
        expected = self.evaluate(snapshot)
        expected["future_decision_input"] = {"version": 1, "authority": "bound"}
        expected = MODULE._seal(expected)

        with mock.patch.object(
            MODULE,
            "observe_repository",
            return_value=(snapshot, DEFAULT_DIFF_BYTES),
        ):
            report, _fresh, _diff = MODULE.verify_current_receipt(
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

        self.assertTrue(report["checks"]["expected_receipt_self_seal"])
        self.assertFalse(report["checks"]["causal_binding"])
        self.assertFalse(report["ledger_safe"])
        self.assertFalse(report["progress_successor"])

    def test_active_writer_change_is_a_nonprojectable_bound_successor(self):
        waiting = self.snapshot(active_writers=[{
            "id": 777,
            "name": "QIKVRT repository evidence materialization",
            "status": "in_progress",
            "head_sha": HEAD_SHA,
            "workflow_id": 222,
            "path": ".github/workflows/qikvrt_batch04_integrity.yml",
            "event": "pull_request",
            "run_number": 10,
            "run_attempt": 1,
        }])
        expected = self.evaluate(waiting)
        fresh_snapshot = self.snapshot()

        with mock.patch.object(
            MODULE,
            "observe_repository",
            return_value=(fresh_snapshot, DEFAULT_DIFF_BYTES),
        ):
            report, fresh, _diff = MODULE.verify_current_receipt(
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

        self.assertTrue(report["ledger_safe"])
        self.assertTrue(report["progress_successor"])
        self.assertFalse(report["exact"])
        self.assertNotEqual(
            expected["active_writers_observed"],
            fresh["active_writers_observed"],
        )

    def test_review_thread_order_is_canonical_but_resolution_is_semantic(self):
        threads = [
            {"id": "PRRT_2", "is_resolved": True, "body_sha256": "2" * 64},
            {"id": "PRRT_1", "is_resolved": True, "body_sha256": "1" * 64},
        ]
        first = self.evaluate(self.snapshot(review_threads=threads))
        second = self.evaluate(self.snapshot(review_threads=list(reversed(threads))))
        self.assertEqual(first["discussion_sha256"], second["discussion_sha256"])
        self.assertEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])

        resolved = self.evaluate(self.snapshot(review_threads=[threads[0]]))
        unresolved_snapshot = self.snapshot(
            review_threads=[{**threads[0], "is_resolved": False}],
            unresolved_review_threads=1,
        )
        with mock.patch.object(
            MODULE,
            "observe_repository",
            return_value=(unresolved_snapshot, DEFAULT_DIFF_BYTES),
        ):
            report, _fresh, _diff = MODULE.verify_current_receipt(
                resolved,
                MODULE._pretty_json_bytes(resolved),
                DEFAULT_DIFF_BYTES,
                "example/qik-vrt",
                349,
                999,
                list(REQUIRED_GATE_PATHS),
                REQUIRED_GATE_PATHS,
                [],
            )
        self.assertFalse(report["ledger_safe"])
        self.assertFalse(report["checks"]["causal_binding"])

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
        live_status = {
            "id": 3,
            "body": "<!-- qikvrt-live-status-watch -->\nExact status projection.",
            "user": {"login": "github-actions[bot]"},
            "created_at": "2026-08-22T20:02:00Z",
        }
        human_marker = {
            **live_status,
            "id": 4,
            "user": {"login": "reviewer"},
            "created_at": "2026-08-22T20:03:00Z",
        }
        embedded_marker = {
            **live_status,
            "id": 5,
            "body": "Telemetry follows <!-- qikvrt-live-status-watch -->",
            "created_at": "2026-08-22T20:04:00Z",
        }
        other_bot = {
            **live_status,
            "id": 6,
            "user": {"login": "dependabot[bot]"},
            "created_at": "2026-08-22T20:05:00Z",
        }

        def pages(endpoint):
            if endpoint.endswith("/reviews?per_page=100"):
                return [own]
            if endpoint.endswith("/comments?per_page=100") and "/issues/" in endpoint:
                return [foreign, live_status, human_marker, embedded_marker, other_bot]
            return []

        with mock.patch.object(MODULE, "_gh_pages", side_effect=pages):
            observed = MODULE._discussion_observation("example/qik-vrt", 349)
        self.assertEqual(
            [item["id"] for item in observed],
            ["2", "4", "5", "6"],
        )

    def test_status_dedup_considers_only_latest_context_projection(self):
        fingerprint = "a" * 64
        continued = {
            "id": 10,
            "context": "QIKVRT requested review execution",
            "state": "success",
            "created_at": "2026-08-22T10:00:00Z",
            "description": (
                "Technical observation complete; independent approval required; "
                f"fp={fingerprint}"
            ),
        }
        waiting = {
            "id": 11,
            "context": "QIKVRT requested review execution",
            "state": "pending",
            "created_at": "2026-08-22T10:01:00Z",
            "description": f"Mesh WAIT; D0=1; fp={'b' * 64}",
        }
        recontinued = {
            **continued,
            "id": 12,
            "created_at": "2026-08-22T10:02:00Z",
        }

        self.assertTrue(
            MODULE.latest_status_matches_projection(
                [continued], continued["context"], "success", fingerprint
            )
        )
        self.assertFalse(
            MODULE.latest_status_matches_projection(
                [continued, waiting], continued["context"], "success", fingerprint
            )
        )
        self.assertTrue(
            MODULE.latest_status_matches_projection(
                [continued, waiting, recontinued],
                continued["context"],
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

        missing = MODULE.plan_ledger_update(receipt, diff, None, None, None)
        self.assertEqual(missing["action"], "HOLD")
        self.assertEqual(
            missing["first_blocker"],
            "MESH_REVIEW_LEDGER_EXTERNAL_GENESIS_REQUIRED",
        )

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

    def test_mesh_ledger_protection_requires_external_exact_ref_and_sole_app(self):
        delegation = self.mesh_ledger_delegation()
        observed = MODULE.validate_mesh_ledger_protection(
            delegation, "example/qik-vrt"
        )
        self.assertEqual(observed["genesis_commit_sha"], "9" * 40)
        self.assertEqual(observed["writer_integration_id"], 4242)
        self.assertEqual(
            observed["required_rule_types"],
            ["deletion", "non_fast_forward", "update"],
        )

        cases = []
        unverified = self.mesh_ledger_delegation()
        unverified["ledger_authority_boundary"][
            "external_configuration_verified"
        ] = False
        cases.append(unverified)
        deleted_ref = self.mesh_ledger_delegation(ref_initialized=False)
        cases.append(deleted_ref)
        missing_update = self.mesh_ledger_delegation(
            required_rule_types=["deletion", "non_fast_forward"]
        )
        cases.append(missing_update)
        broad_secret = self.mesh_ledger_delegation(
            repository_scope_secret_names_absent=[]
        )
        cases.append(broad_secret)
        forged_bypass = self.mesh_ledger_delegation(
            sole_bypass_actors=[
                {
                    "actor_id": 1,
                    "actor_type": "RepositoryRole",
                    "bypass_mode": "always",
                }
            ]
        )
        cases.append(forged_bypass)
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    MODULE.ReviewSnapshotError,
                    "MESH_REVIEW_LEDGER_PROTECTION_NOT_VERIFIED",
                ):
                    MODULE.validate_mesh_ledger_protection(
                        value, "example/qik-vrt"
                    )

        repository_delegation = json.loads(
            (
                ROOT
                / "state"
                / "authorization"
                / "delegations"
                / "OWNER_MESH_REPOSITORY_SELF_REVIEW_FEEDBACK_V1.json"
            ).read_text(encoding="utf-8")
        )
        boundary = repository_delegation["ledger_authority_boundary"]
        self.assertFalse(boundary["external_configuration_verified"])
        self.assertEqual(boundary["external_readback_receipts"], [])
        self.assertEqual(
            boundary["external_configuration_hold"],
            "MESH_REVIEW_LEDGER_PROTECTION_NOT_VERIFIED",
        )

    def test_mesh_ledger_write_requires_effect_local_environment_and_app_readback(self):
        sealed = MODULE.validate_mesh_ledger_protection(
            self.mesh_ledger_delegation(), "example/qik-vrt"
        )
        branch_rules = [
            {"type": name, "ruleset_id": 19344903}
            for name in ("deletion", "non_fast_forward", "update")
        ]
        ruleset = {
            "id": 19344903,
            "name": "QIKVRT Mesh review ledger writer",
            "target": "branch",
            "source_type": "Repository",
            "source": "example/qik-vrt",
            "enforcement": "active",
            "bypass_actors": sealed["sole_bypass_actors"],
            "conditions": {
                "ref_name": {"include": [MODULE.LEDGER_REF], "exclude": []}
            },
            "rules": [{"type": name} for name in sealed["required_rule_types"]],
        }
        kwargs = {
            "repository": "example/qik-vrt",
            "installation": {"app_id": 4242},
            "branch_rules": branch_rules,
            "ruleset": ruleset,
            "ref": {"object": {"sha": "8" * 40}},
            "environment": {
                "name": MODULE.MESH_LEDGER_AUTHORITY_ENVIRONMENT,
                "deployment_branch_policy": {
                    "protected_branches": False,
                    "custom_branch_policies": True,
                },
                "protection_rules": [{"type": "branch_policy"}],
            },
            "repository_owner": {
                "login": "example",
                "id": 1001,
                "type": "User",
            },
            "branch_policies": [{"name": "main", "type": "branch"}],
            "environment_secret_names": [
                MODULE.MESH_LEDGER_AUDITOR_SECRET,
                MODULE.MESH_LEDGER_WRITER_SECRET,
            ],
            "repository_secret_names": [],
            "organization_secret_names": [],
            "organization_scope_readback": "NOT_APPLICABLE_USER_OWNER",
        }
        exact = MODULE.verify_live_mesh_ledger_authority(sealed, **kwargs)
        self.assertTrue(exact["external_configuration_verified"])
        self.assertEqual(
            exact["organization_scope_readback"],
            "NOT_APPLICABLE_USER_OWNER",
        )

        for mutation in ("fallback", "missing_env", "wrong_app", "fake_org"):
            changed = copy.deepcopy(kwargs)
            if mutation == "fallback":
                changed["repository_secret_names"] = [
                    MODULE.MESH_LEDGER_WRITER_SECRET
                ]
            elif mutation == "missing_env":
                changed["environment_secret_names"] = [
                    MODULE.MESH_LEDGER_WRITER_SECRET
                ]
            elif mutation == "wrong_app":
                changed["installation"] = {"app_id": 7}
            else:
                changed["organization_secret_names"] = []
                changed["organization_scope_readback"] = (
                    "VERIFIED_ORGANIZATION_SECRET_INVENTORY"
                )
            with self.subTest(mutation=mutation), self.assertRaisesRegex(
                MODULE.ReviewSnapshotError,
                "MESH_REVIEW_LEDGER_LIVE_AUTHORITY_NOT_VERIFIED",
            ):
                MODULE.verify_live_mesh_ledger_authority(sealed, **changed)

    def test_missing_ref_after_record_never_reinitializes_ledger(self):
        receipt = b'{"receipt":1}\n'
        diff = b"diff bytes"
        recorded_head = "1" * 40
        recorded = MODULE.plan_ledger_update(
            receipt, diff, recorded_head, None, None
        )
        self.assertEqual(recorded["action"], "APPEND_FAST_FORWARD")

        after_external_delete = MODULE.plan_ledger_update(
            receipt, diff, None, None, None
        )
        self.assertEqual(after_external_delete["action"], "HOLD")
        self.assertEqual(
            after_external_delete["first_blocker"],
            "MESH_REVIEW_LEDGER_EXTERNAL_GENESIS_REQUIRED",
        )
        self.assertNotEqual(
            after_external_delete["action"], "INITIALIZE_ORPHAN_ROOT"
        )

    def test_bounded_cas_replans_after_parallel_pr_ref_race(self):
        initial = "1" * 40
        rival = "2" * 40
        state = {"head": initial, "trees": {initial: {}}, "raced": False}
        target_path = "state/mesh/reviews/pr-935.json"
        target_bytes = b"pr-935"

        def read_head():
            return state["head"]

        def plan_at(parent):
            existing = state["trees"][parent].get(target_path)
            if existing is not None and existing != target_bytes:
                raise MODULE.ReviewSnapshotError("APPEND_ONLY_LEDGER_PATH_COLLISION")
            return existing is None

        def build_commit(parent):
            commit = "3" * 40 if parent == initial else "4" * 40
            state["trees"][commit] = {
                **state["trees"][parent],
                target_path: target_bytes,
            }
            return commit

        def update_ref(commit):
            if not state["raced"]:
                state["raced"] = True
                state["trees"][rival] = {
                    **state["trees"][initial],
                    "state/mesh/reviews/pr-936.json": b"pr-936",
                }
                state["head"] = rival
                raise RuntimeError("non-fast-forward")
            state["head"] = commit

        def verify_at(head):
            return state["trees"][head].get(target_path) == target_bytes

        result = MODULE.bounded_append_only_cas(
            read_head=read_head,
            plan_at=plan_at,
            build_commit=build_commit,
            update_ref=update_ref,
            verify_at=verify_at,
        )
        self.assertTrue(result["persisted"])
        self.assertTrue(result["appended"])
        self.assertEqual(result["attempts"], 2)
        final_tree = state["trees"][state["head"]]
        self.assertEqual(final_tree[target_path], target_bytes)
        self.assertEqual(final_tree["state/mesh/reviews/pr-936.json"], b"pr-936")

    def test_bounded_cas_never_overwrites_existing_path(self):
        initial = "1" * 40
        path = "state/mesh/reviews/pr-935.json"
        state = {"head": initial, "tree": {path: b"authority-bytes"}}
        effects = []

        def plan_at(_parent):
            if state["tree"].get(path) != b"candidate-bytes":
                raise MODULE.ReviewSnapshotError("APPEND_ONLY_LEDGER_PATH_COLLISION")
            return False

        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "APPEND_ONLY_LEDGER_PATH_COLLISION"
        ):
            MODULE.bounded_append_only_cas(
                read_head=lambda: state["head"],
                plan_at=plan_at,
                build_commit=lambda _parent: effects.append("build") or "2" * 40,
                update_ref=lambda _commit: effects.append("update"),
                verify_at=lambda _head: False,
            )
        self.assertEqual(effects, [])
        self.assertEqual(state["tree"][path], b"authority-bytes")

    def test_recursive_queue_intent_and_ack_are_content_addressed_and_immutable(self):
        receipt = self.evaluate(self.snapshot())
        predecessor = "a" * 64
        path, intent = MODULE.review_queue_intent(receipt, predecessor)
        self.assertEqual(
            path,
            f"{MODULE.REVIEW_QUEUE_ROOT}/pr-349/{HEAD_SHA}/"
            f"{receipt['evidence_fingerprint']}.json",
        )
        self.assertEqual(intent["predecessor_fingerprint"], predecessor)
        self.assertEqual(
            intent["successor_fingerprint"], receipt["evidence_fingerprint"]
        )
        self.assertEqual(intent["tree_sha"], HEAD_TREE_SHA)
        self.assertEqual(intent["base_sha"], MAIN_SHA)
        self.assertFalse(any(intent["completion_claims"].values()))
        self.assertEqual(
            MODULE.review_queue_intent(receipt, predecessor),
            (path, intent),
        )

        ack_path, ack = MODULE.review_queue_ack(
            "example/qik-vrt",
            349,
            HEAD_SHA,
            predecessor,
            receipt["evidence_fingerprint"],
        )
        self.assertEqual(
            ack_path,
            f"{MODULE.REVIEW_QUEUE_ACK_ROOT}/pr-349/{HEAD_SHA}/{predecessor}.json",
        )
        self.assertEqual(ack["state"], "SUPERSEDED_BY_CAUSAL_REOBSERVATION")
        self.assertFalse(any(ack["completion_claims"].values()))

    def test_mixed_legacy_and_current_ledger_receipts_skip_legacy(self):
        current = self.evaluate(self.snapshot())
        legacy = copy.deepcopy(current)
        legacy["state"] = "APPROVE"
        legacy["mesh_disposition"] = "APPROVE"

        current_receipts = []
        holds = []
        for receipt in (legacy, current):
            semantics = MODULE.mesh_receipt_semantics(receipt)
            if semantics["current"]:
                current_receipts.append(receipt)
            else:
                holds.append(semantics)

        self.assertEqual(current_receipts, [current])
        self.assertEqual(holds[0]["state"], "LEGACY_HOLD")
        self.assertEqual(
            holds[0]["first_blocker"],
            "LEGACY_TECHNICAL_APPROVE_RECEIPT",
        )
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError,
            "LEGACY_TECHNICAL_APPROVE_RECEIPT",
        ):
            MODULE.review_queue_intent(legacy, "a" * 64)

        _, intent = MODULE.review_queue_intent(current, "a" * 64)
        self.assertEqual(
            intent["successor_fingerprint"], current["evidence_fingerprint"]
        )

    def test_recursive_queue_dispatches_once_then_defers_to_admission_recovery(self):
        receipt = self.evaluate(self.snapshot())
        queue_path, intent = MODULE.review_queue_intent(receipt, "a" * 64)
        pr = {
            "number": 349,
            "state": "open",
            "head": {"sha": HEAD_SHA},
            "base": {"sha": MAIN_SHA},
        }
        commit = {"sha": HEAD_SHA, "tree": {"sha": HEAD_TREE_SHA}}

        first = MODULE.plan_review_queue_drain(
            intent,
            pr=pr,
            commit=commit,
            child_runs=[],
            trusted_workflow_id=8100,
            trusted_evaluator_sha=MAIN_SHA,
        )
        self.assertEqual(first["state"], "WORK_UNIT")
        self.assertEqual(first["next_attempt"], 1)
        self.assertTrue(first["dispatch_required"])

        _, transport = MODULE.review_queue_dispatch_intent(
            intent,
            queue_path=queue_path,
            evaluator_sha=MAIN_SHA,
            workflow_id=8100,
            dispatch_attempt=1,
        )
        title = transport["expected_title"]
        cancelled = {
            "id": 910,
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "cancelled",
            "display_title": title,
            "workflow_id": 8100,
            "path": MODULE.TRUSTED_WORKFLOW_PATH,
            "event": "workflow_dispatch",
            "head_branch": "main",
            "repository": {"full_name": "example/qik-vrt"},
        }
        second = MODULE.plan_review_queue_drain(
            intent,
            pr=pr,
            commit=commit,
            child_runs=[cancelled],
            trusted_workflow_id=8100,
            trusted_evaluator_sha=MAIN_SHA,
        )
        self.assertEqual(second["state"], "ADMISSION_RECOVERY_PENDING")
        self.assertIsNone(second["next_attempt"])
        self.assertFalse(second["dispatch_required"])
        self.assertEqual(
            second["first_blocker"],
            "ADMISSION_RECOVERY_OWNS_ACCEPTED_CHILD",
        )

        exhausted_run = {**cancelled, "run_attempt": 2}
        exhausted = MODULE.plan_review_queue_drain(
            intent,
            pr=pr,
            commit=commit,
            child_runs=[exhausted_run],
            trusted_workflow_id=8100,
            trusted_evaluator_sha=MAIN_SHA,
        )
        self.assertEqual(exhausted["state"], "ADMISSION_RECOVERY_PENDING")
        self.assertEqual(exhausted["d0"], 2)
        self.assertFalse(exhausted["dispatch_required"])
        self.assertIsNone(exhausted["next_attempt"])
        self.assertFalse(any(exhausted["completion_claims"].values()))

    def test_v3_child_title_is_exact_and_bounded_at_ten_digit_pr(self):
        title = MODULE.requested_review_run_title(
            evaluator_sha=MAIN_SHA,
            pr_number=9_999_999_999,
            head_sha=HEAD_SHA,
            fingerprint="a" * 64,
            transport_intent_sha256="b" * 64,
            transport_attempt=1,
        )
        self.assertEqual(len(title), 249)
        self.assertLessEqual(len(title), 255)
        self.assertEqual(
            title,
            f"qikvrt-rr-v3 e={MAIN_SHA} p=9999999999 h={HEAD_SHA} "
            f"f={'a' * 64} i={'b' * 64} a=1",
        )
        self.assertEqual(
            MODULE.parse_requested_review_run_title(title),
            {
                "schema": "qikvrt_requested_review_run_locator_v3",
                "evaluator_sha": MAIN_SHA,
                "pr_number": 9_999_999_999,
                "head_sha": HEAD_SHA,
                "fingerprint": "a" * 64,
                "transport_intent_sha256": "b" * 64,
                "transport_attempt": 1,
            },
        )
        self.assertIsNone(MODULE.parse_requested_review_run_title(title + " suffix"))
        self.assertIsNone(MODULE.parse_requested_review_run_title(title[:-1] + "2"))
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "one-shot attempt one"
        ):
            MODULE.requested_review_run_title(
                evaluator_sha=MAIN_SHA,
                pr_number=935,
                head_sha=HEAD_SHA,
                fingerprint="a" * 64,
                transport_intent_sha256="b" * 64,
                transport_attempt=2,
            )
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "PR number is invalid"
        ):
            MODULE.requested_review_run_title(
                evaluator_sha=MAIN_SHA,
                pr_number=10_000_000_000,
                head_sha=HEAD_SHA,
                fingerprint="a" * 64,
                transport_intent_sha256="b" * 64,
                transport_attempt=1,
            )

    def test_returned_dispatch_child_binds_fast_terminal_conclusion(self):
        title = MODULE.requested_review_run_title(
            evaluator_sha=MAIN_SHA,
            pr_number=935,
            head_sha=HEAD_SHA,
            fingerprint="e" * 64,
            transport_intent_sha256="f" * 64,
            transport_attempt=1,
        )
        raw = {
            "id": 8123,
            "run_attempt": 1,
            "workflow_id": 99,
            "path": f"{MODULE.TRUSTED_WORKFLOW_PATH}@main",
            "event": "workflow_dispatch",
            "repository": {"full_name": "example/qik-vrt"},
            "head_branch": "main",
            "head_sha": MAIN_SHA,
            "display_title": title,
            "status": "completed",
            "conclusion": "success",
        }
        success = MODULE.requested_review_dispatch_child(
            raw,
            repository="example/qik-vrt",
            workflow_id=99,
            evaluator_sha=MAIN_SHA,
            display_title=title,
        )
        self.assertEqual(success["conclusion"], "success")

        cancelled = MODULE.requested_review_dispatch_child(
            dict(raw, conclusion="cancelled"),
            repository="example/qik-vrt",
            workflow_id=99,
            evaluator_sha=MAIN_SHA,
            display_title=title,
        )
        self.assertEqual(cancelled["conclusion"], "cancelled")
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "returned dispatch child differs"
        ):
            MODULE.requested_review_dispatch_child(
                dict(raw, conclusion=None),
                repository="example/qik-vrt",
                workflow_id=99,
                evaluator_sha=MAIN_SHA,
                display_title=title,
            )

    def test_terminal_completion_envelope_is_exact_and_non_authorizing(self):
        title = MODULE.requested_review_run_title(
            evaluator_sha=MAIN_SHA,
            pr_number=935,
            head_sha=HEAD_SHA,
            fingerprint="e" * 64,
            transport_intent_sha256="f" * 64,
            transport_attempt=1,
        )
        results = {
            name: ("failure" if name == "ledger-write" else "skipped")
            for name in MODULE.REQUESTED_REVIEW_COMPLETION_JOB_RESULTS
        }
        envelope = MODULE.build_requested_review_completion_envelope(
            repository="example/qik-vrt",
            workflow_sha=MAIN_SHA,
            workflow_ref=(
                "example/qik-vrt/"
                ".github/workflows/qikvrt_requested_review_executor.yml@refs/heads/main"
            ),
            run_id=8123,
            run_attempt=1,
            event="workflow_dispatch",
            display_title=title,
            subject={
                "pr_number": 935,
                "head_sha": HEAD_SHA,
                "tree_sha": HEAD_TREE_SHA,
                "base_sha": MAIN_SHA,
                "semantic_fingerprint": "e" * 64,
                "technical_disposition": "WAIT",
            },
            job_results=results,
        )
        self.assertEqual(
            MODULE.validate_requested_review_completion_envelope(envelope),
            envelope,
        )
        self.assertFalse(any(envelope["completion_claims"].values()))
        self.assertNotIn("conclusion", envelope["run"])
        self.assertNotIn("id", envelope["workflow"])
        tampered = copy.deepcopy(envelope)
        tampered["job_results"]["ledger-write"] = "success"
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "completion envelope bytes differ"
        ):
            MODULE.validate_requested_review_completion_envelope(tampered)

    def test_failed_dispatch_planner_keeps_immutable_completion_subject(self):
        intent = "f" * 64
        fingerprint = "e" * 64
        title = MODULE.requested_review_run_title(
            evaluator_sha=MAIN_SHA,
            pr_number=935,
            head_sha=HEAD_SHA,
            fingerprint=fingerprint,
            transport_intent_sha256=intent,
            transport_attempt=1,
        )
        blank_plan = {
            "pr_number": None,
            "head_sha": None,
            "tree_sha": None,
            "base_sha": None,
            "semantic_fingerprint": None,
            "technical_disposition": None,
        }
        dispatch_inputs = {
            "pr": "935",
            "head": HEAD_SHA,
            "fingerprint": fingerprint,
            "evaluator_sha": MAIN_SHA,
            "transport_intent_sha256": intent,
            "transport_attempt": "1",
        }
        binding = MODULE.resolve_requested_review_completion_binding(
            event="workflow_dispatch",
            workflow_sha=MAIN_SHA,
            display_title=title,
            plan_subject=blank_plan,
            dispatch_inputs=dispatch_inputs,
        )
        subject = binding["subject"]
        self.assertEqual(subject["pr_number"], 935)
        self.assertEqual(subject["head_sha"], HEAD_SHA)
        self.assertIsNone(subject["semantic_fingerprint"])
        self.assertIsNone(subject["tree_sha"])
        self.assertIsNone(subject["base_sha"])
        self.assertEqual(binding["dispatch_locator"]["request_fingerprint"], fingerprint)
        self.assertEqual(binding["dispatch_locator"]["transport_intent_sha256"], intent)

        observed_plan = dict(blank_plan, semantic_fingerprint="a" * 64)
        observed = MODULE.resolve_requested_review_completion_binding(
            event="workflow_dispatch",
            workflow_sha=MAIN_SHA,
            display_title=title,
            plan_subject=observed_plan,
            dispatch_inputs=dispatch_inputs,
        )
        self.assertEqual(observed["subject"]["semantic_fingerprint"], "a" * 64)
        self.assertEqual(
            observed["dispatch_locator"]["request_fingerprint"], fingerprint
        )

        for field, value in (
            ("head_sha", "a" * 40),
        ):
            changed = dict(blank_plan)
            changed[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                MODULE.ReviewSnapshotError, "immutable dispatch input"
            ):
                MODULE.resolve_requested_review_completion_binding(
                    event="workflow_dispatch",
                    workflow_sha=MAIN_SHA,
                    display_title=title,
                    plan_subject=changed,
                    dispatch_inputs=dispatch_inputs,
                )

        bad_inputs = dict(dispatch_inputs, transport_attempt="2")
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "dispatch inputs differ"
        ):
            MODULE.resolve_requested_review_completion_binding(
                event="workflow_dispatch",
                workflow_sha=MAIN_SHA,
                display_title=title,
                plan_subject=blank_plan,
                dispatch_inputs=bad_inputs,
            )

    def test_recursive_queue_drain_waits_for_active_exact_child(self):
        receipt = self.evaluate(self.snapshot())
        queue_path, intent = MODULE.review_queue_intent(receipt, "a" * 64)
        _, transport = MODULE.review_queue_dispatch_intent(
            intent,
            queue_path=queue_path,
            evaluator_sha=MAIN_SHA,
            workflow_id=8100,
            dispatch_attempt=1,
        )
        title = transport["expected_title"]
        active = {
            "id": 911,
            "run_attempt": 1,
            "status": "queued",
            "conclusion": None,
            "display_title": title,
            "workflow_id": 8100,
            "path": f"{MODULE.TRUSTED_WORKFLOW_PATH}@refs/heads/main",
            "event": "workflow_dispatch",
            "head_branch": "main",
            "repository": {"full_name": "example/qik-vrt"},
        }
        result = MODULE.plan_review_queue_drain(
            intent,
            pr={
                "number": 349,
                "state": "open",
                "head": {"sha": HEAD_SHA},
                "base": {"sha": MAIN_SHA},
            },
            commit={"sha": HEAD_SHA, "tree": {"sha": HEAD_TREE_SHA}},
            child_runs=[active],
            trusted_workflow_id=8100,
            trusted_evaluator_sha=MAIN_SHA,
        )
        self.assertEqual(result["state"], "ADMISSION_RECOVERY_PENDING")
        self.assertFalse(result["dispatch_required"])

    def test_recursive_queue_drain_fails_closed_on_live_or_child_provenance_drift(self):
        receipt = self.evaluate(self.snapshot())
        queue_path, intent = MODULE.review_queue_intent(receipt, "a" * 64)
        stale = MODULE.plan_review_queue_drain(
            intent,
            pr={
                "number": 349,
                "state": "open",
                "head": {"sha": "e" * 40},
                "base": {"sha": MAIN_SHA},
            },
            commit={"sha": HEAD_SHA, "tree": {"sha": HEAD_TREE_SHA}},
            child_runs=[],
            trusted_workflow_id=8100,
            trusted_evaluator_sha=MAIN_SHA,
        )
        self.assertEqual(stale["state"], "STALE_SUBJECT_D0_3")
        self.assertFalse(stale["dispatch_required"])

        _, transport = MODULE.review_queue_dispatch_intent(
            intent,
            queue_path=queue_path,
            evaluator_sha=MAIN_SHA,
            workflow_id=8100,
            dispatch_attempt=1,
        )
        title = transport["expected_title"]
        with self.assertRaisesRegex(
            MODULE.ReviewSnapshotError, "trusted provenance drifted"
        ):
            MODULE.plan_review_queue_drain(
                intent,
                pr={
                    "number": 349,
                    "state": "open",
                    "head": {"sha": HEAD_SHA},
                    "base": {"sha": MAIN_SHA},
                },
                commit={"sha": HEAD_SHA, "tree": {"sha": HEAD_TREE_SHA}},
                child_runs=[{
                    "id": 912,
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "cancelled",
                    "display_title": title,
                    "workflow_id": 9999,
                    "path": MODULE.TRUSTED_WORKFLOW_PATH,
                    "event": "workflow_dispatch",
                    "head_branch": "main",
                    "repository": {"full_name": "example/qik-vrt"},
                }],
                trusted_workflow_id=8100,
                trusted_evaluator_sha=MAIN_SHA,
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

    def test_active_writer_observation_is_exact_head_scoped(self):
        writer_name = "QIK-VRT autonomous bounded self-heal"
        runs = [
            {
                "id": 901,
                "name": writer_name,
                "status": "queued",
                "head_sha": "e" * 40,
                "workflow_id": 7001,
                "path": ".github/workflows/qikvrt_autonomous_self_heal.yml",
                "event": "schedule",
                "run_number": 1,
                "run_attempt": 1,
            },
            {
                "id": 902,
                "name": writer_name,
                "status": "queued",
                "head_sha": MAIN_SHA,
                "workflow_id": 7001,
                "path": ".github/workflows/qikvrt_autonomous_self_heal.yml",
                "event": "workflow_dispatch",
                "run_number": 2,
                "run_attempt": 1,
            },
            {
                "id": 903,
                "name": writer_name,
                "status": "in_progress",
                "head_sha": HEAD_SHA,
                "workflow_id": 7001,
                "path": ".github/workflows/qikvrt_autonomous_self_heal.yml",
                "event": "pull_request",
                "run_number": 3,
                "run_attempt": 1,
            },
            {
                "id": 999,
                "name": writer_name,
                "status": "in_progress",
                "head_sha": MAIN_SHA,
                "workflow_id": 7001,
                "path": ".github/workflows/qikvrt_autonomous_self_heal.yml",
                "event": "workflow_dispatch",
                "run_number": 4,
                "run_attempt": 1,
            },
        ]
        with mock.patch.object(MODULE, "_gh_runs", return_value=runs) as gh_runs:
            observed = MODULE._active_writer_observation(
                "example/qik-vrt",
                999,
                {writer_name},
                {MAIN_SHA, HEAD_SHA},
                8100,
            )

        self.assertEqual([item["id"] for item in observed], [902, 903])
        self.assertNotIn("e" * 40, {item["head_sha"] for item in observed})
        self.assertEqual(gh_runs.call_count, len(MODULE.ACTIVE_WRITER_STATES))

    def test_active_writer_observation_rejects_unbound_head_set(self):
        with self.assertRaisesRegex(
            MODULE.ReviewObservationError,
            "relevant-head binding",
        ):
            MODULE._active_writer_observation(
                "example/qik-vrt",
                999,
                {"QIK-VRT autonomous bounded self-heal"},
                {"not-a-git-sha"},
                8100,
            )

    def test_dynamic_requested_review_run_name_is_still_an_active_writer(self):
        dynamic_name = MODULE.requested_review_run_title(
            evaluator_sha=MAIN_SHA,
            pr_number=935,
            head_sha=HEAD_SHA,
            fingerprint="a" * 64,
            transport_intent_sha256="b" * 64,
            transport_attempt=1,
        )
        runs = [
            {
                "id": 910,
                "name": dynamic_name,
                "status": "in_progress",
                "head_sha": MAIN_SHA,
                "workflow_id": 8100,
                "path": MODULE.TRUSTED_WORKFLOW_PATH,
                "event": "issue_comment",
                "run_number": 7566,
                "run_attempt": 1,
            },
            {
                "id": 911,
                "name": dynamic_name,
                "status": "in_progress",
                "head_sha": MAIN_SHA,
                "workflow_id": 8101,
                "path": ".github/workflows/untrusted.yml",
                "event": "issue_comment",
                "run_number": 1,
                "run_attempt": 1,
            },
        ]
        with mock.patch.object(MODULE, "_gh_runs", return_value=runs):
            observed = MODULE._active_writer_observation(
                "example/qik-vrt",
                999,
                {MODULE.TRUSTED_WORKFLOW_NAME},
                {MAIN_SHA, HEAD_SHA},
                8100,
            )

        self.assertEqual([item["id"] for item in observed], [910])
        self.assertEqual(observed[0]["name"], dynamic_name)
        self.assertEqual(observed[0]["path"], MODULE.TRUSTED_WORKFLOW_PATH)

    def test_dynamic_requested_review_writer_requires_stable_workflow_id(self):
        run = {
            "id": 910,
            "name": MODULE.requested_review_run_title(
                evaluator_sha=MAIN_SHA,
                pr_number=935,
                head_sha=HEAD_SHA,
                fingerprint="a" * 64,
                transport_intent_sha256="b" * 64,
                transport_attempt=1,
            ),
            "status": "queued",
            "head_sha": MAIN_SHA,
            "workflow_id": None,
            "path": MODULE.TRUSTED_WORKFLOW_PATH,
            "event": "issue_comment",
            "run_number": 7566,
            "run_attempt": 1,
        }
        with mock.patch.object(MODULE, "_gh_runs", return_value=[run]):
            with self.assertRaisesRegex(
                MODULE.ReviewObservationError,
                "active writer workflow id is invalid",
            ):
                MODULE._active_writer_observation(
                    "example/qik-vrt",
                    999,
                    {MODULE.TRUSTED_WORKFLOW_NAME},
                    {MAIN_SHA, HEAD_SHA},
                    8100,
                )

    def test_serialized_requested_successor_does_not_self_block_current_intake(self):
        dynamic_name = MODULE.requested_review_run_title(
            evaluator_sha=MAIN_SHA,
            pr_number=936,
            head_sha=HEAD_SHA,
            fingerprint="a" * 64,
            transport_intent_sha256="b" * 64,
            transport_attempt=1,
        )
        runs = [
            {
                "id": 999,
                "name": MODULE.requested_review_run_title(
                    evaluator_sha=MAIN_SHA,
                    pr_number=935,
                    head_sha=HEAD_SHA,
                    fingerprint="a" * 64,
                    transport_intent_sha256="b" * 64,
                    transport_attempt=1,
                ),
                "status": "in_progress",
                "head_sha": MAIN_SHA,
                "workflow_id": 8100,
                "path": MODULE.TRUSTED_WORKFLOW_PATH,
                "event": "workflow_dispatch",
                "run_number": 7566,
                "run_attempt": 1,
            },
            {
                "id": 910,
                "name": dynamic_name,
                "status": "queued",
                "head_sha": MAIN_SHA,
                "workflow_id": 8100,
                "path": MODULE.TRUSTED_WORKFLOW_PATH,
                "event": "workflow_dispatch",
                "run_number": 7567,
                "run_attempt": 1,
            },
        ]
        with mock.patch.object(MODULE, "_gh_runs", return_value=runs):
            observed = MODULE._active_writer_observation(
                "example/qik-vrt",
                999,
                {MODULE.TRUSTED_WORKFLOW_NAME},
                {MAIN_SHA, HEAD_SHA},
                8100,
            )
        self.assertEqual(observed, [])

    def test_second_in_progress_requested_executor_remains_a_writer_blocker(self):
        run = {
            "id": 910,
            "name": MODULE.requested_review_run_title(
                evaluator_sha=MAIN_SHA,
                pr_number=936,
                head_sha=HEAD_SHA,
                fingerprint="a" * 64,
                transport_intent_sha256="b" * 64,
                transport_attempt=1,
            ),
            "status": "in_progress",
            "head_sha": MAIN_SHA,
            "workflow_id": 8100,
            "path": MODULE.TRUSTED_WORKFLOW_PATH,
            "event": "workflow_dispatch",
            "run_number": 7567,
            "run_attempt": 1,
        }
        with mock.patch.object(MODULE, "_gh_runs", return_value=[run]):
            observed = MODULE._active_writer_observation(
                "example/qik-vrt",
                999,
                {MODULE.TRUSTED_WORKFLOW_NAME},
                {MAIN_SHA, HEAD_SHA},
                8100,
            )
        self.assertEqual([item["id"] for item in observed], [910])

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
        self.assertIn(
            "run-name: qikvrt-rr-v3 e=${{ github.workflow_sha }} p=",
            text,
        )
        for required_input in (
            "fingerprint", "evaluator_sha", "transport_intent_sha256",
            "transport_attempt",
        ):
            self.assertRegex(
                text,
                rf"(?s)      {required_input}:\n.*?        required: true",
            )
        self.assertNotIn("\n  pull_request:\n", text)
        self.assertNotIn("\n  schedule:\n", text)
        self.assertNotIn("Select one exact zero-job ingress recovery", text)
        self.assertNotIn("\n  pull_request_review:\n", text)
        self.assertIn("workflow_run:", text)
        self.assertNotIn('"QIKVRT code-owner review observer"', text)
        self.assertNotIn("BOUNDED_SCHEDULE_ROTATION", text)
        self.assertNotIn("RUN_NUMBER", text)
        self.assertNotIn("_gh_pages", text)
        self.assertIn("select_review_subject", text)
        self.assertIn("qikvrt-mesh-review-selection-", text)
        self.assertIn("EVENT_NAME: ${{ github.event_name }}", text)
        self.assertIn("EVENT_WORKFLOW_RUN_ID:", text)
        self.assertIn("WORKFLOW_RUN_SOURCE_PROVENANCE_INVALID", text)
        self.assertIn("source.get('workflow_id') != workflow.get('id')", text)
        self.assertIn("REQUESTED_HEAD: ${{ inputs.head || '' }}", text)
        self.assertIn("evaluator_sha:", text)
        self.assertIn("inputs.evaluator_sha == github.workflow_sha", text)
        self.assertIn("inputs.evaluator_sha == github.sha", text)
        self.assertIn("inputs.transport_attempt == '1'", text)
        self.assertNotIn("inputs.transport_attempt == '2'", text)
        self.assertNotIn("r'[12]'", text)
        self.assertIn(
            "group: qikvrt-requested-review-executor-${{ github.repository }}",
            text,
        )
        self.assertIn("  queue: max", text)
        self.assertIn("GITHUB_EVENT_PATH", text)
        self.assertIn("event_payload_sha256", text)
        self.assertIn("qikvrt-review-event-context.json", text)
        self.assertIn("--event-context-file /tmp/qikvrt-review-event-context.json", text)
        self.assertIn("EXPECTED_SELECTOR_HEAD", text)
        self.assertIn('--expected-head "$EXPECTED_SELECTOR_HEAD"', text)
        self.assertNotIn("if not people and not teams", text)
        self.assertIn("github.ref == 'refs/heads/main' &&", text)
        self.assertIn("github.workflow_sha == github.sha", text)
        self.assertEqual(text.count("ref: ${{ github.workflow_sha }}"), 9)
        self.assertEqual(text.count("Bind exact evaluator checkout"), 9)
        self.assertNotIn("          ref: main", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("  publish-run-completion-envelope:", text)
        completion = text.split("  publish-run-completion-envelope:\n", 1)[1]
        self.assertIn("if: always()", completion)
        self.assertIn("permissions: {}", completion)
        self.assertIn("build_requested_review_completion_envelope", completion)
        self.assertIn("resolve_requested_review_completion_binding", completion)
        self.assertIn("DISPATCH_TRANSPORT_INTENT_SHA256", completion)
        self.assertIn(
            "qikvrt-requested-review-completion-${{ github.run_id }}-attempt-${{ github.run_attempt }}",
            completion,
        )
        self.assertNotIn("secrets.", completion)
        self.assertIn("/tmp/qikvrt-mesh-review-producer/*", text)
        self.assertIn("MESH_REVIEW_PRODUCER_STAGING_SET_INVALID", text)

    def test_workflow_isolates_every_write_scope_in_one_effect_job(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        core = (ROOT / "tools/qikvrt_requested_review_executor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("permissions: {}", text)
        names = (
            "plan-review", "ledger-write", "project-comment",
            "project-status", "plan-successor-outbox",
            "enqueue-successor-outbox", "select-successor",
            "prepare-successor-transport", "dispatch-successor",
            "record-successor-acceptance", "publish-run-completion-envelope",
        )
        blocks = {}
        for index, name in enumerate(names):
            start = text.index(f"  {name}:\n")
            end = (
                text.index(f"  {names[index + 1]}:\n", start)
                if index + 1 < len(names)
                else len(text)
            )
            blocks[name] = text[start:end]
        self.assertNotIn(": write", blocks["plan-review"])
        self.assertNotIn(": write", blocks["plan-successor-outbox"])
        self.assertNotIn(": write", blocks["select-successor"])
        expected = {
            "project-comment": "pull-requests: write",
            "project-status": "statuses: write",
            "dispatch-successor": "actions: write",
        }
        all_write_scopes = tuple(expected.values())
        self.assertNotIn(": write", blocks["ledger-write"])
        self.assertIn("contents: read", blocks["ledger-write"])
        self.assertIn(
            "environment: qikvrt-outbox-ledger-authority",
            blocks["ledger-write"],
        )
        self.assertIn(
            "secrets.QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN",
            blocks["ledger-write"],
        )
        self.assertIn("writer_token=os.environ.pop", blocks["ledger-write"])
        self.assertIn("verify_ledger_authority", blocks["ledger-write"])
        self.assertIn("writer=True", blocks["ledger-write"])
        for name in (
            "enqueue-successor-outbox",
            "prepare-successor-transport",
            "record-successor-acceptance",
        ):
            with self.subTest(outbox_writer=name):
                self.assertNotIn(": write", blocks[name])
                self.assertIn("contents: read", blocks[name])
                self.assertIn(
                    "environment: qikvrt-outbox-ledger-authority", blocks[name]
                )
                self.assertIn(
                    "group: qikvrt-outbox-ledger-v2-mesh-review-successor-dispatch",
                    blocks[name],
                )
                self.assertIn(
                    "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", blocks[name]
                )
                self.assertIn(
                    "QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID", blocks[name]
                )
                self.assertIn(
                    "QIKVRT_OUTBOX_WRITER_GROUP: qikvrt-outbox-ledger-v2-mesh-review-successor-dispatch",
                    blocks[name],
                )
        self.assertIn(
            "environment: qikvrt-outbox-ledger-authority",
            blocks["select-successor"],
        )
        self.assertIn(
            "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN",
            blocks["select-successor"],
        )
        self.assertNotIn(
            "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN",
            blocks["select-successor"],
        )
        for name, allowed in expected.items():
            with self.subTest(job=name):
                self.assertIn(allowed, blocks[name])
                for scope in all_write_scopes:
                    if scope != allowed:
                        self.assertNotIn(scope, blocks[name])
        self.assertNotIn("statuses: read", blocks["ledger-write"])
        self.assertNotIn("statuses: read", blocks["project-comment"])
        self.assertNotIn("statuses: read", blocks["dispatch-successor"])
        self.assertNotIn("pull-requests: read", blocks["project-comment"])
        self.assertNotIn("actions: read", blocks["dispatch-successor"])
        self.assertIn("Preserve sealed read-only review plan", blocks["plan-review"])
        self.assertIn("Download exact read-only review plan", blocks["ledger-write"])
        self.assertIn("Download exact ledger-bound review", blocks["project-comment"])
        self.assertIn("Download exact ledger-bound review", blocks["project-status"])
        self.assertIn(
            "Download exact pre-effect transport receipt",
            blocks["dispatch-successor"],
        )
        self.assertIn('"--no-ext-diff", "--no-textconv", "--no-renames"', core)
        self.assertIn('"diff", "--name-status", "-z", "--no-renames"', core)
        self.assertIn("REVIEW_INTAKE_SCHEMA", core)
        self.assertIn("GITHUB_ACTIONS_NO_CROSS_EVENT_PRIORITY_GUARANTEE", core)
        self.assertIn("REQUIRED_GATE_PATHS_JSON", text)
        self.assertIn("refs/heads/qikvrt/mesh-review-ledger-v1", text)
        self.assertIn("'force':False", text)
        self.assertIn("bounded_append_only_cas", text)
        self.assertIn("max_attempts=8", text)
        self.assertIn("observed_after_error", core)
        self.assertIn("existing_diff=blob_at(diff_path,parent_sha)", text)
        self.assertIn("prepare_diff_transport_ledger_entries", core)
        self.assertIn("prepare_diff_transport_ledger_entries", text)
        self.assertIn(
            "prepare_diff_transport_ledger_entries,\n"
            "              reassemble_diff_transport,",
            text,
        )
        self.assertIn("blob_at(diff_path,observed_head) == manifest_bytes", text)
        self.assertNotIn("'parents':[]", text)
        self.assertNotIn("INITIALIZE_ORPHAN_ROOT", text)
        self.assertNotIn("INVALID_LEDGER_INITIALIZATION_PLAN", text)
        self.assertIn(
            "MESH_REVIEW_LEDGER_REF_MISSING_AFTER_VERIFIED_GENESIS", text
        )
        self.assertIn("verify_live_mesh_ledger_authority", text)
        self.assertIn("MESH_REVIEW_LEDGER_LIVE_AUTHORITY_NOT_VERIFIED", core)
        self.assertIn("MESH_REVIEW_LEDGER_WRITER_IDENTITY_NOT_VERIFIED", text)
        self.assertIn("pre-ledger-cas", text)
        self.assertIn("post-ledger-cas", text)
        self.assertIn("LEDGER_EFFECT_EVALUATOR_SUPERSEDED", text)
        self.assertIn("LEDGER_QUEUE_EFFECT_EVALUATOR_SUPERSEDED", text)
        self.assertIn("actions: write", text)
        self.assertIn("'--mode','ledger-history'", text)
        self.assertIn("projection_current", text)
        self.assertIn("Dispatch exactly the sealed shared-outbox request", text)
        self.assertIn("'X-GitHub-Api-Version: 2026-03-10'", text)
        self.assertIn("return_run_details=true", text)
        self.assertIn("envelope.get('workflow_run_id')", text)
        self.assertIn("MESH_SUCCESSOR_RETURNED_RUN_DIFFERS", text)
        self.assertIn('inputs[head]=$head', text)
        self.assertIn('inputs[fingerprint]=$fingerprint', text)
        self.assertIn('inputs[evaluator_sha]=$evaluator', text)
        self.assertIn('inputs[transport_intent_sha256]=$intent_sha', text)
        self.assertIn('inputs[transport_attempt]=$attempt', text)
        self.assertIn("needs.select-successor.outputs.needed == 'true'", text)
        self.assertNotIn("steps.ledger.outputs.duplicate != 'true'", text)
        self.assertIn("Read only the next exact sharded FIFO item", text)
        self.assertIn("review_queue_intent", text)
        self.assertIn("mesh-review-successor-dispatch", text)
        self.assertIn("prepare-transport", text)
        self.assertIn("qikvrt_ruleset_outbox_transport_v2", text)
        self.assertIn("value['cas'].get('appended')", text)
        self.assertIn(
            "prepared={'true' if value['cas']['appended'] else 'false'}", text
        )
        self.assertIn("prepared['cas'].get('appended') is not True", text)
        self.assertNotIn("qikvrt_ruleset_outbox_transport_v1", text)
        self.assertIn("ADMISSION_RECOVERY_OWNS_ACCEPTED_CHILD", core)
        self.assertNotIn("EXPECTED_NEXT_ATTEMPT", text)
        self.assertNotIn("PROGRESS_SUCCESSOR_ATTEMPT_PLAN_DRIFT", text)
        self.assertIn("review_queue_ack", text)
        self.assertIn("successor_evidence_persisted", text)
        self.assertIn("MESH_SUCCESSOR_OUTBOX_SOURCE_BINDING_INVALID", text)
        self.assertIn("SUPERSEDED_BY_CAUSAL_REOBSERVATION", core)
        self.assertIn("MESH_SUCCESSOR_RETURNED_RUN_DIFFERS", text)
        self.assertIn("Persist exact child acceptance in shared FIFO", text)
        self.assertIn("TRANSPORT_ACCEPTED_LOCATOR", text)
        self.assertIn("_historical_receipt_binding", core)
        self.assertIn("REOBSERVATION_PROGRESS_FIELDS", core)
        self.assertIn("LIVE_STATUS_MARKER", core)
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
        self.assertIn("- Technical disposition:", text)
        self.assertIn(
            "Technical observation complete; independent approval required; fp=",
            text,
        )
        self.assertIn(
            "current_marker=\"<!-- ${REVIEW_MARKER} head=${EXPECTED_HEAD} "
            "tree=${EXPECTED_TREE} fingerprint=${FINGERPRINT} "
            "disposition=${DISPOSITION} -->\"",
            text,
        )
        self.assertIn('startswith(\\"${current_marker}\\")', text)
        self.assertNotIn(
            'contains(\\"fingerprint=${FINGERPRINT}\\")',
            text,
        )
        self.assertIn("mesh_receipt_semantics", core)
        self.assertIn("LEGACY_TECHNICAL_APPROVE_RECEIPT", core)
        self.assertIn("D0: ${{ needs.ledger-write.outputs.d0 }}", text)
        self.assertIn(
            "NEXT_ACTION: ${{ needs.ledger-write.outputs.next_action }}",
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
        self.assertIn("on: {}", observer)
        self.assertIn("if: false", observer)
        self.assertIn("RETIRED_NO_UNTRUSTED_REVIEW_TRIGGER", observer)
        self.assertNotIn("pull_request_review:", observer)
        self.assertNotIn("pull_request:", observer)
        legacy_fanout = LEGACY_FANOUT_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("on: {}", legacy_fanout)
        self.assertIn("permissions: {}", legacy_fanout)
        self.assertIn("if: false", legacy_fanout)
        self.assertIn("RETIRED_NO_LEGACY_REVIEW_REPORT_FANOUT", legacy_fanout)
        self.assertNotIn("workflow_run:", legacy_fanout)
        self.assertNotIn("pull_request_review", legacy_fanout.split("on: {}", 1)[1])
        self.assertNotIn("secrets.", legacy_fanout)
        self.assertNotIn(": write", legacy_fanout)
        self.assertIn(
            "- qikvrt/mesh-review-ledger-v1",
            CI_WORKFLOW.read_text(encoding="utf-8"),
        )

    def test_legacy_same_fingerprint_bot_comment_is_not_current_dedup(self):
        fingerprint = "a" * 64
        shared = (
            f"{MODULE.REVIEW_MARKER} head={HEAD_SHA} tree={HEAD_TREE_SHA} "
            f"fingerprint={fingerprint} disposition="
        )
        legacy_body = f"<!-- {shared}APPROVE -->\nlegacy technical review"
        current_marker = f"{shared}{MODULE.TECHNICAL_CONTINUE} -->"

        self.assertIn(f"fingerprint={fingerprint}", legacy_body)
        self.assertNotIn(current_marker, legacy_body)

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
            LEGACY_FANOUT_WORKFLOW,
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
