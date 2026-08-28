# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/qikvrt_quantum_causal_neutron_star_fixpoint.py"
SPEC = importlib.util.spec_from_file_location("qikvrt_inside_out", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class QuantumCausalNeutronStarFixpointTests(unittest.TestCase):
    def test_complete_validation_is_observe_without_completion_claims(self) -> None:
        receipt = MODULE.validate()
        self.assertEqual(receipt["state"], "OBSERVE")
        self.assertFalse(receipt["claims"]["PASS"])
        self.assertFalse(receipt["claims"]["FINAL_PASS"])
        self.assertFalse(receipt["claims"]["EFFECT_ACK_DONE"])

    def test_inside_out_order_is_exact(self) -> None:
        contract = json.loads(MODULE.CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in contract["inside_out_layers"]], MODULE.EXPECTED_LAYERS)

    def test_uploaded_source_contracts_are_byte_exact(self) -> None:
        contract = json.loads(MODULE.CONTRACT_PATH.read_text(encoding="utf-8"))
        MODULE.validate_source_contracts(contract)

    def test_vhdl_is_hardware_description_not_cpu_machine_code(self) -> None:
        contract = json.loads(MODULE.CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["vhdl_profile"]["role"], "HARDWARE_DESCRIPTION_AND_SYNTHESIS_BRIDGE")
        self.assertFalse(contract["vhdl_profile"]["literal_cpu_machine_code"])
        MODULE.validate_vhdl(contract)

    def test_physical_and_quantum_claims_remain_fail_closed(self) -> None:
        contract = json.loads(MODULE.CONTRACT_PATH.read_text(encoding="utf-8"))
        boundary = contract["claim_boundary"]
        self.assertEqual(boundary["quantum_causality_class"], "QUANTUM_CAUSALITY_HYPOTHESIS")
        self.assertFalse(boundary["physical_quantum_causality_established"])
        self.assertFalse(boundary["physical_hardware_execution_observed"])
        self.assertFalse(boundary["astrophysical_neutron_star_simulation_observed"])

    def test_terminal_is_manual_public_get_only(self) -> None:
        status = json.loads(MODULE.STATUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(status["mode"], "PUBLIC_GET_ONLY")
        self.assertFalse(status["background_polling"])
        self.assertEqual(status["layer_order"], MODULE.EXPECTED_LAYERS)

    def test_cli_validate_is_json(self) -> None:
        completed = subprocess.run([sys.executable, "-B", str(MODULE_PATH), "validate"], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["state"], "OBSERVE")

if __name__ == "__main__":
    unittest.main()
