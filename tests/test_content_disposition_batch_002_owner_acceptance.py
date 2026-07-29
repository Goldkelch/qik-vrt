#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "tools/qikvrt_content_disposition_batch_002_owner_acceptance.py"
S = importlib.util.spec_from_file_location("b2oa", P)
m = importlib.util.module_from_spec(S)
assert S.loader is not None
S.loader.exec_module(m)


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = load(m.ACCEPTANCE)
        cls.owner_return = load(m.RETURN_RECEIPT)
        cls.disposition = load(m.DISPOSITION)
        cls.publication = load(m.PUBLICATION_CORRECTION)
        cls.work = load(m.WORK_UNIT)

    def test_positive(self):
        result = m.verify()
        self.assertEqual(
            result["state"],
            "OWNER_ACCEPTANCE_VERIFIED_FOR_BATCH_002",
        )
        self.assertEqual(result["decision"], "ACCEPT")
        self.assertEqual(result["accepted_candidate_head"], m.ACCEPTED_HEAD)
        self.assertTrue(result["owner_acceptance_recorded"])
        self.assertFalse(result["zenodo_mutation_authorized"])
        for key in ("pass", "final_pass", "effect_ack_done"):
            self.assertIs(result[key], False)

    def test_exact_comment_and_head_binding(self):
        evidence = self.acceptance["decision_evidence"]
        self.assertEqual(evidence["id"], 5122279522)
        self.assertEqual(evidence["created_at"], "2026-07-29T19:00:40Z")
        self.assertEqual(
            evidence["body_binding"]["accepted_candidate_head"],
            m.ACCEPTED_HEAD,
        )
        self.assertEqual(
            self.acceptance["candidate_binding"]["accepted_head"],
            m.ACCEPTED_HEAD,
        )

    def test_pre_acceptance_events_remain_immutable(self):
        m.validate_pending_source_history(
            self.owner_return,
            self.disposition,
            self.publication,
        )
        self.assertEqual(
            self.owner_return["owner_decision"]["state"],
            "PENDING",
        )
        self.assertEqual(self.acceptance["state"], "ACCEPTED")

    def test_accepted_artifacts_equal_returned_artifacts(self):
        self.assertEqual(
            self.acceptance["accepted_artifacts"],
            self.owner_return["artifacts"],
        )

    def test_wrong_head_blocks(self):
        bad = copy.deepcopy(self.acceptance)
        bad["candidate_binding"]["accepted_head"] = "0" * 40
        with self.assertRaises(m.E):
            m.validate_acceptance(
                bad,
                self.owner_return,
                self.disposition,
                self.publication,
            )

    def test_wrong_comment_blocks(self):
        bad = copy.deepcopy(self.acceptance)
        bad["decision_evidence"]["id"] = 0
        with self.assertRaises(m.E):
            m.validate_acceptance(
                bad,
                self.owner_return,
                self.disposition,
                self.publication,
            )

    def test_zenodo_authorization_inflation_blocks(self):
        bad = copy.deepcopy(self.acceptance)
        bad["completion_claims"]["zenodo_mutation_authorized"] = True
        with self.assertRaises(m.E):
            m.validate_acceptance(
                bad,
                self.owner_return,
                self.disposition,
                self.publication,
            )

    def test_false_final_pass_blocks(self):
        bad = copy.deepcopy(self.work)
        bad["completion_claims"]["final_pass"] = True
        with self.assertRaises(m.E):
            m.validate_work_unit(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
