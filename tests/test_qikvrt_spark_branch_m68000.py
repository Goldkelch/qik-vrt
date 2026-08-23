import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_spark_branch_m68000_compiler.py"
spec = importlib.util.spec_from_file_location("qikvrt_spark_branch_m68000_compiler", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class SparkBranchM68000CompilerTests(unittest.TestCase):
    def test_exact_machine_code_and_exhaustive_equivalence(self):
        self.assertEqual(len(mod.MACHINE), 134)
        report = mod.verify_exhaustive()
        self.assertEqual(report["verified_flag_bytes"], 256)
        self.assertEqual(report["plan_codes_observed"], list(range(12)))
        self.assertEqual(report["max_dynamic_instructions"], 18)

    def test_malformed_always_holds(self):
        for flags in range(256):
            if flags & mod.FLAG_MALFORMED:
                self.assertEqual(mod.reference_plan(flags), mod.PLAN_HOLD_INVALID)

    def test_merge_plans_require_authority(self):
        merge_plans = {
            mod.PLAN_REBASE_TO_CLOSE,
            mod.PLAN_MATERIALIZE_TO_CLOSE,
            mod.PLAN_VERIFY_TO_CLOSE,
            mod.PLAN_REPAIR_TO_CLOSE,
            mod.PLAN_MERGE_TO_CLOSE,
        }
        for flags in range(256):
            if mod.reference_plan(flags) in merge_plans:
                self.assertTrue(flags & mod.FLAG_AUTHORITY_AVAILABLE)

    def test_completion_requires_observed_main_effect(self):
        for flags in range(256):
            if mod.reference_plan(flags) == mod.PLAN_ALREADY_COMPLETE:
                self.assertTrue(flags & mod.FLAG_MAIN_EFFECT)


if __name__ == "__main__":
    unittest.main()
