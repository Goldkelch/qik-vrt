from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import struct
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_m68000_tos_consumer.py"
PERSISTED_HEX = ROOT / "runtime" / "m68000" / "tos" / "MLP.TOS.hex"
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_m68000_tos_consumer.yml"

spec = importlib.util.spec_from_file_location("qikvrt_m68000_tos_consumer", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class M68000TosConsumerTests(unittest.TestCase):
    def test_deterministic_image_matches_persisted_hex(self):
        image, report = mod.build_tos(ROOT)
        self.assertEqual(
            image.hex(), PERSISTED_HEX.read_text(encoding="ascii").strip()
        )
        self.assertEqual(report["tos_sha256"], hashlib.sha256(image).hexdigest())
        self.assertEqual(report["schema"], "QIKVRT_M68000_TOS_CONSUMER_BUILD_V2")
        self.assertEqual(report["kernel_bytes"], [24, 20, 24, 82, 134])
        self.assertEqual(report["receipt_size"], 320)

    def test_atari_tos_header_is_absolute_position_independent_program(self):
        image, report = mod.build_tos(ROOT)
        self.assertEqual(struct.unpack_from(">H", image, 0)[0], 0x601A)
        self.assertEqual(
            struct.unpack_from(">I", image, 2)[0], report["text_bytes"]
        )
        self.assertEqual(struct.unpack_from(">I", image, 6)[0], 0)
        self.assertEqual(struct.unpack_from(">I", image, 10)[0], 0)
        self.assertEqual(struct.unpack_from(">H", image, 26)[0], 1)
        self.assertEqual(len(image), 28 + report["text_bytes"])

    def test_all_five_registry_kernels_are_embedded_byte_identically(self):
        image, _ = mod.build_tos(ROOT)
        _, kernels = mod.load_registry(ROOT)
        self.assertEqual(len(kernels), 5)
        for kernel in kernels:
            self.assertIn(kernel, image)

    def test_protected_hz_200_read_is_bound_to_xbios_supexec(self):
        text, report = mod.build_text(ROOT)
        self.assertEqual(report["timer_access"], "XBIOS_SUPEXEC_HZ_200")
        self.assertIn(bytes.fromhex("3f3c00264e4e"), text)
        self.assertEqual(text.count(bytes.fromhex("203804ba4e75")), 1)
        self.assertNotIn(bytes.fromhex("2c3804ba"), text)
        self.assertNotIn(bytes.fromhex("223804ba"), text)

    def _valid_receipt(self) -> bytes:
        registry_raw = (ROOT / mod.REGISTRY_PATH).read_bytes()
        _, kernels = mod.load_registry(ROOT)
        receipt = bytearray(mod.receipt_template(registry_raw, kernels))
        receipt[mod.GATE_OFFSET:mod.GATE_OFFSET + 4] = bytes([0, 1, 2, 2])
        receipt[mod.D3_OFFSET:mod.D3_OFFSET + 3] = bytes([3, 1, 0xA5])
        receipt[mod.MESH_OFFSET:mod.MESH_OFFSET + 8] = bytes(
            [0, 0, 0, 0, 1, 1, 1, 2]
        )
        pass_flat = []
        for _flags, expected in mod.SPARK_PASS_CASES:
            pass_flat.extend(expected)
        receipt[
            mod.SPARK_PASS_OFFSET:mod.SPARK_PASS_OFFSET + len(pass_flat)
        ] = bytes(pass_flat)
        receipt[mod.SPARK_PLAN_OFFSET:mod.SPARK_PLAN_OFFSET + 5] = bytes(
            expected for _flags, expected in mod.SPARK_PLAN_CASES
        )
        for index, ticks in enumerate((40, 25, 35, 45, 50)):
            start = mod.TICKS_OFFSET + index * 4
            receipt[start:start + 4] = struct.pack(">I", ticks)
        receipt[mod.COMPLETE_OFFSET:mod.COMPLETE_OFFSET + 4] = struct.pack(">I", 1)
        return bytes(receipt)

    def test_synthetic_reobservation_contract_covers_both_spark_kernels(self):
        report = mod.parse_receipt(self._valid_receipt(), ROOT)
        self.assertEqual(report["schema"], "QIKVRT_M68000_TOS_REOBSERVATION_V2")
        self.assertTrue(report["execution_observed"])
        self.assertTrue(report["m68000_emulator_execution_observed"])
        self.assertTrue(report["spark_m68000_emulator_execution_observed"])
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertEqual(report["gate_outputs"], [0, 1, 2, 2])
        self.assertEqual(
            [item["decision_code"] for item in report["spark_branch_pass_outputs"]],
            [0, 2, 3, 1],
        )
        self.assertEqual(report["spark_branch_plan_outputs"], [1, 0, 11, 10, 2])
        self.assertEqual(set(report["ticks_200hz"]), {
            "gate", "d3_step", "mesh_recovery",
            "spark_branch_pass", "spark_branch_plan",
        })

    def test_tampered_provenance_and_semantics_fail_closed(self):
        receipt = bytearray(self._valid_receipt())
        receipt[mod.REGISTRY_HASH_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "provenance"):
            mod.parse_receipt(bytes(receipt), ROOT)
        receipt = bytearray(self._valid_receipt())
        receipt[mod.SPARK_PLAN_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "Spark plan"):
            mod.parse_receipt(bytes(receipt), ROOT)

    def test_main_effect_reobservation_is_push_bound_and_persisted(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("push:\n    branches: [main]", text)
        self.assertIn(
            "github.event_name == 'push' && github.ref == 'refs/heads/main'",
            text,
        )
        self.assertIn("QIKVRT_M68000_TOS_MAIN_EFFECT_RECEIPT_V2", text)
        self.assertIn("qikvrt/m68000-tos-systemtest-ledger-v1", text)
        self.assertIn("HOLD_M68000_TOS_LEDGER_SINGLE_CAS_FAILED", text)
        self.assertIn("physical_m68000_execution_observed': False", text)
        self.assertIn("physical_speedup_measured': False", text)

    def test_network_and_ledger_paths_are_one_attempt_and_fail_closed(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("--retry", text)
        self.assertNotIn("retry-all-errors", text)
        self.assertNotIn("for attempt in", text)
        self.assertNotIn("sleep ", text)
        self.assertIn("--max-time 180", text)
        self.assertIn("HOLD_EMUTOS_SINGLE_FETCH_FAILED", text)
        self.assertIn("BLOCK_EMUTOS_ARCHIVE_SHA256_MISMATCH", text)
        self.assertIn("QIKVRT_M68000_TOS_EMUTOS_ACQUISITION_RECEIPT_V1", text)
        self.assertIn("HOLD_M68000_TOS_LEDGER_SINGLE_CAS_FAILED", text)
        self.assertIn("HOLD_LEDGER_POST_WRITE_REF_DRIFT", text)
        self.assertIn("BLOCK_LEDGER_POST_WRITE_RECEIPT_MISMATCH", text)
        self.assertIn("QIKVRT_M68000_TOS_LEDGER_WRITE_RECEIPT_V3", text)
        self.assertIn("emutos-acquisition-receipt.json", text)
        self.assertIn("m68000-tos-ledger-write-receipt.json", text)


if __name__ == "__main__":
    unittest.main()
