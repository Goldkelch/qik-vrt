import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "qikvrt_m68000_emitter_ansic.c"

CAPSULES = {
    0: bytes.fromhex("70004e75"),
    1: bytes.fromhex("70014e75"),
    2: bytes.fromhex("70024e75"),
    3: bytes.fromhex("70034e75"),
}


class M68000EmitterAnsiCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / "qikvrt-m68000-emitter"
        subprocess.run([
            "cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
            str(SOURCE), "-o", str(cls.binary)
        ], check=True, cwd=ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_ir(self, text):
        return subprocess.run([str(self.binary)], input=text.encode("ascii"), capture_output=True, cwd=ROOT)

    def test_exact_four_capsules(self):
        for code, expected in CAPSULES.items():
            with self.subTest(code=code):
                r = self.run_ir("MOVEQ D0 %d\nRTS\n" % code)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout, expected)

    def test_comments_and_blank_lines_do_not_change_capsule(self):
        r = self.run_ir("# bound capsule\n\nMOVEQ D0 2\n\nRTS\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, CAPSULES[2])

    def test_generic_nop_is_outside_closed_kernel(self):
        r = self.run_ir("NOP\nRTS\n")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, b"")
        self.assertIn(b"HOLD", r.stderr)

    def test_other_register_is_outside_closed_kernel(self):
        r = self.run_ir("MOVEQ D3 1\nRTS\n")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, b"")
        self.assertIn(b"HOLD", r.stderr)

    def test_code_outside_zero_to_three_fails_closed(self):
        for code in [-1, 4, 127]:
            with self.subTest(code=code):
                r = self.run_ir("MOVEQ D0 %d\nRTS\n" % code)
                self.assertEqual(r.returncode, 2)
                self.assertEqual(r.stdout, b"")
                self.assertIn(b"HOLD", r.stderr)

    def test_missing_rts_emits_no_partial_binary(self):
        r = self.run_ir("MOVEQ D0 1\n")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, b"")
        self.assertIn(b"HOLD", r.stderr)

    def test_extra_instruction_emits_no_partial_binary(self):
        r = self.run_ir("MOVEQ D0 1\nRTS\nRTS\n")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, b"")
        self.assertIn(b"HOLD", r.stderr)

    def test_unknown_instruction_fails_closed(self):
        r = self.run_ir("MAGIC D0 1\nRTS\n")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, b"")
        self.assertIn(b"HOLD", r.stderr)


if __name__ == "__main__":
    unittest.main()
