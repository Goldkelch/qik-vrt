from __future__ import annotations

import json
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import qikvrt_evidence_cost as cost  # noqa: E402


class EvidenceCostTests(unittest.TestCase):
    def test_landauer_per_bit_at_300_kelvin(self) -> None:
        value = cost.landauer_minimum_joules(1, "300", "1")
        self.assertGreater(value, Decimal("2.87097888507872e-21"))
        self.assertLess(value, Decimal("2.87097888507873e-21"))

    def test_exact_audio_carrier_lower_bound(self) -> None:
        bits = cost.carrier_bits(7_142_895)
        self.assertEqual(bits, 57_143_160)
        energy = cost.landauer_minimum_joules(bits, "300", "1")
        self.assertGreater(energy, Decimal("1.6405680578667e-13"))
        self.assertLess(energy, Decimal("1.6405680578668e-13"))

    def test_repository_size_scenario(self) -> None:
        byte_count = 186_801 * 1024
        self.assertEqual(byte_count, 191_284_224)
        bits = cost.carrier_bits(byte_count)
        self.assertEqual(bits, 1_530_273_792)
        energy = cost.landauer_minimum_joules(bits, "300", "1")
        self.assertGreater(energy, Decimal("4.3933837452213e-12"))
        self.assertLess(energy, Decimal("4.3933837452214e-12"))

    def test_ideal_width_scaling_is_32_to_1(self) -> None:
        byte_count = 191_284_224
        t8 = cost.ideal_transfer_seconds(byte_count, 8, "8000000", "1")
        t256 = cost.ideal_transfer_seconds(byte_count, 256, "8000000", "1")
        self.assertEqual(t8 / t256, Decimal(32))
        self.assertEqual(t8, Decimal("23.910528"))
        self.assertEqual(t256, Decimal("0.747204"))

    def test_storage_scenario(self) -> None:
        value = cost.storage_list_price_usd(
            191_284_224, "0.023", "12", replicas=3
        )
        self.assertGreater(value, Decimal("0.14750597"))
        self.assertLess(value, Decimal("0.14750598"))

    def test_replacement_cost_is_separate(self) -> None:
        self.assertEqual(
            cost.replacement_cost("5000", "100", "25000"), Decimal("525000")
        )

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(cost.InputError):
            cost.landauer_minimum_joules(1, "0")
        with self.assertRaises(cost.InputError):
            cost.ideal_transfer_seconds(1, 8, 1, "1.01")
        with self.assertRaises(cost.InputError):
            cost.carrier_bits(-1)

    def test_cli_receipt_preserves_claim_boundaries(self) -> None:
        command = [
            sys.executable,
            str(ROOT / "tools" / "qikvrt_evidence_cost.py"),
            "--bytes",
            "7142895",
            "--source-label",
            "four-owner-audio-files-2026-08-22",
            "--clock-hz",
            "8000000",
            "--bandwidth-gb-s",
            "3.7",
            "--bandwidth-gb-s",
            "8",
            "--runner-seconds",
            "45",
        ]
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        receipt = json.loads(completed.stdout)
        self.assertFalse(receipt["carrier"]["semantic_information_measured"])
        self.assertFalse(
            receipt["thermodynamic_lower_bound"]["actual_energy_measured"]
        )
        self.assertFalse(receipt["boundaries"]["market_value_determined"])
        self.assertEqual(len(receipt["transport_envelopes"]), 6)
        self.assertEqual(len(receipt["bandwidth_envelopes"]), 2)


if __name__ == "__main__":
    unittest.main()
