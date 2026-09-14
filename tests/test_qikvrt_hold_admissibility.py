#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest

from tools import qikvrt_hold_admissibility as admissibility


class HoldAdmissibilityTests(unittest.TestCase):
    def test_hold_is_admissible_only_without_any_carrier(self):
        result = admissibility.classify(first_blocker="NO_ACTIVE_CARRIER")
        self.assertEqual(result["state"], "HOLD")
        self.assertTrue(result["hold_admissible"])
        self.assertEqual(result["carrier_count"], 0)
        self.assertIsNone(result["next_action"])

    def test_open_issue_forces_nonterminal_continuation(self):
        result = admissibility.classify(
            issue_carriers=["#963"],
            continuation_state="ACTION",
            next_action="PROCESS_OPEN_ISSUE",
        )
        self.assertEqual(result["state"], "ACTION")
        self.assertFalse(result["hold_admissible"])
        self.assertEqual(result["carriers"]["open_issues"], ["#963"])

    def test_open_pull_request_forces_request_authority(self):
        result = admissibility.classify(
            pull_request_carriers=["#984@2284b9ea"],
            continuation_state="REQUEST_AUTHORITY",
            first_blocker="RULESET_ADMIN_AUTHORITY_REQUIRED",
            next_action="ROUTE_AUTHORITY_THROUGH_ACTIVE_PR",
        )
        self.assertEqual(result["state"], "REQUEST_AUTHORITY")
        self.assertFalse(result["hold_admissible"])
        self.assertEqual(result["carrier_count"], 1)

    def test_work_branch_forces_successor(self):
        result = admissibility.classify(
            branch_carriers=["repair/ruleset@2284b9ea"],
            continuation_state="SUCCESSOR",
        )
        self.assertEqual(result["state"], "SUCCESSOR")
        self.assertFalse(result["hold_admissible"])

    def test_mixed_carriers_are_canonical_and_counted(self):
        result = admissibility.classify(
            issue_carriers=["#12", "#2"],
            pull_request_carriers=["#4"],
            branch_carriers=["work/b", "work/a"],
        )
        self.assertEqual(result["state"], "CONTINUE")
        self.assertEqual(result["carrier_count"], 5)
        self.assertEqual(result["carriers"]["open_issues"], ["#12", "#2"])
        self.assertEqual(result["carriers"]["work_branches"], ["work/a", "work/b"])

    def test_duplicate_carrier_is_rejected(self):
        with self.assertRaises(admissibility.CarrierBindingError):
            admissibility.classify(pull_request_carriers=["#4", "#4"])

    def test_invalid_continuation_state_is_rejected(self):
        with self.assertRaises(admissibility.CarrierBindingError):
            admissibility.classify(
                pull_request_carriers=["#4"],
                continuation_state="HOLD",
            )


if __name__ == "__main__":
    unittest.main()
