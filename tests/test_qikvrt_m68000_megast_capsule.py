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

    def test_tos_program_checks_action_before_sentinel(self):
        text = tos_text(ACTIONS["REQUEST_AUTHORITY"])
        self.assertEqual(len(text), 69)
        self.assertEqual(
            text[:56],
            bytes.fromhex(
                "61320c400003662241fa002e3f3c00002f083f3c003c4e41"
                "3f003f3c003e4e413f3c00003f3c004c4e413f3c00013f3c004c4e41"
                "70034e75"
            ),
        )
        self.assertTrue(text.endswith(SENTINEL_PATH))
        # BSR target, BNE fail target and LEA filename target are all exact.
        self.assertEqual(2 + int.from_bytes(text[1:2], "big", signed=True), 52)
        self.assertEqual(8 + int.from_bytes(text[7:8], "big", signed=True), 42)
        self.assertEqual(10 + int.from_bytes(text[10:12], "big", signed=True), 56)

        prg = tos_prg(3)
        magic, text_len, data_len, bss_len, sym_len, reserved, flags, absflag = struct.unpack(">HLLLLLLH", prg[:28])
        self.assertEqual(magic, 0x601A)
        self.assertEqual(text_len, len(text))
        self.assertEqual((data_len, bss_len, sym_len, reserved, flags, absflag), (0, 0, 0, 0, 0, 1))
        self.assertEqual(prg[28:], text)
        self.assertLess(len(prg), 1024)

    def test_all_actions_embed_their_expected_compare_and_moveq(self):
        for name, action in ACTIONS.items():
            with self.subTest(name=name):
                text = tos_text(action)
                self.assertEqual(text[2:6], struct.pack(">HH", 0x0C40, action))
                self.assertEqual(text[52:56], decision_code(action))

    def test_only_four_effect_actions_exist(self):
        self.assertEqual(ACTIONS, {"NOOP": 0, "HOLD": 1, "REOBSERVE": 2, "REQUEST_AUTHORITY": 3})
        with self.assertRaises(ValueError):
            decision_code(4)
        with self.assertRaises(ValueError):
            tos_text(4)


if __name__ == "__main__":
    unittest.main()
