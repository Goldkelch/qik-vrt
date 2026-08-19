import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "tools" / "qikvrt_universal_understanding_ansic.c"
LOWER = ROOT / "tools" / "qikvrt_metagrammar_m68000_lower_ansic.c"
EMIT = ROOT / "tools" / "qikvrt_m68000_emitter_ansic.c"


class M68000SemanticDecisionCapsuleV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.front = Path(cls.tmp.name) / "universal-front"
        cls.lower = Path(cls.tmp.name) / "m68000-lower"
        cls.emit = Path(cls.tmp.name) / "m68000-emit"
        for source, target in [(FRONT, cls.front), (LOWER, cls.lower), (EMIT, cls.emit)]:
            subprocess.run(
                [
                    "cc",
                    "-std=c89",
                    "-pedantic-errors",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    str(source),
                    "-o",
                    str(target),
                ],
                check=True,
                cwd=ROOT,
            )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def source(
        self,
        *,
        next_action="REOBSERVE",
        auth_state="BOUND",
        effect_state="NONE",
        cause="-",
    ):
        return (
            "QIKU1\n"
            "KIND OBSERVE\n"
            "RID r1\n"
            f"SUBJECT repo Goldkelch/qik-vrt {'a' * 40} {'b' * 40}\n"
            "INTENT OBSERVE terminal\n"
            f"AUTH {auth_state} po-1\n"
            f"EVID HEAD {'c' * 64}\n"
            "STATE OBSERVED\n"
            f"EFFECT {effect_state} effect-1\n"
            f"NEXT {next_action}\n"
            f"PROOF {'d' * 64}\n"
            f"CAUSE {cause}\n"
            "END\n"
        )

    def compile_plan(self, text):
        front = subprocess.run(
            [str(self.front), "--target-megast"],
            input=text,
            text=True,
            capture_output=True,
            cwd=ROOT,
        )
        self.assertEqual(front.returncode, 0, front.stderr)
        return front.stdout

    def emit(self, plan, *, v2):
        argv = [str(self.lower)]
        if v2:
            argv.append("--semantic-witness-v2")
        lower = subprocess.run(argv, input=plan, text=True, capture_output=True, cwd=ROOT)
        self.assertEqual(lower.returncode, 0, lower.stderr)
        emitted = subprocess.run(
            [str(self.emit)],
            input=lower.stdout.encode("ascii"),
            capture_output=True,
            cwd=ROOT,
        )
        self.assertEqual(emitted.returncode, 0, emitted.stderr)
        return emitted.stdout

    def test_v1_bytes_remain_unchanged(self):
        plan = self.compile_plan(self.source(next_action="REOBSERVE"))
        self.assertEqual(self.emit(plan, v2=False), bytes.fromhex("70024e75"))

    def test_v2_binds_kernel_authority_effect_and_action_to_registers(self):
        plan = self.compile_plan(self.source(next_action="REOBSERVE"))
        # D1=0b0111: kernel + type boundaries + bound authority; no explicit cause.
        # D2=0: EFFECT NONE. D0=2: REOBSERVE. RTS.
        self.assertEqual(self.emit(plan, v2=True), bytes.fromhex("7207740070024e75"))

    def test_v2_explicit_cause_is_machine_visible(self):
        plan = self.compile_plan(
            self.source(next_action="REOBSERVE", effect_state="OBSERVED", cause="parent-event")
        )
        # D1=0b1111 includes explicit causal predecessor; D2=3 is OBSERVED.
        self.assertEqual(self.emit(plan, v2=True), bytes.fromhex("720f740370024e75"))

    def test_v2_nonbound_authority_clears_authority_bit_but_stays_fail_closed(self):
        plan = self.compile_plan(
            self.source(
                next_action="HOLD",
                auth_state="MISSING",
                effect_state="REQUESTED",
                cause="parent-event",
            )
        )
        # D1=0b1011: kernel + type boundaries + explicit cause, but no authority bit.
        # D2=1: REQUESTED. D0=1: HOLD.
        self.assertEqual(self.emit(plan, v2=True), bytes.fromhex("720b740170014e75"))

    def test_v2_rejects_plan_without_semantic_witness(self):
        lower = subprocess.run(
            [str(self.lower), "--semantic-witness-v2"],
            input="NEXT_ACTION=HOLD\nADMISSION=VALIDATED\n",
            text=True,
            capture_output=True,
            cwd=ROOT,
        )
        self.assertEqual(lower.returncode, 2)
        self.assertIn("SEMANTIC_WITNESS_UNVOLLSTAENDIG", lower.stderr)
        self.assertEqual(lower.stdout, "")


if __name__ == "__main__":
    unittest.main()
