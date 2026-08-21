# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import itertools
import pathlib
import sys
import unittest

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools import qikvrt_iedl_for_children as iedl


class IEDLSevenStageContractTests(unittest.TestCase):
    def test_positive_witness_executes_all_seven_stages_and_improves(self) -> None:
        result = iedl.run_positive_witness()
        self.assertEqual(
            result.stages,
            (
                "MATCH",
                "PARSE",
                "BIND",
                "BEWEIS",
                "ENTSCHEIDE",
                "MACH",
                "SCHAU_NACH",
            ),
        )
        self.assertTrue(result.executed)
        self.assertTrue(result.reobserved)
        self.assertTrue(result.improved)
        self.assertTrue(result.verified_improvement)
        self.assertEqual(result.before.stone3, result.after.stone3)
        self.assertGreater(result.after.quality, result.before.quality)

    def test_every_missing_gate_blocks_productive_effect_exhaustively(self) -> None:
        names = (
            "match_ok",
            "parse_ok",
            "bind_ok",
            "evidence_ok",
            "authorized_decision",
            "invariant_safe",
        )
        blocked = 0
        executed = 0
        for values in itertools.product((False, True), repeat=len(names)):
            gates = iedl.Gates(**dict(zip(names, values, strict=True)))
            result = iedl.run(gates, observed_quality=2)
            if all(values):
                executed += 1
                self.assertTrue(result.executed)
            else:
                blocked += 1
                self.assertFalse(result.executed)
                self.assertFalse(result.verified_improvement)
                self.assertEqual(result.before, result.after)
        self.assertEqual(blocked, 63)
        self.assertEqual(executed, 1)

    def test_mach_is_not_success_without_better_reobservation(self) -> None:
        result = iedl.run(iedl.Gates.all_open(), observed_quality=1)
        self.assertTrue(result.executed)
        self.assertTrue(result.reobserved)
        self.assertFalse(result.improved)
        self.assertFalse(result.verified_improvement)

    def test_invariant_break_is_blocked_before_effect(self) -> None:
        gates = iedl.Gates.all_open().replace(invariant_safe=False)
        result = iedl.run(gates, observed_quality=2)
        self.assertFalse(result.executed)
        self.assertEqual(result.decision, iedl.Decision.HOLD)
        self.assertEqual(result.before.stone3, result.after.stone3)

    def test_missing_evidence_reobserves(self) -> None:
        gates = iedl.Gates.all_open().replace(evidence_ok=False)
        result = iedl.run(gates, observed_quality=2)
        self.assertFalse(result.executed)
        self.assertEqual(result.decision, iedl.Decision.REOBSERVE)

    def test_missing_authority_is_d0_three_request_authority(self) -> None:
        gates = iedl.Gates.all_open().replace(authorized_decision=False)
        result = iedl.run(gates, observed_quality=2)
        self.assertFalse(result.executed)
        self.assertEqual(result.decision, iedl.Decision.REQUEST_AUTHORITY)
        self.assertEqual(result.decision.value, 3)

    def test_later_without_improvement_is_not_better(self) -> None:
        result = iedl.run(iedl.Gates.all_open(), observed_quality=1)
        self.assertGreater(result.after.logical_time, result.before.logical_time)
        self.assertFalse(result.improved)
        self.assertFalse(result.verified_improvement)

    def test_machine_proof_receipt_covers_all_64_gate_combinations(self) -> None:
        receipt = iedl.prove_contract()
        self.assertEqual(receipt["gate_combinations_checked"], 64)
        self.assertEqual(receipt["blocked_combinations"], 63)
        self.assertEqual(receipt["productive_combinations"], 1)
        self.assertTrue(receipt["positive_witness"]["verified_improvement"])
        self.assertTrue(receipt["protected_invariant_preserved"])
        self.assertFalse(receipt["MACH_IMPLIES_SUCCESS"])
        self.assertFalse(receipt["LATER_IMPLIES_BETTER"])
        self.assertFalse(receipt["PASS"])
        self.assertFalse(receipt["FINAL_PASS"])
        self.assertFalse(receipt["EFFECT_ACK_DONE"])


if __name__ == "__main__":
    unittest.main()
