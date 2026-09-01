#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed contract tests for retired status-report release carriers."""

from __future__ import annotations

import hashlib
import json
import pathlib
import unittest

from tests.release_authority_hold_contract import assert_authority_hold_workflow


ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKER = ROOT / "release/status-clarification-request.json"
SCHEMA = ROOT / "policy/qikvrt-status-report-release-request.schema.json"
ZERO40 = "0" * 40
ZERO64 = "0" * 64


class StatusReleaseWorkflowTests(unittest.TestCase):
    def test_initial_marker_is_canonically_inert(self) -> None:
        marker = json.loads(MARKER.read_text(encoding="utf-8"))
        schema_raw = SCHEMA.read_bytes()
        json.loads(schema_raw)
        self.assertEqual(marker["action"], "inactive")
        self.assertEqual(marker["confirm"], "NOT_AUTHORIZED")
        self.assertEqual(marker["release"]["expected_source_tree"], ZERO40)
        self.assertEqual(
            marker["release"]["expected_source_commits"],
            {"Goldkelch/qik-vrt": ZERO40, "ingolf-lohmann/qik-vrt": ZERO40},
        )
        for key in (
            "client_sha256",
            "reservation_manifest_sha256",
            "final_template_manifest_sha256",
            "final_manifest_sha256",
            "reservation_evidence_sha256",
        ):
            self.assertEqual(marker["zenodo"][key], ZERO64)
        projection = dict(marker)
        supplied = projection.pop("authorization_payload_sha256")
        canonical = json.dumps(
            projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(supplied, hashlib.sha256(canonical).hexdigest())
        self.assertEqual(marker["schema_sha256"], hashlib.sha256(schema_raw).hexdigest())

    def test_reserve_and_finalize_are_trusted_main_authority_holds(self) -> None:
        for workflow in (
            "qikvrt_status_report_reserve.yml",
            "qikvrt_status_report_finalize.yml",
        ):
            with self.subTest(workflow=workflow):
                assert_authority_hold_workflow(self, workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
