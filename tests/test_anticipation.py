#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tools import qikvrt_anticipation as anticipation
from tools.qikvrt_seed_common import write_json


class GlobalSystemClosureContractTests(unittest.TestCase):
    def test_repository_contract_is_bounded_and_valid(self) -> None:
        receipt = anticipation.check()
        self.assertEqual(receipt["state"], "CONTINUE")
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertEqual(
            receipt["completion_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )

    def test_monotonic_improvement_is_measured_and_non_regressing(self) -> None:
        self.assertEqual(
            anticipation.classify_monotonic_transition(
                {"tests": 6, "receipts": 1}, {"tests": 7, "receipts": 1}
            ),
            "NON_REGRESSING_GATE_IMPROVEMENT",
        )
        self.assertEqual(
            anticipation.classify_monotonic_transition(
                {"tests": 6, "receipts": 1}, {"tests": 6, "receipts": 1}
            ),
            "BYTE_STABLE_NO_OP",
        )
        self.assertEqual(
            anticipation.classify_monotonic_transition(
                {"tests": 6, "receipts": 1}, {"tests": 7, "receipts": 0}
            ),
            "REJECTED_REGRESSION",
        )

    def test_metric_shape_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(anticipation.ClosureError, "metric sets"):
            anticipation.classify_monotonic_transition(
                {"tests": 6}, {"tests": 6, "receipts": 1}
            )

    def test_checkpoint_hash_binds_predecessor(self) -> None:
        checkpoint = {"checkpoint_id": "gsc-0001", "state": "CONTRACT_BOUND"}
        first = anticipation.checkpoint_hash(
            checkpoint, previous_checkpoint_sha256=anticipation.ZERO_SHA256
        )
        second = anticipation.checkpoint_hash(
            checkpoint, previous_checkpoint_sha256="1" * 64
        )
        self.assertNotEqual(first, second)
        self.assertEqual(
            first,
            anticipation.checkpoint_hash(
                checkpoint, previous_checkpoint_sha256=anticipation.ZERO_SHA256
            ),
        )

    def test_false_completion_claim_in_policy_is_blocked(self) -> None:
        policy, evidence = anticipation.load_contract()
        policy = copy.deepcopy(policy)
        policy["completion_claims"]["PASS"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / anticipation.POLICY_PATH, policy)
            write_json(root / anticipation.EVIDENCE_PATH, evidence)
            with self.assertRaisesRegex(anticipation.ClosureError, "false completion"):
                anticipation.check(root)

    def test_functionality_evidence_cannot_claim_merge(self) -> None:
        policy, evidence = anticipation.load_contract()
        evidence = copy.deepcopy(evidence)
        evidence["authority_evidence"]["merged"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / anticipation.POLICY_PATH, policy)
            write_json(root / anticipation.EVIDENCE_PATH, evidence)
            with self.assertRaisesRegex(anticipation.ClosureError, "PR boundary"):
                anticipation.check(root)


if __name__ == "__main__":
    unittest.main()
