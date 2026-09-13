#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_create_versioned_corrected_candidates as builder
from tools.qikvrt_hold_contract import validate_document


class VersionedCorrectedCandidateRecoveryTests(unittest.TestCase):
    def test_accepted_candidate_state_verifies_offline_without_zenodo_reads(self) -> None:
        with mock.patch.object(
            builder.remaining_probe,
            "get",
            side_effect=AssertionError("accepted evidence verification must stay offline"),
        ), mock.patch.object(
            builder.subject_172_probe,
            "fetch_public_record",
            side_effect=AssertionError("accepted evidence verification must stay offline"),
        ):
            result, exit_code = builder.ensure_current()

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["state"], "ACCEPTED_ALL_SIX_OFFLINE_VERIFIED")
        self.assertEqual(result["recovery"]["state"], "CURRENT_OFFLINE_CANDIDATE_EVIDENCE")
        self.assertFalse(result["recovery"]["live_reobservation_attempted"])

    def test_verify_current_is_offline_only_when_ready_evidence_drifts(self) -> None:
        with mock.patch.object(
            builder,
            "classify_candidate_state",
            return_value="READY",
        ), mock.patch.object(
            builder,
            "_safe_check",
            side_effect=builder.CorrectionError("candidate evidence drift"),
        ), mock.patch.object(
            builder,
            "materialize_atomically",
            side_effect=AssertionError("verify-current must not materialize"),
        ):
            result, exit_code = builder.verify_current_offline()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(
            result["first_blocker"],
            "VERSIONED_CANDIDATE_EVIDENCE_DRIFT_REQUIRES_EXPLICIT_REPAIR_CARRIER",
        )
        self.assertFalse(result["live_repair_invoked"])
        validate_document(result)

    def test_accepted_state_drift_holds_without_rebuilding_or_reading_zenodo(self) -> None:
        with mock.patch.object(
            builder,
            "classify_candidate_state",
            return_value="ACCEPTED",
        ), mock.patch.object(
            builder,
            "_safe_check",
            side_effect=builder.CorrectionError("accepted archive binding drift"),
        ), mock.patch.object(
            builder,
            "materialize_atomically",
            side_effect=AssertionError("accepted state must never rebuild automatically"),
        ):
            result, exit_code = builder.ensure_current()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(
            result["first_blocker"],
            "VERSIONED_CANDIDATE_EVIDENCE_DRIFT_AFTER_OWNER_BOUNDARY",
        )
        self.assertEqual(result["d0"], 3)
        self.assertFalse(result["live_repair_invoked"])
        validate_document(result)

    def test_ready_state_transport_failure_persists_a_typed_hold_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "RECOVERY_RECEIPT.json"
            with mock.patch.object(
                builder,
                "classify_candidate_state",
                return_value="READY",
            ), mock.patch.object(
                builder,
                "_safe_check",
                side_effect=builder.CorrectionError("candidate evidence absent"),
            ), mock.patch.object(
                builder,
                "materialize_atomically",
                side_effect=builder.remaining_probe.TransientObservationError(
                    "GET failed: HTTP Error 504"
                ),
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = builder.main(
                    ["--ensure-current", "--receipt", str(receipt), "--json"]
                )
            result = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "ZENODO_PUBLIC_REOBSERVATION_UNCONFIRMED")
        self.assertEqual(
            result["external_reobservation_policy"]["source"],
            "qikvrt_batch003_remaining_archive_probe",
        )
        self.assertTrue(result["live_repair_invoked"])
        validate_document(result)

    def test_direct_materialize_respects_an_accepted_owner_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "RECOVERY_RECEIPT.json"
            with mock.patch.object(
                builder,
                "classify_candidate_state",
                return_value="ACCEPTED",
            ), mock.patch.object(
                builder,
                "materialize_atomically",
                side_effect=AssertionError("accepted evidence must not be rebuilt"),
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = builder.main(
                    ["--materialize", "--receipt", str(receipt), "--json"]
                )
            result = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["d0"], 3)
        self.assertFalse(result["live_repair_invoked"])
        validate_document(result)

    def test_malformed_owner_artifact_is_a_d3_hold_without_a_live_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            output = root / "versioned-corrected-candidates"
            work = root / "CREATE.json"
            owner = root / "OWNER.json"
            acceptance = output / "OWNER_ACCEPTANCE_RECEIPT.json"
            promotion = root / "PROMOTION.json"
            work.write_text(json.dumps({"state": "READY"}), encoding="utf-8")
            owner.write_text("{not-json", encoding="utf-8")
            with (
                mock.patch.object(builder, "OUTPUT", output),
                mock.patch.object(builder, "WORK_UNIT", work),
                mock.patch.object(builder, "OWNER_WORK_UNIT", owner),
                mock.patch.object(builder, "ACCEPTANCE_RECEIPT", acceptance),
                mock.patch.object(builder, "PROMOTION_WORK_UNIT", promotion),
                mock.patch.object(
                    builder,
                    "materialize_atomically",
                    side_effect=AssertionError("owner-bound evidence must not rebuild"),
                ),
            ):
                result, exit_code = builder.ensure_current()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["d0"], 3)
        self.assertFalse(result["live_repair_invoked"])
        validate_document(result)

    def test_atomic_repair_restores_the_complete_candidate_tree_and_work_units(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            output = root / "versioned-corrected-candidates"
            work_unit = root / "CREATE.json"
            owner_work_unit = root / "OWNER.json"
            acceptance = output / "OWNER_ACCEPTANCE_RECEIPT.json"
            acceptance.parent.mkdir(parents=True)
            acceptance.write_bytes(b"accepted-owner-evidence")
            work_unit.write_bytes(b"prior-work-unit")
            owner_work_unit.write_bytes(b"prior-owner-work-unit")

            def write_partial_then_fail() -> None:
                (output / "partial" / "candidate.zip").parent.mkdir(parents=True)
                (output / "partial" / "candidate.zip").write_bytes(b"partial-candidate")
                acceptance.write_bytes(b"overwritten-owner-evidence")
                work_unit.write_bytes(b"overwritten-work-unit")
                owner_work_unit.write_bytes(b"overwritten-owner-work-unit")
                raise builder.remaining_probe.TransientObservationError("GET failed: HTTP Error 504")

            with (
                mock.patch.object(builder, "OUTPUT", output),
                mock.patch.object(builder, "WORK_UNIT", work_unit),
                mock.patch.object(builder, "OWNER_WORK_UNIT", owner_work_unit),
                mock.patch.object(builder, "classify_candidate_state", return_value="READY"),
                mock.patch.object(builder, "materialize", side_effect=write_partial_then_fail),
            ):
                with self.assertRaisesRegex(
                    builder.remaining_probe.TransientObservationError,
                    r"HTTP Error 504",
                ):
                    builder.materialize_atomically()

            self.assertEqual(acceptance.read_bytes(), b"accepted-owner-evidence")
            self.assertFalse((output / "partial" / "candidate.zip").exists())
            self.assertEqual(work_unit.read_bytes(), b"prior-work-unit")
            self.assertEqual(owner_work_unit.read_bytes(), b"prior-owner-work-unit")

    def test_workflow_is_read_only_and_artifacts_before_hold_enforcement(self) -> None:
        workflow = (
            pathlib.Path(__file__).resolve().parents[1]
            / ".github/workflows/qikvrt_versioned_corrected_candidates.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("--verify-current --receipt", workflow)
        self.assertIn('statuses=("${PIPESTATUS[@]}")', workflow)
        self.assertIn("Preserve versioned candidate recovery evidence", workflow)
        self.assertIn("Enforce typed candidate HOLD after evidence upload", workflow)
        self.assertIn("steps.candidate_evidence.outcome == 'success'", workflow)
        self.assertIn("steps.candidates.outputs.exit_code != ''", workflow)
        self.assertLess(
            workflow.index("Preserve versioned candidate recovery evidence"),
            workflow.index("Enforce typed candidate HOLD after evidence upload"),
        )
        self.assertNotIn("git push", workflow)
        self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
