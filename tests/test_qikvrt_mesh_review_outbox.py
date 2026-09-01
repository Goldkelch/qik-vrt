#!/usr/bin/env python3
import hashlib
import io
import json
import unittest
import zipfile

from tests.test_qikvrt_ruleset_outbox import MemoryBackend, artifact, payload
from tools import qikvrt_ruleset_outbox as outbox
from tools.qikvrt_mesh_review_outbox import (
    MeshReviewOutboxError,
    materialize_mesh_authority_terminal,
    materialize_mesh_completion,
    materialize_mesh_completion_query_bound_observation,
    materialize_mesh_missing_evidence_observation,
    materialize_mesh_orphan_authority_observation,
    materialize_mesh_retry_scan_cursor,
    materialize_mesh_subject_supersession,
    materialize_mesh_target_workflow_supersession,
    select_mesh_completion_target,
    select_mesh_orphan_adoption,
)
from tools.qikvrt_native_account_review import (
    build_trusted_executor_producer_binding,
)
from tools.qikvrt_requested_review_executor import (
    REQUESTED_REVIEW_COMPLETION_JOB_RESULTS,
    build_requested_review_completion_envelope,
)


class MeshReviewOutboxTests(unittest.TestCase):
    def setUp(self):
        self.backend = MemoryBackend()
        value = payload("mesh-review-successor-dispatch")
        queue = {
            "schema": "qikvrt_mesh_review_queue_intent_v1",
            "work_unit_id": f"pr-935/{'b' * 40}/{'9' * 64}",
            "repository": "Goldkelch/qik-vrt",
            "pr_number": 935,
            "head_sha": "b" * 40,
            "tree_sha": "c" * 40,
            "base_sha": "d" * 40,
            "predecessor_fingerprint": "8" * 64,
            "successor_fingerprint": "9" * 64,
            "receipt_path": "receipts/pr-935/review.json",
            "diff_path": "receipts/pr-935/review.diff.chunks.json",
            "state": "QUEUED_RECURSIVE_REOBSERVATION",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
                "MERGE": False,
            },
        }
        value["producer"] = {
            "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
            "workflow_sha": "a" * 40,
            "workflow_id": 77,
            "run_id": 401,
            "run_attempt": 1,
            "event": "workflow_dispatch",
        }
        value["subject"] = {
            "schema": "qikvrt_mesh_review_successor_subject_v1",
            "queue_path": "queue/pr-935/item.json",
            "queue_intent_sha256": outbox.digest(queue),
            "queue_intent": queue,
            "source_ledger_commit": "e" * 40,
            "receipt_sha256": "1" * 64,
            "diff_sha256": "2" * 64,
            "productive_effect": False,
        }
        value["request"]["inputs"].update(
            pr="935",
            head="b" * 40,
            fingerprint="8" * 64,
            evaluator_sha="a" * 40,
        )
        value = outbox.seal_review_transport_payload(value)
        self.intent = outbox.append_intent(
            self.backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            self.backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            request=outbox.request_for_transport_attempt(self.intent, 1),
            actor_run_id=402,
            actor_run_attempt=1,
        )
        title = (
            f"qikvrt-rr-v3 e={'a' * 40} p=935 h={'b' * 40} "
            f"f={'8' * 64} i={self.intent['fingerprint']} a=1"
        )
        self.locator = {
            "run_id": 501,
            "run_attempt": 1,
            "workflow_id": 77,
            "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": title,
        }
        outbox.record_acceptance(
            self.backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=self.locator,
        )

    @staticmethod
    def archive(files):
        target = io.BytesIO()
        with zipfile.ZipFile(target, "w") as archive:
            for name, value in files.items():
                archive.writestr(name, value)
        return target.getvalue()

    @staticmethod
    def artifact_api(name, archive, *, run_id=501):
        return {
            "id": 701,
            "name": name,
            "digest": f"sha256:{hashlib.sha256(archive).hexdigest()}",
            "expired": False,
            "workflow_run": {"id": run_id},
        }

    def completed_child(self, conclusion, *, run_attempt=1):
        return {
            **self.locator,
            "run_attempt": run_attempt,
            "status": "completed",
            "conclusion": conclusion,
        }

    def orphan_backend(self):
        backend = MemoryBackend()
        value = self.intent["payload"]
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        outbox.prepare_transport(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=402,
            actor_run_attempt=1,
        )
        return backend, intent

    def accepted_backend(self):
        backend, intent = self.orphan_backend()
        outbox.record_acceptance(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=self.locator,
        )
        return backend, intent

    @staticmethod
    def cursor_actor():
        return {
            "id": 402,
            "run_attempt": 1,
            "workflow_id": 77,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml@main",
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-09-01T08:00:00Z",
            "updated_at": "2026-09-01T08:05:00Z",
        }

    @staticmethod
    def cursor_observer(*, run_id=901, run_attempt=1):
        return {
            "id": run_id,
            "run_attempt": run_attempt,
            "workflow_id": 88,
            "path": (
                ".github/workflows/"
                "qikvrt_mesh_review_successor_completion.yml@main"
            ),
            "event": "schedule",
            "head_sha": "a" * 40,
        }

    @staticmethod
    def persist_cursor(backend, intent, cursor, *, artifact_id=990):
        producer = cursor["observation_producer"]
        return outbox.record_retry_scan_cursor(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            cursor=cursor,
            artifact={
                "id": artifact_id,
                "name": (
                    "qikvrt-outbox-retry-scan-cursor-"
                    "mesh-review-successor-dispatch-1-attempt-1-"
                    f"ordinal-{cursor['ordinal']}-run-{producer['run_id']}-"
                    f"attempt-{producer['run_attempt']}"
                ),
                "archive_sha256": "f" * 64,
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(cursor)
                ),
                "producer_run_id": producer["run_id"],
                "producer_run_attempt": producer["run_attempt"],
                "producer_workflow_id": producer["workflow_id"],
            },
        )

    def success_archive(self, *, run_id=501, run_attempt=1, intent=None):
        item = intent or outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        semantic = "7" * 64
        review = {
            "repository": "Goldkelch/qik-vrt",
            "pr_number": 935,
            "head_sha": "b" * 40,
            "tree_sha": "c" * 40,
            "base_sha": "d" * 40,
            "evidence_fingerprint": semantic,
            "state": "TECHNICAL_CONTINUE",
            "mesh_disposition": "TECHNICAL_CONTINUE",
        }
        ledger = {
            "schema": "qikvrt_mesh_review_ledger_write_v1",
            "persisted": True,
            "projection_current": True,
            "ledger_commit": "e" * 40,
        }
        transport = {
            "schema": "qikvrt_mesh_review_transport_provenance_v1",
            "review_intake": {
                "event_name": "workflow_dispatch",
                "predecessor_successor_fingerprint": "8" * 64,
                "transport_intent_sha256": item["fingerprint"],
                "transport_attempt": 1,
            },
            "productive_effect": False,
        }
        compact = json.dumps(transport, sort_keys=True, separators=(",", ":")).encode()
        transport["provenance_payload_sha256"] = hashlib.sha256(compact).hexdigest()
        files = {
            "review.json": json.dumps(review).encode(),
            "review.diff": b"mesh recursive review\n",
            "ledger-write.json": json.dumps(ledger).encode(),
            "review-transport.json": json.dumps(transport).encode(),
        }
        name = (
            f"qikvrt-mesh-review-pr-935-{'b' * 40}-{semantic}-"
            f"run-{run_id}-attempt-{run_attempt}"
        )
        binding = build_trusted_executor_producer_binding(
            repository="Goldkelch/qik-vrt",
            run_id=run_id,
            run_attempt=run_attempt,
            artifact_name=name,
            pr_number=935,
            head_sha="b" * 40,
            evidence_fingerprint=semantic,
            files=files,
        )
        files["producer-binding.json"] = (
            json.dumps(binding, sort_keys=True, indent=2) + "\n"
        ).encode()
        return name, self.archive(files)

    def adverse_archive(self, child, *, locator_override=None):
        envelope = build_requested_review_completion_envelope(
            repository="Goldkelch/qik-vrt",
            workflow_sha="a" * 40,
            workflow_ref=(
                "Goldkelch/qik-vrt/.github/workflows/"
                "qikvrt_requested_review_executor.yml@refs/heads/main"
            ),
            run_id=child["run_id"],
            run_attempt=child["run_attempt"],
            event="workflow_dispatch",
            display_title=child["display_title"],
            subject={
                "pr_number": 935,
                "head_sha": "b" * 40,
                "tree_sha": "c" * 40,
                "base_sha": "d" * 40,
                "semantic_fingerprint": None,
                "technical_disposition": None,
            },
            job_results={
                name: "skipped"
                for name in REQUESTED_REVIEW_COMPLETION_JOB_RESULTS
            },
        )
        if locator_override:
            envelope["dispatch_locator"].update(locator_override)
        return self.archive(
            {
                "envelope.json": (
                    json.dumps(envelope, sort_keys=True, indent=2) + "\n"
                ).encode()
            }
        )

    def completion_envelope_artifact(self, child):
        archive = self.adverse_archive(child)
        name = (
            f"qikvrt-requested-review-completion-{child['run_id']}-"
            f"attempt-{child['run_attempt']}"
        )
        return self.artifact_api(name, archive, run_id=child["run_id"]), archive

    def record_authority_and_terminalize(self, backend, item, observation, *, run=901):
        producer = {
            "workflow_path": (
                ".github/workflows/"
                "qikvrt_mesh_review_successor_completion.yml"
            ),
            "workflow_sha": "a" * 40,
            "workflow_id": 88,
            "run_id": run,
            "run_attempt": 1,
            "event": "schedule",
        }
        name = (
            "qikvrt-outbox-authority-observation-"
            f"mesh-review-successor-dispatch-{item['sequence']}-"
            f"{observation['blocker']}-run-{run}-attempt-1"
        )
        record = outbox.record_authority_observation(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=item["sequence"],
            observation=observation,
            producer=producer,
            artifact={
                "id": run + 1000,
                "name": name,
                "archive_sha256": "f" * 64,
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(observation)
                ),
                "producer_run_id": producer["run_id"],
                "producer_run_attempt": producer["run_attempt"],
                "producer_workflow_id": producer["workflow_id"],
            },
        )
        terminal = materialize_mesh_authority_terminal(
            item=item, authority_record=record
        )
        outbox.terminalize(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=item["sequence"],
            evidence=terminal,
        )
        return terminal

    def test_success_completion_terminal_advances_two_item_fifo(self):
        item = outbox.read_next(self.backend, "mesh-review-successor-dispatch")
        target = select_mesh_completion_target(item)
        self.assertEqual(target["state"], "OBSERVE_CHILD")
        self.assertFalse(target["child_recovery"])
        name, archive = self.success_archive(intent=item)
        result = materialize_mesh_completion(
            item=item,
            child=self.completed_child("success"),
            jobs=[
                {
                    "id": 601,
                    "name": "project-status",
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "success",
                }
            ],
            artifact_api=self.artifact_api(name, archive),
            artifact_zip=archive,
            transport_attempt=1,
            child_recovery=False,
        )
        outbox.record_completion(
            self.backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=result["child"],
            evidence=result["completion_evidence"],
        )
        second = payload("mesh-review-successor-dispatch", run_id=999, subject="two")
        second = outbox.seal_review_transport_payload(second)
        outbox.append_intent(self.backend, payload=second, artifact=artifact(second))
        outbox.terminalize(
            self.backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            evidence=result["terminal"],
        )
        current = outbox.read_next(self.backend, "mesh-review-successor-dispatch")
        self.assertEqual(current["state"], "PENDING")
        self.assertEqual(current["sequence"], 2)
        self.assertEqual(result["terminal"]["d0"], 2)

    def test_attempt_one_adverse_is_terminal_authority_without_new_child(self):
        item = outbox.read_next(self.backend, "mesh-review-successor-dispatch")
        child = self.completed_child("failure")
        archive = self.adverse_archive(child)
        result = materialize_mesh_completion(
            item=item,
            child=child,
            jobs=[
                {
                    "id": 601,
                    "name": "project-status",
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "failure",
                },
                {
                    "id": 602,
                    "name": "publish-run-completion-envelope",
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "success",
                },
            ],
            artifact_api=self.artifact_api(
                "qikvrt-requested-review-completion-501-attempt-1", archive
            ),
            artifact_zip=archive,
            transport_attempt=1,
            child_recovery=False,
        )
        outbox.record_completion(
            self.backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=result["child"],
            evidence=result["completion_evidence"],
        )
        outbox.validate_terminal_evidence(
            result["terminal"],
            next_item=outbox.read_next(
                self.backend, "mesh-review-successor-dispatch"
            ),
        )
        self.assertEqual(result["terminal"]["d0"], 3)
        self.assertEqual(result["terminal"]["reason"], "MESH_REVIEW_RESULT_ADVERSE")
        self.assertEqual(set(item["transport"]), {"1"})

    def test_recovered_same_run_attempt_two_success_is_core_valid(self):
        original = self.completed_child("cancelled")
        # The original acceptance was queued.  Core accepts the exact terminal
        # result as completion input only after the accepted locator is updated
        # via the child-rerun chain; seed a fresh lane to model that chain.
        backend = MemoryBackend()
        value = self.intent["payload"]
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        outbox.prepare_transport(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=402,
            actor_run_attempt=1,
        )
        outbox.record_acceptance(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=original,
        )
        retry = {
            "schema": outbox.CHILD_RETRY_EVIDENCE_SCHEMA,
            "lane": "mesh-review-successor-dispatch",
            "sequence": 1,
            "fingerprint": intent["fingerprint"],
            "transport_attempt": 1,
            "classification": "ZERO_JOB_CONCURRENCY_CANCELLED",
            "first_blocker": "ATTEMPT_1_ZERO_JOB_CONCURRENCY_CANCELLED",
            "accepted_child_sha256": outbox.digest(original),
            "observed_terminal_child": original,
            "observed_terminal_child_sha256": outbox.digest(original),
            "jobs_total_count": 0,
            "verified": True,
            "productive_effect": False,
        }
        outbox.prepare_child_rerun(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            transport_attempt=1,
            retry_evidence=retry,
            actor_run_id=801,
            actor_run_attempt=1,
        )
        recovered = self.completed_child("success", run_attempt=2)
        outbox.record_child_rerun_acceptance(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            transport_attempt=1,
            child=recovered,
        )
        item = outbox.read_next(backend, "mesh-review-successor-dispatch")
        name, archive = self.success_archive(
            run_id=501, run_attempt=2, intent=item
        )
        result = materialize_mesh_completion(
            item=item,
            child=recovered,
            jobs=[
                {
                    "id": 701,
                    "name": "project-status",
                    "run_attempt": 2,
                    "status": "completed",
                    "conclusion": "success",
                }
            ],
            artifact_api=self.artifact_api(name, archive),
            artifact_zip=archive,
            transport_attempt=1,
            child_recovery=True,
        )
        outbox.record_completion(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=result["child"],
            evidence=result["completion_evidence"],
            child_recovery=True,
        )
        outbox.validate_terminal_evidence(
            result["terminal"],
            next_item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
        )
        self.assertTrue(result["terminal"]["business_receipt"]["child_recovery"])

    def test_tampered_transport_and_extra_zip_file_fail_closed(self):
        item = outbox.read_next(self.backend, "mesh-review-successor-dispatch")
        name, archive = self.success_archive(intent=item)
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            files = {info.filename: source.read(info) for info in source.infolist()}
        files["extra.txt"] = b"unbound\n"
        extra = self.archive(files)
        with self.assertRaisesRegex(MeshReviewOutboxError, "file set is not exact"):
            materialize_mesh_completion(
                item=item,
                child=self.completed_child("success"),
                jobs=[
                    {
                        "id": 601,
                        "name": "project-status",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
                artifact_api=self.artifact_api(name, extra),
                artifact_zip=extra,
                transport_attempt=1,
                child_recovery=False,
            )
        nested = self.archive(
            {
                f"nested/{member}": value
                for member, value in files.items()
                if member != "extra.txt"
            }
        )
        with self.assertRaisesRegex(MeshReviewOutboxError, "archive file is unsafe"):
            materialize_mesh_completion(
                item=item,
                child=self.completed_child("success"),
                jobs=[
                    {
                        "id": 601,
                        "name": "project-status",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
                artifact_api=self.artifact_api(name, nested),
                artifact_zip=nested,
                transport_attempt=1,
                child_recovery=False,
            )
        child = self.completed_child("failure")
        adverse = self.adverse_archive(
            child, locator_override={"transport_intent_sha256": "0" * 64}
        )
        with self.assertRaisesRegex(
            MeshReviewOutboxError,
            "completion envelope is invalid|subject/run binding",
        ):
            materialize_mesh_completion(
                item=item,
                child=child,
                jobs=[
                    {
                        "id": 601,
                        "name": "project-status",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": "failure",
                    },
                    {
                        "id": 602,
                        "name": "publish-run-completion-envelope",
                        "run_attempt": 1,
                        "status": "completed",
                        "conclusion": "success",
                    },
                ],
                artifact_api=self.artifact_api(
                    "qikvrt-requested-review-completion-501-attempt-1", adverse
                ),
                artifact_zip=adverse,
                transport_attempt=1,
                child_recovery=False,
            )

    def test_post_to_acceptance_crash_adopts_one_exact_child(self):
        backend = MemoryBackend()
        value = self.intent["payload"]
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        outbox.prepare_transport(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=402,
            actor_run_attempt=1,
        )
        item = outbox.read_next(backend, "mesh-review-successor-dispatch")
        target = select_mesh_completion_target(item)
        self.assertEqual(target["state"], "SCAN_ORPHAN")
        actor = {
            "id": 402,
            "run_attempt": 1,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml@main",
            "repository": {"full_name": "Goldkelch/qik-vrt"},
            "status": "completed",
            "conclusion": "success",
            "run_started_at": "2026-09-01T08:00:00Z",
            "updated_at": "2026-09-01T08:05:00Z",
        }
        raw_child = {
            "id": 501,
            "run_attempt": 1,
            "workflow_id": 77,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml@main",
            "event": "workflow_dispatch",
            "repository": {"full_name": "Goldkelch/qik-vrt"},
            "head_branch": "main",
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": self.locator["display_title"],
            "created_at": "2026-09-01T08:03:00Z",
        }
        result = select_mesh_orphan_adoption(
            item=item,
            actor_run=actor,
            candidate_runs=[raw_child],
            scan_complete=True,
            transport_attempt=1,
        )
        self.assertTrue(result["adopted"])
        self.assertEqual(result["child"]["run_id"], 501)
        accepted = outbox.record_acceptance(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=result["child"],
        )
        self.assertEqual(accepted["state"], "TRANSPORT_ACCEPTED_LOCATOR")

    def test_bounded_cursor_adopts_one_exact_child(self):
        backend, intent = self.orphan_backend()
        raw_child = {
            "id": 501,
            "run_attempt": 1,
            "workflow_id": 77,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml@main",
            "event": "workflow_dispatch",
            "repository": {"full_name": "Goldkelch/qik-vrt"},
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": self.locator["display_title"],
            # The receiver becomes visible only after the transport actor's
            # terminal timestamp, but before the first stable observer tick.
            "created_at": "2026-09-01T08:05:01Z",
        }
        first = materialize_mesh_retry_scan_cursor(
            item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
            transport_attempt=1,
            actor_run=self.cursor_actor(),
            observer_run=self.cursor_observer(),
            page_runs=[],
            declared_total_count=0,
            queried_window_start="2026-09-01T08:00:00Z",
            queried_window_end="2026-09-01T08:05:00Z",
            observation_started_at="2026-09-01T08:05:00Z",
            observation_completed_at="2026-09-01T08:05:01Z",
            same_second_boundary_complete=False,
        )
        self.persist_cursor(backend, intent, first)
        with self.assertRaisesRegex(
            MeshReviewOutboxError, "API window differs from sealed query window"
        ):
            materialize_mesh_retry_scan_cursor(
                item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
                transport_attempt=1,
                actor_run=self.cursor_actor(),
                observer_run=self.cursor_observer(run_id=902),
                page_runs=[raw_child],
                declared_total_count=1,
                queried_window_start="2026-09-01T08:00:00Z",
                # Querying only through actor.updated_at would miss this child
                # while falsely sealing the later observer cutoff.
                queried_window_end="2026-09-01T08:05:00Z",
                observation_started_at="2026-09-01T08:05:02Z",
                observation_completed_at="2026-09-01T08:05:03Z",
                same_second_boundary_complete=True,
            )
        second = materialize_mesh_retry_scan_cursor(
            item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
            transport_attempt=1,
            actor_run=self.cursor_actor(),
            observer_run=self.cursor_observer(run_id=902),
            page_runs=[raw_child],
            declared_total_count=1,
            queried_window_start="2026-09-01T08:00:00Z",
            queried_window_end="2026-09-01T08:05:02Z",
            observation_started_at="2026-09-01T08:05:02Z",
            observation_completed_at="2026-09-01T08:05:03Z",
            same_second_boundary_complete=True,
        )
        self.persist_cursor(backend, intent, second, artifact_id=991)
        self.assertEqual(second["query_window_end"], "2026-09-01T08:05:02Z")
        item = outbox.read_next(backend, "mesh-review-successor-dispatch")
        target = select_mesh_completion_target(item)
        self.assertEqual(target["state"], "ADOPT_CURSOR_CHILD")
        self.assertEqual(target["child"]["run_id"], 501)
        accepted = outbox.record_acceptance(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=target["child"],
        )
        self.assertEqual(accepted["state"], "TRANSPORT_ACCEPTED_LOCATOR")

    def test_zero_cursor_materializes_core_bound_one_shot_authority(self):
        backend, intent = self.orphan_backend()
        first = materialize_mesh_retry_scan_cursor(
            item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
            transport_attempt=1,
            actor_run=self.cursor_actor(),
            observer_run=self.cursor_observer(),
            page_runs=[],
            declared_total_count=0,
            queried_window_start="2026-09-01T08:00:00Z",
            queried_window_end="2026-09-01T08:05:00Z",
            observation_started_at="2026-09-01T08:05:00Z",
            observation_completed_at="2026-09-01T08:05:01Z",
            same_second_boundary_complete=False,
        )
        self.persist_cursor(backend, intent, first)
        second = materialize_mesh_retry_scan_cursor(
            item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
            transport_attempt=1,
            actor_run=self.cursor_actor(),
            observer_run=self.cursor_observer(run_id=902),
            page_runs=[],
            declared_total_count=0,
            queried_window_start="2026-09-01T08:00:00Z",
            queried_window_end="2026-09-01T08:05:02Z",
            observation_started_at="2026-09-01T08:05:02Z",
            observation_completed_at="2026-09-01T08:05:03Z",
            same_second_boundary_complete=True,
        )
        self.persist_cursor(backend, intent, second, artifact_id=991)
        item = outbox.read_next(backend, "mesh-review-successor-dispatch")
        target = select_mesh_completion_target(item)
        self.assertEqual(target["state"], "TERMINALIZE_ORPHAN")
        self.assertEqual(
            target["first_blocker"],
            "REPEATED_MESH_REVIEW_TRANSPORT_UNACKNOWLEDGED",
        )
        observation = materialize_mesh_orphan_authority_observation(
            item=item, transport_attempt=1, observed_main_head_sha="a" * 40
        )
        self.assertEqual(
            observation["retry_scan_cursor_record_sha256"],
            outbox.digest(item["retry_scan_cursor"]["1"]),
        )
        self.assertEqual(observation["bound_successor_count"], 0)

    def test_cursor_total_inventory_is_exact_before_zero_or_authority(self):
        backend, intent = self.orphan_backend()
        incomplete = materialize_mesh_retry_scan_cursor(
            item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
            transport_attempt=1,
            actor_run=self.cursor_actor(),
            observer_run=self.cursor_observer(),
            page_runs=[],
            declared_total_count=1,
            queried_window_start="2026-09-01T08:00:00Z",
            queried_window_end="2026-09-01T08:05:02Z",
            observation_started_at="2026-09-01T08:05:02Z",
            observation_completed_at="2026-09-01T08:05:03Z",
            same_second_boundary_complete=True,
        )
        self.assertFalse(incomplete["inventory_consistent"])
        self.assertEqual(
            incomplete["inventory_blocker"],
            "SHORT_PAGE_BEFORE_DECLARED_TOTAL",
        )
        self.assertFalse(incomplete["scan_complete"])
        self.persist_cursor(backend, intent, incomplete)
        item = outbox.read_next(backend, "mesh-review-successor-dispatch")
        self.assertEqual(
            item["retry_scan_cursor"]["1"]["state"],
            "SCAN_INVENTORY_INCONSISTENT_AUTHORITY",
        )
        target = select_mesh_completion_target(item)
        self.assertEqual(target["state"], "TERMINALIZE_ORPHAN")
        self.assertEqual(
            target["first_blocker"],
            "MESH_REVIEW_RECOVERY_QUERY_INVENTORY_INCONSISTENT",
        )
        observation = materialize_mesh_orphan_authority_observation(
            item=item, transport_attempt=1, observed_main_head_sha="a" * 40
        )
        self.assertEqual(
            observation["blocker"],
            "MESH_REVIEW_RECOVERY_QUERY_INVENTORY_INCONSISTENT",
        )
        self.assertEqual(observation["declared_total_count"], 1)
        self.assertEqual(observation["observed_unique_run_count"], 0)
        producer = self.cursor_observer()
        producer = {
            "workflow_path": producer["path"].split("@", 1)[0],
            "workflow_sha": producer["head_sha"],
            "workflow_id": producer["workflow_id"],
            "run_id": producer["id"],
            "run_attempt": producer["run_attempt"],
            "event": producer["event"],
        }
        blocker = observation["blocker"]
        record = outbox.record_authority_observation(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            observation=observation,
            producer=producer,
            artifact={
                "id": 992,
                "name": (
                    "qikvrt-outbox-authority-observation-"
                    "mesh-review-successor-dispatch-1-"
                    f"{blocker}-run-901-attempt-1"
                ),
                "archive_sha256": "f" * 64,
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(observation)
                ),
                "producer_run_id": 901,
                "producer_run_attempt": 1,
                "producer_workflow_id": 88,
            },
        )
        terminal = materialize_mesh_authority_terminal(
            item=item, authority_record=record
        )
        self.assertEqual(terminal["d0"], 3)
        outbox.terminalize(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            evidence=terminal,
        )
        self.assertEqual(
            outbox.lookup(
                backend,
                lane="mesh-review-successor-dispatch",
                sequence=1,
                fingerprint=intent["fingerprint"],
            )["state"],
            "TERMINAL",
        )

    def test_cursor_declared_total_and_page_ids_are_monotone(self):
        page_one = [{"id": value} for value in range(200, 100, -1)]

        def first_page():
            backend, intent = self.orphan_backend()
            first = materialize_mesh_retry_scan_cursor(
                item=outbox.read_next(
                    backend, "mesh-review-successor-dispatch"
                ),
                transport_attempt=1,
                actor_run=self.cursor_actor(),
                observer_run=self.cursor_observer(),
                page_runs=page_one,
                declared_total_count=101,
                queried_window_start="2026-09-01T08:00:00Z",
                queried_window_end="2026-09-01T08:05:02Z",
                observation_started_at="2026-09-01T08:05:02Z",
                observation_completed_at="2026-09-01T08:05:03Z",
                same_second_boundary_complete=True,
            )
            self.assertTrue(first["inventory_consistent"])
            self.assertFalse(first["scan_complete"])
            self.assertEqual(first["observed_unique_run_count"], 100)
            self.persist_cursor(backend, intent, first)
            return backend, intent

        backend, intent = first_page()
        complete = materialize_mesh_retry_scan_cursor(
            item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
            transport_attempt=1,
            actor_run=self.cursor_actor(),
            observer_run=self.cursor_observer(run_id=902),
            page_runs=[{"id": 100}],
            declared_total_count=101,
            queried_window_start="2026-09-01T08:00:00Z",
            queried_window_end="2026-09-01T08:05:02Z",
            observation_started_at="2026-09-01T08:05:04Z",
            observation_completed_at="2026-09-01T08:05:05Z",
            same_second_boundary_complete=True,
        )
        self.assertTrue(complete["scan_complete"])
        self.assertEqual(complete["observed_unique_run_count"], 101)
        self.assertEqual(complete["cumulative_run_ids"], list(range(200, 99, -1)))
        self.persist_cursor(backend, intent, complete, artifact_id=991)

        for label, second_page, declared, blocker in (
            ("total drift", [{"id": 100}], 102, "DECLARED_TOTAL_CHANGED"),
            ("page overlap", [{"id": 101}], 101, "PAGE_RUN_ID_OVERLAP"),
        ):
            with self.subTest(label=label):
                other_backend, other_intent = first_page()
                inconsistent = materialize_mesh_retry_scan_cursor(
                    item=outbox.read_next(
                        other_backend, "mesh-review-successor-dispatch"
                    ),
                    transport_attempt=1,
                    actor_run=self.cursor_actor(),
                    observer_run=self.cursor_observer(run_id=903),
                    page_runs=second_page,
                    declared_total_count=declared,
                    queried_window_start="2026-09-01T08:00:00Z",
                    queried_window_end="2026-09-01T08:05:02Z",
                    observation_started_at="2026-09-01T08:05:04Z",
                    observation_completed_at="2026-09-01T08:05:05Z",
                    same_second_boundary_complete=True,
                )
                self.assertFalse(inconsistent["inventory_consistent"])
                self.assertEqual(inconsistent["inventory_blocker"], blocker)
                self.persist_cursor(
                    other_backend, other_intent, inconsistent, artifact_id=992
                )
                state = outbox.read_next(
                    other_backend, "mesh-review-successor-dispatch"
                )["retry_scan_cursor"]["1"]["state"]
                self.assertEqual(
                    state, "SCAN_INVENTORY_INCONSISTENT_AUTHORITY"
                )

    def test_cursor_retains_eight_witnesses_for_larger_ambiguity_set(self):
        backend, intent = self.orphan_backend()
        raw = {
            "run_attempt": 1,
            "workflow_id": 77,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml@main",
            "event": "workflow_dispatch",
            "repository": {"full_name": "Goldkelch/qik-vrt"},
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": self.locator["display_title"],
        }
        page = [{**raw, "id": run_id} for run_id in range(509, 500, -1)]
        cursor = materialize_mesh_retry_scan_cursor(
            item=outbox.read_next(backend, "mesh-review-successor-dispatch"),
            transport_attempt=1,
            actor_run=self.cursor_actor(),
            observer_run=self.cursor_observer(),
            page_runs=page,
            declared_total_count=9,
            queried_window_start="2026-09-01T08:00:00Z",
            queried_window_end="2026-09-01T08:05:02Z",
            observation_started_at="2026-09-01T08:05:02Z",
            observation_completed_at="2026-09-01T08:05:03Z",
            same_second_boundary_complete=True,
        )
        self.assertEqual(cursor["bound_successor_count"], 9)
        self.assertEqual(len(cursor["candidate_locators"]), 8)
        self.assertEqual(
            cursor["cumulative_candidate_run_ids"], list(range(509, 500, -1))
        )
        self.assertEqual(
            cursor["candidate_set_sha256"],
            outbox.digest(cursor["cumulative_candidate_run_ids"]),
        )
        self.persist_cursor(backend, intent, cursor)
        item = outbox.read_next(backend, "mesh-review-successor-dispatch")
        self.assertEqual(
            item["retry_scan_cursor"]["1"]["state"],
            "AMBIGUITY_SET_EXCEEDED_AUTHORITY",
        )
        target = select_mesh_completion_target(item)
        self.assertEqual(
            target["first_blocker"],
            "MESH_REVIEW_TRANSPORT_CHILD_SET_EXCEEDED",
        )

    def test_target_workflow_supersession_is_persisted_and_advances_fifo(self):
        item = outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        observation = materialize_mesh_target_workflow_supersession(
            item=item,
            observed_workflow={
                "id": 78,
                "path": (
                    ".github/workflows/"
                    "qikvrt_requested_review_executor.yml@refs/heads/main"
                ),
            },
            observed_main_head_sha="a" * 40,
        )
        self.assertEqual(
            observation["blocker"], "OUTBOX_TARGET_WORKFLOW_SUPERSEDED"
        )
        producer = {
            "workflow_path": (
                ".github/workflows/"
                "qikvrt_mesh_review_successor_completion.yml"
            ),
            "workflow_sha": "a" * 40,
            "workflow_id": 88,
            "run_id": 901,
            "run_attempt": 1,
            "event": "schedule",
        }
        name = (
            "qikvrt-outbox-authority-observation-"
            "mesh-review-successor-dispatch-1-"
            "OUTBOX_TARGET_WORKFLOW_SUPERSEDED-run-901-attempt-1"
        )
        record = outbox.record_authority_observation(
            self.backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            observation=observation,
            producer=producer,
            artifact={
                "id": 991,
                "name": name,
                "archive_sha256": "f" * 64,
                "payload_sha256": outbox.sha256_bytes(
                    outbox.canonical_bytes(observation)
                ),
                "producer_run_id": producer["run_id"],
                "producer_run_attempt": producer["run_attempt"],
                "producer_workflow_id": producer["workflow_id"],
            },
        )
        terminal = materialize_mesh_authority_terminal(
            item=item, authority_record=record
        )
        second_payload = outbox.seal_review_transport_payload(
            payload("mesh-review-successor-dispatch", run_id=999, subject="two")
        )
        outbox.append_intent(
            self.backend,
            payload=second_payload,
            artifact=artifact(second_payload),
        )
        outbox.terminalize(
            self.backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            evidence=terminal,
        )
        current = outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        self.assertEqual((current["state"], current["sequence"]), ("PENDING", 2))

    def test_target_workflow_supersession_rejects_same_target_or_main_drift(self):
        item = outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        same = {
            "id": 77,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml",
        }
        with self.assertRaisesRegex(
            MeshReviewOutboxError, "has not been exactly superseded"
        ):
            materialize_mesh_target_workflow_supersession(
                item=item,
                observed_workflow=same,
                observed_main_head_sha="a" * 40,
            )
        with self.assertRaisesRegex(
            MeshReviewOutboxError, "has not been exactly superseded"
        ):
            materialize_mesh_target_workflow_supersession(
                item=item,
                observed_workflow={**same, "id": 78},
                observed_main_head_sha="0" * 40,
            )

    def test_synchronized_or_closed_subject_terminalizes_and_advances(self):
        cases = (
            ("open", "f" * 40, "0" * 40),
            ("closed", "b" * 40, "c" * 40),
        )
        for index, (state, head, tree) in enumerate(cases, start=1):
            with self.subTest(state=state):
                backend, _intent = self.accepted_backend()
                item = outbox.read_next(
                    backend, "mesh-review-successor-dispatch"
                )
                observation = materialize_mesh_subject_supersession(
                    item=item,
                    observed_pr={
                        "number": 935,
                        "state": state,
                        "head": {"sha": head},
                        "base": {"sha": "d" * 40},
                    },
                    observed_tree_sha=tree,
                )
                second = outbox.seal_review_transport_payload(
                    payload(
                        "mesh-review-successor-dispatch",
                        run_id=1000 + index,
                        subject=f"subject-{index}",
                    )
                )
                outbox.append_intent(
                    backend, payload=second, artifact=artifact(second)
                )
                terminal = self.record_authority_and_terminalize(
                    backend, item, observation, run=910 + index
                )
                self.assertEqual(
                    (terminal["d0"], terminal["reason"]),
                    (3, "OUTBOX_SUBJECT_SUPERSEDED"),
                )
                current = outbox.read_next(
                    backend, "mesh-review-successor-dispatch"
                )
                self.assertEqual(
                    (current["state"], current["sequence"]),
                    ("PENDING", 2),
                )
                if state == "closed":
                    self.assertEqual(
                        observation["observed_subject"]["queue_intent"]["state"],
                        "LIVE_PR_CLOSED",
                    )

    def test_missing_completion_artifact_is_durable_authority_and_advances(self):
        item = outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        child = self.completed_child("failure")
        jobs = [
            {
                "id": 601,
                "name": "publish-run-completion-envelope",
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "success",
            },
            {
                "id": 602,
                "name": "plan-review",
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "failure",
            },
        ]
        observation = materialize_mesh_missing_evidence_observation(
            item=item,
            child=child,
            child_recovery=False,
            jobs=jobs,
            artifacts=[],
            artifact_archives={},
            jobs_pages_scanned=1,
            jobs_page_cap=100,
            artifacts_pages_scanned=1,
            artifacts_page_cap=100,
            observation_started_at="2026-09-01T09:00:00Z",
            observation_completed_at="2026-09-01T09:00:01Z",
        )
        self.assertEqual(
            (
                observation["blocker"],
                observation["evidence_classification"],
            ),
            ("MESH_REVIEW_COMPLETION_EVIDENCE_MISSING", "MISSING_ARTIFACT"),
        )
        second = outbox.seal_review_transport_payload(
            payload("mesh-review-successor-dispatch", run_id=999, subject="two")
        )
        outbox.append_intent(self.backend, payload=second, artifact=artifact(second))
        terminal = self.record_authority_and_terminalize(
            self.backend, item, observation
        )
        self.assertEqual((terminal["d0"], terminal["reason"]), (3, observation["blocker"]))
        current = outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        self.assertEqual((current["state"], current["sequence"]), ("PENDING", 2))

    def test_missing_success_business_artifact_requires_valid_envelope(self):
        item = outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        child = self.completed_child("success")
        completion, archive = self.completion_envelope_artifact(child)
        jobs = [
            {
                "id": 601,
                "name": "project-status",
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "success",
            },
            {
                "id": 602,
                "name": "publish-run-completion-envelope",
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "success",
            },
        ]
        observation = materialize_mesh_missing_evidence_observation(
            item=item,
            child=child,
            child_recovery=False,
            jobs=jobs,
            artifacts=[completion],
            artifact_archives={completion["id"]: archive},
            jobs_pages_scanned=1,
            jobs_page_cap=100,
            artifacts_pages_scanned=1,
            artifacts_page_cap=100,
            observation_started_at="2026-09-01T09:00:00Z",
            observation_completed_at="2026-09-01T09:00:01Z",
        )
        self.assertEqual(
            (
                observation["blocker"],
                observation["business_evidence_classification"],
                observation["completion_envelope_artifact_count"],
            ),
            ("MESH_REVIEW_BUSINESS_EVIDENCE_MISSING", "MISSING_ARTIFACT", 1),
        )
        self.record_authority_and_terminalize(self.backend, item, observation)
        self.assertEqual(
            outbox.read_next(self.backend, "mesh-review-successor-dispatch")["state"],
            "EMPTY",
        )

    def test_completion_query_cap_is_durable_authority(self):
        item = outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        child = self.completed_child("success")
        jobs = [
            {
                "id": 601,
                "name": "project-status",
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "success",
            }
        ]
        observation = materialize_mesh_completion_query_bound_observation(
            item=item,
            child=child,
            child_recovery=False,
            query_kind="JOBS",
            jobs=jobs,
            artifacts=[],
            jobs_declared_total_count=101,
            jobs_pages_scanned=1,
            jobs_page_cap=1,
            jobs_scan_complete=False,
            artifacts_declared_total_count=0,
            artifacts_pages_scanned=0,
            artifacts_page_cap=1,
            artifacts_scan_complete=False,
            observation_started_at="2026-09-01T09:00:00Z",
            observation_completed_at="2026-09-01T09:00:01Z",
        )
        self.assertEqual(
            observation["blocker"],
            "MESH_REVIEW_COMPLETION_QUERY_BOUND_EXCEEDED",
        )
        self.record_authority_and_terminalize(self.backend, item, observation)
        self.assertEqual(
            outbox.read_next(self.backend, "mesh-review-successor-dispatch")["state"],
            "EMPTY",
        )

    def test_missing_evidence_rejects_wrong_acceptance_kind(self):
        item = outbox.read_next(
            self.backend, "mesh-review-successor-dispatch"
        )
        child = self.completed_child("failure")
        with self.assertRaisesRegex(
            MeshReviewOutboxError, "uncompleted immutable acceptance"
        ):
            materialize_mesh_missing_evidence_observation(
                item=item,
                child=child,
                child_recovery=True,
                jobs=[],
                artifacts=[],
                artifact_archives={},
                jobs_pages_scanned=1,
                jobs_page_cap=100,
                artifacts_pages_scanned=1,
                artifacts_page_cap=100,
                observation_started_at="2026-09-01T09:00:00Z",
                observation_completed_at="2026-09-01T09:00:01Z",
            )

    def test_completion_target_prefers_exact_same_run_recovery_acceptance(self):
        original = self.completed_child("cancelled")
        backend = MemoryBackend()
        value = self.intent["payload"]
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        outbox.prepare_transport(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=402,
            actor_run_attempt=1,
        )
        outbox.record_acceptance(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            child=original,
        )
        retry = {
            "schema": outbox.CHILD_RETRY_EVIDENCE_SCHEMA,
            "lane": "mesh-review-successor-dispatch",
            "sequence": 1,
            "fingerprint": intent["fingerprint"],
            "transport_attempt": 1,
            "classification": "ZERO_JOB_CONCURRENCY_CANCELLED",
            "first_blocker": "ATTEMPT_1_ZERO_JOB_CONCURRENCY_CANCELLED",
            "accepted_child_sha256": outbox.digest(original),
            "observed_terminal_child": original,
            "observed_terminal_child_sha256": outbox.digest(original),
            "jobs_total_count": 0,
            "verified": True,
            "productive_effect": False,
        }
        outbox.prepare_child_rerun(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            transport_attempt=1,
            retry_evidence=retry,
            actor_run_id=801,
            actor_run_attempt=1,
        )
        recovered = self.completed_child("success", run_attempt=2)
        outbox.record_child_rerun_acceptance(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            transport_attempt=1,
            child=recovered,
        )
        target = select_mesh_completion_target(
            outbox.read_next(backend, "mesh-review-successor-dispatch")
        )
        self.assertEqual(target["state"], "OBSERVE_CHILD")
        self.assertTrue(target["child_recovery"])
        self.assertEqual(target["child"]["run_attempt"], 2)

    def test_orphan_adoption_is_wait_or_authority_on_zero_or_multiple_children(self):
        backend = MemoryBackend()
        value = self.intent["payload"]
        intent = outbox.append_intent(backend, payload=value, artifact=artifact(value))
        outbox.prepare_transport(
            backend,
            lane="mesh-review-successor-dispatch",
            sequence=1,
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=402,
            actor_run_attempt=1,
        )
        item = outbox.read_next(backend, "mesh-review-successor-dispatch")
        actor = {
            "id": 402,
            "run_attempt": 1,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml@main",
            "repository": {"full_name": "Goldkelch/qik-vrt"},
            "status": "completed",
            "conclusion": "success",
            "run_started_at": "2026-09-01T08:00:00Z",
            "updated_at": "2026-09-01T08:05:00Z",
        }
        empty = select_mesh_orphan_adoption(
            item=item,
            actor_run=actor,
            candidate_runs=[],
            scan_complete=True,
            transport_attempt=1,
        )
        self.assertEqual(empty["state"], "WAIT")
        raw = {
            "id": 501,
            "run_attempt": 1,
            "workflow_id": 77,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml@main",
            "event": "workflow_dispatch",
            "repository": {"full_name": "Goldkelch/qik-vrt"},
            "head_branch": "main",
            "head_sha": "a" * 40,
            "status": "queued",
            "conclusion": None,
            "display_title": self.locator["display_title"],
            "created_at": "2026-09-01T08:03:00Z",
        }
        ambiguous = select_mesh_orphan_adoption(
            item=item,
            actor_run=actor,
            candidate_runs=[raw, {**raw, "id": 502}],
            scan_complete=True,
            transport_attempt=1,
        )
        self.assertEqual(ambiguous["state"], "REQUEST_AUTHORITY")
        self.assertEqual(ambiguous["matching_child_count"], 2)
        with self.assertRaisesRegex(MeshReviewOutboxError, "input is incomplete"):
            select_mesh_orphan_adoption(
                item=item,
                actor_run=actor,
                candidate_runs=[],
                scan_complete=False,
                transport_attempt=1,
            )


if __name__ == "__main__":
    unittest.main()
