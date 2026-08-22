from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_d3_ring_lifecycle",
    ROOT / "tools/qikvrt_d3_ring_lifecycle.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class D3RingLifecycleTests(unittest.TestCase):
    def test_exact_virtual_ring_widths_and_byte_cardinality_remain_distinct(self) -> None:
        self.assertEqual(MODULE.ring_width_bits(1), 8)
        self.assertEqual(MODULE.byte_state_cardinality(), 256)
        self.assertEqual(MODULE.ring_width_bits(2), 256)
        self.assertEqual(MODULE.ring_width_bits(3), 256**3)
        self.assertEqual(MODULE.ring_width_bits(3), 2**24)

    def test_reference_lifecycle_returns_each_ring_to_quiescence(self) -> None:
        result = MODULE.reference_run()
        self.assertEqual(result["final"]["d3"], 0)
        self.assertEqual(result["final"]["phase"], "QUIESCENT")
        self.assertFalse(result["final"]["global_halt"])
        self.assertFalse(result["final"]["owner_interrupt"])
        operations = [event["operation"] for event in result["events"]]
        self.assertEqual(
            operations,
            ["ACTIVATE", "COLLECT_RESULT", "PERSIST", "RELEASE_RESOURCES", "QUIESCE"] * 3,
        )

    def test_quiesce_fails_closed_before_collect_persist_release(self) -> None:
        machine = MODULE.Machine()
        machine.activate(1)
        with self.assertRaises(MODULE.LifecycleError):
            machine.quiesce()
        machine.collect_result()
        with self.assertRaises(MODULE.LifecycleError):
            machine.quiesce()
        machine.persist()
        with self.assertRaises(MODULE.LifecycleError):
            machine.quiesce()
        machine.release_resources()
        event = machine.quiesce()
        self.assertEqual((event.d3_before, event.d3_after), (1, 0))

    def test_m68000_lowering_executes_exact_d3_boundaries(self) -> None:
        payload = MODULE.lower_d3_lifecycle_to_m68000()
        result = MODULE.execute_m68000_lifecycle(payload)
        expected = MODULE.lifecycle_boundary(MODULE.reference_run()["events"])
        self.assertEqual(result["transitions"], expected)
        self.assertEqual(result["final_d3"], 0)
        self.assertFalse(result["physical_execution_observed"])

    def test_m68000_interpreter_rejects_unsupported_or_incomplete_programs(self) -> None:
        with self.assertRaises(MODULE.LifecycleError):
            MODULE.execute_m68000_lifecycle(bytes.fromhex("4e71"))
        with self.assertRaises(MODULE.LifecycleError):
            MODULE.execute_m68000_lifecycle(MODULE.lower_d3_lifecycle_to_m68000()[:-2])
        with self.assertRaises(MODULE.LifecycleError):
            MODULE.execute_m68000_lifecycle(bytes.fromhex("76004e75"))

    def test_c89_host_execution_matches_reference_trace(self) -> None:
        source = ROOT / "src/qikvrt_d3_ring_lifecycle.c"
        with tempfile.TemporaryDirectory() as temporary:
            binary = pathlib.Path(temporary) / "d3-lifecycle"
            subprocess.run(
                ["cc", "-std=c90", "-pedantic", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            completed = subprocess.run(
                [str(binary)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        lines = completed.stdout.strip().splitlines()
        reference = MODULE.reference_run()
        expected = []
        for event, width in zip(reference["events"], [8]*5 + [256]*5 + [256**3]*5):
            expected.append(
                f"{event['operation']} {event['ring']} {event['d3_before']} {event['d3_after']} {width}"
            )
        self.assertEqual(lines[:-1], expected)
        self.assertEqual(lines[-1], "FINAL D3=0 GLOBAL_HALT=0 OWNER_INTERRUPT=0 BYTE_STATES=256")

    def test_equivalence_report_preserves_truth_boundaries(self) -> None:
        report = MODULE.equivalence_report()
        self.assertTrue(report["equivalent_boundary"])
        self.assertEqual(report["final_d3"], 0)
        for value in report["claims"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
