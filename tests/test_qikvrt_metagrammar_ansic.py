import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "qikvrt_metagrammar_ansic.c"


class MetagrammarAnsiCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / "qikvrt-metagrammar-ansic"
        subprocess.run(
            [
                "cc",
                "-std=c89",
                "-pedantic-errors",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(SOURCE),
                "-o",
                str(cls.binary),
            ],
            check=True,
            cwd=ROOT,
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_message(self, message):
        return subprocess.run(
            [str(self.binary)],
            input=message + "\n",
            text=True,
            capture_output=True,
            cwd=ROOT,
        )

    def test_valid_observation_compiles_to_ast(self):
        msg = (
            "OBSERVE|r1|Goldkelch/qik-vrt@" + "a" * 40 + ":" + "b" * 40
            + "|OBSERVE terminal|AUTH=BOUND:po-1|EVID=HEAD:" + "c" * 64
            + "|STATE=OBSERVED|EFFECT=NONE:none|PROOF=" + "d" * 64
        )
        result = self.run_message(msg)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("QMG_AST_V1", result.stdout)
        self.assertIn("VALID", result.stdout)

    def test_productive_action_without_bound_authority_is_hold(self):
        msg = (
            "ACT|r2|Goldkelch/qik-vrt@" + "a" * 40 + ":" + "b" * 40
            + "|EXECUTE repair|AUTH=MISSING:none|EVID=TEST:" + "c" * 64
            + "|STATE=READY|EFFECT=REQUESTED:e1|PROOF=" + "d" * 64
        )
        result = self.run_message(msg)
        self.assertEqual(result.returncode, 2)
        self.assertIn("HOLD", result.stderr)

    def test_bad_head_is_hold(self):
        msg = (
            "OBSERVE|r3|Goldkelch/qik-vrt@short:" + "b" * 40
            + "|OBSERVE terminal|AUTH=BOUND:po-1|EVID=HEAD:" + "c" * 64
            + "|STATE=OBSERVED|EFFECT=NONE:none|PROOF=" + "d" * 64
        )
        result = self.run_message(msg)
        self.assertEqual(result.returncode, 2)

    def test_acknowledged_effect_requires_ack_message_kind(self):
        msg = (
            "ACT|r4|Goldkelch/qik-vrt@" + "a" * 40 + ":" + "b" * 40
            + "|EXECUTE effect|AUTH=BOUND:po-1|EVID=RECEIPT:" + "c" * 64
            + "|STATE=OBSERVED|EFFECT=ACKNOWLEDGED:e1|PROOF=" + "d" * 64
        )
        result = self.run_message(msg)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ACK", result.stderr)


if __name__ == "__main__":
    unittest.main()
