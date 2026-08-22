import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_lean_gate_m68000_compiler.py"
LEAN = ROOT / "formalization" / "QIKVRT_Formalization_v1.0" / "QIKVRTFormalization" / "M68000Kernel.lean"
ASM = ROOT / "src" / "m68000" / "qikvrt_lean_gate_kernel.s"

spec = importlib.util.spec_from_file_location("qikvrt_lean_gate_m68000_compiler", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class LeanGateM68000CompilerTests(unittest.TestCase):
    def test_exact_machine_code(self):
        self.assertEqual(
            mod.compile_kernel().hex(),
            "08000001670470024e7508000000670470014e7570004e75",
        )

    def test_truth_table(self):
        expected = {0: 0, 1: 1, 2: 2, 3: 2}
        code = mod.compile_kernel()
        for flags, gate in expected.items():
            actual, _ = mod.execute_kernel(code, flags)
            self.assertEqual(actual, gate)
            self.assertEqual(mod.reference_gate(flags), gate)

    def test_all_low_byte_inputs_preserve_only_certificate_semantics(self):
        code = mod.compile_kernel()
        for flags in range(256):
            actual, _ = mod.execute_kernel(code, flags)
            self.assertEqual(actual, mod.reference_gate(flags))

    def test_bounded_dynamic_instruction_count(self):
        report = mod.verify_exhaustive(mod.compile_kernel())
        self.assertEqual(report["machine_bytes"], 24)
        self.assertLessEqual(report["max_dynamic_instructions"], 6)
        self.assertEqual(report["verified_inputs"], 256)

    def test_fail_closed_unknown_opcode(self):
        with self.assertRaisesRegex(RuntimeError, "unsupported opcode"):
            mod.execute_kernel(bytes.fromhex("ffff"), 0)

    def test_fail_closed_truncated_program(self):
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            mod.execute_kernel(mod.compile_kernel()[:-1], 0)

    def test_lean_source_binds_projection_theorem(self):
        text = LEAN.read_text(encoding="utf-8")
        self.assertIn("theorem evaluateGate_boolean_projection", text)
        self.assertIn("evaluateBooleanGate true true = Gate.block", text)
        self.assertIn("evaluateBooleanGate false false = Gate.continue", text)

    def test_assembly_source_preserves_block_priority(self):
        text = ASM.read_text(encoding="utf-8")
        self.assertLess(text.index("btst    #1,d0"), text.index("btst    #0,d0"))
        self.assertIn("moveq   #2,d0", text)
        self.assertIn("moveq   #1,d0", text)
        self.assertIn("moveq   #0,d0", text)

    def test_report_does_not_claim_physical_execution(self):
        report = mod.verify_exhaustive(mod.compile_kernel())
        self.assertFalse(report["physical_m68000_execution_observed"])


if __name__ == "__main__":
    unittest.main()
