import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import qikvrt_spark_branch as spark


class SparkBranchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler_report = spark.verify_exhaustive()

    def test_exact_machine_code_and_bound(self):
        self.assertEqual(spark.MACHINE.hex(), spark.EXPECTED_HEX)
        self.assertEqual(len(spark.MACHINE), 82)
        self.assertEqual(self.compiler_report["input_pairs_verified"], 65536)
        self.assertTrue(self.compiler_report["d3_preserved"])
        self.assertLessEqual(
            self.compiler_report["max_dynamic_instructions"], 21
        )

    def test_persisted_hex_is_compiler_identical(self):
        stored = bytes.fromhex(
            spark.HEX_PATH.read_text(encoding="utf-8").strip()
        )
        self.assertEqual(stored, spark.MACHINE)

    def test_complete_batch_closes_one_work_unit_per_pass(self):
        report = spark.run_batch(
            repository="Goldkelch/qik-vrt",
            branch="fixture",
            base_sha="a" * 40,
            head_sha="b" * 40,
            tree_sha="c" * 40,
            mode="complete",
            batch=256,
        )
        self.assertEqual(report["processor_passes"], 256)
        self.assertEqual(report["work_units_consumed"], 256)
        self.assertEqual(report["bounded_work_units_closed"], 256)
        self.assertTrue(report["one_processor_pass_per_work_unit"])
        self.assertTrue(
            all(item["decision_code"] == 0 for item in report["results"])
        )
        self.assertTrue(
            all(
                item["d3_before"] == item["d3_after"]
                for item in report["results"]
            )
        )

    def test_terminal_modes_remain_distinct(self):
        expected = {
            "complete": (0, 1, 0),
            "stale": (2, 0, 1),
            "authority": (3, 0, 0),
            "hold": (1, 0, 0),
            "incomplete": (2, 0, 1),
        }
        for mode, triple in expected.items():
            with self.subTest(mode=mode):
                report = spark.run_batch(
                    repository="Goldkelch/qik-vrt",
                    branch="fixture",
                    base_sha="a" * 40,
                    head_sha="b" * 40,
                    tree_sha="c" * 40,
                    mode=mode,
                    batch=1,
                )
                item = report["results"][0]
                self.assertEqual(
                    (
                        item["decision_code"],
                        item["completion_witness"],
                        item["machine_owned_active"],
                    ),
                    triple,
                )

    def test_three_ring_architecture_and_two_three_eight_three_resolution(self):
        architecture = json.loads(
            spark.ARCHITECTURE.read_text(encoding="utf-8")
        )
        self.assertEqual(len(architecture["structural_rings"]), 3)
        binding = architecture["two_three_eight_three_binding"]
        self.assertEqual(binding["two_power_three_bits"], 8)
        self.assertEqual(binding["first_ring_possible_states"], 256)
        self.assertEqual(binding["outer_evidence_ring_bits"], 256)
        self.assertIn(
            "not derived from 8^3", binding["outer_evidence_ring_rule"]
        )

    def test_generation_v2_registry_is_bound_without_reinterpretation(self):
        architecture, code = spark.load_contract()
        self.assertEqual(code, spark.MACHINE)
        self.assertEqual(
            architecture["required_upstream_kernel_ids"],
            [
                "lean_gate_v1",
                "lean_v2_d3_step_v1",
                "lean_v2_mesh_recovery_v1",
                "lean_spark_branch_pass_v1",
                "lean_spark_branch_plan_v1",
            ],
        )
        self.assertEqual(
            architecture["registry_evolution"][
                "registered_machine_bytes_total"
            ],
            284,
        )

    def test_lean_source_closes_expected_finite_statements_without_holes(self):
        source = (
            ROOT / "formalization/QIKVRT_Spark_v1/QIKVRTSpark.lean"
        ).read_text(encoding="utf-8")
        for theorem in (
            "one_spark_pass_closes_complete_capsule",
            "projection_preserves_d3",
            "stale_capsule_requires_reobservation",
            "missing_authority_requests_authority",
            "unclassified_capsule_holds_fail_closed",
        ):
            self.assertIn(theorem, source)
        self.assertIsNone(
            re.search(
                r"(?m)^[ \t]*(axiom|sorry|admit)(?:[ \t]|$)", source
            )
        )

    def test_claim_boundaries(self):
        report = spark.run_batch(
            repository="Goldkelch/qik-vrt",
            branch="fixture",
            base_sha="a" * 40,
            head_sha="b" * 40,
            tree_sha="c" * 40,
            mode="complete",
            batch=1,
        )
        self.assertTrue(report["virtual_m68000_execution_observed"])
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertFalse(report["physical_atari_mega_st_execution_observed"])
        self.assertFalse(report["numeric_physical_speedup_measured"])
        self.assertFalse(report["git_merge_effect_applied"])
        self.assertFalse(report["pass"])
        self.assertFalse(report["final_pass"])
        self.assertFalse(report["effect_ack_done"])


if __name__ == "__main__":
    unittest.main()
