# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Portable admission checks for a worker with a different local review core."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_review_mesh_work as mesh


class PortableWorkerTest(unittest.TestCase):
    def test_source_main_and_run_are_verified_before_code_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = {"schema": "qikvrt_review_mesh_work_v1",
                    "source_repository": "Goldkelch/qik-vrt", "worker_repository": "ingolf-lohmann/qik-vrt",
                    "source_main_sha": "a" * 40, "source_run_id": "123", "source_run_attempt": "2"}
            raw = json.dumps(work).encode()
            (root / "work.json").write_bytes(raw)
            client = mock.Mock()
            main = {"sha": "a" * 40}
            run = {"path": ".github/workflows/qikvrt_requested_review_executor.yml",
                   "head_branch": "main", "run_attempt": 2, "event": "pull_request_target"}
            with mock.patch.object(mesh, "ObservationClient", return_value=client), \
                    mock.patch.object(mesh, "git", return_value="b" * 40), \
                    mock.patch.dict("os.environ", {"SOURCE_RUN_ID": "123", "GH_TOKEN": "fixture"}):
                client.get.side_effect = [(main, {}), (run, {})]
                result = mesh.verify_source(root, mesh.digest(raw), "ingolf-lohmann/qik-vrt")
                self.assertEqual(result["sha"], "a" * 40)
                self.assertEqual(result["worker_head"], "b" * 40)
                client.get.side_effect = [({"sha": "c" * 40}, {})]
                with self.assertRaisesRegex(ValueError, "SOURCE_TRUSTED_MAIN_DRIFT"):
                    mesh.verify_source(root, mesh.digest(raw), "ingolf-lohmann/qik-vrt")
                client.get.side_effect = [(main, {}), ({**run, "path": ".github/workflows/untrusted.yml"}, {})]
                with self.assertRaisesRegex(ValueError, "SOURCE_TRUSTED_RUN_MISMATCH"):
                    mesh.verify_source(root, mesh.digest(raw), "ingolf-lohmann/qik-vrt")
                with self.assertRaisesRegex(ValueError, "WORK_DIGEST_MISMATCH"):
                    mesh.verify_source(root, "0" * 64, "ingolf-lohmann/qik-vrt")


if __name__ == "__main__":
    unittest.main()
