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

spec = importlib.util.spec_from_file_location("qikvrt_m68000_tos_consumer", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class M68000TosConsumerTests(unittest.TestCase):
    def test_deterministic_image_matches_persisted_hex(self):
        image, report = mod.build_tos(ROOT)
        self.assertEqual(image.hex(), PERSISTED_HEX.read_text(encoding="ascii").strip())
        self.assertEqual(report["tos_sha256"], hashlib.sha256(image).hexdigest())
        self.assertEqual(report["kernel_bytes"], [24, 20, 24])

    def test_atari_tos_header_is_absolute_position_independent_program(self):
        image, report = mod.build_tos(ROOT)
        self.assertEqual(struct.unpack_from(">H", image, 0)[0], 0x601A)
        self.assertEqual(struct.unpack_from(">I", image, 2)[0], report["text_bytes"])
        self.assertEqual(struct.unpack_from(">I", image, 6)[0], 0)
        self.assertEqual(struct.unpack_from(">I", image, 10)[0], 0)
        self.assertEqual(struct.unpack_from(">H", image, 26)[0], 1)
        self.assertEqual(len(image), 28 + report["text_bytes"])

    def test_registry_kernels_are_embedded_byte_identically(self):
        image, _ = mod.build_tos(ROOT)
        _, kernels = mod.load_registry(ROOT)
        for kernel in kernels:
            self.assertIn(kernel, image)

    def test_protected_hz_200_read_is_bound_to_xbios_supexec(self):
        text, report = mod.build_text(ROOT)
        self.assertEqual(report["timer_access"], "XBIOS_SUPEXEC_HZ_200")
        self.assertIn(bytes.fromhex("3f3c00264e4e"), text)
        self.assertEqual(text.count(bytes.fromhex("203804ba4e75")), 1)
        self.assertNotIn(bytes.fromhex("2c3804ba"), text)
        self.assertNotIn(bytes.fromhex("223804ba"), text)

    def test_synthetic_reobservation_contract(self):
        registry_raw = (ROOT / mod.REGISTRY_PATH).read_bytes()
        _, kernels = mod.load_registry(ROOT)
        receipt = bytearray(mod.receipt_template(registry_raw, kernels))
        receipt[144:148] = bytes([0, 1, 2, 2])
        receipt[148:151] = bytes([3, 1, 0xA5])
        receipt[152:160] = bytes([0, 0, 0, 0, 1, 1, 1, 2])
        for offset, ticks in zip((160, 164, 168), (40, 25, 35)):
            receipt[offset:offset + 4] = struct.pack(">I", ticks)
        receipt[172:176] = struct.pack(">I", 1)
        report = mod.parse_receipt(bytes(receipt), ROOT)
        self.assertTrue(report["execution_observed"])
        self.assertTrue(report["m68000_emulator_execution_observed"])
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertEqual(report["gate_outputs"], [0, 1, 2, 2])

    def test_tampered_provenance_fails_closed(self):
        registry_raw = (ROOT / mod.REGISTRY_PATH).read_bytes()
        _, kernels = mod.load_registry(ROOT)
        receipt = bytearray(mod.receipt_template(registry_raw, kernels))
        receipt[12] ^= 1
        with self.assertRaisesRegex(ValueError, "provenance"):
            mod.parse_receipt(bytes(receipt), ROOT)


if __name__ == "__main__":
    unittest.main()
