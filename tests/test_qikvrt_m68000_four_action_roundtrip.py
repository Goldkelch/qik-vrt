import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import qikvrt_m68000_four_action_roundtrip as roundtrip

FRONT = ROOT / "tools" / "qikvrt_universal_understanding_ansic.c"
LOWER = ROOT / "tools" / "qikvrt_metagrammar_m68000_lower_ansic.c"
EMIT = ROOT / "tools" / "qikvrt_m68000_emitter_ansic.c"


class M68000FourActionRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.front = Path(cls.tmp.name) / "front"
        cls.lower = Path(cls.tmp.name) / "lower"
        cls.emit = Path(cls.tmp.name) / "emit"
        for source, target in ((FRONT, cls.front), (LOWER, cls.lower), (EMIT, cls.emit)):
            subprocess.run(
                ["cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(target)],
                check=True,
                cwd=ROOT,
            )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def source(self, action, rid="roundtrip-1", cause="-"):
        return (
            "QIKU1\n"
            "KIND OBSERVE\n"
            f"RID {rid}\n"
            f"SUBJECT repo Goldkelch/qik-vrt {'a' * 40} {'b' * 40}\n"
            "INTENT OBSERVE terminal\n"
            "AUTH BOUND po-temdd\n"
            f"EVID HEAD {'c' * 64}\n"
            "STATE OBSERVED\n"
            "EFFECT NONE none\n"
            f"NEXT {action}\n"
            f"PROOF {'d' * 64}\n"
            f"CAUSE {cause}\n"
            "END\n"
        )

    def compile_source(self, source):
        front = subprocess.run(
            [str(self.front), "--target-megast"],
            input=source,
            text=True,
            capture_output=True,
            cwd=ROOT,
        )
        self.assertEqual(front.returncode, 0, front.stderr)
        lower = subprocess.run(
            [str(self.lower)], input=front.stdout.encode("ascii"), capture_output=True, cwd=ROOT
        )
        self.assertEqual(lower.returncode, 0, lower.stderr)
        emit = subprocess.run([str(self.emit)], input=lower.stdout, capture_output=True, cwd=ROOT)
        self.assertEqual(emit.returncode, 0, emit.stderr)
        return emit.stdout

    def compile_action(self, action):
        return self.compile_source(self.source(action))

    def test_exact_four_action_bijection(self):
        rows = roundtrip.verify_bijection()
        self.assertEqual([row.action for row in rows], list(roundtrip.ACTIONS))
        self.assertEqual(
            [row.machine_hex for row in rows],
            ["70004e75", "70014e75", "70024e75", "70034e75"],
        )

    def test_full_forward_pipeline_and_reverse_decoder_are_identity(self):
        for action in roundtrip.ACTIONS:
            with self.subTest(action=action):
                machine = self.compile_action(action)
                self.assertEqual(machine, roundtrip.encode(action))
                self.assertEqual(roundtrip.decode(machine), action)
                self.assertEqual(roundtrip.encode(roundtrip.decode(machine)), machine)

    def test_source_to_machine_lowering_is_intentionally_many_to_one(self):
        left = self.source("HOLD", rid="source-a", cause="cause-a")
        right = self.source("HOLD", rid="source-b", cause="cause-b")
        self.assertNotEqual(left, right)
        left_machine = self.compile_source(left)
        right_machine = self.compile_source(right)
        self.assertEqual(left_machine, right_machine)
        self.assertEqual(roundtrip.decode(left_machine), "HOLD")
        self.assertEqual(roundtrip.decode(right_machine), "HOLD")

    def test_reverse_path_rejects_every_nearby_noncanonical_code(self):
        rejected = (
            bytes.fromhex("4e71"),
            bytes.fromhex("70044e75"),
            bytes.fromhex("70004e71"),
            bytes.fromhex("7000"),
            bytes.fromhex("70004e7500"),
        )
        for code in rejected:
            with self.subTest(code=code.hex()):
                with self.assertRaises(ValueError):
                    roundtrip.decode(code)

    def test_all_four_codes_are_real_moveq_then_rts_encodings(self):
        for index, action in enumerate(roundtrip.ACTIONS):
            code = roundtrip.encode(action)
            self.assertEqual(code[:2], bytes.fromhex(f"{0x7000 | index:04x}"))
            self.assertEqual(code[2:], bytes.fromhex("4e75"))
            self.assertEqual(roundtrip.describe(action).instruction, f"MOVEQ #{index},D0 ; RTS")


if __name__ == "__main__":
    unittest.main()
