#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Adversarial tests for handler authorization, integrity and replay controls."""
from __future__ import annotations

import base64
import concurrent.futures
import contextlib
import hashlib
import hmac
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import qikvrt_api_handler as handler  # noqa: E402
import qikvrt_github_api_shim as shim  # noqa: E402
from qikvrt_api_handler import (  # noqa: E402
    HandlerConfig,
    IntegrityIsolationError,
    dirs,
    run_handler,
    validate_audit_chain,
)
from qikvrt_effect_ack import (  # noqa: E402
    EffectState,
    ResponsibilityProtocol,
    canonical_json,
    compute_protocol_hash,
)


DISPATCH_PATH = "/repos/security/qik-vrt/actions/workflows/qikvrt_mesh_api.yml/dispatches"
API_TOKEN_MATERIAL = b"qikvrt-security-test-api-token-32"
API_TOKEN = "b64url:" + base64.urlsafe_b64encode(API_TOKEN_MATERIAL).rstrip(b"=").decode("ascii")


def encoded_secret(material: bytes) -> str:
    return "b64url:" + base64.urlsafe_b64encode(material).rstrip(b"=").decode("ascii")


@contextlib.contextmanager
def live_shim(root: Path):
    environment = {
        "QIKVRT_API_TOKEN": API_TOKEN,
        "QIKVRT_API_TOKEN_EXPIRES_UTC": "2099-01-01T00:00:00Z",
        "QIKVRT_ALLOWED_REPOSITORY": "security/qik-vrt",
        "QIKVRT_API_PRINCIPAL": "security-test-owner",
        "QIKVRT_REPO_ROOT": str(root),
        "QIKVRT_RATE_LIMIT_PER_MINUTE": "10000",
        "QIKVRT_API_LOG": "0",
        "QIKVRT_REMOTE_ATTESTATION_SECRET": "",
        "QIKVRT_TRUSTED_ATTESTATION_SIGNER": "",
    }
    with mock.patch.dict(os.environ, environment, clear=False):
        with shim._RATE_LOCK:
            shim._RATE_WINDOWS.clear()
        server = ThreadingHTTPServer(("127.0.0.1", 0), shim.QikvrtGitHubApiShim)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def http_json(
    address: tuple[str, int],
    body: bytes,
    *,
    token: str | None = API_TOKEN,
    content_length: str | None = None,
) -> tuple[int, dict[str, object]]:
    connection = http.client.HTTPConnection(*address, timeout=5)
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if content_length is not None:
        headers["Content-Length"] = content_length
    connection.request("POST", DISPATCH_PATH, body=body, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    connection.close()
    return response.status, json.loads(raw.decode("utf-8"))


def http_health(address: tuple[str, int]) -> tuple[int, dict[str, object]]:
    connection = http.client.HTTPConnection(*address, timeout=5)
    connection.request("GET", "/health")
    response = connection.getresponse()
    raw = response.read()
    connection.close()
    return response.status, json.loads(raw.decode("utf-8"))


def http_get(address: tuple[str, int], path: str) -> tuple[int, bytes, str]:
    connection = http.client.HTTPConnection(*address, timeout=5)
    connection.request("GET", path)
    response = connection.getresponse()
    raw = response.read()
    content_type = response.getheader("Content-Type", "")
    connection.close()
    return response.status, raw, content_type


class HandlerSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="qikvrt-handler-security-")
        self.root = Path(self.temporary.name) / "state"
        self.root.mkdir()
        self.payload = b"security-sensitive QIK-VRT payload"
        self.payload_b64 = base64.b64encode(self.payload).decode("ascii")
        self.sha256 = hashlib.sha256(self.payload).hexdigest()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def config(self, **changes: object) -> HandlerConfig:
        values: dict[str, object] = {
            "root": self.root,
            "operation": "ingest",
            "artifact_id": "secure-artifact",
            "payload_b64": self.payload_b64,
            "expected_sha256": self.sha256,
            "dry_run": False,
            "repository": "security/qik-vrt",
            "run_id": "security-run",
            "request_id": "secure-request",
            "effect_accepted": True,
            "responsibility_owner": "security-test-owner",
            "origin_authenticated": True,
        }
        values.update(changes)
        return HandlerConfig(**values)  # type: ignore[arg-type]

    def target(self, artifact_id: str = "secure-artifact") -> Path:
        return self.root / ".qikvrt" / "api" / "inbox" / f"{artifact_id}.bin"

    def test_missing_and_expired_api_credentials_are_rejected(self) -> None:
        body = json.dumps(
            {
                "ref": "main",
                "inputs": {
                    "operation": "release_status",
                    "artifact_id": "status",
                    "dry_run": "true",
                    "request_id": "security-credential-check",
                    "effect_accepted": "false",
                },
            }
        ).encode("utf-8")
        with live_shim(self.root) as address:
            health_status, health = http_health(address)
            self.assertEqual(health_status, 200)
            self.assertEqual(health["status"], "ALIVE")
            self.assertTrue(health["configuration_valid"])

            status, _ = http_json(address, body, token=None)
            self.assertEqual(status, 401)

            with mock.patch.dict(
                os.environ,
                {"QIKVRT_API_TOKEN": "weak-and-ambiguously-encoded"},
                clear=False,
            ):
                health_status, health = http_health(address)
                self.assertEqual(health_status, 503)
                self.assertEqual(health["status"], "BLOCK")
                self.assertFalse(health["configuration_valid"])

            with mock.patch.dict(
                os.environ,
                {
                    "QIKVRT_REMOTE_ATTESTATION_SECRET": "b64url:dG9vLXNob3J0",
                    "QIKVRT_TRUSTED_ATTESTATION_SIGNER": "security-attestor",
                },
                clear=False,
            ):
                health_status, health = http_health(address)
                self.assertEqual(health_status, 503)
                self.assertEqual(health["status"], "BLOCK")

            with mock.patch.dict(
                os.environ,
                {
                    "QIKVRT_REMOTE_ATTESTATION_SECRET": API_TOKEN,
                    "QIKVRT_TRUSTED_ATTESTATION_SIGNER": "security-attestor",
                },
                clear=False,
            ):
                health_status, health = http_health(address)
                self.assertEqual(health_status, 503)
                self.assertEqual(health["status"], "BLOCK")

            with mock.patch.dict(
                os.environ,
                {"QIKVRT_API_TOKEN_EXPIRES_UTC": "2000-01-01T00:00:00Z"},
                clear=False,
            ):
                status, _ = http_json(address, body)
                self.assertEqual(status, 401)
                health_status, _ = http_health(address)
                self.assertEqual(health_status, 503)

            status, response = http_json(address, body)
            self.assertEqual(status, 202, response)
            self.assertEqual(response["status"], "CONTINUE")

    def test_public_capabilities_and_openapi_are_read_only(self) -> None:
        with live_shim(REPOSITORY_ROOT) as address:
            status, raw, content_type = http_get(address, "/capabilities")
            self.assertEqual(status, 200)
            self.assertIn("application/json", content_type)
            capabilities = json.loads(raw.decode("utf-8"))
            self.assertEqual(capabilities["schema"], "qikvrt_mesh_api_capabilities_v1")
            self.assertIn("/openapi.yaml", capabilities["public_read_endpoints"])
            self.assertFalse(capabilities["ordinary_release"])

            status, raw, content_type = http_get(address, "/openapi.yaml")
            self.assertEqual(status, 200)
            self.assertIn("openapi", content_type)
            self.assertIn(b"QIKVRT GitHub Dispatch Adapter API", raw)

    def test_client_cannot_claim_a_different_responsibility_owner(self) -> None:
        body = json.dumps(
            {
                "ref": "main",
                "inputs": {
                    "operation": "release_status",
                    "artifact_id": "status",
                    "dry_run": "true",
                    "request_id": "security-principal-check",
                    "effect_accepted": "false",
                    "responsibility_owner": "untrusted-client-claim",
                },
            }
        ).encode("utf-8")
        with live_shim(self.root) as address:
            status, response = http_json(address, body)
        self.assertEqual(status, 400)
        self.assertEqual(response["status"], "BLOCK")
        self.assertIn("authenticated principal", str(response["reason"]))

    def test_missing_explicit_effect_decision_is_rejected(self) -> None:
        body = json.dumps(
            {
                "ref": "main",
                "inputs": {
                    "operation": "release_status",
                    "artifact_id": "status",
                    "dry_run": "true",
                    "request_id": "missing-effect-decision",
                },
            }
        ).encode("utf-8")
        with live_shim(self.root) as address:
            status, response = http_json(address, body)
        self.assertEqual(status, 400)
        self.assertEqual(response["status"], "BLOCK")
        self.assertIn("effect_accepted", str(response["reason"]))

    def test_hash_mismatch_blocks_without_writing_payload(self) -> None:
        result = run_handler(self.config(expected_sha256="0" * 64))
        self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_BLOCK.value)
        self.assertFalse(result["ordinary_release"])
        self.assertFalse(self.target().exists())

    def test_old_receipt_is_not_an_authorization_credential(self) -> None:
        accepted = run_handler(self.config())
        self.assertEqual(accepted["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        before = self.target().stat().st_mtime_ns

        unauthorized = run_handler(replace(self.config(), origin_authenticated=False))
        self.assertEqual(unauthorized["effect_state"], EffectState.EFFECT_ACK_BLOCK.value)
        self.assertFalse(unauthorized["ordinary_release"])
        self.assertNotIn("replayed", unauthorized)
        self.assertEqual(self.target().stat().st_mtime_ns, before)

    def test_same_request_id_with_different_facts_is_isolated(self) -> None:
        run_handler(self.config())
        other = b"content that must not share the old idempotency key"
        result = run_handler(
            self.config(
                artifact_id="conflicting-artifact",
                payload_b64=base64.b64encode(other).decode("ascii"),
                expected_sha256=hashlib.sha256(other).hexdigest(),
            )
        )
        self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_ISOLATE.value)
        self.assertFalse(result["ordinary_release"])
        self.assertFalse(self.target("conflicting-artifact").exists())

    def test_identical_authorized_replay_is_idempotent(self) -> None:
        first = run_handler(self.config())
        first_stat = self.target().stat()
        second = run_handler(self.config())
        second_stat = self.target().stat()

        self.assertEqual(first["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertEqual(second["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertTrue(second["replayed"])
        self.assertEqual(first_stat.st_ino, second_stat.st_ino)
        self.assertEqual(first_stat.st_mtime_ns, second_stat.st_mtime_ns)
        self.assertEqual(self.target().read_bytes(), self.payload)
        last = validate_audit_chain(self.root / ".qikvrt" / "api" / "audit" / "events.jsonl")
        self.assertEqual(last["sequence"], 4)

    def test_multiple_ingest_requests_and_stage_manifests_remain_append_only(self) -> None:
        first_cfg = self.config(request_id="ingest-provenance-one")
        second_cfg = self.config(request_id="ingest-provenance-two")

        first = run_handler(first_cfg)
        second = run_handler(second_cfg)
        replay_first = run_handler(first_cfg)

        self.assertEqual(first["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertEqual(second["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertEqual(replay_first["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertTrue(replay_first["replayed"])
        provenance = self.root / ".qikvrt" / "api" / "provenance"
        self.assertEqual(
            sorted(path.name for path in provenance.glob("secure-artifact.*.json")),
            [
                "secure-artifact.ingest-provenance-one.json",
                "secure-artifact.ingest-provenance-two.json",
            ],
        )

        stage_one_cfg = self.config(
            operation="stage",
            artifact_id="status",
            payload_b64="",
            expected_sha256="",
            request_id="stage-manifest-one",
        )
        stage_two_cfg = replace(stage_one_cfg, request_id="stage-manifest-two")
        stage_one = run_handler(stage_one_cfg)
        stage_two = run_handler(stage_two_cfg)
        first_path = self.root / str(stage_one["stage_manifest"])
        second_path = self.root / str(stage_two["stage_manifest"])
        first_bytes = first_path.read_bytes()

        self.assertEqual(stage_one["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertEqual(stage_two["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertNotEqual(first_path, second_path)
        self.assertTrue(first_path.is_file())
        self.assertTrue(second_path.is_file())

        replay_stage_one = run_handler(stage_one_cfg)
        self.assertEqual(replay_stage_one["effect_state"], EffectState.EFFECT_ACK_DONE.value)
        self.assertTrue(replay_stage_one["replayed"])
        self.assertEqual(first_path.read_bytes(), first_bytes)

    def test_tampered_remote_attestation_is_isolated(self) -> None:
        secret_material = b"test-only-trusted-attestation-key"
        secret = encoded_secret(secret_material)
        asset = b"attested release bytes"
        digest = hashlib.sha256(asset).hexdigest()
        projection = {
            "schema": "qikvrt_remote_release_attestation_v1",
            "repository": "security/qik-vrt",
            "release_run_id": "42",
            "asset_name": "release.bin",
            "asset_sha256": digest,
            "asset_size": len(asset),
            "source_uri": "https://github.com/security/qik-vrt/actions/runs/42",
            "immutable_source_id": "github-actions-run:42:artifact:release.bin",
            "signer": "security-attestor",
        }
        signature = hmac.new(
            secret_material,
            canonical_json(projection).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        attestation = {**projection, "signature": "0" + signature[1:]}
        if attestation["signature"] == signature:
            attestation["signature"] = "1" + signature[1:]
        result = run_handler(
            self.config(
                operation="release_status",
                artifact_id="status",
                payload_b64=base64.b64encode(asset).decode("ascii"),
                expected_sha256=digest,
                dry_run=True,
                request_id="tampered-attestation",
                effect_accepted=False,
                remote_evidence_b64=base64.b64encode(
                    json.dumps(attestation).encode("utf-8")
                ).decode("ascii"),
                trusted_attestation_secret=secret,
                trusted_attestation_signer="security-attestor",
            )
        )
        self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_ISOLATE.value)
        self.assertFalse(result["ordinary_release"])

        weak_key = run_handler(
            self.config(
                operation="release_status",
                artifact_id="status",
                payload_b64=base64.b64encode(asset).decode("ascii"),
                expected_sha256=digest,
                dry_run=True,
                request_id="weak-attestation-key",
                effect_accepted=False,
                remote_evidence_b64=base64.b64encode(
                    json.dumps({**projection, "signature": signature}).encode("utf-8")
                ).decode("ascii"),
                trusted_attestation_secret="weak-raw-key",
                trusted_attestation_signer="security-attestor",
            )
        )
        self.assertEqual(weak_key["effect_state"], EffectState.EFFECT_ACK_BLOCK.value)
        self.assertFalse(weak_key["ordinary_release"])

    def test_symlinked_intermediate_directory_cannot_escape_root(self) -> None:
        external = Path(self.temporary.name) / "external-intermediate"
        external.mkdir()
        sentinel = external / "sentinel"
        sentinel.write_bytes(b"unchanged")
        (self.root / ".qikvrt").mkdir()
        (self.root / ".qikvrt" / "api").symlink_to(external, target_is_directory=True)

        with self.assertRaises(IntegrityIsolationError):
            run_handler(self.config())
        self.assertEqual(sentinel.read_bytes(), b"unchanged")
        self.assertFalse((external / "inbox" / "secure-artifact.bin").exists())

    def test_symlinked_target_is_isolated_without_external_write(self) -> None:
        external = Path(self.temporary.name) / "external-target.bin"
        external.write_bytes(b"must remain unchanged")
        inbox = dirs(self.root)["inbox"]
        (inbox / "secure-artifact.bin").symlink_to(external)

        result = run_handler(self.config())
        self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_ISOLATE.value)
        self.assertFalse(result["ordinary_release"])
        self.assertEqual(external.read_bytes(), b"must remain unchanged")

    def test_oversized_base64_is_rejected_before_decode_or_write(self) -> None:
        oversized = "A" * (handler.MAX_BASE64_CHARS + 1)
        result = run_handler(
            self.config(
                payload_b64=oversized,
                expected_sha256="0" * 64,
                dry_run=True,
                request_id="oversized-request",
                effect_accepted=False,
                responsibility_owner="",
                origin_authenticated=False,
            )
        )
        self.assertIn(
            result["effect_state"],
            {EffectState.EFFECT_NACK.value, EffectState.EFFECT_ACK_BLOCK.value},
        )
        self.assertFalse(result["ordinary_release"])
        self.assertIn("exceeds", result["reason"])
        self.assertFalse(self.target().exists())

    def test_stage_isolates_tampered_sidecar_and_metadata(self) -> None:
        for evidence_name in (
            "sidecar",
            "metadata",
            "transaction-request-id",
            "receipt-request-id",
            "transaction-result-hash",
            "protocol-input-id",
            "transaction-history",
        ):
            with self.subTest(evidence=evidence_name):
                subroot = self.root / evidence_name
                subroot.mkdir()
                ingest = replace(
                    self.config(),
                    root=subroot,
                    request_id=f"ingest-{evidence_name}",
                )
                self.assertEqual(
                    run_handler(ingest)["effect_state"],
                    EffectState.EFFECT_ACK_DONE.value,
                )
                inbox = subroot / ".qikvrt" / "api" / "inbox"
                request_id = f"ingest-{evidence_name}"
                metadata = (
                    subroot
                    / ".qikvrt"
                    / "api"
                    / "provenance"
                    / f"secure-artifact.{request_id}.json"
                )
                transaction = subroot / ".qikvrt" / "api" / "transactions" / f"{request_id}.json"
                receipt = subroot / ".qikvrt" / "api" / "replay" / f"{request_id}.json"
                if evidence_name == "metadata":
                    changed = json.loads(metadata.read_text(encoding="utf-8"))
                    changed["responsibility_owner"] = "different-owner"
                    metadata.write_text(json.dumps(changed), encoding="utf-8")
                elif evidence_name == "sidecar":
                    (inbox / "secure-artifact.bin.sha256").write_text(
                        "tampered\n", encoding="utf-8"
                    )
                elif evidence_name.startswith("transaction-"):
                    changed = json.loads(transaction.read_text(encoding="utf-8"))
                    if evidence_name == "transaction-request-id":
                        changed["request_id"] = "different-request"
                    elif evidence_name == "transaction-result-hash":
                        changed["result_sha256"] = "sha256:" + "0" * 64
                    else:
                        changed["history"] = [
                            changed["history"][0],
                            changed["history"][2],
                        ]
                    transaction.write_text(json.dumps(changed), encoding="utf-8")
                else:
                    changed_receipt = json.loads(receipt.read_text(encoding="utf-8"))
                    changed_transaction = json.loads(transaction.read_text(encoding="utf-8"))
                    if evidence_name == "receipt-request-id":
                        changed_receipt["request_id"] = "different-request"
                    else:
                        protocol_raw = changed_receipt["result"]["effect_ack"][
                            "responsibility_protocol"
                        ]
                        protocol = ResponsibilityProtocol.from_dict(protocol_raw)
                        forged = replace(protocol, input_id="different-request", protocol_hash="")
                        forged = replace(forged, protocol_hash=compute_protocol_hash(forged))
                        changed_receipt["result"]["effect_ack"][
                            "responsibility_protocol"
                        ] = forged.to_dict()
                        result_hash = handler.sha256_identifier(
                            handler._canonical_bytes(changed_receipt["result"])
                        )
                        changed_receipt["result_sha256"] = result_hash
                        changed_transaction["result_sha256"] = result_hash
                        transaction.write_text(
                            json.dumps(changed_transaction), encoding="utf-8"
                        )
                    receipt.write_text(json.dumps(changed_receipt), encoding="utf-8")

                stage = HandlerConfig(
                    root=subroot,
                    operation="stage",
                    artifact_id="status",
                    payload_b64="",
                    expected_sha256="",
                    dry_run=True,
                    request_id=f"stage-{evidence_name}",
                )
                result = run_handler(stage)
                self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_ISOLATE.value)
                self.assertFalse(result["ordinary_release"])

    def test_audit_tampering_is_detected_and_new_effect_is_isolated(self) -> None:
        run_handler(
            HandlerConfig(
                root=self.root,
                operation="release_status",
                artifact_id="status",
                payload_b64="",
                expected_sha256="",
                dry_run=True,
                request_id="audit-before-tamper",
            )
        )
        audit = self.root / ".qikvrt" / "api" / "audit" / "events.jsonl"
        records = audit.read_text(encoding="utf-8").splitlines()
        first = json.loads(records[0])
        first["artifact_id"] = "forged"
        records[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
        audit.write_text("\n".join(records) + "\n", encoding="utf-8")

        result = run_handler(self.config(request_id="after-audit-tamper"))
        self.assertEqual(result["effect_state"], EffectState.EFFECT_ACK_ISOLATE.value)
        self.assertEqual(result["audit_status"], "ISOLATED_UNTRUSTED")
        self.assertFalse(result["ordinary_release"])
        self.assertFalse(self.target().exists())

    def test_malformed_json_and_negative_content_length_are_rejected(self) -> None:
        with live_shim(self.root) as address:
            malformed_status, malformed = http_json(address, b"{")
            self.assertEqual(malformed_status, 400)
            self.assertEqual(malformed["status"], "BLOCK")

            negative_status, negative = http_json(
                address,
                b"",
                content_length="-1",
            )
            self.assertEqual(negative_status, 400)
            self.assertEqual(negative["status"], "BLOCK")

    def test_duplicate_keys_nonfinite_numbers_and_query_routes_are_rejected(self) -> None:
        with live_shim(self.root) as address:
            duplicate_status, duplicate = http_json(
                address,
                b'{"ref":"main","ref":"other","inputs":{}}',
            )
            self.assertEqual(duplicate_status, 400)
            self.assertEqual(duplicate["status"], "BLOCK")

            nonfinite_status, nonfinite = http_json(
                address,
                b'{"ref":NaN,"inputs":{}}',
            )
            self.assertEqual(nonfinite_status, 400)
            self.assertEqual(nonfinite["status"], "BLOCK")

            connection = http.client.HTTPConnection(*address, timeout=5)
            connection.request(
                "POST",
                DISPATCH_PATH + "?unexpected=true",
                body=b"{}",
                headers={
                    "Authorization": f"Bearer {API_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            response = connection.getresponse()
            query_body = json.loads(response.read().decode("utf-8"))
            connection.close()
            self.assertEqual(response.status, 404)
            self.assertEqual(query_body["status"], "BLOCK")

    def test_cross_thread_duplicate_causes_one_effect_and_safe_replays(self) -> None:
        cfg = self.config(request_id="thread-duplicate")
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: run_handler(cfg), range(8)))

        self.assertTrue(
            all(result["effect_state"] == EffectState.EFFECT_ACK_DONE.value for result in results)
        )
        self.assertEqual(sum(bool(result.get("replayed")) for result in results), 7)
        self.assertEqual(self.target().read_bytes(), self.payload)
        inbox_payloads = list((self.root / ".qikvrt" / "api" / "inbox").glob("*.bin"))
        self.assertEqual(inbox_payloads, [self.target()])
        last = validate_audit_chain(self.root / ".qikvrt" / "api" / "audit" / "events.jsonl")
        self.assertEqual(last["sequence"], 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)
