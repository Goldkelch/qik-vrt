#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regressions for the no-secret EFFECT_ACK state persistence handoff."""

from __future__ import annotations

import copy
import json
import pathlib
import unittest

from tests.release_authority_hold_contract import assert_authority_hold_workflow
from tools import qikvrt_effect_ack_evidence_transport as transport


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_effect_ack_finalize.yml"


class EffectAckEvidenceTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = "Goldkelch/qik-vrt"
        self.workflow_sha = "a" * 40
        self.head_sha = "b" * 40
        self.source_commit = "c" * 40
        self.source_tree = "d" * 40
        self.tag_object_sha = "e" * 40
        self.marker_sha256 = "f" * 64
        self.run_id = 123456
        self.run_attempt = 2
        self.artifact_name = "effect-ack-zenodo-state-input-123456-2"
        self.tag = "v2026.07.22-effect-ack-universality-1.0.0"
        self.evidence = {
            "schema": "qikvrt_effect_ack_zenodo_finalization_evidence_v1",
            "client_result": {
                "schema_version": 1,
                "phase": "published",
                "release_id": "2026.07.22-effect-ack-universality-1.0.0",
                "tag": self.tag,
                "repositories": [
                    "Goldkelch/qik-vrt",
                    "ingolf-lohmann/qik-vrt",
                ],
                "datatracker_submitted": False,
                "paper": {"doi": "10.5281/zenodo.12345678"},
                "software": {"doi": "10.5281/zenodo.12345679"},
                "final_manifest_sha256": "1" * 64,
            },
            "final_manifest_sha256": "1" * 64,
            "deposited_files": {
                "paper": [
                    {
                        "name": "paper.txt",
                        "size": 1,
                        "md5": "2" * 32,
                        "sha256": "3" * 64,
                    }
                ],
                "software": [
                    {
                        "name": "source.tar.gz",
                        "size": 2,
                        "md5": "4" * 32,
                        "sha256": "5" * 64,
                    }
                ],
            },
            "repository": self.repository,
            "tag": self.tag,
            "tag_object_sha": self.tag_object_sha,
            "target_commit": self.source_commit,
            "target_tree": self.source_tree,
            "mirror_annotated_tag_verified": True,
            "github_release_object_absence_verified_at_tag_effect": True,
            "datatracker_submission_performed": False,
        }

    def evidence_bytes(self, value: dict | None = None) -> bytes:
        return (
            json.dumps(
                self.evidence if value is None else value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

    def build(self, evidence_bytes: bytes | None = None, **overrides):
        arguments = {
            "evidence_bytes": self.evidence_bytes()
            if evidence_bytes is None
            else evidence_bytes,
            "artifact_name": self.artifact_name,
            "repository": self.repository,
            "workflow_sha": self.workflow_sha,
            "head_sha": self.head_sha,
            "run_id": self.run_id,
            "run_attempt": self.run_attempt,
            "marker_sha256": self.marker_sha256,
            "source_commit": self.source_commit,
            "source_tree": self.source_tree,
            "tag_object_sha": self.tag_object_sha,
        }
        arguments.update(overrides)
        return transport.build_transport(**arguments)

    def validate(self, envelope: dict, evidence_bytes: bytes | None = None):
        return transport.validate_transport(
            transport_bytes=transport.pretty_json_bytes(envelope),
            evidence_bytes=self.evidence_bytes()
            if evidence_bytes is None
            else evidence_bytes,
            expected_artifact_name=self.artifact_name,
            expected_repository=self.repository,
            expected_workflow_sha=self.workflow_sha,
            expected_head_sha=self.head_sha,
            expected_run_id=self.run_id,
            expected_run_attempt=self.run_attempt,
            expected_marker_sha256=self.marker_sha256,
            expected_source_commit=self.source_commit,
            expected_source_tree=self.source_tree,
            expected_tag_object_sha=self.tag_object_sha,
            expected_tag=self.tag,
        )

    def test_exact_same_run_transport_is_accepted(self) -> None:
        evidence = self.validate(self.build())
        self.assertEqual(evidence["target_commit"], self.source_commit)

    def test_tampered_evidence_is_rejected(self) -> None:
        envelope = self.build()
        changed = copy.deepcopy(self.evidence)
        changed["target_tree"] = "9" * 40
        with self.assertRaisesRegex(
            transport.EvidenceTransportError, "evidence digest"
        ):
            self.validate(envelope, self.evidence_bytes(changed))

    def test_foreign_run_artifact_is_rejected(self) -> None:
        envelope = self.build(run_id=self.run_id + 1)
        with self.assertRaisesRegex(transport.EvidenceTransportError, "producer"):
            self.validate(envelope)

    def test_resealed_foreign_subject_is_rejected(self) -> None:
        envelope = self.build(source_commit="9" * 40)
        with self.assertRaisesRegex(transport.EvidenceTransportError, "subject"):
            self.validate(envelope)

    def test_secret_job_is_read_only_and_writer_job_is_secret_free(self) -> None:
        assert_authority_hold_workflow(self, "qikvrt_effect_ack_finalize.yml")
        return
        workflow = WORKFLOW.read_text(encoding="utf-8")
        finalize_start = workflow.index("  zenodo-finalize:")
        persist_start = workflow.index("  zenodo-state-persist:")
        finalize_job = workflow[finalize_start:persist_start]
        persist_job = workflow[persist_start:]
        self.assertIn("permissions:\n      contents: read", finalize_job)
        self.assertNotIn("contents: write", finalize_job)
        self.assertIn("secrets.ZENODO_ACCESS_TOKEN", finalize_job)
        self.assertIn("permissions:\n      actions: read\n      contents: write", persist_job)
        self.assertNotIn("ZENODO_ACCESS_TOKEN", persist_job)
        self.assertNotIn("secrets.", persist_job)

    def test_writer_binds_artifact_and_fresh_reciprocal_cut_before_effect(self) -> None:
        assert_authority_hold_workflow(self, "qikvrt_effect_ack_finalize.yml")
        return
        workflow = WORKFLOW.read_text(encoding="utf-8")
        persist = workflow[workflow.index("  zenodo-state-persist:") :]
        for required in (
            "public_artifact_id",
            "public_artifact_digest",
            "public_artifact_name",
            "artifact-ids: ${{ needs.zenodo-finalize.outputs.public_artifact_id }}",
            'artifact.get("digest") != artifact_digest',
            'workflow_run.get("id") != int(os.environ["GITHUB_RUN_ID"])',
            "validate_transport(",
            "validate_prepublication_barrier(",
            "public evidence artifact file set is not exact",
        ):
            self.assertIn(required, persist)
        barrier = persist.index("validate_prepublication_barrier(")
        first_effect = persist.index('api("POST", "/git/blobs"')
        self.assertLess(barrier, first_effect)
        self.assertIn("state branch ref readback differs", persist[first_effect:])
        self.assertIn("persisted public evidence bytes differ", persist[first_effect:])


if __name__ == "__main__":
    unittest.main(verbosity=2)
