from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "qikvrt_2383_architecture.py"
SPEC_PATH = (
    ROOT
    / "spec"
    / "architecture"
    / "QIKVRT_2383_VIRTUAL_M68000_ARCHITECTURE_V1.json"
)

MODULE_SPEC = importlib.util.spec_from_file_location("qikvrt_2383_architecture", TOOL_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"cannot import {TOOL_PATH}")
ARCH = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(ARCH)


class Qikvrt2383ArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = ARCH.load_contract(SPEC_PATH)

    def test_coherent_arithmetic_is_exact(self) -> None:
        result = ARCH.validate_contract(self.contract)
        self.assertEqual(
            result["verified_arithmetic"],
            {
                "two_pow_three": 8,
                "two_pow_eight": 256,
                "eight_pow_three": 512,
            },
        )
        self.assertNotEqual(8**3, 256)
        self.assertEqual(8**3, 512)
        self.assertEqual(2**8, 256)

    def test_literal_eight_cubed_equals_256_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["verified_arithmetic"]["eight_pow_three"] = 256
        with self.assertRaisesRegex(ARCH.ContractError, "verified_arithmetic"):
            ARCH.validate_contract(mutated)

    def test_state_cardinality_and_bit_width_remain_distinct(self) -> None:
        blockers = {
            item["blocker"]: item for item in self.contract["blocked_equivalences"]
        }
        boundary = blockers["CARDINALITY_WIDTH_CONFLATION"]
        self.assertEqual(boundary["claim"], "256 states = 256 bits")
        self.assertEqual(
            boundary["actual"], "STATE_CARDINALITY_AND_BIT_WIDTH_ARE_DISTINCT"
        )

    def test_all_material_blockers_are_required(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["blocked_equivalences"] = [
            item
            for item in mutated["blocked_equivalences"]
            if item["blocker"] != "MODEL_NOT_EFFECT"
        ]
        with self.assertRaisesRegex(ARCH.ContractError, "missing fail-closed blockers"):
            ARCH.validate_contract(mutated)

    def test_m68000_reference_witness_materializes_tuple_in_d4_to_d7(self) -> None:
        witness = self.contract["m68000_witness"]
        machine = ARCH.emulate_m68000_capsule(witness["machine_code_hex_big_endian"])
        observed = [machine["final_registers"][name] for name in ["D4", "D5", "D6", "D7"]]
        self.assertEqual(observed, [2, 3, 8, 3])
        self.assertEqual(machine["trace"][-1]["operation"], "RTS")
        self.assertFalse(machine["physical_execution_observed"])

    def test_m68000_reference_witness_preserves_d0_to_d3(self) -> None:
        witness = self.contract["m68000_witness"]
        machine = ARCH.emulate_m68000_capsule(witness["machine_code_hex_big_endian"])
        for register in ["D0", "D1", "D2", "D3"]:
            self.assertEqual(
                machine["final_registers"][register],
                machine["initial_registers"][register],
            )

    def test_unknown_m68000_opcode_fails_closed(self) -> None:
        with self.assertRaisesRegex(ARCH.ContractError, "unsupported M68000 opcode"):
            ARCH.emulate_m68000_capsule("ffff4e75")

    def test_virtual_witness_cannot_be_upgraded_to_physical_observation(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["m68000_witness"]["physical_m68000_execution_observed"] = True
        with self.assertRaisesRegex(ARCH.ContractError, "must remain false"):
            ARCH.validate_contract(mutated)

    def test_quantum_interface_model_cannot_be_upgraded_to_observed_effect(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["proof_boundaries"]["quantum_computation_observed"] = True
        with self.assertRaisesRegex(ARCH.ContractError, "must remain false"):
            ARCH.validate_contract(mutated)

    def test_owner_resolutions_remain_open(self) -> None:
        result = ARCH.validate_contract(self.contract)
        self.assertEqual(
            result["owner_resolution_required"],
            ["R1_256_RELATION", "R2_FINAL_THREE"],
        )
        self.assertEqual(result["status"], "HOLD_UNVERIFIED")
        self.assertFalse(result["pass"])
        self.assertFalse(result["final_pass"])
        self.assertFalse(result["effect_ack_done"])

    def test_cli_emits_deterministic_hold_record(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(TOOL_PATH), "--spec", str(SPEC_PATH)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        record = json.loads(completed.stdout)
        self.assertEqual(record["first_deterministic_blocker"], "ARITHMETIC_CONTRADICTION")
        self.assertEqual(record["status"], "HOLD_UNVERIFIED")
        self.assertFalse(record["pass"])


if __name__ == "__main__":
    unittest.main()
