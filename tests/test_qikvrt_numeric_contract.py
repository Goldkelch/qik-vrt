# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import unittest

from tools.qikvrt_numeric_contract import ContractError, DEFAULT_CONTRACT, exact_mac, read_contract, validate


class NumericContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = read_contract(DEFAULT_CONTRACT)

    def test_bound_contract_validates(self) -> None:
        report = validate(self.contract)
        self.assertEqual(report["state"], "OBSERVE")
        self.assertFalse(report["claims"]["performance_superiority_observed"])

    def test_exact_signed_mac(self) -> None:
        self.assertEqual(exact_mac([(3, 4), (-2, 5)], operand_width=8, accumulator_width=16), 2)

    def test_operand_violation_is_fail_closed(self) -> None:
        with self.assertRaisesRegex(ContractError, "operand out of range"):
            exact_mac([(128, 1)], operand_width=8, accumulator_width=16)

    def test_accumulator_overflow_is_fail_closed(self) -> None:
        with self.assertRaisesRegex(ContractError, "accumulator overflow"):
            exact_mac([(127, 127)] * 3, operand_width=8, accumulator_width=16)

    def test_contract_drift_breaks_digest(self) -> None:
        changed = copy.deepcopy(self.contract)
        changed["rounding"] = "toward_zero"
        with self.assertRaisesRegex(ContractError, "digest mismatch"):
            validate(changed)


if __name__ == "__main__":
    unittest.main()
