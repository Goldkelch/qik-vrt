import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_virtual_mesh_m68000_acceptance.py"
spec = importlib.util.spec_from_file_location("qikvrt_virtual_mesh_m68000_acceptance", TOOL)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class VirtualMeshM68000AcceptanceTests(unittest.TestCase):
    def test_registry_loads_exact_four_kernel_inventory(self):
        registry, kernels = mod.load_registry()
        self.assertEqual(registry["target"], "Motorola 68000")
        self.assertEqual(tuple(kernels), mod.EXPECTED_IDS)
        self.assertEqual(sum(map(len, kernels.values())), 202)

    def test_virtual_mesh_executes_registered_bytes(self):
        report = mod.execute_virtual_mesh(iterations=2)
        self.assertEqual(report["schema"], "QIKVRT_VIRTUAL_MESH_M68000_ACCEPTANCE_V2")
        self.assertTrue(report["compiled_kernel_registry_loaded"])
        self.assertTrue(report["registered_machine_bytes_executed"])
        self.assertTrue(report["virtual_m68000_execution_observed"])
        self.assertTrue(report["complete_branch_plan_selected_by_m68000"])
        self.assertEqual(report["compiled_machine_bytes_total"], 202)

    def test_existing_abis_and_spark_plan_are_distinct(self):
        report = mod.execute_virtual_mesh()
        self.assertTrue(report["semantic_abis_kept_distinct"])
        self.assertEqual(report["gate"]["output_gate"], 1)
        self.assertEqual(report["d3_lifecycle"]["decision_code"], 2)
        self.assertEqual(report["d3_lifecycle"]["final_phase_code"], 0)
        self.assertTrue(report["d3_lifecycle"]["d3_preserved"])
        self.assertEqual(report["spark_branch"]["exhaustive_flag_bytes_verified"], 256)
        self.assertEqual(report["spark_branch"]["max_dynamic_instructions"], 18)
        self.assertEqual(report["spark_branch"]["last_observations"][-2:], [
            {"observation_flags": 252, "plan_code": 10},
            {"observation_flags": 248, "plan_code": 2},
        ])

    def test_invalid_iteration_count_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "iterations must be positive"):
            mod.execute_virtual_mesh(iterations=0)

    def test_registry_path_cannot_escape_repository(self):
        with self.assertRaisesRegex(ValueError, "escapes repository"):
            mod._repository_path(ROOT, "../outside")

    def test_cli_emits_machine_readable_report(self):
        proc = subprocess.run([sys.executable, str(TOOL), "--iterations", "1", "--json"], cwd=ROOT, text=True, capture_output=True, check=True)
        report = json.loads(proc.stdout)
        self.assertEqual(report["kernel_ids"], list(mod.EXPECTED_IDS))

    def test_no_physical_or_terminal_claim_is_promoted(self):
        report = mod.execute_virtual_mesh()
        self.assertFalse(report["host_github_effect_executed_by_m68000"])
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertFalse(report["physical_speedup_measured"])
        self.assertFalse(report["workflow_accelerated_by_m68000"])
        self.assertFalse(report["pass_claimed"])
        self.assertFalse(report["final_pass_claimed"])
        self.assertFalse(report["effect_ack_done_claimed"])


if __name__ == "__main__":
    unittest.main()
