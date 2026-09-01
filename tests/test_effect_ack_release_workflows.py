#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed contract tests for the retired EFFECT_ACK carriers."""

from __future__ import annotations

import hashlib
import json
import pathlib
import unittest

from tests.release_authority_hold_contract import assert_authority_hold_workflow


ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKER = ROOT / "release/effect-ack-universality-request.json"
SCHEMA = ROOT / "policy/qikvrt-effect-ack-release-request.schema.json"


class EffectAckReleaseWorkflowTests(unittest.TestCase):
    def test_inert_marker_binds_schema_and_canonical_payload(self) -> None:
        marker = json.loads(MARKER.read_text(encoding="utf-8"))
        json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(marker["state"], "inactive")
        self.assertEqual(marker["confirm"], "NOT_AUTHORIZED")
        self.assertEqual(marker["release"]["expected_source_commit"], "0" * 40)
        self.assertEqual(marker["release"]["expected_source_tree"], "0" * 40)
        self.assertEqual(
            marker["schema_sha256"], hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
        )
        supplied = marker.pop("authorization_payload_sha256")
        canonical = json.dumps(
            marker, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(supplied, hashlib.sha256(canonical).hexdigest())

    def test_reserve_and_finalize_are_trusted_main_authority_holds(self) -> None:
        for workflow in (
            "qikvrt_zenodo_reserve.yml",
            "qikvrt_effect_ack_finalize.yml",
        ):
            with self.subTest(workflow=workflow):
                assert_authority_hold_workflow(self, workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
