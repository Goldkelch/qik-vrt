# SPDX-License-Identifier: Apache-2.0
import json
import pathlib
import tempfile
import unittest

from tools import qikvrt_zenodo_successor_guard as guard


class ZenodoSuccessorGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "policy").mkdir()
        (self.root / "release/x").mkdir(parents=True)
        (self.root / "docs").mkdir()
        (self.root / "a.txt").write_text("A\n", encoding="utf-8")
        (self.root / "docs/b.txt").write_text("B\n", encoding="utf-8")
        self.target = {
            "id": "x",
            "publication_id": "pub-x",
            "authority_repository": "o/r",
            "source_paths": ["a.txt", "docs/b.txt"],
            "candidate_path": "release/x/AUTO_SUCCESSOR_CANDIDATE.json",
            "publish_request_path": "release/x/publish-request.json",
            "owner_authorization_path": "release/x/OWNER.json",
            "publication_receipt_path": "release/x/zenodo-publication.json",
            "enforce_public_effect_on_main": True,
        }
        self._write_registry()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_registry(self):
        (self.root / "policy/QIKVRT_ZENODO_SUCCESSOR_TARGETS_V1.json").write_text(
            json.dumps({"schema": "qikvrt_zenodo_successor_targets_v1", "targets": [self.target]}),
            encoding="utf-8",
        )

    def _source_files(self):
        current = guard.source_set(self.root, guard.target(self.root, "x"))
        return [{"path": item["path"], "git_blob_sha": item["git_blob_sha1"]} for item in current]

    def test_materialize_all_detects_successor_drift(self):
        guard.materialize_all(self.root)
        self.assertTrue(guard.evaluate(self.root, "x")["candidate"]["current"])
        (self.root / "a.txt").write_text("A2\n", encoding="utf-8")
        self.assertEqual(guard.evaluate(self.root, "x")["candidate"]["state"], "STALE")

    def test_stale_predecessor_controls_do_not_close_effect(self):
        guard.materialize(self.root, "x")
        files = self._source_files()
        (self.root / "release/x/publish-request.json").write_text(
            json.dumps({
                "schema": "qikvrt_zenodo_publication_manifest_v2",
                "state": "publish",
                "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
                "repository": "o/r",
                "files": files,
            }),
            encoding="utf-8",
        )
        (self.root / "release/x/OWNER.json").write_text(
            json.dumps({
                "schema": "qikvrt_zenodo_owner_authorization_v1",
                "repository": "o/r",
                "publication_id": "pub-x",
                "single_use": True,
                "uploads": files,
                "authorization_event": {"decision": "AUTHORIZE_EXACT_UPLOAD"},
            }),
            encoding="utf-8",
        )
        (self.root / "release/x/zenodo-publication.json").write_text(
            json.dumps({
                "schema": "qikvrt_zenodo_publication_evidence_v2",
                "state": "published",
                "phase": "public_verified",
                "recovery": {"public_verified": True, "remote_state_requires_reconciliation": False},
                "doi": "10.5281/zenodo.123",
                "conceptdoi": "10.5281/zenodo.122",
                "record_id": 123,
                "record_url": "https://zenodo.org/records/123",
                "files": files,
            }),
            encoding="utf-8",
        )
        self.assertTrue(guard.evaluate(self.root, "x")["PUBLICATION_EFFECT_ACK_DONE"])
        (self.root / "docs/b.txt").write_text("changed\n", encoding="utf-8")
        state = guard.evaluate(self.root, "x")
        self.assertFalse(state["PUBLICATION_EFFECT_ACK_DONE"])
        self.assertEqual(state["candidate"]["state"], "STALE")
        self.assertEqual(state["publish_request"]["state"], "STALE")
        self.assertEqual(state["owner_authorization"]["state"], "STALE")
        self.assertEqual(state["public_receipt"]["state"], "STALE")

    def test_legacy_receipt_is_not_public_effect(self):
        guard.materialize(self.root, "x")
        files = self._source_files()
        (self.root / "release/x/zenodo-publication.json").write_text(
            json.dumps({
                "schema": "qikvrt_zenodo_publication_evidence_v1",
                "state": "published",
                "doi": "10.5281/zenodo.123",
                "files": files,
            }),
            encoding="utf-8",
        )
        self.assertFalse(guard.evaluate(self.root, "x")["public_receipt"]["current"])

    def test_path_escape_is_rejected(self):
        self.target["source_paths"] = ["../escape"]
        self._write_registry()
        with self.assertRaises(guard.GuardError):
            guard.target(self.root, "x")


class ZenodoSuccessorWorkflowContractTest(unittest.TestCase):
    ROOT = pathlib.Path(__file__).resolve().parents[1]

    def _read(self, relative):
        return (self.ROOT / relative).read_text(encoding="utf-8")

    def test_projection_successor_is_immediately_reverified(self):
        workflow = self._read(".github/workflows/qikvrt_pr_integrity_projection.yml")
        self.assertIn("reason:\"PROJECTION_SUCCESSOR\"", workflow)
        self.assertIn("qikvrt_autonomous_exact_head_verify", workflow)
        self.assertLess(
            workflow.index('git push origin "HEAD:refs/heads/$TARGET_REF"'),
            workflow.index('reason:"PROJECTION_SUCCESSOR"'),
        )

    def test_zero_job_fallback_watches_publication_closure(self):
        workflow = self._read(".github/workflows/qikvrt_zero_job_self_dispatch.yml")
        self.assertIn('"QIKVRT PR integrity projection"', workflow)
        self.assertIn('"QIKVRT Zenodo successor closure guard"', workflow)

    def test_global_reobserve_watches_publication_closure(self):
        workflow = self._read(".github/workflows/qikvrt_autonomous_pr_head_continuation.yml")
        self.assertIn('"QIKVRT PR integrity projection"', workflow)
        self.assertIn('"QIKVRT Zenodo successor closure guard"', workflow)

    def test_publication_receipt_successor_is_reverified(self):
        workflow = self._read(".github/workflows/qikvrt_zenodo_successor_publish.yml")
        self.assertIn("reason:\"PUBLICATION_RECEIPT_SUCCESSOR\"", workflow)
        self.assertIn("qikvrt_autonomous_exact_head_verify", workflow)

    unittest.main()
