#!/usr/bin/env python3
import io
import json
import unittest
import zipfile

from tests.test_qikvrt_ruleset_outbox import (
    MemoryBackend,
    artifact,
    payload,
    persist_authority_observation,
    transport_child,
)
from tools import qikvrt_ruleset_outbox as outbox
from tools.qikvrt_exact_review_outbox import (
    ExactReviewOutboxError,
    materialize_authority_terminal,
    materialize_completion,
    materialize_retry_cursor_authority_observation,
    materialize_retry_scan_cursor,
)
from tools.qikvrt_native_account_review import (
    build_trusted_executor_producer_binding,
)
from tools.qikvrt_requested_review_executor import (
    REQUESTED_REVIEW_COMPLETION_JOB_RESULTS,
    build_requested_review_completion_envelope,
)


class ExactReviewOutboxTests(unittest.TestCase):
    def setUp(self):
        self.backend = MemoryBackend()
        value = payload("exact-review-dispatch")
        value["subject"] = {
            "pull_request": 935,
            "head_repository": "Goldkelch/qik-vrt",
            "head_ref": "authority-pr931",
            "head_sha": "b" * 40,
            "head_tree_sha": "c" * 40,
            "base_ref": "main",
            "base_sha": "d" * 40,
        }
        value = outbox.seal_review_transport_payload(value)
        self.intent = outbox.append_intent(
            self.backend, payload=value, artifact=artifact(value)
        )
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        request = outbox.request_for_transport_attempt(item["intent"], 1)
        outbox.prepare_transport(
            self.backend,
            lane="exact-review-dispatch",
            sequence=1,
            attempt=1,
            request=request,
            retry_evidence=None,
            actor_run_id=901,
            actor_run_attempt=1,
        )
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        inputs = item["intent"]["payload"]["request"]["inputs"]
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
            "display_title": (
                f"qikvrt-rr-v3 e={'a'*40} p=935 h={'b'*40} "
                f"f={inputs['fingerprint']} i={item['fingerprint']} a=1"
            ),
        }
        outbox.record_acceptance(
            self.backend,
            lane="exact-review-dispatch",
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

    def completed_child(self, conclusion):
        return {**self.locator, "status": "completed", "conclusion": conclusion}

    def success_archive(self, *, predecessor_fingerprint=None, extra_files=None):
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        inputs = item["intent"]["payload"]["request"]["inputs"]
        semantic_fingerprint = "9" * 64
        review = {
            "pr_number": 935,
            "head_sha": "b" * 40,
            "evidence_fingerprint": semantic_fingerprint,
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
                "predecessor_successor_fingerprint": (
                    inputs["fingerprint"]
                    if predecessor_fingerprint is None
                    else predecessor_fingerprint
                ),
                "transport_intent_sha256": item["fingerprint"],
                "transport_attempt": 1,
            },
            "productive_effect": False,
        }
        compact = json.dumps(transport, sort_keys=True, separators=(",", ":")).encode()
        import hashlib

        transport["provenance_payload_sha256"] = hashlib.sha256(compact).hexdigest()
        raw = {
            "review.json": json.dumps(review).encode(),
            "review.diff": b"exact review diff\n",
            "ledger-write.json": json.dumps(ledger).encode(),
            "review-transport.json": json.dumps(transport).encode(),
        }
        artifact_name = (
            f"qikvrt-mesh-review-pr-935-{'b'*40}-{semantic_fingerprint}-"
            "run-501-attempt-1"
        )
        binding = build_trusted_executor_producer_binding(
            repository="Goldkelch/qik-vrt",
            run_id=501,
            run_attempt=1,
            artifact_name=artifact_name,
            pr_number=935,
            head_sha="b" * 40,
            evidence_fingerprint=semantic_fingerprint,
            files=raw,
        )
        raw["producer-binding.json"] = (
            json.dumps(binding, sort_keys=True, indent=2) + "\n"
        ).encode()
        if extra_files:
            raw.update(extra_files)
        return artifact_name, self.archive(raw)

    def adverse_archive(self, *, subject_overrides=None, locator_overrides=None):
        child = self.completed_child("failure")
        subject = {
            "pr_number": 935,
            "head_sha": "b" * 40,
            "tree_sha": "c" * 40,
            "base_sha": "d" * 40,
            # Newly calculated review evidence, intentionally distinct from
            # the predecessor/request fingerprint in dispatch_locator.
            "semantic_fingerprint": "9" * 64,
            "technical_disposition": None,
        }
        subject.update(subject_overrides or {})
        envelope = build_requested_review_completion_envelope(
            repository="Goldkelch/qik-vrt",
            workflow_sha="a" * 40,
            workflow_ref=(
                "Goldkelch/qik-vrt/.github/workflows/"
                "qikvrt_requested_review_executor.yml@refs/heads/main"
            ),
            run_id=501,
            run_attempt=1,
            event="workflow_dispatch",
            display_title=child["display_title"],
            subject=subject,
            job_results={
                name: "skipped"
                for name in REQUESTED_REVIEW_COMPLETION_JOB_RESULTS
            },
        )
        if locator_overrides:
            envelope["dispatch_locator"].update(locator_overrides)
        archive = self.archive(
            {
                "envelope.json": (
                    json.dumps(envelope, sort_keys=True, indent=2) + "\n"
                ).encode()
            }
        )
        return child, archive

    @staticmethod
    def artifact_api(name, archive):
        import hashlib

        return {
            "id": 701,
            "name": name,
            "digest": f"sha256:{hashlib.sha256(archive).hexdigest()}",
            "expired": False,
            "workflow_run": {"id": 501},
        }

    def test_success_builds_core_valid_completion_and_terminal(self):
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        name, archive = self.success_archive()
        result = materialize_completion(
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
            lane="exact-review-dispatch",
            sequence=1,
            attempt=1,
            child=result["child"],
            evidence=result["completion_evidence"],
        )
        current = outbox.read_next(self.backend, "exact-review-dispatch")
        outbox.validate_terminal_evidence(result["terminal"], next_item=current)
        second = payload("exact-review-dispatch", run_id=202)
        second["subject"] = {
            "pull_request": 936,
            "head_repository": "Goldkelch/qik-vrt",
            "head_ref": "next-exact-subject",
            "head_sha": "f" * 40,
            "head_tree_sha": "1" * 40,
            "base_ref": "main",
            "base_sha": "d" * 40,
        }
        second["request"]["inputs"].update(pr="936", head="f" * 40)
        second = outbox.seal_review_transport_payload(second)
        outbox.append_intent(
            self.backend, payload=second, artifact=artifact(second)
        )
        outbox.terminalize(
            self.backend,
            lane="exact-review-dispatch",
            sequence=1,
            evidence=result["terminal"],
        )
        next_item = outbox.read_next(self.backend, "exact-review-dispatch")
        self.assertEqual(next_item["state"], "PENDING")
        self.assertEqual(next_item["sequence"], 2)
        self.assertEqual(result["terminal"]["d0"], 2)

    def test_adverse_envelope_builds_core_valid_authority_terminal(self):
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        child, archive = self.adverse_archive()
        name = "qikvrt-requested-review-completion-501-attempt-1"
        result = materialize_completion(
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
            artifact_api=self.artifact_api(name, archive),
            artifact_zip=archive,
            transport_attempt=1,
            child_recovery=False,
        )
        outbox.record_completion(
            self.backend,
            lane="exact-review-dispatch",
            sequence=1,
            attempt=1,
            child=result["child"],
            evidence=result["completion_evidence"],
        )
        current = outbox.read_next(self.backend, "exact-review-dispatch")
        outbox.validate_terminal_evidence(result["terminal"], next_item=current)
        self.assertEqual(result["terminal"]["d0"], 3)
        self.assertEqual(
            result["terminal"]["reason"], "ATTEMPT_1_ACCEPTED_ADVERSE"
        )

    def test_success_binds_predecessor_separately_from_result_fingerprint(self):
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        request_fingerprint = item["intent"]["payload"]["request"]["inputs"][
            "fingerprint"
        ]
        self.assertNotEqual(request_fingerprint, "9" * 64)
        name, archive = self.success_archive(
            predecessor_fingerprint="8" * 64
        )
        with self.assertRaisesRegex(
            ExactReviewOutboxError, "business payload is not current"
        ):
            materialize_completion(
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

    def test_adverse_subject_and_dispatch_locator_drift_are_rejected(self):
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        name = "qikvrt-requested-review-completion-501-attempt-1"
        cases = (
            ({"tree_sha": "1" * 40}, None),
            ({"base_sha": "2" * 40}, None),
            (None, {"request_fingerprint": "3" * 64}),
            (None, {"transport_intent_sha256": "4" * 64}),
            (None, {"transport_attempt": 2}),
        )
        for subject_overrides, locator_overrides in cases:
            with self.subTest(
                subject=subject_overrides, locator=locator_overrides
            ):
                child, archive = self.adverse_archive(
                    subject_overrides=subject_overrides,
                    locator_overrides=locator_overrides,
                )
                with self.assertRaises(ExactReviewOutboxError):
                    materialize_completion(
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
                        artifact_api=self.artifact_api(name, archive),
                        artifact_zip=archive,
                        transport_attempt=1,
                        child_recovery=False,
                    )

    def test_success_archive_rejects_unbound_extra_file(self):
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        name, archive = self.success_archive(extra_files={"extra.txt": b"no\n"})
        with self.assertRaisesRegex(ExactReviewOutboxError, "file set is not exact"):
            materialize_completion(
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

    def test_authority_terminal_requires_persisted_exact_observation(self):
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        sealed_subject = item["intent"]["payload"]["subject"]
        observed_subject = {**sealed_subject, "head_sha": "7" * 40}
        observation = {
            "schema": outbox.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_SUBJECT_SUPERSEDED",
            "lane": "exact-review-dispatch",
            "sequence": item["sequence"],
            "fingerprint": item["fingerprint"],
            "sealed_subject_sha256": outbox.digest(sealed_subject),
            "observed_subject": observed_subject,
            "observed_subject_sha256": outbox.digest(observed_subject),
            "verified": True,
            "productive_effect": False,
        }
        record = persist_authority_observation(
            self.backend, item["intent"], observation, run_id=8802
        )
        terminal = materialize_authority_terminal(
            item=item, authority_record=record
        )
        self.assertEqual(terminal["reason"], "OUTBOX_SUBJECT_SUPERSEDED")
        self.assertEqual(
            terminal["exhaustion"]["authority_observation_sha256"],
            outbox.digest(record),
        )
        tampered = dict(record, observation_sha256="0" * 64)
        with self.assertRaisesRegex(
            ExactReviewOutboxError, "observation record is not exact"
        ):
            materialize_authority_terminal(
                item=item, authority_record=tampered
            )

    def test_recovered_same_run_attempt_two_reaches_adverse_terminal(self):
        backend = MemoryBackend()
        value = payload("exact-review-dispatch", run_id=801)
        value["subject"] = {
            "pull_request": 935,
            "head_repository": "Goldkelch/qik-vrt",
            "head_ref": "authority-pr931",
            "head_sha": "b" * 40,
            "head_tree_sha": "c" * 40,
            "base_ref": "main",
            "base_sha": "d" * 40,
        }
        value = outbox.seal_review_transport_payload(value)
        intent = outbox.append_intent(
            backend, payload=value, artifact=artifact(value)
        )
        outbox.prepare_transport(
            backend,
            lane="exact-review-dispatch",
            sequence=1,
            attempt=1,
            request=outbox.request_for_transport_attempt(intent, 1),
            actor_run_id=801,
            actor_run_attempt=1,
        )
        inputs = intent["payload"]["request"]["inputs"]
        title = (
            f"qikvrt-rr-v3 e={'a'*40} p=935 h={'b'*40} "
            f"f={inputs['fingerprint']} i={intent['fingerprint']} a=1"
        )
        original = {
            "run_id": 802,
            "run_attempt": 1,
            "workflow_id": 77,
            "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
            "event": "workflow_dispatch",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "cancelled",
            "display_title": title,
        }
        outbox.record_acceptance(
            backend,
            lane="exact-review-dispatch",
            sequence=1,
            attempt=1,
            child=original,
        )
        retry = {
            "schema": outbox.CHILD_RETRY_EVIDENCE_SCHEMA,
            "lane": "exact-review-dispatch",
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
            lane="exact-review-dispatch",
            sequence=1,
            transport_attempt=1,
            retry_evidence=retry,
            actor_run_id=803,
            actor_run_attempt=1,
        )
        recovered = {
            **original,
            "run_attempt": 2,
            "conclusion": "failure",
        }
        outbox.record_child_rerun_acceptance(
            backend,
            lane="exact-review-dispatch",
            sequence=1,
            transport_attempt=1,
            child=recovered,
        )
        item = outbox.read_next(backend, "exact-review-dispatch")
        envelope = build_requested_review_completion_envelope(
            repository="Goldkelch/qik-vrt",
            workflow_sha="a" * 40,
            workflow_ref=(
                "Goldkelch/qik-vrt/.github/workflows/"
                "qikvrt_requested_review_executor.yml@refs/heads/main"
            ),
            run_id=802,
            run_attempt=2,
            event="workflow_dispatch",
            display_title=title,
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
        archive = self.archive(
            {
                "envelope.json": (
                    json.dumps(envelope, sort_keys=True, indent=2) + "\n"
                ).encode()
            }
        )
        import hashlib

        result = materialize_completion(
            item=item,
            child=recovered,
            jobs=[
                {
                    "id": 901,
                    "name": "project-status",
                    "run_attempt": 2,
                    "status": "completed",
                    "conclusion": "failure",
                },
                {
                    "id": 902,
                    "name": "publish-run-completion-envelope",
                    "run_attempt": 2,
                    "status": "completed",
                    "conclusion": "success",
                },
            ],
            artifact_api={
                "id": 903,
                "name": "qikvrt-requested-review-completion-802-attempt-2",
                "digest": f"sha256:{hashlib.sha256(archive).hexdigest()}",
                "expired": False,
                "workflow_run": {"id": 802},
            },
            artifact_zip=archive,
            transport_attempt=1,
            child_recovery=True,
        )
        outbox.record_completion(
            backend,
            lane="exact-review-dispatch",
            sequence=1,
            attempt=1,
            child=result["child"],
            evidence=result["completion_evidence"],
            child_recovery=True,
        )
        outbox.validate_terminal_evidence(
            result["terminal"],
            next_item=outbox.read_next(backend, "exact-review-dispatch"),
        )
        self.assertEqual(result["terminal"]["d0"], 3)

    def test_exact_cursor_terminal_fixed_points_drain_both_lanes(self):
        def pending_lane(lane, run_id):
            backend = MemoryBackend()
            value = payload(lane, run_id=run_id)
            if lane == "exact-review-dispatch":
                value["subject"] = {
                    "pull_request": 935,
                    "head_repository": "Goldkelch/qik-vrt",
                    "head_ref": "authority-pr931",
                    "head_sha": "b" * 40,
                    "head_tree_sha": "c" * 40,
                    "base_ref": "main",
                    "base_sha": "d" * 40,
                }
                value = outbox.seal_review_transport_payload(value)
            intent = outbox.append_intent(
                backend, payload=value, artifact=artifact(value)
            )
            request = outbox.request_for_transport_attempt(intent, 1)
            prepared = outbox.prepare_transport(
                backend,
                lane=lane,
                sequence=intent["sequence"],
                attempt=1,
                request=request,
                retry_evidence=None,
                actor_run_id=901,
                actor_run_attempt=1,
            )
            return backend, intent, prepared

        def persist_cursor(
            backend,
            item,
            *,
            attempt,
            successor_count,
            page_cap=10,
            unrelated_count=0,
            unrelated_start=4000,
            declared_total_count=None,
            duplicate_first_page_id=False,
            page_order_drift=False,
            boundary_complete=True,
            observation_started_at="2026-09-01T08:02:00Z",
            observation_completed_at="2026-09-01T08:02:01Z",
        ):
            lane = item["lane"]
            actor_path = (
                ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"
                if attempt == 1 and lane == "exact-review-dispatch"
                else ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
            )
            actor_event = (
                "repository_dispatch"
                if attempt == 1 and lane == "exact-review-dispatch"
                else ("pull_request_target" if attempt == 1 else "schedule")
            )
            actor_run_id = item["transport"][str(attempt)]["actor_run_id"]
            actor = {
                "id": actor_run_id,
                "run_attempt": 1,
                "workflow_id": 17,
                "path": actor_path,
                "event": actor_event,
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-09-01T08:00:00Z",
                "updated_at": "2026-09-01T08:01:00Z",
            }
            observer = {
                "id": 1000 + attempt,
                "run_attempt": 1,
                "workflow_id": 18,
                "path": ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml",
                "event": "schedule",
                "head_sha": item["intent"]["payload"]["main_head_sha"],
            }
            page = []
            for offset in range(successor_count):
                child = transport_child(
                    item["intent"],
                    attempt=attempt,
                    run_id=2000 + attempt * 100 + offset,
                )
                page.append(
                    {
                        "id": child["run_id"],
                        "run_attempt": child["run_attempt"],
                        "workflow_id": child["workflow_id"],
                        "path": child["workflow_path"],
                        "event": child["event"],
                        "repository": {"full_name": child["repository"]},
                        "head_sha": child["head_sha"],
                        "status": child["status"],
                        "conclusion": child["conclusion"],
                        "display_title": child["display_title"],
                        # This receiver was materialized after the transport
                        # actor ended (08:01:00) but before the first stable
                        # observer cutoff (08:02:00).
                        "created_at": "2026-09-01T08:01:30Z",
                    }
                )
            for offset in range(unrelated_count):
                page.append(
                    {
                        "id": unrelated_start + offset,
                        "run_attempt": 1,
                        "workflow_id": 999,
                        "path": ".github/workflows/unrelated.yml",
                        "event": "workflow_dispatch",
                        "repository": {"full_name": item["intent"]["repository"]},
                        "head_sha": item["intent"]["payload"]["main_head_sha"],
                        "status": "queued",
                        "conclusion": None,
                        "display_title": f"unrelated-{offset}",
                    }
                )
            page.sort(key=lambda value: value["id"], reverse=True)
            if duplicate_first_page_id and page:
                page.append(dict(page[0]))
            if page_order_drift:
                page.reverse()
            response = {
                "total_count": (
                    len(page)
                    if declared_total_count is None
                    else declared_total_count
                ),
                "workflow_runs": page,
            }
            if not boundary_complete:
                response = {"total_count": 0, "workflow_runs": []}
            cursor = materialize_retry_scan_cursor(
                item=item,
                transport_attempt=attempt,
                actor_run=actor,
                observer_run=observer,
                page_response=response,
                observation_started_at=observation_started_at,
                observation_completed_at=observation_completed_at,
                same_second_boundary_complete=boundary_complete,
                page_cap=page_cap,
            )
            return outbox.record_retry_scan_cursor(
                backend,
                lane=lane,
                sequence=item["sequence"],
                cursor=cursor,
                artifact={
                    "id": 3000 + attempt + cursor["ordinal"],
                    "name": (
                        f"qikvrt-outbox-retry-scan-cursor-{lane}-"
                        f"{item['sequence']}-attempt-{attempt}-ordinal-{cursor['ordinal']}-"
                        f"run-{observer['id']}-attempt-1"
                    ),
                    "archive_sha256": "9" * 64,
                    "payload_sha256": outbox.sha256_bytes(
                        outbox.canonical_bytes(cursor)
                    ),
                    "producer_run_id": observer["id"],
                    "producer_run_attempt": 1,
                    "producer_workflow_id": observer["workflow_id"],
                },
            )

        for lane in ("exact-head-dispatch", "exact-review-dispatch"):
            with self.subTest(lane=lane, boundary_transition=True):
                backend, intent, prepared = pending_lane(lane, 319)
                self.assertTrue(prepared["cas"]["appended"])
                item = outbox.read_next(backend, lane)
                first = persist_cursor(
                    backend,
                    item,
                    attempt=1,
                    successor_count=1,
                    boundary_complete=False,
                    observation_started_at="2026-09-01T08:01:00Z",
                    observation_completed_at="2026-09-01T08:01:01Z",
                )
                self.assertEqual(
                    first["record"]["cursor"]["query_window_end"],
                    "2026-09-01T08:01:00Z",
                )
                self.assertEqual(
                    first["record"]["state"],
                    "BOUNDARY_STABILIZATION_REOBSERVE",
                )
                item = outbox.read_next(backend, lane)
                second = persist_cursor(
                    backend,
                    item,
                    attempt=1,
                    successor_count=1,
                    boundary_complete=True,
                    observation_started_at="2026-09-01T08:02:00Z",
                )
                self.assertEqual(
                    second["record"]["cursor"]["query_window_end"],
                    "2026-09-01T08:02:00Z",
                )
                self.assertEqual(
                    second["record"]["cursor"]["bound_successor_count"], 1
                )

            for successor_count in (2, 9):
                with self.subTest(lane=lane, successor_count=successor_count):
                    backend, intent, prepared = pending_lane(
                        lane, 320 + successor_count
                    )
                    self.assertTrue(prepared["cas"]["appended"])
                    item = outbox.read_next(backend, lane)
                    persist_cursor(
                        backend, item, attempt=1, successor_count=successor_count
                    )
                    item = outbox.read_next(backend, lane)
                    observation = materialize_retry_cursor_authority_observation(
                        item=item,
                        transport_attempt=1,
                        observed_main_head_sha=item["intent"]["payload"][
                            "main_head_sha"
                        ],
                    )
                    self.assertEqual(
                        observation["blocker"],
                        (
                            "BOUND_EVIDENCE_AMBIGUOUS"
                            if successor_count == 2
                            else "BOUND_EVIDENCE_AMBIGUITY_SET_EXCEEDED"
                        ),
                    )
                    record = persist_authority_observation(
                        backend, intent, observation, run_id=9800 + successor_count
                    )
                    item = outbox.read_next(backend, lane)
                    terminal = materialize_authority_terminal(
                        item=item, authority_record=record
                    )
                    outbox.terminalize(
                        backend,
                        lane=lane,
                        sequence=intent["sequence"],
                        evidence=terminal,
                    )
                    self.assertEqual(outbox.read_next(backend, lane)["state"], "EMPTY")

            with self.subTest(lane=lane, scan_bound=True):
                backend, intent, prepared = pending_lane(lane, 339)
                self.assertTrue(prepared["cas"]["appended"])
                item = outbox.read_next(backend, lane)
                receipt = persist_cursor(
                    backend,
                    item,
                    attempt=1,
                    successor_count=0,
                    page_cap=1,
                    unrelated_count=100,
                    declared_total_count=101,
                )
                self.assertEqual(
                    receipt["state"], "SCAN_BOUND_EXCEEDED_AUTHORITY"
                )
                item = outbox.read_next(backend, lane)
                observation = materialize_retry_cursor_authority_observation(
                    item=item,
                    transport_attempt=1,
                    observed_main_head_sha=item["intent"]["payload"][
                        "main_head_sha"
                    ],
                )
                self.assertEqual(
                    observation["blocker"], "RECOVERY_QUERY_BOUND_EXCEEDED"
                )
                record = persist_authority_observation(
                    backend, intent, observation, run_id=9839
                )
                item = outbox.read_next(backend, lane)
                terminal = materialize_authority_terminal(
                    item=item, authority_record=record
                )
                outbox.terminalize(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    evidence=terminal,
                )
                self.assertEqual(outbox.read_next(backend, lane)["state"], "EMPTY")

            with self.subTest(lane=lane, partial_short_page_is_authority=True):
                backend, intent, prepared = pending_lane(lane, 3391)
                self.assertTrue(prepared["cas"]["appended"])
                item = outbox.read_next(backend, lane)
                receipt = persist_cursor(
                    backend,
                    item,
                    attempt=1,
                    successor_count=0,
                    declared_total_count=1,
                )
                self.assertEqual(
                    receipt["state"],
                    "SCAN_INVENTORY_INCONSISTENT_AUTHORITY",
                )
                self.assertEqual(
                    receipt["record"]["cursor"]["inventory_blocker"],
                    "SHORT_PAGE_BEFORE_DECLARED_TOTAL",
                )
                item = outbox.read_next(backend, lane)
                observation = materialize_retry_cursor_authority_observation(
                    item=item,
                    transport_attempt=1,
                    observed_main_head_sha=item["intent"]["payload"][
                        "main_head_sha"
                    ],
                )
                self.assertEqual(
                    observation["blocker"],
                    "RECOVERY_QUERY_INVENTORY_INCONSISTENT",
                )
                record = persist_authority_observation(
                    backend, intent, observation, run_id=98391
                )
                terminal = materialize_authority_terminal(
                    item=outbox.read_next(backend, lane),
                    authority_record=record,
                )
                outbox.terminalize(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    evidence=terminal,
                )
                self.assertEqual(outbox.read_next(backend, lane)["state"], "EMPTY")

            with self.subTest(lane=lane, declared_inventory_paginates=True):
                backend, intent, prepared = pending_lane(lane, 3392)
                self.assertTrue(prepared["cas"]["appended"])
                item = outbox.read_next(backend, lane)
                first = persist_cursor(
                    backend,
                    item,
                    attempt=1,
                    successor_count=0,
                    unrelated_count=100,
                    unrelated_start=5000,
                    declared_total_count=101,
                )
                self.assertEqual(first["state"], "SCAN_INCOMPLETE_REOBSERVE")
                self.assertFalse(first["record"]["cursor"]["scan_complete"])
                self.assertEqual(
                    first["record"]["cursor"]["observed_unique_run_count"],
                    100,
                )
                item = outbox.read_next(backend, lane)
                second = persist_cursor(
                    backend,
                    item,
                    attempt=1,
                    successor_count=0,
                    unrelated_count=1,
                    unrelated_start=4999,
                    declared_total_count=101,
                    observation_started_at="2026-09-01T08:03:00Z",
                    observation_completed_at="2026-09-01T08:03:01Z",
                )
                self.assertEqual(second["state"], "COMPLETE_ZERO_SUCCESSOR")
                self.assertTrue(second["record"]["cursor"]["scan_complete"])
                self.assertEqual(
                    second["record"]["cursor"]["observed_unique_run_count"],
                    101,
                )

            with self.subTest(lane=lane, page_overlap_is_authority=True):
                backend, intent, prepared = pending_lane(lane, 3393)
                self.assertTrue(prepared["cas"]["appended"])
                item = outbox.read_next(backend, lane)
                persist_cursor(
                    backend,
                    item,
                    attempt=1,
                    successor_count=0,
                    unrelated_count=100,
                    unrelated_start=5000,
                    declared_total_count=101,
                )
                item = outbox.read_next(backend, lane)
                overlap = persist_cursor(
                    backend,
                    item,
                    attempt=1,
                    successor_count=0,
                    unrelated_count=1,
                    unrelated_start=5000,
                    declared_total_count=101,
                    observation_started_at="2026-09-01T08:03:00Z",
                    observation_completed_at="2026-09-01T08:03:01Z",
                )
                self.assertEqual(
                    overlap["state"],
                    "SCAN_INVENTORY_INCONSISTENT_AUTHORITY",
                )
                self.assertEqual(
                    overlap["record"]["cursor"]["inventory_blocker"],
                    "PAGE_RUN_ID_OVERLAP",
                )

            for drift_flag, expected_blocker in (
                ("duplicate_first_page_id", "PAGE_RUN_ID_DUPLICATE"),
                ("page_order_drift", "PAGE_RUN_ID_PAGE_ORDER_DRIFT"),
            ):
                with self.subTest(lane=lane, raw_page_drift=expected_blocker):
                    backend, intent, prepared = pending_lane(lane, 3394)
                    self.assertTrue(prepared["cas"]["appended"])
                    item = outbox.read_next(backend, lane)
                    drifted = persist_cursor(
                        backend,
                        item,
                        attempt=1,
                        successor_count=0,
                        unrelated_count=(1 if drift_flag == "duplicate_first_page_id" else 2),
                        declared_total_count=2,
                        **{drift_flag: True},
                    )
                    self.assertEqual(
                        drifted["state"],
                        "SCAN_INVENTORY_INCONSISTENT_AUTHORITY",
                    )
                    self.assertEqual(
                        drifted["record"]["cursor"]["inventory_blocker"],
                        expected_blocker,
                    )

            with self.subTest(lane=lane, successor_count=0, one_shot=True):
                backend, intent, prepared = pending_lane(lane, 340)
                self.assertTrue(prepared["cas"]["appended"])
                item = outbox.read_next(backend, lane)
                persist_cursor(backend, item, attempt=1, successor_count=0)
                item = outbox.read_next(backend, lane)
                observation = materialize_retry_cursor_authority_observation(
                    item=item,
                    transport_attempt=1,
                    observed_main_head_sha=item["intent"]["payload"][
                        "main_head_sha"
                    ],
                )
                self.assertEqual(
                    observation["blocker"],
                    (
                        "REPEATED_EXACT_HEAD_TRANSPORT_UNACKNOWLEDGED"
                        if lane == "exact-head-dispatch"
                        else "REPEATED_EXACT_REVIEW_TRANSPORT_UNACKNOWLEDGED"
                    ),
                )
                record = persist_authority_observation(
                    backend, intent, observation, run_id=9902
                )
                item = outbox.read_next(backend, lane)
                terminal = materialize_authority_terminal(
                    item=item, authority_record=record
                )
                outbox.terminalize(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    evidence=terminal,
                )
                self.assertEqual(outbox.read_next(backend, lane)["state"], "EMPTY")
                with self.assertRaises(outbox.OutboxBlock):
                    outbox.prepare_transport(
                        backend,
                        lane=lane,
                        sequence=intent["sequence"],
                        attempt=2,
                        request={},
                        retry_evidence=None,
                        actor_run_id=902,
                        actor_run_attempt=1,
                    )

            with self.subTest(lane=lane, successor_count=1, lost_acceptance=True):
                backend, intent, prepared = pending_lane(lane, 360)
                self.assertTrue(prepared["cas"]["appended"])
                replay = outbox.prepare_transport(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    request=outbox.request_for_transport_attempt(intent, 1),
                    retry_evidence=None,
                    actor_run_id=901,
                    actor_run_attempt=1,
                )
                self.assertFalse(replay["cas"]["appended"])
                item = outbox.read_next(backend, lane)
                delayed = persist_cursor(
                    backend, item, attempt=1, successor_count=1
                )
                self.assertEqual(
                    delayed["record"]["cursor"]["query_window_end"],
                    "2026-09-01T08:02:00Z",
                )
                self.assertEqual(
                    delayed["record"]["cursor"]["bound_successor_count"], 1
                )
                item = outbox.read_next(backend, lane)
                child = item["retry_scan_cursor"]["1"]["cursor"][
                    "candidate_locators"
                ][0]
                outbox.record_acceptance(
                    backend,
                    lane=lane,
                    sequence=intent["sequence"],
                    attempt=1,
                    child=child,
                )
                current = outbox.read_next(backend, lane)
                self.assertEqual(set(current["transport"]), {"1"})
                self.assertEqual(set(current["acceptance"]), {"1"})
                with self.assertRaises(outbox.OutboxBlock):
                    outbox.prepare_transport(
                        backend,
                        lane=lane,
                        sequence=intent["sequence"],
                        attempt=2,
                        request={},
                        retry_evidence=None,
                        actor_run_id=902,
                        actor_run_attempt=1,
                    )

    def test_transport_locator_drift_is_rejected(self):
        item = outbox.read_next(self.backend, "exact-review-dispatch")
        name, archive = self.success_archive()
        with self.assertRaises(ExactReviewOutboxError):
            materialize_completion(
                item=item,
                child=self.completed_child("success"),
                jobs=[],
                artifact_api=self.artifact_api(name, archive),
                artifact_zip=archive,
                transport_attempt=2,
                child_recovery=False,
            )
        tampered = bytearray(archive)
        # The API digest still matches the bytes, so rejection must come from
        # semantic producer/transport validation, not archive hashing alone.
        files = {"envelope.json": b"{}"}
        bad_archive = self.archive(files)
        with self.assertRaises(ExactReviewOutboxError):
            materialize_completion(
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
                artifact_api=self.artifact_api(name, bad_archive),
                artifact_zip=bad_archive,
                transport_attempt=1,
                child_recovery=False,
            )


if __name__ == "__main__":
    unittest.main()
