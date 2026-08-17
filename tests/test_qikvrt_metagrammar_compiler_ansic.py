import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "qikvrt_metagrammar_compiler_ansic.c"


class MetagrammarCompilerAnsiCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / "qikvrt-metagrammar-compiler"
        subprocess.run([
            "cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
            str(SOURCE), "-o", str(cls.binary)
        ], check=True, cwd=ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_message(self, message):
        return subprocess.run([str(self.binary)], input=message + "\n", text=True,
                              capture_output=True, cwd=ROOT)

    def base(self, kind="OBSERVE", intent="OBSERVE terminal", auth="BOUND:po-1",
             state="OBSERVED", effect="NONE:none", next_action="REOBSERVE"):
        return (
            f"{kind}|r1|Goldkelch/qik-vrt@" + "a" * 40 + ":" + "b" * 40
            + f"|{intent}|AUTH={auth}|EVID=HEAD:" + "c" * 64
            + f"|STATE={state}|EFFECT={effect}|NEXT={next_action}|PROOF=" + "d" * 64
        )

    def test_compiles_valid_message_to_deterministic_plan(self):
        result = self.run_message(self.base())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("QIKVRT_METAGRAMMAR_PLAN_V1", result.stdout)
        self.assertIn("NEXT_ACTION=REOBSERVE", result.stdout)
        self.assertIn("ADMISSION=VALIDATED", result.stdout)

    def test_lexer_rejects_wrong_field_count(self):
        result = self.run_message("OBSERVE|too|few")
        self.assertEqual(result.returncode, 2)
        self.assertIn("LEXER_ERWARTET_10_FELDER", result.stderr)

    def test_productive_action_requires_bound_authority(self):
        result = self.run_message(self.base(kind="ACT", intent="EXECUTE repair",
                                            auth="MISSING:none", effect="REQUESTED:e1",
                                            next_action="HOLD"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("PRODUKTIVE_WIRKUNG_OHNE_AUTORITAET", result.stderr)

    def test_unbound_authority_allows_only_nonproductive_continuation(self):
        result = self.run_message(self.base(auth="MISSING:none", next_action="EXECUTE"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("UNBEFUGTE_FORTSETZUNG", result.stderr)

    def test_unknown_cannot_drive_productive_effect(self):
        result = self.run_message(self.base(kind="ACT", intent="EXECUTE repair",
                                            state="UNKNOWN", effect="REQUESTED:e1",
                                            next_action="EXECUTE"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("UNKNOWN_DARF_NICHT_WIRKEN", result.stderr)

    def test_acknowledged_effect_requires_ack_message(self):
        result = self.run_message(self.base(kind="ACT", intent="EXECUTE effect",
                                            effect="ACKNOWLEDGED:e1", next_action="REOBSERVE"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("ACK_ERFORDERT_ACK_NACHRICHT", result.stderr)


if __name__ == "__main__":
    unittest.main()
