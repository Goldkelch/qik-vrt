import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "qikvrt_m68000_emitter_ansic.c"

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

    def test_nop_and_rts_exact_words(self):
        r = self.run_ir("NOP\nRTS\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, bytes.fromhex("4e714e75"))

    def test_moveq_d0_zero(self):
        r = self.run_ir("MOVEQ D0 0\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, bytes.fromhex("7000"))

    def test_moveq_register_and_signed_immediate(self):
        r = self.run_ir("MOVEQ D3 -1\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, bytes.fromhex("76ff"))

    def test_out_of_range_immediate_fails_closed(self):
        r = self.run_ir("MOVEQ D0 128\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"HOLD", r.stderr)

    def test_unknown_instruction_fails_closed(self):
        r = self.run_ir("MAGIC D0 1\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"HOLD", r.stderr)

if __name__ == "__main__":
    unittest.main()
