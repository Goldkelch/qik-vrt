from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "qikvrt_siemens_reference_integration.py"
spec = importlib.util.spec_from_file_location("qikvrt_siemens_reference_integration", MODULE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class SiemensReferenceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = m.TwinState(
            entity="unit-1", version=7, position_m=10.0,
            velocity_mps=2.0, temperature_c=20.0,
        )

    def test_closed_roundtrip_earns_simulated_effect_ack(self) -> None:
        result = m.run_roundtrip(self.state, 5.0)
        self.assertEqual(result["receipt"]["phase"], "EFFECT_ACK")
        self.assertTrue(result["receipt"]["effect_ack"])
        self.assertFalse(result["receipt"]["physical_effect_ack"])
        self.assertEqual(result["receipt"]["subject"]["version"], 8)
        self.assertEqual(result["effect"]["adapter"], "SIMULATED_DIGITAL_TWIN_ONLY")

    def test_prepare_never_claims_effect(self) -> None:
        prepared = m.prepare(self.state, target_velocity_mps=3.0)
        self.assertFalse(prepared["protected_effect_executed"])

    def test_stale_subject_fails_closed(self) -> None:
        prepared = m.prepare(self.state, target_velocity_mps=3.0)
        stale = m.TwinState(
            entity=self.state.entity, version=8, position_m=10.0,
            velocity_mps=2.0, temperature_c=20.0,
        )
        with self.assertRaises(ValueError):
            m.simulate(stale, prepared)

    def test_out_of_domain_command_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            m.prepare(self.state, target_velocity_mps=121.0)

    def test_receipt_is_deterministic(self) -> None:
        a = m.run_roundtrip(self.state, 4.0)
        b = m.run_roundtrip(self.state, 4.0)
        self.assertEqual(a["receipt"]["receipt_sha256"], b["receipt"]["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
