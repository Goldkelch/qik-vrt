import importlib.util
import json
import pathlib
import tempfile
import unittest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "tools" / "qikvrt_io_roundtrip.py"
spec = importlib.util.spec_from_file_location("qikvrt_io_roundtrip", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class IoRoundTripTests(unittest.TestCase):
    def test_trace_only_without_claim(self):
        self.assertEqual(mod.classify({}), "TRACE_ONLY")

    def test_claim_requires_proof_before_publication(self):
        meta = {"claim_bearing": True, "publication_targets": ["zenodo"]}
        state = mod.classify(meta)
        self.assertEqual(state, "KNOWLEDGE_CANDIDATE")
        decision = mod.publication_decision(meta, state)
        self.assertEqual(decision["global_blocker"], "machine-checkable proof/evidence receipt not bound")

    def test_ietf_has_additional_applicability_gate(self):
        meta = {
            "claim_bearing": True,
            "proof_receipt_sha256": "a" * 64,
            "publication_targets": ["ietf"],
            "exact_artifact_binding": True,
            "proof_or_evidence_receipt": True,
            "provenance_complete": True,
            "rights_clear": True,
            "scientific_status_explicit": True,
            "granularity_suitable": True,
            "connectivity_suitable": True,
            "target_authorized": True,
            "credentials_available": True,
        }
        decision = mod.publication_decision(meta, mod.classify(meta))
        self.assertEqual(decision["targets"]["ietf"]["status"], "BLOCK")
        self.assertIn("protocol_or_specification_applicable=false", decision["targets"]["ietf"]["blockers"])

    def test_ready_target_requires_every_gate(self):
        meta = {
            "claim_bearing": True,
            "proof_receipt_sha256": "b" * 64,
            "publication_targets": ["zenodo"],
            "exact_artifact_binding": True,
            "proof_or_evidence_receipt": True,
            "provenance_complete": True,
            "rights_clear": True,
            "scientific_status_explicit": True,
            "granularity_suitable": True,
            "connectivity_suitable": True,
            "target_authorized": True,
            "credentials_available": True,
        }
        decision = mod.publication_decision(meta, mod.classify(meta))
        self.assertEqual(decision["targets"]["zenodo"]["status"], "READY")
        self.assertEqual(decision["ready_targets"], ["zenodo"])

    def test_check_detects_malformed_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            old_root, old_events = mod.ROOT, mod.EVENTS_DIR
            try:
                mod.ROOT = root
                mod.EVENTS_DIR = root / "state" / "io_roundtrip" / "events"
                mod.EVENTS_DIR.mkdir(parents=True)
                (mod.EVENTS_DIR / "bad.json").write_text(json.dumps({"knowledge_state": "PUBLISHED"}), encoding="utf-8")
                class Args: pass
                self.assertEqual(mod.check(Args()), 1)
            finally:
                mod.ROOT, mod.EVENTS_DIR = old_root, old_events


if __name__ == "__main__":
    unittest.main()
