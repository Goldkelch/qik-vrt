#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import contextlib
import copy
import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

from tools import qikvrt_batch003_remaining_archive_probe as probe
from tools import qikvrt_batch003_subject_172dd_public_probe as subject_172_probe
from tools import qikvrt_content_disposition_batch_003_remaining_archives as disposition
from tools.qikvrt_hold_contract import validate_document


class Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_unused: object) -> bool:
        return False

    def geturl(self) -> str:
        return "https://zenodo.org/api/records/21244412"

    def read(self, size: int) -> bytes:
        part, self.payload = self.payload[:size], self.payload[size:]
        return part


def gateway_timeout() -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://zenodo.org/api/records/21244412",
        504,
        "Gateway Time-out",
        {},
        None,
    )


class RemainingArchiveRecoveryTests(unittest.TestCase):
    def test_public_get_retries_bounded_504_then_recovers(self) -> None:
        with mock.patch.object(
            probe.urllib.request,
            "urlopen",
            side_effect=[gateway_timeout(), gateway_timeout(), Response(b"exact")],
        ) as opener, mock.patch.object(probe.time, "sleep") as sleep:
            result = probe.get(
                "https://zenodo.org/api/records/21244412",
                "application/json",
                1024,
            )

        self.assertEqual(result, b"exact")
        self.assertEqual(opener.call_count, probe.GET_ATTEMPTS)
        self.assertEqual(
            sleep.call_args_list,
            [mock.call(seconds) for seconds in probe.GET_BACKOFF_SECONDS],
        )
        self.assertEqual(
            [call.kwargs["timeout"] for call in opener.call_args_list],
            [probe.GET_TIMEOUT_SECONDS] * probe.GET_ATTEMPTS,
        )

    def test_public_get_ends_after_bounded_504_retries(self) -> None:
        with mock.patch.object(
            probe.urllib.request,
            "urlopen",
            side_effect=[gateway_timeout() for _ in range(probe.GET_ATTEMPTS)],
        ) as opener, mock.patch.object(probe.time, "sleep") as sleep:
            with self.assertRaisesRegex(probe.E, r"HTTP Error 504"):
                probe.get(
                    "https://zenodo.org/api/records/21244412",
                    "application/json",
                    1024,
                )

        self.assertEqual(opener.call_count, probe.GET_ATTEMPTS)
        self.assertEqual(
            sleep.call_args_list,
            [mock.call(seconds) for seconds in probe.GET_BACKOFF_SECONDS],
        )
        self.assertEqual(
            [call.kwargs["timeout"] for call in opener.call_args_list],
            [probe.GET_TIMEOUT_SECONDS] * probe.GET_ATTEMPTS,
        )

    def test_terminal_http_errors_are_blocks_without_retries(self) -> None:
        missing = urllib.error.HTTPError(
            "https://zenodo.org/api/records/21244412",
            404,
            "Not Found",
            {},
            None,
        )
        with mock.patch.object(
            probe.urllib.request,
            "urlopen",
            side_effect=missing,
        ) as opener, mock.patch.object(probe.time, "sleep") as sleep:
            with self.assertRaisesRegex(probe.E, r"HTTP Error 404"):
                probe.get(
                    "https://zenodo.org/api/records/21244412",
                    "application/json",
                    1024,
                )
        self.assertEqual(opener.call_count, 1)
        sleep.assert_not_called()

        with mock.patch.object(subject_172_probe.time, "sleep") as subject_sleep:
            with self.assertRaisesRegex(subject_172_probe.ProbeError, r"HTTP Error 404"):
                subject_172_probe.request_bytes(
                    "https://zenodo.org/api/records/21244412",
                    accept="application/json",
                    max_bytes=1024,
                    opener=mock.Mock(side_effect=missing),
                )
        subject_sleep.assert_not_called()

    def test_direct_probe_persists_a_typed_hold_receipt_before_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "REMAINING_ARCHIVE_PROBE.json"
            receipt = pathlib.Path(directory) / "RECOVERY_RECEIPT.json"
            with mock.patch.object(
                probe,
                "record",
                side_effect=probe.TransientObservationError("GET failed: HTTP Error 504"),
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = probe.main(
                    ["--output", str(output), "--receipt", str(receipt)]
                )
            result = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "ZENODO_PUBLIC_REOBSERVATION_UNCONFIRMED")
        validate_document(result)

    def test_ensure_current_uses_offline_verification_before_live_repair(self) -> None:
        verified = {
            "schema": "qikvrt_remaining_archive_disposition_verification_v1",
            "state": "CURRENT",
            "completion_claims": {"pass": False},
        }
        with mock.patch.object(
            disposition,
            "verify_materialized",
            return_value=copy.deepcopy(verified),
        ) as verify, mock.patch.object(
            disposition,
            "materialize_atomically",
        ) as materialize, mock.patch.object(
            probe,
            "get",
            side_effect=AssertionError("offline-current verification must not fetch Zenodo"),
        ):
            result, exit_code = disposition.ensure_current()

        self.assertEqual(exit_code, 0)
        self.assertEqual(verify.call_count, 1)
        materialize.assert_not_called()
        self.assertEqual(result["recovery"]["state"], "CURRENT_OFFLINE_MATERIALIZATION")
        self.assertTrue(result["recovery"]["offline_materialization_verified"])
        self.assertFalse(result["recovery"]["live_reobservation_attempted"])

    def test_ensure_current_turns_a_504_into_a_typed_persistent_hold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "RECOVERY_RECEIPT.json"
            with mock.patch.object(
                disposition,
                "verify_materialized",
                side_effect=disposition.DispositionError("materialized output drift"),
            ) as verify, mock.patch.object(
                disposition,
                "materialize_atomically",
                side_effect=probe.TransientObservationError(
                    "GET failed https://zenodo.org/api/records/21244412: HTTP Error 504"
                ),
            ) as materialize, mock.patch.object(
                disposition,
                "versioned_candidate_owner_boundary",
                return_value=None,
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = disposition.main(
                    ["--ensure-current", "--receipt", str(receipt), "--json"]
                )
            result = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 2)
        self.assertEqual(verify.call_count, 1)
        materialize.assert_called_once_with()
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["failure_class"], "ZENODO_PUBLIC_REOBSERVATION_UNCONFIRMED")
        self.assertEqual(result["d0"], 2)
        self.assertTrue(result["live_materialization_invoked"])
        self.assertEqual(result["public_get_retry_policy"]["attempts"], probe.GET_ATTEMPTS)
        self.assertTrue(result["continuation_required"])
        self.assertTrue(all(value is False for value in result["completion_claims"].values()))
        self.assertEqual(
            validate_document(result)[0]["hold_reason"]["reason_code"],
            "ZENODO_PUBLIC_REOBSERVATION_UNCONFIRMED",
        )

    def test_owner_bound_candidate_drift_never_rebuilds_live_content_evidence(self) -> None:
        with mock.patch.object(
            disposition,
            "verify_materialized",
            side_effect=disposition.DispositionError("materialized output drift"),
        ), mock.patch.object(
            disposition,
            "versioned_candidate_owner_boundary",
            return_value="ACCEPTED",
        ), mock.patch.object(
            disposition,
            "materialize_atomically",
            side_effect=AssertionError("owner-bound evidence must not be rematerialized"),
        ):
            result, exit_code = disposition.ensure_current()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["d0"], 3)
        self.assertEqual(
            result["first_blocker"],
            "ACCEPTED_VERSIONED_CANDIDATE_EVIDENCE_DRIFT_REQUIRES_OWNER_AUTHORIZATION",
        )
        self.assertFalse(result["live_materialization_invoked"])
        validate_document(result)

    def test_returned_candidate_boundary_without_acceptance_is_owner_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            owner = root / "OWNER_DECISION.json"
            acceptance = root / "OWNER_ACCEPTANCE_RECEIPT.json"
            owner.write_text(
                json.dumps({"state": "WAITING_OWNER_DECISION"}),
                encoding="utf-8",
            )
            with mock.patch.object(
                disposition,
                "VERSIONED_CANDIDATES",
                root / "versioned-corrected-candidates",
            ), mock.patch.object(
                disposition,
                "VERSIONED_OWNER_RETURN_PACKAGE",
                root / "OWNER_RETURN_PACKAGE.json",
            ), mock.patch.object(
                disposition,
                "VERSIONED_CREATE_WORK_UNIT",
                root / "CREATE.json",
            ), mock.patch.object(
                disposition,
                "VERSIONED_OWNER_WORK_UNIT",
                owner,
            ), mock.patch.object(
                disposition,
                "VERSIONED_PROMOTION_WORK_UNIT",
                root / "PROMOTION.json",
            ), mock.patch.object(
                disposition,
                "VERSIONED_ACCEPTANCE_RECEIPT",
                acceptance,
            ):
                self.assertEqual(
                    disposition.versioned_candidate_owner_boundary(),
                    "RETURNED",
                )

    def test_malformed_accepted_boundary_still_requires_owner_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            acceptance = root / "OWNER_ACCEPTANCE_RECEIPT.json"
            acceptance.write_text("{not-json", encoding="utf-8")
            with mock.patch.object(
                disposition,
                "VERSIONED_OWNER_WORK_UNIT",
                root / "OWNER_DECISION.json",
            ), mock.patch.object(
                disposition,
                "VERSIONED_ACCEPTANCE_RECEIPT",
                acceptance,
            ), mock.patch.object(
                disposition,
                "verify_materialized",
                side_effect=disposition.DispositionError("materialized evidence drift"),
            ), mock.patch.object(
                disposition,
                "materialize_atomically",
                side_effect=AssertionError("owner-bound evidence must not rebuild"),
            ):
                result, exit_code = disposition.ensure_current()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["d0"], 3)
        self.assertFalse(result["live_materialization_invoked"])
        validate_document(result)

    def test_surviving_owner_return_package_blocks_live_disposition_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            candidates = root / "versioned-corrected-candidates"
            package = candidates / "OWNER_RETURN_PACKAGE.json"
            package.parent.mkdir(parents=True)
            package.write_text("{}", encoding="utf-8")
            with (
                mock.patch.object(disposition, "VERSIONED_CANDIDATES", candidates),
                mock.patch.object(disposition, "VERSIONED_OWNER_RETURN_PACKAGE", package),
                mock.patch.object(disposition, "VERSIONED_CREATE_WORK_UNIT", root / "CREATE.json"),
                mock.patch.object(disposition, "VERSIONED_OWNER_WORK_UNIT", root / "OWNER.json"),
                mock.patch.object(disposition, "VERSIONED_PROMOTION_WORK_UNIT", root / "PROMOTION.json"),
                mock.patch.object(disposition, "VERSIONED_ACCEPTANCE_RECEIPT", candidates / "OWNER_ACCEPTANCE_RECEIPT.json"),
                mock.patch.object(
                    disposition,
                    "verify_materialized",
                    side_effect=disposition.DispositionError("materialized evidence drift"),
                ),
                mock.patch.object(
                    disposition,
                    "materialize_atomically",
                    side_effect=AssertionError("owner-return evidence must not be rebuilt"),
                ),
            ):
                result, exit_code = disposition.ensure_current()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["d0"], 3)
        self.assertEqual(
            result["first_blocker"],
            "OWNER_RETURN_VERSIONED_CANDIDATE_EVIDENCE_DRIFT_REQUIRES_OWNER_AUTHORIZATION",
        )
        self.assertFalse(result["live_materialization_invoked"])
        validate_document(result)

    def test_ensure_current_returns_a_verified_live_repair_only_after_drift(self) -> None:
        repaired = {
            "schema": "qikvrt_remaining_archive_disposition_verification_v1",
            "state": "CURRENT",
        }
        with mock.patch.object(
            disposition,
            "verify_materialized",
            side_effect=disposition.DispositionError("materialized output drift"),
        ) as verify, mock.patch.object(
            disposition,
            "materialize_atomically",
            return_value=copy.deepcopy(repaired),
        ) as materialize, mock.patch.object(
            disposition,
            "versioned_candidate_owner_boundary",
            return_value=None,
        ):
            result, exit_code = disposition.ensure_current()

        self.assertEqual(exit_code, 0)
        self.assertEqual(verify.call_count, 1)
        materialize.assert_called_once_with()
        self.assertEqual(result["recovery"]["state"], "CURRENT_LIVE_REPAIRED")
        self.assertTrue(result["recovery"]["live_reobservation_attempted"])

    def test_schema_drift_is_a_typed_block_not_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "RECOVERY_RECEIPT.json"
            with mock.patch.object(
                disposition,
                "verify_materialized",
                side_effect=KeyError("subjects"),
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = disposition.main(["--check", "--receipt", str(receipt)])
            result = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REMAINING_ARCHIVE_CONTENT_DISPOSITION_INVALID")
        self.assertIn("materialized evidence schema drift", result["reason"])

    def test_non_transport_public_validation_failure_is_block_not_hold(self) -> None:
        with mock.patch.object(
            disposition,
            "verify_materialized",
            side_effect=disposition.DispositionError("materialized output drift"),
        ), mock.patch.object(
            disposition,
            "materialize_atomically",
            side_effect=probe.E("exact public byte mismatch"),
        ), mock.patch.object(
            disposition,
            "versioned_candidate_owner_boundary",
            return_value=None,
        ):
            result, exit_code = disposition.ensure_current()

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "ZENODO_PUBLIC_EVIDENCE_VALIDATION_FAILED")

    def test_atomic_materialization_restores_the_previous_complete_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            base = root / "release/zenodo-corpus-proof-2026-07-28/canonical-union"
            batch = base / "content-disposition-batch-003"
            proof = base / "retrospective-proof-corpus"
            progress = root / "AI_PROGRESS.json"
            status = root / "AI_STATUS.md"
            with (
                mock.patch.object(disposition, "ROOT", root),
                mock.patch.object(disposition, "BASE", base),
                mock.patch.object(disposition, "B3", batch),
                mock.patch.object(disposition, "PROOF", proof),
                mock.patch.object(disposition, "AI_PROGRESS", progress),
                mock.patch.object(disposition, "AI_STATUS", status),
            ):
                prior = disposition.paths(probe.SUBJECTS[0]["subject_id"])["CLAIM_MATRIX.json"]
                partial = disposition.paths(probe.SUBJECTS[1]["subject_id"])["CLAIM_MATRIX.json"]
                prior.parent.mkdir(parents=True)
                prior.write_bytes(b"complete-prior-evidence")
                progress.write_bytes(b"prior-progress")

                def write_partial_then_fail() -> None:
                    prior.write_bytes(b"partial-rewrite")
                    partial.parent.mkdir(parents=True, exist_ok=True)
                    partial.write_bytes(b"partial-new-evidence")
                    progress.write_bytes(b"partial-progress")
                    raise probe.E("GET failed: HTTP Error 504")

                with mock.patch.object(
                    disposition,
                    "materialize",
                    side_effect=write_partial_then_fail,
                ):
                    with self.assertRaisesRegex(probe.E, r"HTTP Error 504"):
                        disposition.materialize_atomically()

                self.assertEqual(prior.read_bytes(), b"complete-prior-evidence")
                self.assertEqual(progress.read_bytes(), b"prior-progress")
                self.assertFalse(partial.exists())

    def test_direct_materialization_persists_a_typed_hold_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "RECOVERY_RECEIPT.json"
            with mock.patch.object(
                disposition,
                "materialize_atomically",
                side_effect=probe.TransientObservationError("GET failed: HTTP Error 504"),
            ), mock.patch.object(
                disposition,
                "versioned_candidate_owner_boundary",
                return_value=None,
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = disposition.main(
                    ["--materialize", "--receipt", str(receipt), "--json"]
                )

            result = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "ZENODO_PUBLIC_REOBSERVATION_UNCONFIRMED")
        self.assertFalse(result["zenodo_mutation_attempted"])

    def test_direct_materialization_respects_an_accepted_owner_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "RECOVERY_RECEIPT.json"
            with mock.patch.object(
                disposition,
                "versioned_candidate_owner_boundary",
                return_value="ACCEPTED",
            ), mock.patch.object(
                disposition,
                "materialize_atomically",
                side_effect=AssertionError("accepted evidence must not be rematerialized"),
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = disposition.main(
                    ["--materialize", "--receipt", str(receipt), "--json"]
                )
            result = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["d0"], 3)
        self.assertFalse(result["live_materialization_invoked"])
        validate_document(result)

    def test_direct_probe_workflow_uploads_receipt_before_hold_enforcement(self) -> None:
        workflow = (
            pathlib.Path(__file__).resolve().parents[1]
            / ".github/workflows/qikvrt_batch003_remaining_archive_probe.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("--receipt", workflow)
        self.assertIn('statuses=("${PIPESTATUS[@]}")', workflow)
        self.assertIn("Upload immutable remaining-subject probe evidence", workflow)
        self.assertIn("Enforce typed archive-probe HOLD after evidence upload", workflow)
        self.assertIn("steps.probe_evidence.outcome == 'success'", workflow)
        self.assertIn("steps.probe.outputs.exit_code != ''", workflow)
        self.assertLess(
            workflow.index("Upload immutable remaining-subject probe evidence"),
            workflow.index("Enforce typed archive-probe HOLD after evidence upload"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
