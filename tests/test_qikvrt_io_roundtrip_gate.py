# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qikvrt_io_roundtrip_gate", ROOT / "tools/qikvrt_io_roundtrip_gate.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class IORoundTripGateTests(unittest.TestCase):
    def test_repository_work_units_validate(self) -> None:
        result = mod.run(list((ROOT / "state/io_work_units").glob("*.json")))
        self.assertEqual("PASS", result["status"])
        self.assertGreaterEqual(result["work_units_checked"], 1)
        self.assertFalse(result["publication_effect_performed"])

    def test_normative_claim_cannot_claim_formal_proof(self) -> None:
        record = {
            "schema": "qikvrt_io_work_unit_v1",
            "work_unit_id": "negative-proof-inflation-test",
            "observed_at": "2026-08-07T15:44:00+02:00",
            "direction": "INPUT",
            "kind": "text",
            "provenance": {"origin": "test"},
            "payload_binding": {"sha256": "0" * 64},
            "epistemic_class": "NORMATIVE_CLAIM",
            "persistence": {"repository": "Goldkelch/qik-vrt", "path": "PLACEHOLDER"},
            "derivation": {"machine_proof_status": "PROVED"},
            "publication": {"connectable": True, "ietf_relevant": True},
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", dir=ROOT, delete=False, encoding="utf-8") as handle:
            path = Path(handle.name)
            record["persistence"]["path"] = path.relative_to(ROOT).as_posix()
            json.dump(record, handle)
        try:
            with self.assertRaisesRegex(ValueError, "non-formal epistemic class"):
                mod.validate_unit(path)
        finally:
            path.unlink(missing_ok=True)

    def test_connectable_ietf_relevant_record_routes_candidates_without_external_effect(self) -> None:
        path = ROOT / "state/io_work_units/2026-08-07T1544+0200-product-owner-universal-io-roundtrip.json"
        result = mod.validate_unit(path)
        self.assertEqual("BUILD_CANDIDATE", result["zenodo_route"])
        self.assertEqual("BUILD_CANDIDATE", result["ietf_route"])
        self.assertEqual("SEPARATE_AUTHORIZATION_REQUIRED", result["external_effect"])


if __name__ == "__main__":
    unittest.main()
