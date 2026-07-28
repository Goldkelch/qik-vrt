# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_transactional_workflow_trigger.py"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TransactionalWorkflowTriggerTests(unittest.TestCase):
    def make_case(self):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        (root / "payload").mkdir()
        (root / "payload" / "a.txt").write_text("alpha\n", encoding="utf-8")
        manifest = {
            "schema": "qikvrt_transactional_workflow_trigger_v1",
            "transaction_id": "TEST-TRANSACTION",
            "base_commit": "0" * 40,
            "allowed_changed_paths": ["payload/a.txt", "ready.json", "transaction.json"],
            "required_changed_paths": ["payload/a.txt", "ready.json", "transaction.json"],
            "required_files": [
                {"path": "payload/a.txt", "sha256": sha256(root / "payload" / "a.txt")}
            ],
            "ready_marker": "ready.json",
            "completion_claims": {"pass": False, "final_pass": False, "effect_ack_done": False},
        }
        (root / "transaction.json").write_text(json.dumps(manifest), encoding="utf-8")
        return td, root

    def ready(self, root: pathlib.Path, txid: str = "TEST-TRANSACTION"):
        (root / "ready.json").write_text(
            json.dumps({"state": "READY", "transaction_id": txid}) + "\n",
            encoding="utf-8",
        )

    def run_tool(self, root: pathlib.Path, changed):
        changed_file = root / "changed.txt"
        changed_file.write_text("\n".join(changed) + "\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(TOOL), "verify", "--root", str(root), "--manifest", "transaction.json", "--changed-paths", str(changed_file)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_missing_ready_marker_blocks(self):
        td, root = self.make_case()
        with td:
            p = self.run_tool(root, ["payload/a.txt", "transaction.json"])
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("READY_MARKER_MISSING", p.stdout)

    def test_mismatched_ready_marker_blocks(self):
        td, root = self.make_case()
        with td:
            self.ready(root, "OTHER-TRANSACTION")
            p = self.run_tool(root, ["payload/a.txt", "ready.json", "transaction.json"])
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("READY_MARKER_INVALID", p.stdout)

    def test_hash_mismatch_blocks(self):
        td, root = self.make_case()
        with td:
            self.ready(root)
            (root / "payload" / "a.txt").write_text("tampered\n", encoding="utf-8")
            p = self.run_tool(root, ["payload/a.txt", "ready.json", "transaction.json"])
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("REQUIRED_FILE_HASH_MISMATCH", p.stdout)

    def test_missing_required_file_blocks(self):
        td, root = self.make_case()
        with td:
            self.ready(root)
            (root / "payload" / "a.txt").unlink()
            p = self.run_tool(root, ["payload/a.txt", "ready.json", "transaction.json"])
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("REQUIRED_FILE_MISSING", p.stdout)

    def test_missing_required_changed_path_blocks(self):
        td, root = self.make_case()
        with td:
            self.ready(root)
            p = self.run_tool(root, ["ready.json", "transaction.json"])
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("REQUIRED_CHANGED_PATH_MISSING", p.stdout)

    def test_unexpected_changed_path_blocks(self):
        td, root = self.make_case()
        with td:
            self.ready(root)
            p = self.run_tool(root, ["payload/a.txt", "ready.json", "transaction.json", "extra.txt"])
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("UNEXPECTED_CHANGED_PATH", p.stdout)

    def test_false_completion_claim_blocks(self):
        td, root = self.make_case()
        with td:
            self.ready(root)
            manifest = json.loads((root / "transaction.json").read_text(encoding="utf-8"))
            manifest["completion_claims"]["pass"] = True
            (root / "transaction.json").write_text(json.dumps(manifest), encoding="utf-8")
            p = self.run_tool(root, ["payload/a.txt", "ready.json", "transaction.json"])
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("FALSE_COMPLETION_CLAIM_IN_TRIGGER_MANIFEST", p.stdout)

    def test_complete_transaction_verifies(self):
        td, root = self.make_case()
        with td:
            self.ready(root)
            p = self.run_tool(root, ["payload/a.txt", "ready.json", "transaction.json"])
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            receipt = json.loads(p.stdout)
            self.assertEqual(receipt["state"], "TRANSACTION_TRIGGER_VERIFIED")
            self.assertFalse(receipt["completion_claims"]["pass"])


if __name__ == "__main__":
    unittest.main()
