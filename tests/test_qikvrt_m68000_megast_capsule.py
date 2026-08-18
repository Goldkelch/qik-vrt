import struct
import unittest

from tools.qikvrt_m68000_megast_capsule import ACTIONS, MAGIC, SENTINEL_PATH, capsule, decision_code, tos_prg, tos_text


class MegaSTCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.meta = {
            "source_binding": "Goldkelch/qik-vrt@HEAD:TREE",
            "causal_graph": "sha256:causal",
            "authority": "owner:bound",
            "evidence": "sha256:evidence",
            "role_identity": "AUTHORITY:QIKVRT_AI",
        }

    def test_hardwired_decision_bytes(self):
        self.assertEqual(decision_code(0), bytes.fromhex("70004e75"))
        self.assertEqual(decision_code(1), bytes.fromhex("70014e75"))
        self.assertEqual(decision_code(2), bytes.fromhex("70024e75"))
        self.assertEqual(decision_code(3), bytes.fromhex("70034e75"))

    def test_qik_capsule_is_small_and_metadata_bound(self):
        blob = capsule("REOBSERVE", self.meta)
        self.assertTrue(blob.startswith(MAGIC))
        self.assertEqual(blob[-4:], bytes.fromhex("70024e75"))
        self.assertLess(len(blob), 512)
        changed = dict(self.meta)
        changed["evidence"] = "sha256:other"
        self.assertNotEqual(blob, capsule("REOBSERVE", changed))

    def test_tos_program_creates_post_capsule_sentinel(self):
        text = tos_text(ACTIONS["REQUEST_AUTHORITY"])
        self.assertEqual(len(text), 53)
        self.assertTrue(text.startswith(bytes.fromhex(
            "612241fa00223f3c00002f083f3c003c4e413f003f3c003e4e413f3c00003f3c004c4e4170034e75"
        )))
        self.assertTrue(text.endswith(SENTINEL_PATH))
        prg = tos_prg(3)
        magic, text_len, data_len, bss_len, sym_len, reserved, flags, absflag = struct.unpack(">HLLLLLLH", prg[:28])
        self.assertEqual(magic, 0x601A)
        self.assertEqual(text_len, len(text))
        self.assertEqual((data_len, bss_len, sym_len, reserved, flags, absflag), (0, 0, 0, 0, 0, 1))
        self.assertEqual(prg[28:], text)
        self.assertLess(len(prg), 1024)

    def test_only_four_effect_actions_exist(self):
        self.assertEqual(ACTIONS, {"NOOP": 0, "HOLD": 1, "REOBSERVE": 2, "REQUEST_AUTHORITY": 3})
        with self.assertRaises(ValueError):
            decision_code(4)


if __name__ == "__main__":
    unittest.main()
