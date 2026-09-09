#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools import qikvrt_effect_attempts as attempts


class EffectAttemptsTests(unittest.TestCase):
    def test_appending_an_uncertain_post_preserves_prior_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = pathlib.Path(directory) / "effect-attempts.json"
            attempts.write_attempts(
                ledger,
                [
                    {
                        "kind": "ruleset_put",
                        "endpoint_or_subject": "repos/Goldkelch/qik-vrt/rulesets/19344903",
                        "mutation": "PUT",
                        "effect_transport_attempted": True,
                        "transport_outcome": "ACKED",
                        "effect_observed": True,
                        "evidence_ref": "ruleset-reconcile-receipt:PUT",
                    }
                ],
            )

            value = attempts.append_attempt(
                ledger,
                {
                    "kind": "issue_comment_post",
                    "endpoint_or_subject": "repos/Goldkelch/qik-vrt/issues/1/comments",
                    "mutation": "POST_UNCONFIRMED_RATE_LIMIT",
                    "effect_transport_attempted": True,
                    "transport_outcome": "UNCONFIRMED_RATE_LIMIT",
                    "effect_observed": False,
                    "evidence_ref": "post-stderr:installation-rate-limit",
                },
            )

            self.assertEqual([entry["mutation"] for entry in value], ["PUT", "POST_UNCONFIRMED_RATE_LIMIT"])
            summary = attempts.summary(value)
            self.assertTrue(summary["effect_transport_attempted"])
            self.assertTrue(summary["effect_observed"])
            self.assertEqual(summary["mutation"], "POST_UNCONFIRMED_RATE_LIMIT")

    def test_readback_evidence_is_not_misrepresented_as_a_transport_attempt(self):
        entry = attempts._attempt(
            {
                "kind": "issue_comment_readback",
                "endpoint_or_subject": "repos/Goldkelch/qik-vrt/issues/comments/99",
                "mutation": "NONE",
                "effect_transport_attempted": False,
                "transport_outcome": "OBSERVED_READBACK",
                "effect_observed": True,
                "evidence_ref": "readback:comment:99",
            }
        )
        self.assertFalse(entry["effect_transport_attempted"])
        self.assertTrue(entry["effect_observed"])

    def test_invalid_nontransport_entry_is_rejected(self):
        with self.assertRaisesRegex(attempts.EffectAttemptError, "non-transport"):
            attempts._attempt(
                {
                    "kind": "bad",
                    "endpoint_or_subject": "repos/Goldkelch/qik-vrt",
                    "mutation": "NONE",
                    "effect_transport_attempted": False,
                    "transport_outcome": "ACKED",
                    "effect_observed": False,
                    "evidence_ref": "bad",
                }
            )

    def test_missing_ledger_summarizes_to_no_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            value = attempts.summary(attempts.read_attempts(pathlib.Path(directory) / "missing.json"))
        self.assertFalse(value["effect_transport_attempted"])
        self.assertFalse(value["effect_observed"])
        self.assertEqual(value["mutation"], "NONE")

    def test_create_refuses_to_replace_existing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = pathlib.Path(directory) / "effect-attempts.json"
            attempts.create_empty_ledger(ledger)
            with self.assertRaisesRegex(attempts.EffectAttemptError, "may not replace history"):
                attempts.create_empty_ledger(ledger)

    def test_status_dedupe_requires_the_latest_context_state(self):
        snapshot = [
            [
                {"id": 10, "sha": "a" * 40, "context": "effect", "state": "success"},
                {"id": 11, "sha": "a" * 40, "context": "other", "state": "success"},
            ],
            [
                {"id": 12, "sha": "a" * 40, "context": "effect", "state": "pending"},
            ],
        ]
        self.assertIsNone(
            attempts.select_latest_status_id(
                snapshot,
                sha="a" * 40,
                context="effect",
                state="success",
            )
        )
        self.assertEqual(
            attempts.select_latest_status_id(
                snapshot,
                sha="a" * 40,
                context="effect",
                state="pending",
            ),
            12,
        )

    def test_status_dedupe_rejects_malformed_paginated_entries(self):
        with self.assertRaisesRegex(attempts.EffectAttemptError, "array of pages"):
            attempts.select_latest_status_id(
                {"statuses": []},
                sha="a" * 40,
                context="effect",
                state="success",
            )

    def test_status_dedupe_rejects_boolean_ids(self):
        with self.assertRaisesRegex(attempts.EffectAttemptError, "positive integer"):
            attempts.select_latest_status_id(
                [[{"id": True, "sha": "a" * 40, "context": "effect", "state": "success"}]],
                sha="a" * 40,
                context="effect",
                state="success",
            )

    def test_append_write_is_atomic_when_the_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = pathlib.Path(directory) / "effect-attempts.json"
            attempts.write_attempts(
                ledger,
                [
                    {
                        "kind": "ruleset_put",
                        "endpoint_or_subject": "repos/Goldkelch/qik-vrt/rulesets/19344903",
                        "mutation": "PUT",
                        "effect_transport_attempted": True,
                        "transport_outcome": "ACKED",
                        "effect_observed": True,
                        "evidence_ref": "ruleset-reconcile-receipt:PUT",
                    }
                ],
            )
            original = ledger.read_bytes()
            original_replace = attempts.os.replace
            try:
                def failed_replace(*_args):
                    raise OSError("simulated atomic replace failure")

                attempts.os.replace = failed_replace
                with self.assertRaisesRegex(OSError, "replace failure"):
                    attempts.append_attempt(
                        ledger,
                        {
                            "kind": "issue_comment_post",
                            "endpoint_or_subject": "repos/Goldkelch/qik-vrt/issues/1/comments",
                            "mutation": "POST",
                            "effect_transport_attempted": True,
                            "transport_outcome": "ACKED",
                            "effect_observed": False,
                            "evidence_ref": "post-response:comment:1",
                        },
                    )
            finally:
                attempts.os.replace = original_replace
            self.assertEqual(ledger.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
