# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_review_mesh_work as mesh
from tools import qikvrt_requested_review_executor as review
from tests import test_qikvrt_requested_review_executor as fixtures

DEFAULT_DIFF_BYTES = fixtures.DEFAULT_DIFF_BYTES


class MeshWorkTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.bundle, self.result = self.root / "bundle", self.root / "result"
        snapshot = fixtures.RequestedReviewExecutorTests().snapshot(
            repository="Goldkelch/qik-vrt", head_repository="Goldkelch/qik-vrt",
            trusted_evaluator_blob_sha="e" * 40, trusted_read_transport_blob_sha="e" * 40)
        mesh.write(self.source / "snapshot.json", snapshot)
        (self.source / "review.diff").write_bytes(DEFAULT_DIFF_BYTES)
        mesh.write(self.source / "review.json", review.evaluate(snapshot, DEFAULT_DIFF_BYTES))
        self.git_patch = mock.patch.object(mesh, "git", side_effect=lambda *args: "a" * 40 if args[-1] == "HEAD" else "e" * 40)
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)
        self.key = mesh.pack(self.source, self.bundle)

    def run_worker(self):
        return mesh.worker(self.bundle, self.key, "ingolf-lohmann/qik-vrt", self.result)

    def test_full_work_survives_independent_directory_and_byte_exact_consolidation(self):
        value = self.run_worker()
        self.assertFalse(value["native_approval"])
        self.assertFalse(value["merge"])
        result = mesh.consolidate(self.bundle, self.result)
        self.assertEqual(result["state"], "EXACT_BYTES_CONSOLIDATED")
        self.assertTrue(result["fresh_authority_reobservation_required"])
        self.assertEqual((self.result / "review.json").read_bytes(),
                         (self.source / "review.json").read_bytes())
        self.assertEqual(result, mesh.consolidate(self.bundle, self.result))

    def test_mirror_identity_cannot_be_replaced_by_source_identity(self):
        with self.assertRaisesRegex(ValueError, "WORKER_ROLE_MISMATCH"):
            mesh.worker(self.bundle, self.key, "Goldkelch/qik-vrt", self.result)

    def test_predecessor_work_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "WORK_DIGEST_MISMATCH"):
            mesh.worker(self.bundle, "0" * 64, "ingolf-lohmann/qik-vrt", self.result)

    def test_snapshot_change_cannot_be_hidden_by_same_work_manifest(self):
        snapshot = json.loads((self.bundle / "snapshot.json").read_bytes())
        snapshot["head_sha"] = "0" * 40
        mesh.write(self.bundle / "snapshot.json", snapshot)
        with self.assertRaisesRegex(ValueError, "WORK_INPUT_DIGEST_MISMATCH"):
            self.run_worker()

    def test_corrupted_and_missing_packets_are_rejected(self):
        path = self.bundle / "packet-000000.bin"
        path.write_bytes(path.read_bytes() + b"corrupt")
        with self.assertRaises(review.ReviewSnapshotError):
            self.run_worker()
        path.unlink()
        with self.assertRaisesRegex(ValueError, "WORK_PACKET_SET_MISMATCH"):
            self.run_worker()

    def test_surplus_packet_cannot_be_silently_discarded(self):
        (self.bundle / "packet-999999.bin").write_bytes(b"unaccounted")
        with self.assertRaisesRegex(ValueError, "WORK_PACKET_SET_MISMATCH"):
            self.run_worker()

    def test_worker_with_different_code_cannot_attest_source_result(self):
        with mock.patch.object(mesh, "git", return_value="a" * 40):
            with self.assertRaisesRegex(ValueError, "WORKER_CODE_IDENTITY_MISMATCH"):
                self.run_worker()

    def test_contradiction_is_retained_as_error_not_consolidated(self):
        self.run_worker()
        path = self.result / "review.json"
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "WORKER_RESULT_BYTES_MISMATCH"):
            mesh.consolidate(self.bundle, self.result)
        self.assertEqual(path.read_bytes(), original + b" ")

    def test_consolidation_rejects_claimed_native_approval(self):
        self.run_worker()
        path = self.result / "worker.json"
        value = json.loads(path.read_bytes())
        value["native_approval"] = True
        mesh.write(path, value)
        with self.assertRaisesRegex(ValueError, "WORKER_RESULT_BINDING_MISMATCH"):
            mesh.consolidate(self.bundle, self.result)

    def test_missing_mesh_credential_keeps_executable_local_result_and_is_explicit(self):
        with mock.patch.dict("os.environ", {"QIKVRT_MESH_TOKEN": ""}):
            result = mesh.execute(self.bundle, self.root / "execution")
        self.assertEqual(result["state"], "LOCAL_RETAINED_MESH_CREDENTIAL_MISSING")
        self.assertFalse(result["remote_execution_verified"])
        self.assertFalse(result["dispatch_performed"])
        self.assertTrue((self.bundle / "source-review.json").is_file())

    def test_transport_implementation_identity_changes_review_fingerprint(self):
        before = json.loads((self.source / "snapshot.json").read_bytes())
        first = review.evaluate(before, DEFAULT_DIFF_BYTES)
        before["trusted_read_transport_blob_sha"] = "a" * 40
        second = review.evaluate(before, DEFAULT_DIFF_BYTES)
        self.assertNotEqual(first["evidence_fingerprint"], second["evidence_fingerprint"])


if __name__ == "__main__":
    unittest.main()
