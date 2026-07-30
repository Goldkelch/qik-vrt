# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.qikvrt_effect_ack import (
    ConnectionDecision,
    EffectAckEngine,
    EffectAckRequest,
    EffectState,
    RiskLevel,
)
from tools.qikvrt_anticipation import checkpoint_hash, sha256_bytes
from tools.qikvrt_seed_common import canonical_json_bytes
from tools.qikvrt_targeted_effect import (
    TargetedEffectError,
    evaluate_targeted_envelope,
    targeted_effect_subject,
    validate_envelope,
)


ROOT = Path(__file__).resolve().parents[1]


class TargetedEffectEnvelopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.guid = "11111111-2222-4333-8444-555555555555"
        self.repository = "example/node"
        self.ref = "main"

        self._write_bytes("payload/effect.json", b'{"effect":"bounded"}\n')
        self._write_json(
            f"registry/nodes/{self.guid}.json",
            {
                "guid": self.guid,
                "repository": self.repository,
                "node_branch": self.ref,
            },
        )
        self._write_json(
            "registry/NODEMESH_INDEX.json",
            {
                "nodes": [
                    {
                        "guid": self.guid,
                        "repository": self.repository,
                        "node_branch": self.ref,
                        "registry_path": f"registry/nodes/{self.guid}.json",
                        "registry_status": "ACCEPTED",
                        "policy_status": "ACTIVE",
                        "effective_status": "ACTIVE",
                    }
                ]
            },
        )
        self._write_json(
            "registry/NODEMESH_STATUS.json",
            {
                "nodes": [
                    {
                        "guid": self.guid,
                        "heartbeat_status": "FRESH",
                        "expires_utc": "2026-08-01T12:10:00Z",
                    }
                ]
            },
        )
        checkpoint: dict[str, Any] = {
            "schema": "qikvrt_closure_checkpoint_v1",
            "scope_id": "test-scope",
            "checkpoint_id": "test-checkpoint-2",
            "stage": "ANTICIPATION_MATERIALIZED",
            "observed_at": "2026-08-01T11:00:00Z",
            "source_revision": "git-tree:" + "1" * 40,
            "previous_checkpoint_sha256": "0" * 64,
            "bindings": {},
            "effect_state": "EFFECT_ACK_CONTINUE",
            "external_effect": "NONE",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        }
        checkpoint["checkpoint_sha256"] = checkpoint_hash(
            checkpoint, previous_checkpoint_sha256="0" * 64
        )
        self._write_json("receipts/checkpoint-2.json", checkpoint)

        self.envelope = {
            "_license": {
                "classification": "test_fixture",
                "copyright": "Copyright 2026 Ingolf Lohmann",
                "license": "CC-BY-NC-ND-4.0",
                "rights_holder": "Ingolf Lohmann",
            },
            "schema": "qikvrt_targeted_effect_envelope_v1",
            "envelope_id": "targeted-effect-test-0001",
            "effect_scope": "bounded test effect",
            "payload": self._binding("payload/effect.json"),
            "target": {
                "node_guid": self.guid,
                "repository": self.repository,
                "ref": self.ref,
                "registry_path": f"registry/nodes/{self.guid}.json",
                "registry_entry_sha256": self._binding(
                    f"registry/nodes/{self.guid}.json"
                )["sha256"],
                "registry_index_path": "registry/NODEMESH_INDEX.json",
                "registry_index_sha256": self._binding(
                    "registry/NODEMESH_INDEX.json"
                )["sha256"],
                "registry_status_path": "registry/NODEMESH_STATUS.json",
                "registry_status_sha256": self._binding(
                    "registry/NODEMESH_STATUS.json"
                )["sha256"],
            },
            "timing": {
                "not_before_utc": "2026-08-01T12:00:00Z",
                "expires_utc": "2026-08-01T12:15:00Z",
                "evaluated_at_utc": "2026-08-01T12:05:00Z",
            },
            "authorization": {
                "responsible_human": "Responsible Reviewer",
                "origin_authenticated": False,
                "effect_ack_state": "EFFECT_ACK_CONTINUE",
                "effect_ack_protocol_path": None,
                "effect_ack_protocol_hash": None,
                "effect_ack_evaluated_at_utc": None,
            },
            "checkpoint": {
                "previous_checkpoint_path": "receipts/checkpoint-2.json",
                "previous_checkpoint_sha256": checkpoint["checkpoint_sha256"],
            },
            "dispatch": {
                "state": "NOT_DISPATCHED",
                "attempted": False,
                "transport_ack": False,
                "effect_receipt": None,
            },
            "non_claims": [
                "transport acknowledgement is effect acknowledgement",
                "delivery was completed",
                "eligibility is dispatch authorization",
                "the target has received the payload",
            ],
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_bytes(self, relative: str, payload: bytes) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def _write_json(self, relative: str, value: Any) -> None:
        self._write_bytes(relative, canonical_json_bytes(value))

    def _binding(self, relative: str) -> dict[str, Any]:
        payload = (self.root / relative).read_bytes()
        return {
            "path": relative,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
        }

    def _bind_done_protocol(self, envelope: dict[str, Any]) -> None:
        envelope["authorization"]["origin_authenticated"] = True
        envelope["authorization"]["effect_ack_state"] = EffectState.EFFECT_ACK_DONE.value
        subject = targeted_effect_subject(envelope)
        evidence = "sha256:" + sha256_bytes(b"targeted-effect-test-evidence")
        request = EffectAckRequest(
            protocol_root_id="qikvrt:targeted-effect:test",
            input_id=envelope["envelope_id"],
            payload=subject,
            declared_input_hash="sha256:" + sha256_bytes(subject),
            transport_ack=True,
            origin_checked=True,
            context_checked=True,
            semantics_reconstructed=True,
            effect_anticipated=True,
            risk_classified=True,
            risk_level=RiskLevel.LOW,
            responsibility_assigned=True,
            responsibility_owner=envelope["authorization"]["responsible_human"],
            connection_decision=ConnectionDecision.RELEASE,
            policy_allows_release=True,
            reasons=("target, time and payload evaluated",),
            evidence_refs=(evidence,),
            required_evidence_refs=(evidence,),
            open_questions=(),
            next_required_checks=(),
        )
        protocol = EffectAckEngine().evaluate(
            request,
            created_utc=envelope["timing"]["evaluated_at_utc"],
        ).protocol
        self.assertIs(protocol.state, EffectState.EFFECT_ACK_DONE)
        protocol_path = "evidence/effect-ack.json"
        self._write_json(protocol_path, protocol.to_dict())
        envelope["authorization"]["effect_ack_protocol_path"] = protocol_path
        envelope["authorization"]["effect_ack_protocol_hash"] = (
            protocol.protocol_hash
        )
        envelope["authorization"]["effect_ack_evaluated_at_utc"] = (
            protocol.created_utc
        )

    def test_schema_is_generic_and_contains_no_old_live_target(self) -> None:
        schema_path = ROOT / "schemas/qikvrt-targeted-effect-envelope.schema.json"
        schema_text = schema_path.read_text(encoding="utf-8")
        schema = json.loads(schema_text)
        self.assertNotIn("a84f157a-cef2-4c47-bca9-8f407085bdbe", schema_text)
        self.assertNotIn("2026-08-01T12:00:00Z", schema_text)
        target_properties = schema["properties"]["target"]["properties"]
        self.assertEqual(target_properties["registry_index_path"]["type"], "string")
        self.assertEqual(target_properties["registry_status_path"]["type"], "string")

    def test_due_target_without_fresh_done_remains_continue(self) -> None:
        result = evaluate_targeted_envelope(self.envelope, self.root)
        self.assertEqual(result["state"], "CONTINUE_AWAITING_FRESH_EFFECT_ACK")
        self.assertFalse(result["dispatch_eligible"])
        self.assertFalse(result["dispatch_attempted"])

    def test_payload_hash_tamper_blocks(self) -> None:
        self._write_bytes("payload/effect.json", b"tampered\n")
        result = evaluate_targeted_envelope(self.envelope, self.root)
        self.assertEqual(result["state"], "BLOCK")
        self.assertIn("PAYLOAD_HASH_OR_SIZE_MISMATCH", result["failure_classes"])

    def test_unknown_target_blocks(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["target"]["node_guid"] = "99999999-8888-4777-8666-555555555555"
        result = evaluate_targeted_envelope(envelope, self.root)
        self.assertEqual(result["state"], "BLOCK")
        self.assertIn("TARGET_NODE_NOT_UNIQUE", result["failure_classes"])

    def test_malformed_registry_shape_fails_closed(self) -> None:
        self._write_json("registry/NODEMESH_INDEX.json", {"nodes": {}})
        envelope = copy.deepcopy(self.envelope)
        envelope["target"]["registry_index_sha256"] = self._binding(
            "registry/NODEMESH_INDEX.json"
        )["sha256"]
        with self.assertRaisesRegex(
            TargetedEffectError, "index and status nodes must be arrays"
        ):
            evaluate_targeted_envelope(envelope, self.root)

    def test_fresh_target_before_time_remains_continue(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["timing"]["evaluated_at_utc"] = "2026-08-01T11:59:00Z"
        result = evaluate_targeted_envelope(envelope, self.root)
        self.assertEqual(result["state"], "CONTINUE_NOT_YET_DUE")
        self.assertFalse(result["dispatch_eligible"])

    def test_claimed_done_without_valid_protocol_blocks(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["authorization"].update(
            {
                "origin_authenticated": True,
                "effect_ack_state": "EFFECT_ACK_DONE",
                "effect_ack_protocol_path": "evidence/invalid.json",
                "effect_ack_protocol_hash": "sha256:" + "0" * 64,
                "effect_ack_evaluated_at_utc": envelope["timing"][
                    "evaluated_at_utc"
                ],
            }
        )
        self._write_json("evidence/invalid.json", {"invalid": True})
        result = evaluate_targeted_envelope(envelope, self.root)
        self.assertEqual(result["state"], "BLOCK")
        self.assertIn("FALSE_EFFECT_ACK_DONE", result["failure_classes"])

    def test_due_target_with_fresh_done_is_only_eligible(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        self._bind_done_protocol(envelope)
        result = evaluate_targeted_envelope(envelope, self.root)
        self.assertEqual(
            result["state"], "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_DISPATCH"
        )
        self.assertTrue(result["dispatch_eligible"])
        self.assertFalse(result["dispatch_attempted"])
        self.assertFalse(result["transport_ack_is_effect_ack"])

    def test_expired_window_blocks_even_with_done(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["timing"]["evaluated_at_utc"] = "2026-08-01T12:16:00Z"
        self._bind_done_protocol(envelope)
        result = evaluate_targeted_envelope(envelope, self.root)
        self.assertEqual(result["state"], "BLOCK")
        self.assertIn("DELIVERY_WINDOW_EXPIRED", result["failure_classes"])

    def test_checkpoint_tamper_blocks(self) -> None:
        checkpoint = json.loads(
            (self.root / "receipts/checkpoint-2.json").read_text(encoding="utf-8")
        )
        checkpoint["stage"] = "TAMPERED"
        self._write_json("receipts/checkpoint-2.json", checkpoint)
        result = evaluate_targeted_envelope(self.envelope, self.root)
        self.assertEqual(result["state"], "BLOCK")
        self.assertIn("PREVIOUS_CHECKPOINT_MISMATCH", result["failure_classes"])

    def test_non_inert_dispatch_state_is_rejected(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["dispatch"]["attempted"] = True
        with self.assertRaisesRegex(TargetedEffectError, "must remain inert"):
            validate_envelope(envelope)

    def test_non_string_non_claim_fails_closed(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["non_claims"].append({"invalid": True})
        with self.assertRaisesRegex(TargetedEffectError, "non-claims"):
            validate_envelope(envelope)

    def test_evaluation_is_read_only_and_deterministic(self) -> None:
        before = {
            path.relative_to(self.root).as_posix(): sha256_bytes(path.read_bytes())
            for path in self.root.rglob("*")
            if path.is_file()
        }
        first = evaluate_targeted_envelope(self.envelope, self.root)
        second = evaluate_targeted_envelope(self.envelope, self.root)
        after = {
            path.relative_to(self.root).as_posix(): sha256_bytes(path.read_bytes())
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(first, second)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
