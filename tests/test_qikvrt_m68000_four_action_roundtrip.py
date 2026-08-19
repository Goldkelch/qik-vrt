import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUNDTRIP_PATH = ROOT / "tools" / "qikvrt_m68000_four_action_roundtrip.py"
FRONT = ROOT / "tools" / "qikvrt_universal_understanding_ansic.c"
LOWER = ROOT / "tools" / "qikvrt_metagrammar_m68000_lower_ansic.c"
EMIT = ROOT / "tools" / "qikvrt_m68000_emitter_ansic.c"

spec = importlib.util.spec_from_file_location("qikvrt_m68000_four_action_roundtrip", ROUNDTRIP_PATH)
assert spec is not None and spec.loader is not None
roundtrip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roundtrip)


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

    def source(self, action):
        return (
            "QIKU1\n"
            "KIND OBSERVE\n"
            "RID roundtrip-1\n"
            f"SUBJECT repo Goldkelch/qik-vrt {'a' * 40} {'b' * 40}\n"
            "INTENT OBSERVE terminal\n"
            "AUTH BOUND po-temdd\n"
            f"EVID HEAD {'c' * 64}\n"
            "STATE OBSERVED\n"
            "EFFECT NONE none\n"
            f"NEXT {action}\n"
            f"PROOF {'d' * 64}\n"
            "CAUSE -\n"
            "END\n"
        )

    def compile_action(self, action):
        front = subprocess.run(
            [str(self.front), "--target-megast"],
            input=self.source(action),
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
