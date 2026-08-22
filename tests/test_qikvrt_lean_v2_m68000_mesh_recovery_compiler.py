import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "qikvrt_lean_v2_m68000_mesh_recovery_compiler.py"
LEAN = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "QIKVRTFormalization" / "Hardware" / "AuthorityMirrorWitness.lean"

spec = importlib.util.spec_from_file_location("qikvrt_lean_v2_m68000_mesh_recovery_compiler", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class MeshRecoveryCompilerTests(unittest.TestCase):
    def test_exact_machine_code(self):
        self.assertEqual(mod.MACHINE.hex(), "0c000006620e0c000004640470004e7570014e7570024e75")

    def test_exact_valid_truth_table(self):
        expected = [0, 0, 0, 0, 1, 1, 1]
        for cutpoint, result in enumerate(expected):
            actual, _ = mod.execute(mod.MACHINE, cutpoint)
            self.assertEqual(actual, result)
            self.assertEqual(mod.lean_reference(cutpoint), result)

    def test_all_invalid_byte_values_hold(self):
        for cutpoint in range(7, 256):
            actual, _ = mod.execute(mod.MACHINE, cutpoint)
            self.assertEqual(actual, mod.HOLD)

    def test_report(self):
        report = mod.verify()
        self.assertEqual(report["valid_cutpoints_verified"], 7)
        self.assertEqual(report["invalid_cutpoints_fail_closed"], 249)
        self.assertEqual(report["machine_bytes"], 24)
        self.assertLessEqual(report["max_dynamic_instructions"], 6)

    def test_frozen_lean_source_binds_recovery_theorems(self):
        text = LEAN.read_text(encoding="utf-8")
        self.assertIn("def recoveryChoice : CutPoint → RecoveryChoice", text)
        self.assertIn("theorem T06_crash_before_witness_recovers_predecessor", text)
        self.assertIn("theorem T07_crash_after_witness_recovers_successor", text)
        self.assertIn("def witnesslessRecovery : DuplexSelection := .hold", text)

    def test_no_physical_claim(self):
        report = mod.verify()
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertFalse(report["physical_speedup_measured"])


if __name__ == "__main__":
    unittest.main()
