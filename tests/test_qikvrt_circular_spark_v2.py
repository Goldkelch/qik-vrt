import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_circular_spark_v2.py"
spec = importlib.util.spec_from_file_location("qikvrt_circular_spark_v2", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class CircularSparkV2Tests(unittest.TestCase):
    def test_scale_preserves_width_and_state_cardinality_distinctions(self):
        architecture = mod.load_architecture()
        scale = architecture["scale"]
        self.assertEqual(scale["sequence"], [0, 1, 2, 8, 256])
        self.assertEqual(scale["explicit_evidence_ring_bits"], 256)
        self.assertEqual(scale["macro_ring_bits"], 256 ** 3)
        self.assertEqual(scale["macro_ring_bytes"], 2 * 1024 * 1024)
        self.assertEqual(
            scale["macro_ring_state_cardinality"]["expression"],
            "2^(256^3)",
        )
        self.assertFalse(
            scale["macro_ring_state_cardinality"]["materialized_or_enumerated"]
        )

    def test_hardware_and_virtual_roles_are_circular_and_alternating(self):
        architecture = mod.load_architecture()
        cycle = architecture["circular_layer_cycle"]
        self.assertEqual(len(cycle), 6)
        self.assertEqual(cycle[0]["kind"], "VIRTUAL_COMPILER")
        self.assertEqual(cycle[1]["kind"], "PHYSICAL_M68000_PLAN_ROLE")
        self.assertEqual(
            cycle[2]["kind"], "VIRTUAL_INTERPRETER_EFFECT_ADAPTER"
        )
        self.assertEqual(cycle[3]["kind"], "PHYSICAL_M68000_CLOSURE_ROLE")
        self.assertEqual(cycle[4]["kind"], "VIRTUAL_REOBSERVATION")

    def test_ready_work_unit_closes_one_reference_spark_cycle(self):
        report = mod.run_reference_cycle(mod.fixture_observation("complete"))
        self.assertEqual(report["spark_core_cycle_count"], 1)
        self.assertEqual(report["branch_work_units_admitted"], 1)
        self.assertEqual(report["complete_branch_plans_selected"], 1)
        self.assertEqual(report["selected_plan"], "MERGE_TO_CLOSE")
        self.assertEqual(report["reference_terminal"], "COMPLETE")
        self.assertTrue(report["d3_preserved"])
        self.assertEqual(report["runtime_compiler_invocations"], 0)

    def test_full_rebase_work_unit_closes_in_same_bounded_reference_ring(self):
        report = mod.run_reference_cycle(mod.fixture_observation("rebase"))
        self.assertEqual(report["selected_plan"], "REBASE_TO_CLOSE")
        self.assertEqual(report["reference_terminal"], "COMPLETE")
        adapter = report["trace"][2]
        self.assertEqual(
            adapter["steps"],
            [
                "REBASE",
                "MATERIALIZE",
                "VERIFY",
                "MERGE",
                "REOBSERVE_MAIN_EFFECT",
                "COLLECT",
                "PERSIST",
                "RELEASE",
            ],
        )

    def test_no_authority_and_invalid_inputs_fail_closed(self):
        noauth = mod.run_reference_cycle(
            mod.fixture_observation("no-authority")
        )
        self.assertEqual(noauth["selected_plan"], "REQUEST_AUTHORITY")
        self.assertEqual(
            noauth["reference_terminal"], "PRECISE_EXTERNAL_HOLD"
        )
        invalid = mod.run_reference_cycle(mod.fixture_observation("invalid"))
        self.assertEqual(invalid["selected_plan"], "HOLD_INVALID")
        self.assertEqual(invalid["reference_terminal"], "HOLD_INVALID")

    def test_reference_cycle_does_not_claim_host_or_physical_effect(self):
        report = mod.run_reference_cycle(mod.fixture_observation("complete"))
        self.assertFalse(report["host_effects_executed"])
        self.assertFalse(report["authority_main_effect"])
        self.assertFalse(
            report["hatari_m68000_execution_observed_for_new_spark_kernels"]
        )
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertFalse(report["physical_speedup_ratio_measured"])
        self.assertFalse(report["pass"])
        self.assertFalse(report["final_pass"])
        self.assertFalse(report["effect_ack_done"])

    def test_registry_contains_both_spark_kernels(self):
        registry = json.loads(
            (
                ROOT
                / "runtime/m68000/QIKVRT_COMPILED_KERNELS_V1.json"
            ).read_text(encoding="utf-8")
        )
        ids = [item["id"] for item in registry["kernels"]]
        self.assertEqual(
            ids,
            [
                "lean_gate_v1",
                "lean_v2_d3_step_v1",
                "lean_v2_mesh_recovery_v1",
                "lean_spark_branch_pass_v1",
                "lean_spark_branch_plan_v1",
            ],
        )
        self.assertEqual(registry["compiled_machine_bytes_total"], 284)


if __name__ == "__main__":
    unittest.main()
