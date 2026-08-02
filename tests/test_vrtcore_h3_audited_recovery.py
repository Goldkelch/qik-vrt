#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Static and semantic controls for the exact-one H3 recovery proxy."""
from __future__ import annotations

import inspect
import unittest

from tools import qikvrt_vrtcore_h3_audited_recovery as recovery


CURRENT_MAIN = "bad1a0558b88b9bc13a6b47fe621ac27d8bfaa62"


class AuditedH3RecoveryTests(unittest.TestCase):
    def test_exact_external_effect_bindings(self) -> None:
        self.assertEqual(
            recovery.ORIGINAL_EXECUTION_HEAD,
            "53e757ebce929b40250f90a02ed2a9ec62de6217",
        )
        self.assertEqual(
            recovery.ORIGINAL_EXECUTION_PARENT,
            "cdb0e9fe8444565df665affa64463295648b1368",
        )
        self.assertEqual(recovery.ORIGINAL_RUN_ID, 30753751400)
        self.assertEqual(recovery.ORIGINAL_ATTEMPT_1_JOB, 91512247885)
        self.assertEqual(recovery.ORIGINAL_ATTEMPT_2_JOB, 91514264546)
        self.assertEqual(
            recovery.CONSUMPTION_REF,
            "refs/tags/qikvrt-zenodo-auth/"
            "a330351c76975a00afb644e739ed1cc3504b8a63581285b62d68abca13a5d0e1",
        )
        self.assertEqual(
            recovery.CONSUMPTION_TAG_OBJECT,
            "e831a5298cb4b95011b7a53719f784d622ccc42e",
        )

    def test_no_new_lock_or_deposition_constructor_is_reachable(self) -> None:
        source = inspect.getsource(recovery)
        self.assertNotIn("_acquire_remote_consumption_lock", source)
        self.assertNotIn(".create_paper(", source)
        self.assertNotIn('"create_requested"', source)
        self.assertIn("_read_exact_existing_consumption_lock", source)
        self.assertIn("_canonical_inventory_candidates", source)
        self.assertIn("_complete_exact_record", source)

    def test_zero_inventory_is_terminal_no_effect(self) -> None:
        original = recovery.EXPECTED_MAIN
        recovery.EXPECTED_MAIN = CURRENT_MAIN
        try:
            receipt = recovery.terminal_receipt(
                reason="NO_CANONICAL_MATCH",
                remote_consumption=self.remote_consumption(),
                matches=[],
            )
        finally:
            recovery.EXPECTED_MAIN = original
        self.assertEqual(receipt["state"], "NO_ZENODO_EFFECT")
        self.assertEqual(receipt["disposition"], "MANUAL_REAUTH_REQUIRED")
        self.assertEqual(receipt["successor_parent"], CURRENT_MAIN)
        self.assertEqual(
            receipt["authenticated_zenodo_inventory"]["canonical_match_count"],
            0,
        )
        self.assertFalse(any(receipt["effects_by_this_recovery_run"].values()))
        self.assertFalse(receipt["completion_claims"]["PASS"])
        self.assertFalse(receipt["completion_claims"]["FINAL_PASS"])

    def test_multiple_inventory_matches_are_terminal_ambiguous(self) -> None:
        receipt = recovery.terminal_receipt(
            reason="NON_UNIQUE_CANONICAL_MATCH",
            remote_consumption=self.remote_consumption(),
            matches=[
                (1, "10.5281/zenodo.1", None),
                (2, "10.5281/zenodo.2", {"id": 2}),
            ],
        )
        self.assertEqual(
            receipt["state"], "AMBIGUOUS_MULTIPLE_CANONICAL_MATCHES"
        )
        self.assertEqual(receipt["disposition"], "MANUAL_REAUTH_REQUIRED")
        self.assertEqual(
            receipt["authenticated_zenodo_inventory"]["canonical_match_count"],
            2,
        )

    def test_proxy_and_target_scopes_are_minimal(self) -> None:
        self.assertEqual(len(recovery.INTEGRITY_PATHS), 3)
        self.assertEqual(
            recovery.PROXY_SCOPE - recovery.INTEGRITY_PATHS,
            {
                ".github/workflows/qikvrt_vrtcore_h3_audited_recovery.yml",
                "tools/qikvrt_vrtcore_h3_audited_recovery.py",
                "tests/test_vrtcore_h3_audited_recovery.py",
            },
        )
        self.assertNotEqual(
            recovery.PUBLICATION_EVIDENCE_RELATIVE,
            recovery.TERMINAL_EVIDENCE_RELATIVE,
        )

    @staticmethod
    def remote_consumption() -> dict[str, object]:
        return {
            "remote": "github_git_data_api",
            "api_origin": "https://api.github.com",
            "repository": recovery.REPOSITORY,
            "ref": recovery.CONSUMPTION_REF,
            "tag_object": recovery.CONSUMPTION_TAG_OBJECT,
            "object_type": "tag",
            "execution_head": recovery.ORIGINAL_EXECUTION_HEAD,
            "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
            "recovery_mode": "EXISTING_EXACT_REF_NO_CREATE",
        }


if __name__ == "__main__":
    unittest.main()
