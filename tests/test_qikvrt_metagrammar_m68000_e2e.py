import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "tools" / "qikvrt_metagrammar_compiler_ansic.c"
LOWER = ROOT / "tools" / "qikvrt_metagrammar_m68000_lower_ansic.c"
EMIT = ROOT / "tools" / "qikvrt_m68000_emitter_ansic.c"

class MetagrammarM68000E2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.front = Path(cls.tmp.name) / "front"
        cls.lower = Path(cls.tmp.name) / "lower"
        cls.emit = Path(cls.tmp.name) / "emit"
        for source, target in [(FRONT, cls.front), (LOWER, cls.lower), (EMIT, cls.emit)]:
            subprocess.run([
                "cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
                str(source), "-o", str(target)
            ], check=True, cwd=ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def compile_message(self, next_action):
        msg = (
            "OBSERVE|r1|Goldkelch/qik-vrt@" + "a" * 40 + ":" + "b" * 40
            + "|OBSERVE terminal|AUTH=BOUND:po-1|EVID=HEAD:" + "c" * 64
            + "|STATE=OBSERVED|EFFECT=NONE:none|NEXT=" + next_action
            + "|PROOF=" + "d" * 64 + "\n"
        )
        front = subprocess.run([str(self.front)], input=msg.encode("ascii"), capture_output=True, cwd=ROOT)
        self.assertEqual(front.returncode, 0, front.stderr)
        lower = subprocess.run([str(self.lower)], input=front.stdout, capture_output=True, cwd=ROOT)
        self.assertEqual(lower.returncode, 0, lower.stderr)
        emit = subprocess.run([str(self.emit)], input=lower.stdout, capture_output=True, cwd=ROOT)
        self.assertEqual(emit.returncode, 0, emit.stderr)
        return emit.stdout

    def test_noop_capsule(self):
        self.assertEqual(self.compile_message("NOOP"), bytes.fromhex("70004e75"))

    def test_hold_capsule(self):
        self.assertEqual(self.compile_message("HOLD"), bytes.fromhex("70014e75"))

    def test_reobserve_capsule(self):
        self.assertEqual(self.compile_message("REOBSERVE"), bytes.fromhex("70024e75"))

    def test_request_authority_capsule(self):
        self.assertEqual(self.compile_message("REQUEST_AUTHORITY"), bytes.fromhex("70034e75"))

    def test_unsupported_action_stops_before_binary_emission(self):
        plan = b"QIKVRT_METAGRAMMAR_PLAN_V1\nNEXT_ACTION=EXECUTE\nADMISSION=VALIDATED\n"
        lower = subprocess.run([str(self.lower)], input=plan, capture_output=True, cwd=ROOT)
        self.assertEqual(lower.returncode, 2)
        self.assertEqual(lower.stdout, b"")
        self.assertIn(b"HOLD", lower.stderr)

if __name__ == "__main__":
    unittest.main()
