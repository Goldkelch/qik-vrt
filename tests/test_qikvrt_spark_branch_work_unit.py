import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_spark_branch_work_unit.py"
spec = importlib.util.spec_from_file_location("qikvrt_spark_branch_work_unit", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def obs(**overrides):
    value = {
        "malformed_or_scope_invalid": False,
        "main_effect_observed": False,
        "base_current": True,
        "integrity_current": True,
        "gates_terminal": True,
        "gates_non_adverse": True,
        "mergeable": True,
        "authority_available": True,
    }
    value.update(overrides)
    return value


class SparkBranchWorkUnitTests(unittest.TestCase):
    def test_one_core_pass_selects_complete_merge_ring(self):
        report = mod.select_complete_plan(obs())
        self.assertEqual(report["spark_core_passes"], 1)
        self.assertTrue(report["complete_branch_plan_selected"])
        self.assertEqual(report["plan"]["id"], "MERGE_TO_CLOSE")
        self.assertEqual(
            report["plan"]["steps"],
            ["MERGE", "REOBSERVE_MAIN_EFFECT", "COLLECT", "PERSIST", "RELEASE"],
        )

    def test_full_rebase_ring_reaches_complete_in_pure_adapter(self):
        report = mod.execute_pure_reference_ring(
            obs(
                base_current=False,
                integrity_current=False,
                gates_terminal=False,
                gates_non_adverse=False,
                mergeable=False,
            )
        )
        self.assertEqual(report["plan"]["id"], "REBASE_TO_CLOSE")
        self.assertEqual(report["pure_reference_execution"]["terminal"], "COMPLETE")
        self.assertTrue(
            report["pure_reference_execution"]["final_state"]["main_effect_observed"]
        )

    def test_no_authority_closes_to_precise_external_hold(self):
        report = mod.execute_pure_reference_ring(obs(authority_available=False))
        self.assertEqual(report["plan"]["id"], "REQUEST_AUTHORITY")
        self.assertEqual(
            report["pure_reference_execution"]["terminal"],
            "PRECISE_EXTERNAL_HOLD",
        )

    def test_malformed_is_fail_closed(self):
        report = mod.execute_pure_reference_ring(obs(malformed_or_scope_invalid=True))
        self.assertEqual(report["plan"]["id"], "HOLD_INVALID")
        self.assertEqual(report["pure_reference_execution"]["terminal"], "HOLD_INVALID")

    def test_unknown_or_non_boolean_observation_is_rejected(self):
        with self.assertRaises(ValueError):
            mod.select_complete_plan({})
        value = obs()
        value["mergeable"] = 1
        with self.assertRaises(ValueError):
            mod.select_complete_plan(value)

    def test_plan_selection_does_not_claim_effect_execution(self):
        report = mod.select_complete_plan(obs())
        self.assertFalse(report["host_effects_executed"])
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertFalse(report["pass_claimed"])
        self.assertFalse(report["final_pass_claimed"])
        self.assertFalse(report["effect_ack_done_claimed"])


if __name__ == "__main__":
    unittest.main()
