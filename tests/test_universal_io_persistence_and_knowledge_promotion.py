import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "UNIVERSAL_IO_PERSISTENCE_AND_KNOWLEDGE_PROMOTION_V1.json"
TOOL = ROOT / "tools" / "qikvrt_io_work_unit.py"


class UniversalIOPersistenceContractTest(unittest.TestCase):
    def test_policy_is_machine_readable_and_modality_neutral(self):
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "qikvrt_universal_io_persistence_and_knowledge_promotion_v1")
        capture = " ".join(data["acceptance_criteria"]["capture"])
        for modality in ("text", "audio", "image", "video", "binary attachment", "tool result"):
            self.assertIn(modality, capture)

    def test_policy_locks_epistemic_and_effect_boundaries(self):
        data = json.loads(POLICY.read_text(encoding="utf-8"))
        invariants = set(data["fail_closed_invariants"])
        self.assertIn("CHAT_MEMORY_IS_NOT_REPOSITORY_PERSISTENCE", invariants)
        self.assertIn("FORMAL_PROOF_IS_NOT_EMPIRICAL_CONFIRMATION", invariants)
        self.assertIn("PUBLICATION_ROUTING_IS_NOT_PUBLICATION_EFFECT", invariants)

    def test_exact_bytes_produce_deterministic_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            source = td / "input.bin"
            source.write_bytes(b"qik-vrt-io")
            out = td / "receipt.json"
            cmd = [
                sys.executable, str(TOOL),
                "--work-unit-id", "WU-1",
                "--timestamp", "2026-08-07T15:31:00+02:00",
                "--direction", "INPUT",
                "--modality", "binary",
                "--file", str(source),
                "--source-or-generator", "human-interface",
                "--human-attribution", "Ingolf Lohmann",
                "--output", str(out),
            ]
            first = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(receipt["sha256"], hashlib.sha256(b"qik-vrt-io").hexdigest())
            second = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
            self.assertEqual(second.stdout.strip(), "NOOP")
            self.assertTrue(first.stdout.strip())

    def test_digest_only_requires_exact_identity(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "receipt.json"
            proc = subprocess.run([
                sys.executable, str(TOOL),
                "--work-unit-id", "WU-2",
                "--timestamp", "2026-08-07T15:31:00+02:00",
                "--direction", "INPUT",
                "--modality", "audio",
                "--source-or-generator", "human-interface",
                "--output", str(out),
            ], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("sha256 and byte_length", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
