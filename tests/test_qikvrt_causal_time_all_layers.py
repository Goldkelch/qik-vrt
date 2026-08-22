import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOWER = ROOT / "tools" / "qikvrt_metagrammar_m68000_lower_ansic.c"
EMIT = ROOT / "tools" / "qikvrt_m68000_emitter_ansic.c"


def plan(cause="-", next_action="REOBSERVE", effect="OBSERVED", authority="BOUND"):
    return "\n".join([
        "QIKVRT_UNIVERSAL_PLAN_V1",
        "DISTINCTION_KERNEL=1-0=1;1-1=0;x=y;z=0;x=1;y=1",
        "TYPE_INVARIANTS=DISTINCTION!=RELATION;RELATION!=CAUSALITY;CAUSALITY!=SEQUENCE;ZERO_RESULT!=NO_EFFECT",
        f"AUTHORITY=AUTH={authority}:po-1",
        f"EFFECT={effect}:e1",
        f"CAUSE={cause}",
        f"NEXT_ACTION={next_action}",
        "ADMISSION=VALIDATED",
        "",
    ])


class CausalTimeAllLayersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lower_bin = Path(cls.tmp.name) / "lower"
        cls.emit_bin = Path(cls.tmp.name) / "emit"
        for src, out in [(LOWER, cls.lower_bin), (EMIT, cls.emit_bin)]:
            subprocess.run(
                ["cc", "-std=c89", "-pedantic-errors", "-Wall", "-Wextra", "-Werror", str(src), "-o", str(out)],
                check=True,
                cwd=ROOT,
            )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_lower(self, text, profile):
        return subprocess.run(
            [str(self.lower_bin), profile], input=text, text=True, capture_output=True, cwd=ROOT
        )

    def bytes_for(self, text):
        low = self.run_lower(text, "--causal-time-v3")
        self.assertEqual(low.returncode, 0, low.stderr)
        emit = subprocess.run(
            [str(self.emit_bin)], input=low.stdout.encode("ascii"), capture_output=True, cwd=ROOT
        )
        self.assertEqual(emit.returncode, 0, emit.stderr)
        return low.stdout, emit.stdout

    def test_no_predecessor_is_not_invented_as_causality(self):
        ir, raw = self.bytes_for(plan(cause="-"))
        self.assertIn("MOVEQ D3 0\n", ir)
        self.assertEqual(raw, bytes.fromhex("72077403760070024e75"))

    def test_explicit_predecessor_is_machine_visible(self):
        ir, raw = self.bytes_for(plan(cause="r0"))
        self.assertIn("MOVEQ D3 1\n", ir)
        self.assertEqual(raw, bytes.fromhex("720f7403760170024e75"))

    def test_later_or_timestamp_is_not_a_cause_field(self):
        _, raw_a = self.bytes_for(plan(cause="-"))
        _, raw_b = self.bytes_for(plan(cause="-"))
        self.assertEqual(raw_a, raw_b)

    def test_v2_bytes_remain_unchanged(self):
        r = self.run_lower(plan(cause="r0"), "--semantic-witness-v2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("MOVEQ D3", r.stdout)

    def test_missing_cause_fails_closed(self):
        text = plan(cause="r0").replace("CAUSE=r0\n", "")
        r = self.run_lower(text, "--causal-time-v3")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertIn("SEMANTIC_WITNESS_UNVOLLSTAENDIG", r.stderr)


if __name__ == "__main__":
    unittest.main()
