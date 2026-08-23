from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools import qikvrt_spark_branch_pass_m68000 as spark

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/SPARK_CIRCULAR_ARCHITECTURE_V1.json"
HEX = ROOT / "runtime/m68000/qikvrt_spark_branch_pass.hex"
LEAN = ROOT / "formalization/QIKVRT_Spark_Circular_v0.1/QIKVRTSparkCircular.lean"


class SparkBranchPassM68000Tests(unittest.TestCase):
    def test_exact_machine_code(self) -> None:
        expected = HEX.read_text(encoding="utf-8").strip()
        self.assertEqual(spark.compile_kernel().hex(), expected)
        self.assertEqual(len(spark.compile_kernel()), 44)

    def test_exhaustive_valid_descriptor_lifecycle_domain(self) -> None:
        code = spark.compile_kernel()
        for mask in range(spark.FULL_MASK + 1):
            for d3 in (0, 1):
                out_mask, disposition, out_d3, _count = spark.execute_kernel(code, mask, d3)
                self.assertEqual(out_mask, mask)
                self.assertEqual(
                    (disposition, out_d3),
                    spark.reference_branch_pass(mask, d3),
                )

    def test_lifecycle_semantics(self) -> None:
        code = spark.compile_kernel()
        self.assertEqual(spark.execute_kernel(code, 0, 0)[:3], (0, spark.IDLE, 0))
        self.assertEqual(spark.execute_kernel(code, 1, 0)[:3], (1, spark.ACTIVE, 1))
        self.assertEqual(spark.execute_kernel(code, 1, 1)[:3], (1, spark.ACTIVE, 1))
        self.assertEqual(
            spark.execute_kernel(code, spark.FULL_MASK, 1)[:3],
            (spark.FULL_MASK, spark.COMPLETE, 0),
        )

    def test_invalid_inputs_fail_closed(self) -> None:
        code = spark.compile_kernel()
        for d3 in range(2, 256):
            out_mask, disposition, out_d3, _count = spark.execute_kernel(code, 1, d3)
            self.assertEqual((out_mask, disposition, out_d3), (1, spark.HOLD, d3))
        for mask in (spark.FULL_MASK + 1, 0xFFFFFFFF):
            out_mask, disposition, out_d3, _count = spark.execute_kernel(code, mask, 0)
            self.assertEqual((out_mask, disposition, out_d3), (mask, spark.HOLD, 0))

    def test_ring_arithmetic_keeps_distinctions(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        rings = {entry["id"]: entry for entry in policy["ring_ladder"]}
        self.assertEqual(2**3, 8)
        self.assertEqual(2**8, 256)
        self.assertEqual(rings["R256_STATES"]["meaning"], "POSSIBLE_VALUES_OF_ONE_BYTE")
        self.assertEqual(
            rings["R256_WIDTH"]["meaning"],
            "EXPLICIT_VIRTUAL_RING_WIDTH_INDEPENDENT_OF_BYTE_STATE_COUNT",
        )
        self.assertEqual(rings["R_SYMBOLIC_OUTER"]["literal"], "2^(256^3)")
        self.assertEqual(rings["R_SYMBOLIC_OUTER"]["materialization"], "SPARSE_HASH_ADDRESSED_ONLY")
        self.assertEqual(policy["branch_pass"]["physical_data_register_bits"], 32)

    def test_complete_is_not_promoted_to_external_effect(self) -> None:
        report = spark.verify()
        self.assertFalse(report["branch_pass_complete_is_git_merge"])
        self.assertFalse(report["symbolic_outer_ring_eagerly_materialized"])
        self.assertFalse(report["physical_m68000_execution_observed"])
        self.assertFalse(report["physical_speedup_measured"])
        self.assertFalse(report["pass"])
        self.assertFalse(report["final_pass"])
        self.assertFalse(report["effect_ack_done"])

    def test_formal_candidate_contains_required_theorems_without_holes(self) -> None:
        source = LEAN.read_text(encoding="utf-8")
        for name in (
            "zero_quiescent_is_idle",
            "partial_descriptor_activates",
            "complete_descriptor_quiesces",
            "invalid_lifecycle_holds",
            "unknown_descriptor_bits_hold",
        ):
            self.assertIn(name, source)
        for forbidden in ("sorry", "admit", "axiom"):
            self.assertNotRegex(source, rf"(?m)^\\s*{forbidden}\\b")


if __name__ == "__main__":
    unittest.main()
