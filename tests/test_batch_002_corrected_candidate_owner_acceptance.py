#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Regression checks for exact owner acceptance of the Batch-002 candidate."""
from __future__ import annotations

import hashlib
import json
import pathlib
import unittest
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = pathlib.PurePosixPath(
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-002/corrected-candidate-owner-return"
)
ACCEPTANCE_PATH = str(BASE / "OWNER_ACCEPTANCE_RECEIPT.json")
CANDIDATE_PATH = str(BASE / "PUBLICATION_CORRECTED_CANDIDATE.json")
PUBLICATION_ID = "ontology-des-unterschieds-reverse-engineering-v2-candidate"
ACCEPTED_HEAD = "04f95b32b0bb42bd1ca95f63391dff5893b81b6e"
NEXT_EFFECT = "BUILD_MACHINE_PROOF_BUNDLE_FOR_ACCEPTED_BATCH_002_CORRECTED_CANDIDATE"


def load_json(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / pathlib.PurePosixPath(relative)).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object in {relative}")
    return value


def identity(relative: str) -> dict[str, Any]:
    data = (ROOT / pathlib.PurePosixPath(relative)).read_bytes()
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": hashlib.sha1(  # noqa: S324 - canonical Git identity
            f"blob {len(data)}\0".encode("ascii") + data
        ).hexdigest(),
    }


class Batch002CorrectedCandidateOwnerAcceptanceTests(unittest.TestCase):
    def test_acceptance_is_owner_specific_and_exact(self) -> None:
        receipt = load_json(ACCEPTANCE_PATH)
        self.assertEqual(
            receipt["schema"],
            "qikvrt_batch_002_corrected_candidate_owner_acceptance_v1",
        )
        self.assertEqual(receipt["decision"], "ACCEPTED")
        acceptance = receipt["acceptance"]
        self.assertIs(acceptance["accepted"], True)
        self.assertEqual(acceptance["owner_name"], "Ingolf Lohmann")
        self.assertEqual(acceptance["owner_type"], "NATURAL_PERSON")
        self.assertEqual(
            acceptance["decision_command"],
            "OWNER_ACCEPT_OR_REJECT_BATCH_002_CORRECTED_CANDIDATE",
        )
        self.assertEqual(acceptance["decision_statement"], "Accepted!")
        self.assertTrue(acceptance["accepted_at"].endswith("Z"))

    def test_receipt_binds_the_previously_verified_candidate_bytes(self) -> None:
        receipt = load_json(ACCEPTANCE_PATH)
        accepted = receipt["accepted_candidate"]
        self.assertEqual(accepted["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(accepted["pull_request"], 207)
        self.assertEqual(accepted["publication_id"], PUBLICATION_ID)
        self.assertEqual(accepted["path"], CANDIDATE_PATH)
        self.assertEqual(accepted["pre_acceptance_verified_exact_head"], ACCEPTED_HEAD)
        observed = identity(CANDIDATE_PATH)
        for key in ("bytes", "sha256", "git_blob_sha1"):
            self.assertEqual(accepted[key], observed[key])

    def test_accepted_candidate_itself_remains_byte_stable(self) -> None:
        candidate = load_json(CANDIDATE_PATH)
        self.assertEqual(candidate["publication_id"], PUBLICATION_ID)
        self.assertEqual(candidate["candidate_version"], "2.0-candidate.1")
        self.assertTrue(candidate["completion_claims"]["candidate_returned_to_owner"])
        self.assertFalse(candidate["authorization"]["owner_acceptance_recorded"])
        self.assertEqual(
            candidate["next_deterministic_effect"],
            "OWNER_ACCEPT_OR_REJECT_BATCH_002_CORRECTED_CANDIDATE",
        )
        precedence = load_json(ACCEPTANCE_PATH)["status_precedence"]
        self.assertTrue(precedence["accepted_candidate_bytes_immutable"])
        self.assertEqual(
            precedence["receipt_supersedes_candidate_predecision_next_effect"],
            candidate["next_deterministic_effect"],
        )

    def test_acceptance_does_not_authorize_any_external_effect(self) -> None:
        receipt = load_json(ACCEPTANCE_PATH)
        boundary = receipt["authorization_boundary"]
        self.assertTrue(boundary["owner_acceptance_recorded"])
        for field in (
            "proof_bundle_complete",
            "exact_upload_authorization",
            "production_upload_authorized",
            "zenodo_mutation_performed",
            "zenodo_corpus_complete",
            "pass",
            "final_pass",
            "effect_ack_done",
        ):
            self.assertIs(boundary[field], False, field)
        self.assertTrue(
            receipt["status_precedence"]["receipt_does_not_modify_or_authorize_upload"]
        )
        self.assertEqual(receipt["next_deterministic_effect"], NEXT_EFFECT)

    def test_historical_record_is_not_mutated(self) -> None:
        receipt = load_json(ACCEPTANCE_PATH)
        historical = receipt["historical_record"]
        self.assertEqual(historical["record_id"], 21582781)
        self.assertEqual(historical["doi"], "10.5281/zenodo.21582781")
        self.assertFalse(historical["historical_bytes_mutated"])


if __name__ == "__main__":
    unittest.main()
