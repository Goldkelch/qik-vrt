#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Unit conformance tests for the fail-closed API handler.

All state is created below the operating system's temporary directory.  The
test suite therefore never writes runtime evidence into the source checkout.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from qikvrt_api_handler import (  # noqa: E402
    HandlerConfig,
    run_handler,
    validate_audit_chain,
)
from qikvrt_effect_ack import EffectState, canonical_json  # noqa: E402


class HandlerUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="qikvrt-handler-unit-")
        self.root = Path(self.temporary.name)
        self.payload = b"QIK-VRT handler unit payload"
        self.sha256 = hashlib.sha256(self.payload).hexdigest()
        self.payload_b64 = base64.b64encode(self.payload).decode("ascii")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def config(self, operation: str, **changes: object) -> HandlerConfig:
        values: dict[str, object] = {
            "root": self.root,
            "operation": operation,
            "artifact_id": "unit-artifact",
            "payload_b64": self.payload_b64,
            "expected_sha256": self.sha256,
            "dry_run": True,
            "repository": "tests/qik-vrt",
            "run_id": "unit-run",
            "request_id": "unit-request",
            "effect_accepted": False,
            "responsibility_owner": "unit-test-owner",
            "origin_authenticated": True,
        }
        values.update(changes)
        return HandlerConfig(**values)  # type: ignore[arg-type]

    def authorized_ingest(self, **changes: object) -> HandlerConfig:
        authorized: dict[str, object] = {
            "dry_run": False,
            "request_id": "authorized-ingest",
            "effect_accepted": True,
            "responsibility_owner": "unit-test-owner",
            "origin_authenticated": True,
        }
        authorized.update(changes)
        return self.config("ingest", **authorized)

    def test_handler_reaches_all_five_effect_ack_states(self) -> None:
        done = run_handler(self.config("ingest"))
        nack = run_handler(
            self.config(
                "verify",
                artifact_id="not-present",
                payload_b64="",
                request_id="nack-request",
            )
        )
        continued = run_handler(
            self.config(
                "release_status",
                artifact_id="status",
                payload_b64="",
                expected_sha256="",
                request_id="continue-request",
            )
        )
        blocked = run_handler(
            self.config(
                "ingest",
                expected_sha256="0" * 64,
                request_id="blocked-request",
            )
        )

        accepted = run_handler(self.authorized_ingest())
        self.assertEqual(accepted["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        isolated = run_handler(
            self.authorized_ingest(
                artifact_id="different-artifact",
                payload_b64=base64.b64encode(b"different").decode("ascii"),
                expected_sha256=hashlib.sha256(b"different").hexdigest(),
            )
        )

        observed = {
            done["effect_state"],
            nack["effect_state"],
            continued["effect_state"],
            blocked["effect_state"],
            isolated["effect_state"],
        }
        self.assertEqual(observed, {state.value for state in EffectState})
        self.assertTrue(done["ordinary_release"])
        self.assertFalse(nack["ordinary_release"])
        self.assertFalse(continued["ordinary_release"])
        self.assertFalse(blocked["ordinary_release"])
        self.assertFalse(isolated["ordinary_release"])

    def test_real_mutation_requires_complete_scoped_authorization(self) -> None:
        cases = {
            "request-id": ({"request_id": ""}, EffectState.EFFECT_ACK_BLOCK),
            "acceptance": ({"effect_accepted": False}, EffectState.EFFECT_ACK_BLOCK),
            "owner": ({"responsibility_owner": ""}, EffectState.EFFECT_ACK_BLOCK),
            "authentication": ({"origin_authenticated": False}, EffectState.EFFECT_ACK_BLOCK),
        }
        for name, (changes, expected_state) in cases.items():
            with self.subTest(name=name):
                artifact_id = f"blocked-{name}"
                result = run_handler(self.authorized_ingest(artifact_id=artifact_id, **changes))
                self.assertEqual(result["effect_state"], expected_state.value)
                self.assertFalse(result["ordinary_release"])
                target = self.root / ".qikvrt" / "api" / "inbox" / f"{artifact_id}.bin"
                self.assertFalse(target.exists())

    def test_complete_authorization_allows_exactly_scoped_mutation(self) -> None:
        result = run_handler(self.authorized_ingest())
        target = self.root / ".qikvrt" / "api" / "inbox" / "unit-artifact.bin"

        self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertTrue(result["ordinary_release"])
        self.assertEqual(result["write_status"], "WRITTEN")
        self.assertFalse(result["git_invoked"])
        self.assertEqual(target.read_bytes(), self.payload)

    def test_release_status_is_continue_until_remote_hash_is_confirmed(self) -> None:
        result = run_handler(
            self.config(
                "release_status",
                artifact_id="status",
                payload_b64="",
                expected_sha256="",
            )
        )
        self.assertEqual(result["status"], "CONTINUE")
        self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_CONTINUE.value)
        self.assertEqual(result["remote_byte_exact_asset_hash"], "NOT_CONFIRMED")
        self.assertFalse(result["ordinary_release"])
        self.assertEqual(result["haltpoint"]["exit_code"], 20)

    def test_release_status_reaches_done_only_with_verified_remote_attestation(self) -> None:
        asset = b"immutable remote release asset"
        digest = hashlib.sha256(asset).hexdigest()
        secret_material = b"unit-test-attestation-secret-key-32"
        secret = "b64url:" + base64.urlsafe_b64encode(secret_material).rstrip(b"=").decode("ascii")
        projection = {
            "schema": "qikvrt_remote_release_attestation_v1",
            "repository": "tests/qik-vrt",
            "release_run_id": "remote-run-42",
            "asset_name": "release.bin",
            "asset_sha256": digest,
            "asset_size": len(asset),
            "source_uri": "https://github.com/tests/qik-vrt/actions/runs/42",
            "immutable_source_id": "github-actions-run:42:artifact:release.bin",
            "signer": "release-attestor",
        }
        attestation = {
            **projection,
            "signature": hmac.new(secret_material, canonical_json(projection).encode(), hashlib.sha256).hexdigest(),
        }
        result = run_handler(
            self.config(
                "release_status",
                artifact_id="status",
                payload_b64=base64.b64encode(asset).decode("ascii"),
                expected_sha256=digest,
                request_id="release-attested",
                remote_evidence_b64=base64.b64encode(json.dumps(attestation).encode()).decode("ascii"),
                trusted_attestation_secret=secret,
                trusted_attestation_signer="release-attestor",
            )
        )
        self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertTrue(result["ordinary_release"])
        self.assertEqual(result["remote_byte_exact_asset_hash"], digest)

    def test_every_completed_request_extends_a_valid_audit_chain(self) -> None:
        run_handler(self.config("ingest", request_id="audit-one"))
        run_handler(
            self.config(
                "release_status",
                artifact_id="status",
                payload_b64="",
                expected_sha256="",
                request_id="audit-two",
            )
        )
        audit_path = self.root / ".qikvrt" / "api" / "audit" / "events.jsonl"
        last = validate_audit_chain(audit_path)
        self.assertEqual(last["sequence"], 4)
        self.assertEqual(last["event"], "request_result")
        self.assertRegex(last["event_hash"], r"^[0-9a-f]{64}$|^sha256:[0-9a-f]{64}$")


    def test_work_order_is_hash_bound_registered_and_not_executed(self) -> None:
        work_order = {
            "schema": "qikvrt_work_order_v1",
            "task_type": "implement_artifact",
            "output_path": "QIK_VRT_MESH.html",
            "requirements": {
                "offline": True,
                "singleFile": True,
                "svgEngine": True,
            },
            "acceptance": {
                "roundtripTests": True,
                "idempotenceTests": True,
            },
            "notes": "unit work order",
        }
        payload = json.dumps(
            work_order, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        encoded = base64.b64encode(payload).decode("ascii")

        dry = run_handler(
            self.config(
                "work_order",
                artifact_id="mesh-html",
                payload_b64=encoded,
                expected_sha256=digest,
                request_id="work-order-dry",
            )
        )
        self.assertEqual(dry["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertTrue(dry["work_order_accepted"])
        self.assertEqual(dry["task_execution"], "NOT_EXECUTED")
        self.assertEqual(dry["write_status"], "DRY_RUN")

        cfg = self.config(
            "work_order",
            artifact_id="mesh-html",
            payload_b64=encoded,
            expected_sha256=digest,
            dry_run=False,
            request_id="work-order-live",
            effect_accepted=True,
            responsibility_owner="unit-test-owner",
            origin_authenticated=True,
        )
        live = run_handler(cfg)
        self.assertEqual(live["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertTrue(live["ordinary_release"])
        self.assertEqual(live["task_execution"], "NOT_EXECUTED")
        self.assertEqual(live["write_status"], "WRITTEN")
        registration = self.root / live["registration_path"]
        self.assertTrue(registration.is_file())
        registered = json.loads(registration.read_text(encoding="utf-8"))
        self.assertEqual(registered["work_order"]["output_path"], "QIK_VRT_MESH.html")
        self.assertEqual(registered["source_sha256"], digest)

        replay = run_handler(cfg)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["source_sha256"], digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
