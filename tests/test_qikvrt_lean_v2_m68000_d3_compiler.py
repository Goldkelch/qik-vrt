import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_lean_v2_m68000_d3_compiler.py"
LEAN = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "QIKVRTFormalization" / "Hardware" / "M68000D3Step.lean"

spec = importlib.util.spec_from_file_location("qikvrt_lean_v2_m68000_d3_compiler", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class V2D3CompilerTests(unittest.TestCase):
    def test_exact_machine_code(self):
        self.assertEqual(mod.MACHINE.hex(), "0c020002620a670452024e7574004e7570014e75")

    def test_exhaustive_valid_projection(self):
        report = mod.verify()
        self.assertEqual(report["valid_state_tuples_verified"], 3072)
        self.assertTrue(report["d3_preserved"])

    def test_each_phase_advances_mod_three(self):
        for phase in range(3):
            d0, d2, d3, _ = mod.execute(mod.MACHINE, 3, phase, 0x7F)
            self.assertEqual((d0, d2, d3), (3, (phase + 1) % 3, 0x7F))

    def test_invalid_phase_fails_closed_and_preserves_d3(self):
        for phase in range(3, 256):
            d0, _d2, d3, _ = mod.execute(mod.MACHINE, 0, phase, 0xA5)
            self.assertEqual(d0, 1)
            self.assertEqual(d3, 0xA5)

    def test_lean_refinement_and_d3_theorems_present(self):
        text = LEAN.read_text(encoding="utf-8")
        self.assertIn("theorem machineProjection_refines_step", text)
        self.assertIn("theorem machineProjection_preserves_d3", text)
        self.assertIn("theorem phaseCode_next_mod_three", text)

    def test_no_physical_claim(self):
        report = mod.verify()
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertFalse(report["physical_speedup_measured"])


if __name__ == "__main__":
    unittest.main()
